"""백테스트 결과를 단일 HTML 대시보드로 저장한다.

템플릿(dashboard_template.html)에 결과 JSON을 끼워 넣기만 하므로 서버 없이 브라우저로 바로 열린다.
"""
from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .backtest import BacktestResult, compute_metrics, run_backtest
from .config import Config

TEMPLATE = Path(__file__).with_name("dashboard_template.html")


def _num(x: float) -> float | None:
    x = float(x)
    return None if not np.isfinite(x) else round(x, 6)


def _run_payload(key: str, name: str, r: BacktestResult, price_digits: int = 2) -> dict:
    eq = r.equity
    dd = eq / eq.cummax() - 1
    monthly = eq.resample("ME").last().pct_change()
    monthly.iloc[0] = eq.resample("ME").last().iloc[0] / eq.iloc[0] - 1
    trades = r.trades_frame()
    reasons = trades["reason"].value_counts().to_dict() if len(trades) else {}
    return {
        "key": key,
        "name": name,
        "metrics": {k: _num(v) for k, v in r.metrics.items()},
        "signalsTotal": int(r.signals_total),
        "signalsFiltered": int(r.signals_filtered),
        "equity": [[d.strftime("%Y-%m-%d"), round(v, 2)] for d, v in eq.items()],
        "drawdown": [round(v, 5) for v in dd],
        "monthly": [[d.strftime("%Y-%m"), _num(v)] for d, v in monthly.items()],
        "reasons": reasons,
        "trades": [
            {
                "ticker": t.ticker,
                "entry": t.entry_date.strftime("%Y-%m-%d"),
                "exit": t.exit_date.strftime("%Y-%m-%d"),
                "shares": int(t.shares),
                "entryPrice": round(float(t.entry_price), price_digits),
                "exitPrice": round(float(t.exit_price), price_digits),
                "pnl": round(float(t.pnl), 2),
                "ret": round(float(t.return_pct), 5),
                "reason": t.reason,
            }
            for t in r.trades
        ],
        "positions": [
            {"ticker": t, "shares": p.shares, "entryPrice": round(p.entry_price, 2),
             "stopPrice": round(p.stop_price, 2), "entry": p.entry_date.strftime("%Y-%m-%d")}
            for t, p in r.open_positions.items()
        ],
    }


def build_dashboard(
    data: dict[str, pd.DataFrame],
    cfg: Config,
    out_path: str | Path,
    source: str,
    standalone: bool = True,
) -> Path:
    runs = [("filtered", "AI 필터 적용", cfg)]
    if cfg.filter.enabled:
        runs.append(("baseline", "전략 단독", replace(cfg, filter=replace(cfg.filter, enabled=False))))
    else:
        runs[0] = ("baseline", "전략 단독", cfg)

    last_close = {t: float(df["close"].iloc[-1]) for t, df in data.items()}
    payload_runs = []
    for key, name, c in runs:
        p = _run_payload(key, name, run_backtest(data, c))
        for pos in p["positions"]:
            pos["lastPrice"] = round(last_close[pos["ticker"]], 2)
        payload_runs.append(p)

    payload = {
        "meta": {
            "source": source,
            "tickers": sorted(data),
            "start": min(df.index[0] for df in data.values()).strftime("%Y-%m-%d"),
            "end": max(df.index[-1] for df in data.values()).strftime("%Y-%m-%d"),
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "initialCash": cfg.initial_cash,
            "stopLoss": cfg.risk.stop_loss_pct,
            "minProb": cfg.filter.min_prob,
            "maxPositions": cfg.risk.max_positions,
            "commission": cfg.cost.commission_rate,
            "slippageBps": cfg.cost.slippage_bps,
        },
        "runs": payload_runs,
    }
    return write_html(payload, out_path, standalone)


def write_html(payload: dict, out_path: str | Path, standalone: bool = True) -> Path:
    # </script> 조기 종료를 막기 위해 '<'를 이스케이프
    blob = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", blob)
    if standalone:
        # 템플릿은 조각(fragment)이라 파일로 직접 열 때는 문서 머리말을 붙인다
        html = (
            '<!doctype html>\n<html lang="ko">\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n' + html
        )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


def build_live_dashboard(
    state_dir: str | Path,
    cfg: Config,
    out_path: str | Path,
    names: dict[str, str] | None = None,
    standalone: bool = True,
) -> Path:
    """kr_live 운영 기록(perf.csv, fills.csv, orders.csv, plans.csv)으로 모의투자 성과 대시보드를 만든다."""
    from .kr_live import STR_COLS, read_csv, round_trips

    d = Path(state_dir)
    perf_p = d / "perf.csv"
    if not perf_p.exists():
        raise SystemExit(f"{perf_p} 가 없습니다. 장 마감 기록(close)이 한 번 이상 돌아야 합니다")
    perf = pd.read_csv(perf_p, parse_dates=["date"]).set_index("date").sort_index()
    equity = perf["equity"].astype(float)
    fills = read_csv(d / "fills.csv", dtype=STR_COLS)
    orders = read_csv(d / "orders.csv", dtype=STR_COLS)
    plans = read_csv(d / "plans.csv")
    trades = round_trips(fills, orders) if not fills.empty else []
    names = names or {}
    for t in trades:
        t.ticker = f"{names[t.ticker]} {t.ticker}" if t.ticker in names else t.ticker

    live = BacktestResult(
        equity=equity, trades=trades, metrics=compute_metrics(equity, trades),
        signals_total=int(plans["signals"].sum()) if len(plans) else 0,
        signals_filtered=int(plans["filtered"].sum()) if len(plans) else 0,
    )
    runs = [_run_payload("filtered", "키움 모의투자", live, price_digits=0)]
    bench = perf["bench_close"].astype(float)
    if bench.notna().sum() >= 2:
        bench = bench.ffill().bfill()
        bench_eq = equity.iloc[0] * bench / bench.iloc[0]
        runs.append(_run_payload("baseline", "KODEX 200 보유", BacktestResult(bench_eq, [], compute_metrics(bench_eq, [])), 0))

    status = json.loads((d / "status.json").read_text()) if (d / "status.json").exists() else {}
    runs[0]["positions"] = [
        {"ticker": f"{names.get(h['ticker'], '')} {h['ticker']}".strip(), "shares": int(h["shares"]),
         "entryPrice": round(float(h["avg_price"])), "stopPrice": round(float(h["stop_price"])),
         "entry": h["entry_date"], "lastPrice": round(float(h["last_price"]))}
        for h in status.get("holdings", [])
    ]
    days = len(equity)
    payload = {
        "meta": {
            "title": "키움 모의투자 성과",
            "positionsTitle": f"현재 보유 종목 · {status.get('holdings_date', '')} 종가 기준",
            "notice": (
                f"모의투자 {days}거래일 기록입니다. "
                + ("기간이 짧아 수익률·샤프 지수는 아직 통계적으로 의미가 약합니다. 최소 3개월 이상 쌓인 뒤 판단하세요."
                   if days < 60 else "백테스트 기대치와 비교해 크게 벗어나는지 확인하세요.")
            ),
            "footNote": "신호는 장 마감 종가, 주문은 다음 거래일 09:00 시장가, 손절은 장중 1분 간격 감시",
            "currency": "KRW",
            "source": "kiwoom-mock",
            "tickers": sorted(names) if names else [],
            "start": equity.index[0].strftime("%Y-%m-%d"),
            "end": equity.index[-1].strftime("%Y-%m-%d"),
            "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "initialCash": float(equity.iloc[0]),
            "stopLoss": cfg.risk.stop_loss_pct,
            "minProb": cfg.filter.min_prob,
            "maxPositions": cfg.risk.max_positions,
            "commission": cfg.cost.commission_rate,
            "slippageBps": cfg.cost.slippage_bps,
        },
        "runs": runs,
    }
    return write_html(payload, out_path, standalone)

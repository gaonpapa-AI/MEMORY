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

from .backtest import BacktestResult, run_backtest
from .config import Config

TEMPLATE = Path(__file__).with_name("dashboard_template.html")


def _num(x: float) -> float | None:
    x = float(x)
    return None if not np.isfinite(x) else round(x, 6)


def _run_payload(key: str, name: str, r: BacktestResult) -> dict:
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
        "signalsTotal": r.signals_total,
        "signalsFiltered": r.signals_filtered,
        "equity": [[d.strftime("%Y-%m-%d"), round(v, 2)] for d, v in eq.items()],
        "drawdown": [round(v, 5) for v in dd],
        "monthly": [[d.strftime("%Y-%m"), _num(v)] for d, v in monthly.items()],
        "reasons": reasons,
        "trades": [
            {
                "ticker": t.ticker,
                "entry": t.entry_date.strftime("%Y-%m-%d"),
                "exit": t.exit_date.strftime("%Y-%m-%d"),
                "shares": t.shares,
                "entryPrice": round(t.entry_price, 2),
                "exitPrice": round(t.exit_price, 2),
                "pnl": round(t.pnl, 2),
                "ret": round(t.return_pct, 5),
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

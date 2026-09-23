"""명령행 진입점.

    python -m aitrader backtest --tickers AAPL MSFT NVDA --start 2018-01-01 --compare
    python -m aitrader backtest --synthetic --compare        # 네트워크 없이 합성 데이터로 데모
    python -m aitrader paper --tickers AAPL MSFT NVDA        # 모의투자 1일 실행 (장 마감 후)
    python -m aitrader dashboard --tickers AAPL MSFT NVDA    # 백테스트 결과 HTML 대시보드
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from . import data as data_mod
from .backtest import run_backtest
from .broker import PaperBroker
from .config import Config
from .dashboard import build_dashboard
from .live import check_stops, run_daily
from .notify import Notifier

DEFAULT_TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "COST", "JPM", "LLY"]


def load_data(args: argparse.Namespace):
    if args.synthetic:
        return data_mod.synthetic(args.tickers or [f"SYN{i}" for i in range(8)])
    if args.csv_dir:
        return data_mod.load_csv_dir(args.csv_dir)
    return data_mod.load_yfinance(args.tickers or DEFAULT_TICKERS, args.start, args.end)


def build_config(args: argparse.Namespace) -> Config:
    cfg = Config(initial_cash=args.cash)
    cfg.risk = replace(cfg.risk, stop_loss_pct=args.stop_loss)
    cfg.filter = replace(cfg.filter, min_prob=args.min_prob, enabled=not args.no_filter)
    return cfg


def fmt_metrics(name: str, r) -> str:
    m = r.metrics
    return (
        f"{name:<14} 총수익 {m['total_return']:+8.2%}  CAGR {m['cagr']:+7.2%}  MDD {m['max_drawdown']:7.2%}  "
        f"샤프 {m['sharpe']:5.2f}  거래 {int(m['trades']):4d}  승률 {m['win_rate']:6.2%}  "
        f"PF {m['profit_factor']:5.2f}"
    )


def cmd_backtest(args: argparse.Namespace) -> None:
    data = load_data(args)
    cfg = build_config(args)
    runs = [("AI 필터 적용" if cfg.filter.enabled else "전략 단독", cfg)]
    if args.compare and cfg.filter.enabled:
        runs.append(("전략 단독", replace(cfg, filter=replace(cfg.filter, enabled=False))))

    print(f"종목 {len(data)}개, 기간 {min(df.index[0] for df in data.values()).date()} ~ "
          f"{max(df.index[-1] for df in data.values()).date()}")
    for name, c in runs:
        r = run_backtest(data, c)
        print(fmt_metrics(name, r))
        if c.filter.enabled:
            print(f"{'':<14} 진입 신호 {r.signals_total}건 중 {r.signals_filtered}건을 AI 필터가 제외 "
                  f"(초기 학습 전 구간 포함)")
        if args.out:
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            slug = "filtered" if c.filter.enabled else "baseline"
            r.equity.to_csv(out / f"equity_{slug}.csv", header=["equity"])
            r.trades_frame().to_csv(out / f"trades_{slug}.csv", index=False)
    if args.out:
        print(f"자산곡선·거래내역 저장: {args.out}/")


def cmd_dashboard(args: argparse.Namespace) -> None:
    data = load_data(args)
    source = "synthetic" if args.synthetic else "csv" if args.csv_dir else "yfinance"
    out = build_dashboard(data, build_config(args), args.out, source, standalone=not args.fragment)
    print(f"대시보드 저장: {out}  (브라우저로 여세요)")


def cmd_paper(args: argparse.Namespace) -> None:
    if not args.synthetic and not args.csv_dir and args.start is None:
        # 지표·학습에 필요한 과거 데이터를 넉넉히 받는다
        args.start = (date.today() - timedelta(days=365 * 4)).isoformat()
    data = load_data(args)
    cfg = build_config(args)
    broker = PaperBroker(cfg.initial_cash, cfg.cost, state_path=args.state)
    broker.set_prices({t: float(df["close"].iloc[-1]) for t, df in data.items()})
    notifier = Notifier()
    check_stops(broker, notifier)
    run_daily(broker, data, cfg, notifier)


def main() -> None:
    p = argparse.ArgumentParser(prog="aitrader", description="미국주식 퀀트 + AI 리스크 필터")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("backtest", "paper", "dashboard"):
        s = sub.add_parser(name)
        s.add_argument("--tickers", nargs="+")
        s.add_argument("--start", default=None if name == "paper" else "2018-01-01")
        s.add_argument("--end")
        s.add_argument("--synthetic", action="store_true", help="합성 데이터 사용 (오프라인 데모)")
        s.add_argument("--csv-dir", help="<티커>.csv 파일이 있는 폴더")
        s.add_argument("--cash", type=float, default=100_000.0)
        s.add_argument("--stop-loss", type=float, default=0.02, help="손절 비율 (기본 0.02 = -2%%)")
        s.add_argument("--min-prob", type=float, default=0.55, help="AI 필터 최소 상승확률")
        s.add_argument("--no-filter", action="store_true", help="AI 필터 끄기")
    bt = sub.choices["backtest"]
    bt.add_argument("--compare", action="store_true", help="AI 필터 적용/미적용 결과 비교")
    bt.add_argument("--out", help="자산곡선·거래내역 CSV 저장 폴더")
    sub.choices["paper"].add_argument("--state", default="paper_state.json", help="모의계좌 상태 파일")

    db = sub.choices["dashboard"]
    db.add_argument("--out", default="reports/dashboard.html", help="저장할 HTML 경로")
    db.add_argument("--fragment", action="store_true", help="<!doctype> 없이 본문 조각만 저장")

    args = p.parse_args()
    {"backtest": cmd_backtest, "paper": cmd_paper, "dashboard": cmd_dashboard}[args.cmd](args)


if __name__ == "__main__":
    main()

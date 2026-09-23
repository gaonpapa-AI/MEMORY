import numpy as np
import pandas as pd
import pytest

from aitrader import data as data_mod
from aitrader import risk
from aitrader.ai_filter import walk_forward_proba
from aitrader.backtest import run_backtest
from aitrader.broker import PaperBroker
from aitrader.config import Config, CostConfig, FilterConfig, RiskConfig
from aitrader.features import make_features
from aitrader.live import check_stops, run_daily
from aitrader.notify import Notifier


def uptrend(days: int = 70, step: float = 0.01) -> pd.DataFrame:
    close = 100 * (1 + step) ** np.arange(days)
    idx = pd.bdate_range("2023-01-02", periods=days)
    return pd.DataFrame(
        {"open": close, "high": close * 1.001, "low": close * 0.999, "close": close, "volume": 1e6},
        index=idx,
    )


def no_filter_config() -> Config:
    cfg = Config(cost=CostConfig(commission_rate=0.0, sec_fee_rate=0.0, slippage_bps=0.0))
    cfg.filter.enabled = False
    return cfg


def test_features_do_not_use_future_data():
    df = data_mod.synthetic(["A"], days=300)["A"]
    full = make_features(df)
    truncated = make_features(df.iloc[:200])
    pd.testing.assert_frame_equal(full.iloc[:200], truncated)


def test_walk_forward_has_no_lookahead():
    data = data_mod.synthetic(["A", "B", "C"], days=700)
    cfg = FilterConfig(train_window=300, retrain_every=21, min_train_samples=200)
    full = walk_forward_proba(data, cfg)
    cutoff = 550
    truncated = walk_forward_proba({t: df.iloc[:cutoff] for t, df in data.items()}, cfg)
    common = truncated.index
    assert truncated.notna().to_numpy().sum() > 0
    pd.testing.assert_frame_equal(full.loc[common], truncated)


def test_position_size_respects_risk_and_cap():
    cfg = RiskConfig(stop_loss_pct=0.02, risk_per_trade=0.005, max_position_pct=0.20)
    # 위험 기준 25,000 vs 비중 한도 20,000 → 20,000 / 100 = 200주
    assert risk.position_size(100_000, 100_000, 100.0, cfg) == 200
    # 현금이 더 적으면 현금 한도
    assert risk.position_size(100_000, 5_000, 100.0, cfg) == 50


def test_stop_loss_exits_at_stop_price():
    df = uptrend()
    buy_day = 50  # 50일 이평이 처음 생기는 49번 인덱스 종가 신호 → 다음날 시가 매수
    entry = df["open"].iloc[buy_day]
    df.iloc[buy_day + 1, df.columns.get_loc("low")] = entry * 0.95
    r = run_backtest({"A": df}, no_filter_config())
    first = r.trades[0]
    assert first.entry_date == df.index[buy_day]
    assert first.reason == "stop_loss"
    assert first.exit_price == pytest.approx(entry * 0.98)


def test_stop_loss_gap_down_fills_at_open():
    df = uptrend()
    buy_day = 50
    entry = df["open"].iloc[buy_day]
    gap_open = entry * 0.90
    df.iloc[buy_day + 1, df.columns.get_loc("open")] = gap_open
    df.iloc[buy_day + 1, df.columns.get_loc("low")] = gap_open * 0.99
    r = run_backtest({"A": df}, no_filter_config())
    assert r.trades[0].reason == "stop_loss"
    assert r.trades[0].exit_price == pytest.approx(gap_open)


def test_daily_loss_limit_blocks_next_entry():
    cfg = RiskConfig(daily_loss_limit_pct=0.03)
    assert risk.daily_loss_breached(100_000, 96_000, cfg)
    assert not risk.daily_loss_breached(100_000, 98_000, cfg)


def test_costs_reduce_pnl():
    data = data_mod.synthetic(["A", "B"], days=400)
    free = run_backtest(data, no_filter_config())
    costly = no_filter_config()
    costly.cost = CostConfig()
    paid = run_backtest(data, costly)
    assert len(free.trades) > 0
    assert paid.equity.iloc[-1] < free.equity.iloc[-1]


def test_paper_broker_accounting(tmp_path):
    cost = CostConfig(commission_rate=0.001, sec_fee_rate=0.0, slippage_bps=0.0)
    state = tmp_path / "state.json"
    b = PaperBroker(10_000, cost, state_path=state)
    b.set_prices({"A": 100.0})
    fill = b.buy("A", 10, 0.02, "2024-01-02")
    assert fill.shares == 10
    assert b.get_cash() == pytest.approx(10_000 - 1000 - 1.0)
    assert b.get_positions()["A"].stop_price == pytest.approx(98.0)

    # 상태 파일에서 복원
    b2 = PaperBroker(0, cost, state_path=state)
    b2.set_prices({"A": 97.0})
    stopped = check_stops(b2, Notifier(token="", chat_id=""))
    assert stopped == ["A"]
    assert b2.get_positions() == {}
    assert b2.get_cash() == pytest.approx(10_000 - 1001 + 970 - 0.97)


def test_run_daily_buys_on_entry_signal():
    df = uptrend(days=60)
    cfg = no_filter_config()
    b = PaperBroker(cfg.initial_cash, cfg.cost)
    b.set_prices({"A": float(df["close"].iloc[-1])})
    run_daily(b, {"A": df}, cfg, Notifier(token="", chat_id=""))
    pos = b.get_positions()["A"]
    assert pos.shares > 0
    assert pos.stop_price == pytest.approx(pos.avg_price * 0.98)

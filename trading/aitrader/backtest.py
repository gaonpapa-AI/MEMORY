"""일봉 이벤트 기반 백테스터.

하루의 처리 순서:
1. 시가: 전일 종가에 낸 매도 → 매수 주문 체결 (슬리피지·수수료·SEC 수수료 반영)
2. 장중: 보유 종목의 저가가 손절가 이하이면 손절. 시가부터 손절가 아래로 갭하락했다면 시가에 체결
3. 종가: 평가금액 기록, 일일 손실 한도 점검
4. 종가 신호: 청산 신호·최대 보유기간 → 다음날 매도 주문 / 진입 신호 + AI 필터 → 다음날 매수 주문
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import risk
from .ai_filter import walk_forward_proba
from .config import Config
from .strategy import generate_signals


@dataclass
class Position:
    shares: int
    entry_price: float
    stop_price: float
    entry_date: pd.Timestamp
    entry_cost: float  # 수수료 포함 총 매수금액


@dataclass
class Trade:
    ticker: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    shares: int
    entry_price: float
    exit_price: float
    pnl: float
    return_pct: float
    reason: str


@dataclass
class BacktestResult:
    equity: pd.Series
    trades: list[Trade]
    metrics: dict[str, float]
    signals_total: int = 0
    signals_filtered: int = 0
    open_positions: dict[str, Position] = field(default_factory=dict)

    def trades_frame(self) -> pd.DataFrame:
        return pd.DataFrame([t.__dict__ for t in self.trades])


def compute_metrics(equity: pd.Series, trades: list[Trade]) -> dict[str, float]:
    rets = equity.pct_change().dropna()
    years = max(len(equity) / 252, 1e-9)
    total = equity.iloc[-1] / equity.iloc[0] - 1
    drawdown = equity / equity.cummax() - 1
    std = rets.std()
    pnls = np.array([t.pnl for t in trades])
    wins, losses = pnls[pnls > 0], pnls[pnls <= 0]
    return {
        "total_return": total,
        "cagr": (1 + total) ** (1 / years) - 1 if total > -1 else -1.0,
        "max_drawdown": drawdown.min(),
        "sharpe": rets.mean() / std * np.sqrt(252) if std > 0 else 0.0,
        "trades": float(len(trades)),
        "win_rate": len(wins) / len(pnls) if len(pnls) else 0.0,
        "profit_factor": wins.sum() / -losses.sum() if losses.sum() < 0 else float("inf") if len(wins) else 0.0,
        "avg_trade_return": float(np.mean([t.return_pct for t in trades])) if trades else 0.0,
    }


def run_backtest(
    data: dict[str, pd.DataFrame],
    cfg: Config,
    probs: pd.DataFrame | None = None,
) -> BacktestResult:
    """probs를 주지 않으면 cfg.filter.enabled일 때 워크포워드로 계산한다."""
    c = cfg.cost
    slip = c.slippage_bps / 10_000
    signals = {t: generate_signals(df, cfg.strategy) for t, df in data.items()}
    if cfg.filter.enabled and probs is None:
        probs = walk_forward_proba(data, cfg.filter)

    dates = sorted(set().union(*(df.index for df in data.values())))
    cash = cfg.initial_cash
    positions: dict[str, Position] = {}
    trades: list[Trade] = []
    pending_sells: dict[str, str] = {}  # ticker -> 사유
    pending_buys: dict[str, int] = {}  # ticker -> 주식 수
    equity_curve = {}
    prev_equity = cfg.initial_cash
    halt_entries = False
    n_signals = n_filtered = 0

    def bar(t: str, d: pd.Timestamp) -> pd.Series | None:
        df = data[t]
        return df.loc[d] if d in df.index else None

    def close_position(t: str, d: pd.Timestamp, raw_price: float, reason: str) -> None:
        nonlocal cash
        pos = positions.pop(t)
        price = raw_price * (1 - slip)
        gross = price * pos.shares
        proceeds = gross - gross * (c.commission_rate + c.sec_fee_rate)
        cash += proceeds
        pnl = proceeds - pos.entry_cost
        trades.append(
            Trade(t, pos.entry_date, d, pos.shares, pos.entry_price, price, pnl, pnl / pos.entry_cost, reason)
        )

    for d in dates:
        # 1) 시가 체결: 매도 먼저, 그다음 매수
        for t, reason in list(pending_sells.items()):
            b = bar(t, d)
            if b is not None and t in positions:
                close_position(t, d, b["open"], reason)
                del pending_sells[t]
        for t, shares in list(pending_buys.items()):
            b = bar(t, d)
            if b is None:
                continue  # 해당 종목 거래 없는 날이면 주문 취소
            price = b["open"] * (1 + slip)
            unit_cost = price * (1 + c.commission_rate)
            shares = min(shares, int(cash // unit_cost))
            if shares > 0:
                cost = shares * unit_cost
                cash -= cost
                positions[t] = Position(shares, price, risk.stop_price(price, cfg.risk), d, cost)
        pending_buys.clear()

        # 2) 장중 손절
        for t in list(positions):
            b = bar(t, d)
            pos = positions[t]
            if b is not None and b["low"] <= pos.stop_price:
                close_position(t, d, min(b["open"], pos.stop_price), "stop_loss")
                pending_sells.pop(t, None)

        # 3) 종가 평가
        equity = cash
        for t, pos in positions.items():
            df = data[t]
            last_close = df["close"].loc[:d].iloc[-1]
            equity += pos.shares * last_close
        equity_curve[d] = equity
        halt_entries = risk.daily_loss_breached(prev_equity, equity, cfg.risk)
        prev_equity = equity

        # 4) 종가 신호 → 다음 거래일 주문
        for t, pos in positions.items():
            sig = signals[t]
            if d not in sig.index:
                continue
            held_days = len(data[t].loc[pos.entry_date : d]) - 1
            if sig.at[d, "exit"]:
                pending_sells[t] = "exit_signal"
            elif held_days >= cfg.risk.max_holding_days:
                pending_sells[t] = "max_holding"

        if halt_entries:
            continue
        candidates = []
        for t, sig in signals.items():
            if t in positions or d not in sig.index or not sig.at[d, "entry"]:
                continue
            n_signals += 1
            p = np.nan
            if probs is not None:
                p = probs.at[d, t] if d in probs.index and t in probs.columns else np.nan
                if cfg.filter.enabled and not (p >= cfg.filter.min_prob):
                    n_filtered += 1  # 확률 미달이거나 아직 학습 전이면 진입하지 않음
                    continue
            candidates.append((p if not np.isnan(p) else 0.0, t))

        slots = cfg.risk.max_positions - (len(positions) - len(pending_sells))
        budget_cash = cash
        for _, t in sorted(candidates, reverse=True)[: max(0, slots)]:
            price = data[t].at[d, "close"]
            per_share = price * (1 + slip) * (1 + c.commission_rate)
            shares = risk.position_size(equity, budget_cash, per_share, cfg.risk)
            if shares > 0:
                pending_buys[t] = shares
                budget_cash -= shares * per_share

    equity_s = pd.Series(equity_curve).sort_index()
    return BacktestResult(
        equity=equity_s,
        trades=trades,
        metrics=compute_metrics(equity_s, trades),
        signals_total=n_signals,
        signals_filtered=n_filtered,
        open_positions=positions,
    )

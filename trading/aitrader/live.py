"""실거래/모의투자 루틴.

- run_daily: 하루 한 번(미국장 마감 후) 실행. 청산 신호 → 매도, 진입 신호 + AI 필터 → 매수
- check_stops: 장중에 주기적으로 실행. 현재가가 손절가 이하인 종목을 즉시 매도
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import risk
from .ai_filter import predict_latest
from .broker import Broker
from .config import Config
from .notify import Notifier
from .strategy import generate_signals


def check_stops(broker: Broker, notifier: Notifier) -> list[str]:
    stopped = []
    for t, pos in broker.get_positions().items():
        price = broker.get_price(t)
        if price <= pos.stop_price:
            fill = broker.sell(t, pos.shares)
            if fill:
                stopped.append(t)
                notifier.send(
                    f"[손절] {t} {fill.shares}주 @ {fill.price:.2f} "
                    f"(진입 {pos.avg_price:.2f}, {fill.price / pos.avg_price - 1:+.2%})"
                )
    return stopped


def run_daily(broker: Broker, data: dict[str, pd.DataFrame], cfg: Config, notifier: Notifier) -> None:
    today = max(df.index[-1] for df in data.values())
    today_str = today.strftime("%Y-%m-%d")
    signals = {t: generate_signals(df, cfg.strategy) for t, df in data.items()}

    # 1) 청산
    for t, pos in broker.get_positions().items():
        if t not in data:
            continue
        sig = signals[t]
        held_days = len(data[t].loc[pos.entry_date :]) - 1
        reason = None
        if sig["exit"].iloc[-1]:
            reason = "청산 신호"
        elif held_days >= cfg.risk.max_holding_days:
            reason = "최대 보유기간"
        if reason:
            fill = broker.sell(t, pos.shares)
            if fill:
                notifier.send(f"[매도] {t} {fill.shares}주 @ {fill.price:.2f} ({reason})")

    # 2) 진입
    positions = broker.get_positions()
    candidates = [
        t for t, sig in signals.items()
        if t not in positions and sig.index[-1] == today and sig["entry"].iloc[-1]
    ]
    if not candidates:
        notifier.send(f"[{today_str}] 진입 신호 없음. 보유 {len(positions)}종목, 평가금액 {broker.equity():,.0f}")
        return

    probs = predict_latest(data, cfg.filter) if cfg.filter.enabled else pd.Series(dtype=float)
    ranked = []
    for t in candidates:
        p = probs.get(t, np.nan)
        if cfg.filter.enabled and not (p >= cfg.filter.min_prob):
            notifier.send(f"[필터] {t} 진입 신호 제외 (AI 상승확률 {p:.2f} < {cfg.filter.min_prob})")
            continue
        ranked.append((0.0 if np.isnan(p) else p, t))

    slots = cfg.risk.max_positions - len(positions)
    equity = broker.equity()
    for p, t in sorted(ranked, reverse=True)[: max(0, slots)]:
        shares = risk.position_size(equity, broker.get_cash(), broker.get_price(t), cfg.risk)
        fill = broker.buy(t, shares, cfg.risk.stop_loss_pct, today_str)
        if fill:
            notifier.send(
                f"[매수] {t} {fill.shares}주 @ {fill.price:.2f} (AI 확률 {p:.2f}, "
                f"손절가 {fill.price * (1 - cfg.risk.stop_loss_pct):.2f})"
            )
    notifier.send(f"[{today_str}] 완료. 현금 {broker.get_cash():,.0f}, 평가금액 {broker.equity():,.0f}")

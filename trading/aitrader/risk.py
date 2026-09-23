"""하드코딩된 리스크 관리 규칙. AI 판단과 무관하게 항상 적용된다."""
from __future__ import annotations

import math

from .config import RiskConfig


def stop_price(entry_price: float, cfg: RiskConfig) -> float:
    return entry_price * (1 - cfg.stop_loss_pct)


def position_size(equity: float, cash: float, price: float, cfg: RiskConfig) -> int:
    """손절 시 손실이 계좌의 risk_per_trade를 넘지 않도록 주식 수를 정한다.

    예: 계좌 10만달러, risk_per_trade 0.5%, 손절폭 2% → 손실 한도 500달러 → 투입금 25,000달러.
    다만 max_position_pct(종목당 최대 비중)와 가용 현금을 넘을 수 없다.
    """
    if price <= 0:
        return 0
    by_risk = equity * cfg.risk_per_trade / cfg.stop_loss_pct
    by_cap = equity * cfg.max_position_pct
    budget = min(by_risk, by_cap, cash)
    return max(0, math.floor(budget / price))


def daily_loss_breached(prev_equity: float, equity: float, cfg: RiskConfig) -> bool:
    return prev_equity > 0 and (equity / prev_equity - 1) <= -cfg.daily_loss_limit_pct

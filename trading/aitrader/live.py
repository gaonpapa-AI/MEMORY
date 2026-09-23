"""실거래/모의투자 루틴.

백테스트와 같은 시점에 체결되도록 두 단계로 나눈다.
- plan_orders: 장 마감 후 종가 기준으로 다음 거래일 주문 목록을 만든다
- execute_orders: 다음 거래일 장 시작 직후 주문을 낸다 (시장가)
- check_stops: 장중에 주기적으로 실행. 현재가가 손절가 이하인 종목을 즉시 매도

run_daily는 plan + execute를 곧바로 이어서 실행한다 (가상 체결 모의계좌용).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from . import risk
from .ai_filter import predict_latest
from .broker import Broker, BrokerPosition
from .config import Config
from .notify import Notifier
from .strategy import generate_signals


@dataclass
class Order:
    ticker: str
    side: str  # "buy" | "sell"
    shares: int
    reason: str
    prob: float | None = None
    ref_price: float | None = None  # 주문을 계획한 날의 종가

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PlanInfo:
    date: str
    signals: int
    filtered: int
    notes: list[str]


def plan_orders(
    data: dict[str, pd.DataFrame],
    positions: dict[str, BrokerPosition],
    equity: float,
    cash: float,
    cfg: Config,
    halt_entries: bool = False,
) -> tuple[list[Order], PlanInfo]:
    today = max(df.index[-1] for df in data.values())
    signals = {t: generate_signals(df, cfg.strategy) for t, df in data.items()}
    orders: list[Order] = []
    notes: list[str] = []

    # 1) 청산
    for t, pos in positions.items():
        if t not in data:
            continue
        sig = signals[t]
        held_days = len(data[t].loc[pos.entry_date :]) - 1
        reason = None
        if sig["exit"].iloc[-1]:
            reason = "exit_signal"
        elif held_days >= cfg.risk.max_holding_days:
            reason = "max_holding"
        if reason:
            orders.append(Order(t, "sell", pos.shares, reason, ref_price=float(data[t]["close"].iloc[-1])))

    info = PlanInfo(today.strftime("%Y-%m-%d"), 0, 0, notes)
    if halt_entries:
        notes.append("일일 손실 한도 초과로 신규 진입 중단")
        return orders, info

    # 2) 진입
    candidates = [
        t for t, sig in signals.items()
        if t not in positions and sig.index[-1] == today and sig["entry"].iloc[-1]
    ]
    info.signals = len(candidates)
    if not candidates:
        return orders, info
    probs = predict_latest(data, cfg.filter) if cfg.filter.enabled else pd.Series(dtype=float)
    ranked = []
    for t in candidates:
        p = float(probs.get(t, np.nan))
        if cfg.filter.enabled and not (p >= cfg.filter.min_prob):
            info.filtered += 1
            notes.append(f"{t} 진입 신호 제외 (AI 상승확률 {p:.2f} < {cfg.filter.min_prob})")
            continue
        ranked.append((0.0 if np.isnan(p) else p, t))

    selling = sum(1 for o in orders if o.side == "sell")
    slots = cfg.risk.max_positions - (len(positions) - selling)
    budget = cash
    slip = cfg.cost.slippage_bps / 10_000
    for p, t in sorted(ranked, reverse=True)[: max(0, slots)]:
        close = float(data[t]["close"].iloc[-1])
        per_share = close * (1 + slip) * (1 + cfg.cost.commission_rate)
        shares = risk.position_size(equity, budget, per_share, cfg.risk)
        if shares > 0:
            orders.append(Order(t, "buy", shares, "entry_signal", prob=p, ref_price=close))
            budget -= shares * per_share
    return orders, info


REASON_KO = {"exit_signal": "청산 신호", "max_holding": "최대 보유기간", "entry_signal": "진입 신호", "stop_loss": "손절"}


def execute_orders(broker: Broker, orders: list[Order], cfg: Config, today: str, notifier: Notifier) -> list[dict]:
    """매도 먼저, 그다음 매수. 주문 결과(성공/실패)를 기록용 dict로 돌려준다."""
    results = []
    held = broker.get_positions()
    for o in sorted(orders, key=lambda o: o.side != "sell"):
        rec = o.to_dict() | {"date": today, "status": "", "order_no": "", "est_price": None, "error": ""}
        try:
            if o.side == "sell":
                if o.ticker not in held:
                    rec["status"] = "skipped"
                    rec["error"] = "보유하지 않음 (이미 손절 등)"
                    results.append(rec)
                    continue
                fill = broker.sell(o.ticker, held[o.ticker].shares)
            else:
                fill = broker.buy(o.ticker, o.shares, cfg.risk.stop_loss_pct, today)
            if fill is None:
                rec["status"] = "skipped"
                rec["error"] = "주문 수량 0 또는 현금 부족"
            else:
                rec |= {"status": "sent", "order_no": fill.order_no, "est_price": fill.price, "shares": fill.shares}
                side = "매수" if o.side == "buy" else "매도"
                extra = f", AI 확률 {o.prob:.2f}" if o.prob is not None else ""
                notifier.send(f"[{side}] {o.ticker} {fill.shares}주 @ 약 {fill.price:,.2f} ({REASON_KO.get(o.reason, o.reason)}{extra})")
        except Exception as e:  # 한 종목 실패가 나머지 주문을 막지 않게
            rec["status"] = "error"
            rec["error"] = str(e)
            notifier.send(f"[주문 실패] {o.ticker} {o.side} {o.shares}주: {e}")
        results.append(rec)
    return results


def check_stops(broker: Broker, notifier: Notifier, skip: set[str] | None = None) -> list[str]:
    """skip: 오늘 이미 매도 주문을 낸 종목 (체결 대기 중 중복 매도 방지)."""
    stopped = []
    for t, pos in broker.get_positions().items():
        if skip and t in skip:
            continue
        price = broker.get_price(t)
        if price <= pos.stop_price:
            try:
                fill = broker.sell(t, pos.shares)
            except Exception as e:  # 한 종목 실패가 다른 종목 손절을 막지 않게
                notifier.send(f"[손절 실패] {t}: {e}")
                continue
            if fill:
                stopped.append(t)
                notifier.send(
                    f"[손절] {t} {fill.shares}주 @ 약 {fill.price:,.2f} "
                    f"(진입 {pos.avg_price:,.2f}, {fill.price / pos.avg_price - 1:+.2%})"
                )
    return stopped


def run_daily(broker: Broker, data: dict[str, pd.DataFrame], cfg: Config, notifier: Notifier) -> None:
    orders, info = plan_orders(data, broker.get_positions(), broker.equity(), broker.get_cash(), cfg)
    for n in info.notes:
        notifier.send(f"[필터] {n}")
    if not orders:
        notifier.send(f"[{info.date}] 주문 없음. 평가금액 {broker.equity():,.0f}")
        return
    execute_orders(broker, orders, cfg, info.date, notifier)
    notifier.send(f"[{info.date}] 완료. 현금 {broker.get_cash():,.0f}, 평가금액 {broker.equity():,.0f}")

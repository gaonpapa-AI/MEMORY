"""주문 집행 계층.

전략·리스크 코드는 Broker 인터페이스에만 의존한다. 실제 증권사를 붙일 때는 Broker를 상속한
어댑터 하나만 구현하면 된다. 지금은 모의투자용 PaperBroker만 제공한다.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import CostConfig


@dataclass
class BrokerPosition:
    shares: int
    avg_price: float
    stop_price: float
    entry_date: str  # YYYY-MM-DD


@dataclass
class Fill:
    ticker: str
    side: str  # "buy" | "sell"
    shares: int
    price: float
    fee: float


class Broker(ABC):
    @abstractmethod
    def get_cash(self) -> float: ...

    @abstractmethod
    def get_positions(self) -> dict[str, BrokerPosition]: ...

    @abstractmethod
    def get_price(self, ticker: str) -> float: ...

    @abstractmethod
    def buy(self, ticker: str, shares: int, stop_price_pct: float, date: str) -> Fill | None:
        """시장가 매수. 체결되면 진입가 × (1 - stop_price_pct)를 손절가로 기록한다."""

    @abstractmethod
    def sell(self, ticker: str, shares: int) -> Fill | None: ...

    def equity(self) -> float:
        return self.get_cash() + sum(p.shares * self.get_price(t) for t, p in self.get_positions().items())


class PaperBroker(Broker):
    """메모리(+선택적 JSON 파일)에서 동작하는 모의 브로커. 슬리피지·수수료를 백테스터와 같게 적용."""

    def __init__(self, cash: float, cost: CostConfig, state_path: str | Path | None = None):
        self.cost = cost
        self.state_path = Path(state_path) if state_path else None
        self.cash = cash
        self.positions: dict[str, BrokerPosition] = {}
        self.prices: dict[str, float] = {}
        if self.state_path and self.state_path.exists():
            state = json.loads(self.state_path.read_text())
            self.cash = state["cash"]
            self.positions = {t: BrokerPosition(**p) for t, p in state["positions"].items()}

    def save(self) -> None:
        if self.state_path:
            state = {"cash": self.cash, "positions": {t: asdict(p) for t, p in self.positions.items()}}
            self.state_path.write_text(json.dumps(state, indent=2))

    def set_prices(self, prices: dict[str, float]) -> None:
        self.prices.update(prices)

    def get_cash(self) -> float:
        return self.cash

    def get_positions(self) -> dict[str, BrokerPosition]:
        return dict(self.positions)

    def get_price(self, ticker: str) -> float:
        if ticker not in self.prices:
            raise KeyError(f"{ticker}: 현재가가 없습니다. set_prices()로 먼저 넣어주세요")
        return self.prices[ticker]

    def buy(self, ticker: str, shares: int, stop_price_pct: float, date: str) -> Fill | None:
        price = self.get_price(ticker) * (1 + self.cost.slippage_bps / 10_000)
        unit_cost = price * (1 + self.cost.commission_rate)
        shares = min(shares, int(self.cash // unit_cost))
        if shares <= 0 or ticker in self.positions:
            return None
        fee = shares * price * self.cost.commission_rate
        self.cash -= shares * price + fee
        self.positions[ticker] = BrokerPosition(shares, price, price * (1 - stop_price_pct), date)
        self.save()
        return Fill(ticker, "buy", shares, price, fee)

    def sell(self, ticker: str, shares: int) -> Fill | None:
        pos = self.positions.get(ticker)
        if pos is None:
            return None
        shares = min(shares, pos.shares)
        price = self.get_price(ticker) * (1 - self.cost.slippage_bps / 10_000)
        fee = shares * price * (self.cost.commission_rate + self.cost.sec_fee_rate)
        self.cash += shares * price - fee
        if shares == pos.shares:
            del self.positions[ticker]
        else:
            pos.shares -= shares
        self.save()
        return Fill(ticker, "sell", shares, price, fee)

"""국내주식 모의투자/실거래 운영기.

하루 흐름 (한국시간):
- 09:00:30  execute  : 전날 장 마감 후 만든 주문을 시장가로 낸다 (백테스트의 "다음날 시가 체결"과 같은 시점)
- 09:01~15:19 monitor: 1분마다 보유 종목 현재가를 확인해 손절가 이하면 즉시 매도
- 15:40     close    : 당일 체결내역·평가금액·벤치마크(KODEX 200) 종가를 기록하고, 다음날 주문을 계획한다

모든 기록은 state_dir 아래 CSV/JSON으로 남고, report가 이를 대시보드로 만든다.
"""
from __future__ import annotations

import json
import logging
import time as time_mod
from collections import defaultdict, deque
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .backtest import Trade
from .broker import Broker
from .config import Config
from .live import Order, check_stops, execute_orders, plan_orders
from .notify import Notifier

log = logging.getLogger(__name__)
KST = ZoneInfo("Asia/Seoul")

# 대형주 위주 기본 종목 (종목코드 6자리)
KR_UNIVERSE = {
    "005930": "삼성전자", "000660": "SK하이닉스", "373220": "LG에너지솔루션", "207940": "삼성바이오로직스",
    "005380": "현대차", "000270": "기아", "068270": "셀트리온", "035420": "NAVER",
    "105560": "KB금융", "055550": "신한지주", "012330": "현대모비스", "035720": "카카오",
    "051910": "LG화학", "006400": "삼성SDI", "028260": "삼성물산", "066570": "LG전자",
    "003550": "LG", "032830": "삼성생명", "015760": "한국전력", "017670": "SK텔레콤",
}
BENCHMARK = "069500"  # KODEX 200


def now_kst() -> datetime:
    return datetime.now(KST)


def is_trading_day(d: date) -> bool:
    """주말·공휴일·연말(12/31) 휴장일이면 False. 임시공휴일은 holidays 패키지 갱신에 의존한다."""
    if d.weekday() >= 5 or (d.month == 12 and d.day == 31):
        return False
    try:
        import holidays

        return d not in holidays.KR(years=d.year)
    except ImportError:
        return True


def read_csv(path: Path, **kw) -> pd.DataFrame:
    """없거나 비어 있는 CSV는 빈 DataFrame으로."""
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path, **kw)


STR_COLS = {"ticker": str, "code": str, "order_no": str}


def previous_trading_day(d: date) -> date:
    d -= timedelta(days=1)
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d


class LiveTrader:
    def __init__(
        self,
        broker: Broker,
        cfg: Config,
        load_data: Callable[[], dict[str, pd.DataFrame]],
        state_dir: str | Path,
        notifier: Notifier,
        bench_price: Callable[[], float] | None = None,
        fetch_fills: Callable[[], list[dict]] | None = None,
        names: dict[str, str] | None = None,
    ):
        self.broker = broker
        self.cfg = cfg
        self.load_data = load_data
        self.dir = Path(state_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.notifier = notifier
        self.bench_price = bench_price
        self.fetch_fills = fetch_fills
        self.names = names or {}
        self._sold: tuple[str, set[str]] = ("", set())  # (날짜, 그날 매도 주문을 낸 종목)

    def _sold_today(self, today: date) -> set[str]:
        if self._sold[0] != str(today):
            self._sold = (str(today), set())
        return self._sold[1]

    # ---------- 상태 파일 ----------
    def _path(self, name: str) -> Path:
        return self.dir / name

    def _status(self) -> dict:
        p = self._path("status.json")
        return json.loads(p.read_text()) if p.exists() else {}

    def _set_status(self, **kw) -> None:
        st = self._status() | kw
        self._path("status.json").write_text(json.dumps(st, ensure_ascii=False, indent=2))

    def _append_csv(self, name: str, rows: list[dict]) -> None:
        if not rows:
            return
        p = self._path(name)
        df = pd.concat([read_csv(p, dtype=STR_COLS), pd.DataFrame(rows)], ignore_index=True)
        df.to_csv(p, index=False)

    def label(self, code: str) -> str:
        return f"{self.names[code]}({code})" if code in self.names else code

    # ---------- 장 마감 후 ----------
    def close(self, today: date | None = None, force: bool = False) -> None:
        """당일 기록 + 다음날 주문 계획."""
        today = today or now_kst().date()
        data = self.load_data()
        last_bar = max(df.index[-1] for df in data.values()).date()
        if last_bar != today and not force:
            self.notifier.send(f"[{today}] 오늘 일봉이 없습니다 (마지막 {last_bar}). 휴장일로 보고 건너뜁니다")
            return
        self.snapshot(today)
        self.plan(data, today)
        self._set_status(last_close=str(today))

    def snapshot(self, today: date) -> None:
        positions = self.broker.get_positions()
        equity = self.broker.equity()
        cash = self.broker.get_cash()
        bench = self.bench_price() if self.bench_price else np.nan
        row = {"date": str(today), "equity": equity, "cash": cash, "positions": len(positions), "bench_close": bench}
        p = self._path("perf.csv")
        perf = pd.read_csv(p) if p.exists() else pd.DataFrame(columns=list(row))
        perf = perf[perf["date"] != str(today)]
        pd.concat([perf, pd.DataFrame([row])], ignore_index=True).to_csv(p, index=False)

        holdings = [
            {"ticker": t, "shares": pos.shares, "avg_price": pos.avg_price, "stop_price": pos.stop_price,
             "entry_date": pos.entry_date, "last_price": self.broker.get_price(t)}
            for t, pos in positions.items()
        ]
        self._set_status(holdings=holdings, holdings_date=str(today))

        if self.fetch_fills:
            fills = [normalize_fill(f, today) for f in self.fetch_fills()]
            fills = [f for f in fills if f["qty"] > 0]
            fp = self._path("fills.csv")
            old = read_csv(fp, dtype=STR_COLS)
            if not old.empty:
                old = old[old["date"] != str(today)]
            merged = pd.concat([old, pd.DataFrame(fills)], ignore_index=True)
            if not merged.empty:
                merged.to_csv(fp, index=False)

        first = perf["equity"].iloc[0] if len(perf) else equity
        self.notifier.send(
            f"[{today} 마감] 추정자산 {equity:,.0f}원 (시작 대비 {equity / first - 1:+.2%}), "
            f"보유 {len(positions)}종목, 예수금 {cash:,.0f}원"
        )

    def plan(self, data: dict[str, pd.DataFrame], today: date) -> list[Order]:
        perf_p = self._path("perf.csv")
        halt = False
        if perf_p.exists():
            perf = pd.read_csv(perf_p)
            if len(perf) >= 2:
                prev, cur = perf["equity"].iloc[-2], perf["equity"].iloc[-1]
                halt = prev > 0 and cur / prev - 1 <= -self.cfg.risk.daily_loss_limit_pct
        positions = self.broker.get_positions()
        orders, info = plan_orders(data, positions, self.broker.equity(), self.broker.get_cash(), self.cfg, halt)
        self._path("pending.json").write_text(
            json.dumps({"planned_on": str(today), "orders": [o.to_dict() for o in orders]}, ensure_ascii=False, indent=2)
        )
        self._append_csv("plans.csv", [{"date": str(today), "signals": info.signals, "filtered": info.filtered,
                                        "buy_orders": sum(o.side == "buy" for o in orders),
                                        "sell_orders": sum(o.side == "sell" for o in orders)}])
        lines = [f"[{today} 계획] 진입 신호 {info.signals}건, AI 필터 제외 {info.filtered}건"]
        lines += [f"  · {n}" for n in info.notes]
        lines += [f"  · 내일 {'매수' if o.side == 'buy' else '매도'} {self.label(o.ticker)} {o.shares}주 ({o.reason})" for o in orders]
        if not orders:
            lines.append("  · 내일 주문 없음")
        self.notifier.send("\n".join(lines))
        return orders

    # ---------- 장 시작 ----------
    def execute(self, today: date | None = None) -> list[dict]:
        today = today or now_kst().date()
        p = self._path("pending.json")
        if not p.exists():
            return []
        pending = json.loads(p.read_text())
        if pending.get("executed_on"):
            return []
        expected = previous_trading_day(today)
        if pending.get("planned_on") != str(expected):
            # 며칠 묵은 주문을 오늘 시가에 내면 백테스트와 어긋난다
            self.notifier.send(
                f"[{today}] {pending.get('planned_on')}에 만든 주문은 오래되어 내지 않습니다 "
                f"(직전 거래일 {expected}). 오늘 장 마감 후 새로 계획합니다"
            )
            pending["executed_on"] = f"expired:{today}"
            p.write_text(json.dumps(pending, ensure_ascii=False, indent=2))
            return []
        orders = [Order(**o) for o in pending["orders"]]
        results = execute_orders(self.broker, orders, self.cfg, str(today), self.notifier) if orders else []
        self._sold_today(today).update(r["ticker"] for r in results if r["side"] == "sell" and r["status"] == "sent")
        self._append_csv("orders.csv", results)
        pending["executed_on"] = str(today)
        p.write_text(json.dumps(pending, ensure_ascii=False, indent=2))
        self._set_status(last_execute=str(today))
        return results

    # ---------- 장중 ----------
    def monitor_once(self, today: date | None = None) -> list[str]:
        today = today or now_kst().date()
        positions = self.broker.get_positions()
        sold = self._sold_today(today)
        stopped = check_stops(self.broker, self.notifier, skip=sold)
        sold.update(stopped)
        self._append_csv("orders.csv", [
            {"date": str(today), "ticker": t, "side": "sell", "shares": positions[t].shares, "reason": "stop_loss",
             "status": "sent", "time": now_kst().strftime("%H:%M:%S")}
            for t in stopped
        ])
        return stopped

    # ---------- 스케줄러 ----------
    def run_forever(
        self,
        execute_at: time = time(9, 0, 30),
        monitor_from: time = time(9, 1),
        monitor_to: time = time(15, 19),
        close_at: time = time(15, 40),
        interval: int = 60,
    ) -> None:
        self.notifier.send("[aitrader] 키움 모의투자 운영을 시작합니다. 이 창을 닫으면 멈춥니다")
        while True:
            now = now_kst()
            today, t = now.date(), now.time()
            st = self._status()
            try:
                if is_trading_day(today):
                    if t >= execute_at and st.get("last_execute") != str(today) and t < close_at:
                        self.execute(today)
                    if monitor_from <= t <= monitor_to:
                        self.monitor_once(today)
                    if t >= close_at and st.get("last_close") != str(today):
                        self.close(today)
            except Exception as e:  # 네트워크 오류 등으로 루프가 죽지 않게
                log.exception("운영 루프 오류")
                self.notifier.send(f"[오류] {type(e).__name__}: {e}")
            time_mod.sleep(interval)


def normalize_fill(f: dict, today: date) -> dict:
    """키움 체결내역(ka10076) 한 줄 → fills.csv 한 줄. 이미 정리된 dict면 그대로 쓴다."""
    from .kiwoom import strip_code, to_num, to_price

    if "side" in f and "qty" in f:
        return f
    side = "sell" if "매도" in str(f.get("io_tp_nm", "")) else "buy"
    return {
        "date": str(today),
        "time": str(f.get("ord_tm", "")),
        "order_no": str(f.get("ord_no", "")),
        "code": strip_code(f.get("stk_cd", "")),
        "name": str(f.get("stk_nm", "")).strip(),
        "side": side,
        "qty": int(abs(to_num(f.get("cntr_qty")))),
        "price": to_price(f.get("cntr_pric")),
        "fee": abs(to_num(f.get("tdy_trde_cmsn"))),
        "tax": abs(to_num(f.get("tdy_trde_tax"))),
    }


def round_trips(fills: pd.DataFrame, orders: pd.DataFrame | None = None) -> list[Trade]:
    """체결내역을 선입선출로 짝지어 매수→매도 거래 목록을 만든다."""
    # 청산 사유: 주문번호로 찾고, 없으면 같은 날·같은 종목의 매도 주문 기록으로 찾는다
    reason_by_order: dict[str, str] = {}
    reason_by_day: dict[tuple[str, str], str] = {}
    if orders is not None and not orders.empty and "reason" in orders:
        for _, o in orders.iterrows():
            if str(o.get("side")) != "sell":
                continue
            reason = str(o["reason"])
            if pd.notna(o.get("order_no")) and str(o.get("order_no")):
                reason_by_order[str(o["order_no"])] = reason
            key = (str(o["ticker"]), str(o["date"]))
            if reason_by_day.get(key) != "stop_loss":  # 같은 날 손절이 있으면 손절을 우선
                reason_by_day[key] = reason

    lots: dict[str, deque] = defaultdict(deque)
    trades: list[Trade] = []
    fills = fills.sort_values(["date", "time"], kind="stable")
    for _, f in fills.iterrows():
        code, qty, price = str(f["code"]), int(f["qty"]), float(f["price"])
        cost_extra = float(f.get("fee", 0) or 0) + float(f.get("tax", 0) or 0)
        if f["side"] == "buy":
            lots[code].append([str(f["date"]), qty, price, cost_extra / qty if qty else 0.0])
            continue
        remaining, cost, bought, entry_date = qty, 0.0, 0, None
        while remaining > 0 and lots[code]:
            lot = lots[code][0]
            take = min(remaining, lot[1])
            entry_date = entry_date or lot[0]
            cost += take * (lot[2] + lot[3])
            bought += take * lot[2]
            lot[1] -= take
            remaining -= take
            if lot[1] == 0:
                lots[code].popleft()
        matched = qty - remaining
        if matched == 0:
            continue  # 기록 시작 전에 산 종목은 짝이 없어 제외
        proceeds = matched * price - cost_extra * matched / qty
        reason = reason_by_order.get(str(f["order_no"])) or reason_by_day.get((code, str(f["date"])), "manual")
        pnl = proceeds - cost
        trades.append(Trade(code, pd.Timestamp(entry_date), pd.Timestamp(f["date"]), matched,
                            bought / matched, price, pnl, pnl / cost if cost else 0.0, reason))
    return trades

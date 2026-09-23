"""키움 REST 클라이언트·운영기 테스트. 실제 서버 대신 공식 명세 형식의 가짜 응답을 쓴다."""
import json
from datetime import date

import pandas as pd
import pytest

from aitrader import data as data_mod
from aitrader.broker import Fill, PaperBroker
from aitrader.config import Config, kr_cost
from aitrader.dashboard import build_live_dashboard
from aitrader.kiwoom import Journal, KiwoomBroker, KiwoomClient, KiwoomError, strip_code, to_num, to_price
from aitrader.kr_live import LiveTrader, previous_trading_day, round_trips
from aitrader.notify import Notifier


class FakeResp:
    def __init__(self, body, headers=None):
        self._body = body
        self.headers = headers or {}
        self.status_code = 200
        self.text = json.dumps(body)

    def json(self):
        return self._body


class FakeSession:
    """api-id 헤더별로 응답을 돌려주고, 받은 요청을 기록한다."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def post(self, url, json=None, headers=None, timeout=None):
        api_id = "au10001" if url.endswith("/oauth2/token") else headers["api-id"]
        self.calls.append((url, api_id, json, headers))
        route = self.routes[api_id]
        return route(json, headers) if callable(route) else FakeResp(route)


TOKEN = {"return_code": 0, "token": "TKN", "token_type": "bearer", "expires_dt": "20991231235959"}


def make_client(routes):
    session = FakeSession({"au10001": TOKEN, **routes})
    return KiwoomClient("k", "s", mock=True, session=session, min_interval=0), session


def test_number_parsing():
    assert to_num("+000000061300") == 61300
    assert to_num("-00000001500") == -1500
    assert to_num("") == 0
    assert to_price("-61300") == 61300  # 부호는 등락 방향
    assert strip_code("A005930") == "005930"
    assert strip_code("005930") == "005930"


def test_order_uses_mock_domain_and_market_order():
    client, session = make_client({"kt10000": {"return_code": 0, "ord_no": "0000123", "dmst_stex_tp": "KRX"}})
    assert client.order("buy", "005930", 3) == "0000123"
    url, api_id, body, headers = session.calls[-1]
    assert url == "https://mockapi.kiwoom.com/api/dostk/ordr"
    assert headers["authorization"] == "Bearer TKN"
    assert body == {"dmst_stex_tp": "KRX", "stk_cd": "005930", "ord_qty": "3", "ord_uv": "", "trde_tp": "3", "cond_uv": ""}


def test_error_code_raises_and_rate_limit_retries(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    attempts = {"n": 0}

    def flaky(body, headers):
        attempts["n"] += 1
        if attempts["n"] == 1:
            return FakeResp({"return_code": 1700, "return_msg": "유량 초과"})
        return FakeResp({"return_code": 0, "cur_prc": "+70000"})

    client, _ = make_client({"ka10001": flaky, "kt10001": {"return_code": 20, "return_msg": "매도가능수량 부족"}})
    assert client.current_price("005930") == 70000
    with pytest.raises(KiwoomError, match="매도가능수량"):
        client.order("sell", "005930", 1)


def test_daily_chart_follows_continuation():
    page1 = {"return_code": 0, "stk_dt_pole_chart_qry": [
        {"dt": "20260922", "open_pric": "100", "high_pric": "110", "low_pric": "95", "cur_prc": "105", "trde_qty": "10"},
        {"dt": "20260921", "open_pric": "98", "high_pric": "101", "low_pric": "97", "cur_prc": "100", "trde_qty": "12"},
    ]}
    page2 = {"return_code": 0, "stk_dt_pole_chart_qry": [
        {"dt": "20260918", "open_pric": "95", "high_pric": "99", "low_pric": "94", "cur_prc": "98", "trde_qty": "9"},
    ]}

    def chart(body, headers):
        if headers.get("cont-yn") == "Y":
            assert headers["next-key"] == "K2"
            return FakeResp(page2)
        return FakeResp(page1, {"cont-yn": "Y", "next-key": "K2"})

    client, _ = make_client({"ka10081": chart})
    df = client.daily_chart("005930", min_rows=3)
    assert list(df.index.strftime("%Y%m%d")) == ["20260918", "20260921", "20260922"]
    assert df["close"].tolist() == [98, 100, 105]


def test_broker_reads_balance_and_sets_stop(tmp_path):
    balance = {
        "return_code": 0, "prsm_dpst_aset_amt": "000000100500000",
        "acnt_evlt_remn_indv_tot": [
            {"stk_cd": "A005930", "stk_nm": "삼성전자", "rmnd_qty": "000000000000010",
             "pur_pric": "000000000070000", "cur_prc": "-000000068000"},
        ],
    }
    client, _ = make_client({"kt00018": balance, "kt00001": {"return_code": 0, "ord_alow_amt": "000000030000000"}})
    journal = Journal(tmp_path / "journal.json")
    journal.set_entry("005930", "2026-09-20")
    journal.set_entry("000660", "2026-09-01")  # 증권사에 없는 종목은 정리돼야 함
    broker = KiwoomBroker(client, journal, stop_loss_pct=0.02)
    assert KiwoomBroker(client, Journal(tmp_path / "j2.json"), 0.02, universe={"000660"}).get_positions() == {}
    pos = broker.get_positions()
    assert pos["005930"].shares == 10
    assert pos["005930"].stop_price == pytest.approx(68600)
    assert pos["005930"].entry_date == "2026-09-20"
    assert "000660" not in journal.data
    assert broker.get_price("005930") == 68000
    assert broker.equity() == 100_500_000
    assert broker.get_cash() == 30_000_000


def test_round_trips_fifo_with_costs():
    fills = pd.DataFrame([
        {"date": "2026-09-01", "time": "090001", "order_no": "1", "code": "005930", "side": "buy", "qty": 10, "price": 100.0, "fee": 1.0, "tax": 0.0},
        {"date": "2026-09-02", "time": "090001", "order_no": "2", "code": "005930", "side": "buy", "qty": 10, "price": 110.0, "fee": 1.0, "tax": 0.0},
        {"date": "2026-09-03", "time": "100000", "order_no": "3", "code": "005930", "side": "sell", "qty": 15, "price": 120.0, "fee": 1.5, "tax": 3.0},
    ])
    orders = pd.DataFrame([{"date": "2026-09-03", "ticker": "005930", "side": "sell", "reason": "exit_signal", "order_no": "3"}])
    [t] = round_trips(fills, orders)
    assert t.shares == 15
    assert t.entry_date == pd.Timestamp("2026-09-01")
    # 매입: 10×100 + 5×110, 매수수수료 주당 0.1 / 매도: 15×120 − 4.5
    cost = 10 * 100.1 + 5 * 110.1
    assert t.pnl == pytest.approx(15 * 120 - 4.5 - cost)
    assert t.reason == "exit_signal"


def test_previous_trading_day_skips_weekend_and_holiday():
    assert previous_trading_day(date(2026, 9, 21)) == date(2026, 9, 18)  # 월 → 금
    assert previous_trading_day(date(2026, 9, 28)) == date(2026, 9, 23)  # 추석 연휴(9/24~9/26) 건너뜀
    assert previous_trading_day(date(2026, 10, 6)) == date(2026, 10, 2)  # 개천절 대체휴일(10/5) 건너뜀


def test_live_trader_cycle_and_report(tmp_path):
    """장 마감 계획 → 다음날 시가 주문 → 손절 감시 → 기록 → 대시보드까지 한 바퀴."""
    all_data = data_mod.synthetic(["111111", "222222", "333333", "444444"], days=700, seed=3)
    cfg = Config(cost=kr_cost())
    cfg.filter.enabled = False
    broker = PaperBroker(100_000_000, cfg.cost)
    msgs = []
    notifier = Notifier(token="", chat_id="")
    notifier.send = msgs.append
    fills_log = []
    view = {"n": 600}

    def load():
        return {t: df.iloc[: view["n"]] for t, df in all_data.items()}

    def fetch_fills():
        return list(fills_log)

    trader = LiveTrader(broker, cfg, load, tmp_path, notifier, bench_price=lambda: 100.0, fetch_fills=fetch_fills)

    planned_total = 0
    for step in range(60):
        cur = load()
        day = max(df.index[-1] for df in cur.values()).date()
        broker.set_prices({t: float(df["close"].iloc[-1]) for t, df in cur.items()})
        trader.close(day)
        pending = json.loads((tmp_path / "pending.json").read_text())
        planned_total += len(pending["orders"])
        # 다음 거래일 시가에 주문
        view["n"] += 1
        nxt = load()
        next_day = max(df.index[-1] for df in nxt.values()).date()
        broker.set_prices({t: float(df["open"].iloc[-1]) for t, df in nxt.items()})
        pending["planned_on"] = str(previous_trading_day(next_day))  # 합성 달력과 휴장일 달력 맞추기
        (tmp_path / "pending.json").write_text(json.dumps(pending))
        fills_log.clear()
        for r in trader.execute(next_day):
            if r["status"] == "sent":
                fills_log.append({"date": str(next_day), "time": "090031", "order_no": str(step) + r["ticker"],
                                  "code": r["ticker"], "side": r["side"], "qty": r["shares"],
                                  "price": r["est_price"], "fee": 0.0, "tax": 0.0})
        trader.monitor_once(next_day)

    assert planned_total > 0
    perf = pd.read_csv(tmp_path / "perf.csv")
    assert len(perf) == 60
    orders = pd.read_csv(tmp_path / "orders.csv")
    assert set(orders["status"]) <= {"sent", "skipped", "error"}
    assert (orders["status"] == "sent").any()
    trips = round_trips(pd.read_csv(tmp_path / "fills.csv", dtype={"code": str, "order_no": str}),
                        pd.read_csv(tmp_path / "orders.csv", dtype={"ticker": str, "order_no": str}))
    assert trips and all(t.reason in {"exit_signal", "max_holding", "stop_loss"} for t in trips)
    out = build_live_dashboard(tmp_path, cfg, tmp_path / "report.html")
    html = out.read_text()
    assert "키움 모의투자" in html and "KODEX 200" in html


def test_execute_skips_stale_orders(tmp_path):
    cfg = Config(cost=kr_cost())
    broker = PaperBroker(1_000_000, cfg.cost)
    msgs = []
    notifier = Notifier(token="", chat_id="")
    notifier.send = msgs.append
    trader = LiveTrader(broker, cfg, lambda: {}, tmp_path, notifier)
    (tmp_path / "pending.json").write_text(json.dumps({"planned_on": "2026-09-10", "orders": [
        {"ticker": "005930", "side": "buy", "shares": 1, "reason": "entry_signal"}]}))
    assert trader.execute(date(2026, 9, 22)) == []
    assert "오래되어" in msgs[-1]
    assert broker.get_positions() == {}


def test_monitor_does_not_resell_same_day(tmp_path):
    cfg = Config(cost=kr_cost())
    broker = PaperBroker(1_000_000, cfg.cost)
    broker.set_prices({"005930": 100.0})
    broker.buy("005930", 10, 0.02, "2026-09-21")
    notifier = Notifier(token="", chat_id="")
    notifier.send = lambda m: None
    trader = LiveTrader(broker, cfg, lambda: {}, tmp_path, notifier)
    sells = []

    def counting_sell(t, n):
        # 체결이 지연되는 상황: 주문은 나갔지만 잔고는 그대로
        sells.append(t)
        return Fill(t, "sell", n, 97.0, 0.0)

    broker.sell = counting_sell
    broker.set_prices({"005930": 97.0})
    assert trader.monitor_once(date(2026, 9, 22)) == ["005930"]
    assert trader.monitor_once(date(2026, 9, 22)) == []
    assert sells == ["005930"]

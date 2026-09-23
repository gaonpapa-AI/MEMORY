"""키움증권 REST API 클라이언트와 Broker 어댑터 (국내주식).

명세 출처: 키움증권 공식 REST API 명세 (github.com/Kiwoom-Securities/Kiwoom-REST-API)
- 토큰: POST /oauth2/token (au10001)
- 주문: POST /api/dostk/ordr  매수 kt10000 / 매도 kt10001
- 계좌: POST /api/dostk/acnt  예수금 kt00001 / 평가잔고 kt00018 / 체결 ka10076
- 시세: POST /api/dostk/stkinfo 기본정보 ka10001, POST /api/dostk/chart 일봉 ka10081

앱키는 KIWOOM_APP_KEY, KIWOOM_APP_SECRET 환경변수에서만 읽는다. 모의투자와 실전투자 키는 서로 다르다.
"""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
import requests

from .broker import Broker, BrokerPosition, Fill

log = logging.getLogger(__name__)

MOCK_URL = "https://mockapi.kiwoom.com"
REAL_URL = "https://api.kiwoom.com"
RATE_LIMIT_CODES = {1700, 1701, 1702}
TOKEN_INVALID_CODES = {8005}


class KiwoomError(RuntimeError):
    def __init__(self, code: int, message: str, api_id: str = ""):
        super().__init__(f"[{api_id}] {code}: {message}")
        self.code = code
        self.message = message


def to_num(value: Any) -> float:
    """'+000000061300', '-1.25', '' 같은 키움 응답 숫자를 float로."""
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", "")
    if text in ("", "+", "-"):
        return 0.0
    return float(text)


def to_price(value: Any) -> float:
    # 현재가 앞의 +/-는 전일 대비 방향 표시일 뿐이라 절대값을 쓴다
    return abs(to_num(value))


def strip_code(code: str) -> str:
    """'A005930' → '005930'."""
    code = str(code).strip()
    return code[1:] if len(code) == 7 and code[0].isalpha() else code


class KiwoomClient:
    def __init__(
        self,
        appkey: str,
        secretkey: str,
        mock: bool = True,
        session: requests.Session | None = None,
        min_interval: float = 0.25,
        timeout: float = 15.0,
    ):
        if not appkey or not secretkey:
            raise ValueError("키움 앱키/시크릿키가 비어 있습니다")
        self.appkey = appkey
        self.secretkey = secretkey
        self.mock = mock
        self.base_url = MOCK_URL if mock else REAL_URL
        self.session = session or requests.Session()
        self.min_interval = min_interval
        self.timeout = timeout
        self._token: str | None = None
        self._token_expires = datetime.min
        self._last_call = 0.0

    @classmethod
    def from_env(cls, mock: bool = True) -> "KiwoomClient":
        key, secret = os.environ.get("KIWOOM_APP_KEY"), os.environ.get("KIWOOM_APP_SECRET")
        if not key or not secret:
            raise SystemExit(
                "KIWOOM_APP_KEY, KIWOOM_APP_SECRET 환경변수를 설정하세요 (모의투자용 키). README의 '키움 모의투자' 참고"
            )
        return cls(key, secret, mock=mock)

    # ---------- 인증 ----------
    def token(self) -> str:
        if self._token and datetime.now() < self._token_expires - timedelta(minutes=10):
            return self._token
        resp = self.session.post(
            f"{self.base_url}/oauth2/token",
            json={"grant_type": "client_credentials", "appkey": self.appkey, "secretkey": self.secretkey},
            headers={"Content-Type": "application/json;charset=UTF-8"},
            timeout=self.timeout,
        )
        data = resp.json()
        if data.get("return_code") not in (None, 0) or not data.get("token"):
            raise KiwoomError(int(data.get("return_code", -1)), str(data.get("return_msg", "토큰 발급 실패")), "au10001")
        self._token = data["token"]
        try:
            self._token_expires = datetime.strptime(str(data["expires_dt"]), "%Y%m%d%H%M%S")
        except (KeyError, ValueError):
            self._token_expires = datetime.now() + timedelta(hours=12)
        return self._token

    # ---------- 공통 요청 ----------
    def request(
        self,
        api_id: str,
        path: str,
        body: dict[str, Any],
        cont_yn: str | None = None,
        next_key: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """응답 body와 연속조회 헤더를 돌려준다. 유량 초과는 잠시 쉬고 재시도, 토큰 만료는 재발급 후 재시도."""
        for attempt in range(4):
            wait = self.min_interval - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            headers = {
                "Content-Type": "application/json;charset=UTF-8",
                "api-id": api_id,
                "authorization": f"Bearer {self.token()}",
            }
            if cont_yn:
                headers["cont-yn"] = cont_yn
            if next_key:
                headers["next-key"] = next_key
            resp = self.session.post(f"{self.base_url}{path}", json=body, headers=headers, timeout=self.timeout)
            self._last_call = time.monotonic()
            try:
                data = resp.json()
            except ValueError:
                raise KiwoomError(resp.status_code, resp.text[:200], api_id) from None
            code = data.get("return_code")
            if code in (None, 0):
                cont = {"cont-yn": resp.headers.get("cont-yn", ""), "next-key": resp.headers.get("next-key", "")}
                return data, cont
            code = int(code)
            if code in RATE_LIMIT_CODES and attempt < 3:
                time.sleep(1.0 + attempt)
                continue
            if code in TOKEN_INVALID_CODES and attempt < 3:
                self._token = None
                continue
            raise KiwoomError(code, str(data.get("return_msg", "")), api_id)
        raise KiwoomError(-1, "재시도 한도 초과", api_id)

    def pages(self, api_id: str, path: str, body: dict[str, Any], max_pages: int = 10) -> Iterator[dict[str, Any]]:
        cont_yn = next_key = None
        for _ in range(max_pages):
            data, cont = self.request(api_id, path, body, cont_yn, next_key)
            yield data
            if cont["cont-yn"] != "Y":
                return
            cont_yn, next_key = "Y", cont["next-key"]

    # ---------- 시세 ----------
    def daily_chart(self, code: str, min_rows: int = 700, max_pages: int = 5) -> pd.DataFrame:
        """수정주가 일봉 (ka10081). 최신 → 과거 순서로 연속조회해 min_rows개 이상 모은다."""
        rows: list[dict[str, Any]] = []
        body = {"stk_cd": code, "base_dt": datetime.now().strftime("%Y%m%d"), "upd_stkpc_tp": "1"}
        for data in self.pages("ka10081", "/api/dostk/chart", body, max_pages=max_pages):
            rows.extend(data.get("stk_dt_pole_chart_qry") or [])
            if len(rows) >= min_rows:
                break
        if not rows:
            raise KiwoomError(-1, f"{code} 일봉 데이터가 없습니다", "ka10081")
        df = pd.DataFrame(
            {
                "open": [to_price(r["open_pric"]) for r in rows],
                "high": [to_price(r["high_pric"]) for r in rows],
                "low": [to_price(r["low_pric"]) for r in rows],
                "close": [to_price(r["cur_prc"]) for r in rows],
                "volume": [abs(to_num(r["trde_qty"])) for r in rows],
            },
            index=pd.to_datetime([r["dt"] for r in rows], format="%Y%m%d"),
        )
        df = df[~df.index.duplicated()].sort_index()
        return df[df["close"] > 0]

    def current_price(self, code: str) -> float:
        data, _ = self.request("ka10001", "/api/dostk/stkinfo", {"stk_cd": code})
        return to_price(data.get("cur_prc"))

    # ---------- 계좌 ----------
    def balance(self) -> dict[str, Any]:
        """계좌평가잔고 (kt00018). 보유종목은 연속조회로 모두 모은다."""
        summary: dict[str, Any] = {}
        holdings: list[dict[str, Any]] = []
        for data in self.pages("kt00018", "/api/dostk/acnt", {"qry_tp": "1", "dmst_stex_tp": "KRX"}):
            if not summary:
                summary = data
            holdings.extend(data.get("acnt_evlt_remn_indv_tot") or [])
        return {"summary": summary, "holdings": holdings}

    def deposit(self) -> dict[str, Any]:
        data, _ = self.request("kt00001", "/api/dostk/acnt", {"qry_tp": "3"})
        return data

    def order(self, side: str, code: str, qty: int) -> str:
        """시장가 주문. 주문번호를 돌려준다."""
        api_id = {"buy": "kt10000", "sell": "kt10001"}[side]
        body = {"dmst_stex_tp": "KRX", "stk_cd": code, "ord_qty": str(int(qty)), "ord_uv": "", "trde_tp": "3", "cond_uv": ""}
        data, _ = self.request(api_id, "/api/dostk/ordr", body)
        return str(data.get("ord_no", ""))

    def today_fills(self) -> list[dict[str, Any]]:
        """당일 체결 내역 (ka10076)."""
        out: list[dict[str, Any]] = []
        body = {"stk_cd": "", "qry_tp": "0", "sell_tp": "0", "ord_no": "", "stex_tp": "1"}
        for data in self.pages("ka10076", "/api/dostk/acnt", body):
            out.extend(data.get("cntr") or [])
        return out


@dataclass
class Holding:
    code: str
    name: str
    shares: int
    avg_price: float
    cur_price: float


class Journal:
    """증권사가 모르는 정보(매수일)를 로컬 JSON에 저장한다."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.data: dict[str, dict[str, Any]] = json.loads(self.path.read_text()) if self.path.exists() else {}

    def get_entry_date(self, code: str) -> str | None:
        return self.data.get(code, {}).get("entry_date")

    def set_entry(self, code: str, entry_date: str) -> None:
        self.data.setdefault(code, {})["entry_date"] = entry_date
        self.save()

    def remove(self, code: str) -> None:
        if self.data.pop(code, None) is not None:
            self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2))


class KiwoomBroker(Broker):
    """키움 계좌를 Broker 인터페이스로 감싼다. 손절가 = 증권사 매입가 × (1 - stop_loss_pct)."""

    def __init__(self, client: KiwoomClient, journal: Journal, stop_loss_pct: float, universe: set[str] | None = None):
        self.client = client
        self.journal = journal
        self.stop_loss_pct = stop_loss_pct
        # 전략 종목만 관리한다. 계좌에 원래 있던 다른 종목은 손절·청산 대상에서 뺀다
        self.universe = set(universe) if universe else None
        self._holdings: dict[str, Holding] = {}
        self._summary: dict[str, Any] = {}

    def refresh(self) -> dict[str, Holding]:
        bal = self.client.balance()
        self._summary = bal["summary"]
        self._holdings = {}
        for h in bal["holdings"]:
            qty = int(to_num(h.get("rmnd_qty")))
            if qty <= 0:
                continue
            code = strip_code(h.get("stk_cd", ""))
            if self.universe is not None and code not in self.universe:
                continue
            self._holdings[code] = Holding(
                code, str(h.get("stk_nm", "")).strip(), qty, to_price(h.get("pur_pric")), to_price(h.get("cur_prc"))
            )
        # 증권사에 없는 종목은 저널에서도 지운다 (손절·수동 매도 등)
        for code in list(self.journal.data):
            if code not in self._holdings:
                self.journal.remove(code)
        return self._holdings

    def holdings(self) -> dict[str, Holding]:
        return self.refresh()

    def get_cash(self) -> float:
        d = self.client.deposit()
        # 주문가능금액이 가장 보수적이다 (미결제 매수대금 반영)
        return to_num(d.get("ord_alow_amt")) or to_num(d.get("d2_entra"))

    def get_positions(self) -> dict[str, BrokerPosition]:
        today = datetime.now().strftime("%Y-%m-%d")
        return {
            code: BrokerPosition(
                h.shares, h.avg_price, h.avg_price * (1 - self.stop_loss_pct), self.journal.get_entry_date(code) or today
            )
            for code, h in self.refresh().items()
        }

    def get_price(self, ticker: str) -> float:
        if ticker in self._holdings and self._holdings[ticker].cur_price > 0:
            return self._holdings[ticker].cur_price
        return self.client.current_price(ticker)

    def equity(self) -> float:
        if not self._summary:
            self.refresh()
        return to_num(self._summary.get("prsm_dpst_aset_amt"))

    def buy(self, ticker: str, shares: int, stop_price_pct: float, date: str) -> Fill | None:
        if shares <= 0:
            return None
        price = self.get_price(ticker)
        ord_no = self.client.order("buy", ticker, shares)
        self.journal.set_entry(ticker, date)
        return Fill(ticker, "buy", shares, price, 0.0, ord_no)

    def sell(self, ticker: str, shares: int) -> Fill | None:
        if shares <= 0:
            return None
        price = self.get_price(ticker)
        ord_no = self.client.order("sell", ticker, shares)
        return Fill(ticker, "sell", shares, price, 0.0, ord_no)

"""시세 데이터 수집.

모든 함수는 {티커: DataFrame} 형태를 돌려준다.
DataFrame은 DatetimeIndex와 소문자 컬럼 open, high, low, close, volume을 가진다.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

COLUMNS = ["open", "high", "low", "close", "volume"]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        # yfinance는 (Price, Ticker) 2단 컬럼을 돌려준다
        df = df.copy()
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)
    df = df[COLUMNS].dropna()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df.sort_index()


def load_yfinance(
    tickers: list[str],
    start: str,
    end: str | None = None,
    cache_dir: str | Path | None = "data_cache",
) -> dict[str, pd.DataFrame]:
    """야후 파이낸스에서 수정주가(배당·분할 반영) 일봉을 받는다. cache_dir가 있으면 CSV로 캐시."""
    import yfinance as yf

    out: dict[str, pd.DataFrame] = {}
    cache = Path(cache_dir) if cache_dir else None
    if cache:
        cache.mkdir(parents=True, exist_ok=True)
    for t in tickers:
        path = cache / f"{t}_{start}_{end or 'latest'}.csv" if cache else None
        if path and path.exists() and end is not None:
            out[t] = pd.read_csv(path, index_col=0, parse_dates=True)
            continue
        raw = yf.download(t, start=start, end=end, auto_adjust=True, progress=False)
        if raw.empty:
            raise RuntimeError(f"{t}: 데이터를 받지 못했습니다 (티커나 네트워크를 확인하세요)")
        df = _normalize(raw)
        if path:
            df.to_csv(path)
        out[t] = df
    return out


def load_csv_dir(directory: str | Path) -> dict[str, pd.DataFrame]:
    """<티커>.csv 파일들을 읽는다. 컬럼명은 대소문자 무관(Date, Open, High, Low, Close, Volume)."""
    out = {}
    for path in sorted(Path(directory).glob("*.csv")):
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        out[path.stem.upper()] = _normalize(df)
    return out


def synthetic(
    tickers: list[str],
    days: int = 1500,
    seed: int = 7,
    start: str = "2019-01-02",
) -> dict[str, pd.DataFrame]:
    """오프라인 테스트·데모용 합성 일봉. 추세 구간이 바뀌는 랜덤워크로 만든다."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range(start, periods=days)
    out = {}
    for t in tickers:
        # 60일마다 드리프트가 바뀌는 국면(regime) 전환 랜덤워크
        regimes = rng.normal(0.0004, 0.0015, size=days // 60 + 1)
        drift = np.repeat(regimes, 60)[:days]
        vol = rng.uniform(0.012, 0.025)
        rets = drift + rng.normal(0, vol, size=days)
        close = 100 * np.exp(np.cumsum(rets))
        gap = rng.normal(0, vol / 3, size=days)
        open_ = np.r_[close[0], close[:-1]] * np.exp(gap)
        spread = np.abs(rng.normal(0, vol / 2, size=days))
        high = np.maximum(open_, close) * (1 + spread)
        low = np.minimum(open_, close) * (1 - spread)
        volume = rng.integers(1_000_000, 5_000_000, size=days) * (1 + np.abs(rets) * 20)
        out[t] = pd.DataFrame(
            {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
            index=dates,
        )
    return out


def load_krx(codes: list[str], start: str, end: str | None = None) -> dict[str, pd.DataFrame]:
    """국내주식 일봉 (FinanceDataReader). 키움 API 키 없이 백테스트할 때 쓴다."""
    import FinanceDataReader as fdr

    out = {}
    for code in codes:
        raw = fdr.DataReader(code, start, end)
        if raw.empty:
            raise RuntimeError(f"{code}: 데이터를 받지 못했습니다")
        out[code] = _normalize(raw)
    return out

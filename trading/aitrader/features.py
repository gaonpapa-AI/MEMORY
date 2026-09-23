"""기술적 지표와 머신러닝 피처.

모든 값은 해당 날짜 종가까지의 정보만으로 계산한다(미래 정보 누수 없음).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100.0).where(loss.notna())


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev_close = df["close"].shift()
    tr = pd.concat(
        [df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


FEATURE_COLUMNS = [
    "ret_1",
    "ret_5",
    "ret_20",
    "rsi_14",
    "atr_pct",
    "vol_20",
    "dist_sma20",
    "dist_sma50",
    "volume_ratio",
    "high_dist_20",
]


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    c = df["close"]
    f = pd.DataFrame(index=df.index)
    f["ret_1"] = c.pct_change()
    f["ret_5"] = c.pct_change(5)
    f["ret_20"] = c.pct_change(20)
    f["rsi_14"] = rsi(c, 14) / 100
    f["atr_pct"] = atr(df, 14) / c
    f["vol_20"] = f["ret_1"].rolling(20).std()
    f["dist_sma20"] = c / sma(c, 20) - 1
    f["dist_sma50"] = c / sma(c, 50) - 1
    f["volume_ratio"] = df["volume"] / df["volume"].rolling(20).mean()
    f["high_dist_20"] = c / c.rolling(20).max() - 1
    return f[FEATURE_COLUMNS]


def make_label(df: pd.DataFrame, horizon: int) -> pd.Series:
    """horizon 거래일 뒤 종가가 오늘 종가보다 높으면 1. 마지막 horizon일은 NaN."""
    fwd = df["close"].shift(-horizon) / df["close"] - 1
    return (fwd > 0).astype(float).where(fwd.notna())

"""규칙 기반 퀀트 전략: 추세 추종 돌파.

- 진입: 종가 > trend_sma 이동평균 (상승 추세)  AND  종가가 최근 breakout_lookback일 최고 종가 경신
- 청산: 종가 < exit_sma 이동평균

신호는 당일 종가 기준으로 계산하고, 주문은 다음 거래일 시가에 체결된다고 가정한다.
"""
from __future__ import annotations

import pandas as pd

from .config import StrategyConfig
from .features import sma


def generate_signals(df: pd.DataFrame, cfg: StrategyConfig) -> pd.DataFrame:
    c = df["close"]
    trend_ok = c > sma(c, cfg.trend_sma)
    # 전일까지의 최고 종가를 오늘 종가가 넘었는지
    prior_high = c.shift(1).rolling(cfg.breakout_lookback).max()
    breakout = c > prior_high
    exit_ = c < sma(c, cfg.exit_sma)
    return pd.DataFrame({"entry": trend_ok & breakout, "exit": exit_}, index=df.index)

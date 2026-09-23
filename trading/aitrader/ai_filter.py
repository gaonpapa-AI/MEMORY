"""AI 리스크 필터: 전략 진입 신호를 머신러닝 확률로 걸러낸다.

모델은 "horizon 거래일 뒤 종가가 오늘보다 높을 확률"을 예측하고, 이 확률이 min_prob 미만인
진입 신호는 버린다. 과적합과 미래 정보 누수를 막기 위해 워크포워드(walk-forward) 방식으로만 학습한다:
어떤 날짜 d의 예측에는 d 종가 시점에 이미 결과가 확정된 과거 표본만 사용한다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from .config import FilterConfig
from .features import FEATURE_COLUMNS, make_features, make_label


def make_model() -> HistGradientBoostingClassifier:
    # 얕은 트리 + 규제로 복잡도를 낮게 유지 (금융 데이터는 잡음이 커서 과적합되기 쉽다)
    return HistGradientBoostingClassifier(
        max_depth=3,
        learning_rate=0.05,
        max_iter=150,
        l2_regularization=1.0,
        min_samples_leaf=50,
        random_state=0,
    )


def build_panel(data: dict[str, pd.DataFrame], horizon: int) -> pd.DataFrame:
    frames = []
    for ticker, df in data.items():
        f = make_features(df)
        f["label"] = make_label(df, horizon)
        # 라벨의 정답이 확정되는 날짜 (horizon 거래일 뒤 종가)
        f["label_date"] = pd.Series(df.index, index=df.index).shift(-horizon)
        f["ticker"] = ticker
        frames.append(f)
    panel = pd.concat(frames)
    panel.index.name = "date"
    return panel.dropna(subset=FEATURE_COLUMNS)


def _fit(train: pd.DataFrame, cfg: FilterConfig) -> HistGradientBoostingClassifier | None:
    train = train.dropna(subset=["label"])
    if len(train) < cfg.min_train_samples or train["label"].nunique() < 2:
        return None
    model = make_model()
    model.fit(train[FEATURE_COLUMNS].to_numpy(), train["label"].to_numpy())
    return model


def walk_forward_proba(data: dict[str, pd.DataFrame], cfg: FilterConfig) -> pd.DataFrame:
    """날짜 × 티커 상승 확률표. 학습 표본이 부족한 초기 구간은 NaN."""
    panel = build_panel(data, cfg.horizon)
    dates = panel.index.unique().sort_values()
    probs = pd.DataFrame(np.nan, index=dates, columns=list(data))

    for i in range(0, len(dates), cfg.retrain_every):
        d = dates[i]
        window_start = dates[max(0, i - cfg.train_window)]
        train = panel[(panel.index >= window_start) & (panel["label_date"] <= d)]
        model = _fit(train, cfg)
        if model is None:
            continue
        block = dates[i : i + cfg.retrain_every]
        test = panel[panel.index.isin(block)]
        p = model.predict_proba(test[FEATURE_COLUMNS].to_numpy())[:, 1]
        for (date, ticker), prob in zip(zip(test.index, test["ticker"]), p):
            probs.at[date, ticker] = prob
    return probs


def predict_latest(data: dict[str, pd.DataFrame], cfg: FilterConfig) -> pd.Series:
    """실거래용: 최근 train_window 구간으로 학습한 뒤 각 티커의 마지막 날짜 확률을 돌려준다."""
    panel = build_panel(data, cfg.horizon)
    dates = panel.index.unique().sort_values()
    last = dates[-1]
    window_start = dates[max(0, len(dates) - 1 - cfg.train_window)]
    train = panel[(panel.index >= window_start) & (panel["label_date"] <= last)]
    model = _fit(train, cfg)
    latest = panel[panel.index == last]
    if model is None:
        return pd.Series(np.nan, index=latest["ticker"])
    p = model.predict_proba(latest[FEATURE_COLUMNS].to_numpy())[:, 1]
    return pd.Series(p, index=latest["ticker"])

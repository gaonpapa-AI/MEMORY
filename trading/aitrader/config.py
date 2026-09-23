"""전략·리스크·비용 설정값.

모든 비율은 소수(0.02 = 2%)로 표기한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CostConfig:
    # 국내 증권사 미국주식 온라인 수수료는 보통 0.07~0.25% 수준. 보수적으로 0.25%.
    commission_rate: float = 0.0025
    # 미국 SEC 수수료(매도 시에만 부과). 실제 요율은 주기적으로 바뀌므로 확인 필요.
    sec_fee_rate: float = 0.0000278
    # 호가 공백·시장가 체결로 인한 슬리피지 (basis point, 1bp = 0.01%)
    slippage_bps: float = 5.0


@dataclass
class RiskConfig:
    # 진입가 대비 이 비율만큼 하락하면 무조건 기계적 손절
    stop_loss_pct: float = 0.02
    # 1회 거래에서 감수할 계좌 대비 최대 손실 (손절 폭과 함께 포지션 크기를 결정)
    risk_per_trade: float = 0.005
    # 한 종목에 투입할 수 있는 계좌 대비 최대 비중
    max_position_pct: float = 0.20
    max_positions: int = 5
    # 하루 계좌 손실이 이 비율을 넘으면 다음 거래일 신규 진입 중단
    daily_loss_limit_pct: float = 0.03
    # 이 기간 동안 보유하면 전략 신호와 무관하게 청산
    max_holding_days: int = 20


@dataclass
class StrategyConfig:
    # 추세 필터: 종가 > 장기 이동평균
    trend_sma: int = 50
    # 돌파: 종가가 최근 N일 최고 종가를 경신
    breakout_lookback: int = 20
    # 청산: 종가 < 단기 이동평균
    exit_sma: int = 10


@dataclass
class FilterConfig:
    enabled: bool = True
    # 예측 대상: horizon 거래일 뒤 종가가 오늘 종가보다 높을 확률
    horizon: int = 5
    # 이 확률 이상일 때만 진입 허용
    min_prob: float = 0.55
    # 워크포워드 학습: 최근 train_window 거래일 데이터로 retrain_every 거래일마다 재학습
    train_window: int = 504
    retrain_every: int = 21
    min_train_samples: int = 300


@dataclass
class Config:
    initial_cash: float = 100_000.0
    cost: CostConfig = field(default_factory=CostConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    strategy: StrategyConfig = field(default_factory=StrategyConfig)
    filter: FilterConfig = field(default_factory=FilterConfig)

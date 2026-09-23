# aitrader — 미국주식 퀀트 전략 + AI 리스크 필터

규칙 기반 추세추종 전략이 매수 후보를 만들고, 머신러닝 모델이 그중 "상승 확률이 낮은" 신호를 걸러내는
자동매매 프레임워크입니다. AI 판단과 별개로 **-2% 기계적 손절** 같은 하드코딩된 리스크 규칙이 항상 적용됩니다.

## 구조

```
데이터(yfinance/CSV) → 전략 신호 → AI 필터(확률 ≥ 0.55) → 리스크(손절·비중·일일손실한도) → 브로커(모의/실거래)
                                                                                       ↓
                                                                               텔레그램 알림
```

| 파일 | 역할 |
|---|---|
| `aitrader/config.py` | 비용·리스크·전략·필터 설정값 |
| `aitrader/data.py` | yfinance 수정주가 수집(CSV 캐시), CSV 폴더 로드, 오프라인 합성 데이터 |
| `aitrader/features.py` | RSI·ATR·이평 괴리·거래량비 등 ML 피처 |
| `aitrader/strategy.py` | 진입: 종가 > 50일선 & 20일 신고가 돌파 / 청산: 종가 < 10일선 |
| `aitrader/ai_filter.py` | 워크포워드 학습 GradientBoosting 분류기 (5거래일 뒤 상승 확률) |
| `aitrader/risk.py` | 손절가, 위험 기반 포지션 크기, 일일 손실 한도 |
| `aitrader/backtest.py` | 일봉 이벤트 백테스터 (익일 시가 체결, 갭하락 손절, 수수료·SEC 수수료·슬리피지) |
| `aitrader/broker.py` | `Broker` 인터페이스 + `PaperBroker`(JSON 상태 저장 모의계좌) |
| `aitrader/live.py` | `run_daily`(장 마감 후 1회), `check_stops`(장중 손절 감시) |
| `aitrader/notify.py` | 텔레그램 알림 |
| `aitrader/kiwoom.py` | 키움 REST API 클라이언트(토큰·주문·잔고·체결·일봉)와 `KiwoomBroker` |
| `aitrader/kr_live.py` | 국내주식 운영기: 장 시작 주문, 장중 손절 감시, 장 마감 기록·계획, 성과 집계 |
| `aitrader/dashboard.py` | 백테스트 결과 → 단일 HTML 대시보드 (누적수익·낙폭·청산사유·월별수익·거래내역) |

## 설치

```bash
cd trading
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 사용법

```bash
# 백테스트: AI 필터 적용 vs 전략 단독 비교
python -m aitrader backtest --tickers AAPL MSFT NVDA AMZN GOOGL META --start 2018-01-01 --compare --out reports

# 네트워크 없이 합성 데이터로 동작 확인
python -m aitrader backtest --synthetic --compare

# 옵션
#   --stop-loss 0.03   손절폭 변경 (기본 0.02)
#   --min-prob 0.6     AI 필터 기준 확률
#   --no-filter        AI 필터 끄기

# 결과 대시보드 (HTML 한 파일, 브라우저로 열기)
python -m aitrader dashboard --tickers AAPL MSFT NVDA AMZN GOOGL META --out reports/dashboard.html

# 모의투자 1일 실행 (미국장 마감 후, 상태는 paper_state.json에 누적)
python -m aitrader paper --tickers AAPL MSFT NVDA

# 테스트
pytest
```

텔레그램 알림을 받으려면 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` 환경변수를 설정하세요.

## 설계상 주의점

- **미래 정보 누수 방지**: 신호는 당일 종가로 계산하고 다음날 시가에 체결합니다. AI 모델은 예측 시점에
  정답이 이미 확정된 과거 표본으로만 학습합니다(`tests/test_core.py`에서 데이터를 잘라도 과거 예측이
  바뀌지 않는지 검증).
- **과적합 억제**: 얕은 트리·강한 규제·21거래일마다 재학습. 파라미터를 백테스트 결과에 맞춰 여러 번
  조정하면 그 자체가 과적합이므로, 조정은 학습 기간에서만 하고 마지막 1~2년은 검증용으로 남겨 두세요.
- **-2% 손절**: 미국 대형주의 하루 변동폭이 1.5~2%라 일봉 전략에서는 손절이 자주 걸립니다. `--stop-loss`로
  2%/3%/ATR 기반 등을 비교해 보세요.
- **수수료**: 기본값은 0.25%(국내 증권사 미국주식 기준 보수적)입니다. 환전 수수료·양도소득세(연 250만원
  공제 후 22%)는 백테스트에 반영되지 않았습니다.
- **생존 편향**: 현재 대형주 목록으로 과거를 테스트하면 성과가 부풀려집니다.

## 키움 모의투자 (국내주식)

키움 REST API 모의투자 서버(`mockapi.kiwoom.com`)에 실제 주문을 내고, 매일 성과를 기록합니다.
코드는 모의투자 서버에만 접속하도록 고정되어 있습니다.

### 준비

1. 키움증권 홈페이지 > 모의투자 > **상시모의투자 신청**
2. [키움 REST API 포털](https://openapi.kiwoom.com)에서 API 사용 신청 후 **모의투자용 App Key / Secret Key 발급**
   (실전투자 키와 다릅니다)
3. 키를 환경변수로 설정 (코드·채팅·깃에 붙여넣지 마세요)

```powershell
# Windows PowerShell (영구 설정)
setx KIWOOM_APP_KEY "발급받은_앱키"
setx KIWOOM_APP_SECRET "발급받은_시크릿키"
```
```bash
# macOS / Linux
export KIWOOM_APP_KEY="발급받은_앱키"
export KIWOOM_APP_SECRET="발급받은_시크릿키"
```

### 실행

```bash
pip install -r requirements.txt

# 1) 접속·잔고·일봉 조회 확인 (주문 없음)
python -m aitrader kiwoom check

# 2) (선택) 국내주식 백테스트로 기대치 먼저 보기
python -m aitrader dashboard --market kr --out reports/kr_backtest.html

# 3) 자동 운영: 켜 두면 매 거래일 아래를 반복합니다. PC가 켜져 있어야 합니다
python -m aitrader kiwoom run

# 4) 언제든 성과 확인
python -m aitrader kiwoom report      # → reports/kiwoom_mock.html
```

| 시각 (KST) | 하는 일 |
|---|---|
| 09:00:30 | 전날 계획한 주문을 **시장가**로 제출 (백테스트의 "다음날 시가 체결"과 같은 시점) |
| 09:01 ~ 15:19 | 1분마다 보유 종목 현재가 확인, **매입가 대비 −2% 이하면 즉시 매도** |
| 15:40 | 당일 체결내역·추정예탁자산·KODEX 200 종가 기록 → 다음날 주문 계획 → 텔레그램 요약 |

- 주말·공휴일·12/31은 쉬고, 오늘 일봉이 없으면 휴장으로 보고 건너뜁니다.
- 프로그램을 며칠 꺼 두었다면 묵은 주문은 내지 않고 다시 계획부터 시작합니다.
- 종목은 기본으로 시가총액 상위 20개(`kr_live.KR_UNIVERSE`)이며 `--tickers 005930 000660 ...`으로 바꿀 수 있습니다.
- 기록은 `kiwoom_mock/` 폴더에 쌓입니다: `perf.csv`(일별 자산), `fills.csv`(실제 체결),
  `orders.csv`(주문·사유), `plans.csv`(신호·필터 통계), `journal.json`(매수일).
- 수동 실행도 가능합니다: `kiwoom close`(기록+계획), `kiwoom execute`(주문), `kiwoom monitor`(손절 점검 1회).

### 한계

- 손절은 1분 간격 감시라 급락 시 −2%보다 더 밀려서 체결될 수 있습니다.
- 모의투자 체결은 실제 시장과 다를 수 있습니다(호가 잔량 무시 등). 수익률은 참고용입니다.
- 이 코드는 공식 명세와 가짜 응답으로만 테스트했습니다. 처음 `kiwoom check`에서 오류가 나면 메시지를 그대로 알려 주세요.

## 실계좌 연동 (다음 단계)

`Broker`를 상속해 `get_cash / get_positions / get_price / buy / sell`만 구현하면 `run_daily`,
`check_stops`를 그대로 쓸 수 있습니다.

> 키움증권은 Windows 전용 Open API+ 외에 OS 무관 **REST API**를 제공하며, 공식 예제에 국내주식과 미국주식
> 주문이 모두 있습니다. 이 프로젝트는 국내주식 모의투자(`aitrader/kiwoom.py`)를 구현했고, 미국주식 모의투자
> 지원 여부는 키움에 확인이 필요합니다.

실계좌 전에 최소 수주~수개월간 `paper` 모드로 검증하는 것을 권장합니다.

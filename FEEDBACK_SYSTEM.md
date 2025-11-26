# 실시간 트레이딩 결과 추적 시스템

## 개요

Manager가 추천한 트레이딩 결정이 실제로 어떤 결과를 가져왔는지 추적하고, 이를 학습 데이터로 활용하는 시스템입니다.

## 문제 정의

기존 시스템의 한계:
- Simulation 실행 시 Manager Report 저장 ✅
- **1주일 후 실제 수익률 저장 ❌**

백테스트는 과거 데이터를 모두 가지고 있어서 즉시 결과 확인이 가능하지만, 실시간 트레이딩은 미래 데이터가 없어 **나중에 다시 확인**해야 합니다.

## 해결 방법

### 1. 시뮬레이션 실행 시 (현재)

```
2025-11-26: 트레이딩 요청
  ↓
Manager Report 생성
  - 리스크: ["뉴스 악재", "섹터 약세"]
  - 전략: "소액 매수, 손절 -5%"
  - 진입가: $150
  ↓
피드백 스케줄 등록 ⭐ (NEW!)
  - check_date: 2025-12-03 (7일 후)
  - is_checked: False
```

### 2. N일 후 (미래)

```
2025-12-03: 크론잡 실행
  ↓
/api/feedback/check 호출
  ↓
체크 날짜 지난 피드백 조회
  ↓
각 종목의 현재 가격 조회
  ↓
실제 수익률 계산
  - 진입가: $150
  - 현재가: $162
  - 수익률: +8%
  ↓
DB 업데이트 + 메모리 저장
  - actual_price: $162
  - actual_return: 0.08
  - is_checked: True
  - salience: 0.8 (중요도)
```

## 구현 내용

### 1. DB 모델 ([models.py:58-80](db/models.py#L58-L80))

```python
class SimulationFeedback(Base):
    __tablename__ = "simulation_feedbacks"

    simulation_id: str  # 원본 시뮬레이션 ID
    ticker: str

    # 의사결정 시점 정보
    decision_date: datetime
    entry_price: float
    decision: str
    report: str

    # 추적 기간
    check_date: datetime  # N일 후

    # 실제 결과 (나중에 업데이트)
    actual_price: float | None
    actual_return: float | None
    is_checked: bool = False
```

### 2. 피드백 서비스 ([feedback.py](services/feedback.py))

**주요 메서드:**
- `schedule_feedback()`: 시뮬레이션 후 피드백 스케줄 등록
- `check_pending_feedbacks()`: 체크 날짜 지난 피드백들 확인 및 업데이트
- `get_feedback_stats()`: 피드백 통계 조회 (승률, 평균 수익률 등)

**Salience 계산:**
```python
# 수익률 절댓값 기반 (좋은/나쁜 결과 모두 중요)
salience = abs(actual_return) * 10

# 예시:
# +8% 수익 → salience = 0.8
# -15% 손실 → salience = 1.5 (더 중요!)
```

### 3. API 엔드포인트 ([feedback.py](routers/feedback.py))

**POST /api/feedback/check**
- 체크 날짜 지난 피드백들 확인 및 결과 업데이트
- 크론잡으로 주기적으로 호출
- Response: `{"status": "ok", "checked_count": 5}`

**GET /api/feedback/stats?ticker=AAPL**
- 피드백 통계 조회
- ticker 생략 시 전체 통계
- Response:
```json
{
  "total": 42,
  "avg_return": 0.035,
  "win_rate": 0.62,
  "best_return": 0.25,
  "worst_return": -0.18
}
```

### 4. 통합 ([simulation.py:144-145](services/simulation.py#L144-L145))

```python
async def run_on_snapshot(...):
    # ... 기존 시뮬레이션 로직 ...

    # ⭐ 피드백 스케줄 등록 (NEW!)
    await self.feedback_service.schedule_feedback(sim_id, ticker, summary)

    return result
```

## 사용 방법

### 1. 실시간 트레이딩 실행

```bash
curl -X POST http://localhost:8000/api/run \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "AAPL",
    "window": 200,
    "news": true
  }'

# Response:
# {
#   "simulation_id": "abc-123",
#   "status": "completed",
#   "summary": {
#     "decision": "LONG",
#     "report": "소액 매수, 손절 -5%",
#     ...
#   }
# }
```

→ 자동으로 7일 후 체크 스케줄 등록됨

### 2. 크론잡 설정 (매일 실행)

```bash
# crontab -e
0 9 * * * curl -X POST http://localhost:8000/api/feedback/check
```

또는 수동 실행:
```bash
curl -X POST http://localhost:8000/api/feedback/check

# Response:
# {"status": "ok", "checked_count": 3}
```

### 3. 통계 확인

```bash
# 전체 통계
curl http://localhost:8000/api/feedback/stats

# 특정 종목 통계
curl http://localhost:8000/api/feedback/stats?ticker=AAPL
```

## 설정

`.env` 파일:
```bash
# 피드백 체크 기간 (기본: 7일)
FEEDBACK_CHECK_DAYS=7
```

## 데이터 흐름

```
┌─────────────────────┐
│ 사용자 요청         │
│ "AAPL 분석해줘"     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Simulation 실행     │
│ - Bull/Bear 토론    │
│ - Trader 결정       │
│ - Manager 리포트    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ DB에 저장           │
│ 1. Simulation       │
│ 2. AgentLog         │
│ 3. SimulationFeedback ⭐ (NEW!)
│    - check_date: 7일 후
│    - is_checked: False
└──────────┬──────────┘
           │
           │ ... 7일 경과 ...
           │
           ▼
┌─────────────────────┐
│ 크론잡 실행         │
│ POST /feedback/check│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 현재 가격 조회      │
│ - Entry: $150       │
│ - Current: $162     │
│ - Return: +8%       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 결과 저장           │
│ 1. DB 업데이트      │
│    - actual_return: 0.08
│    - is_checked: True
│                     │
│ 2. 메모리 저장 ⭐   │
│    - role: feedback │
│    - salience: 0.8  │
│    - 학습 데이터로 활용
└─────────────────────┘
```

## 메모리 활용

저장된 피드백은 다음 시뮬레이션에서 자동으로 활용됩니다:

```python
# 다음 시뮬레이션 실행 시
ltm_memories = await memory.search(f"{ticker} market", k=3)

# 반환 예시:
# [
#   {
#     "content": "[Past Decision Feedback]\n"
#                "Ticker: AAPL\n"
#                "Decision: LONG\n"
#                "Actual Return: +8%\n...",
#     "metadata": {
#       "role": "feedback",
#       "salience": 0.8  # 높은 중요도
#     }
#   },
#   ...
# ]
```

→ Manager가 과거 결과를 참고하여 더 나은 결정을 내림!

## 테스트

```bash
# 단위 테스트 실행
python -m pytest tests/test_feedback.py -v

# 커버리지:
# - Salience 계산 로직
# - 수익률 계산 로직
```

## 향후 개선 사항

1. **자동 리밸런싱**
   - 좋은 결과가 나온 전략의 가중치 증가
   - 나쁜 결과가 나온 전략 학습 및 개선

2. **A/B 테스트**
   - 다양한 전략 동시 실행
   - 실제 결과 비교 후 최적 전략 선택

3. **알림 시스템**
   - 큰 손실(-10% 이상) 발생 시 알림
   - 예상과 크게 다른 결과 발생 시 알림

4. **대시보드**
   - 시간대별 승률 추이
   - 종목별 성과 분석
   - 전략별 수익률 비교

## 요약

**Before:**
```
실시간 트레이딩 → Manager Report → 저장 (끝)
                                   ❌ 결과 추적 없음
```

**After:**
```
실시간 트레이딩 → Manager Report → 저장
                                   ↓
                            피드백 스케줄 등록
                                   ↓
                            (7일 후)
                                   ↓
                            실제 결과 확인
                                   ↓
                            메모리에 저장
                                   ↓
                            다음 결정에 활용 ✅
```

이제 AI가 **자신의 과거 결정을 학습**할 수 있습니다!

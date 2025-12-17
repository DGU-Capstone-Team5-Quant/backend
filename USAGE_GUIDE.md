# Quant CLI 사용 가이드

## 📺 인터랙티브 CLI

### 시작하기

```bash
python quant.py
```

### 메인 메뉴

```
무엇을 하시겠습니까?

  📊 백테스팅 (Backtesting)
  🚀 실시간 거래 (Live Trading)
  🧠 메모리 관리 (Memory Management)
  📈 대시보드 (Dashboard)
  ❌ 종료 (Exit)
```

## 📊 백테스팅

### 1. 빠른 백테스트 (Quick Start)

**가장 쉬운 방법!** 티커만 입력하면 즉시 실행됩니다

- 기본 기간: 최근 6개월
- 기본 설정: 메모리 학습 ON
- 실행 시간: 약 5-10분

### 2. 커스텀 백테스트 (Custom Setup)

모든 설정을 직접 제어합니다.

**설정 항목:**
- 티커 (예: AAPL, TSLA, NVDA)
- 시작/종료 날짜
- 랜덤 시드 (재현성)
- 메모리 학습 ON/OFF

### 3. 과거 결과 조회 (View Results)

최근 실행한 백테스트 결과를 조회합니다.

**표시 정보:**
- 총 수익률 (Total Return)
- 최종 잔고 (Final Balance)
- 승률 (Win Rate)
- 샤프 비율 (Sharpe Ratio)
- 최대 낙폭 (Max Drawdown)
- 최근 거래 내역

## 🧠 메모리 관리

### 1. 메모리 통계 조회

현재 Redis 메모리 상태를 확인합니다.

**표시 정보:**
- Redis 버전
- 전체 키 개수
- 메모리 관련 키 개수
- 사용 메모리 / 피크 메모리

### 2. 메모리 초기화

**주의:** 모든 학습된 메모리가 삭제됩니다!

**사용 시기:**
- 새로운 실험 시작 전
- 메모리가 오염되었을 때
- 깨끗한 상태로 재시작

### 3. 메모리 내보내기

현재 메모리를 JSON 파일로 저장합니다.

**용도:**
- 메모리 백업
- 분석 및 디버깅
- 다른 시스템으로 이전

## 📈 대시보드

시스템 전체 상태를 한눈에 확인합니다.

**표시 정보:**

1. **시스템 상태**
   - Ollama (LLM) 연결 상태
   - Redis (Memory) 연결 상태

2. **메모리 상태**
   - 전체 키 개수
   - 메모리 키 개수
   - 사용 메모리
   - 피크 메모리

3. **최근 백테스트 결과**
   - 날짜/시간
   - 티커
   - 수익률
   - 승률

## 💡 사용 팁

### 첫 백테스트

1. `python quant.py` 실행
2. "백테스팅" 선택
3. "빠른 백테스트" 선택
4. 티커 입력 (예: AAPL)
5. 완료 후 결과 확인!

### 메모리 효과 비교하기

```bash
# 1. 메모리 없이 실행
python quant.py
→ 백테스팅 → 커스텀 → 메모리 학습 OFF

# 2. 메모리 초기화
python quant.py
→ 메모리 관리 → 메모리 초기화

# 3. 메모리로 실행
python quant.py
→ 백테스팅 → 커스텀 → 메모리 학습 ON

# 4. 결과 비교
python quant.py
→ 백테스팅 → 과거 결과 조회
```

### 키보드 단축키

- **방향키 (↑↓)**: 메뉴 이동
- **Enter**: 선택
- **Ctrl+C**: 취소 / 이전 메뉴

## 🔧 문제 해결

### "Ollama 연결 실패"

```bash
# Ollama 실행 확인
ollama list

# Ollama 시작
ollama serve
```

### "Redis 연결 실패"

```bash
# Docker로 Redis 시작
docker run -d -p 6379:6379 redis:latest
```

### CLI가 멈춤

- **Ctrl+C** 눌러서 취소
- 다시 `python quant.py` 실행

## 📸 스크린샷

```
===============================================================

   EEEEEE  III  N   N  M   M  EEEEEE  M   M
   E        I   NN  N  MM MM  E       MM MM
   EEEE     I   N N N  M M M  EEEE    M M M
   E        I   N  NN  M   M  E       M   M
   EEEEEE  III  N   N  M   M  EEEEEE  M   M

        Memory-Based Multi-Agent Trading System

===============================================================

┌─────────────── 시스템 상태 체크 ───────────────┐
│ 컴포넌트            │ 상태          │ 세부정보  │
├─────────────────────┼───────────────┼───────────┤
│ Ollama (LLM)        │ ✓ 연결됨      │ 준비 완료 │
│ Redis (Memory)      │ ✓ 연결됨      │ 준비 완료 │
└─────────────────────┴───────────────┴───────────┘

✓ 시스템 준비 완료!
```

## 🚀 고급 사용법

### 명령줄에서 직접 실행

CLI 대신 스크립트로 직접 실행:

```bash
# 백테스트
python scripts/run_backtest.py --ticker AAPL --seed 42

# 메모리 초기화
python scripts/reset_memory.py --all --yes

# 메모리 확인
python scripts/check_memory.py
```

### 배치 실험

여러 티커를 자동으로 실행:

```bash
# PowerShell
$tickers = @("AAPL", "TSLA", "NVDA", "MSFT")
foreach ($ticker in $tickers) {
    python scripts/run_backtest.py --ticker $ticker --seed 42
}
```

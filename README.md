# FinMem Trading System

메모리 기반 멀티 에이전트 트레이딩 시스템

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# uv 설치: https://astral.sh/uv
# 가상환경 생성 및 의존성 설치
uv venv .venv
uv sync

# Ollama 설치 (Windows)
winget install Ollama.Ollama

# 모델 다운로드
ollama pull llama3.1:8b
```

### 2. 환경 변수 설정 (.env)

**최소 설정 (로컬 테스트):**
```bash
# .env 파일 없어도 됨! (기본값으로 작동)
```

**실제 주가 데이터 사용 시:**
```bash
RAPID_API_KEY=your_key
RAPID_API_HOST=twelve-data1.p.rapidapi.com
RAPID_API_PRICE_URL_INTRADAY=https://twelve-data1.p.rapidapi.com/time_series
RAPID_API_PRICE_URL_DAILY=https://twelve-data1.p.rapidapi.com/time_series
```

### 3. 실행

```bash
# 단일 시뮬레이션
python scripts/run_simulation.py --ticker AAPL --seed 42

# 백테스트
python scripts/run_backtest.py --ticker AAPL --start-date 2024-01-01 --end-date 2024-12-31 --seed 42
```

## 📖 사용법

### 단일 시뮬레이션

```bash
python scripts/run_simulation.py \
  --ticker AAPL \
  --window 30 \
  --seed 42 \
  --mode intraday \
  --interval 1h \
  --use-memory
```

### 백테스트

```bash
python scripts/run_backtest.py \
  --ticker AAPL \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --seed 42
```

**결과:**
- `results/backtest_*.json` - 전체 결과
- `results/backtest_*_metrics.csv` - 성과 메트릭스
- `results/backtest_*_trades.csv` - 거래 내역

### 배치 실험 (논문 연구용)

```bash
# 여러 시드로 대규모 실험 (for loop 사용)
# Bash/Linux/Mac:
for seed in 42 43 44 45 46; do
  python scripts/run_backtest.py \
    --ticker AAPL \
    --start-date 2024-01-01 \
    --end-date 2024-06-30 \
    --seed $seed \
    --use-memory \
    --output-dir results/with_memory
done

# PowerShell (Windows):
for ($seed=42; $seed -le 46; $seed++) {
  python scripts/run_backtest.py `
    --ticker AAPL `
    --start-date 2024-01-01 `
    --end-date 2024-06-30 `
    --seed $seed `
    --use-memory `
    --output-dir results/with_memory
}
```

## 🧪 논문 실험 예시

### 1. 학습 효과 검증 (메모리 vs 비메모리)

```bash
# 대조군 (메모리 미사용)
for seed in 42 43 44 45 46; do
  python scripts/run_backtest.py \
    --ticker AAPL \
    --start-date 2024-01-01 \
    --end-date 2024-06-30 \
    --seed $seed \
    --no-memory \
    --output-dir results/no_memory
done

# 실험군 (메모리 사용)
for seed in 42 43 44 45 46; do
  python scripts/run_backtest.py \
    --ticker AAPL \
    --start-date 2024-01-01 \
    --end-date 2024-06-30 \
    --seed $seed \
    --use-memory \
    --output-dir results/with_memory
done
```

### 2. 재현성 테스트

```bash
# 같은 seed로 3회 실행 → 결과가 정확히 동일해야 함
python scripts/run_backtest.py --ticker AAPL --seed 42
python scripts/run_backtest.py --ticker AAPL --seed 42
python scripts/run_backtest.py --ticker AAPL --seed 42
```

## ⚙️ 환경 변수 (.env)

### LLM 설정
- `OLLAMA_MODEL` (기본: llama3.1:8b): 사용할 Ollama 모델
- `OLLAMA_BASE_URL` (기본: http://localhost:11434): Ollama 서버 주소
- `LLM_TEMPERATURE` (기본: 0.3): 생성 temperature
- `LLM_MAX_TOKENS` (기본: 512): 최대 토큰 수

### 메모리 설정
- `MEMORY_STORE_MANAGER_ONLY` (기본: true): Manager만 메모리 저장
- `MEMORY_SEARCH_K` (기본: 3): 검색할 메모리 개수
- `MEMORY_RECENCY_LAMBDA` (기본: 0.01): 최근성 페널티 (일당)
- `MEMORY_DUPLICATE_THRESHOLD` (기본: 0.9): 중복 임계값
- `MEMORY_TTL_DAYS` (기본: 30): 메모리 만료 기간
- `WORKING_MEM_MAX` (기본: 10): 작업 메모리 최대 크기

### 백테스트 설정
- `BACKTEST_FEE_BPS` (기본: 0): 거래 수수료 (bps)
- `BACKTEST_SLIPPAGE_BPS` (기본: 0): 슬리피지 (bps)
- `BACKTEST_STOP_LOSS` (기본: -0.05): 손절 (-5%)
- `BACKTEST_TAKE_PROFIT` (기본: 0.1): 익절 (+10%)

### 데이터 소스
- **가격 데이터**: RapidAPI (Twelve Data) 사용. `RAPID_API_KEY`, `RAPID_API_HOST`, `RAPID_API_PRICE_URL_INTRADAY`, `RAPID_API_PRICE_URL_DAILY` 설정 필요.
- **뉴스 데이터**: Google News RSS 사용 (기본값). API 키 불필요.

## 📊 성과 메트릭스

- `total_return`: 총 수익률
- `win_rate`: 승률
- `total_trades`: 총 거래 횟수
- `sharpe_ratio`: 샤프 비율
- `max_drawdown`: 최대 낙폭
- `final_balance`: 최종 잔고

## 📁 프로젝트 구조

```
backend/
├── scripts/               # CLI 스크립트
│   ├── run_simulation.py  # 단일 시뮬레이션 실행
│   └── run_backtest.py    # 백테스트 실행
├── services/             # 핵심 로직
│   ├── simulation.py
│   ├── backtest.py
│   ├── llm.py           # Ollama 클라이언트
│   └── feedback.py
├── memory/              # 메모리 시스템
├── agents/              # 에이전트
└── results/             # 실험 결과 (자동 생성)
```

## 🐛 트러블슈팅

### Ollama 연결 실패
```bash
ollama list              # 설치 확인
ollama run llama3.1:8b  # 모델 테스트
```

### Redis/PostgreSQL 없음
- 프로젝트는 DB 없이도 작동 (InMemory 모드)
- 메모리 영속성은 없지만 실험 가능
- **논문 실험 시**: InMemory 모드 권장 (각 실행마다 자동 초기화)

### 메모리 초기화 (Redis 사용 시)
```bash
# 메모리 모드 확인
python scripts/reset_memory.py --check

# 실험 전 초기화 (Redis 사용 시만)
python scripts/reset_memory.py --all
```
- **InMemory 모드**: 초기화 불필요 (자동)
- **Redis 모드**: 각 실험 전 수동 초기화 필요

## VS Code 설정
- `.vscode/settings.json`이 `.venv` 자동 활성화 설정
- Python 3.12 사용 (`.python-version`)
- VS Code에서 터미널 열면 자동으로 `(.venv)` 활성화

## 📚 참고
- [Ollama](https://ollama.com)
- [Llama 3.1](https://ollama.com/library/llama3.1)

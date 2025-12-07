# Quant Trading System - Documentation

메모리 기반 멀티 에이전트 트레이딩 시스템

## 🎯 핵심 기능

1. **백테스팅**: 과거 데이터로 전략 검증
2. **실시간 거래**: 실제 시장에서 자동 매매 (개발 예정)

## 🏗️ 시스템 아키텍처

```
LLM 기반 멀티 에이전트
├── Bull Agent (매수 관점)
├── Bear Agent (매도 관점)
└── Manager Agent (최종 결정)
    └── 메모리 시스템 (Redis)
        ├── 단기 메모리 (Working Memory)
        └── 장기 메모리 (Vector Store)
```

### 핵심 컴포넌트

**agents/**
- `bull_agent.py`: 매수 신호 분석
- `bear_agent.py`: 매도 신호 분석
- `manager_agent.py`: 최종 의사결정 + 메모리 학습

**services/**
- `backtest.py`: 백테스팅 엔진
- `simulation.py`: 실시간 거래 시뮬레이션
- `llm.py`: Ollama LLM 클라이언트
- `feedback.py`: 거래 피드백 생성

**memory/**
- Redis 기반 벡터 저장소
- 과거 거래 경험 학습 및 검색

## ⚙️ 환경 설정

### 필수 요구사항

1. **Python 3.12+**
2. **Ollama** (LLM)
   ```bash
   winget install Ollama.Ollama
   ollama pull llama3.1:8b
   ```
3. **Redis** (메모리 저장소)
   ```bash
   docker run -d -p 6379:6379 redis:latest
   ```

### 환경 변수 (.env)

```bash
# LLM 설정
OLLAMA_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=512

# 메모리 설정
MEMORY_STORE_MANAGER_ONLY=true
MEMORY_SEARCH_K=3
MEMORY_RECENCY_LAMBDA=0.01
MEMORY_DUPLICATE_THRESHOLD=0.9
MEMORY_TTL_DAYS=30
WORKING_MEM_MAX=10

# 백테스트 설정
BACKTEST_FEE_BPS=0
BACKTEST_SLIPPAGE_BPS=0
BACKTEST_STOP_LOSS=-0.05
BACKTEST_TAKE_PROFIT=0.1

# 데이터 소스
RAPID_API_KEY=your_key
RAPID_API_HOST=twelve-data1.p.rapidapi.com
```

## 📊 성과 메트릭

- `total_return`: 총 수익률
- `win_rate`: 승률
- `sharpe_ratio`: 샤프 비율
- `max_drawdown`: 최대 낙폭
- `total_trades`: 총 거래 횟수
- `final_balance`: 최종 잔고

## 🔧 유틸리티

**메모리 초기화:**
```bash
python scripts/reset_memory.py --all
```

**메모리 확인:**
```bash
python scripts/check_memory.py
```

## 📁 프로젝트 구조

```
backend/
├── scripts/              # CLI 도구
│   ├── run_backtest.py   # 백테스팅 실행
│   ├── check_memory.py   # 메모리 상태 확인
│   └── reset_memory.py   # 메모리 초기화
├── services/             # 핵심 로직
│   ├── backtest.py       # 백테스팅 엔진
│   ├── simulation.py     # 실시간 거래
│   ├── llm.py            # LLM 클라이언트
│   └── feedback.py       # 피드백 생성
├── agents/               # 멀티 에이전트
│   ├── bull_agent.py
│   ├── bear_agent.py
│   └── manager_agent.py
├── memory/               # 메모리 시스템
└── results/              # 결과 저장
```

## 🐛 트러블슈팅

**Ollama 연결 실패:**
```bash
ollama list
ollama run llama3.1:8b
```

**Redis 연결 실패:**
```bash
# Docker로 Redis 시작
docker run -d -p 6379:6379 redis:latest
```

**메모리 초기화:**
```bash
python scripts/reset_memory.py --all
```

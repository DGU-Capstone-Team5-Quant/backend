# Quant Trading System

메모리 기반 멀티 에이전트 트레이딩 시스템

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 가상환경 생성 및 의존성 설치
uv venv .venv
uv sync

# Ollama 설치 및 모델 다운로드
winget install Ollama.Ollama
ollama pull llama3.1:8b

# Redis 시작 (Docker)
docker run -d -p 6379:6379 redis:latest
```

### 2. Quant CLI 실행 (추천!)

```bash
# 인터랙티브 CLI 시작 (가상환경 자동 감지!)
python quant.py
```

**💡 Tip:** 가상환경을 활성화하지 않아도 됩니다! CLI가 자동으로 `.venv`를 찾아서 사용합니다.

**CLI 메뉴:**
- 📊 백테스팅 (빠른 시작 / 커스텀 설정 / 결과 조회)
- 🚀 실시간 거래 (개발 예정)
- 🧠 메모리 관리 (통계 / 초기화 / 내보내기)
- 📈 대시보드 (시스템 상태 한눈에 보기)

### 3. 수동 백테스팅 (고급)

```bash
# 간단한 백테스트
python scripts/run_backtest.py --ticker AAPL --seed 42

# 기간 지정
python scripts/run_backtest.py \
  --ticker AAPL \
  --start-date 2024-01-01 \
  --end-date 2024-12-31 \
  --seed 42
```

## 📊 주요 기능

- **백테스팅**: 과거 데이터로 전략 검증
- **실시간 거래**: 자동 매매 시스템 (개발 예정)
- **멀티 에이전트**: Bull, Bear, Manager 협업
- **메모리 학습**: 과거 거래 경험 학습

## 🔧 유틸리티

```bash
# 메모리 초기화
python scripts/reset_memory.py --all

# 메모리 상태 확인
python scripts/check_memory.py
```

## 📁 프로젝트 구조

```
backend/
├── scripts/          # CLI 도구
├── services/         # 백테스팅, 실시간 거래 엔진
├── agents/           # Bull, Bear, Manager 에이전트
├── memory/           # Redis 기반 메모리 시스템
└── results/          # 결과 저장
```

## 📚 문서

자세한 내용은 [DOCS.md](DOCS.md)를 참고하세요.

## ⚠️ 필수 요구사항

- Python 3.12+
- Ollama(LLM)
- Redis (메모리 저장소)

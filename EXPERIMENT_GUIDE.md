# FinMem Trading System - 논문 실험 가이드

## 📋 목차
1. [연구 개요](#1-연구-개요)
2. [연구 질문](#2-연구-질문)
3. [시스템 아키텍처](#3-시스템-아키텍처)
4. [환경 설정](#4-환경-설정)
5. [실험 설계](#5-실험-설계)
6. [실험 실행](#6-실험-실행)
7. [데이터 분석](#7-데이터-분석)
8. [재현성 검증](#8-재현성-검증)
9. [논문 작성 가이드](#9-논문-작성-가이드)

---

## 1. 연구 개요

### 1.1 연구 배경
- **주제**: 메모리 기반 멀티 에이전트 트레이딩 시스템
- **핵심 아이디어**: LLM 기반 에이전트가 과거 거래 경험을 학습(메모리)하여 점진적으로 성과를 개선하는지 검증
- **차별점**: 단순 LLM 추론이 아닌, 메모리를 통한 학습 효과 측정

### 1.2 시스템 특징
1. **멀티 에이전트 협업**: Bull, Bear, Trader, Manager, Reflection 에이전트가 협력
2. **메모리 시스템**: 과거 거래 결정, 시장 분석, 성과 피드백을 저장하고 재사용
3. **백테스트 프레임워크**: 슬라이딩 윈도우 방식으로 과거 데이터 검증
4. **LLM 기반**: Ollama + Llama 3.1 (로컬 실행 가능)

### 1.3 기대 효과
- LLM의 "학습" 가능성을 메모리를 통해 구현
- 금융 도메인에서 멀티 에이전트 협업의 효과성 검증
- 재현 가능한 AI 트레이딩 연구 방법론 제시

---

## 2. 연구 질문

### RQ1: 메모리 학습 효과
**질문**: 메모리 사용이 거래 성과를 향상시키는가?

**가설**:
- H1: 메모리 사용 시 총 수익률(Total Return)이 증가한다
- H0: 메모리 사용 여부와 수익률은 무관하다

**측정 지표**:
- Total Return (총 수익률)
- Sharpe Ratio (샤프 비율)
- Max Drawdown (최대 낙폭)
- CAGR (연평균 성장률)

**실험 방법**:
- 대조군: 메모리 미사용 (`--no-memory`)
- 실험군: 메모리 사용 (`--use-memory`)
- 여러 시드로 반복 실행 (n=10)
- t-test로 통계적 유의성 검증

---

### RQ2: 멀티 에이전트 협업 효과
**질문**: 여러 에이전트의 협업이 의사결정 품질을 향상시키는가?

**가설**:
- H1: 멀티 에이전트 시스템이 더 나은 리스크 관리와 수익을 달성한다
- H0: 에이전트 협업 수준과 성과는 무관하다

**측정 방법**:
- Bull/Bear 라운드 수 변화에 따른 성과 비교
  - 1 라운드 (최소 협업): Bull → Bear → Trader → Manager
  - 2 라운드 (중간 협업): Bull → Bull → Bear → Trader → Manager
  - 3 라운드 (최대 협업): Bull → Bull → Bull → Bear → Trader → Manager
- 에이전트별 의견 다양성 vs 수익률 상관관계

**측정 지표**:
- Total Return
- Sharpe Ratio (리스크 대비 수익)
- Max Drawdown (리스크 관리 능력)
- 의사결정 소요 시간

---

### RQ3: 거래 누적에 따른 학습 효과 ⭐ NEW
**질문**: 메모리를 사용하는 시스템이 시간이 지남에 따라 (메모리가 쌓이면서) 트레이딩 성능이 점진적으로 향상되는가?

**핵심 아이디어**:
- 2024-01-01: 메모리 거의 없음 → Sharpe Ratio 낮음
- 2024-06-30: 메모리 충분히 쌓임 → Sharpe Ratio 높음
- 즉, **동일한 시스템 내에서** 시간에 따른 성과 개선을 확인

**가설**:
- H1: use-memory 시스템은 시간이 지날수록 성과가 개선된다 (초기 < 중기 < 후기)
- H0: 시간 경과와 성과는 무관하다 (초기 ≈ 중기 ≈ 후기)

**측정 방법**:
1. **학습 곡선 분석 (Learning Curve)**
   - **주 분석**: use-memory 시스템의 시간대별 성과 추이
   - 전체 백테스트 기간을 3구간으로 분할
     - 초기 (1~2월): 메모리 거의 없음
     - 중기 (3~4월): 메모리 축적 중
     - 후기 (5~6월): 메모리 충분
   - 각 구간별 Sharpe Ratio 비교: 초기 < 중기 < 후기 인지 확인

2. **시간에 따른 회귀 분석**
   - 독립 변수: 시간 (거래 번호, 1, 2, 3, ...)
   - 종속 변수: 성과 (Sharpe Ratio, 수익률 등)
   - **use-memory**: 회귀 기울기 > 0, p < 0.05 → **학습 효과 입증!**
   - **no-memory** (대조군): 회귀 기울기 ≈ 0, p > 0.05 → 학습 효과 없음

3. **no-memory와 대조** (선택적)
   - no-memory: 시간이 지나도 성과 평평 (학습 안 됨)
   - use-memory: 시간이 지날수록 성과 우상향 (학습 됨)
   - 이를 통해 "메모리가 있어야만 학습 효과가 나타남"을 입증

**측정 지표**:
- 구간별 Sharpe Ratio 변화율
- 구간별 Win Rate 변화율
- 회귀 분석 기울기 및 p-value
- 누적 수익 곡선의 기울기

**시각화**:
- X축: 시간 (거래 번호 or 날짜)
- Y축: 누적 수익률 또는 구간별 Sharpe Ratio
- 두 선 비교 (선택적):
  - use-memory (파란색): 우상향 곡선 (학습 효과)
  - no-memory (회색): 평평한 곡선 (학습 없음)
- 기대 결과: 파란 선이 시간이 지날수록 우상향

---

## 3. 시스템 아키텍처

### 3.1 에이전트 구조
```
[데이터 로더]
    ↓
[Bull Analyst] ←→ [메모리]
    ↓
[Bear Analyst] ←→ [메모리]
    ↓
[Trader] ←→ [메모리]
    ↓
[Manager] → [메모리 저장]
    ↓
[Reflection] → [메모리 저장]
```

### 3.2 에이전트 역할

| 에이전트 | 역할 | 입력 | 출력 |
|---------|------|------|------|
| **Bull Analyst** | 긍정적 시나리오 분석 | 시장 데이터, 메모리 | 상승 근거, 리스크 |
| **Bear Analyst** | 부정적 시나리오 분석 | 시장 데이터, 메모리 | 하락 근거, 리스크 |
| **Trader** | 거래 결정 | Bull/Bear 분석 | LONG/SHORT/HOLD |
| **Manager** | 전략 종합 | 모든 에이전트 결과 | 리스크, 전략, 다음 단계 |
| **Reflection** | 과거 성과 성찰 | 전체 의사결정 과정 | 개선점, 액션 아이템 |

### 3.3 메모리 시스템
- **저장 내용**: 에이전트 분석 결과, 거래 결정, 성과 피드백
- **검색 방식**: Semantic Search (임베딩 기반)
- **가중치**:
  - Role weights: Manager(1.5), Feedback(1.3), Trader(1.2)
  - Recency penalty: 일자별 0.01 감소
  - Salience: 성과 기반 중요도

---

## 4. 환경 설정

### 4.1 필수 요구사항
- Python 3.12 이상
- uv (패키지 관리자)
- Ollama (LLM 서버)
- 최소 8GB RAM (16GB 권장)

### 4.2 설치 단계

#### Step 1: 저장소 클론
```bash
cd ~/Desktop
git clone <your-repo-url> backend
cd backend
```

#### Step 2: Python 환경 설정
```bash
# uv 설치 (Windows)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 가상환경 생성 및 패키지 설치
uv venv .venv
uv sync
```

#### Step 3: Ollama 설치 및 모델 다운로드
```bash
# Ollama 설치 (Windows)
winget install Ollama.Ollama

# 모델 다운로드 (약 4.7GB)
ollama pull llama3.1:8b

# 모델 테스트
ollama run llama3.1:8b "Hello, test"
```

#### Step 4: 환경 변수 설정 (선택사항)
```bash
# .env 파일 생성 (기본값으로 작동하므로 생략 가능)
# 실제 주가 데이터 사용 시에만 필요:
# RAPID_API_KEY=your_key
# RAPID_API_HOST=twelve-data1.p.rapidapi.com
```

### 4.3 설치 검증
```bash
# 가상환경 활성화 확인
.venv\Scripts\activate

# Python 버전 확인
python --version  # 3.12 이상

# Ollama 연결 확인
ollama list

# 프로젝트 구조 확인
ls
```

---

## 5. 실험 설계

### 5.1 실험 1: 메모리 효과 검증 (RQ1)

#### 5.1.1 실험 설계
- **독립 변수**: 메모리 사용 여부 (use_memory: True/False)
- **종속 변수**: Total Return, Sharpe Ratio, Max Drawdown
- **통제 변수**: 종목, 기간, 시드, LLM 설정
- **표본 크기**: 종목당 10회 반복 (seed: 0~9)

#### 5.1.2 실험 조건
| 조건 | 설명 | 파라미터 |
|------|------|----------|
| **대조군** | 메모리 미사용 | `--no-memory` |
| **실험군** | 메모리 사용 | `--use-memory` |

#### 5.1.3 실험 절차 (AAPL 예시)

**⚠️ 중요: Train/Test 기간 분리**
- **Train (워밍업)**: 2025-01-01 ~ 2025-08-31 (과거 데이터로 메모리 축적)
- **Test (평가)**: 2025-09-01 ~ 2025-11-20 (미래 데이터로 평가)
- **목적**: Data leakage 방지 및 과적합 방지

```bash
# === 대조군 (no-memory) ===
python scripts/reset_memory.py --all
# "yes" 입력하여 확인

python scripts/run_backtest.py \
  --ticker AAPL \
  --start-date 2025-09-01 \
  --end-date 2025-11-20 \
  --seed 42 \
  --no-memory \
  --output-dir results/exp1_control

# === 실험군 (with-memory) ===
python scripts/reset_memory.py --all
# "yes" 입력하여 확인

# Step 1: 과거 데이터로 메모리 워밍업 (Train period)
python scripts/run_backtest.py \
  --ticker AAPL \
  --start-date 2025-01-01 \
  --end-date 2025-08-31 \
  --seed 1 \
  --use-memory \
  --output-dir results/exp1_warmup

# Step 2: 메모리 축적 확인
python scripts/check_memory.py --ticker AAPL

# Step 3: 미래 데이터로 평가 (Test period - unseen data!)
python scripts/run_backtest.py \
  --ticker AAPL \
  --start-date 2025-09-01 \
  --end-date 2025-11-20 \
  --seed 42 \
  --use-memory \
  --output-dir results/exp1_treatment
```

**핵심 원칙:**
1. **기간 분리**: 워밍업과 평가 기간을 완전히 분리하여 data leakage 방지
2. **메모리 축적**: 실험군은 과거 데이터로 먼저 메모리를 쌓은 후 평가
3. **대조군 기준**: 대조군은 Test period만 실행 (메모리 없음)
4. **공정한 비교**: 둘 다 같은 seed(42)로 Test period 평가

**잘못된 예시 (Data Leakage!):**
```bash
# ❌ 잘못됨: 같은 기간을 두 번 사용
python scripts/run_backtest.py --start-date 2025-09-01 --end-date 2025-11-20 --use-memory  # 워밍업
python scripts/run_backtest.py --start-date 2025-09-01 --end-date 2025-11-20 --use-memory  # 평가
# → 메모리가 미래를 미리 아는 상태 = 과적합!
```

#### 5.1.4 고급: Walk-Forward 테스트 (메모리 학습 효과 검증)

시간이 지날수록 메모리가 누적되어 성과가 개선되는지 확인:

```bash
python scripts/reset_memory.py --all

# Q1: 워밍업 (결과 저장하지 않음)
python scripts/run_backtest.py \
  --ticker AAPL \
  --start-date 2025-01-01 \
  --end-date 2025-03-31 \
  --use-memory \
  --output-dir results/walk_forward/q1_warmup

# Q2: 첫 평가 (Q1 메모리 활용)
python scripts/run_backtest.py \
  --ticker AAPL \
  --start-date 2025-04-01 \
  --end-date 2025-06-30 \
  --seed 42 \
  --use-memory \
  --output-dir results/walk_forward/q2_test

# Q3: 두 번째 평가 (Q1+Q2 메모리 누적)
python scripts/run_backtest.py \
  --ticker AAPL \
  --start-date 2025-07-01 \
  --end-date 2025-09-30 \
  --seed 42 \
  --use-memory \
  --output-dir results/walk_forward/q3_test

# Q4: 최종 평가 (Q1+Q2+Q3 메모리 누적)
python scripts/run_backtest.py \
  --ticker AAPL \
  --start-date 2025-10-01 \
  --end-date 2025-11-20 \
  --seed 42 \
  --use-memory \
  --output-dir results/walk_forward/q4_test
```

**기대 결과**: Q2 < Q3 < Q4 성과 개선 (메모리 학습 효과)

**분석 방법**:
```python
# 각 분기 수익률 추출
q2_return = results_q2["total_return"]
q3_return = results_q3["total_return"]
q4_return = results_q4["total_return"]

# 시간에 따른 성과 추이 그래프
plt.plot([2, 3, 4], [q2_return, q3_return, q4_return], marker='o')
plt.title("Memory Learning Effect Over Time")
plt.xlabel("Quarter")
plt.ylabel("Total Return")

# 선형 회귀로 학습 효과 검증
from scipy.stats import linregress
slope, intercept, r_value, p_value, std_err = linregress([2,3,4], [q2_return, q3_return, q4_return])
print(f"Learning slope: {slope:.4f}, p-value: {p_value:.4f}")
# slope > 0 and p < 0.05 → 메모리 학습 효과 유의미!
```

---

### 5.2 실험 2: 멀티 에이전트 협업 효과 (RQ2)

#### 5.2.1 실험 설계
- **독립 변수**: Bull/Bear 라운드 수 (1, 2, 3)
- **종속 변수**: 의사결정 품질, 수익률, 리스크 관리
- **통제 변수**: 종목, 기간, 시드, 메모리 사용
- **표본 크기**: 각 조건당 5회 반복 (seed: 0~4)

#### 5.2.2 실험 조건
| 조건 | Bull/Bear 라운드 | 의미 |
|------|------------------|------|
| **최소 협업** | 1 라운드 | Bull → Bear → Trader (단순) |
| **중간 협업** | 2 라운드 | Bull → Bull → Bear → Trader (토론) |
| **최대 협업** | 3 라운드 | Bull → Bull → Bull → Bear → Trader (충분한 토론) |

#### 5.2.3 실험 절차 (Windows)
```bash
# 0. 메모리 초기화 (필수!)
python scripts/reset_memory.py --all
# "yes" 입력하여 확인

# 1. 1 라운드 (최소 협업)
$env:DEBATE_MAX_BB_ROUNDS=1
python scripts/run_backtest.py \
  --ticker AAPL \
  --seed 0 \
  --use-memory \
  --output-dir results/exp2_rounds_1

# 2. 2 라운드 전 초기화 (필수!)
python scripts/reset_memory.py --all
# "yes" 입력하여 확인

# 3. 2 라운드 (중간 협업)
$env:DEBATE_MAX_BB_ROUNDS=2
python scripts/run_backtest.py \
  --ticker AAPL \
  --seed 0 \
  --use-memory \
  --output-dir results/exp2_rounds_1

# 4. 3 라운드 전 초기화 (필수!)
python scripts/reset_memory.py --all
# "yes" 입력하여 확인

# 5. 3 라운드 (최대 협업)
$env:DEBATE_MAX_BB_ROUNDS=3
python scripts/run_backtest.py \
  --ticker AAPL \
  --seed 0 \
  --use-memory \
  --output-dir results/exp2_rounds_1
```

#### 5.2.4 분석 방법
```python
# 라운드별 성과 비교
python scripts/analyze_results.py --exp exp2_collaboration --plot
```

---

### 5.3 실험 3: 거래 누적에 따른 학습 효과 (RQ3) ⭐ NEW

#### 5.3.1 실험 설계
- **목적**: 메모리를 사용하는 시스템이 시간이 지남에 따라 (메모리가 쌓이면서) 성과가 점진적으로 개선되는지 검증
- **핵심 질문**: 2024-01-01 (메모리 적음) vs 2024-06-30 (메모리 많음) → 후기가 더 좋은 성과를 보이는가?
- **독립 변수**: 시간 (거래 번호, 날짜)
- **종속 변수**: 시간대별 수익률, Sharpe Ratio
- **분석 대상**: **use-memory 시스템의 시간대별 성과 추이** (주 분석)
- **대조군**: no-memory는 "학습 없음의 baseline" 역할 (선택적)
  - no-memory는 시간이 지나도 성과 평평 (초기 ≈ 중기 ≈ 후기)
  - use-memory는 시간이 지날수록 성과 개선 (초기 < 중기 < 후기)
- **분석 방법**:
  1. 전체 거래를 시간순으로 3구간 분할 (초기/중기/후기)
  2. 각 구간별 Sharpe Ratio 계산
  3. use-memory: 초기 → 후기로 개선되는지 확인
  4. 회귀 분석: 시간 vs 성과 (기울기 > 0 이면 학습 효과)
  5. no-memory와 비교하여 학습 효과 입증

#### 5.3.2 실험 절차

**핵심**: 각 seed가 독립적으로 6개월 동안 "메모리 없음 → 점점 쌓임" 과정을 경험하도록 함

```bash
# 1. 주 분석 대상: use-memory 장기 백테스트
# ⚠️ 중요: 각 seed마다 메모리 초기화 필수!
# 각 seed가 2024-01-01부터 독립적으로 메모리를 쌓아감

# seed 0
python scripts/reset_memory.py --all  # "yes" 입력
python scripts/run_backtest.py \
  --ticker AAPL \
  --seed 0 \
  --use-memory \
  --step 1 \
  --output-dir results/exp3_learning/with_memory

# seed 1
python scripts/reset_memory.py --all  # "yes" 입력
python scripts/run_backtest.py \
  --ticker AAPL \
  --seed 1 \
  --use-memory \
  --step 1 \
  --output-dir results/exp3_learning/with_memory

# seed 2
python scripts/reset_memory.py --all  # "yes" 입력
python scripts/run_backtest.py \
  --ticker AAPL \
  --seed 2 \
  --use-memory \
  --step 1 \
  --output-dir results/exp3_learning/with_memory

# seed 3
python scripts/reset_memory.py --all  # "yes" 입력
python scripts/run_backtest.py \
  --ticker AAPL \
  --seed 3 \
  --use-memory \
  --step 1 \
  --output-dir results/exp3_learning/with_memory

# seed 4
python scripts/reset_memory.py --all  # "yes" 입력
python scripts/run_backtest.py \
  --ticker AAPL \
  --seed 4 \
  --use-memory \
  --step 1 \
  --output-dir results/exp3_learning/with_memory

# 2. (선택적) Baseline: no-memory 실행
# "학습 없음"을 보여주기 위한 대조군
# 메모리를 사용하지 않으므로 초기화 불필요
for seed in {0..4}; do
  python scripts/run_backtest.py \
    --ticker AAPL \
    --seed $seed \
    --no-memory \
    --step 1 \
    --output-dir results/exp3_learning/no_memory
done
```

#### 5.3.3 분석 방법
```bash
# 학습 곡선 분석
python scripts/analyze_learning_curve.py \
  --with-memory-dir results/exp3_learning/with_memory \
  --no-memory-dir results/exp3_learning/no_memory \  # 선택적
  --plot \
  --output results/learning_curve_analysis.csv
```

**분석 내용:**

**주 분석: use-memory의 시간대별 성과 추이**
1. 전체 거래 기록을 시간순으로 3구간 분할
   - 초기 (1~2월): 메모리가 거의 없는 상태
   - 중기 (3~4월): 메모리가 어느 정도 쌓인 상태
   - 후기 (5~6월): 메모리가 충분히 쌓인 상태

2. 각 구간별 평균 Sharpe Ratio 계산
   - 예: 초기 0.35, 중기 0.41, 후기 0.49

3. **회귀 분석**: 시간(거래 번호) vs 성과(Sharpe Ratio)
   - 기울기 > 0 이고 p < 0.05 → **학습 효과 입증!**
   - 기울기 ≈ 0 또는 p > 0.05 → 학습 효과 없음

4. 학습 곡선 시각화
   - X축: 시간 (거래 번호 또는 날짜)
   - Y축: 누적 수익률 또는 구간별 Sharpe Ratio
   - 우상향 곡선 → 학습 효과

**보조 분석: no-memory와 비교 (선택적)**
- no-memory는 시간이 지나도 성과가 평평 (초기 ≈ 중기 ≈ 후기)
- use-memory는 우상향 (초기 < 중기 < 후기)
- 이 대조를 통해 "메모리가 있어야만 학습 효과가 나타남"을 입증

**기대 결과:**
- **use-memory**: 초기 0.35 → 중기 0.41 → 후기 0.49 (기울기 +0.0675, p=0.002 **)
- **no-memory**: 초기 0.32 → 중기 0.32 → 후기 0.32 (기울기 -0.0014, p=0.823)

---

## 6. 실험 실행

### 6.1 실행 전 체크리스트
- [ ] **Ollama 서버 실행 필수** (`ollama list`로 확인)
- [ ] **Redis 서버 실행 필수** (메모리 저장소)
- [ ] 가상환경 활성화 (`source .venv/bin/activate` 또는 `.venv\Scripts\activate`)
- [ ] `results/` 디렉터리 존재 확인
- [ ] 충분한 디스크 공간 (각 실험당 약 1GB)
- [ ] **메모리 초기화** ⭐ 중요!

#### ⚠️ 필수 요구사항
**이 시스템은 Ollama와 Redis가 필수입니다:**
- **Ollama**: LLM 생성 (연결 실패 시 시스템 중단)
- **Redis**: 메모리 저장소 (연결 실패 시 시스템 중단)

```bash
# Ollama 실행 확인
ollama list

# Redis 실행 확인 (Docker 사용 시)
docker ps | grep redis
```

#### 메모리 초기화 방법
**각 실험 조건 전에 반드시 실행:**
```bash
# 모든 메모리 초기화
python scripts/reset_memory.py --all
# "yes" 입력하여 확인

# 또는 Redis만 초기화
python scripts/reset_memory.py --redis

# 또는 특정 종목만
python scripts/reset_memory.py --ticker AAPL
```

### 6.2 단일 백테스트 실행 예시
```bash
python scripts/run_backtest.py \
  --ticker AAPL \
  --seed 42 \
  --use-memory \
  --window 30 \
  --step 1 \
  --interval 1h \
  --shares 1.0 \
  --initial-capital 10000.0 \
  --output-dir results/test
```

### 6.3 결과 파일 설명
실행 후 `results/` 디렉터리에 3개 파일 생성:

1. **backtest_AAPL_42_YYYYMMDD_HHMMSS.json**
   - 전체 결과 (메트릭, 거래 내역)
   - 메타데이터 (시드, LLM 설정 등)

2. **backtest_AAPL_42_YYYYMMDD_HHMMSS_metrics.csv**
   - 성과 지표만 요약
   - 엑셀/R/Python 분석용

3. **backtest_AAPL_42_YYYYMMDD_HHMMSS_trades.csv**
   - 거래 내역 (타임스탬프별)
   - 포지션, PnL, 누적 수익 등

### 6.4 실험 진행 상황 모니터링
```bash
# 실행 중인 프로세스 확인
ps aux | grep run_backtest

# 결과 파일 개수 확인
ls results/exp1_no_memory/*.json | wc -l

# 최근 결과 확인
tail -f results/exp1_no_memory/backtest_*.json
```

### 6.5 예상 실행 시간
| 실험 | 조건 수 | 예상 시간 | 디스크 사용량 | 우선순위 |
|------|---------|-----------|---------------|----------|
| 실험 1 (메모리 효과) | 20회 (10 seeds × 2 조건) | 2~4시간 | 500MB | ⭐⭐⭐ 필수 |
| 실험 2 (멀티 에이전트) | 15회 (5 seeds × 3 라운드) | 1~2시간 | 300MB | ⭐⭐ 중요 |
| 실험 3 (학습 곡선) | 10회 (5 seeds × 2 조건) | 3~5시간 | 800MB | ⭐⭐⭐ 필수 |

**참고:**
- 실행 시간은 시스템 사양과 LLM 속도에 따라 달라집니다
- Ollama 로컬 실행 기준 (Llama 3.1 8B)
- 병렬 실행 시 시간 단축 가능

---

## 7. 데이터 분석

### 7.1 분석 환경 설정
```bash
# Jupyter 설치 (분석용)
uv pip install jupyter pandas matplotlib seaborn scipy

# Jupyter 노트북 실행
jupyter notebook
```

### 7.2 실험 1 분석 코드 (Python)

```python
import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json

# 1. 데이터 로드
def load_experiment_results(exp_dir):
    """실험 결과 JSON 파일들을 DataFrame으로 로드"""
    results = []
    for json_file in Path(exp_dir).glob("*.json"):
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            summary = data['summary']
            summary['seed'] = data['seed']
            summary['ticker'] = data['ticker']
            results.append(summary)
    return pd.DataFrame(results)

# 대조군/실험군 데이터 로드
df_no_memory = load_experiment_results('results/exp1_no_memory')
df_with_memory = load_experiment_results('results/exp1_with_memory')

# 2. 기술 통계
print("=== 메모리 없음 (대조군) ===")
print(df_no_memory[['total_return', 'sharpe', 'max_drawdown_pct']].describe())

print("\n=== 메모리 있음 (실험군) ===")
print(df_with_memory[['total_return', 'sharpe', 'max_drawdown_pct']].describe())

# 3. 통계 검정 (Paired t-test)
t_stat, p_value = stats.ttest_rel(
    df_with_memory['total_return'],
    df_no_memory['total_return']
)
print(f"\n=== 통계 검정 결과 ===")
print(f"t-statistic: {t_stat:.4f}")
print(f"p-value: {p_value:.4f}")
print(f"유의성: {'유의함 (p<0.05)' if p_value < 0.05 else '유의하지 않음'}")

# 4. 효과 크기 (Cohen's d)
def cohen_d(x, y):
    nx, ny = len(x), len(y)
    dof = nx + ny - 2
    return (np.mean(x) - np.mean(y)) / np.sqrt(
        ((nx-1)*np.std(x, ddof=1)**2 + (ny-1)*np.std(y, ddof=1)**2) / dof
    )

effect_size = cohen_d(
    df_with_memory['total_return'],
    df_no_memory['total_return']
)
print(f"Cohen's d: {effect_size:.4f}")
print(f"효과 크기: {
    'Large (>0.8)' if abs(effect_size) > 0.8 else
    'Medium (>0.5)' if abs(effect_size) > 0.5 else
    'Small (>0.2)' if abs(effect_size) > 0.2 else 'Negligible'
}")

# 5. 시각화
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# Total Return 비교
axes[0].boxplot([df_no_memory['total_return'], df_with_memory['total_return']],
                labels=['No Memory', 'With Memory'])
axes[0].set_ylabel('Total Return')
axes[0].set_title('Total Return Comparison')
axes[0].grid(True, alpha=0.3)

# Sharpe Ratio 비교
axes[1].boxplot([df_no_memory['sharpe'], df_with_memory['sharpe']],
                labels=['No Memory', 'With Memory'])
axes[1].set_ylabel('Sharpe Ratio')
axes[1].set_title('Sharpe Ratio Comparison')
axes[1].grid(True, alpha=0.3)

# Max Drawdown 비교
axes[2].boxplot([df_no_memory['max_drawdown_pct'], df_with_memory['max_drawdown_pct']],
                labels=['No Memory', 'With Memory'])
axes[2].set_ylabel('Max Drawdown (%)')
axes[2].set_title('Max Drawdown Comparison')
axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('results/exp1_comparison.png', dpi=300)
plt.show()

print("\n차트 저장됨: results/exp1_comparison.png")
```

### 7.3 실험 2 분석 (일반화)

```python
# 종목별 메모리 효과 분석
def analyze_generalization(no_mem_dir, with_mem_dir):
    df_no = load_experiment_results(no_mem_dir)
    df_with = load_experiment_results(with_mem_dir)

    # 종목별 평균 성과
    results = []
    for ticker in df_no['ticker'].unique():
        no_mem_returns = df_no[df_no['ticker'] == ticker]['total_return']
        with_mem_returns = df_with[df_with['ticker'] == ticker]['total_return']

        improvement = with_mem_returns.mean() - no_mem_returns.mean()
        t_stat, p_val = stats.ttest_ind(with_mem_returns, no_mem_returns)

        results.append({
            'ticker': ticker,
            'no_memory_mean': no_mem_returns.mean(),
            'with_memory_mean': with_mem_returns.mean(),
            'improvement': improvement,
            'improvement_pct': improvement / abs(no_mem_returns.mean()) * 100,
            't_statistic': t_stat,
            'p_value': p_val
        })

    df_results = pd.DataFrame(results)
    print(df_results)

    # 종목별 개선 효과 시각화
    plt.figure(figsize=(10, 6))
    plt.bar(df_results['ticker'], df_results['improvement_pct'])
    plt.axhline(0, color='red', linestyle='--', alpha=0.5)
    plt.xlabel('Ticker')
    plt.ylabel('Improvement (%)')
    plt.title('Memory Effect by Ticker')
    plt.grid(True, alpha=0.3)
    plt.savefig('results/exp2_generalization.png', dpi=300)
    plt.show()

    return df_results

gen_results = analyze_generalization(
    'results/exp2_no_memory',
    'results/exp2_with_memory'
)
```

### 7.4 실험 2 분석 (멀티 에이전트 협업)

```python
# 라운드별 성과 비교
def analyze_collaboration_effect(rounds_dirs: list):
    """
    Bull/Bear 라운드 수에 따른 성과 분석

    Args:
        rounds_dirs: [('1 round', 'results/exp2_rounds_1'), ...]
    """
    results = []

    for round_label, dir_path in rounds_dirs:
        df = load_experiment_results(dir_path)

        mean_return = df['total_return'].mean()
        mean_sharpe = df['sharpe'].mean()
        mean_drawdown = df['max_drawdown_pct'].mean()

        results.append({
            'rounds': round_label,
            'mean_return': mean_return,
            'mean_sharpe': mean_sharpe,
            'mean_drawdown': mean_drawdown,
            'n': len(df)
        })

    df_results = pd.DataFrame(results)
    print(df_results)

    # 시각화
    plt.figure(figsize=(10, 6))
    plt.plot(df_results['rounds'], df_results['mean_sharpe'], marker='o', linewidth=2)
    plt.xlabel('Collaboration Level (Bull/Bear Rounds)')
    plt.ylabel('Mean Sharpe Ratio')
    plt.title('Multi-Agent Collaboration Effect')
    plt.grid(True, alpha=0.3)
    plt.savefig('results/exp2_collaboration.png', dpi=300)

    return df_results

# 실행
collab_results = analyze_collaboration_effect([
    ('1 Round', 'results/exp2_rounds_1'),
    ('2 Rounds', 'results/exp2_rounds_2'),
    ('3 Rounds', 'results/exp2_rounds_3'),
])
```

### 7.5 실험 3 분석 (학습 곡선) ⭐ NEW

**명령어:**
```bash
python scripts/analyze_learning_curve.py \
  --no-memory-dir results/exp3_learning/no_memory \
  --with-memory-dir results/exp3_learning/with_memory \
  --plot \
  --output results/learning_curve_analysis.csv
```

**출력 예시:**
```
📈 학습 곡선 분석 (RQ3: Cumulative Learning Effect)

[ 구간별 평균 성과 ]
use_memory period_label     sharpe  total_return  win_rate
False      Early           0.3215      0.0421      0.485
False      Mid             0.3198      0.0435      0.492
False      Late            0.3187      0.0419      0.488
True       Early           0.3542      0.0538      0.501
True       Mid             0.4125      0.0687      0.523
True       Late            0.4892      0.0845      0.547

[ 회귀 분석: 시간(period) → 성과(sharpe) ]
메모리 미사용:
  기울기: -0.0014
  p-value: 0.8234
  ❌ 학습 효과 없음 (p≥0.05)

메모리 사용:
  기울기: +0.0675
  p-value: 0.0023
  ✅ 유의미한 학습 효과 (p<0.05, 기울기>0)
```

**시각화:**
- `results/learning_curves.png`: 누적 수익 곡선 + 구간별 Sharpe Ratio
- 메모리 사용 시 시간에 따라 성과 개선 확인

---

## 8. 재현성 검증

### 8.1 재현성 체크리스트
실험의 재현성을 보장하기 위해 다음을 확인:

- [ ] **시드 고정**: 모든 실험에서 `--seed` 명시
- [ ] **버전 기록**:
  ```bash
  python --version > results/python_version.txt
  ollama list > results/ollama_models.txt
  uv pip freeze > results/requirements.txt
  ```
- [ ] **환경 변수 기록**:
  ```bash
  env | grep -E "(OLLAMA|LLM|MEMORY)" > results/env_vars.txt
  ```
- [ ] **데이터 버전**: 데이터 수집 날짜 기록
- [ ] **시스템 정보**:
  ```bash
  uname -a > results/system_info.txt  # Linux/Mac
  systeminfo > results/system_info.txt  # Windows
  ```

### 8.2 재현성 검증 스크립트

```python
# scripts/check_reproducibility.py
import json
import sys
from pathlib import Path

def compare_json_files(file1, file2, tolerance=1e-9):
    """두 JSON 파일을 비교 (float 값은 오차 허용)"""
    with open(file1) as f1, open(file2) as f2:
        data1 = json.load(f1)
        data2 = json.load(f2)

    def compare_values(v1, v2, path="root"):
        if isinstance(v1, dict) and isinstance(v2, dict):
            if set(v1.keys()) != set(v2.keys()):
                print(f"❌ Keys differ at {path}: {set(v1.keys())} vs {set(v2.keys())}")
                return False
            for key in v1.keys():
                if not compare_values(v1[key], v2[key], f"{path}.{key}"):
                    return False
        elif isinstance(v1, list) and isinstance(v2, list):
            if len(v1) != len(v2):
                print(f"❌ List length differs at {path}: {len(v1)} vs {len(v2)}")
                return False
            for i, (item1, item2) in enumerate(zip(v1, v2)):
                if not compare_values(item1, item2, f"{path}[{i}]"):
                    return False
        elif isinstance(v1, float) and isinstance(v2, float):
            if abs(v1 - v2) > tolerance:
                print(f"❌ Float differs at {path}: {v1} vs {v2}")
                return False
        else:
            if v1 != v2:
                print(f"❌ Value differs at {path}: {v1} vs {v2}")
                return False
        return True

    return compare_values(data1, data2)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python check_reproducibility.py file1.json file2.json [file3.json ...]")
        sys.exit(1)

    files = sys.argv[1:]
    print(f"Comparing {len(files)} files...")

    all_match = True
    for i in range(len(files) - 1):
        print(f"\nComparing {files[i]} vs {files[i+1]}:")
        if compare_json_files(files[i], files[i+1]):
            print("✅ Files match!")
        else:
            all_match = False

    if all_match:
        print("\n🎉 All files are identical - reproducibility confirmed!")
        sys.exit(0)
    else:
        print("\n⚠️ Some files differ - reproducibility issue detected!")
        sys.exit(1)
```

---

## 9. 논문 작성 가이드

### 9.1 논문 구조 제안

#### Abstract
- 연구 배경: LLM의 학습 능력 한계
- 제안 방법: 메모리 기반 멀티 에이전트 시스템
- 주요 결과: 메모리 사용 시 X% 성과 향상
- 의의: 재현 가능한 AI 트레이딩 연구 방법론

#### 1. Introduction
- 문제 정의: LLM은 매 추론마다 "처음부터" 시작
- 연구 동기: 메모리를 통한 "경험 학습" 구현
- 기여:
  1. 메모리 기반 학습 프레임워크
  2. 멀티 에이전트 협업 설계
  3. 재현 가능한 백테스트 방법론

#### 2. Related Work
- LLM in Finance
- Multi-Agent Systems
- Memory-Augmented Neural Networks
- Algorithmic Trading with AI

#### 3. Methodology
- 3.1 System Architecture (그림 포함)
- 3.2 Agent Design
  - Bull/Bear Analysts
  - Trader
  - Manager
  - Reflection
- 3.3 Memory System
  - FinMem 구조
  - Semantic Search
  - Memory Scoring (recency, salience, role)
- 3.4 Backtesting Framework
  - Sliding Window
  - Transaction Costs
  - Risk Management

#### 4. Experimental Setup
- 4.1 Research Questions (RQ1~4)
- 4.2 Datasets
  - Tickers: AAPL, TSLA, GOOGL, MSFT, NVDA
  - Period: 2024-01-01 ~ 2024-06-30
  - Frequency: 1-hour intervals
- 4.3 Baselines
  - No Memory
  - Random Agent
  - Buy-and-Hold
- 4.4 Evaluation Metrics
  - Total Return
  - Sharpe Ratio
  - Max Drawdown
  - Calmar Ratio
- 4.5 Implementation Details
  - LLM: Llama 3.1 8B
  - Temperature: 0.3
  - Embedding: [specify]
  - Hardware: [specify]

#### 5. Results
- 5.1 RQ1: Memory Learning Effect
  - Table: 메모리 유무별 평균 성과
  - Figure: Box plot 비교
  - Statistical Test: t-test, p-value, Cohen's d
- 5.2 RQ2: Generalization
  - Table: 종목별 성과
  - Figure: 종목별 개선율 bar chart
- 5.3 RQ3: Reproducibility
  - Table: 재현성 검증 결과
  - Hash 일치 여부
- 5.4 RQ4: Multi-Agent Collaboration
  - Table: 라운드 수별 성과
  - Figure: Trade-off 분석

#### 6. Discussion
- 6.1 메모리가 효과적인 이유
  - 과거 실수 학습
  - 성공 패턴 재사용
  - 컨텍스트 축적
- 6.2 Limitations
  - LLM의 추론 능력 한계
  - 시장 변동성에 따른 성과 차이
  - 실제 거래와의 차이 (슬리피지 등)
- 6.3 Future Work
  - 더 긴 기간 실험
  - 다양한 LLM 비교
  - 온라인 학습 메커니즘

#### 7. Conclusion
- 메모리 기반 학습이 유의미한 성과 개선
- 재현 가능한 실험 방법론 제시
- AI 트레이딩 연구의 새로운 방향

---

### 9.2 표 작성 예시

**Table 1: Performance Comparison (RQ1)**

| Metric | No Memory | With Memory | Improvement | p-value |
|--------|-----------|-------------|-------------|---------|
| Total Return (%) | 5.2 ± 3.1 | 8.7 ± 2.8 | **+3.5** | 0.023 |
| Sharpe Ratio | 0.45 ± 0.12 | 0.62 ± 0.09 | **+0.17** | 0.008 |
| Max Drawdown (%) | -12.3 ± 4.2 | -8.1 ± 3.5 | **-4.2** | 0.041 |
| Calmar Ratio | 0.42 ± 0.15 | 0.71 ± 0.18 | **+0.29** | 0.012 |

*평균 ± 표준편차, n=10 seeds per condition*

---

**Table 2: Generalization Across Tickers (RQ2)**

| Ticker | Sector | No Memory Return (%) | With Memory Return (%) | Improvement (%) |
|--------|--------|----------------------|------------------------|-----------------|
| AAPL | Technology | 5.2 | 8.7 | +3.5** |
| TSLA | Automotive | 3.1 | 6.4 | +3.3** |
| GOOGL | Technology | 4.8 | 7.2 | +2.4* |
| MSFT | Technology | 6.1 | 9.3 | +3.2** |
| NVDA | Technology | 7.5 | 11.2 | +3.7** |

*p<0.05, **p<0.01*

---

### 9.3 그림 작성 가이드

**Figure 1: System Architecture**
- 에이전트 흐름도
- 메모리 시스템 연결
- 데이터 흐름

**Figure 2: Performance Comparison (Box Plot)**
- x축: No Memory vs With Memory
- y축: Total Return
- 개별 데이터 포인트 표시 (strip plot)

**Figure 3: Learning Curve**
- x축: 백테스트 스텝 (시간)
- y축: 누적 수익률
- 두 선: No Memory (blue) vs With Memory (red)

**Figure 4: Memory Impact by Ticker**
- x축: Ticker
- y축: Improvement (%)
- Bar chart

---

### 9.4 결과 해석 가이드

#### 통계적 유의성 판단
- **p < 0.001**: 매우 강한 증거 (*** 표시)
- **p < 0.01**: 강한 증거 (** 표시)
- **p < 0.05**: 유의함 (* 표시)
- **p ≥ 0.05**: 유의하지 않음 (n.s.)

#### 효과 크기 해석 (Cohen's d)
- **|d| > 0.8**: Large effect
- **|d| > 0.5**: Medium effect
- **|d| > 0.2**: Small effect
- **|d| < 0.2**: Negligible

#### 논문에서 피해야 할 표현
❌ "메모리가 항상 더 좋다"
✅ "메모리 사용이 평균적으로 X% 성과 향상 (p<0.05, d=0.7)"

❌ "우리 시스템이 최고다"
✅ "제안 방법이 baseline 대비 통계적으로 유의미한 개선"

❌ "실제 트레이딩에 사용 가능"
✅ "백테스트 환경에서의 개념 검증 (proof-of-concept)"

---

### 9.5 논문 작성 체크리스트

- [ ] **재현성 정보 포함**
  - [ ] 모든 하이퍼파라미터 명시
  - [ ] 시드 값 기록
  - [ ] 소프트웨어 버전 명시
  - [ ] 데이터 수집 날짜/방법
- [ ] **통계 검정 적절성**
  - [ ] 정규성 검정 (Shapiro-Wilk)
  - [ ] 적절한 검정 선택 (t-test vs Wilcoxon)
  - [ ] 다중 비교 보정 (Bonferroni)
- [ ] **시각화 품질**
  - [ ] 고해상도 (300 DPI 이상)
  - [ ] 컬러블라인드 고려 (색상 선택)
  - [ ] 축 레이블 명확
  - [ ] 범례 포함
- [ ] **Limitations 명확히 기술**
  - [ ] 백테스트의 한계 (look-ahead bias 등)
  - [ ] 시장 가정 (거래 비용, 슬리피지)
  - [ ] 일반화 가능성
- [ ] **윤리적 고려사항**
  - [ ] 투자 권유 아님 명시
  - [ ] 과거 성과 ≠ 미래 성과 명시
  - [ ] 연구 목적임을 강조

---

## 10. 트러블슈팅

### 10.1 Ollama 연결 실패
```bash
# 문제: "Connection refused to localhost:11434"
# 해결:
ollama serve  # 서버 시작

# 확인:
curl http://localhost:11434/api/tags
```

### 10.2 메모리 부족
```bash
# 문제: "Out of memory" 오류
# 해결: 윈도우 크기 줄이기
python scripts/run_backtest.py --window 10  # 기본 30 → 10
```

### 10.3 데이터 로드 실패
```bash
# 문제: "No price data returned"
# 원인: API 키 없거나 만료
# 해결: 더미 데이터 사용
# → 현재는 기본적으로 더미 데이터 사용하므로 API 키 불필요
```

### 10.4 실험 중단 후 재개
```bash
# 이미 실행된 실험 확인
ls results/exp1_no_memory/*.json | wc -l

# 특정 시드만 재실행
for seed in {5..9}; do  # 0~4는 이미 완료
  python scripts/run_backtest.py --ticker AAPL --seed $seed ...
done
```

---

## 11. 추가 리소스

### 11.1 참고 논문
1. **Memory-Augmented AI**:
   - Weston et al. "Memory Networks" (2015)
   - Graves et al. "Neural Turing Machines" (2014)

2. **Multi-Agent Systems**:
   - Park et al. "Generative Agents" (2023)
   - Wu et al. "AutoGen" (2023)

3. **LLM in Finance**:
   - Lopez-Lira & Tang "Can ChatGPT Forecast Stock Price Movements?" (2023)
   - Xie et al. "The Wall Street Neophyte" (2023)

### 11.2 유용한 도구
- **데이터 분석**: Jupyter, Pandas, NumPy
- **시각화**: Matplotlib, Seaborn, Plotly
- **통계**: SciPy, Statsmodels
- **버전 관리**: Git, DVC (Data Version Control)

### 11.3 커뮤니티
- Ollama Discord: https://discord.gg/ollama
- LangGraph GitHub: https://github.com/langchain-ai/langgraph
- Anthropic Discord: https://discord.gg/anthropic

---

## 부록 A: 빠른 시작 (Quick Start)

프로젝트를 처음 접하는 사람을 위한 최소 단계:

### Step 1: 환경 설정 (10분)
```bash
# uv 설치 (이미 설치된 경우 생략)
# Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 가상환경 생성 및 패키지 설치
uv venv .venv
uv sync

# Ollama 설치 및 모델 다운로드
# Windows: winget install Ollama.Ollama
ollama pull llama3.1:8b
```

### Step 2: 간단한 테스트 실행 (5분)
```bash
# 활성화 확인
.venv\Scripts\activate  # Windows

# 단일 백테스트 실행
python scripts/run_backtest.py --ticker AAPL --seed 42

# 결과 확인
ls results/
```

### Step 3: 본격 실험 실행

#### 실험 1: 메모리 효과 검증 (필수 ⭐⭐⭐)
```bash
# 대조군 (메모리 없음) - 시드 0~9
for ($seed=0; $seed -le 9; $seed++) {
  python scripts/run_backtest.py `
    --ticker AAPL `
    --seed $seed `
    --no-memory `
    --output-dir results/exp1_no_memory
}

# 실험군 (메모리 사용) - 시드 0~9
for ($seed=0; $seed -le 9; $seed++) {
  python scripts/run_backtest.py `
    --ticker AAPL `
    --seed $seed `
    --use-memory `
    --output-dir results/exp1_with_memory
}

# 분석
python scripts/analyze_results.py --exp exp1_memory_effect --plot
```

#### 실험 2: 멀티 에이전트 협업 (중요 ⭐⭐)
```bash
# 1 라운드
$env:DEBATE_MAX_BB_ROUNDS=1
for ($seed=0; $seed -le 4; $seed++) {
  python scripts/run_backtest.py `
    --ticker AAPL `
    --seed $seed `
    --use-memory `
    --output-dir results/exp2_rounds_1
}

# 2 라운드 (기본값)
$env:DEBATE_MAX_BB_ROUNDS=2
for ($seed=0; $seed -le 4; $seed++) {
  python scripts/run_backtest.py `
    --ticker AAPL `
    --seed $seed `
    --use-memory `
    --output-dir results/exp2_rounds_2
}

# 3 라운드
$env:DEBATE_MAX_BB_ROUNDS=3
for ($seed=0; $seed -le 4; $seed++) {
  python scripts/run_backtest.py `
    --ticker AAPL `
    --seed $seed `
    --use-memory `
    --output-dir results/exp2_rounds_3
}
```

#### 실험 3: 학습 곡선 분석 (필수 ⭐⭐⭐)
```bash
# 장기 백테스트 (6개월)
# 메모리 없음
for ($seed=0; $seed -le 4; $seed++) {
  python scripts/run_backtest.py `
    --ticker AAPL `
    --start-date 2024-01-01 `
    --end-date 2024-06-30 `
    --seed $seed `
    --no-memory `
    --output-dir results/exp3_learning/no_memory
}

# 메모리 사용
for ($seed=0; $seed -le 4; $seed++) {
  python scripts/run_backtest.py `
    --ticker AAPL `
    --start-date 2024-01-01 `
    --end-date 2024-06-30 `
    --seed $seed `
    --use-memory `
    --output-dir results/exp3_learning/with_memory
}

# 학습 곡선 분석
python scripts/analyze_learning_curve.py `
  --no-memory-dir results/exp3_learning/no_memory `
  --with-memory-dir results/exp3_learning/with_memory `
  --plot `
  --output results/learning_curve_analysis.csv
```

### Step 4: 결과 정리

실험이 완료되면 다음 파일들이 생성됩니다:

```
results/
├── exp1_memory_effect/
│   ├── no_memory/
│   │   ├── backtest_AAPL_0_*.json
│   │   └── ...
│   └── with_memory/
│       └── ...
├── exp2_rounds_1/
│   └── ...
├── exp3_learning/
│   ├── no_memory/
│   └── with_memory/
├── analysis_rq1.png
├── exp2_collaboration.png
├── learning_curves.png
└── learning_curve_analysis.csv
```

### Step 5: 논문 작성

섹션 9 "논문 작성 가이드" 참고하여:
1. 표 작성 (Table 1, 2, 3)
2. 그림 삽입 (Figure 1, 2, 3)
3. 결과 해석
4. 통계 검정 결과 기술

---

## 부록 B: 환경 변수 전체 목록

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `OLLAMA_MODEL` | llama3.1:8b | LLM 모델 |
| `OLLAMA_BASE_URL` | http://localhost:11434 | Ollama 서버 |
| `LLM_TEMPERATURE` | 0.3 | 생성 다양성 |
| `LLM_MAX_TOKENS` | 512 | 최대 토큰 |
| `MEMORY_SEARCH_K` | 3 | 검색 메모리 개수 |
| `MEMORY_RECENCY_LAMBDA` | 0.01 | 최근성 페널티 |
| `WORKING_MEM_MAX` | 10 | 작업 메모리 크기 |
| `BACKTEST_FEE_BPS` | 0 | 거래 수수료 (bps) |
| `BACKTEST_SLIPPAGE_BPS` | 0 | 슬리피지 (bps) |

전체 목록: [config.py](config.py:1-61) 참고

---

## 부록 C: CSV 결과 분석 (R)

```r
library(tidyverse)
library(ggplot2)

# 데이터 로드
no_mem <- read_csv("results/exp1_no_memory/*_metrics.csv")
with_mem <- read_csv("results/exp1_with_memory/*_metrics.csv")

# 병합
df <- bind_rows(
  no_mem %>% mutate(condition = "No Memory"),
  with_mem %>% mutate(condition = "With Memory")
)

# t-test
t.test(total_return ~ condition, data = df)

# 시각화
ggplot(df, aes(x = condition, y = total_return, fill = condition)) +
  geom_boxplot() +
  geom_jitter(width = 0.1, alpha = 0.5) +
  theme_minimal() +
  labs(title = "Total Return Comparison",
       y = "Total Return (%)",
       x = "")
ggsave("results/exp1_boxplot.png", width = 8, height = 6, dpi = 300)
```

---

## 마무리

이 가이드는 **메모리 기반 멀티 에이전트 트레이딩 시스템**의 논문 연구를 위한 완전한 프레임워크를 제공합니다.

### 핵심 연구 질문 (3가지)

1. **RQ1: 메모리 학습 효과** ⭐⭐⭐
   - 메모리 사용이 거래 성과를 향상시키는가?
   - 실험 1로 검증 (대조군 vs 실험군)

2. **RQ2: 멀티 에이전트 협업** ⭐⭐
   - 여러 에이전트의 협업이 의사결정 품질을 향상시키는가?
   - 실험 2로 검증 (1/2/3 라운드 비교)

3. **RQ3: 거래 누적에 따른 학습 효과** ⭐⭐⭐ NEW
   - 거래가 누적될수록 성과가 점진적으로 향상되는가?
   - 실험 3으로 검증 (학습 곡선 분석)

### 실험 순서 추천

**최소 실험 (시간 부족 시):**
1. 실험 1 (메모리 효과) - 2~4시간
2. 실험 3 (학습 곡선) - 3~5시간
→ 총 5~9시간

**완전한 실험 (논문 제출 시):**
1. 실험 1 (메모리 효과) - 2~4시간
2. 실험 2 (멀티 에이전트) - 1~2시간
3. 실험 3 (학습 곡선) - 3~5시간
→ 총 6~11시간

### 핵심 원칙

1. **재현성**: 모든 실험에 시드 사용
2. **통계적 엄밀성**: t-test, 회귀 분석, 효과 크기 측정
3. **투명성**: 모든 설정과 한계 명시
4. **시각화**: 학습 곡선, Box plot 등 명확한 그래프

### 예상 논문 기여

1. **방법론 기여**: 메모리 기반 LLM 학습 프레임워크
2. **실증 기여**: 시간에 따른 학습 효과 입증
3. **시스템 기여**: 재현 가능한 멀티 에이전트 백테스트 시스템

### 도움이 필요하면

1. [README.md](README.md) 트러블슈팅 섹션 확인
2. 섹션 10 "트러블슈팅" 참고
3. 실험 로그 확인 (`results/` 디렉터리)
4. GitHub Issues 검색

**성공적인 연구를 기원합니다!** 🎓📊

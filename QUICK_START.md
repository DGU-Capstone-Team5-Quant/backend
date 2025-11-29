# 논문 실험 빠른 시작 가이드

**목표:** 메모리 기반 멀티 에이전트 트레이딩 시스템의 학습 효과를 실험으로 검증

## 📋 3가지 핵심 실험

1. **메모리 학습 효과** ⭐⭐⭐ (필수)
   - 메모리 사용이 성과를 향상시키는가?

2. **멀티 에이전트 협업** ⭐⭐ (중요)
   - 에이전트 협업이 의사결정을 개선하는가?

3. **거래 누적 학습 효과** ⭐⭐⭐ (필수, NEW)
   - 시간이 지날수록 성과가 개선되는가?

---

## 🚀 1분 만에 시작하기

### 환경 확인
```powershell
# 1. Ollama 실행 중인지 확인
ollama list

# 2. 가상환경 활성화
.venv\Scripts\activate

# 3. 메모리 시스템 확인 ⭐ 중요!
python scripts/reset_memory.py --check

# 4. 테스트 실행 (1회, 약 5분)
python scripts/run_backtest.py --ticker AAPL --seed 42
```

**⚠️ 필수 요구사항:**
- **Ollama**: LLM 생성 (연결 실패 시 시스템 중단)
- **Redis**: 메모리 저장소 (연결 실패 시 시스템 중단)
- 각 실험 전 메모리 초기화 필수: `python scripts/reset_memory.py --all`

---

## 🔬 실험 실행 (복사해서 붙여넣기)

### 실험 1: 메모리 효과 (⏱️ 2~4시간)

**0. 메모리 초기화 (필수!):**
```powershell
python scripts/reset_memory.py --all
# "yes" 입력하여 확인
```

**1. 대조군 (메모리 없음):**
```powershell
for ($seed=0; $seed -le 9; $seed++) {
  python scripts/run_backtest.py --ticker AAPL --seed $seed --no-memory --output-dir results/exp1_no_memory
}
```

**2. 실험군 전 초기화 (필수!):**
```powershell
python scripts/reset_memory.py --all
# "yes" 입력하여 확인
```

**3. 실험군 (메모리 사용):**
```powershell
for ($seed=0; $seed -le 9; $seed++) {
  python scripts/run_backtest.py --ticker AAPL --seed $seed --use-memory --output-dir results/exp1_with_memory
}
```

**분석:**
```powershell
python scripts/analyze_results.py --exp exp1_memory_effect --plot
```

---

### 실험 2: 멀티 에이전트 (⏱️ 1~2시간)

**0. 메모리 초기화 (필수!):**
```powershell
python scripts/reset_memory.py --all
# "yes" 입력하여 확인
```

**1. 1 라운드 (최소 협업):**
```powershell
$env:DEBATE_MAX_BB_ROUNDS=1
for ($seed=0; $seed -le 4; $seed++) {
  python scripts/run_backtest.py --ticker AAPL --seed $seed --use-memory --output-dir results/exp2_rounds_1
}
```

**2. 2 라운드 전 초기화 (필수!):**
```powershell
python scripts/reset_memory.py --all
# "yes" 입력하여 확인
```

**3. 2 라운드 (중간 협업):**
```powershell
$env:DEBATE_MAX_BB_ROUNDS=2
for ($seed=0; $seed -le 4; $seed++) {
  python scripts/run_backtest.py --ticker AAPL --seed $seed --use-memory --output-dir results/exp2_rounds_2
}
```

**4. 3 라운드 전 초기화 (필수!):**
```powershell
python scripts/reset_memory.py --all
# "yes" 입력하여 확인
```

**5. 3 라운드 (최대 협업):**
```powershell
$env:DEBATE_MAX_BB_ROUNDS=3
for ($seed=0; $seed -le 4; $seed++) {
  python scripts/run_backtest.py --ticker AAPL --seed $seed --use-memory --output-dir results/exp2_rounds_3
}
```

---

### 실험 3: 학습 곡선 (⏱️ 3~5시간)

**핵심**: 시간이 지남에 따라 (메모리가 쌓이면서) 성과가 개선되는지 확인
- 2024-01-01 (메모리 적음) vs 2024-06-30 (메모리 많음)
- 주 분석: use-memory의 시간대별 성과 추이

**1. 주 분석 대상: use-memory 장기 백테스트**
```powershell
# ⚠️ 중요: 각 seed가 독립적으로 6개월 동안 "메모리 없음 → 점점 쌓임" 과정을 경험

# seed 0
python scripts/reset_memory.py --all  # "yes" 입력
python scripts/run_backtest.py --ticker AAPL --start-date 2024-01-01 --end-date 2024-06-30 --seed 0 --use-memory --output-dir results/exp3_learning/with_memory

# seed 1
python scripts/reset_memory.py --all  # "yes" 입력
python scripts/run_backtest.py --ticker AAPL --start-date 2024-01-01 --end-date 2024-06-30 --seed 1 --use-memory --output-dir results/exp3_learning/with_memory

# seed 2
python scripts/reset_memory.py --all  # "yes" 입력
python scripts/run_backtest.py --ticker AAPL --start-date 2024-01-01 --end-date 2024-06-30 --seed 2 --use-memory --output-dir results/exp3_learning/with_memory

# seed 3
python scripts/reset_memory.py --all  # "yes" 입력
python scripts/run_backtest.py --ticker AAPL --start-date 2024-01-01 --end-date 2024-06-30 --seed 3 --use-memory --output-dir results/exp3_learning/with_memory

# seed 4
python scripts/reset_memory.py --all  # "yes" 입력
python scripts/run_backtest.py --ticker AAPL --start-date 2024-01-01 --end-date 2024-06-30 --seed 4 --use-memory --output-dir results/exp3_learning/with_memory
```

**2. (선택적) Baseline: no-memory 실행**
```powershell
# "학습 없음"을 보여주기 위한 대조군
# 메모리를 사용하지 않으므로 초기화 불필요
for ($seed=0; $seed -le 4; $seed++) {
  python scripts/run_backtest.py `
    --ticker AAPL `
    --start-date 2024-01-01 `
    --end-date 2024-06-30 `
    --seed $seed `
    --no-memory `
    --output-dir results/exp3_learning/no_memory
}
```

**분석:**
```powershell
python scripts/analyze_learning_curve.py `
  --no-memory-dir results/exp3_learning/no_memory `
  --with-memory-dir results/exp3_learning/with_memory `
  --plot `
  --output results/learning_curve_analysis.csv
```

---

## 📊 결과 확인

실험 완료 후 다음 파일들이 생성됩니다:

```
results/
├── exp1_no_memory/          # 실험 1 대조군
├── exp1_with_memory/        # 실험 1 실험군
├── exp2_rounds_1/           # 실험 2 (1 라운드)
├── exp2_rounds_2/           # 실험 2 (2 라운드)
├── exp2_rounds_3/           # 실험 2 (3 라운드)
├── exp3_learning/           # 실험 3
│   ├── no_memory/
│   └── with_memory/
├── analysis_rq1.png         # 실험 1 시각화
├── exp2_collaboration.png   # 실험 2 시각화
├── learning_curves.png      # 실험 3 시각화
└── learning_curve_analysis.csv
```

---

## 📈 예상 결과

### 실험 1: 메모리 효과
```
[ 기술 통계 ]
Metric          No Memory           With Memory         p-value
Total Return    5.2% ± 3.1%         8.7% ± 2.8%        0.023 *
Sharpe Ratio    0.45 ± 0.12         0.62 ± 0.09        0.008 **

✅ 메모리 사용 시 성과 향상 (p<0.05)
```

### 실험 2: 멀티 에이전트
```
Rounds    Mean Sharpe    Mean Return
1 Round      0.52          6.1%
2 Rounds     0.61          7.8%
3 Rounds     0.58          7.3%

✅ 2 라운드가 최적 (과도한 협업은 오히려 역효과)
```

### 실험 3: 학습 곡선
```
[ 구간별 성과 - 주 분석: use-memory의 시간대별 추이 ]
구간          Sharpe Ratio    해석
초기 (1~2월)     0.35       메모리 거의 없음
중기 (3~4월)     0.41       메모리 축적 중 (+17%)
후기 (5~6월)     0.49       메모리 충분 (+40%)

[ 회귀 분석: 시간 vs 성과 ]
메모리 사용: 기울기 +0.0675, p=0.002 **
  → ✅ 유의미한 학습 효과! (시간이 지날수록 성과 개선)

[ 대조군: no-memory ]
초기 0.32, 중기 0.32, 후기 0.32 (기울기 -0.0014, p=0.823)
  → 학습 효과 없음 (시간이 지나도 변화 없음)

결론: 메모리가 쌓일수록 (1월 → 6월) 성과가 점진적으로 향상됨!
```

---

## 📝 논문 작성 체크리스트

실험 완료 후:

- [ ] 실험 1 결과 → Table 1 (메모리 효과 비교)
- [ ] 실험 2 결과 → Table 2 (라운드별 성과)
- [ ] 실험 3 결과 → Table 3 (학습 곡선 분석)
- [ ] `analysis_rq1.png` → Figure 1 (Box Plot)
- [ ] `exp2_collaboration.png` → Figure 2 (라운드 비교)
- [ ] `learning_curves.png` → Figure 3 (학습 곡선)
- [ ] 통계 검정 결과 기술 (p-value, Cohen's d)
- [ ] Limitations 섹션 작성
- [ ] 재현성 정보 명시 (시드, LLM 모델 등)

---

## ⚠️ 메모리 초기화 (중요!)

### 왜 초기화가 필요한가?

**문제 상황:**
```
실험 1 (seed=0) → Redis에 메모리 저장
실험 1 (seed=1) → 이전 메모리(seed=0)가 남아있음!
                → 실험 독립성 위반 ❌
```

**해결:**
- **Redis 필수**: 각 실험 전 수동 초기화 필요!

### 메모리 초기화 방법
```powershell
# 전체 초기화 (권장)
python scripts/reset_memory.py --all

# Redis만 초기화
python scripts/reset_memory.py --redis

# 특정 ticker만 초기화
python scripts/reset_memory.py --ticker AAPL
```

---

## 🆘 문제 해결

### Ollama 연결 안 됨
```powershell
ollama serve
```

### 메모리 부족
```powershell
# 윈도우 크기 줄이기
--window 10  # 기본 30 → 10
```

### 실험 중단 후 재개
```powershell
# 이미 실행된 개수 확인
Get-ChildItem results/exp1_no_memory/*.json | Measure-Object

# 특정 시드만 재실행
for ($seed=5; $seed -le 9; $seed++) { ... }
```

### Redis 연결 실패
```powershell
# Redis 서버 실행 필요 (필수!)
# Docker 사용:
docker run -d -p 6379:6379 redis:latest

# 또는 Windows용 Redis 설치:
# https://github.com/microsoftarchive/redis/releases
```
**⚠️ Redis 없이는 시스템 실행 불가**

---

## 📚 더 자세한 내용

- **전체 가이드**: [EXPERIMENT_GUIDE.md](EXPERIMENT_GUIDE.md)
- **시스템 설명**: [README.md](README.md)
- **분석 코드**: `scripts/analyze_*.py`

---

## ⏱️ 실험 소요 시간

| 실험 | 조건 수 | 예상 시간 | 우선순위 |
|------|---------|-----------|----------|
| 실험 1 | 20회 | 2~4시간 | ⭐⭐⭐ 필수 |
| 실험 2 | 15회 | 1~2시간 | ⭐⭐ 중요 |
| 실험 3 | 10회 | 3~5시간 | ⭐⭐⭐ 필수 |

**총 소요 시간: 6~11시간** (하룻밤 실행 권장)

---

## 🎯 최소 실험 (시간 부족 시)

실험 1 + 실험 3만 실행하면 논문 작성 가능:
- 총 5~9시간
- 메모리 효과 + 학습 곡선 증명

---

**Good luck with your research!** 🎓

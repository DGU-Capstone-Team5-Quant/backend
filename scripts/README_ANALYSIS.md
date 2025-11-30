# 실험 결과 분석 가이드

## 📦 필수 패키지 설치

```bash
# 분석용 패키지 설치
pip install matplotlib seaborn scipy pandas numpy

# 또는 uv 사용
uv pip install matplotlib seaborn scipy pandas numpy
```

## 🚀 사용 방법

### 1. 기본 사용 (콘솔 출력만)

```bash
python scripts/analyze_experiments.py \
    --control-dir results/exp1_control \
    --treatment-dir results/exp1_treatment
```

**출력 예시:**
```
================================================================================
📊 실험 결과 비교 (Control vs Treatment)
================================================================================

📈 TOTAL RETURN
   Control:       0.0617 ± 0.0000
   Treatment:     0.0223 ± 0.0000
   차이:         -0.0394 (-63.86%) n.s.
   통계:      p=1.0000, Cohen's d=-inf (Negligible)

📈 SHARPE
   Control:       1.2641 ± 0.0000
   Treatment:     1.9573 ± 0.0000
   차이:         +0.6932 (+54.83%) n.s.
   통계:      p=1.0000, Cohen's d=+inf (Negligible)
...
```

### 2. 그래프 생성 + 결과 저장

```bash
python scripts/analyze_experiments.py \
    --control-dir results/exp1_control \
    --treatment-dir results/exp1_treatment \
    --output-dir results/analysis \
    --plot
```

**생성되는 파일:**
- `results/analysis/comparison_boxplot.png` - Box plot 비교
- `results/analysis/comparison_violin.png` - Violin plot (분포)
- `results/analysis/comparison_bar.png` - 평균 비교 bar chart
- `results/analysis/comparison_by_seed.png` - Seed별 추이
- `results/analysis/comparison_summary.csv` - 통계 요약표
- `results/analysis/comparison_table.tex` - 논문용 LaTeX 표
- `results/analysis/control_raw.csv` - Control 원본 데이터
- `results/analysis/treatment_raw.csv` - Treatment 원본 데이터

### 3. CSV만 내보내기 (그래프 없이)

```bash
python scripts/analyze_experiments.py \
    --control-dir results/exp1_control \
    --treatment-dir results/exp1_treatment \
    --output-dir results/analysis \
    --export
```

## 📊 출력 해석

### 통계 지표

| 지표 | 의미 |
|------|------|
| **Control Mean** | 메모리 미사용 그룹 평균 |
| **Treatment Mean** | 메모리 사용 그룹 평균 |
| **Improvement** | 절대값 개선량 |
| **Improvement %** | 퍼센트 개선율 |
| **p-value** | 통계적 유의성 (< 0.05면 유의) |
| **Cohen's d** | 효과 크기 (0.2=Small, 0.5=Medium, 0.8=Large) |
| **Significance** | *** p<0.001, ** p<0.01, * p<0.05, n.s.=not significant |

### 예시 해석

```
📈 SHARPE RATIO
   Control:       1.2641 ± 0.1234
   Treatment:     1.9573 ± 0.0987
   차이:         +0.6932 (+54.83%) **
   통계:      p=0.0023, Cohen's d=+1.25 (Large)
```

**해석:**
- 메모리 사용 시 Sharpe Ratio가 **평균 0.69 증가** (54.83% 향상)
- p=0.0023 < 0.01 → **통계적으로 매우 유의함** (**)
- Cohen's d=1.25 → **큰 효과 크기** (Large)
- **결론: 메모리가 리스크 조정 수익을 크게 개선함**

## 🔬 여러 Seed 실험 분석

### 실험 설정

```bash
# Seed 0~9로 실험 (각 10회)
for seed in 0 1 2 3 4 5 6 7 8 9; do
  # Control
  python scripts/run_backtest.py \
    --ticker AAPL \
    --seed $seed \
    --no-memory \
    --output-dir results/exp1_control_multi

  # Treatment (warmup + test)
  python scripts/reset_memory.py --all
  python scripts/run_backtest.py \
    --ticker AAPL \
    --seed $seed \
    --use-memory \
    --start-date 2025-01-01 --end-date 2025-08-31 \
    --output-dir results/exp1_warmup_multi

  python scripts/run_backtest.py \
    --ticker AAPL \
    --seed $seed \
    --use-memory \
    --start-date 2025-09-01 --end-date 2025-11-20 \
    --output-dir results/exp1_treatment_multi
done
```

### 분석

```bash
python scripts/analyze_experiments.py \
    --control-dir results/exp1_control_multi \
    --treatment-dir results/exp1_treatment_multi \
    --output-dir results/analysis_multi \
    --plot
```

## 📄 논문에 삽입하기

### 1. 표 삽입 (LaTeX)

생성된 `comparison_table.tex`를 논문에 직접 삽입:

```latex
\section{Results}

Table~\ref{tab:performance_comparison} shows the performance comparison between the control group (no memory) and the treatment group (with memory).

\input{results/analysis/comparison_table.tex}
```

### 2. 그래프 삽입

```latex
\begin{figure}[h]
\centering
\includegraphics[width=0.9\textwidth]{results/analysis/comparison_boxplot.png}
\caption{Performance comparison across different metrics. The treatment group (with memory) shows significantly higher Sharpe ratio despite lower total return, indicating better risk-adjusted performance.}
\label{fig:comparison}
\end{figure}
```

### 3. Excel/Google Sheets 사용

`comparison_summary.csv`를 Excel에서 열어 표 작성:

1. Excel에서 `comparison_summary.csv` 열기
2. 데이터 → 텍스트 나누기 → 쉼표로 구분
3. 표 서식 지정
4. 논문에 복사/붙여넣기

## 🎯 체크리스트

분석 전 확인사항:

- [ ] Control과 Treatment 디렉터리에 JSON 파일이 있는가?
- [ ] 최소 3개 이상의 seed 결과가 있는가? (통계적 검증)
- [ ] 필수 패키지가 설치되어 있는가? (matplotlib, seaborn)
- [ ] 결과 출력 디렉터리 경로가 올바른가?

## 🐛 문제 해결

### 문제 1: "No module named 'seaborn'"

```bash
pip install seaborn matplotlib scipy
```

### 문제 2: "디렉터리가 없습니다"

```bash
# 경로 확인
ls results/exp1_control
ls results/exp1_treatment

# 절대 경로 사용
python scripts/analyze_experiments.py \
    --control-dir c:/Users/user/Desktop/backend/results/exp1_control \
    --treatment-dir c:/Users/user/Desktop/backend/results/exp1_treatment
```

### 문제 3: "파일 로드 실패"

JSON 파일 형식 확인:
```bash
python -c "import json; json.load(open('results/exp1_control/backtest_AAPL_42_*.json'))"
```

## 📚 추가 분석

더 깊은 분석이 필요하면 Python에서 직접 사용:

```python
from scripts.analyze_experiments import load_results, extract_metrics, compare_groups

# 데이터 로드
control = load_results('results/exp1_control')
treatment = load_results('results/exp1_treatment')

# 메트릭 추출
df_control = extract_metrics(control)
df_treatment = extract_metrics(treatment)

# 커스텀 분석
print(df_control.describe())
print(df_treatment.describe())

# 비교
comparison = compare_groups(df_control, df_treatment)
print(comparison)
```

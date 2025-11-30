"""
실험 2: 멀티 에이전트 협업 효과 (RQ2) 분석 스크립트

Bull/Bear 라운드 수 변화(1, 2, 3)에 따른 성과 비교

사용예:
    python scripts/analyze_collaboration_effect.py \
        --rounds1-dir results/exp2_rounds_1 \
        --rounds2-dir results/exp2_rounds_2 \
        --rounds3-dir results/exp2_rounds_3 \
        --output-dir results/exp2_analysis \
        --plot

    # 결과만 출력 (그래프 없이)
    python scripts/analyze_collaboration_effect.py \
        --rounds1-dir results/exp2_rounds_1 \
        --rounds2-dir results/exp2_rounds_2 \
        --rounds3-dir results/exp2_rounds_3
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict

import pandas as pd
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt
import seaborn as sns

# Windows 인코딩 문제 해결
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_results(directory: str) -> List[Dict[str, Any]]:
    """디렉터리에서 모든 JSON 결과 파일 로드"""
    results = []
    path = Path(directory)

    if not path.exists():
        print(f"⚠️  디렉터리가 없습니다: {directory}")
        return results

    for json_file in path.glob("*.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                results.append({
                    'file': json_file.name,
                    'ticker': data.get('ticker'),
                    'seed': data.get('seed'),
                    'summary': data.get('summary', {}),
                    'trades': data.get('trades', []),
                    'start_date': data.get('start_date'),
                    'end_date': data.get('end_date'),
                })
        except Exception as e:
            print(f"⚠️  파일 로드 실패: {json_file.name} - {e}")

    return results


def extract_metrics(results: List[Dict[str, Any]], rounds: int) -> pd.DataFrame:
    """결과에서 주요 메트릭 추출"""
    rows = []

    for result in results:
        summary = result['summary']
        meta = summary.get('meta', {})

        row = {
            'ticker': result['ticker'],
            'seed': result['seed'],
            'rounds': rounds,
            'total_return': summary.get('total_return', 0),
            'sharpe': summary.get('sharpe', 0),
            'max_drawdown': summary.get('max_drawdown_pct', 0),
            'cagr': summary.get('cagr', 0),
            'volatility': summary.get('volatility', 0),
            'calmar': summary.get('calmar', 0),
            'trades_count': summary.get('trades_count', 0),
            'final_equity': summary.get('final_equity', 10000),
            'turnover_shares': summary.get('turnover_shares', 0),
        }
        rows.append(row)

    return pd.DataFrame(rows)


def perform_anova(df_all: pd.DataFrame, metric: str) -> Dict[str, Any]:
    """ANOVA 분석 수행 (3개 그룹 비교)"""
    rounds1 = df_all[df_all['rounds'] == 1][metric].values
    rounds2 = df_all[df_all['rounds'] == 2][metric].values
    rounds3 = df_all[df_all['rounds'] == 3][metric].values

    # One-way ANOVA
    f_stat, p_value = stats.f_oneway(rounds1, rounds2, rounds3)

    return {
        'metric': metric,
        'f_statistic': f_stat,
        'p_value': p_value,
        'significance': get_significance(p_value),
    }


def perform_posthoc_tukey(df_all: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Tukey HSD post-hoc test (쌍별 비교)"""
    from scipy.stats import ttest_ind

    results = []

    rounds_list = [1, 2, 3]

    for i, rounds_a in enumerate(rounds_list):
        for rounds_b in rounds_list[i+1:]:
            data_a = df_all[df_all['rounds'] == rounds_a][metric].values
            data_b = df_all[df_all['rounds'] == rounds_b][metric].values

            # t-test
            t_stat, p_value = ttest_ind(data_a, data_b)

            # 평균 차이
            mean_diff = np.mean(data_b) - np.mean(data_a)

            # Cohen's d
            effect_size = cohen_d(data_b, data_a)

            results.append({
                'comparison': f'{rounds_a} vs {rounds_b}',
                'mean_diff': mean_diff,
                't_statistic': t_stat,
                'p_value': p_value,
                'cohen_d': effect_size,
                'significance': get_significance(p_value),
            })

    return pd.DataFrame(results)


def cohen_d(x: np.ndarray, y: np.ndarray) -> float:
    """Cohen's d 효과 크기 계산"""
    nx, ny = len(x), len(y)
    if nx == 0 or ny == 0:
        return 0.0

    dof = nx + ny - 2
    pooled_std = np.sqrt(((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1)) / dof)

    if pooled_std == 0:
        return 0.0

    return (np.mean(x) - np.mean(y)) / pooled_std


def get_significance(p_value: float) -> str:
    """p-value를 유의성 기호로 변환"""
    if p_value < 0.001:
        return '***'
    elif p_value < 0.01:
        return '**'
    elif p_value < 0.05:
        return '*'
    else:
        return 'n.s.'


def print_summary_table(df_all: pd.DataFrame):
    """라운드별 요약 통계 출력"""
    print("\n" + "=" * 100)
    print("📊 실험 2: 멀티 에이전트 협업 효과 (RQ2)")
    print("=" * 100)
    print()
    print("💡 Bull/Bear 라운드 수 변화(1, 2, 3)에 따른 성과 비교")
    print("   - 1 라운드: Bull → Bear → Trader (최소 협업)")
    print("   - 2 라운드: Bull → Bear → Bull → Bear → Trader (중간 협업)")
    print("   - 3 라운드: Bull → Bear → Bull → Bear → Bull → Bear → Trader (최대 협업)")
    print()

    # 라운드별 요약 통계
    print("┌─ 📈 라운드별 성과 요약 ──────────────────────────────────────────────")
    print()

    metrics = ['total_return', 'sharpe', 'max_drawdown', 'cagr', 'volatility', 'calmar']
    metric_names = {
        'total_return': '총 수익률',
        'sharpe': '샤프 비율',
        'max_drawdown': '최대 낙폭 (%)',
        'cagr': '연환산 수익률 (CAGR)',
        'volatility': '변동성',
        'calmar': '칼마 비율',
    }

    for metric in metrics:
        print(f"【 {metric_names[metric]} 】")

        for rounds in [1, 2, 3]:
            data = df_all[df_all['rounds'] == rounds][metric]
            mean = data.mean()
            std = data.std()

            if metric == 'total_return' or metric == 'cagr':
                print(f"   {rounds} 라운드: {mean:>8.2%} ± {std:.4f}")
            elif metric == 'max_drawdown':
                print(f"   {rounds} 라운드: {mean:>8.2%} ± {std:.4f}")
            else:
                print(f"   {rounds} 라운드: {mean:>8.4f} ± {std:.4f}")

        print()

    print("└" + "─" * 75)
    print()


def print_anova_results(anova_results: List[Dict[str, Any]]):
    """ANOVA 결과 출력"""
    print("┌─ 📊 ANOVA 분석 결과 (3개 그룹 비교) ─────────────────────────────────")
    print()
    print("💡 귀무가설(H0): 라운드 수에 따른 성과 차이가 없다")
    print("   대립가설(H1): 적어도 하나의 그룹에서 유의미한 차이가 있다")
    print()

    for result in anova_results:
        metric = result['metric']
        f_stat = result['f_statistic']
        p_value = result['p_value']
        sig = result['significance']

        sig_emoji = "✅" if sig in ['*', '**', '***'] else "ℹ️"

        print(f"{sig_emoji} {metric.replace('_', ' ').title()}")
        print(f"   F-statistic: {f_stat:.4f}")
        print(f"   p-value: {p_value:.4f} {sig}")

        if sig in ['*', '**', '***']:
            print(f"   → 유의미한 차이 있음 (p < 0.05)")
        else:
            print(f"   → 유의미한 차이 없음 (p ≥ 0.05)")

        print()

    print("└" + "─" * 75)
    print()


def print_posthoc_results(metric: str, posthoc_df: pd.DataFrame):
    """Post-hoc 결과 출력"""
    print(f"   【 {metric.replace('_', ' ').title()} - 쌍별 비교 (Post-hoc) 】")
    print()

    for _, row in posthoc_df.iterrows():
        comparison = row['comparison']
        mean_diff = row['mean_diff']
        p_value = row['p_value']
        cohen_d_val = row['cohen_d']
        sig = row['significance']

        sig_emoji = "✅" if sig in ['*', '**', '***'] else "ℹ️"

        print(f"   {sig_emoji} {comparison}")
        print(f"      평균 차이: {mean_diff:+.6f}")
        print(f"      Cohen's d: {cohen_d_val:+.3f}")
        print(f"      p-value: {p_value:.4f} {sig}")
        print()


def create_comparison_plots(df_all: pd.DataFrame, output_dir: str):
    """라운드별 비교 그래프 생성"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 스타일 설정
    sns.set_style("whitegrid")
    plt.rcParams['figure.dpi'] = 300
    plt.rcParams['font.size'] = 10

    # 1. Line Plot: 라운드 수 vs 성과 (평균 + 표준오차)
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    metrics_plot = [
        ('total_return', 'Total Return'),
        ('sharpe', 'Sharpe Ratio'),
        ('max_drawdown', 'Max Drawdown (%)'),
        ('cagr', 'CAGR'),
    ]

    for idx, (metric, title) in enumerate(metrics_plot):
        # 라운드별 평균 및 표준오차
        means = df_all.groupby('rounds')[metric].mean()
        sems = df_all.groupby('rounds')[metric].sem()  # Standard Error of Mean

        # 라인 플롯
        axes[idx].plot(means.index, means.values, marker='o', linewidth=2,
                      markersize=8, color='#3498DB', label='Mean')

        # 에러바
        axes[idx].errorbar(means.index, means.values, yerr=sems.values,
                          fmt='none', ecolor='#E74C3C', capsize=5, alpha=0.7)

        # 개별 데이터 포인트
        for rounds in [1, 2, 3]:
            data = df_all[df_all['rounds'] == rounds][metric]
            x_jitter = rounds + np.random.normal(0, 0.05, size=len(data))
            axes[idx].scatter(x_jitter, data, alpha=0.3, s=30, color='gray')

        axes[idx].set_xlabel('Bull/Bear Rounds', fontweight='bold')
        axes[idx].set_ylabel(title, fontweight='bold')
        axes[idx].set_title(f'{title} by Collaboration Level', fontweight='bold')
        axes[idx].set_xticks([1, 2, 3])
        axes[idx].grid(True, alpha=0.3)
        axes[idx].legend()

    plt.tight_layout()
    plt.savefig(output_path / 'collaboration_line_plot.png', dpi=300, bbox_inches='tight')
    print(f"✅ 저장됨: {output_path / 'collaboration_line_plot.png'}")
    plt.close()

    # 2. Box Plot: 3개 그룹 비교
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))
    axes = axes.flatten()

    box_metrics = [
        ('total_return', 'Total Return'),
        ('sharpe', 'Sharpe Ratio'),
        ('max_drawdown', 'Max Drawdown (%)'),
        ('cagr', 'CAGR'),
        ('volatility', 'Volatility'),
        ('calmar', 'Calmar Ratio'),
    ]

    for idx, (metric, title) in enumerate(box_metrics):
        sns.boxplot(data=df_all, x='rounds', y=metric, ax=axes[idx],
                   palette=['#E74C3C', '#F39C12', '#3498DB'])
        sns.stripplot(data=df_all, x='rounds', y=metric, ax=axes[idx],
                     color='black', alpha=0.3, size=4)
        axes[idx].set_title(title, fontweight='bold')
        axes[idx].set_xlabel('Rounds', fontweight='bold')
        axes[idx].set_ylabel(title)
        axes[idx].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_path / 'collaboration_boxplot.png', dpi=300, bbox_inches='tight')
    print(f"✅ 저장됨: {output_path / 'collaboration_boxplot.png'}")
    plt.close()

    # 3. Violin Plot: 분포 비교
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    violin_metrics = [
        ('total_return', 'Total Return'),
        ('sharpe', 'Sharpe Ratio'),
        ('max_drawdown', 'Max Drawdown (%)'),
        ('volatility', 'Volatility'),
    ]

    for idx, (metric, title) in enumerate(violin_metrics):
        sns.violinplot(data=df_all, x='rounds', y=metric, ax=axes[idx],
                      palette=['#E74C3C', '#F39C12', '#3498DB'])
        axes[idx].set_title(title, fontweight='bold')
        axes[idx].set_xlabel('Rounds', fontweight='bold')
        axes[idx].set_ylabel(title)
        axes[idx].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_path / 'collaboration_violin.png', dpi=300, bbox_inches='tight')
    print(f"✅ 저장됨: {output_path / 'collaboration_violin.png'}")
    plt.close()

    # 4. Bar Chart: 평균 비교 (에러바 포함)
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    bar_metrics = [
        ('total_return', 'Total Return'),
        ('sharpe', 'Sharpe Ratio'),
        ('cagr', 'CAGR'),
        ('calmar', 'Calmar Ratio'),
    ]

    colors = ['#E74C3C', '#F39C12', '#3498DB']

    for idx, (metric, title) in enumerate(bar_metrics):
        means = df_all.groupby('rounds')[metric].mean()
        stds = df_all.groupby('rounds')[metric].std()

        x = np.arange(len(means))
        bars = axes[idx].bar(x, means.values, yerr=stds.values, capsize=5,
                            color=colors, alpha=0.7, edgecolor='black')

        axes[idx].set_xticks(x)
        axes[idx].set_xticklabels(['1 Round', '2 Rounds', '3 Rounds'])
        axes[idx].set_ylabel(title, fontweight='bold')
        axes[idx].set_title(f'{title} by Collaboration Level', fontweight='bold')
        axes[idx].grid(True, alpha=0.3, axis='y')

        # 값 표시
        for i, (mean, std) in enumerate(zip(means.values, stds.values)):
            axes[idx].text(i, mean + std, f'{mean:.4f}',
                          ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path / 'collaboration_bar.png', dpi=300, bbox_inches='tight')
    print(f"✅ 저장됨: {output_path / 'collaboration_bar.png'}")
    plt.close()

    # 5. Heatmap: 라운드 × Seed 성과 매트릭스
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Total Return 히트맵
    pivot_return = df_all.pivot_table(values='total_return', index='seed', columns='rounds')
    sns.heatmap(pivot_return, annot=True, fmt='.4f', cmap='RdYlGn',
               ax=axes[0], cbar_kws={'label': 'Total Return'})
    axes[0].set_title('Total Return by Seed and Rounds', fontweight='bold')
    axes[0].set_xlabel('Rounds', fontweight='bold')
    axes[0].set_ylabel('Seed', fontweight='bold')

    # Sharpe Ratio 히트맵
    pivot_sharpe = df_all.pivot_table(values='sharpe', index='seed', columns='rounds')
    sns.heatmap(pivot_sharpe, annot=True, fmt='.4f', cmap='RdYlGn',
               ax=axes[1], cbar_kws={'label': 'Sharpe Ratio'})
    axes[1].set_title('Sharpe Ratio by Seed and Rounds', fontweight='bold')
    axes[1].set_xlabel('Rounds', fontweight='bold')
    axes[1].set_ylabel('Seed', fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path / 'collaboration_heatmap.png', dpi=300, bbox_inches='tight')
    print(f"✅ 저장됨: {output_path / 'collaboration_heatmap.png'}")
    plt.close()


def export_results(df_all: pd.DataFrame, anova_results: List[Dict[str, Any]],
                   posthoc_results: Dict[str, pd.DataFrame], output_dir: str):
    """결과를 CSV로 내보내기"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. 전체 데이터
    df_all.to_csv(output_path / 'collaboration_raw_data.csv', index=False)
    print(f"✅ 저장됨: {output_path / 'collaboration_raw_data.csv'}")

    # 2. 라운드별 요약 통계
    summary = df_all.groupby('rounds').agg({
        'total_return': ['mean', 'std', 'min', 'max'],
        'sharpe': ['mean', 'std', 'min', 'max'],
        'max_drawdown': ['mean', 'std', 'min', 'max'],
        'cagr': ['mean', 'std', 'min', 'max'],
    })
    summary.to_csv(output_path / 'collaboration_summary.csv')
    print(f"✅ 저장됨: {output_path / 'collaboration_summary.csv'}")

    # 3. ANOVA 결과
    anova_df = pd.DataFrame(anova_results)
    anova_df.to_csv(output_path / 'anova_results.csv', index=False)
    print(f"✅ 저장됨: {output_path / 'anova_results.csv'}")

    # 4. Post-hoc 결과
    for metric, posthoc_df in posthoc_results.items():
        filename = f'posthoc_{metric}.csv'
        posthoc_df.to_csv(output_path / filename, index=False)
        print(f"✅ 저장됨: {output_path / filename}")

    # 5. 논문용 LaTeX 테이블
    latex_table = create_latex_table(df_all, anova_results)
    with open(output_path / 'collaboration_table.tex', 'w', encoding='utf-8') as f:
        f.write(latex_table)
    print(f"✅ 저장됨: {output_path / 'collaboration_table.tex'}")


def create_latex_table(df_all: pd.DataFrame, anova_results: List[Dict[str, Any]]) -> str:
    """논문용 LaTeX 테이블 생성"""
    latex = "\\begin{table}[h]\n"
    latex += "\\centering\n"
    latex += "\\caption{Multi-Agent Collaboration Effect: Performance by Bull/Bear Rounds}\n"
    latex += "\\label{tab:collaboration_effect}\n"
    latex += "\\begin{tabular}{lccccc}\n"
    latex += "\\hline\n"
    latex += "Metric & 1 Round & 2 Rounds & 3 Rounds & F-stat & p-value \\\\\n"
    latex += "\\hline\n"

    metrics = ['total_return', 'sharpe', 'max_drawdown', 'cagr']

    for metric in metrics:
        # 각 라운드별 평균 ± 표준편차
        r1_mean = df_all[df_all['rounds'] == 1][metric].mean()
        r1_std = df_all[df_all['rounds'] == 1][metric].std()
        r2_mean = df_all[df_all['rounds'] == 2][metric].mean()
        r2_std = df_all[df_all['rounds'] == 2][metric].std()
        r3_mean = df_all[df_all['rounds'] == 3][metric].mean()
        r3_std = df_all[df_all['rounds'] == 3][metric].std()

        # ANOVA 결과
        anova_row = next((r for r in anova_results if r['metric'] == metric), None)
        f_stat = anova_row['f_statistic'] if anova_row else 0
        p_value = anova_row['p_value'] if anova_row else 1.0

        metric_name = metric.replace('_', ' ').title()

        latex += f"{metric_name} & "
        latex += f"{r1_mean:.4f} $\\pm$ {r1_std:.4f} & "
        latex += f"{r2_mean:.4f} $\\pm$ {r2_std:.4f} & "
        latex += f"{r3_mean:.4f} $\\pm$ {r3_std:.4f} & "
        latex += f"{f_stat:.3f} & {p_value:.4f} \\\\\n"

    latex += "\\hline\n"
    latex += "\\end{tabular}\n"
    latex += "\\end{table}\n"

    return latex


def main():
    parser = argparse.ArgumentParser(
        description="실험 2: 멀티 에이전트 협업 효과 (RQ2) 분석"
    )
    parser.add_argument('--rounds1-dir', type=str, required=True,
                       help='1 라운드 결과 디렉터리')
    parser.add_argument('--rounds2-dir', type=str, required=True,
                       help='2 라운드 결과 디렉터리')
    parser.add_argument('--rounds3-dir', type=str, required=True,
                       help='3 라운드 결과 디렉터리')
    parser.add_argument('--output-dir', type=str, default='results/exp2_analysis',
                       help='출력 디렉터리')
    parser.add_argument('--plot', action='store_true', help='그래프 생성')
    parser.add_argument('--export', action='store_true', help='CSV/LaTeX 내보내기')

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("📊 실험 2 분석 시작: 멀티 에이전트 협업 효과 (RQ2)")
    print("=" * 80)

    # 1. 데이터 로드
    print(f"\n📂 1 라운드 로드: {args.rounds1_dir}")
    rounds1_results = load_results(args.rounds1_dir)
    print(f"   → {len(rounds1_results)}개 파일 로드됨")

    print(f"\n📂 2 라운드 로드: {args.rounds2_dir}")
    rounds2_results = load_results(args.rounds2_dir)
    print(f"   → {len(rounds2_results)}개 파일 로드됨")

    print(f"\n📂 3 라운드 로드: {args.rounds3_dir}")
    rounds3_results = load_results(args.rounds3_dir)
    print(f"   → {len(rounds3_results)}개 파일 로드됨")

    if not rounds1_results or not rounds2_results or not rounds3_results:
        print("\n❌ 일부 결과 파일이 없습니다. 경로를 확인하세요.")
        return

    # 2. 메트릭 추출
    df_rounds1 = extract_metrics(rounds1_results, rounds=1)
    df_rounds2 = extract_metrics(rounds2_results, rounds=2)
    df_rounds3 = extract_metrics(rounds3_results, rounds=3)

    # 3. 전체 데이터프레임 결합
    df_all = pd.concat([df_rounds1, df_rounds2, df_rounds3], ignore_index=True)

    # 4. 요약 통계 출력
    print_summary_table(df_all)

    # 5. ANOVA 분석
    print("┌─ 🔬 통계 분석 (ANOVA) ────────────────────────────────────────────")
    print()

    metrics_to_test = ['total_return', 'sharpe', 'max_drawdown', 'cagr', 'volatility']
    anova_results = []

    for metric in metrics_to_test:
        result = perform_anova(df_all, metric)
        anova_results.append(result)

    print_anova_results(anova_results)

    # 6. Post-hoc 분석 (유의미한 ANOVA만)
    print("┌─ 🔍 Post-hoc 분석 (쌍별 비교) ──────────────────────────────────────")
    print()

    posthoc_results = {}

    for result in anova_results:
        if result['significance'] in ['*', '**', '***']:
            metric = result['metric']
            posthoc_df = perform_posthoc_tukey(df_all, metric)
            posthoc_results[metric] = posthoc_df
            print_posthoc_results(metric, posthoc_df)

    if not posthoc_results:
        print("   ℹ️  유의미한 ANOVA 결과가 없어 Post-hoc 분석을 건너뜁니다.")
        print()

    print("└" + "─" * 75)
    print()

    # 7. 그래프 생성
    if args.plot:
        print("\n📊 그래프 생성 중...")
        create_comparison_plots(df_all, args.output_dir)

    # 8. 결과 내보내기
    if args.export or args.plot:
        print("\n💾 결과 내보내기 중...")
        export_results(df_all, anova_results, posthoc_results, args.output_dir)

    print("\n✅ 분석 완료!")
    print(f"📁 결과 저장 위치: {args.output_dir}")
    print()
    print("📌 통계적 유의성: *** p<0.001, ** p<0.01, * p<0.05, n.s. = 유의하지 않음")
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()

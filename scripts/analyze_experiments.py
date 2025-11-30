"""
실험 결과 분석 및 논문용 표/그래프 생성 스크립트

사용예:
    # 실험 1: Control vs Treatment 비교
    python scripts/analyze_experiments.py \
        --control-dir results/exp1_control \
        --treatment-dir results/exp1_treatment \
        --output-dir results/analysis \
        --plot

    # 결과만 출력 (그래프 없이)
    python scripts/analyze_experiments.py \
        --control-dir results/exp1_control \
        --treatment-dir results/exp1_treatment
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
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
    """디렉터리에서 모든 JSON 결과 파일 로드 (trades 포함)"""
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


def extract_metrics(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """결과에서 주요 메트릭 추출"""
    rows = []

    for result in results:
        summary = result['summary']
        meta = summary.get('meta', {})

        row = {
            'ticker': result['ticker'],
            'seed': result['seed'],
            'total_return': summary.get('total_return', 0),
            'sharpe': summary.get('sharpe', 0),
            'max_drawdown': summary.get('max_drawdown_pct', 0),
            'cagr': summary.get('cagr', 0),
            'volatility': summary.get('volatility', 0),
            'calmar': summary.get('calmar', 0),
            'trades_count': summary.get('trades_count', 0),
            'final_equity': summary.get('final_equity', 10000),
            'use_memory': meta.get('use_memory', False),
        }
        rows.append(row)

    return pd.DataFrame(rows)


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


def compare_groups(df_control: pd.DataFrame, df_treatment: pd.DataFrame) -> pd.DataFrame:
    """Control vs Treatment 그룹 비교"""
    # 수익률 관련 메트릭을 먼저 배치
    metrics = ['total_return', 'cagr', 'sharpe', 'calmar', 'max_drawdown', 'volatility', 'trades_count']

    results = []

    for metric in metrics:
        control_vals = df_control[metric].values
        treatment_vals = df_treatment[metric].values

        # 기술 통계
        control_mean = np.mean(control_vals)
        control_std = np.std(control_vals, ddof=1) if len(control_vals) > 1 else 0
        treatment_mean = np.mean(treatment_vals)
        treatment_std = np.std(treatment_vals, ddof=1) if len(treatment_vals) > 1 else 0

        # 통계 검정
        if len(control_vals) > 1 and len(treatment_vals) > 1:
            t_stat, p_value = stats.ttest_ind(treatment_vals, control_vals)
            effect_size = cohen_d(treatment_vals, control_vals)
        else:
            t_stat, p_value, effect_size = 0, 1.0, 0.0

        # 개선율
        improvement = treatment_mean - control_mean
        if control_mean != 0:
            improvement_pct = (improvement / abs(control_mean)) * 100
        else:
            improvement_pct = 0

        results.append({
            'metric': metric,
            'control_mean': control_mean,
            'control_std': control_std,
            'treatment_mean': treatment_mean,
            'treatment_std': treatment_std,
            'improvement': improvement,
            'improvement_pct': improvement_pct,
            't_statistic': t_stat,
            'p_value': p_value,
            'cohen_d': effect_size,
            'significance': get_significance(p_value),
        })

    return pd.DataFrame(results)


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


def get_effect_size_label(d: float) -> str:
    """Cohen's d를 효과 크기 레이블로 변환"""
    abs_d = abs(d)
    if abs_d > 0.8:
        return 'Large'
    elif abs_d > 0.5:
        return 'Medium'
    elif abs_d > 0.2:
        return 'Small'
    else:
        return 'Negligible'


def print_comparison_table(comparison: pd.DataFrame):
    """비교 결과를 보기 좋게 출력"""
    print("\n" + "=" * 100)
    print("📊 실험 결과 비교: 메모리 미사용 vs 메모리 사용")
    print("=" * 100)
    print()
    print("💡 이 분석은 메모리 기능의 효과를 통계적으로 검증합니다.")
    print("   - p-value가 0.05 미만이면 통계적으로 유의미한 차이가 있다는 의미입니다.")
    print("   - 개선율(%)이 양수면 메모리 사용 시 성능이 더 좋다는 의미입니다.")
    print()

    # 메트릭 이름 매핑
    metric_names = {
        'total_return': '총 수익률',
        'cagr': '연환산 수익률 (CAGR)',
        'sharpe': '샤프 비율 (위험대비 수익)',
        'calmar': '칼마 비율',
        'max_drawdown': '최대 낙폭 (%)',
        'volatility': '변동성',
        'trades_count': '거래 횟수',
    }

    # 수익률 관련 메트릭 먼저 출력
    print("┌─ 📈 수익률 메트릭 ────────────────────────────────────────────────────")
    print()

    for _, row in comparison.iterrows():
        metric = row['metric']
        if metric not in ['total_return', 'cagr']:
            continue

        metric_name = metric_names.get(metric, metric)
        control = row['control_mean']
        treatment = row['treatment_mean']
        improvement_pct = row['improvement_pct']
        sig = row['significance']

        # 유의성에 따른 이모지
        sig_emoji = "✅" if sig in ['*', '**', '***'] else "ℹ️"

        print(f"{sig_emoji} {metric_name}")
        print(f"   메모리 미사용: {control:>8.2%}")
        print(f"   메모리 사용:   {treatment:>8.2%}")
        print(f"   개선:          {improvement_pct:>+8.2f}% {sig}")
        print()

    # 리스크 관련 메트릭
    print("├─ ⚖️  리스크 조정 메트릭 ──────────────────────────────────────────────")
    print()

    for _, row in comparison.iterrows():
        metric = row['metric']
        if metric not in ['sharpe', 'calmar', 'max_drawdown', 'volatility']:
            continue

        metric_name = metric_names.get(metric, metric)
        control = row['control_mean']
        treatment = row['treatment_mean']
        improvement_pct = row['improvement_pct']
        sig = row['significance']

        sig_emoji = "✅" if sig in ['*', '**', '***'] else "ℹ️"

        # max_drawdown과 volatility는 낮을수록 좋음
        if metric in ['max_drawdown', 'volatility']:
            format_str = "{:>8.2%}" if metric == 'max_drawdown' else "{:>8.4f}"
            print(f"{sig_emoji} {metric_name} (낮을수록 좋음)")
            print(f"   메모리 미사용: {format_str.format(control)}")
            print(f"   메모리 사용:   {format_str.format(treatment)}")
        else:
            print(f"{sig_emoji} {metric_name}")
            print(f"   메모리 미사용: {control:>8.2f}")
            print(f"   메모리 사용:   {treatment:>8.2f}")

        print(f"   개선:          {improvement_pct:>+8.2f}% {sig}")
        print()

    # 거래 관련
    print("├─ 📊 거래 활동 ───────────────────────────────────────────────────────")
    print()

    for _, row in comparison.iterrows():
        metric = row['metric']
        if metric != 'trades_count':
            continue

        metric_name = metric_names.get(metric, metric)
        control = row['control_mean']
        treatment = row['treatment_mean']
        improvement_pct = row['improvement_pct']
        sig = row['significance']

        sig_emoji = "✅" if sig in ['*', '**', '***'] else "ℹ️"

        print(f"{sig_emoji} {metric_name}")
        print(f"   메모리 미사용: {int(control):>8d}")
        print(f"   메모리 사용:   {int(treatment):>8d}")
        print(f"   개선:          {improvement_pct:>+8.2f}% {sig}")
        print()

    print("└" + "─" * 75)
    print()
    print("📌 통계적 유의성: *** p<0.001, ** p<0.01, * p<0.05, n.s. = 유의하지 않음")
    print("=" * 100)


def extract_equity_curves(results: List[Dict[str, Any]]) -> Dict[str, pd.DataFrame]:
    """각 실험의 equity curve 추출"""
    equity_curves = {}

    for result in results:
        trades = result.get('trades', [])
        if not trades:
            continue

        # trades에서 시간과 equity 추출
        timestamps = [trade['ts'] for trade in trades]
        equities = [trade['equity'] for trade in trades]

        df = pd.DataFrame({
            'timestamp': pd.to_datetime(timestamps),
            'equity': equities
        })

        # 초기 자본 대비 수익률로 변환
        initial_equity = equities[0] if equities else 10000
        df['return_pct'] = (df['equity'] / initial_equity - 1) * 100

        key = f"{result['ticker']}_{result['seed']}"
        equity_curves[key] = df

    return equity_curves


def create_equity_comparison_plot(control_results: List[Dict[str, Any]],
                                   treatment_results: List[Dict[str, Any]],
                                   output_dir: str):
    """날짜별 수익률 비교 그래프 생성"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Equity curves 추출
    control_curves = extract_equity_curves(control_results)
    treatment_curves = extract_equity_curves(treatment_results)

    if not control_curves or not treatment_curves:
        print("⚠️  Equity curve 데이터가 없습니다.")
        return

    # 그래프 생성
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))

    # 1. 개별 곡선 비교
    ax1 = axes[0]

    # Control 그룹
    for key, df in control_curves.items():
        ax1.plot(df['timestamp'], df['return_pct'],
                color='#E74C3C', alpha=0.3, linewidth=1)

    # Treatment 그룹
    for key, df in treatment_curves.items():
        ax1.plot(df['timestamp'], df['return_pct'],
                color='#3498DB', alpha=0.3, linewidth=1)

    # 범례용 더미 라인
    ax1.plot([], [], color='#E74C3C', label='No Memory', linewidth=2)
    ax1.plot([], [], color='#3498DB', label='With Memory', linewidth=2)

    ax1.set_xlabel('Date')
    ax1.set_ylabel('Return (%)')
    ax1.set_title('Return Over Time (Individual Experiments)', fontweight='bold', fontsize=12)
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='black', linestyle='--', linewidth=0.5)

    # 2. 평균 곡선 비교
    ax2 = axes[1]

    # 시간대를 통일하기 위해 리샘플링
    def get_average_curve(curves_dict):
        all_dfs = []
        for key, df in curves_dict.items():
            df_copy = df.copy()
            df_copy = df_copy.set_index('timestamp')
            all_dfs.append(df_copy)

        if not all_dfs:
            return None

        # 공통 시간 범위 찾기
        min_time = max(df.index.min() for df in all_dfs)
        max_time = min(df.index.max() for df in all_dfs)

        # 리샘플링하여 평균 계산
        resampled = []
        for df in all_dfs:
            df_range = df[(df.index >= min_time) & (df.index <= max_time)]
            resampled.append(df_range.resample('1h').mean().interpolate())

        # 모든 데이터프레임을 합쳐서 평균 계산
        combined = pd.concat(resampled, axis=1)
        mean_curve = combined.mean(axis=1)
        std_curve = combined.std(axis=1)

        return mean_curve, std_curve

    control_avg = get_average_curve(control_curves)
    treatment_avg = get_average_curve(treatment_curves)

    if control_avg and treatment_avg:
        control_mean, control_std = control_avg
        treatment_mean, treatment_std = treatment_avg

        # 평균 곡선
        ax2.plot(control_mean.index, control_mean,
                color='#E74C3C', label='No Memory (Mean)', linewidth=2)
        ax2.plot(treatment_mean.index, treatment_mean,
                color='#3498DB', label='With Memory (Mean)', linewidth=2)

        # 신뢰 구간
        ax2.fill_between(control_mean.index,
                        control_mean - control_std,
                        control_mean + control_std,
                        color='#E74C3C', alpha=0.2)
        ax2.fill_between(treatment_mean.index,
                        treatment_mean - treatment_std,
                        treatment_mean + treatment_std,
                        color='#3498DB', alpha=0.2)

    ax2.set_xlabel('Date')
    ax2.set_ylabel('Return (%)')
    ax2.set_title('Average Return Over Time (with Confidence Interval)', fontweight='bold', fontsize=12)
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.5)

    plt.tight_layout()
    plt.savefig(output_path / 'equity_curve_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✅ 저장됨: {output_path / 'equity_curve_comparison.png'}")
    plt.close()


def create_comparison_plots(df_control: pd.DataFrame, df_treatment: pd.DataFrame, output_dir: str):
    """비교 그래프 생성"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 스타일 설정
    sns.set_style("whitegrid")
    plt.rcParams['figure.dpi'] = 300
    plt.rcParams['font.size'] = 10

    # 데이터 준비
    df_control['group'] = 'No Memory'
    df_treatment['group'] = 'With Memory'
    df_combined = pd.concat([df_control, df_treatment], ignore_index=True)

    # 1. Box Plot: Total Return, Sharpe, Max Drawdown
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    metrics_plot = [
        ('total_return', 'Total Return', axes[0]),
        ('sharpe', 'Sharpe Ratio', axes[1]),
        ('max_drawdown', 'Max Drawdown (%)', axes[2]),
    ]

    for metric, title, ax in metrics_plot:
        sns.boxplot(data=df_combined, x='group', y=metric, ax=ax, palette=['#E74C3C', '#3498DB'])
        sns.stripplot(data=df_combined, x='group', y=metric, ax=ax,
                     color='black', alpha=0.3, size=4)
        ax.set_title(title, fontweight='bold')
        ax.set_xlabel('')
        ax.set_ylabel(title)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path / 'comparison_boxplot.png', dpi=300, bbox_inches='tight')
    print(f"✅ 저장됨: {output_path / 'comparison_boxplot.png'}")
    plt.close()

    # 2. Violin Plot: 분포 비교
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()

    violin_metrics = [
        ('total_return', 'Total Return'),
        ('sharpe', 'Sharpe Ratio'),
        ('max_drawdown', 'Max Drawdown (%)'),
        ('volatility', 'Volatility'),
    ]

    for idx, (metric, title) in enumerate(violin_metrics):
        sns.violinplot(data=df_combined, x='group', y=metric, ax=axes[idx], palette=['#E74C3C', '#3498DB'])
        axes[idx].set_title(title, fontweight='bold')
        axes[idx].set_xlabel('')
        axes[idx].set_ylabel(title)
        axes[idx].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_path / 'comparison_violin.png', dpi=300, bbox_inches='tight')
    print(f"✅ 저장됨: {output_path / 'comparison_violin.png'}")
    plt.close()

    # 3. Bar Chart: 평균 비교
    comparison_metrics = ['total_return', 'sharpe', 'max_drawdown', 'cagr']

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()

    for idx, metric in enumerate(comparison_metrics):
        means = df_combined.groupby('group')[metric].mean()
        stds = df_combined.groupby('group')[metric].std()

        x = np.arange(len(means))
        axes[idx].bar(x, means.values, yerr=stds.values, capsize=5,
                     color=['#E74C3C', '#3498DB'], alpha=0.7, edgecolor='black')
        axes[idx].set_xticks(x)
        axes[idx].set_xticklabels(means.index)
        axes[idx].set_ylabel(metric.replace('_', ' ').title())
        axes[idx].set_title(f'{metric.replace("_", " ").title()} Comparison', fontweight='bold')
        axes[idx].grid(True, alpha=0.3, axis='y')

        # 값 표시
        for i, (mean, std) in enumerate(zip(means.values, stds.values)):
            axes[idx].text(i, mean + std, f'{mean:.4f}', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig(output_path / 'comparison_bar.png', dpi=300, bbox_inches='tight')
    print(f"✅ 저장됨: {output_path / 'comparison_bar.png'}")
    plt.close()

    # 4. Seed별 비교 (라인 플롯)
    if 'seed' in df_combined.columns and df_combined['seed'].notna().any():
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Total Return by Seed
        for group in ['No Memory', 'With Memory']:
            data = df_combined[df_combined['group'] == group].sort_values('seed')
            axes[0].plot(data['seed'], data['total_return'], marker='o', label=group, linewidth=2)

        axes[0].set_xlabel('Seed')
        axes[0].set_ylabel('Total Return')
        axes[0].set_title('Total Return by Seed', fontweight='bold')
        axes[0].legend()
        axes[0].grid(True, alpha=0.3)

        # Sharpe by Seed
        for group in ['No Memory', 'With Memory']:
            data = df_combined[df_combined['group'] == group].sort_values('seed')
            axes[1].plot(data['seed'], data['sharpe'], marker='o', label=group, linewidth=2)

        axes[1].set_xlabel('Seed')
        axes[1].set_ylabel('Sharpe Ratio')
        axes[1].set_title('Sharpe Ratio by Seed', fontweight='bold')
        axes[1].legend()
        axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_path / 'comparison_by_seed.png', dpi=300, bbox_inches='tight')
        print(f"✅ 저장됨: {output_path / 'comparison_by_seed.png'}")
        plt.close()


def export_results(comparison: pd.DataFrame, df_control: pd.DataFrame, df_treatment: pd.DataFrame, output_dir: str):
    """결과를 CSV로 내보내기"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. 비교 결과 테이블
    comparison.to_csv(output_path / 'comparison_summary.csv', index=False)
    print(f"✅ 저장됨: {output_path / 'comparison_summary.csv'}")

    # 2. 논문용 LaTeX 테이블
    latex_table = create_latex_table(comparison)
    with open(output_path / 'comparison_table.tex', 'w', encoding='utf-8') as f:
        f.write(latex_table)
    print(f"✅ 저장됨: {output_path / 'comparison_table.tex'}")

    # 3. Raw data
    df_control.to_csv(output_path / 'control_raw.csv', index=False)
    df_treatment.to_csv(output_path / 'treatment_raw.csv', index=False)
    print(f"✅ 저장됨: {output_path / 'control_raw.csv'}")
    print(f"✅ 저장됨: {output_path / 'treatment_raw.csv'}")


def create_latex_table(comparison: pd.DataFrame) -> str:
    """논문용 LaTeX 테이블 생성"""
    latex = "\\begin{table}[h]\n"
    latex += "\\centering\n"
    latex += "\\caption{Performance Comparison: Control vs Treatment}\n"
    latex += "\\label{tab:performance_comparison}\n"
    latex += "\\begin{tabular}{lcccccc}\n"
    latex += "\\hline\n"
    latex += "Metric & No Memory & With Memory & Improvement & p-value & Cohen's d & Sig. \\\\\n"
    latex += "\\hline\n"

    for _, row in comparison.iterrows():
        metric = row['metric'].replace('_', ' ').title()
        control = f"{row['control_mean']:.4f} $\\pm$ {row['control_std']:.4f}"
        treatment = f"{row['treatment_mean']:.4f} $\\pm$ {row['treatment_std']:.4f}"
        improvement = f"{row['improvement']:+.4f} ({row['improvement_pct']:+.2f}\\%)"
        p_value = f"{row['p_value']:.4f}"
        cohen_d = f"{row['cohen_d']:+.3f}"
        sig = row['significance']

        latex += f"{metric} & {control} & {treatment} & {improvement} & {p_value} & {cohen_d} & {sig} \\\\\n"

    latex += "\\hline\n"
    latex += "\\end{tabular}\n"
    latex += "\\end{table}\n"

    return latex


def main():
    parser = argparse.ArgumentParser(description="실험 결과 분석 및 논문용 표/그래프 생성")
    parser.add_argument('--control-dir', type=str, required=True, help='Control 그룹 결과 디렉터리')
    parser.add_argument('--treatment-dir', type=str, required=True, help='Treatment 그룹 결과 디렉터리')
    parser.add_argument('--output-dir', type=str, default='results/analysis', help='출력 디렉터리')
    parser.add_argument('--plot', action='store_true', help='그래프 생성')
    parser.add_argument('--export', action='store_true', help='CSV/LaTeX 내보내기')

    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("📊 실험 결과 분석 시작")
    print("=" * 80)

    # 1. 데이터 로드
    print(f"\n📂 Control 그룹 로드: {args.control_dir}")
    control_results = load_results(args.control_dir)
    print(f"   → {len(control_results)}개 파일 로드됨")

    print(f"\n📂 Treatment 그룹 로드: {args.treatment_dir}")
    treatment_results = load_results(args.treatment_dir)
    print(f"   → {len(treatment_results)}개 파일 로드됨")

    if not control_results or not treatment_results:
        print("\n❌ 결과 파일이 없습니다. 경로를 확인하세요.")
        return

    # 2. 메트릭 추출
    df_control = extract_metrics(control_results)
    df_treatment = extract_metrics(treatment_results)

    # 3. 비교 분석
    comparison = compare_groups(df_control, df_treatment)

    # 4. 결과 출력
    print_comparison_table(comparison)

    # 5. 그래프 생성
    if args.plot:
        print("\n📊 그래프 생성 중...")

        # 날짜별 수익률 비교 그래프 (새로 추가)
        print("   → 날짜별 수익률 비교 그래프...")
        create_equity_comparison_plot(control_results, treatment_results, args.output_dir)

        # 기존 박스플롯 등
        print("   → 성과 분포 그래프...")
        create_comparison_plots(df_control, df_treatment, args.output_dir)

    # 6. 결과 내보내기
    if args.export or args.plot:  # plot이면 자동으로 export도 실행
        print("\n💾 결과 내보내기 중...")
        export_results(comparison, df_control, df_treatment, args.output_dir)

    print("\n✅ 분석 완료!")
    print(f"📁 결과 저장 위치: {args.output_dir}")
    print()


if __name__ == "__main__":
    main()

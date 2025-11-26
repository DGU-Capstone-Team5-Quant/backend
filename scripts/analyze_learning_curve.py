"""
학습 곡선 분석 스크립트 (RQ3: Cumulative Learning Effect)

거래가 누적될수록 성과가 개선되는지 분석합니다.

사용예:
    python scripts/analyze_learning_curve.py \
        --no-memory-dir results/exp3_learning/no_memory \
        --with-memory-dir results/exp3_learning/with_memory \
        --plot \
        --output results/learning_curve_analysis.csv
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

import pandas as pd
import numpy as np
from scipy import stats


def load_trades_from_json(json_file: Path) -> pd.DataFrame:
    """JSON 파일에서 거래 내역 로드"""
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    trades = data.get("trades", [])
    if not trades:
        return pd.DataFrame()

    df = pd.DataFrame(trades)

    # 타임스탬프 변환
    if "ts" in df.columns:
        df["ts"] = pd.to_datetime(df["ts"])
        df = df.sort_values("ts")

    # 메타데이터 추가
    df["ticker"] = data.get("ticker", "UNKNOWN")
    df["seed"] = data.get("seed")
    df["use_memory"] = data.get("use_memory")

    return df


def load_all_trades(exp_dir: Path) -> pd.DataFrame:
    """실험 디렉터리의 모든 거래 내역 로드"""
    all_trades = []

    json_files = list(exp_dir.glob("*.json"))
    if not json_files:
        json_files = list(exp_dir.rglob("*.json"))

    print(f"  발견된 파일: {len(json_files)}개")

    for json_file in json_files:
        try:
            df_trades = load_trades_from_json(json_file)
            if not df_trades.empty:
                # 각 실행마다 고유 ID
                df_trades["run_id"] = f"{df_trades['ticker'].iloc[0]}_{df_trades['seed'].iloc[0]}"
                all_trades.append(df_trades)
        except Exception as e:
            print(f"  ⚠️  파일 로드 실패: {json_file.name} - {e}")
            continue

    if not all_trades:
        return pd.DataFrame()

    return pd.concat(all_trades, ignore_index=True)


def split_into_periods(df: pd.DataFrame, n_periods: int = 3) -> List[pd.DataFrame]:
    """
    거래 내역을 n개 구간으로 분할 (초기/중기/후기)

    Args:
        df: 거래 내역 DataFrame (단일 run)
        n_periods: 구간 수 (기본 3)

    Returns:
        [초기 df, 중기 df, 후기 df]
    """
    n_trades = len(df)
    period_size = n_trades // n_periods

    periods = []
    for i in range(n_periods):
        start_idx = i * period_size
        if i == n_periods - 1:
            # 마지막 구간은 나머지 전부
            end_idx = n_trades
        else:
            end_idx = (i + 1) * period_size

        periods.append(df.iloc[start_idx:end_idx].copy())

    return periods


def calculate_period_metrics(df: pd.DataFrame) -> Dict[str, float]:
    """
    특정 구간의 성과 메트릭 계산

    Returns:
        {
            'total_return': 구간 총 수익률,
            'sharpe': 구간 Sharpe Ratio,
            'win_rate': 승률,
            'avg_pnl': 평균 PnL,
            'n_trades': 거래 수
        }
    """
    if df.empty or "pnl" not in df.columns:
        return {
            "total_return": 0.0,
            "sharpe": 0.0,
            "win_rate": 0.0,
            "avg_pnl": 0.0,
            "n_trades": 0,
        }

    pnls = df["pnl"].values
    n_trades = len(pnls)

    # 총 수익률 (누적 PnL / 초기 equity)
    if "equity" in df.columns and len(df) > 0:
        initial_equity = df.iloc[0]["equity"] - df.iloc[0]["pnl"]  # 첫 거래 전 equity
        final_equity = df.iloc[-1]["equity"]
        total_return = (final_equity - initial_equity) / initial_equity if initial_equity > 0 else 0.0
    else:
        total_return = pnls.sum() / 10000.0  # 가정: 초기 자본 10000

    # Sharpe Ratio
    if len(pnls) > 1:
        mean_pnl = pnls.mean()
        std_pnl = pnls.std(ddof=1)
        sharpe = mean_pnl / std_pnl * np.sqrt(len(pnls)) if std_pnl > 0 else 0.0
    else:
        sharpe = 0.0

    # 승률
    wins = (pnls > 0).sum()
    win_rate = wins / n_trades if n_trades > 0 else 0.0

    # 평균 PnL
    avg_pnl = pnls.mean()

    return {
        "total_return": total_return,
        "sharpe": sharpe,
        "win_rate": win_rate,
        "avg_pnl": avg_pnl,
        "n_trades": n_trades,
    }


def analyze_learning_curve(df_trades: pd.DataFrame, n_periods: int = 3) -> pd.DataFrame:
    """
    각 run별로 학습 곡선 분석

    Returns:
        DataFrame with columns: run_id, ticker, seed, use_memory, period, total_return, sharpe, win_rate, ...
    """
    results = []

    for run_id, group in df_trades.groupby("run_id"):
        group = group.sort_values("ts") if "ts" in group.columns else group
        periods = split_into_periods(group, n_periods)

        ticker = group["ticker"].iloc[0]
        seed = group["seed"].iloc[0]
        use_memory = group["use_memory"].iloc[0]

        for period_idx, period_df in enumerate(periods):
            metrics = calculate_period_metrics(period_df)
            metrics["run_id"] = run_id
            metrics["ticker"] = ticker
            metrics["seed"] = seed
            metrics["use_memory"] = use_memory
            metrics["period"] = period_idx + 1  # 1, 2, 3
            metrics["period_label"] = ["Early", "Mid", "Late"][period_idx]

            results.append(metrics)

    return pd.DataFrame(results)


def regression_analysis(df_periods: pd.DataFrame) -> Dict[str, Any]:
    """
    시간(period)에 따른 성과 변화 회귀 분석

    Returns:
        {
            'no_memory': {'slope', 'intercept', 'r_squared', 'p_value'},
            'with_memory': {...}
        }
    """
    results = {}

    for use_memory in [False, True]:
        df_subset = df_periods[df_periods["use_memory"] == use_memory]

        if df_subset.empty:
            continue

        # X: period (1, 2, 3), Y: sharpe ratio
        X = df_subset["period"].values
        Y = df_subset["sharpe"].values

        if len(X) < 2:
            continue

        # 선형 회귀
        slope, intercept, r_value, p_value, std_err = stats.linregress(X, Y)

        label = "with_memory" if use_memory else "no_memory"
        results[label] = {
            "slope": slope,
            "intercept": intercept,
            "r_squared": r_value**2,
            "p_value": p_value,
            "std_err": std_err,
        }

    return results


def print_learning_analysis(df_periods: pd.DataFrame):
    """학습 효과 분석 결과 출력"""
    print("\n" + "=" * 80)
    print("📈 학습 곡선 분석 (RQ3: Cumulative Learning Effect)")
    print("=" * 80)

    # 1. 구간별 평균 성과
    print("\n[ 구간별 평균 성과 ]")
    summary = df_periods.groupby(["use_memory", "period_label"])[["sharpe", "total_return", "win_rate"]].mean()
    print(summary.to_string())

    # 2. 메모리 유무별 추세 분석
    print("\n[ 메모리별 학습 추세 ]")
    for use_memory in [False, True]:
        label = "메모리 사용" if use_memory else "메모리 미사용"
        df_subset = df_periods[df_periods["use_memory"] == use_memory]

        if df_subset.empty:
            continue

        # 초기 vs 후기 비교
        early = df_subset[df_subset["period_label"] == "Early"]["sharpe"].mean()
        late = df_subset[df_subset["period_label"] == "Late"]["sharpe"].mean()
        improvement = late - early
        improvement_pct = improvement / abs(early) * 100 if early != 0 else 0

        print(f"\n{label}:")
        print(f"  초기 Sharpe: {early:.4f}")
        print(f"  후기 Sharpe: {late:.4f}")
        print(f"  개선: {improvement:+.4f} ({improvement_pct:+.2f}%)")

    # 3. 회귀 분석
    print("\n[ 회귀 분석: 시간(period) → 성과(sharpe) ]")
    regression_results = regression_analysis(df_periods)

    for label, res in regression_results.items():
        mem_label = "메모리 사용" if "with" in label else "메모리 미사용"
        print(f"\n{mem_label}:")
        print(f"  기울기 (slope): {res['slope']:.6f}")
        print(f"  절편 (intercept): {res['intercept']:.6f}")
        print(f"  R²: {res['r_squared']:.4f}")
        print(f"  p-value: {res['p_value']:.6f}")

        if res["p_value"] < 0.05:
            if res["slope"] > 0:
                print(f"  ✅ 유의미한 학습 효과 (p<0.05, 기울기>0)")
            else:
                print(f"  ⚠️  유의미한 성과 감소 (p<0.05, 기울기<0)")
        else:
            print(f"  ❌ 학습 효과 없음 (p≥0.05)")

    # 4. t-test: 메모리 유무별 후기 성과 비교
    print("\n[ t-test: 후기 구간 성과 비교 ]")
    late_no_mem = df_periods[(df_periods["use_memory"] == False) & (df_periods["period_label"] == "Late")]["sharpe"]
    late_with_mem = df_periods[(df_periods["use_memory"] == True) & (df_periods["period_label"] == "Late")]["sharpe"]

    if len(late_no_mem) > 0 and len(late_with_mem) > 0:
        t_stat, p_value = stats.ttest_ind(late_with_mem, late_no_mem)
        print(f"  메모리 미사용 (후기 Sharpe): {late_no_mem.mean():.4f} ± {late_no_mem.std():.4f}")
        print(f"  메모리 사용 (후기 Sharpe): {late_with_mem.mean():.4f} ± {late_with_mem.std():.4f}")
        print(f"  t-statistic: {t_stat:.4f}")
        print(f"  p-value: {p_value:.4f}")

        if p_value < 0.05:
            print(f"  ✅ 후기 구간에서 메모리 효과 유의미 (p<0.05)")
        else:
            print(f"  ❌ 후기 구간에서 메모리 효과 미미 (p≥0.05)")


def plot_learning_curves(df_trades: pd.DataFrame, output_path: str = "results/learning_curves.png"):
    """학습 곡선 시각화"""
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns

        sns.set_style("whitegrid")

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # 1. 누적 수익 곡선
        ax1 = axes[0]
        for use_memory in [False, True]:
            df_subset = df_trades[df_trades["use_memory"] == use_memory]

            if df_subset.empty:
                continue

            # run별 평균 누적 수익
            grouped = df_subset.groupby(["run_id", "ts"]) if "ts" in df_subset.columns else df_subset.groupby("run_id")

            # 각 run의 누적 equity를 평균
            all_runs = []
            for run_id, group in df_subset.groupby("run_id"):
                group = group.sort_values("ts") if "ts" in group.columns else group
                cumulative_pnl = group["cumulative_pnl"].values if "cumulative_pnl" in group.columns else group["pnl"].cumsum().values
                all_runs.append(cumulative_pnl)

            # 길이 맞추기 (최소 길이로)
            min_len = min(len(run) for run in all_runs)
            all_runs = [run[:min_len] for run in all_runs]

            # 평균 및 표준편차
            mean_cumulative = np.mean(all_runs, axis=0)
            std_cumulative = np.std(all_runs, axis=0)

            x = np.arange(len(mean_cumulative))
            color = "red" if use_memory else "blue"
            label = "With Memory" if use_memory else "No Memory"

            ax1.plot(x, mean_cumulative, color=color, label=label, linewidth=2)
            ax1.fill_between(x, mean_cumulative - std_cumulative, mean_cumulative + std_cumulative, color=color, alpha=0.2)

        ax1.set_xlabel("Trade Number")
        ax1.set_ylabel("Cumulative PnL ($)")
        ax1.set_title("Learning Curve: Cumulative Profit")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.axhline(0, color="black", linestyle="--", alpha=0.5)

        # 2. 구간별 Sharpe Ratio
        ax2 = axes[1]
        df_periods = analyze_learning_curve(df_trades)

        # 구간별 평균 및 표준편차
        period_stats = df_periods.groupby(["use_memory", "period_label"])["sharpe"].agg(["mean", "std"]).reset_index()

        x_labels = ["Early", "Mid", "Late"]
        x_pos = np.arange(len(x_labels))
        width = 0.35

        for idx, use_memory in enumerate([False, True]):
            stats_subset = period_stats[period_stats["use_memory"] == use_memory]
            means = [stats_subset[stats_subset["period_label"] == label]["mean"].values[0] if len(stats_subset[stats_subset["period_label"] == label]) > 0 else 0 for label in x_labels]
            stds = [stats_subset[stats_subset["period_label"] == label]["std"].values[0] if len(stats_subset[stats_subset["period_label"] == label]) > 0 else 0 for label in x_labels]

            color = "red" if use_memory else "blue"
            label = "With Memory" if use_memory else "No Memory"

            ax2.bar(x_pos + idx * width, means, width, yerr=stds, color=color, alpha=0.7, label=label, capsize=5)

        ax2.set_xlabel("Period")
        ax2.set_ylabel("Sharpe Ratio")
        ax2.set_title("Learning Effect: Sharpe Ratio by Period")
        ax2.set_xticks(x_pos + width / 2)
        ax2.set_xticklabels(x_labels)
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis="y")
        ax2.axhline(0, color="black", linestyle="--", alpha=0.5)

        plt.tight_layout()
        plt.savefig(output_path, dpi=300)
        print(f"\n✅ 학습 곡선 시각화 저장: {output_path}")
        plt.close()

    except ImportError:
        print("\n⚠️  matplotlib 또는 seaborn이 설치되지 않았습니다.")
        print("   설치: uv pip install matplotlib seaborn")


def main():
    parser = argparse.ArgumentParser(description="학습 곡선 분석 (RQ3)")

    # 필수 인자
    parser.add_argument("--no-memory-dir", type=str, required=True, help="메모리 미사용 결과 디렉터리")
    parser.add_argument("--with-memory-dir", type=str, required=True, help="메모리 사용 결과 디렉터리")

    # 옵션
    parser.add_argument("--n-periods", type=int, default=3, help="구간 분할 수 (기본: 3)")
    parser.add_argument("--plot", action="store_true", help="학습 곡선 시각화")
    parser.add_argument("--output", type=str, help="결과 CSV 저장 경로")

    args = parser.parse_args()

    # 데이터 로드
    print("=" * 80)
    print("📂 데이터 로드 중...")
    print("=" * 80)

    print(f"\n[메모리 미사용] {args.no_memory_dir}")
    no_mem_dir = Path(args.no_memory_dir)
    if not no_mem_dir.exists():
        print(f"❌ 디렉터리를 찾을 수 없습니다: {args.no_memory_dir}")
        sys.exit(1)
    df_no_mem = load_all_trades(no_mem_dir)

    print(f"\n[메모리 사용] {args.with_memory_dir}")
    with_mem_dir = Path(args.with_memory_dir)
    if not with_mem_dir.exists():
        print(f"❌ 디렉터리를 찾을 수 없습니다: {args.with_memory_dir}")
        sys.exit(1)
    df_with_mem = load_all_trades(with_mem_dir)

    if df_no_mem.empty and df_with_mem.empty:
        print("\n❌ 거래 데이터를 찾을 수 없습니다.")
        sys.exit(1)

    # 통합
    df_all = pd.concat([df_no_mem, df_with_mem], ignore_index=True)
    print(f"\n✅ 총 {len(df_all)} 거래 로드됨 ({len(df_all['run_id'].unique())} runs)")

    # 학습 곡선 분석
    df_periods = analyze_learning_curve(df_all, n_periods=args.n_periods)

    # 결과 출력
    print_learning_analysis(df_periods)

    # CSV 저장
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_periods.to_csv(output_path, index=False)
        print(f"\n💾 구간별 분석 결과 저장: {output_path}")

    # 시각화
    if args.plot:
        plot_learning_curves(df_all)

    print("\n" + "=" * 80)
    print("✅ 학습 곡선 분석 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()

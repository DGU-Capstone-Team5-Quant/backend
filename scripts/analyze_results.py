"""
실험 결과 분석 스크립트

백테스트 결과를 로드하고 통계 분석, 시각화를 수행합니다.

사용예:
    # 실험 1 분석
    python scripts/analyze_results.py --exp exp1_memory_effect

    # 실험 2 분석
    python scripts/analyze_results.py --exp exp2_generalization --plot

    # 커스텀 경로
    python scripts/analyze_results.py --no-memory-dir results/custom/no_mem --with-memory-dir results/custom/with_mem
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

import pandas as pd
import numpy as np
from scipy import stats


def load_experiment_results(exp_dir: Path) -> pd.DataFrame:
    """
    실험 디렉터리에서 모든 JSON 파일을 로드하여 DataFrame으로 반환
    """
    results = []

    # JSON 파일 찾기
    json_files = list(exp_dir.glob("*.json"))
    if not json_files:
        json_files = list(exp_dir.rglob("*.json"))

    print(f"  발견된 파일: {len(json_files)}개")

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 필요한 필드 추출
            summary = data.get("summary", {})

            # 메타데이터에서 ticker, seed 추출
            ticker = data.get("ticker") or summary.get("ticker", "UNKNOWN")
            seed = data.get("seed")
            if seed is None:
                seed = summary.get("meta", {}).get("seed")

            use_memory = data.get("use_memory")
            if use_memory is None:
                use_memory = summary.get("meta", {}).get("use_memory")

            # 주요 메트릭 추출
            record = {
                "ticker": ticker,
                "seed": seed,
                "use_memory": use_memory,
                "total_return": summary.get("total_return", 0.0),
                "cagr": summary.get("cagr", 0.0),
                "sharpe": summary.get("sharpe", 0.0),
                "max_drawdown_pct": summary.get("max_drawdown_pct", 0.0),
                "calmar": summary.get("calmar", 0.0),
                "volatility": summary.get("volatility", 0.0),
                "trades_count": summary.get("trades_count", 0),
                "turnover_shares": summary.get("turnover_shares", 0.0),
                "final_equity": summary.get("final_equity", 0.0),
                "initial_capital": summary.get("initial_capital", 10000.0),
            }

            results.append(record)

        except Exception as e:
            print(f"  ⚠️  파일 로드 실패: {json_file.name} - {e}")
            continue

    if not results:
        print(f"  ❌ 유효한 데이터를 찾을 수 없습니다.")
        return pd.DataFrame()

    df = pd.DataFrame(results)
    return df


def cohen_d(x, y):
    """Cohen's d 효과 크기 계산"""
    nx, ny = len(x), len(y)
    if nx == 0 or ny == 0:
        return 0.0

    dof = nx + ny - 2
    if dof <= 0:
        return 0.0

    pooled_std = np.sqrt(((nx - 1) * np.std(x, ddof=1) ** 2 + (ny - 1) * np.std(y, ddof=1) ** 2) / dof)

    if pooled_std == 0:
        return 0.0

    return (np.mean(x) - np.mean(y)) / pooled_std


def analyze_memory_effect(df_no_memory: pd.DataFrame, df_with_memory: pd.DataFrame) -> Dict[str, Any]:
    """
    메모리 효과 분석 (RQ1)
    """
    print("\n" + "=" * 80)
    print("📊 메모리 효과 분석 (RQ1: Memory Learning Effect)")
    print("=" * 80)

    if df_no_memory.empty or df_with_memory.empty:
        print("❌ 데이터가 부족합니다.")
        return {}

    metrics = ["total_return", "sharpe", "max_drawdown_pct", "calmar"]
    results = {}

    for metric in metrics:
        no_mem_vals = df_no_memory[metric].dropna()
        with_mem_vals = df_with_memory[metric].dropna()

        if len(no_mem_vals) == 0 or len(with_mem_vals) == 0:
            continue

        # 기술 통계
        no_mem_mean = no_mem_vals.mean()
        no_mem_std = no_mem_vals.std()
        with_mem_mean = with_mem_vals.mean()
        with_mem_std = with_mem_vals.std()

        # t-test
        t_stat, p_value = stats.ttest_ind(with_mem_vals, no_mem_vals)

        # 효과 크기
        effect_size = cohen_d(with_mem_vals, no_mem_vals)

        # 개선율
        if no_mem_mean != 0:
            improvement_pct = (with_mem_mean - no_mem_mean) / abs(no_mem_mean) * 100
        else:
            improvement_pct = 0.0

        results[metric] = {
            "no_memory_mean": no_mem_mean,
            "no_memory_std": no_mem_std,
            "with_memory_mean": with_mem_mean,
            "with_memory_std": with_mem_std,
            "improvement": with_mem_mean - no_mem_mean,
            "improvement_pct": improvement_pct,
            "t_statistic": t_stat,
            "p_value": p_value,
            "cohen_d": effect_size,
        }

    # 결과 출력
    print("\n[ 기술 통계 ]")
    print(f"{'Metric':<20} {'No Memory':<20} {'With Memory':<20} {'Improvement':<15} {'p-value':<10} {'Cohen d':<10}")
    print("-" * 100)

    for metric, res in results.items():
        no_mem_str = f"{res['no_memory_mean']:.4f} ± {res['no_memory_std']:.4f}"
        with_mem_str = f"{res['with_memory_mean']:.4f} ± {res['with_memory_std']:.4f}"
        imp_str = f"{res['improvement_pct']:+.2f}%"

        # 유의성 표시
        if res["p_value"] < 0.001:
            sig = "***"
        elif res["p_value"] < 0.01:
            sig = "**"
        elif res["p_value"] < 0.05:
            sig = "*"
        else:
            sig = "n.s."

        p_str = f"{res['p_value']:.4f} {sig}"
        d_str = f"{res['cohen_d']:.4f}"

        print(f"{metric:<20} {no_mem_str:<20} {with_mem_str:<20} {imp_str:<15} {p_str:<10} {d_str:<10}")

    print("\n[ 해석 ]")
    for metric, res in results.items():
        if res["p_value"] < 0.05:
            direction = "증가" if res["improvement"] > 0 else "감소"
            print(f"  ✅ {metric}: 메모리 사용 시 {direction} (p={res['p_value']:.4f}, d={res['cohen_d']:.4f})")
        else:
            print(f"  ❌ {metric}: 유의미한 차이 없음 (p={res['p_value']:.4f})")

    return results


def analyze_generalization(df: pd.DataFrame) -> pd.DataFrame:
    """
    일반화 성능 분석 (RQ2)
    """
    print("\n" + "=" * 80)
    print("🌐 일반화 성능 분석 (RQ2: Generalization Across Tickers)")
    print("=" * 80)

    if df.empty or "ticker" not in df.columns:
        print("❌ 데이터가 부족합니다.")
        return pd.DataFrame()

    tickers = df["ticker"].unique()
    results = []

    for ticker in tickers:
        df_ticker = df[df["ticker"] == ticker]
        df_no_mem = df_ticker[df_ticker["use_memory"] == False]
        df_with_mem = df_ticker[df_ticker["use_memory"] == True]

        if df_no_mem.empty or df_with_mem.empty:
            continue

        no_mem_return = df_no_mem["total_return"].mean()
        with_mem_return = df_with_mem["total_return"].mean()
        improvement = with_mem_return - no_mem_return
        improvement_pct = improvement / abs(no_mem_return) * 100 if no_mem_return != 0 else 0

        # t-test
        t_stat, p_value = stats.ttest_ind(df_with_mem["total_return"], df_no_mem["total_return"])

        results.append(
            {
                "ticker": ticker,
                "no_memory_return": no_mem_return,
                "with_memory_return": with_mem_return,
                "improvement": improvement,
                "improvement_pct": improvement_pct,
                "t_statistic": t_stat,
                "p_value": p_value,
                "n_no_mem": len(df_no_mem),
                "n_with_mem": len(df_with_mem),
            }
        )

    df_results = pd.DataFrame(results)

    if df_results.empty:
        print("❌ 분석 결과가 없습니다.")
        return df_results

    print("\n[ 종목별 성과 ]")
    print(df_results.to_string(index=False))

    print("\n[ 해석 ]")
    significant_tickers = df_results[df_results["p_value"] < 0.05]
    if len(significant_tickers) > 0:
        print(f"  ✅ {len(significant_tickers)}/{len(df_results)} 종목에서 유의미한 개선")
        print(f"     평균 개선율: {significant_tickers['improvement_pct'].mean():.2f}%")
    else:
        print("  ❌ 유의미한 개선이 관찰된 종목 없음")

    return df_results


def main():
    parser = argparse.ArgumentParser(description="FinMem 실험 결과 분석")

    # 실험 타입
    parser.add_argument(
        "--exp",
        type=str,
        choices=["exp1_memory_effect", "exp2_generalization"],
        help="실험 종류 (자동으로 디렉터리 찾기)",
    )

    # 커스텀 경로
    parser.add_argument("--no-memory-dir", type=str, help="메모리 미사용 결과 디렉터리")
    parser.add_argument("--with-memory-dir", type=str, help="메모리 사용 결과 디렉터리")
    parser.add_argument("--combined-dir", type=str, help="통합 결과 디렉터리 (exp2용)")

    # 옵션
    parser.add_argument("--plot", action="store_true", help="시각화 생성")
    parser.add_argument("--output", type=str, help="결과 저장 경로 (CSV)")

    args = parser.parse_args()

    # 디렉터리 결정
    if args.exp:
        base_dir = Path(f"results/{args.exp}")
        if args.exp == "exp1_memory_effect":
            no_mem_dir = base_dir / "no_memory"
            with_mem_dir = base_dir / "with_memory"
        elif args.exp == "exp2_generalization":
            no_mem_dir = base_dir / "no_memory"
            with_mem_dir = base_dir / "with_memory"
    else:
        if args.no_memory_dir and args.with_memory_dir:
            no_mem_dir = Path(args.no_memory_dir)
            with_mem_dir = Path(args.with_memory_dir)
        elif args.combined_dir:
            no_mem_dir = with_mem_dir = Path(args.combined_dir)
        else:
            print("❌ --exp 또는 --no-memory-dir와 --with-memory-dir를 지정하세요.")
            parser.print_help()
            sys.exit(1)

    # 데이터 로드
    print("=" * 80)
    print("📂 데이터 로드 중...")
    print("=" * 80)

    print(f"\n[메모리 미사용] {no_mem_dir}")
    if not no_mem_dir.exists():
        print(f"❌ 디렉터리를 찾을 수 없습니다: {no_mem_dir}")
        df_no_memory = pd.DataFrame()
    else:
        df_no_memory = load_experiment_results(no_mem_dir)

    print(f"\n[메모리 사용] {with_mem_dir}")
    if not with_mem_dir.exists():
        print(f"❌ 디렉터리를 찾을 수 없습니다: {with_mem_dir}")
        df_with_memory = pd.DataFrame()
    else:
        df_with_memory = load_experiment_results(with_mem_dir)

    # 분석
    if args.exp == "exp1_memory_effect" or (args.no_memory_dir and args.with_memory_dir):
        analyze_memory_effect(df_no_memory, df_with_memory)

    if args.exp == "exp2_generalization" or args.combined_dir:
        df_combined = pd.concat([df_no_memory, df_with_memory], ignore_index=True)
        gen_results = analyze_generalization(df_combined)

        if args.output and not gen_results.empty:
            output_path = Path(args.output)
            gen_results.to_csv(output_path, index=False)
            print(f"\n💾 결과 저장: {output_path}")

    # 시각화
    if args.plot:
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns

            print("\n" + "=" * 80)
            print("📈 시각화 생성 중...")
            print("=" * 80)

            sns.set_style("whitegrid")

            # RQ1 시각화
            if not df_no_memory.empty and not df_with_memory.empty:
                fig, axes = plt.subplots(1, 3, figsize=(15, 5))

                # Total Return
                axes[0].boxplot(
                    [df_no_memory["total_return"].dropna(), df_with_memory["total_return"].dropna()],
                    labels=["No Memory", "With Memory"],
                )
                axes[0].set_ylabel("Total Return")
                axes[0].set_title("Total Return Comparison")
                axes[0].grid(True, alpha=0.3)

                # Sharpe Ratio
                axes[1].boxplot(
                    [df_no_memory["sharpe"].dropna(), df_with_memory["sharpe"].dropna()],
                    labels=["No Memory", "With Memory"],
                )
                axes[1].set_ylabel("Sharpe Ratio")
                axes[1].set_title("Sharpe Ratio Comparison")
                axes[1].grid(True, alpha=0.3)

                # Max Drawdown
                axes[2].boxplot(
                    [df_no_memory["max_drawdown_pct"].dropna(), df_with_memory["max_drawdown_pct"].dropna()],
                    labels=["No Memory", "With Memory"],
                )
                axes[2].set_ylabel("Max Drawdown (%)")
                axes[2].set_title("Max Drawdown Comparison")
                axes[2].grid(True, alpha=0.3)

                plt.tight_layout()
                output_file = "results/analysis_rq1.png"
                plt.savefig(output_file, dpi=300)
                print(f"✅ RQ1 시각화 저장: {output_file}")
                plt.close()

            # RQ2 시각화
            if args.exp == "exp2_generalization":
                df_combined = pd.concat([df_no_memory, df_with_memory], ignore_index=True)
                if not df_combined.empty and "ticker" in df_combined.columns:
                    gen_results = analyze_generalization(df_combined)

                    if not gen_results.empty:
                        plt.figure(figsize=(10, 6))
                        bars = plt.bar(gen_results["ticker"], gen_results["improvement_pct"])

                        # 색상 (양수=녹색, 음수=빨강)
                        for i, bar in enumerate(bars):
                            if gen_results.iloc[i]["improvement_pct"] > 0:
                                bar.set_color("green")
                            else:
                                bar.set_color("red")

                        plt.axhline(0, color="black", linestyle="--", alpha=0.5)
                        plt.xlabel("Ticker")
                        plt.ylabel("Improvement (%)")
                        plt.title("Memory Effect by Ticker")
                        plt.grid(True, alpha=0.3, axis="y")

                        output_file = "results/analysis_rq2.png"
                        plt.savefig(output_file, dpi=300)
                        print(f"✅ RQ2 시각화 저장: {output_file}")
                        plt.close()

        except ImportError:
            print("⚠️  matplotlib 또는 seaborn이 설치되지 않았습니다.")
            print("   설치: uv pip install matplotlib seaborn")

    print("\n" + "=" * 80)
    print("✅ 분석 완료!")
    print("=" * 80)


if __name__ == "__main__":
    main()

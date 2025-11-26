"""
배치 실험 실행 스크립트 (논문용)

여러 종목, 여러 시드로 대규모 실험을 자동 실행합니다.

사용예:
    # 실험 1: 메모리 효과 검증
    python scripts/run_experiments.py --exp exp1_memory_effect --tickers AAPL --seeds 0 1 2 3 4 5 6 7 8 9

    # 실험 2: 일반화 성능
    python scripts/run_experiments.py --exp exp2_generalization --tickers AAPL TSLA GOOGL MSFT NVDA --seeds 0 1 2 3 4

    # 실험 3: 재현성 검증
    python scripts/run_experiments.py --exp exp3_reproducibility --tickers AAPL --seeds 42 --runs 3
"""
import asyncio
import argparse
import sys
import time
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from services.backtest import BacktestService
from services.simulation import SimulationService


async def run_single_backtest(
    ticker: str,
    seed: int,
    use_memory: bool,
    output_dir: str,
    start_date: str,
    end_date: str,
    window: int,
    step: int,
    interval: str,
    shares: float,
    initial_capital: float,
):
    """단일 백테스트 실행"""
    print(f"  [{ticker}, seed={seed}, memory={use_memory}] 시작...")
    start_time = time.time()

    try:
        sim_service = SimulationService(settings)
        service = BacktestService(sim_service, settings)

        result = await service.run(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            window=window,
            step=step,
            interval=interval,
            include_news=True,
            use_memory=use_memory,
            seed=seed,
            shares=shares,
            initial_capital=initial_capital,
        )

        # 결과 저장 (CSV만 - 분석용)
        import csv
        import json

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # JSON 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mem_suffix = "with_mem" if use_memory else "no_mem"
        json_file = output_path / f"backtest_{ticker}_{seed}_{mem_suffix}_{timestamp}.json"

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "ticker": ticker,
                    "seed": seed,
                    "use_memory": use_memory,
                    "start_date": start_date,
                    "end_date": end_date,
                    "summary": result.summary,
                },
                f,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        # CSV 저장
        csv_file = output_path / f"backtest_{ticker}_{seed}_{mem_suffix}_{timestamp}_metrics.csv"
        flat_metrics = {k: v for k, v in result.summary.items() if not isinstance(v, (dict, list))}
        flat_metrics["ticker"] = ticker
        flat_metrics["seed"] = seed
        flat_metrics["use_memory"] = use_memory

        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=flat_metrics.keys())
            writer.writeheader()
            writer.writerow(flat_metrics)

        elapsed = time.time() - start_time
        print(
            f"  ✅ [{ticker}, seed={seed}, memory={use_memory}] 완료 ({elapsed:.1f}s) - Return: {result.summary.get('total_return', 0)*100:.2f}%"
        )

        return result

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"  ❌ [{ticker}, seed={seed}, memory={use_memory}] 실패 ({elapsed:.1f}s): {e}")
        import traceback

        traceback.print_exc()
        return None


async def run_experiment_1(args):
    """실험 1: 메모리 효과 검증 (RQ1)"""
    print("\n" + "=" * 80)
    print("🧪 실험 1: 메모리 효과 검증 (Memory Learning Effect)")
    print("=" * 80)
    print(f"종목: {args.tickers}")
    print(f"시드: {args.seeds}")
    print(f"기간: {args.start_date} ~ {args.end_date}")
    print("=" * 80 + "\n")

    total_runs = len(args.tickers) * len(args.seeds) * 2  # 메모리 있음/없음
    current_run = 0

    for ticker in args.tickers:
        for seed in args.seeds:
            # 대조군: 메모리 없음
            current_run += 1
            print(f"[{current_run}/{total_runs}] 대조군 실행 중...")
            await run_single_backtest(
                ticker=ticker,
                seed=seed,
                use_memory=False,
                output_dir=f"{args.output_dir}/no_memory",
                start_date=args.start_date,
                end_date=args.end_date,
                window=args.window,
                step=args.step,
                interval=args.interval,
                shares=args.shares,
                initial_capital=args.initial_capital,
            )

            # 실험군: 메모리 사용
            current_run += 1
            print(f"[{current_run}/{total_runs}] 실험군 실행 중...")
            await run_single_backtest(
                ticker=ticker,
                seed=seed,
                use_memory=True,
                output_dir=f"{args.output_dir}/with_memory",
                start_date=args.start_date,
                end_date=args.end_date,
                window=args.window,
                step=args.step,
                interval=args.interval,
                shares=args.shares,
                initial_capital=args.initial_capital,
            )

    print("\n" + "=" * 80)
    print("✅ 실험 1 완료!")
    print(f"결과 저장 위치: {args.output_dir}/")
    print("=" * 80 + "\n")


async def run_experiment_2(args):
    """실험 2: 일반화 성능 (RQ2)"""
    print("\n" + "=" * 80)
    print("🧪 실험 2: 일반화 성능 (Generalization Across Tickers)")
    print("=" * 80)
    print(f"종목: {args.tickers}")
    print(f"시드: {args.seeds}")
    print("=" * 80 + "\n")

    # 실험 1과 동일하지만 여러 종목
    await run_experiment_1(args)


async def run_experiment_3(args):
    """실험 3: 재현성 검증 (RQ3)"""
    print("\n" + "=" * 80)
    print("🧪 실험 3: 재현성 검증 (Reproducibility)")
    print("=" * 80)
    print(f"종목: {args.tickers[0]}")
    print(f"시드: {args.seeds[0]}")
    print(f"반복 횟수: {args.runs}")
    print("=" * 80 + "\n")

    ticker = args.tickers[0]
    seed = args.seeds[0]

    for run_idx in range(args.runs):
        print(f"\n[Run {run_idx + 1}/{args.runs}]")
        await run_single_backtest(
            ticker=ticker,
            seed=seed,
            use_memory=True,
            output_dir=f"{args.output_dir}/run_{run_idx + 1}",
            start_date=args.start_date,
            end_date=args.end_date,
            window=args.window,
            step=args.step,
            interval=args.interval,
            shares=args.shares,
            initial_capital=args.initial_capital,
        )

    print("\n" + "=" * 80)
    print("✅ 실험 3 완료!")
    print(f"결과 저장 위치: {args.output_dir}/")
    print("\n다음 명령으로 재현성 검증:")
    print(f"  python scripts/check_reproducibility.py {args.output_dir}/run_*/backtest_{ticker}_{seed}_*.json")
    print("=" * 80 + "\n")


async def main():
    parser = argparse.ArgumentParser(description="FinMem 배치 실험 실행 (논문용)")

    # 실험 타입
    parser.add_argument(
        "--exp",
        type=str,
        required=True,
        choices=["exp1_memory_effect", "exp2_generalization", "exp3_reproducibility"],
        help="실험 종류",
    )

    # 공통 인자
    parser.add_argument("--tickers", type=str, nargs="+", default=["AAPL"], help="종목 리스트")
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2, 3, 4], help="시드 리스트")
    parser.add_argument("--start-date", type=str, default="2024-01-01", help="시작 날짜")
    parser.add_argument("--end-date", type=str, default="2024-06-30", help="종료 날짜")
    parser.add_argument("--window", type=int, default=30, help="윈도우 크기")
    parser.add_argument("--step", type=int, default=1, help="스텝 간격")
    parser.add_argument("--interval", type=str, default="1h", help="시간 간격")
    parser.add_argument("--shares", type=float, default=1.0, help="거래 주수")
    parser.add_argument("--initial-capital", type=float, default=10000.0, help="초기 자본")
    parser.add_argument("--output-dir", type=str, default=None, help="결과 저장 디렉터리")

    # 재현성 실험용
    parser.add_argument("--runs", type=int, default=3, help="재현성 검증 반복 횟수 (exp3만 사용)")

    args = parser.parse_args()

    # 기본 output_dir 설정
    if args.output_dir is None:
        args.output_dir = f"results/{args.exp}"

    # 실험 실행
    if args.exp == "exp1_memory_effect":
        await run_experiment_1(args)
    elif args.exp == "exp2_generalization":
        await run_experiment_2(args)
    elif args.exp == "exp3_reproducibility":
        await run_experiment_3(args)


if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(main())
    total_time = time.time() - start_time

    print("\n" + "=" * 80)
    print(f"🎉 전체 실험 완료! (소요 시간: {total_time/60:.1f}분)")
    print("=" * 80)

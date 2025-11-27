"""
실험 1: 메모리 효과 검증 (RQ1)

Warmup → Treatment/Control을 하나의 프로세스에서 실행하여 메모리 유지
"""
import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from services.backtest import BacktestService
from services.simulation import SimulationService


async def main():
    parser = argparse.ArgumentParser(description="실험 1: 메모리 효과 검증")

    parser.add_argument("--ticker", type=str, default="AAPL", help="종목 심볼")
    parser.add_argument("--seed", type=int, default=42, help="랜덤 시드")
    parser.add_argument("--warmup-start", type=str, default="2025-01-01", help="Warmup 시작일")
    parser.add_argument("--warmup-end", type=str, default="2025-08-31", help="Warmup 종료일")
    parser.add_argument("--test-start", type=str, default="2025-09-01", help="Test 시작일")
    parser.add_argument("--test-end", type=str, default="2025-11-20", help="Test 종료일")
    parser.add_argument("--output-dir", type=str, default="results/exp1_memory", help="결과 디렉터리")

    args = parser.parse_args()

    print("=" * 80)
    print("실험 1: 메모리 효과 검증 (RQ1)")
    print("=" * 80)
    print(f"종목: {args.ticker}")
    print(f"시드: {args.seed}")
    print(f"Warmup: {args.warmup_start} ~ {args.warmup_end}")
    print(f"Test: {args.test_start} ~ {args.test_end}")
    print("=" * 80)

    # 동일한 SimulationService 인스턴스 사용 (메모리 공유)
    sim_service = SimulationService(settings)
    service = BacktestService(sim_service, settings)

    print(f"\nMemory type: {type(sim_service.memory).__name__}")

    # Phase 1: Warmup (메모리 생성)
    print("\n" + "=" * 80)
    print("PHASE 1: WARMUP (메모리 생성)")
    print("=" * 80)

    warmup_result = await service.run(
        ticker=args.ticker,
        start_date=args.warmup_start,
        end_date=args.warmup_end,
        window=30,
        step=1,
        interval="1h",
        include_news=True,
        use_memory=True,
        seed=args.seed,
        shares=1.0,
        initial_capital=10000.0,
    )

    print(f"\nWarmup 완료!")
    print(f"  총 수익률: {warmup_result.summary.get('total_return', 0)*100:.2f}%")
    print(f"  샤프 비율: {warmup_result.summary.get('sharpe', 0):.4f}")

    # 메모리 검색 테스트
    print(f"\n메모리 검색 테스트...")
    memories = await sim_service.memory.search(f"{args.ticker} market", k=5, ticker=args.ticker)
    print(f"  저장된 메모리 개수: {len(memories)}")
    if memories:
        print(f"  첫 번째 메모리 (일부): {memories[0].get('content', '')[:80]}...")

    # Phase 2: Treatment (메모리 사용)
    print("\n" + "=" * 80)
    print("PHASE 2: TREATMENT (메모리 사용)")
    print("=" * 80)

    treatment_result = await service.run(
        ticker=args.ticker,
        start_date=args.test_start,
        end_date=args.test_end,
        window=30,
        step=1,
        interval="1h",
        include_news=True,
        use_memory=True,  # ✅ 메모리 사용
        seed=args.seed,
        shares=1.0,
        initial_capital=10000.0,
    )

    print(f"\nTreatment 완료!")
    print(f"  총 수익률: {treatment_result.summary.get('total_return', 0)*100:.2f}%")
    print(f"  샤프 비율: {treatment_result.summary.get('sharpe', 0):.4f}")
    print(f"  거래 수: {treatment_result.summary.get('trades_count', 0)}")

    # Phase 3: Control (메모리 미사용)
    print("\n" + "=" * 80)
    print("PHASE 3: CONTROL (메모리 미사용)")
    print("=" * 80)

    control_result = await service.run(
        ticker=args.ticker,
        start_date=args.test_start,
        end_date=args.test_end,
        window=30,
        step=1,
        interval="1h",
        include_news=True,
        use_memory=False,  # ❌ 메모리 미사용
        seed=args.seed,
        shares=1.0,
        initial_capital=10000.0,
    )

    print(f"\nControl 완료!")
    print(f"  총 수익률: {control_result.summary.get('total_return', 0)*100:.2f}%")
    print(f"  샤프 비율: {control_result.summary.get('sharpe', 0):.4f}")
    print(f"  거래 수: {control_result.summary.get('trades_count', 0)}")

    # 결과 저장
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 전체 결과
    results = {
        "experiment": "RQ1: 메모리 효과 검증",
        "timestamp": timestamp,
        "ticker": args.ticker,
        "seed": args.seed,
        "memory_type": type(sim_service.memory).__name__,
        "warmup": {
            "period": f"{args.warmup_start} ~ {args.warmup_end}",
            "metrics": warmup_result.summary,
        },
        "treatment": {
            "period": f"{args.test_start} ~ {args.test_end}",
            "use_memory": True,
            "metrics": treatment_result.summary,
            "trades": treatment_result.trades,
        },
        "control": {
            "period": f"{args.test_start} ~ {args.test_end}",
            "use_memory": False,
            "metrics": control_result.summary,
            "trades": control_result.trades,
        },
    }

    result_path = output_dir / f"exp1_{args.ticker}_{args.seed}_{timestamp}.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)

    print("\n" + "=" * 80)
    print("비교 결과")
    print("=" * 80)
    print(f"Treatment (메모리 O) vs Control (메모리 X):")
    print(f"  수익률: {treatment_result.summary.get('total_return', 0)*100:.2f}% vs {control_result.summary.get('total_return', 0)*100:.2f}%")
    print(f"  샤프: {treatment_result.summary.get('sharpe', 0):.4f} vs {control_result.summary.get('sharpe', 0):.4f}")
    print(f"  거래 수: {treatment_result.summary.get('trades_count', 0)} vs {control_result.summary.get('trades_count', 0)}")

    # 첫 3개 거래 비교
    print(f"\n첫 3개 거래 비교:")
    print(f"Treatment:")
    for i, trade in enumerate(treatment_result.trades[:3], 1):
        print(f"  {i}. {trade['action']} at {trade['price']} ({trade['ts']})")
    print(f"Control:")
    for i, trade in enumerate(control_result.trades[:3], 1):
        print(f"  {i}. {trade['action']} at {trade['price']} ({trade['ts']})")

    print(f"\n결과 저장: {result_path}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

"""
단일 시뮬레이션 실행 CLI 스크립트

사용법:
    python scripts/run_simulation.py --ticker AAPL --window 30 --seed 42
    python scripts/run_simulation.py --ticker AAPL --mode daily --interval 1day
"""
import asyncio
import argparse
import json
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from services.simulation import SimulationService


async def main():
    parser = argparse.ArgumentParser(description="FinMem Trading 시뮬레이션 실행")

    # 필수 인자
    parser.add_argument("--ticker", type=str, required=True, help="종목 심볼 (예: AAPL, TSLA)")
    parser.add_argument("--window", type=int, default=30, help="데이터 윈도우 크기 (기본: 30)")

    # 선택 인자
    parser.add_argument("--seed", type=int, default=None, help="재현성을 위한 랜덤 시드")
    parser.add_argument("--mode", type=str, default="intraday", choices=["intraday", "daily"], help="데이터 모드")
    parser.add_argument("--interval", type=str, default="1h", help="시간 간격 (1h, 1day 등)")
    parser.add_argument("--include-news", action="store_true", default=True, help="뉴스 포함 여부")
    parser.add_argument("--no-news", action="store_true", help="뉴스 제외")
    parser.add_argument("--use-memory", action="store_true", default=True, help="메모리 사용 여부")
    parser.add_argument("--no-memory", action="store_true", help="메모리 미사용")
    parser.add_argument("--output", type=str, default=None, help="결과 저장 경로 (JSON)")

    args = parser.parse_args()

    # 뉴스/메모리 플래그 처리
    include_news = not args.no_news
    use_memory = not args.no_memory

    print("=" * 60)
    print("🚀 FinMem Trading Simulation")
    print("=" * 60)
    print(f"종목: {args.ticker}")
    print(f"윈도우: {args.window}")
    print(f"모드: {args.mode} ({args.interval})")
    print(f"시드: {args.seed}")
    print(f"뉴스 포함: {include_news}")
    print(f"메모리 사용: {use_memory}")
    print(f"LLM 모델: {settings.ollama_model}")
    print("=" * 60)

    # 시뮬레이션 실행
    print("\n⏳ 시뮬레이션 실행 중...")
    service = SimulationService(settings)

    try:
        result = await service.run(
            ticker=args.ticker,
            window=args.window,
            mode=args.mode,
            interval=args.interval,
            include_news=include_news,
            use_memory=use_memory,
            seed=args.seed,
        )

        print("\n✅ 시뮬레이션 완료!")
        print("=" * 60)

        # 결과 출력
        summary = result.summary
        decision = summary.get("decision", {})

        print("\n📊 결과 요약:")
        print(f"  - 결정: {decision.get('action', 'N/A')}")
        print(f"  - 신뢰도: {decision.get('confidence', 'N/A')}")
        print(f"  - 근거: {decision.get('rationale', 'N/A')[:100]}...")

        # JSON 저장
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            print(f"\n💾 결과 저장: {output_path}")
        else:
            # 기본 저장 경로
            output_dir = Path("results")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"simulation_{args.ticker}_{args.seed or 'random'}.json"
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            print(f"\n💾 결과 저장: {output_path}")

        print("\n" + "=" * 60)

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

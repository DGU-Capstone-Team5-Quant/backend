"""
백테스트 실행 CLI.

사용예:
    python scripts/run_backtest.py --ticker AAPL --runs 100 --seed 42
    python scripts/run_backtest.py --ticker AAPL --start-date 2024-01-01 --end-date 2024-12-31
"""
import asyncio
import argparse
import json
import sys
import logging
from pathlib import Path
from datetime import datetime
import csv

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from services.backtest import BacktestService
from services.simulation import SimulationService


async def main():
    parser = argparse.ArgumentParser(description="FinMem Trading 백테스트 실행")

    # 필수 인자
    parser.add_argument("--ticker", type=str, required=True, help="종목 심볼 (예: AAPL, TSLA)")

    # 백테스트 설정
    parser.add_argument("--start-date", type=str, default="2025-09-01", help="시작 날짜 (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default="2025-11-20", help="종료 날짜 (YYYY-MM-DD)")
    parser.add_argument("--window", type=int, default=30, help="슬라이딩 윈도우 길이 (기본: 30)")
    parser.add_argument("--step", type=int, default=1, help="스텝 간격 (기본: 1)")
    parser.add_argument("--interval", type=str, default="1h", help="시간 간격 (예: 1h, 1day)")
    parser.add_argument("--shares", type=float, default=1.0, help="거래 시 진입/청산 주수 (기본: 1주)")
    parser.add_argument("--initial-capital", type=float, default=10000.0, help="초기 자본 (기본: 10,000)")

    # 실험 설정
    parser.add_argument("--seed", type=int, default=42, help="랜덤 시드 (기본: 42)")
    parser.add_argument("--include-news", action="store_true", default=True, help="뉴스 포함")
    parser.add_argument("--no-news", action="store_true", help="뉴스 제외")
    parser.add_argument("--use-memory", action="store_true", default=True, help="메모리 사용")
    parser.add_argument("--no-memory", action="store_true", help="메모리 미사용")

    # 출력 설정
    parser.add_argument("--output-dir", type=str, default="results", help="결과 저장 디렉터리")
    parser.add_argument("--verbose", action="store_true", help="자세한 로그 출력")

    args = parser.parse_args()

    # 로깅 설정 - 거래 로그만 표시
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s %(name)s %(levelname)s %(message)s',
            datefmt='%H:%M:%S'
        )
    else:
        # 기본 로깅 레벨을 WARNING으로 설정 (INFO 로그 숨김)
        logging.basicConfig(
            level=logging.WARNING,
            format='%(asctime)s %(name)s %(levelname)s %(message)s',
            datefmt='%H:%M:%S'
        )
        # httpx 로거 완전히 끄기
        logging.getLogger('httpx').setLevel(logging.CRITICAL)
        logging.getLogger('httpcore').setLevel(logging.CRITICAL)
        # 다른 시스템 로거들도 끄기
        logging.getLogger('services').setLevel(logging.WARNING)
        logging.getLogger('redisvl').setLevel(logging.WARNING)
        logging.getLogger('finmem').setLevel(logging.WARNING)

    include_news = not args.no_news
    use_memory = not args.no_memory

    print("=" * 80)
    print("FinMem Trading Backtest")
    print("=" * 80)
    print(f"종목: {args.ticker}")
    print(f"기간: {args.start_date} ~ {args.end_date}")
    print(f"윈도우: {args.window}, 스텝: {args.step}")
    print(f"간격: {args.interval}")
    print(f"주수: {args.shares}")
    print(f"초기 자본: {args.initial_capital}")
    print(f"시드: {args.seed}")
    print(f"뉴스 포함: {include_news}")
    print(f"메모리 사용: {use_memory}")
    print(f"LLM 모델: {settings.ollama_model}")
    print("=" * 80)

    print("\n" + "=" * 80)
    print("백테스트 실행 중...")
    print("=" * 80 + "\n")

    sim_service = SimulationService(settings)
    service = BacktestService(sim_service, settings)

    try:
        result = await service.run(
            ticker=args.ticker,
            start_date=args.start_date,
            end_date=args.end_date,
            window=args.window,
            step=args.step,
            interval=args.interval,
            include_news=include_news,
            use_memory=use_memory,
            seed=args.seed,
            shares=args.shares,
            initial_capital=args.initial_capital,
        )

        print("\n" + "=" * 80)
        print("백테스트 완료!")
        print("=" * 80)

        metrics = result.summary
        print("\n주요 메트릭:")
        print(f"  초기 자본: {metrics.get('initial_capital', 0):.2f}")
        print(f"  최종 자본: {metrics.get('final_equity', 0):.2f}")
        print(f"  현금: {metrics.get('final_cash', 0):.2f}")
        print(f"  총 수익률: {metrics.get('total_return', 0)*100:.2f}%")
        print(f"  CAGR: {metrics.get('cagr', 0)*100:.2f}%")
        print(f"  평균 스텝 수익률: {metrics.get('avg_step_return', 0) * 100:.4f}%")
        print(f"  변동성: {metrics.get('volatility', 0):.6f}")
        print(f"  샤프 비율: {metrics.get('sharpe', 0):.4f}")
        print(f"  최대 낙폭: {metrics.get('max_drawdown_pct', 0)*100:.2f}%")
        print(f"  칼마 비율: {metrics.get('calmar', 0):.4f}")
        print(f"  턴오버(주수): {metrics.get('turnover_shares', 0):.4f}")
        print(f"  거래 수: {metrics.get('trades_count', 0)}")

        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = f"backtest_{args.ticker}_{args.seed}_{timestamp}"

        # 1. JSON 저장(전체 결과)
        json_path = output_dir / f"{prefix}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "ticker": args.ticker,
                    "start_date": args.start_date,
                    "end_date": args.end_date,
                    "seed": args.seed,
                    "summary": metrics,
                    "trades": result.trades,
                },
                f,
                indent=2,
                ensure_ascii=False,
                default=str,  # datetime 직렬화
            )
        print(f"\nSaved full results: {json_path}")

        # 2. CSV 저장(메트릭 요약)
        csv_path = output_dir / f"{prefix}_metrics.csv"
        flat_metrics = {k: v for k, v in metrics.items() if not isinstance(v, (dict, list))}
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=flat_metrics.keys())
            writer.writeheader()
            writer.writerow(flat_metrics)
        print(f"Saved metrics CSV: {csv_path}")

        # 3. 거래 이력 CSV
        if result.trades:
            trades_csv_path = output_dir / f"{prefix}_trades.csv"
            with open(trades_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=result.trades[0].keys())
                writer.writeheader()
                writer.writerows(result.trades)
            print(f"Saved trades CSV: {trades_csv_path}")

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"\nError occurred: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

"""
Trading 시뮬레이션 실행 스크립트
===========================================

주요 기능:
-----------
✅ 실시간/일봉 데이터 분석
✅ 뉴스 감정 분석 통합
✅ 과거 거래 메모리 활용
✅ 다양한 시간 간격 지원
✅ 재현 가능한 시뮬레이션 (시드 설정)
✅ 상세한 결과 분석 및 저장

기본 사용법:
------------
# 가장 간단한 실행 (AAPL 종목, 기본 설정)
python scripts/run_simulation.py --ticker AAPL

# 윈도우 크기 지정 (최근 30개 데이터 포인트 사용)
python scripts/run_simulation.py --ticker AAPL --window 30

# 재현 가능한 시뮬레이션 (시드 고정)
python scripts/run_simulation.py --ticker AAPL --seed 42

고급 사용 예시:
--------------
# 일봉 데이터로 시뮬레이션
python scripts/run_simulation.py --ticker TSLA --mode daily --interval 1day

# 4시간봉 데이터 사용
python scripts/run_simulation.py --ticker GOOGL --interval 4h --window 50

# 뉴스 없이 순수 가격 데이터만으로 분석
python scripts/run_simulation.py --ticker MSFT --no-news

# 메모리 기능 비활성화 (과거 거래 기억 안함)
python scripts/run_simulation.py --ticker NVDA --no-memory

# 초기 자본금 설정
python scripts/run_simulation.py --ticker AMD --initial-capital 100000

# 최대 거래 횟수 제한
python scripts/run_simulation.py --ticker META --max-steps 50

# 결과를 특정 파일로 저장
python scripts/run_simulation.py --ticker AAPL --output results/my_test.json

# 상세 로그 출력
python scripts/run_simulation.py --ticker AAPL --verbose

종합 예시:
----------
# 완전한 설정으로 시뮬레이션 실행
python scripts/run_simulation.py \
    --ticker AAPL \
    --window 60 \
    --seed 42 \
    --mode intraday \
    --interval 1h \
    --initial-capital 50000 \
    --max-steps 100 \
    --output results/aapl_full_test.json \
    --verbose

다양한 종목 테스트:
------------------
# 기술주
python scripts/run_simulation.py --ticker AAPL --seed 42
python scripts/run_simulation.py --ticker MSFT --seed 42
python scripts/run_simulation.py --ticker GOOGL --seed 42
python scripts/run_simulation.py --ticker NVDA --seed 42

# 전기차
python scripts/run_simulation.py --ticker TSLA --seed 42

# 메타버스/소셜
python scripts/run_simulation.py --ticker META --seed 42

다양한 시간 간격 테스트:
-----------------------
# 15분봉
python scripts/run_simulation.py --ticker AAPL --interval 15m --window 96

# 1시간봉 (기본)
python scripts/run_simulation.py --ticker AAPL --interval 1h --window 30

# 4시간봉
python scripts/run_simulation.py --ticker AAPL --interval 4h --window 30

# 일봉
python scripts/run_simulation.py --ticker AAPL --mode daily --interval 1day --window 60
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from services.simulation import SimulationService


def print_header(title: str, width: int = 70):
    """예쁜 헤더 출력"""
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def print_section(title: str, width: int = 70):
    """섹션 구분선 출력"""
    print("\n" + "-" * width)
    print(f"  {title}")
    print("-" * width)


def format_number(value, decimals=2):
    """숫자 포맷팅 (천단위 구분)"""
    if value is None:
        return "N/A"
    if isinstance(value, (int, float)):
        return f"{value:,.{decimals}f}"
    return str(value)


async def main():
    parser = argparse.ArgumentParser(
        description="🚀 FinMem Trading 시뮬레이션 - AI 기반 트레이딩 의사결정 시뮬레이터",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  기본 실행:
    python scripts/run_simulation.py --ticker AAPL

  재현 가능한 실행:
    python scripts/run_simulation.py --ticker AAPL --seed 42

  일봉 데이터 분석:
    python scripts/run_simulation.py --ticker TSLA --mode daily --interval 1day

  상세 로그 + 결과 저장:
    python scripts/run_simulation.py --ticker NVDA --verbose --output results/nvda_test.json

  메모리/뉴스 비활성화:
    python scripts/run_simulation.py --ticker MSFT --no-memory --no-news

  완전한 설정:
    python scripts/run_simulation.py --ticker AAPL --window 60 --seed 42 \\
        --initial-capital 100000 --max-steps 100 --verbose
        """,
    )

    # ========================================================================
    # 필수 인자
    # ========================================================================
    parser.add_argument(
        "--ticker",
        type=str,
        required=True,
        help="종목 심볼 (예: AAPL, TSLA, GOOGL, MSFT, NVDA, AMD, META)",
    )

    # ========================================================================
    # 데이터 설정
    # ========================================================================
    data_group = parser.add_argument_group("📊 데이터 설정")

    data_group.add_argument(
        "--window",
        type=int,
        default=30,
        help="분석에 사용할 데이터 윈도우 크기 (기본: 30) - 최근 N개의 데이터 포인트를 사용",
    )

    data_group.add_argument(
        "--mode",
        type=str,
        default="intraday",
        choices=["intraday", "daily"],
        help="데이터 모드 (기본: intraday) - intraday: 장중 데이터, daily: 일봉 데이터",
    )

    data_group.add_argument(
        "--interval",
        type=str,
        default="1h",
        help="시간 간격 (기본: 1h) - 예: 5m, 15m, 30m, 1h, 2h, 4h, 1day 등",
    )

    # ========================================================================
    # 기능 토글
    # ========================================================================
    feature_group = parser.add_argument_group("🎛️  기능 설정")

    feature_group.add_argument(
        "--no-news",
        action="store_true",
        help="뉴스 분석 비활성화 - 순수 가격 데이터만으로 분석",
    )

    feature_group.add_argument(
        "--no-memory",
        action="store_true",
        help="메모리 기능 비활성화 - 과거 거래 기억 없이 매번 새롭게 분석",
    )

    # ========================================================================
    # 시뮬레이션 파라미터
    # ========================================================================
    sim_group = parser.add_argument_group("⚙️  시뮬레이션 설정")

    sim_group.add_argument(
        "--seed",
        type=int,
        default=None,
        help="재현성을 위한 랜덤 시드 (기본: None, 랜덤) - 같은 시드 = 같은 결과",
    )

    sim_group.add_argument(
        "--initial-capital",
        type=float,
        default=10000.0,
        help="초기 자본금 (기본: 10000.0) - 시뮬레이션 시작 자금",
    )

    sim_group.add_argument(
        "--max-steps",
        type=int,
        default=None,
        help="최대 거래 스텝 수 (기본: None, 무제한) - 시뮬레이션 최대 반복 횟수",
    )

    sim_group.add_argument(
        "--commission",
        type=float,
        default=0.001,
        help="거래 수수료율 (기본: 0.001 = 0.1%%) - 매매시 발생하는 수수료",
    )

    # ========================================================================
    # 출력 및 로깅
    # ========================================================================
    output_group = parser.add_argument_group("💾 출력 설정")

    output_group.add_argument(
        "--output",
        type=str,
        default=None,
        help="결과 저장 경로 (기본: results/simulation_<ticker>_<seed>.json)",
    )

    output_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="상세 로그 출력 - 더 많은 정보를 터미널에 출력",
    )

    output_group.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="최소 출력 모드 - 필수 정보만 출력",
    )

    args = parser.parse_args()

    # ========================================================================
    # 플래그 처리
    # ========================================================================
    include_news = not args.no_news
    use_memory = not args.no_memory

    # ========================================================================
    # 시작 메시지
    # ========================================================================
    if not args.quiet:
        print_header("🚀 FinMem Trading Simulation", 70)
        print(f"\n📅 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        print_section("📋 시뮬레이션 설정", 70)
        print(f"  종목 심볼        : {args.ticker}")
        print(f"  데이터 윈도우    : {args.window}개")
        print(f"  데이터 모드      : {args.mode}")
        print(f"  시간 간격        : {args.interval}")
        print(f"  랜덤 시드        : {args.seed if args.seed else '랜덤'}")

        print_section("💰 거래 설정", 70)
        print(f"  초기 자본금      : ${format_number(args.initial_capital)}")
        print(f"  거래 수수료      : {args.commission * 100}%")
        print(f"  최대 스텝        : {args.max_steps if args.max_steps else '무제한'}")

        print_section("🎛️  기능 설정", 70)
        print(f"  뉴스 분석        : {'✅ 활성화' if include_news else '❌ 비활성화'}")
        print(f"  메모리 사용      : {'✅ 활성화' if use_memory else '❌ 비활성화'}")

        print_section("🤖 AI 모델 설정", 70)
        print(f"  LLM 모델         : {settings.ollama_model}")
        print(f"  API 엔드포인트   : {settings.ollama_base_url}")

        if args.verbose:
            print_section("🔍 추가 정보", 70)
            print(f"  작업 디렉토리    : {Path.cwd()}")
            print(f"  결과 저장 경로   : {args.output if args.output else '자동 생성'}")

        print("\n" + "=" * 70)
        print("\n⏳ 시뮬레이션을 시작합니다...\n")

    # ========================================================================
    # 시뮬레이션 실행
    # ========================================================================
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

        # ====================================================================
        # 결과 출력
        # ====================================================================
        if not args.quiet:
            print("\n" + "=" * 70)
            print("  ✅ 시뮬레이션 완료!")
            print("=" * 70)

        summary = result.summary
        decision = summary.get("decision", {})
        metrics = summary.get("metrics", {})

        if not args.quiet:
            print_section("📊 매매 결정", 70)
            print(f"  결정            : {decision.get('action', 'N/A')}")
            print(f"  신뢰도          : {decision.get('confidence', 'N/A')}")

            rationale = decision.get("rationale", "N/A")
            if args.verbose and rationale != "N/A":
                print(f"\n  💭 결정 근거:")
                # 근거를 줄바꿈하여 출력
                for line in rationale.split("\n"):
                    if line.strip():
                        print(f"     {line.strip()}")
            else:
                # 간략하게 출력
                rationale_short = (
                    rationale[:150] + "..." if len(rationale) > 150 else rationale
                )
                print(f"  근거            : {rationale_short}")

        # 메트릭스 출력
        if metrics and not args.quiet:
            print_section("📈 성과 지표", 70)

            if "total_return" in metrics:
                print(
                    f"  총 수익률       : {format_number(metrics.get('total_return', 0) * 100)}%"
                )

            if "final_capital" in metrics:
                print(
                    f"  최종 자본금     : ${format_number(metrics.get('final_capital', args.initial_capital))}"
                )

            if "total_trades" in metrics:
                print(f"  총 거래 횟수    : {metrics.get('total_trades', 0)}회")

            if "win_rate" in metrics:
                print(
                    f"  승률            : {format_number(metrics.get('win_rate', 0) * 100)}%"
                )

            if args.verbose and "sharpe_ratio" in metrics:
                print(
                    f"  샤프 비율       : {format_number(metrics.get('sharpe_ratio', 0))}"
                )

            if args.verbose and "max_drawdown" in metrics:
                print(
                    f"  최대 낙폭       : {format_number(metrics.get('max_drawdown', 0) * 100)}%"
                )

        # ====================================================================
        # 결과 저장
        # ====================================================================
        if args.output:
            output_path = Path(args.output)
        else:
            # 기본 저장 경로 생성
            output_dir = Path("results")
            output_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            seed_str = str(args.seed) if args.seed else "random"
            output_path = (
                output_dir / f"simulation_{args.ticker}_{seed_str}_{timestamp}.json"
            )

        # 디렉토리 생성
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 추가 메타데이터 포함
        full_result = {
            "metadata": {
                "ticker": args.ticker,
                "timestamp": datetime.now().isoformat(),
                "settings": {
                    "window": args.window,
                    "mode": args.mode,
                    "interval": args.interval,
                    "seed": args.seed,
                    "initial_capital": args.initial_capital,
                    "commission": args.commission,
                    "max_steps": args.max_steps,
                    "include_news": include_news,
                    "use_memory": use_memory,
                },
                "llm_model": settings.ollama_model,
            },
            "results": summary,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(full_result, f, indent=2, ensure_ascii=False)

        if not args.quiet:
            print_section("💾 결과 저장", 70)
            print(f"  저장 경로       : {output_path}")
            print(f"  파일 크기       : {output_path.stat().st_size:,} bytes")

            print("\n" + "=" * 70)
            print(f"  📅 종료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 70 + "\n")
        else:
            print(f"✅ 완료 - 결과 저장: {output_path}")

    except KeyboardInterrupt:
        print("\n\n⚠️  사용자에 의해 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        if args.verbose:
            import traceback

            print("\n" + "=" * 70)
            print("  상세 에러 정보:")
            print("=" * 70)
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

"""
메모리 초기화 스크립트

Redis와 PostgreSQL에 저장된 메모리 및 로그를 초기화합니다.
각 실험 전에 실행하여 독립성을 보장하세요.

사용예:
    # 전체 초기화
    python scripts/reset_memory.py --all

    # Redis만 초기화
    python scripts/reset_memory.py --redis

    # PostgreSQL만 초기화
    python scripts/reset_memory.py --postgres

    # 특정 ticker만 초기화
    python scripts/reset_memory.py --ticker AAPL
"""
import argparse
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings


async def reset_redis(ticker: str = None):
    """Redis 메모리 초기화"""
    try:
        import redis
        from redis.commands.search.indexDefinition import IndexDefinition, IndexType

        print("\n📦 Redis 연결 중...")
        r = redis.from_url(settings.redis_url, decode_responses=True)

        # Redis 연결 확인
        r.ping()
        print(f"✅ Redis 연결 성공: {settings.redis_url}")

        if ticker:
            # 특정 ticker의 키만 삭제
            pattern = f"*{ticker}*"
            keys = r.keys(pattern)
            if keys:
                deleted = r.delete(*keys)
                print(f"✅ {ticker} 관련 키 {deleted}개 삭제됨")
            else:
                print(f"⚠️  {ticker} 관련 키가 없습니다")
        else:
            # 전체 삭제
            print("\n⚠️  경고: 모든 Redis 키를 삭제합니다!")
            confirm = input("계속하시겠습니까? (yes/no): ")
            if confirm.lower() != "yes":
                print("❌ 취소됨")
                return

            # FT.DROPINDEX로 인덱스 삭제
            try:
                r.execute_command(f"FT.DROPINDEX {settings.redis_index} DD")
                print(f"✅ 인덱스 '{settings.redis_index}' 삭제됨")
            except Exception as e:
                print(f"⚠️  인덱스 삭제 실패 (없을 수도 있음): {e}")

            # FLUSHDB로 전체 DB 초기화
            r.flushdb()
            print("✅ Redis DB 초기화 완료")

    except ImportError:
        print("❌ redis 패키지가 설치되지 않았습니다.")
        print("   설치: uv pip install redis")
    except Exception as e:
        print(f"❌ Redis 초기화 실패: {e}")
        print("   Redis가 실행 중이 아니거나 연결 정보가 잘못되었습니다.")


async def reset_postgres(ticker: str = None):
    """PostgreSQL 시뮬레이션 로그 초기화"""
    try:
        from db.session import SessionLocal, engine
        from db.models import Base, Simulation, AgentLog, Backtest, BacktestTrade

        print("\n🐘 PostgreSQL 연결 중...")

        # 테이블 존재 확인
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print(f"✅ PostgreSQL 연결 성공")

        async with SessionLocal() as session:
            if ticker:
                # 특정 ticker의 데이터만 삭제
                from sqlalchemy import delete

                # Simulations
                result = await session.execute(delete(Simulation).where(Simulation.ticker == ticker))
                sim_deleted = result.rowcount

                # Backtests
                result = await session.execute(delete(Backtest).where(Backtest.ticker == ticker))
                backtest_deleted = result.rowcount

                await session.commit()
                print(f"✅ {ticker} 관련 레코드 삭제: Simulations({sim_deleted}), Backtests({backtest_deleted})")

            else:
                # 전체 삭제
                print("\n⚠️  경고: 모든 시뮬레이션 로그를 삭제합니다!")
                confirm = input("계속하시겠습니까? (yes/no): ")
                if confirm.lower() != "yes":
                    print("❌ 취소됨")
                    return

                # 테이블 drop & recreate
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.drop_all)
                    await conn.run_sync(Base.metadata.create_all)

                print("✅ PostgreSQL 테이블 초기화 완료")

    except ImportError:
        print("❌ PostgreSQL 관련 패키지가 설치되지 않았습니다.")
        print("   설치: uv pip install asyncpg sqlalchemy")
    except Exception as e:
        print(f"❌ PostgreSQL 초기화 실패: {e}")
        print("   PostgreSQL이 실행 중이 아니거나 연결 정보가 잘못되었습니다.")


async def check_memory_mode():
    """현재 메모리 모드 확인"""
    print("\n🔍 메모리 시스템 확인 중...")

    # Redis 확인
    try:
        import redis

        r = redis.from_url(settings.redis_url, decode_responses=True)
        r.ping()
        print("✅ Redis: 사용 가능 (영구 메모리 모드)")
        redis_available = True
    except Exception:
        print("❌ Redis: 사용 불가 (InMemory 모드로 작동)")
        redis_available = False

    # PostgreSQL 확인
    try:
        from db.session import engine

        async with engine.connect():
            pass
        print("✅ PostgreSQL: 사용 가능")
        postgres_available = True
    except Exception:
        print("❌ PostgreSQL: 사용 불가")
        postgres_available = False

    print("\n📋 현재 설정:")
    print(f"  - REDIS_URL: {settings.redis_url}")
    print(f"  - DATABASE_URL: {settings.db_url}")
    print(f"  - EMBEDDING_MODE: {settings.embedding_mode}")

    if not redis_available and not postgres_available:
        print("\n💡 InMemory 모드로 작동 중입니다.")
        print("   각 백테스트마다 메모리가 자동 초기화되므로 별도의 초기화가 필요 없습니다.")
    else:
        print("\n⚠️  영구 저장소 사용 중입니다.")
        print("   각 실험 전에 메모리 초기화를 권장합니다.")

    return redis_available, postgres_available


async def main():
    parser = argparse.ArgumentParser(description="메모리 초기화 스크립트")

    # 초기화 대상
    parser.add_argument("--all", action="store_true", help="Redis + PostgreSQL 모두 초기화")
    parser.add_argument("--redis", action="store_true", help="Redis만 초기화")
    parser.add_argument("--postgres", action="store_true", help="PostgreSQL만 초기화")

    # 선택적 필터
    parser.add_argument("--ticker", type=str, help="특정 ticker만 초기화 (예: AAPL)")

    # 확인 모드
    parser.add_argument("--check", action="store_true", help="현재 메모리 모드만 확인")

    args = parser.parse_args()

    print("=" * 80)
    print("🔧 메모리 초기화 스크립트")
    print("=" * 80)

    # 확인 모드
    if args.check:
        await check_memory_mode()
        return

    # 초기화 대상 확인
    if not (args.all or args.redis or args.postgres):
        print("\n❌ 초기화 대상을 지정하세요:")
        print("  --all        : Redis + PostgreSQL 모두")
        print("  --redis      : Redis만")
        print("  --postgres   : PostgreSQL만")
        print("  --check      : 현재 모드만 확인")
        parser.print_help()
        sys.exit(1)

    # Redis 초기화
    if args.all or args.redis:
        await reset_redis(ticker=args.ticker)

    # PostgreSQL 초기화
    if args.all or args.postgres:
        await reset_postgres(ticker=args.ticker)

    print("\n" + "=" * 80)
    print("✅ 초기화 완료!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

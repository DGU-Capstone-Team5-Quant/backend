"""
Redis 메모리 상태 확인 스크립트

메모리에 얼마나 많은 데이터가 저장되어 있는지 확인합니다.

사용예:
    python scripts/check_memory.py
    python scripts/check_memory.py --ticker AAPL
"""
import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from services.llm import build_embeddings
from memory.redis_store import build_vector_store


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Redis 메모리 상태 확인")
    parser.add_argument("--ticker", type=str, help="특정 ticker 필터")
    args = parser.parse_args()

    print("=" * 80)
    print("📊 Redis 메모리 상태 확인")
    print("=" * 80)

    try:
        import redis
        r = redis.from_url(settings.redis_url, decode_responses=True)
        r.ping()
        print("✅ Redis 연결 성공\n")

        # 전체 키 개수
        total_keys = r.dbsize()
        print(f"📦 전체 Redis 키 개수: {total_keys}")

        # 메모리 키 검색
        if args.ticker:
            pattern = f"*{args.ticker}*"
        else:
            pattern = "*"

        keys = r.keys(pattern)
        print(f"🔍 패턴 '{pattern}' 매칭: {len(keys)}개 키")

        # 샘플 출력 (최대 10개)
        if keys:
            print("\n📝 샘플 키 (최대 10개):")
            for key in keys[:10]:
                print(f"  - {key}")
            if len(keys) > 10:
                print(f"  ... 외 {len(keys) - 10}개")

        # Vector Store 검색 테스트
        print("\n" + "=" * 80)
        print("🔎 Vector Store 검색 테스트")
        print("=" * 80)

        vector_results = []
        all_results = []
        try:
            embeddings = build_embeddings(
                model_name=settings.ollama_embedding_model,
                base_url=settings.ollama_base_url,
            )
            store = build_vector_store(settings, embeddings)

            # 테스트 쿼리
            query = f"{args.ticker or 'AAPL'} market"
            print(f"쿼리: '{query}'")

            # 먼저 많은 수를 가져와서 실제 저장된 개수 확인
            all_results = store.similarity_search_with_score(query, k=1000)
            vector_results = all_results[:5]  # 샘플 출력용

            print(f"✅ 전체 검색 결과: {len(all_results)}개")
            print(f"   (샘플 5개만 출력)")

            if vector_results:
                print("\n📄 검색 결과 샘플:")
                for i, (doc, score) in enumerate(vector_results[:3], 1):
                    content = doc.page_content[:100]
                    metadata = doc.metadata or {}
                    role = metadata.get("role", "unknown")
                    ticker = metadata.get("ticker", "N/A")
                    print(f"\n  [{i}] Score: {score:.4f}")
                    print(f"      Role: {role}, Ticker: {ticker}")
                    print(f"      Content: {content}...")
            else:
                print("⚠️  검색 결과가 없습니다.")
                print("   → 메모리가 비어있거나 임베딩이 생성되지 않았습니다.")

        except Exception as e:
            print(f"❌ Vector Store 검색 실패: {e}")

        print("\n" + "=" * 80)
        print("💡 메모리 상태 해석:")
        print("=" * 80)

        if total_keys == 0:
            print("⚠️  메모리가 완전히 비어있습니다.")
            print("   → 백테스트를 한 번도 실행하지 않았거나 최근에 초기화했습니다.")
        elif len(all_results) == 0:
            print(f"⚠️  {args.ticker or '전체'} 관련 메모리가 없습니다.")
            print(f"   → 백테스트를 실행해보세요.")
        else:
            # 티커 필터링 확인
            if args.ticker:
                ticker_matches = [doc for doc, _ in all_results if doc.metadata and doc.metadata.get("ticker") == args.ticker]
                if ticker_matches:
                    print(f"✅ {args.ticker} 메모리가 총 {len(ticker_matches)}개 저장되어 있습니다.")
                    print("   → use-memory 실험이 의미 있는 데이터를 사용합니다.")

                    # Role별 통계
                    from collections import Counter
                    roles = [doc.metadata.get("role", "unknown") for doc, _ in ticker_matches if doc.metadata]
                    role_counts = Counter(roles)
                    print("\n   📊 Role별 분포:")
                    for role, count in role_counts.most_common():
                        print(f"      - {role}: {count}개")
                else:
                    print(f"⚠️  {args.ticker} 관련 메모리가 없습니다.")
                    print(f"   → 검색 결과는 있지만 다른 종목 데이터입니다.")
            else:
                print(f"✅ 메모리가 총 {len(all_results)}개 정상적으로 저장되어 있습니다.")
                print("   → use-memory 실험이 의미 있는 데이터를 사용합니다.")

    except ImportError:
        print("❌ redis 패키지가 설치되지 않았습니다.")
        print("   설치: uv pip install redis")
    except Exception as e:
        print(f"❌ 실패: {e}")


if __name__ == "__main__":
    asyncio.run(main())

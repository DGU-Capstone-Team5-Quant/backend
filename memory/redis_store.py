from typing import Optional

import redis.asyncio as redis
from langchain.embeddings.base import Embeddings
try:
    from langchain_redis import RedisVectorStore
except (ImportError, ModuleNotFoundError):
    from langchain_community.vectorstores import Redis as RedisVectorStore

from config import Settings


def get_redis_client(settings: Settings) -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def build_vector_store(settings: Settings, embedding: Embeddings, index_name: Optional[str] = None) -> RedisVectorStore:
    # Redis vector store는 빈 텍스트로 초기화 불가 - 더미 텍스트로 초기화 후 삭제
    store = RedisVectorStore.from_texts(
        texts=["initialization dummy text"],
        embedding=embedding,
        redis_url=settings.redis_url,
        index_name=index_name or settings.redis_index,
    )
    # 더미 텍스트 삭제 (인덱스는 유지)
    try:
        store.delete(["0"])  # 첫 번째 텍스트의 ID는 보통 "0"
    except Exception:
        pass  # 삭제 실패해도 괜찮음 (인덱스만 생성되면 됨)
    return store

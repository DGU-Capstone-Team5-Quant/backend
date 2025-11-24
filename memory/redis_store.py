from typing import Optional

import redis.asyncio as redis
from langchain.embeddings.base import Embeddings
from langchain_community.vectorstores import Redis as RedisVectorStore

from config import Settings


def get_redis_client(settings: Settings) -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def build_vector_store(settings: Settings, embedding: Embeddings, index_name: Optional[str] = None) -> RedisVectorStore:
    # RedisVectorStore는 add_texts 호출 시 인덱스가 없으면 생성한다.
    return RedisVectorStore(
        redis_url=settings.redis_url,
        index_name=index_name or settings.redis_index,
        embedding=embedding,
    )

from typing import Optional

import redis.asyncio as redis
from langchain.embeddings.base import Embeddings
from langchain_redis import RedisVectorStore

from config import Settings


def get_redis_client(settings: Settings) -> redis.Redis:
    return redis.from_url(settings.redis_url, decode_responses=True)


def build_vector_store(settings: Settings, embedding: Embeddings, index_name: Optional[str] = None) -> RedisVectorStore:
    return RedisVectorStore.from_texts(
        texts=[],
        embedding=embedding,
        redis_url=settings.redis_url,
        index_name=index_name or settings.redis_index,
    )

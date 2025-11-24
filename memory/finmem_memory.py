from __future__ import annotations

from typing import Any, Dict, List
from uuid import uuid4

from langchain_community.vectorstores import Redis as RedisVectorStore


class FinMemMemory:
    def __init__(self, store: RedisVectorStore):
        self.store = store

    async def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        docs = self.store.similarity_search(query, k=k)
        return [{"content": doc.page_content, "metadata": doc.metadata} for doc in docs]

    async def add_memory(self, content: str, metadata: Dict[str, Any]) -> str:
        memory_id = str(uuid4())
        self.store.add_texts([content], metadatas=[metadata], ids=[memory_id])
        return memory_id


class InMemoryMemory:
    """
    간단한 폴백 메모리 구현 (Redis 미사용 환경 대비).
    """

    def __init__(self) -> None:
        self._store: List[Dict[str, Any]] = []

    async def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        # 길이 기반의 매우 단순한 매칭으로 대체.
        sorted_store = sorted(self._store, key=lambda m: abs(len(m.get("content", "")) - len(query)))
        return sorted_store[:k]

    async def add_memory(self, content: str, metadata: Dict[str, Any]) -> str:
        memory_id = str(uuid4())
        self._store.append({"id": memory_id, "content": content, "metadata": metadata})
        return memory_id

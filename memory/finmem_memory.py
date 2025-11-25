from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from langchain_redis import RedisVectorStore


class FinMemMemory:
    def __init__(
        self,
        store: RedisVectorStore,
        *,
        recency_lambda: float = 0.01,
        duplicate_threshold: float = 0.9,
        ttl_days: float = 30.0,
        role_weights: Optional[Dict[str, float]] = None,
    ):
        self.store = store
        self.recency_lambda = recency_lambda
        self.duplicate_threshold = duplicate_threshold
        self.ttl_days = ttl_days
        self.role_weights = role_weights or {"manager": 1.5, "trader": 1.2, "bull": 1.0, "bear": 1.0, "mem": 1.0}

    async def search(
        self,
        query: str,
        k: int = 5,
        *,
        ticker: Optional[str] = None,
        roles: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        try:
            docs_scores = self.store.similarity_search_with_score(query, k=k * 3)
        except Exception:
            docs_scores = []
        results: List[Tuple[Dict[str, Any], float]] = []
        now = time.time()
        for doc, sim in docs_scores:
            md = doc.metadata or {}
            if ticker and md.get("ticker") != ticker:
                continue
            if roles and md.get("role") not in roles:
                continue
            age_days = self._age_days(md, now)
            if self.ttl_days and age_days > self.ttl_days:
                continue
            role = md.get("role", "mem")
            role_weight = self.role_weights.get(role, 1.0)
            score = sim * role_weight - self.recency_lambda * age_days
            results.append(({"content": doc.page_content, "metadata": md}, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:k]]

    async def add_memory(self, content: str, metadata: Dict[str, Any]) -> str:
        metadata = dict(metadata)
        metadata.setdefault("created_at", time.time())
        if await self._is_duplicate(content, metadata):
            return "deduped"
        memory_id = str(uuid4())
        self.store.add_texts([content], metadatas=[metadata], ids=[memory_id])
        return memory_id

    async def _is_duplicate(self, content: str, metadata: Dict[str, Any]) -> bool:
        """
        간단한 중복 억제: 동일 티커/역할에서 높은 유사도 문서가 있으면 저장 생략.
        """
        try:
            docs_scores = self.store.similarity_search_with_score(content, k=1, filter=metadata)
            if docs_scores and docs_scores[0][1] >= self.duplicate_threshold:
                return True
        except Exception:
            return False
        return False

    @staticmethod
    def _age_days(metadata: Dict[str, Any], now: float) -> float:
        ts = metadata.get("created_at")
        if not ts:
            return 0.0
        try:
            return max(0.0, (now - float(ts)) / 86400.0)
        except Exception:
            return 0.0


class InMemoryMemory:
    """
    간단한 폴백 메모리 구현 (Redis 미사용 환경 대비).
    """

    def __init__(self) -> None:
        self._store: List[Dict[str, Any]] = []
        self.recency_lambda = 0.01
        self.ttl_days = 30.0
        self.role_weights = {"manager": 1.5, "trader": 1.2, "bull": 1.0, "bear": 1.0, "mem": 1.0}

    async def search(
        self,
        query: str,
        k: int = 5,
        *,
        ticker: Optional[str] = None,
        roles: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        now = time.time()
        scored = []
        for m in self._store:
            md = m.get("metadata", {})
            if ticker and md.get("ticker") != ticker:
                continue
            if roles and md.get("role") not in roles:
                continue
            age_days = self._age_days(md, now)
            if self.ttl_days and age_days > self.ttl_days:
                continue
            sim = 1.0 / (1.0 + abs(len(m.get("content", "")) - len(query)))
            role = md.get("role", "mem")
            role_weight = self.role_weights.get(role, 1.0)
            score = sim * role_weight - self.recency_lambda * age_days
            scored.append((m, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [m for m, _ in scored[:k]]

    async def add_memory(self, content: str, metadata: Dict[str, Any]) -> str:
        memory_id = str(uuid4())
        md = dict(metadata)
        md.setdefault("created_at", time.time())
        self._store.append({"id": memory_id, "content": content, "metadata": md})
        return memory_id

    @staticmethod
    def _age_days(metadata: Dict[str, Any], now: float) -> float:
        ts = metadata.get("created_at")
        if not ts:
            return 0.0
        try:
            return max(0.0, (now - float(ts)) / 86400.0)
        except Exception:
            return 0.0

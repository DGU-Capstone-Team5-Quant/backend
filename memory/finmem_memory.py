from __future__ import annotations

import time
import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

try:
    from langchain_redis import RedisVectorStore
except (ImportError, ModuleNotFoundError):
    from langchain_community.vectorstores import Redis as RedisVectorStore
from services.llm import BaseLLMClient


class FinMemMemory:
    def __init__(
        self,
        store: RedisVectorStore,
        *,
        recency_lambda: float = 0.01,
        duplicate_threshold: float = 0.9,
        ttl_days: float = 30.0,
        role_weights: Optional[Dict[str, float]] = None,
        rollup_count: int = 50,
        rollup_target: int = 10,
        llm: Optional[BaseLLMClient] = None,
        salience_weight: float = 0.0,
        score_cutoff: float = 0.0,
        min_length: int = 50,
        skip_stub: bool = True,
        is_stub_embedding: bool = True,
        expected_dim: int = 768,
        logger: Optional[logging.Logger] = None,
        gc_batch: int = 50,
    ):
        self.store = store
        self.recency_lambda = recency_lambda
        self.duplicate_threshold = duplicate_threshold
        self.ttl_days = ttl_days
        self.role_weights = role_weights or {"manager": 1.5, "trader": 1.2, "bull": 1.0, "bear": 1.0, "mem": 1.0}
        self.rollup_count = rollup_count
        self.rollup_target = rollup_target
        self.llm = llm
        self.salience_weight = salience_weight
        self.score_cutoff = score_cutoff
        self.min_length = min_length
        self.skip_stub = skip_stub
        self.is_stub_embedding = is_stub_embedding
        self.gc_batch = gc_batch
        self.logger = logger or logging.getLogger(__name__)
        self.expected_dim = expected_dim
        self._check_index_dimension()

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
            sal = md.get("salience", md.get("pnl", 0.0))
            score = sim * role_weight - self.recency_lambda * age_days + self.salience_weight * float(sal)
            if score < self.score_cutoff:
                continue
            results.append(({"content": doc.page_content, "metadata": md}, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:k]]

    async def add_memory(self, content: str, metadata: Dict[str, Any]) -> str:
        if self.skip_stub and self.is_stub_embedding:
            if self.logger:
                self.logger.info("skip LTM write because embedding mode is stub")
            return "skipped_stub"
        if len(content or "") < self.min_length:
            return "skipped_short"
        metadata = dict(metadata)
        metadata.setdefault("created_at", time.time())
        if await self._is_duplicate(content, metadata):
            return "deduped"
        memory_id = str(uuid4())
        self.store.add_texts([content], metadatas=[metadata], ids=[memory_id])
        # 롤업 조건: manager 리포트가 rollup_count 배수일 때 요약
        if metadata.get("role") == "manager" and self.llm:
            try:
                count = self.store.client.zcard(self.store.index_name)
            except Exception:
                count = 0
            if count and count % self.rollup_count == 0:
                await self._rollup_manager(metadata.get("ticker"))
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

    async def _rollup_manager(self, ticker: Optional[str]) -> None:
        """
        오래된 Manager 리포트를 상위 rollup_target개로 요약하고 압축 저장.
        """
        try:
            docs = await self.search("manager report", k=self.rollup_count, ticker=ticker, roles=["manager"])
            if not docs:
                return
            contents = [d.get("content", "") for d in docs]
            prompt = "다음 매니저 리포트를 간결하게 요약해 주세요:\n" + "\n\n".join(contents[: self.rollup_target])
            summary = await self.llm.generate(prompt)
            await self.add_memory(summary, {"role": "manager", "ticker": ticker})
            await self._gc_expired()
        except Exception:
            pass

    def _check_index_dimension(self) -> None:
        """
        Redis 인덱스 차원 정보를 확인하고 기대값과 다르면 경고를 남긴다.
        """
        try:
            info = self.store.client.ft(self.store.index_name).info()
            # attributes 구조가 RedisStack 버전에 따라 달라질 수 있음
            attrs = info.get("attributes") or []
            dim = None
            for a in attrs:
                if isinstance(a, dict) and a.get("attribute") == "content_vector":
                    dim = a.get("dim") or a.get("DIM")
                    break
            if dim and int(dim) != int(self.expected_dim):
                self.logger.warning("Redis index dim %s != expected %s", dim, self.expected_dim)
        except Exception:
            self.logger.info("Could not verify Redis index dimension for %s", getattr(self.store, 'index_name', 'unknown'))

    async def _gc_expired(self) -> None:
        """
        TTL이 지난 manager 리포트를 삭제 (배치 크기 제한).
        """
        if not self.ttl_days:
            return
        try:
            docs = await self.search("manager report", k=self.gc_batch, ticker=None, roles=["manager"])
            now = time.time()
            expired_ids = []
            for doc in docs:
                md = doc.get("metadata", {})
                age_days = self._age_days(md, now)
                if age_days > self.ttl_days and md.get("id"):
                    expired_ids.append(md["id"])
            if expired_ids:
                self.store.delete(expired_ids)
        except Exception:
            pass


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

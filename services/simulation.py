from __future__ import annotations

from dataclasses import dataclass
import json
import time
import logging
import timeit
from typing import Any, Dict, Optional, List
from uuid import uuid4

from config import Settings
from agents.graph import TradeState
from agents import prompts
from memory.finmem_memory import FinMemMemory, InMemoryMemory
from memory.redis_store import build_vector_store
from services.data_loader import MarketDataLoader
from services.llm import build_embeddings, build_llm
from services.metrics import metrics_tracker
from db.session import SessionLocal
from db.models import AgentLog, Simulation
from services.feedback import FeedbackService


@dataclass
class SimulationResult:
    simulation_id: str
    summary: Dict[str, Any]
    status: str = "completed"


class SimulationService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.loader = MarketDataLoader(settings)
        self.llm = build_llm(
            model_name=settings.ollama_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
            base_url=settings.ollama_base_url,
        )
        self.memory = self._build_memory()
        self._records: Dict[str, SimulationResult] = {}
        self.logger = logging.getLogger(__name__)
        self.feedback_service = FeedbackService(settings, self.memory, self.loader)
        self.logger.info(
            "SimulationService initialized: llm=%s embedding_mode=%s environment=%s",
            type(self.llm).__name__,
            settings.embedding_mode,
            settings.environment,
        )

    async def run(
        self,
        ticker: str,
        window: int,
        include_news: bool = True,
        mode: str = "intraday",
        interval: str = "1h",
        start_date: str | None = None,
        end_date: str | None = None,
        news_limit: int = 5,
        news_page: int = 0,
        bb_rounds: int | None = None,
        memory_store_manager_only: bool | None = None,
        seed: Optional[int] = None,
        use_memory: bool = True,
    ) -> SimulationResult:
        t0 = timeit.default_timer()
        try:
            snapshot = await self.loader.load_snapshot(
                ticker,
                window,
                mode=mode,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
                news_limit=news_limit if include_news else 0,
                news_page=news_page,
            )
            result = await self.run_on_snapshot(
                snapshot=snapshot,
                ticker=ticker,
                include_news=include_news,
                bb_rounds=bb_rounds,
                memory_store_manager_only=memory_store_manager_only,
                seed=seed,
                use_memory=use_memory,
                mode=mode,
                interval=interval,
                news_limit=news_limit,
                news_page=news_page,
            )
            metrics_tracker.record_simulation(success=True, duration=timeit.default_timer() - t0)
            return result
        except Exception:
            metrics_tracker.record_simulation(success=False, duration=timeit.default_timer() - t0)
            raise

    async def get(self, simulation_id: str) -> Optional[SimulationResult]:
        if simulation_id in self._records:
            return self._records[simulation_id]
        try:
            async with SessionLocal() as session:
                sim = await session.get(Simulation, simulation_id)
                if sim:
                    return SimulationResult(simulation_id=sim.id, summary=json.loads(sim.summary or "{}"), status=sim.status)
        except Exception:
            return None
        return None

    def _build_memory(self) -> FinMemMemory | InMemoryMemory:
        try:
            embeddings = build_embeddings(mode=self.settings.embedding_mode)
            store = build_vector_store(self.settings, embeddings)
            return FinMemMemory(
                store,
                recency_lambda=self.settings.memory_recency_lambda,
                duplicate_threshold=self.settings.memory_duplicate_threshold,
                ttl_days=self.settings.memory_ttl_days,
                role_weights=self.settings.memory_role_weights,
                rollup_count=self.settings.memory_rollup_count,
                rollup_target=self.settings.memory_rollup_target,
                llm=self.llm,
                salience_weight=self.settings.memory_salience_weight,
                score_cutoff=self.settings.memory_score_cutoff,
                min_length=self.settings.memory_min_length,
                skip_stub=self.settings.memory_skip_stub,
                is_stub_embedding=self.settings.embedding_mode == "stub",
                gc_batch=self.settings.memory_gc_batch,
                expected_dim=self.settings.redis_vector_dim,
                logger=logging.getLogger("finmem"),
            )
        except Exception:
            return InMemoryMemory()

    async def run_on_snapshot(
        self,
        snapshot: Dict[str, Any],
        ticker: str,
        include_news: bool = True,
        bb_rounds: int | None = None,
        memory_store_manager_only: bool | None = None,
        seed: Optional[int] = None,
        use_memory: bool = True,
        mode: str | None = None,
        interval: str | None = None,
        news_limit: int | None = None,
        news_page: int | None = None,
    ) -> SimulationResult:
        bb_rounds = bb_rounds or self.settings.max_rounds_bull_bear
        if bb_rounds < 1:
            raise ValueError("bb_rounds must be >= 1")
        memory_store_flag = (
            self.settings.memory_store_manager_only if memory_store_manager_only is None else memory_store_manager_only
        )
        ltm_memories = await self.memory.search(f"{ticker} market", k=self.settings.memory_search_k, ticker=ticker) if use_memory else []
        initial_state = TradeState(snapshot=snapshot, memories=ltm_memories, working_mem=[])
        final_state = await self._run_manual_rounds(
            initial_state, bb_rounds=bb_rounds, memory_store_manager_only=memory_store_flag, seed=seed
        )

        summary = {
            "decision": self._safe_json(final_state.decision, {"action": "HOLD", "rationale": "", "confidence": "low"}),
            "report": self._safe_json(final_state.report, {"risks": [], "strategy": "", "next_steps": []}),
            "bull": self._safe_json(final_state.bull_view, {"summary": "", "risks": []}),
            "bear": self._safe_json(final_state.bear_view, {"summary": "", "risks": []}),
            "reflection": self._safe_json(getattr(final_state, "reflection", None), {"reflection": "", "actions": []}),
            "snapshot": snapshot if include_news else {k: v for k, v in snapshot.items() if k != "news"},
            "meta": {
                "seed": seed,
                "bb_rounds": bb_rounds,
                "memory_store_manager_only": memory_store_flag,
                "include_news": include_news,
                "use_memory": use_memory,
                "mode": mode or snapshot.get("mode"),
                "interval": interval or snapshot.get("interval"),
                "news_limit": news_limit,
                "news_page": news_page,
                "llm_model": self.settings.ollama_model,
                "llm_temperature": self.settings.llm_temperature,
                "embedding_mode": self.settings.embedding_mode,
                "working_mem_max": self.settings.working_mem_max,
                "environment": self.settings.environment,
            },
        }

        sim_id = str(uuid4())
        result = SimulationResult(simulation_id=sim_id, summary=summary)
        self._records[sim_id] = result

        report_for_memory = final_state.report or json.dumps(summary["report"], ensure_ascii=False)
        await self.memory.add_memory(content=report_for_memory, metadata={"role": "manager", "ticker": ticker})
        await self._persist(sim_id, ticker, summary, final_state)

        # 피드백 스케줄 등록 (실시 후 결과 추적)
        await self.feedback_service.schedule_feedback(sim_id, ticker, summary)

        return result

    async def _persist(self, sim_id: str, ticker: str, summary: Dict[str, Any], state: TradeState) -> None:
        try:
            async with SessionLocal() as session:
                session.add(
                    Simulation(
                        id=sim_id,
                        ticker=ticker,
                        status="completed",
                        summary=json.dumps(summary),
                    )
                )
                await session.flush()
                logs = [
                    AgentLog(simulation_id=sim_id, role="bull", content=state.bull_view or ""),
                    AgentLog(simulation_id=sim_id, role="bear", content=state.bear_view or ""),
                    AgentLog(simulation_id=sim_id, role="trader", content=state.decision or ""),
                    AgentLog(simulation_id=sim_id, role="manager", content=state.report or ""),
                ]
                session.add_all(logs)
                await session.commit()
        except Exception:
            # DB 장애 시에도 메인 흐름이 깨지지 않도록 무시
            pass

    async def _run_manual_rounds(
        self, state: TradeState, bb_rounds: int, memory_store_manager_only: bool, seed: Optional[int]
    ) -> TradeState:
        for _ in range(bb_rounds):
            state = await self._bull(state, memory_store_manager_only, seed)
        state = await self._bear(state, memory_store_manager_only, seed)
        state = await self._trader(state, memory_store_manager_only, seed)
        state = await self._manager(state, seed)
        state = await self._reflection(state, seed)
        return state

    def _add_working(self, state: TradeState, content: str, role: str) -> None:
        if not content:
            return
        entry = {"content": content, "metadata": {"role": role, "ticker": state.snapshot.get("ticker", ""), "created_at": time.time()}}
        state.working_mem.append(entry)
        if len(state.working_mem) > self.settings.working_mem_max:
            state.working_mem = state.working_mem[-self.settings.working_mem_max :]

    async def _bull(self, state: TradeState, memory_store_manager_only: bool, seed: Optional[int]) -> TradeState:
        prompt = prompts.BULL_TEMPLATE.format(
            snapshot=self._fmt_snapshot(state.snapshot), memories=self._fmt_memories(state.working_mem, state.memories)
        )
        state.bull_view = await self._generate_with_retry(
            prompt,
            seed=seed,
            fallback={"summary": "stub bull view", "risks": []},
        )
        self._add_working(state, state.bull_view, "bull")
        if not memory_store_manager_only:
            await self.memory.add_memory(
                content=state.bull_view, metadata={"role": "bull", "ticker": state.snapshot.get("ticker", ""), "created_at": time.time()}
            )
        return state

    async def _bear(self, state: TradeState, memory_store_manager_only: bool, seed: Optional[int]) -> TradeState:
        prompt = prompts.BEAR_TEMPLATE.format(
            snapshot=self._fmt_snapshot(state.snapshot), memories=self._fmt_memories(state.working_mem, state.memories)
        )
        state.bear_view = await self._generate_with_retry(
            prompt,
            seed=seed,
            fallback={"summary": "stub bear view", "risks": []},
        )
        self._add_working(state, state.bear_view, "bear")
        if not memory_store_manager_only:
            await self.memory.add_memory(
                content=state.bear_view, metadata={"role": "bear", "ticker": state.snapshot.get("ticker", ""), "created_at": time.time()}
            )
        return state

    async def _trader(self, state: TradeState, memory_store_manager_only: bool, seed: Optional[int]) -> TradeState:
        prompt = prompts.TRADER_TEMPLATE.format(
            bull=state.bull_view, bear=state.bear_view, memories=self._fmt_memories(state.working_mem, state.memories)
        )
        state.decision = await self._generate_with_retry(
            prompt,
            seed=seed,
            fallback={"action": "HOLD", "rationale": "stub trader decision", "confidence": "low"},
        )
        self._add_working(state, state.decision, "trader")
        if not memory_store_manager_only:
            await self.memory.add_memory(
                content=state.decision, metadata={"role": "trader", "ticker": state.snapshot.get("ticker", ""), "created_at": time.time()}
            )
        return state

    async def _manager(self, state: TradeState, seed: Optional[int]) -> TradeState:
        prompt = prompts.MANAGER_TEMPLATE.format(
            bull=state.bull_view, bear=state.bear_view, trader=state.decision, memories=self._fmt_memories(state.working_mem, state.memories)
        )
        state.report = await self._generate_with_retry(
            prompt,
            seed=seed,
            fallback={"risks": [], "strategy": "stub manager summary", "next_steps": []},
        )
        self._add_working(state, state.report, "manager")
        await self.memory.add_memory(
            content=state.report, metadata={"role": "manager", "ticker": state.snapshot.get("ticker", ""), "created_at": time.time()}
        )
        return state

    async def _reflection(self, state: TradeState, seed: Optional[int]) -> TradeState:
        prompt = prompts.REFLECTION_TEMPLATE.format(
            bull=state.bull_view,
            bear=state.bear_view,
            trader=state.decision,
            manager=state.report,
            memories=self._fmt_memories(state.working_mem, state.memories),
        )
        state.reflection = await self._generate_with_retry(
            prompt,
            seed=seed,
            fallback={"reflection": "stub reflection", "actions": []},
        )
        self._add_working(state, state.reflection, "reflection")
        await self.memory.add_memory(
            content=state.reflection,
            metadata={
                "role": "reflection",
                "ticker": state.snapshot.get("ticker", ""),
                "created_at": time.time(),
                "salience": self.settings.memory_reflection_role_weight,
            },
        )
        return state

    @staticmethod
    def _fmt_memories(working: List[dict[str, Any]], ltm: List[dict[str, Any]]) -> str:
        combined = working + ltm
        if not combined:
            return "기억 없음"
        return "\n".join(f"- ({m.get('metadata', {}).get('role', 'mem')}) {m.get('content')}" for m in combined)

    @staticmethod
    def _fmt_snapshot(snapshot: Dict[str, Any]) -> str:
        ticker = snapshot.get("ticker", "")
        latest = snapshot.get("latest", {})
        return f"티커: {ticker}, 최신: {latest}"

    async def _generate_with_retry(self, prompt: str, *, seed: Optional[int], fallback: Dict[str, Any]) -> str:
        last = ""
        for _ in range(self.settings.llm_max_retries + 1):
            try:
                self.logger.debug("LLM prompt preview (seed=%s): %s", seed, prompt[:2000])
                resp = await self.llm.generate(prompt, seed=seed)
                last = resp
                self.logger.debug("LLM raw response (seed=%s): %s", seed, str(resp)[:2000])
                obj = json.loads(resp)
                return json.dumps(obj, ensure_ascii=False)
            except Exception as exc:
                self.logger.warning("LLM generate/parse failed (seed=%s): %s", seed, exc)
                continue
        # 마지막 실패 시에도 JSON을 반환해 API 계약을 지킨다.
        try:
            return json.dumps(fallback, ensure_ascii=False)
        except Exception:
            return last

    @staticmethod
    def _safe_json(text: Optional[str], fallback: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse JSON string and merge with fallback defaults so required keys are present.
        """
        if not text:
            return dict(fallback)
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                merged = dict(fallback)
                merged.update(obj)
                return merged
            return dict(fallback)
        except Exception:
            return dict(fallback)

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any, Dict, Optional, List
from uuid import uuid4

from config import Settings
from agents.graph import TradeState
from agents import prompts
from memory.finmem_memory import FinMemMemory, InMemoryMemory
from memory.redis_store import build_vector_store
from services.data_loader import MarketDataLoader
from services.llm import build_embeddings, build_llm
from db.session import SessionLocal
from db.models import AgentLog, Simulation


@dataclass
class SimulationResult:
    simulation_id: str
    summary: Dict[str, Any]
    status: str = "completed"


class SimulationService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.loader = MarketDataLoader(settings)
        self.llm = build_llm(settings.gemini_api_key, settings.gemini_model)
        self.memory = self._build_memory()
        self._records: Dict[str, SimulationResult] = {}

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
    ) -> SimulationResult:
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
        return await self.run_on_snapshot(
            snapshot=snapshot,
            ticker=ticker,
            include_news=include_news,
            bb_rounds=bb_rounds,
            memory_store_manager_only=memory_store_manager_only,
        )

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
            embeddings = build_embeddings(self.settings.gemini_api_key, mode=self.settings.embedding_mode)
            store = build_vector_store(self.settings, embeddings)
            return FinMemMemory(
                store,
                recency_lambda=self.settings.memory_recency_lambda,
                duplicate_threshold=self.settings.memory_duplicate_threshold,
                ttl_days=self.settings.memory_ttl_days,
                role_weights=self.settings.memory_role_weights,
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
    ) -> SimulationResult:
        bb_rounds = bb_rounds or self.settings.max_rounds_bull_bear
        if bb_rounds < 1:
            raise ValueError("bb_rounds must be >= 1")
        memory_store_flag = (
            self.settings.memory_store_manager_only if memory_store_manager_only is None else memory_store_manager_only
        )
        ltm_memories = await self.memory.search(f"{ticker} market", k=self.settings.memory_search_k, ticker=ticker)
        initial_state = TradeState(snapshot=snapshot, memories=ltm_memories, working_mem=[])
        final_state = await self._run_manual_rounds(
            initial_state, bb_rounds=bb_rounds, memory_store_manager_only=memory_store_flag
        )

        summary = {
            "decision": final_state.decision,
            "report": final_state.report,
            "bull": final_state.bull_view,
            "bear": final_state.bear_view,
            "snapshot": snapshot if include_news else {k: v for k, v in snapshot.items() if k != "news"},
        }

        sim_id = str(uuid4())
        result = SimulationResult(simulation_id=sim_id, summary=summary)
        self._records[sim_id] = result

        await self.memory.add_memory(content=summary["report"] or "manager report", metadata={"role": "manager", "ticker": ticker})
        await self._persist(sim_id, ticker, summary, final_state)
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
            # DB 장애 시에도 메인 플로우가 깨지지 않도록 무시
            pass

    async def _run_manual_rounds(
        self, state: TradeState, bb_rounds: int, memory_store_manager_only: bool
    ) -> TradeState:
        for _ in range(bb_rounds):
            state = await self._bull(state, memory_store_manager_only)
            state = await self._bear(state, memory_store_manager_only)
        state = await self._trader(state, memory_store_manager_only)
        state = await self._manager(state)
        return state

    def _add_working(self, state: TradeState, content: str, role: str) -> None:
        if not content:
            return
        entry = {"content": content, "metadata": {"role": role, "ticker": state.snapshot.get("ticker", ""), "created_at": time.time()}}
        state.working_mem.append(entry)
        if len(state.working_mem) > self.settings.working_mem_max:
            state.working_mem = state.working_mem[-self.settings.working_mem_max :]

    async def _bull(self, state: TradeState, memory_store_manager_only: bool) -> TradeState:
        prompt = prompts.BULL_TEMPLATE.format(
            snapshot=self._fmt_snapshot(state.snapshot), memories=self._fmt_memories(state.working_mem, state.memories)
        )
        state.bull_view = await self.llm.generate(prompt)
        self._add_working(state, state.bull_view, "bull")
        if not memory_store_manager_only:
            await self.memory.add_memory(
                content=state.bull_view, metadata={"role": "bull", "ticker": state.snapshot.get("ticker", ""), "created_at": time.time()}
            )
        return state

    async def _bear(self, state: TradeState, memory_store_manager_only: bool) -> TradeState:
        prompt = prompts.BEAR_TEMPLATE.format(
            snapshot=self._fmt_snapshot(state.snapshot), memories=self._fmt_memories(state.working_mem, state.memories)
        )
        state.bear_view = await self.llm.generate(prompt)
        self._add_working(state, state.bear_view, "bear")
        if not memory_store_manager_only:
            await self.memory.add_memory(
                content=state.bear_view, metadata={"role": "bear", "ticker": state.snapshot.get("ticker", ""), "created_at": time.time()}
            )
        return state

    async def _trader(self, state: TradeState, memory_store_manager_only: bool) -> TradeState:
        prompt = prompts.TRADER_TEMPLATE.format(
            bull=state.bull_view, bear=state.bear_view, memories=self._fmt_memories(state.working_mem, state.memories)
        )
        state.decision = await self.llm.generate(prompt)
        self._add_working(state, state.decision, "trader")
        if not memory_store_manager_only:
            await self.memory.add_memory(
                content=state.decision, metadata={"role": "trader", "ticker": state.snapshot.get("ticker", ""), "created_at": time.time()}
            )
        return state

    async def _manager(self, state: TradeState) -> TradeState:
        prompt = prompts.MANAGER_TEMPLATE.format(
            bull=state.bull_view, bear=state.bear_view, trader=state.decision, memories=self._fmt_memories(state.working_mem, state.memories)
        )
        state.report = await self.llm.generate(prompt)
        self._add_working(state, state.report, "manager")
        await self.memory.add_memory(
            content=state.report, metadata={"role": "manager", "ticker": state.snapshot.get("ticker", ""), "created_at": time.time()}
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

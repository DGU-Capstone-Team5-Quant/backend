from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import uuid4

from config import Settings
from agents.graph import TradeState, build_graph
from memory.finmem_memory import FinMemMemory, InMemoryMemory
from memory.redis_store import build_vector_store
from services.data_loader import MarketDataLoader
from services.llm import build_embeddings, build_llm


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
        self.graph = build_graph(self.llm, self.memory)
        self._records: Dict[str, SimulationResult] = {}

    async def run(self, ticker: str, window: int, include_news: bool = True, mode: str = "intraday") -> SimulationResult:
        snapshot = await self.loader.load_snapshot(ticker, window, mode=mode)
        memories = await self.memory.search(f"{ticker} market", k=5)
        initial_state = TradeState(snapshot=snapshot, memories=memories)
        final_state = await self.graph.ainvoke(initial_state)

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
        return result

    async def get(self, simulation_id: str) -> Optional[SimulationResult]:
        return self._records.get(simulation_id)

    def _build_memory(self) -> FinMemMemory | InMemoryMemory:
        try:
            embeddings = build_embeddings(self.settings.gemini_api_key)
            store = build_vector_store(self.settings, embeddings)
            return FinMemMemory(store)
        except Exception:
            return InMemoryMemory()

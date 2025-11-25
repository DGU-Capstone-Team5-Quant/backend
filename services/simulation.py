from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Dict, Optional
from uuid import uuid4

from config import Settings
from agents.graph import TradeState, build_graph
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
        self.graph = build_graph(self.llm, self.memory)
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
        memories = await self.memory.search(f"{ticker} market", k=5)
        initial_state = TradeState(snapshot=snapshot, memories=memories)
        raw_state = await self.graph.ainvoke(initial_state)
        final_state = self._ensure_state(raw_state)

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
            embeddings = build_embeddings(self.settings.gemini_api_key)
            store = build_vector_store(self.settings, embeddings)
            return FinMemMemory(store)
        except Exception:
            return InMemoryMemory()

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

    @staticmethod
    def _ensure_state(raw: Any) -> TradeState:
        if isinstance(raw, TradeState):
            return raw
        if isinstance(raw, dict):
            return TradeState(**raw)
        # 폴백: 비정상 응답일 때 최소 필드만 채워 반환
        return TradeState(snapshot={}, memories=[])

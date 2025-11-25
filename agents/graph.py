from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph

from agents import prompts
from memory.finmem_memory import FinMemMemory, InMemoryMemory
from services.llm import BaseLLMClient


@dataclass
class TradeState:
    snapshot: Dict[str, Any]
    memories: List[Dict[str, Any]] = field(default_factory=list)
    working_mem: List[Dict[str, Any]] = field(default_factory=list)
    bull_view: Optional[str] = None
    bear_view: Optional[str] = None
    decision: Optional[str] = None
    report: Optional[str] = None


def _fmt_memories(memories: List[Dict[str, Any]]) -> str:
    if not memories:
        return "기억 없음"
    return "\n".join(
        f"- ({m.get('metadata', {}).get('role', 'mem')}) {m.get('content')}"
        for m in memories
    )


def _fmt_snapshot(snapshot: Dict[str, Any]) -> str:
    ticker = snapshot.get("ticker", "")
    latest = snapshot.get("latest", {})
    return f"티커: {ticker}, 최신: {latest}"


def build_graph(
    llm: BaseLLMClient,
    memory: FinMemMemory | InMemoryMemory,
    *,
    max_bb_rounds: int,
    memory_store_manager_only: bool,
):
    graph = StateGraph(TradeState)

    async def bull_node(state: TradeState) -> TradeState:
        prompt = prompts.BULL_TEMPLATE.format(snapshot=_fmt_snapshot(state.snapshot), memories=_fmt_memories(state.memories))
        state.bull_view = await llm.generate(prompt)
        if not memory_store_manager_only:
            await memory.add_memory(content=state.bull_view, metadata={"role": "bull", "ticker": state.snapshot.get("ticker", "")})
        return state

    async def bear_node(state: TradeState) -> TradeState:
        prompt = prompts.BEAR_TEMPLATE.format(snapshot=_fmt_snapshot(state.snapshot), memories=_fmt_memories(state.memories))
        state.bear_view = await llm.generate(prompt)
        if not memory_store_manager_only:
            await memory.add_memory(content=state.bear_view, metadata={"role": "bear", "ticker": state.snapshot.get("ticker", "")})
        return state

    async def trader_node(state: TradeState) -> TradeState:
        prompt = prompts.TRADER_TEMPLATE.format(bull=state.bull_view, bear=state.bear_view, memories=_fmt_memories(state.memories))
        state.decision = await llm.generate(prompt)
        if not memory_store_manager_only:
            await memory.add_memory(content=state.decision, metadata={"role": "trader", "ticker": state.snapshot.get("ticker", "")})
        return state

    async def manager_node(state: TradeState) -> TradeState:
        prompt = prompts.MANAGER_TEMPLATE.format(bull=state.bull_view, bear=state.bear_view, trader=state.decision, memories=_fmt_memories(state.memories))
        state.report = await llm.generate(prompt)
        await memory.add_memory(content=state.report, metadata={"role": "manager", "ticker": state.snapshot.get("ticker", "")})
        return state

    graph.add_node("bull", bull_node)
    graph.add_node("bear", bear_node)
    graph.add_node("trader", trader_node)
    graph.add_node("manager", manager_node)

    graph.set_entry_point("bull")
    # 루프: bull<->bear를 설정된 라운드 수만큼 반복
    for _ in range(max_bb_rounds - 1):
        graph.add_edge("bull", "bear")
        graph.add_edge("bear", "bull")
    # 마지막 bear에서 trader로 진행
    graph.add_edge("bear", "trader")
    graph.add_edge("trader", "manager")
    graph.add_edge("manager", END)

    return graph.compile()

from typing import Any
from datetime import datetime

import logging

from fastapi import APIRouter, Depends, HTTPException
import httpx
from pydantic import BaseModel, Field, ConfigDict

from config import Settings, get_settings
from services.simulation import SimulationService

router = APIRouter(tags=["simulation"], prefix="/api")
logger = logging.getLogger(__name__)


class AgentView(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"summary": "Uptrend continues", "risks": ["Macro slowdown"]}})

    summary: str | None = Field(default=None, description="핵심 요약")
    risks: list[str] = Field(default_factory=list, description="주요 리스크 목록")


class TraderDecision(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"action": "LONG", "rationale": "Bullish momentum", "confidence": "high"}})

    action: str = Field(..., description="LONG | SHORT | HOLD")
    rationale: str | None = Field(default=None, description="의사결정 근거")
    confidence: str | None = Field(default=None, description="low|medium|high")


class ManagerReport(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"risks": ["Liquidity risk"], "strategy": "Scale in", "next_steps": ["Watch CPI"]}})

    risks: list[str] = Field(default_factory=list)
    strategy: str | None = Field(default=None)
    next_steps: list[str] = Field(default_factory=list)


class Reflection(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"reflection": "Need tighter stops", "actions": ["Test different intervals"]}})

    reflection: str | None = None
    actions: list[str] = Field(default_factory=list)


class Snapshot(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ticker: str
    window: int
    mode: str
    interval: str
    from_: str | None = Field(default=None, alias="from")
    to: str | None = Field(default=None)
    latest: dict[str, Any]
    news: list[dict[str, Any]] | None = Field(default=None)


class SimulationSummary(BaseModel):
    decision: TraderDecision
    report: ManagerReport
    bull: AgentView
    bear: AgentView
    reflection: Reflection
    snapshot: Snapshot
    meta: dict[str, Any] | None = Field(
        default=None,
        description="실험 파라미터 및 시드 등 메타데이터",
        json_schema_extra={"example": {"seed": 42, "bb_rounds": 2, "memory_store_manager_only": True}},
    )


class SimulationRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"ticker": "AAPL", "window": 120, "news": True, "interval": "1h", "seed": 42, "use_memory": True}})

    ticker: str = Field(..., description="Ticker symbol to simulate")
    window: int = Field(default=200, description="Number of periods for the market snapshot")
    news: bool = Field(default=True, description="Include news in the snapshot")
    mode: str = Field(default="intraday", description="intraday 또는 daily 가격 모드")
    interval: str = Field(default="1h", description="intraday 모드에서의 간격 (ex: 5min, 15min, 1h)")
    start_date: datetime | None = Field(default=None, description="시작일자/시간 (YYYY-MM-DD 또는 ISO8601)")
    end_date: datetime | None = Field(default=None, description="종료일자/시간 (YYYY-MM-DD 또는 ISO8601)")
    news_limit: int = Field(default=5, description="뉴스 가져올 개수")
    news_page: int = Field(default=0, description="뉴스 페이지 (0부터 시작)")
    bb_rounds: int | None = Field(default=None, description="Bull/Bear 토론 라운드 수(기본 설정값 사용)")
    memory_store_manager_only: bool | None = Field(
        default=None, description="True이면 Manager 리포트만 메모리에 저장(비용 절감)"
    )
    seed: int | None = Field(default=None, description="LLM 생성 시드(재현성)")
    use_memory: bool = Field(default=True, description="장기 메모리 검색을 사용할지 여부(아블레이션용)")


class SimulationResponse(BaseModel):
    simulation_id: str
    status: str
    # 응답 유연성을 위해 dict 허용 (LLM 출력 변형/스텁 대비)
    summary: dict[str, Any] | None = Field(default=None, description="Simulation summary payload")


def get_service(settings: Settings = Depends(get_settings)) -> SimulationService:
    return SimulationService(settings)


@router.post("/run", response_model=SimulationResponse)
async def run_simulation(payload: SimulationRequest, service: SimulationService = Depends(get_service)) -> SimulationResponse:
    try:
        result = await service.run(
            ticker=payload.ticker,
            window=payload.window,
            include_news=payload.news,
            mode=payload.mode,
            interval=payload.interval,
            start_date=payload.start_date,
            end_date=payload.end_date,
            news_limit=payload.news_limit,
            news_page=payload.news_page,
            bb_rounds=payload.bb_rounds,
            memory_store_manager_only=payload.memory_store_manager_only,
            seed=payload.seed,
            use_memory=payload.use_memory,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # pragma: no cover - placeholder for real error handling
        logger.exception("Simulation failed")
        raise HTTPException(status_code=500, detail=str(exc))

    return SimulationResponse(simulation_id=result.simulation_id, status="completed", summary=result.summary)


@router.get("/simulations/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(simulation_id: str, service: SimulationService = Depends(get_service)) -> SimulationResponse:
    record = await service.get(simulation_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return SimulationResponse(simulation_id=simulation_id, status=record.status, summary=record.summary)

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from config import Settings, get_settings
from services.simulation import SimulationService

router = APIRouter(tags=["simulation"])


class SimulationRequest(BaseModel):
    ticker: str = Field(..., description="Ticker symbol to simulate")
    window: int = Field(default=200, description="Number of periods for the market snapshot")
    news: bool = Field(default=True, description="Include news in the snapshot")
    mode: str = Field(default="intraday", description="intraday 또는 daily 등 가격 소스 모드")
    interval: str = Field(default="1h", description="intraday 모드일 때의 간격 (ex: 5min, 15min, 1h)")
    start_date: str | None = Field(default=None, description="데이터 시작일(YYYY-MM-DD)")
    end_date: str | None = Field(default=None, description="데이터 종료일(YYYY-MM-DD)")
    news_limit: int = Field(default=5, description="뉴스 가져올 개수")
    news_page: int = Field(default=0, description="뉴스 페이지 (0부터 시작)")


class SimulationResponse(BaseModel):
    simulation_id: str
    status: str
    summary: dict[str, Any] | None = None


def get_service(settings: Settings = Depends(get_settings)) -> SimulationService:
    return SimulationService(settings)


@router.post("/run-simulation", response_model=SimulationResponse)
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
        )
    except Exception as exc:  # pragma: no cover - placeholder for real error handling
        raise HTTPException(status_code=500, detail=str(exc))

    return SimulationResponse(simulation_id=result.simulation_id, status="completed", summary=result.summary)


@router.get("/simulations/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(simulation_id: str, service: SimulationService = Depends(get_service)) -> SimulationResponse:
    record = await service.get(simulation_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return SimulationResponse(simulation_id=simulation_id, status=record.status, summary=record.summary)

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


class SimulationResponse(BaseModel):
    simulation_id: str
    status: str
    summary: dict[str, Any] | None = None


def get_service(settings: Settings = Depends(get_settings)) -> SimulationService:
    return SimulationService(settings)


@router.post("/run-simulation", response_model=SimulationResponse)
async def run_simulation(payload: SimulationRequest, service: SimulationService = Depends(get_service)) -> SimulationResponse:
    try:
        result = await service.run(payload.ticker, payload.window, include_news=payload.news, mode=payload.mode)
    except Exception as exc:  # pragma: no cover - placeholder for real error handling
        raise HTTPException(status_code=500, detail=str(exc))

    return SimulationResponse(simulation_id=result.simulation_id, status="completed", summary=result.summary)


@router.get("/simulations/{simulation_id}", response_model=SimulationResponse)
async def get_simulation(simulation_id: str, service: SimulationService = Depends(get_service)) -> SimulationResponse:
    record = await service.get(simulation_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return SimulationResponse(simulation_id=simulation_id, status=record.status, summary=record.summary)

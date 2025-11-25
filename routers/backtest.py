from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import httpx

from config import Settings, get_settings
from services.simulation import SimulationService
from services.backtest import BacktestService

router = APIRouter(tags=["backtest"], prefix="/api")


class BacktestRequest(BaseModel):
    ticker: str = Field(..., description="Ticker symbol")
    window: int = Field(default=50, description="Lookback window size")
    start_date: str | None = Field(default=None, description="YYYY-MM-DD")
    end_date: str | None = Field(default=None, description="YYYY-MM-DD")
    interval: str = Field(default="1h", description="1min/5min/15min/1h/1day etc.")
    step: int = Field(default=1, description="Stride when sliding the window")
    include_news: bool = Field(default=False, description="Include news in backtest snapshots")


class BacktestResponse(BaseModel):
    backtest_id: str
    summary: dict[str, Any]
    trades: List[dict[str, Any]]

class PointBacktestRequest(BaseModel):
    ticker: str = Field(..., description="Ticker symbol")
    window: int = Field(default=50, description="Lookback window size")
    target_datetime: str | None = Field(default=None, description="YYYY-MM-DD or ISO datetime as end point")
    interval: str = Field(default="1h", description="1min/5min/15min/1h/1day etc.")


class PointBacktestResponse(BaseModel):
    backtest_id: str
    summary: dict[str, Any]
    trades: List[dict[str, Any]]


def get_service(settings: Settings = Depends(get_settings)) -> BacktestService:
    sim_service = SimulationService(settings)
    return BacktestService(sim_service, settings)


@router.post("/backtest", response_model=BacktestResponse)
async def run_backtest(payload: BacktestRequest, service: BacktestService = Depends(get_service)) -> BacktestResponse:
    try:
        result = await service.run(
            ticker=payload.ticker,
            window=payload.window,
            start_date=payload.start_date,
            end_date=payload.end_date,
            interval=payload.interval,
            step=payload.step,
            include_news=payload.include_news,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc))

    return BacktestResponse(backtest_id=result.backtest_id, summary=result.summary, trades=result.trades)


@router.post("/point", response_model=PointBacktestResponse)
async def run_point_backtest(payload: PointBacktestRequest, service: BacktestService = Depends(get_service)) -> PointBacktestResponse:
    try:
        result = await service.run_point(
            ticker=payload.ticker,
            window=payload.window,
            target_datetime=payload.target_datetime,
            interval=payload.interval,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc))

    return PointBacktestResponse(backtest_id=result.backtest_id, summary=result.summary, trades=result.trades)

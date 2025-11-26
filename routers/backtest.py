from typing import Any, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
import httpx

from config import Settings, get_settings
from services.simulation import SimulationService
from services.backtest import BacktestService

router = APIRouter(tags=["backtest"], prefix="/api")


class BacktestTrade(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"ts": "2024-11-25T12:00:00Z", "action": "LONG", "price": 150.5, "position": 1, "pnl": 1.2, "cumulative_pnl": 3.4}})

    ts: Any = Field(..., description="타임스탬프 (ISO8601)")
    action: str
    price: float
    position: float
    pnl: float
    cumulative_pnl: float


class BacktestSummary(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"ticker": "AAPL", "interval": "1h", "final_pnl": 12.3, "avg_step_return": 0.001, "volatility": 0.01, "sharpe": 1.5, "mdd": -3.2, "turnover": 5, "trades_count": 20, "meta": {"seed": 42}}})

    ticker: str
    window: int
    interval: str
    start_date: str | None = None
    end_date: str | None = None
    final_pnl: float
    avg_step_return: float
    volatility: float
    sharpe: float
    mdd: float
    turnover: float
    trades_count: int
    step: int
    meta: dict[str, Any] | None = Field(default=None, description="실험/재현성을 위한 메타")


class BacktestRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"ticker": "AAPL", "window": 100, "interval": "1h", "step": 1, "include_news": False, "seed": 123, "use_memory": True}})

    ticker: str = Field(..., description="Ticker symbol")
    window: int = Field(default=50, description="Lookback window size")
    start_date: datetime | None = Field(default=None, description="시작일/시간 (YYYY-MM-DD 또는 ISO8601)")
    end_date: datetime | None = Field(default=None, description="종료일/시간 (YYYY-MM-DD 또는 ISO8601)")
    interval: str = Field(default="1h", description="1min/5min/15min/1h/1day etc.")
    step: int = Field(default=1, description="Stride when sliding the window")
    include_news: bool = Field(default=False, description="Include news in backtest snapshots")
    seed: int | None = Field(default=None, description="LLM 시드(재현성)")
    use_memory: bool = Field(default=True, description="장기 메모리를 사용할지 여부(아블레이션)")


class BacktestResponse(BaseModel):
    backtest_id: str
    summary: BacktestSummary
    trades: List[BacktestTrade]


class PointBacktestRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"ticker": "AAPL", "window": 50, "interval": "1h", "target_datetime": "2024-11-25T12:00:00Z", "seed": 7, "use_memory": True}})

    ticker: str = Field(..., description="Ticker symbol")
    window: int = Field(default=50, description="Lookback window size")
    target_datetime: datetime | None = Field(default=None, description="종료 시점 (YYYY-MM-DD 또는 ISO8601)")
    interval: str = Field(default="1h", description="1min/5min/15min/1h/1day etc.")
    seed: int | None = Field(default=None, description="LLM 시드(재현성)")
    use_memory: bool = Field(default=True, description="장기 메모리를 사용할지 여부(아블레이션)")


class PointBacktestResponse(BaseModel):
    backtest_id: str
    summary: BacktestSummary
    trades: List[BacktestTrade]


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
            seed=payload.seed,
            use_memory=payload.use_memory,
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
            seed=payload.seed,
            use_memory=payload.use_memory,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc))

    return PointBacktestResponse(backtest_id=result.backtest_id, summary=result.summary, trades=result.trades)

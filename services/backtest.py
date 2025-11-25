from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pandas as pd

from config import Settings
from services.simulation import SimulationService
from db.session import SessionLocal
from db.models import Backtest, BacktestTrade


@dataclass
class BacktestResult:
    backtest_id: str
    summary: Dict[str, Any]
    trades: List[Dict[str, Any]]


class BacktestService:
    def __init__(self, sim_service: SimulationService, settings: Settings):
        self.sim_service = sim_service
        self.settings = settings

    async def run_point(
        self,
        ticker: str,
        window: int,
        target_datetime: Optional[str],
        interval: str,
    ) -> BacktestResult:
        loader = self.sim_service.loader
        prices = await loader.fetch_prices(
            ticker, window=window, mode="intraday", interval=interval, start_date=None, end_date=target_datetime
        )
        prices = loader.add_indicators(prices)
        prices = prices.sort_index()
        if prices.empty:
            raise ValueError("no price data returned for target_datetime")
        latest = prices.tail(1).to_dict(orient="records")[0]
        snapshot = {
            "ticker": ticker,
            "window": window,
            "mode": "intraday",
            "interval": interval,
            "from": None,
            "to": target_datetime,
            "latest": latest,
            "news": [],
        }
        sim_result = await self.sim_service.run_on_snapshot(
            snapshot=snapshot,
            ticker=ticker,
            include_news=False,
            bb_rounds=None,
            memory_store_manager_only=self.settings.memory_store_manager_only,
        )
        return BacktestResult(backtest_id=str(uuid4()), summary=sim_result.summary, trades=[])

    async def run(
        self,
        ticker: str,
        window: int,
        start_date: Optional[str],
        end_date: Optional[str],
        interval: str,
        step: int = 1,
    ) -> BacktestResult:
        loader = self.sim_service.loader
        prices = await loader.fetch_prices(ticker, window=window, mode="intraday", interval=interval, start_date=start_date, end_date=end_date)
        prices = loader.add_indicators(prices)
        prices = prices.sort_index()
        closes = prices["close"]

        backtest_id = str(uuid4())
        trades: List[Dict[str, Any]] = []
        position = 0.0
        cum_pnl = 0.0
        peak = 0.0
        mdd = 0.0

        for idx in range(window - 1, len(prices), step):
            slice_df = prices.iloc[: idx + 1]
            latest = slice_df.tail(1).to_dict(orient="records")[0]
            snapshot = {
                "ticker": ticker,
                "window": window,
                "mode": "intraday",
                "interval": interval,
                "from": start_date,
                "to": end_date,
                "latest": latest,
                "news": [],
            }
            sim_result = await self.sim_service.run_on_snapshot(
                snapshot=snapshot,
                ticker=ticker,
                include_news=False,
                bb_rounds=None,
                memory_store_manager_only=self.settings.memory_store_manager_only,
            )
            action = (sim_result.summary.get("decision") or "").upper()
            price = latest.get("close", 0.0)
            prev_price = closes.iloc[idx - 1] if idx > 0 else price

            if "LONG" in action:
                position = 1.0
            elif "SHORT" in action:
                position = -1.0
            else:
                position = 0.0

            pnl = position * (price - prev_price)
            cum_pnl += pnl
            peak = max(peak, cum_pnl)
            mdd = min(mdd, cum_pnl - peak)

            trades.append(
                {
                    "ts": slice_df.index[-1].to_pydatetime(),
                    "action": action,
                    "price": float(price),
                    "position": position,
                    "pnl": float(pnl),
                    "cumulative_pnl": float(cum_pnl),
                }
            )

        summary = {
            "ticker": ticker,
            "window": window,
            "interval": interval,
            "start_date": start_date,
            "end_date": end_date,
            "final_pnl": cum_pnl,
            "mdd": mdd,
            "trades_count": len(trades),
        }

        await self._persist(backtest_id, ticker, summary, trades, window, step, start_date, end_date)
        return BacktestResult(backtest_id=backtest_id, summary=summary, trades=trades)

    async def _persist(
        self,
        backtest_id: str,
        ticker: str,
        summary: Dict[str, Any],
        trades: List[Dict[str, Any]],
        window: int,
        step: int,
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> None:
        try:
            async with SessionLocal() as session:
                session.add(
                    Backtest(
                        id=backtest_id,
                        ticker=ticker,
                        window=window,
                        step=step,
                        start_date=start_date,
                        end_date=end_date,
                        summary=pd.Series(summary).to_json(),
                    )
                )
                for t in trades:
                    session.add(
                        BacktestTrade(
                            backtest_id=backtest_id,
                            ts=t["ts"],
                            action=t["action"],
                            price=t["price"],
                            position=t["position"],
                            pnl=t["pnl"],
                            cumulative_pnl=t["cumulative_pnl"],
                        )
                    )
                await session.commit()
        except Exception:
            pass

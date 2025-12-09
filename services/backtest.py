from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pandas as pd
import time
import timeit

from config import Settings
from services.simulation import SimulationService
from services.metrics import metrics_tracker
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
        seed: Optional[int] = None,
        use_memory: bool = True,
        shares: float = 1.0,
        initial_capital: float = 10000.0,
    ) -> BacktestResult:
        t0 = timeit.default_timer()
        try:
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
                seed=seed,
                use_memory=use_memory,
                mode="intraday",
                interval=interval,
            )
            metrics_tracker.record_backtest(success=True, duration=timeit.default_timer() - t0)
            summary = self._summarize_point(sim_result.summary, shares=shares, initial_capital=initial_capital)
            return BacktestResult(backtest_id=str(uuid4()), summary=summary, trades=[])
        except Exception:
            metrics_tracker.record_backtest(success=False, duration=timeit.default_timer() - t0)
            raise

    async def run(
        self,
        ticker: str,
        window: int,
        start_date: Optional[str],
        end_date: Optional[str],
        interval: str,
        step: int = 1,
        include_news: bool = False,
        seed: Optional[int] = None,
        use_memory: bool = True,
        shares: float = 1.0,
        initial_capital: float = 10000.0,
    ) -> BacktestResult:
        t0 = timeit.default_timer()
        try:
            loader = self.sim_service.loader

            # 윈도우 데이터를 확보하기 위해 start_date를 앞당김
            # 사용자가 지정한 기간의 모든 날에 거래하려면 그 이전 데이터가 필요
            actual_start_date = start_date
            fetch_start = start_date

            if start_date:
                # 간격에 따라 윈도우 기간 계산
                if interval == "1day":
                    # 일봉: window * 1.5일 정도 (주말 고려)
                    window_days = int(window * 1.5) + 2
                else:
                    # 시간봉: 넉넉하게 확보
                    window_days = window + 14

                fetch_start = (pd.to_datetime(start_date) - pd.Timedelta(days=window_days)).strftime("%Y-%m-%d")

            prices = await loader.fetch_prices(
                ticker,
                window=window * 2,  # 넉넉하게 요청
                mode="intraday",
                interval=interval,
                start_date=fetch_start,
                end_date=end_date,
            )
            prices = loader.add_indicators(prices)
            prices = prices.sort_index()
            if prices.empty:
                raise ValueError("no price data returned for backtest")
            closes = prices["close"]

            # 실제 거래 시작 인덱스 찾기 (사용자가 지정한 start_date 이후)
            first_trade_idx = 0
            if actual_start_date:
                start_ts = pd.to_datetime(actual_start_date)
                # start_date 이후의 첫 데이터 인덱스 찾기
                valid_mask = prices.index >= start_ts
                if valid_mask.sum() == 0:
                    raise ValueError(f"지정한 시작일({actual_start_date}) 이후 데이터가 없습니다.")

                first_valid_idx = prices.index[valid_mask][0]
                first_trade_idx = prices.index.get_loc(first_valid_idx)

                # 윈도우 확보 확인
                if first_trade_idx < window:
                    raise ValueError(
                        f"윈도우 데이터가 부족합니다. "
                        f"시작일({actual_start_date})로부터 {window}개의 과거 데이터가 필요하지만 {first_trade_idx}개만 있습니다. "
                        f"시작일을 더 나중으로 설정하거나, 윈도우를 줄여주세요."
                    )
            else:
                first_trade_idx = window

            backtest_id = str(uuid4())
            trades: List[Dict[str, Any]] = []
            returns: List[float] = []
            position = 0.0  # shares
            entry_price = 0.0
            cash = float(initial_capital)
            equity = cash
            peak_equity = equity
            max_drawdown_pct = 0.0
            turnover = 0.0  # shares turned over
            fee_bps = self.settings.backtest_fee_bps
            slip_bps = self.settings.backtest_slippage_bps
            stop_loss = self.settings.backtest_stop_loss
            take_profit = self.settings.backtest_take_profit

            # 전체 거래 횟수 계산 및 출력 (사용자 지정 start_date부터)
            total_steps = len(list(range(first_trade_idx, len(prices), step)))
            print(f"예상 거래 결정 횟수: {total_steps}회", flush=True)

            if total_steps == 0:
                raise ValueError(
                    f"거래 가능한 데이터가 없습니다. "
                    f"데이터 포인트: {len(prices)}개, 윈도우: {window}, "
                    f"첫 거래 인덱스: {first_trade_idx}, "
                    f"기간: {start_date} ~ {end_date}. "
                    f"과거 날짜로 기간을 설정해주세요."
                )

            for step_idx, idx in enumerate(range(first_trade_idx, len(prices), step), 1):
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
                    "news": [],  # 뉴스 포함 시 loader.fetch_news 호출 확장 가능
                    "portfolio": {
                        "cash": float(cash),
                        "position_shares": float(position),
                        "equity": float(equity),
                        "initial_capital": float(initial_capital),
                    },
                }
                sim_result = await self.sim_service.run_on_snapshot(
                    snapshot=snapshot,
                    ticker=ticker,
                    include_news=include_news,
                    bb_rounds=None,
                    memory_store_manager_only=self.settings.memory_store_manager_only,
                    seed=seed,
                    use_memory=use_memory,
                    mode="intraday",
                    interval=interval,
                )
                decision_field = sim_result.summary.get("decision")
                if isinstance(decision_field, dict):
                    action = str(decision_field.get("action", "")).upper()
                else:
                    action = str(decision_field or "").upper()

                # 메모리 정보 추출 (각 의사결정에서 사용된 메모리 기록)
                memories_info = sim_result.summary.get("memories", {})

                price = latest.get("close", 0.0)
                prev_price = closes.iloc[idx - 1] if idx > 0 else price
                prev_equity = cash + position * prev_price

                # stop-loss / take-profit check
                new_pos = position
                stop_or_take = False
                if position != 0 and entry_price > 0:
                    direction = 1.0 if position > 0 else -1.0
                    pnl_since_entry = direction * (price - entry_price) / entry_price
                    if pnl_since_entry <= stop_loss:
                        new_pos = 0.0
                        action = "STOP_LOSS"
                        stop_or_take = True
                    elif pnl_since_entry >= take_profit:
                        new_pos = 0.0
                        action = "TAKE_PROFIT"
                        stop_or_take = True

                # trade decision (only if no stop/take triggered)
                if not stop_or_take:
                    if "BUY" in action:
                        # BUY_25, BUY_50, BUY_100 파싱
                        pct = 100  # 기본값
                        if "BUY_25" in action:
                            pct = 25
                        elif "BUY_50" in action:
                            pct = 50
                        elif "BUY_100" in action:
                            pct = 100

                        # 잔고의 pct%만큼 사용해서 매수
                        buy_cash = cash * (pct / 100.0)
                        buy_shares = buy_cash / price if price > 0 else 0
                        new_pos = position + buy_shares
                    elif "SELL" in action:
                        # SELL_25, SELL_50, SELL_100 파싱
                        pct = 100  # 기본값
                        if "SELL_25" in action:
                            pct = 25
                        elif "SELL_50" in action:
                            pct = 50
                        elif "SELL_100" in action:
                            pct = 100

                        # 보유 주식의 pct%만큼 매도 (현물이므로 position >= 0)
                        sell_shares = position * (pct / 100.0)
                        new_pos = position - sell_shares
                        new_pos = max(0, new_pos)  # 음수 방지
                    elif "HOLD" in action:
                        new_pos = position
                    else:
                        new_pos = position

                # apply fees/slippage on position change
                delta = new_pos - position
                trade_notional = delta * price
                fee = abs(trade_notional) * (fee_bps + slip_bps) / 10000.0
                cash -= trade_notional
                cash -= fee
                turnover += abs(delta)

                position = new_pos
                if position != 0 and entry_price == 0:
                    entry_price = price
                elif position == 0:
                    entry_price = 0.0

                equity = cash + position * price
                peak_equity = max(peak_equity, equity)
                drawdown_pct = (equity - peak_equity) / peak_equity if peak_equity > 0 else 0.0
                max_drawdown_pct = min(max_drawdown_pct, drawdown_pct)

                step_pnl = equity - prev_equity
                step_return = step_pnl / float(prev_equity if prev_equity else 1.0)
                returns.append(step_return)

                # 거래 정보 기록
                trade_info = {
                    "ts": slice_df.index[-1].to_pydatetime(),
                    "action": action,
                    "price": float(price),
                    "trade_shares": float(delta),
                    "position_shares": float(position),
                    "trade_notional": float(trade_notional),
                    "cash": float(cash),
                    "equity": float(equity),
                    "fee": float(fee),
                    "pnl": float(step_pnl),
                    "cumulative_pnl": float(equity - initial_capital),
                    "memories": {
                        "long_term_count": len(memories_info.get("long_term", [])),
                        "working_count": len(memories_info.get("working", [])),
                        "long_term": memories_info.get("long_term", []),
                        "working": memories_info.get("working", []),
                    },
                }
                trades.append(trade_info)

                # 진행률 출력 (항상)
                print(f"PROGRESS: {step_idx}/{total_steps}", flush=True)

                # 거래 발생 시 실시간 로그 출력
                if delta != 0:  # 실제 거래가 발생한 경우만
                    trade_type = "매수" if delta > 0 else "매도"
                    print(f"[거래 #{len(trades):3d}] {slice_df.index[-1].strftime('%Y-%m-%d %H:%M')} | "
                          f"{trade_type:2s} {abs(delta):6.2f}주 @ ${price:7.2f} | "
                          f"포지션: {position:6.2f}주 | "
                          f"수익: ${step_pnl:+8.2f} | "
                          f"잔고: ${equity:,.2f}", flush=True)

            summary = self._summarize(
                ticker=ticker,
                window=window,
                interval=interval,
                start_date=start_date,
                end_date=end_date,
                final_equity=equity,
                final_cash=cash,
                initial_capital=initial_capital,
                max_drawdown_pct=max_drawdown_pct,
                returns=returns,
                turnover=turnover,
                trades_count=len(trades),
                seed=seed,
                step=step,
                include_news=include_news,
                use_memory=use_memory,
                shares=shares,
                start_ts=prices.index[first_trade_idx],
                end_ts=prices.index[-1],
            )

            await self._persist(backtest_id, ticker, summary, trades, window, step, start_date, end_date)
            try:
                await self.sim_service.memory.add_memory(
                    content=f"Backtest feedback {ticker}: final_equity={summary['final_equity']}, total_return={summary['total_return']}",
                    metadata={
                        "role": "feedback",
                        "ticker": ticker,
                        "created_at": time.time(),
                        "salience": float(summary["final_equity"] - initial_capital),
                    },
                )
            except Exception:
                pass
            metrics_tracker.record_backtest(success=True, duration=timeit.default_timer() - t0)
            return BacktestResult(backtest_id=backtest_id, summary=summary, trades=trades)
        except Exception:
            metrics_tracker.record_backtest(success=False, duration=timeit.default_timer() - t0)
            raise

    def _summarize(
        self,
        *,
        ticker: str,
        window: int,
        interval: str,
        start_date: Optional[str],
        end_date: Optional[str],
        final_equity: float,
        final_cash: float,
        initial_capital: float,
        max_drawdown_pct: float,
        returns: List[float],
        turnover: float,
        trades_count: int,
        seed: Optional[int],
        step: int,
        include_news: bool,
        use_memory: bool,
        shares: float,
        start_ts,
        end_ts,
    ) -> Dict[str, Any]:
        if returns:
            ret_series = pd.Series(returns)
            vol = float(ret_series.std(ddof=0))
            mean_ret = float(ret_series.mean())
            sharpe = float(mean_ret / vol * (len(returns) ** 0.5)) if vol > 0 else 0.0
        else:
            vol = 0.0
            sharpe = 0.0
            mean_ret = 0.0

        total_return = (final_equity / initial_capital) - 1.0 if initial_capital else 0.0
        days = max((pd.to_datetime(end_ts) - pd.to_datetime(start_ts)).days, 0)
        if days > 0 and final_equity > 0 and initial_capital > 0:
            cagr = (final_equity / initial_capital) ** (365.0 / max(days, 1)) - 1.0
        else:
            cagr = 0.0
        calmar = cagr / abs(max_drawdown_pct) if max_drawdown_pct < 0 else 0.0

        return {
            "ticker": ticker,
            "window": window,
            "interval": interval,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": initial_capital,
            "final_equity": final_equity,
            "final_cash": final_cash,
            "total_return": total_return,
            "cagr": cagr,
            "avg_step_return": mean_ret,
            "volatility": vol,
            "sharpe": sharpe,
            "max_drawdown_pct": max_drawdown_pct,
            "calmar": calmar,
            "turnover_shares": turnover,
            "trades_count": trades_count,
            "step": step,
            "meta": {
                "seed": seed,
                "include_news": include_news,
                "use_memory": use_memory,
                "shares": shares,
                "llm_model": self.settings.ollama_model,
                "embedding_model": self.settings.ollama_embedding_model,
                "llm_temperature": self.settings.llm_temperature,
                "environment": self.settings.environment,
            },
        }

    def _summarize_point(self, sim_summary: Dict[str, Any], *, shares: float, initial_capital: float) -> Dict[str, Any]:
        # Point-in-time run uses sim summary as-is; attach capital assumptions.
        out = dict(sim_summary)
        out["meta"] = out.get("meta", {})
        out["meta"].update({"shares": shares, "initial_capital": initial_capital})
        return out

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
                            position=t.get("position_shares", t.get("position", 0.0)),
                            pnl=t["pnl"],
                            cumulative_pnl=t["cumulative_pnl"],
                        )
                    )
                await session.commit()
        except Exception:
            pass

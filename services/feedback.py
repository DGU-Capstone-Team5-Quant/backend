from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select

from config import Settings
from db.models import SimulationFeedback, Simulation
from db.session import SessionLocal
from services.data_loader import MarketDataLoader
from memory.finmem_memory import FinMemMemory


class FeedbackService:
    """실시간 시뮬레이션 결과 추적 서비스"""

    def __init__(self, settings: Settings, memory: FinMemMemory, loader: MarketDataLoader):
        self.settings = settings
        self.memory = memory
        self.loader = loader
        self.logger = logging.getLogger(__name__)
        self.feedback_days = settings.feedback_check_days if hasattr(settings, 'feedback_check_days') else 7

    async def schedule_feedback(
        self,
        simulation_id: str,
        ticker: str,
        summary: dict,
    ) -> None:
        """시뮬레이션 실행 후 피드백 스케줄 등록"""
        try:
            snapshot = summary.get("snapshot", {})
            latest = snapshot.get("latest", {})
            entry_price = latest.get("close")

            if not entry_price:
                self.logger.warning(f"No entry price found for simulation {simulation_id}")
                return

            decision = summary.get("decision", "")
            report = summary.get("report", "")
            decision_date = datetime.now()
            check_date = decision_date + timedelta(days=self.feedback_days)

            async with SessionLocal() as session:
                feedback = SimulationFeedback(
                    simulation_id=simulation_id,
                    ticker=ticker,
                    decision_date=decision_date,
                    entry_price=float(entry_price),
                    decision=decision,
                    report=report,
                    check_date=check_date,
                    is_checked=False,
                )
                session.add(feedback)
                await session.commit()

            self.logger.info(
                f"Scheduled feedback for simulation {simulation_id} "
                f"(ticker={ticker}, entry=${entry_price:.2f}, check_date={check_date})"
            )

        except Exception as e:
            self.logger.error(f"Failed to schedule feedback: {e}")

    async def check_pending_feedbacks(self) -> int:
        """체크 날짜가 지난 피드백들을 확인하고 결과 업데이트"""
        try:
            async with SessionLocal() as session:
                stmt = (
                    select(SimulationFeedback)
                    .where(
                        SimulationFeedback.is_checked == False,
                        SimulationFeedback.check_date <= datetime.now(),
                    )
                    .limit(100)  # 한 번에 100개씩 처리
                )
                result = await session.execute(stmt)
                pending_feedbacks = result.scalars().all()

                if not pending_feedbacks:
                    self.logger.info("No pending feedbacks to check")
                    return 0

                checked_count = 0
                for feedback in pending_feedbacks:
                    success = await self._update_feedback_result(session, feedback)
                    if success:
                        checked_count += 1

                await session.commit()
                self.logger.info(f"Checked {checked_count}/{len(pending_feedbacks)} pending feedbacks")
                return checked_count

        except Exception as e:
            self.logger.error(f"Failed to check pending feedbacks: {e}")
            return 0

    async def _update_feedback_result(
        self,
        session,
        feedback: SimulationFeedback,
    ) -> bool:
        """개별 피드백 결과 업데이트"""
        try:
            # 현재 가격 조회
            current_price = await self._get_current_price(feedback.ticker)
            if current_price is None:
                self.logger.warning(f"Could not fetch current price for {feedback.ticker}")
                return False

            # 수익률 계산
            actual_return = (current_price - feedback.entry_price) / feedback.entry_price

            # DB 업데이트
            feedback.actual_price = current_price
            feedback.actual_return = actual_return
            feedback.is_checked = True
            feedback.updated_at = datetime.now()

            # 메모리에 피드백 저장 (학습용)
            await self._store_feedback_in_memory(feedback, actual_return)

            self.logger.info(
                f"Updated feedback for {feedback.ticker}: "
                f"${feedback.entry_price:.2f} -> ${current_price:.2f} "
                f"({actual_return*100:.2f}%)"
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to update feedback {feedback.id}: {e}")
            return False

    async def _get_current_price(self, ticker: str) -> Optional[float]:
        """현재 가격 조회"""
        try:
            # 최근 1일 데이터 가져오기 (최신 가격)
            prices = await self.loader.fetch_prices(
                ticker=ticker,
                window=1,
                mode="intraday",
                interval="1h",
                start_date=None,
                end_date=None,
            )

            if prices.empty:
                return None

            latest = prices.tail(1).iloc[0]
            return float(latest.get("close", 0))

        except Exception as e:
            self.logger.error(f"Failed to fetch current price for {ticker}: {e}")
            return None

    async def _store_feedback_in_memory(
        self,
        feedback: SimulationFeedback,
        actual_return: float,
    ) -> None:
        """피드백 결과를 장기 메모리에 저장"""
        try:
            # 원본 decision과 report 파싱
            try:
                decision_obj = json.loads(feedback.decision)
                decision_text = json.dumps(decision_obj, ensure_ascii=False)
            except:
                decision_text = feedback.decision

            # 피드백 내용 구성
            feedback_content = (
                f"[Past Decision Feedback]\n"
                f"Ticker: {feedback.ticker}\n"
                f"Decision Date: {feedback.decision_date.strftime('%Y-%m-%d')}\n"
                f"Decision: {decision_text}\n"
                f"Entry Price: ${feedback.entry_price:.2f}\n"
                f"Actual Price ({self.feedback_days} days later): ${feedback.actual_price:.2f}\n"
                f"Actual Return: {actual_return*100:.2f}%\n"
                f"Report: {feedback.report[:200]}..."
            )

            # salience는 수익률 기반 (좋은 결과와 나쁜 결과 모두 중요)
            salience = abs(actual_return) * 10  # -0.1 ~ +0.1 -> 1.0, -0.5 ~ +0.5 -> 5.0

            await self.memory.add_memory(
                content=feedback_content,
                metadata={
                    "role": "feedback",
                    "ticker": feedback.ticker,
                    "created_at": datetime.now().timestamp(),
                    "salience": salience,
                    "actual_return": actual_return,
                    "simulation_id": feedback.simulation_id,
                },
            )

            self.logger.info(f"Stored feedback in memory (salience={salience:.2f})")

        except Exception as e:
            self.logger.error(f"Failed to store feedback in memory: {e}")

    async def get_feedback_stats(self, ticker: Optional[str] = None) -> dict:
        """피드백 통계 조회"""
        try:
            async with SessionLocal() as session:
                stmt = select(SimulationFeedback).where(SimulationFeedback.is_checked == True)
                if ticker:
                    stmt = stmt.where(SimulationFeedback.ticker == ticker)

                result = await session.execute(stmt)
                feedbacks = result.scalars().all()

                if not feedbacks:
                    return {"total": 0, "avg_return": 0, "win_rate": 0}

                returns = [f.actual_return for f in feedbacks if f.actual_return is not None]
                wins = sum(1 for r in returns if r > 0)

                return {
                    "total": len(feedbacks),
                    "avg_return": sum(returns) / len(returns) if returns else 0,
                    "win_rate": wins / len(returns) if returns else 0,
                    "best_return": max(returns) if returns else 0,
                    "worst_return": min(returns) if returns else 0,
                }

        except Exception as e:
            self.logger.error(f"Failed to get feedback stats: {e}")
            return {"total": 0, "avg_return": 0, "win_rate": 0}

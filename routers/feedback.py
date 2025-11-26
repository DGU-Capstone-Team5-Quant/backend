from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends

from config import Settings, get_settings
from services.simulation import SimulationService


router = APIRouter(prefix="/api/feedback", tags=["feedback"])


def get_service(settings: Settings = Depends(get_settings)) -> SimulationService:
    return SimulationService(settings)


@router.post("/check")
async def check_pending_feedbacks(
    service: SimulationService = Depends(get_service),
):
    """
    체크 날짜가 지난 피드백들을 확인하고 실제 결과 업데이트
    - 크론잡이나 수동으로 주기적으로 호출
    """
    count = await service.feedback_service.check_pending_feedbacks()
    return {"status": "ok", "checked_count": count}


@router.get("/stats")
async def get_feedback_stats(
    ticker: Optional[str] = None,
    service: SimulationService = Depends(get_service),
):
    """
    피드백 통계 조회
    - ticker가 없으면 전체 통계
    - ticker가 있으면 해당 종목 통계만
    """
    stats = await service.feedback_service.get_feedback_stats(ticker)
    return stats

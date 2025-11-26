from __future__ import annotations

import asyncio
import timeit
from typing import Optional

from config import Settings
from services.simulation import SimulationService
from services.metrics import metrics_tracker


async def _feedback_loop(settings: Settings, interval_seconds: int) -> None:
    service = SimulationService(settings)
    while True:
        t0 = timeit.default_timer()
        try:
            checked = await service.feedback_service.check_pending_feedbacks()
            metrics_tracker.record_feedback(success=True, duration=timeit.default_timer() - t0, checked_count=checked)
        except asyncio.CancelledError:
            raise
        except Exception:
            metrics_tracker.record_feedback(success=False, duration=timeit.default_timer() - t0, checked_count=0)
        await asyncio.sleep(interval_seconds)


def start_feedback_scheduler(settings: Settings, interval_seconds: int = 300) -> Optional[asyncio.Task]:
    """
    Start background feedback checker. Returns the asyncio.Task so the caller can cancel on shutdown.
    """
    try:
        loop = asyncio.get_event_loop()
        return loop.create_task(_feedback_loop(settings, interval_seconds))
    except Exception:
        return None

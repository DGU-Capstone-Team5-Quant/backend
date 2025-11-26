from fastapi import APIRouter

from services.metrics import metrics_tracker

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics() -> str:
    # Prometheus-format metrics
    return metrics_tracker.render_prometheus()

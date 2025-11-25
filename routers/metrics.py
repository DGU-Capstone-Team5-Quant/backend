from fastapi import APIRouter
import time

router = APIRouter(tags=["metrics"])
start_ts = time.time()


@router.get("/metrics")
async def metrics() -> str:
    # Minimal Prometheus-format metrics
    uptime = int(time.time() - start_ts)
    return f"app_uptime_seconds {uptime}\n"

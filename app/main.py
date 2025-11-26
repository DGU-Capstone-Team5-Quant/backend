import asyncio
from contextlib import suppress

from fastapi import FastAPI

from config import settings
from db.session import init_db
from routers import simulation
from routers import backtest
from routers import metrics
from routers import feedback
from services.feedback_scheduler import start_feedback_scheduler


def create_app() -> FastAPI:
    app = FastAPI(
        title="FinMem-Augmented Multi-Agent Trading Backend",
        version="0.1.0",
    )
    app.include_router(simulation.router, prefix="")
    app.include_router(backtest.router, prefix="")
    app.include_router(metrics.router, prefix="")
    app.include_router(feedback.router, prefix="")

    @app.on_event("startup")
    async def _startup() -> None:  # pragma: no cover - startup hook
        try:
            await init_db()
        except Exception:
            # DB 미설치 등 서버 기동만 우선 허용
            pass
        if settings.environment != "test":
            app.state.feedback_task = start_feedback_scheduler(settings, interval_seconds=300)

    @app.on_event("shutdown")
    async def _shutdown() -> None:  # pragma: no cover - shutdown hook
        task = getattr(app.state, "feedback_task", None)
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    return app


app = create_app()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.environment}

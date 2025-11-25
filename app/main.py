from fastapi import FastAPI

from config import settings
from db.session import init_db
from routers import simulation
from routers import backtest


def create_app() -> FastAPI:
    app = FastAPI(
        title="FinMem-Augmented Multi-Agent Trading Backend",
        version="0.1.0",
    )
    app.include_router(simulation.router, prefix="/api")
    app.include_router(backtest.router, prefix="")

    @app.on_event("startup")
    async def _startup() -> None:  # pragma: no cover - startup hook
        try:
            await init_db()
        except Exception:
            # DB 미설정 시에도 서버가 기동되도록 무시
            pass

    return app


app = create_app()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.environment}

from fastapi import FastAPI

from app.api.backtests import router as backtests_router
from app.api.candles import router as candles_router
from app.api.health import router as health_router
from app.api.scanner import router as scanner_router
from app.api.strategies import router as strategies_router
from app.api.ws_candles import router as ws_candles_router
from app.api.ws_scanner import router as ws_scanner_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    app = FastAPI(title="Market Analysis Assistant")
    app.include_router(health_router)
    app.include_router(candles_router)
    app.include_router(ws_candles_router)
    app.include_router(ws_scanner_router)
    app.include_router(scanner_router)
    app.include_router(backtests_router)
    app.include_router(strategies_router)
    # Test-only replay route; mounted solely under ENV=test, never in prod.
    if get_settings().env == "test":
        from app.api.test_routes import router as test_router

        app.include_router(test_router)
    return app


app = create_app()

from fastapi import FastAPI

from app.api.candles import router as candles_router
from app.api.health import router as health_router
from app.api.scanner import router as scanner_router
from app.api.ws_candles import router as ws_candles_router
from app.api.ws_scanner import router as ws_scanner_router


def create_app() -> FastAPI:
    app = FastAPI(title="Market Analysis Assistant")
    app.include_router(health_router)
    app.include_router(candles_router)
    app.include_router(ws_candles_router)
    app.include_router(ws_scanner_router)
    app.include_router(scanner_router)
    return app


app = create_app()

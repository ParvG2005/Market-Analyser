from fastapi import FastAPI

from app.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="Market Analysis Assistant")
    app.include_router(health_router)
    return app


app = create_app()

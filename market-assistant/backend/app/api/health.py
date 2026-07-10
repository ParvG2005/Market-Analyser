from fastapi import APIRouter
from sqlalchemy import text

from app.core.deps import get_engine, get_redis

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str | bool]:
    db_ok = False
    redis_ok = False

    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    try:
        r = get_redis()
        redis_ok = bool(await r.ping())
    except Exception:
        redis_ok = False

    return {"status": "ok", "db": db_ok, "redis": redis_ok}

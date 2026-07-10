from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://market:market@localhost:5434/market_assistant"
    redis_url: str = "redis://localhost:6379/0"
    UNIVERSE_SIZE: int = 20
    UNIVERSE_QUOTE_ASSET: str = "USDT"
    BINANCE_WS_BASE_URL: str = "wss://stream.binance.com:9443"
    WS_MAX_BACKOFF_S: float = 60.0
    BACKFILL_RATE_LIMIT_MS: int = 250
    NEWS_FEED_URLS: list[str] = []


@lru_cache
def get_settings() -> Settings:
    return Settings()

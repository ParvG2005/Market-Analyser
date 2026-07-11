from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Deployment environment. Only "test" mounts the test-only replay route
    # (see app.main); never set to "test" in production.
    env: str = "dev"
    database_url: str = "postgresql+asyncpg://market:market@localhost:5434/market_assistant"
    redis_url: str = "redis://localhost:6379/0"
    UNIVERSE_SIZE: int = 20
    UNIVERSE_QUOTE_ASSET: str = "USDT"
    BINANCE_WS_BASE_URL: str = "wss://stream.binance.com:9443"
    WS_MAX_BACKOFF_S: float = 60.0
    BACKFILL_RATE_LIMIT_MS: int = 250
    NEWS_FEED_URLS: list[str] = []
    EQUITY_POLL_INTERVAL_MIN: int = 15
    EQUITY_DELAY_MINUTES: int = 15

    # Chat assistant (Phase 10). Tests use a scripted provider, so keys may be unset.
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-sonnet-5"
    CHAT_RATE_LIMIT: int = 30
    CHAT_RATE_WINDOW_SECONDS: int = 3600

    # --- Phase 11: auth (Supabase JWT verification) ---
    jwt_secret: str = ""              # HS256 shared secret (Supabase legacy / local dev / tests)
    jwt_issuer: str = ""              # expected iss; "" disables the iss check
    jwt_audience: str = "authenticated"   # Supabase user-token aud
    supabase_url: str = ""            # https://<ref>.supabase.co
    supabase_jwks_url: str = ""       # if set -> verify RS256/ES256 via JWKS instead of HS256
    # --- Phase 11: hardening ---
    cors_allowed_origins: str = "http://localhost:5173"  # comma-separated origins
    sentry_dsn: str = ""
    # --- Phase 11: alerts ---
    telegram_bot_token: str = ""
    telegram_rate_limit_per_min: int = 20
    # --- DB schema isolation (Supabase multi-project). "public" => unchanged local/CI behavior ---
    db_schema: str = "public"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

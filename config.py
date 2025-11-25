from functools import lru_cache
from pydantic import Field, HttpUrl, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="local")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    rapid_api_key: str = Field(default="", alias="RAPID_API_KEY")
    rapid_api_host: str = Field(default="placeholder-rapidapi-host", alias="RAPID_API_HOST")
    price_endpoint: HttpUrl | str = Field(default="https://example-rapidapi-endpoint/prices", alias="RAPID_API_PRICE_URL")
    price_endpoint_intraday: HttpUrl | str = Field(default="", alias="RAPID_API_PRICE_URL_INTRADAY")
    price_endpoint_daily: HttpUrl | str = Field(default="", alias="RAPID_API_PRICE_URL_DAILY")
    news_endpoint: HttpUrl | str = Field(
        default="https://news.google.com/rss/search?q={symbol}+stock&hl=en-US&gl=US&ceid=US:en",
        alias="RAPID_API_NEWS_URL",
    )
    database_url: str = Field(default="postgresql+asyncpg://user:password@localhost:5432/finmem", alias="DATABASE_URL")
    postgres_url: str = Field(default="", alias="POSTGRES_URL")
    postgresql_url: str = Field(default="", alias="POSTGRESQL_URL")
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    redis_index: str = Field(default="finmem_index")
    redis_vector_dim: int = Field(default=768)
    gemini_model: str = Field(default="gemini-2.0-flash")
    memory_store_manager_only: bool = Field(default=True, alias="MEMORY_STORE_MANAGER_ONLY")
    memory_search_k: int = Field(default=3, alias="MEMORY_SEARCH_K")
    memory_recency_lambda: float = Field(default=0.01, alias="MEMORY_RECENCY_LAMBDA")  # score penalty per day
    memory_duplicate_threshold: float = Field(default=0.9, alias="MEMORY_DUPLICATE_THRESHOLD")
    memory_ttl_days: float = Field(default=30.0, alias="MEMORY_TTL_DAYS")  # expire after N days (filter at search time)
    memory_role_weights: dict[str, float] = Field(
        default_factory=lambda: {"manager": 1.5, "trader": 1.2, "bull": 1.0, "bear": 1.0, "mem": 1.0},
        alias="MEMORY_ROLE_WEIGHTS",
    )
    embedding_mode: str = Field(default="stub", alias="EMBEDDING_MODE")  # stub | gemini
    price_cache_ttl: float = Field(default=120.0, alias="PRICE_CACHE_TTL")
    news_cache_ttl: float = Field(default=300.0, alias="NEWS_CACHE_TTL")
    max_rounds: int = Field(default=1, alias="DEBATE_MAX_ROUNDS")
    max_rounds_bull_bear: int = Field(default=2, alias="DEBATE_MAX_BB_ROUNDS")
    interval_allowlist: list[str] = Field(
        default_factory=lambda: ["1min", "5min", "15min", "30min", "45min", "1h", "2h", "4h", "8h", "1day", "1week", "1month"]
    )
    working_mem_max: int = Field(default=10, alias="WORKING_MEM_MAX")

    @computed_field
    @property
    def db_url(self) -> str:
        # POSTGRES_URL 우선, 없으면 DATABASE_URL 기본값 사용
        return self.postgres_url or self.postgresql_url or self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

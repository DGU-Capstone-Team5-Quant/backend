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
    news_endpoint: HttpUrl | str = Field(default="https://example-rapidapi-endpoint/news", alias="RAPID_API_NEWS_URL")
    database_url: str = Field(default="postgresql+asyncpg://user:password@localhost:5432/finmem", alias="DATABASE_URL")
    postgres_url: str = Field(default="", alias="POSTGRES_URL")
    postgresql_url: str = Field(default="", alias="POSTGRESQL_URL")
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    redis_index: str = Field(default="finmem_index")
    redis_vector_dim: int = Field(default=768)
    gemini_model: str = Field(default="gemini-2.0-flash")

    @computed_field
    @property
    def db_url(self) -> str:
        # POSTGRES_URL 우선, 없으면 DATABASE_URL 기본값 사용
        return self.postgres_url or self.postgresql_url or self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

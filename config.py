from functools import lru_cache
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="local")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    rapid_api_key: str = Field(default="", alias="RAPID_API_KEY")
    rapid_api_host: str = Field(default="placeholder-rapidapi-host", alias="RAPID_API_HOST")
    price_endpoint: HttpUrl | str = Field(default="https://example-rapidapi-endpoint/prices", alias="RAPID_API_PRICE_URL")
    news_endpoint: HttpUrl | str = Field(default="https://example-rapidapi-endpoint/news", alias="RAPID_API_NEWS_URL")
    mysql_url: str = Field(default="mysql+asyncmy://user:password@localhost:3306/finmem", alias="MYSQL_URL")
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")
    redis_index: str = Field(default="finmem_index")
    redis_vector_dim: int = Field(default=768)
    gemini_model: str = Field(default="gemini-2.0-flash")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

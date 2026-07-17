from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Defaults to a local SQLite file so the app runs with zero external
    # services. Docker Compose overrides this with a Postgres URL via env.
    database_url: str = "sqlite:///./signalgraph.db"
    github_token: str = ""
    mock_mode: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Defaults to a local SQLite file so the app runs with zero external
    # services. Docker Compose overrides this with a Postgres URL via env.
    database_url: str = "sqlite:///./signalgraph.db"
    github_token: str = ""
    mock_mode: bool = True

    # Comma-separated origins allowed to call the API. Defaults to local dev;
    # a deployed frontend runs on a different origin and must be listed here or
    # the browser blocks every request.
    cors_allow_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins(self) -> list[str]:
        origins = [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]
        # allow_credentials=True makes "*" invalid per the CORS spec — browsers
        # reject a wildcard origin on credentialed requests — so drop it rather
        # than ship a config that silently fails in the browser.
        return [o for o in origins if o != "*"] or ["http://localhost:3000"]


@lru_cache
def get_settings() -> Settings:
    return Settings()

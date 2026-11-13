from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Defaults to a local SQLite file so the app runs with zero external
    # services. Docker Compose overrides this with a Postgres URL via env.
    database_url: str = "sqlite:///./signalgraph.db"
    github_token: str = ""
    mock_mode: bool = True

    # Same-day co-adoption (live mode only): for a sample of stargazers, count the other repos
    # they starred that UTC day via GitHub GraphQL. GitHub spends ~1 s per user, so this adds
    # roughly 10-30 s per analysis (capped at 30 s). Disable to skip the co-adoption signal.
    coadoption_enabled: bool = True
    coadoption_max_users: int = 60

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

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Source : Assemblée nationale ──────────────────────────────────────────
    an_base_url: str = "https://data.assemblee-nationale.fr"
    an_legislature: int = 17

    # ── Database ──────────────────────────────────────────────────────
    # Role isos_ingestion : owner of the schema `raw`, write-only on the
    # content tables of `public`.
    database_url: str = (
        "postgresql+asyncpg://isos_ingestion:isos_ingestion@localhost:5432/isos_db"
    )

    # ── Stockage objet (S3) ──────────────────────────────────
    s3_endpoint: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_bucket_raw: str = "isos-raw"

    # ── HTTP ──────────────────────────────────────────────────────────────────
    http_timeout_s: float = 30.0
    http_max_attempts: int = 3

    # ── Journalisation ────────────────────────────────────────────────────────
    log_level: str = "INFO"

    # ── API ───────────────────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8001

    @property
    def s3_enabled(self) -> bool:
        return bool(self.s3_endpoint and self.s3_access_key and self.s3_secret_key)

    @property
    def safe_database_target(self) -> str:
        from urllib.parse import urlsplit

        parts = urlsplit(self.database_url)
        user = parts.username or "?"
        host = parts.hostname or "?"
        port = f":{parts.port}" if parts.port else ""
        database = parts.path.lstrip("/") or "?"
        return f"{user}@{host}{port}/{database}"


@lru_cache
def get_settings() -> Settings:
    """
    Get the cached instance of the application settings.
    """
    return Settings()

import pytest

from src.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch):
    """Tests never read the developer's .env, and never reuse a cached Settings."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        an_base_url="https://data.assemblee-nationale.fr",
        an_legislature=17,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        s3_endpoint=None,
        log_level="WARNING",
    )

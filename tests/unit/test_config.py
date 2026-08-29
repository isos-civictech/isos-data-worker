from src.config import Settings, get_settings


def test_s3_disabled_when_no_endpoint(settings):
    assert settings.s3_enabled is False


def test_s3_needs_all_three_credentials():
    partial = Settings(s3_endpoint="http://garage:3900", s3_access_key="k", s3_secret_key=None)
    assert partial.s3_enabled is False

    complete = Settings(s3_endpoint="http://garage:3900", s3_access_key="k", s3_secret_key="s")
    assert complete.s3_enabled is True


def test_safe_database_target_hides_the_password():
    s = Settings(
        database_url="postgresql+asyncpg://isos_ingestion:tr3s-secret@db.internal:5432/isos_db"
    )
    target = s.safe_database_target

    assert target == "isos_ingestion@db.internal:5432/isos_db"
    assert "tr3s-secret" not in target


def test_environment_overrides_defaults(monkeypatch):
    monkeypatch.setenv("AN_LEGISLATURE", "16")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    get_settings.cache_clear()

    s = get_settings()

    assert s.an_legislature == 16
    assert s.log_level == "DEBUG"

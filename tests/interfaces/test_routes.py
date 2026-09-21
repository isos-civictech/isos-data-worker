"""Route wiring and status codes; business logic is covered in tests/application."""

import pytest
from fastapi.testclient import TestClient

from src.config import Settings
from src.interfaces.api.app import create_app
from src.interfaces.api.dependencies import get_engine, get_settings_dep


class FakeConnection:
    def __init__(self, rows=None, fail=False):
        self._rows = rows or []
        self._fail = fail

    async def execute(self, *_args, **_kwargs):
        if self._fail:
            raise RuntimeError("database is down")
        return _FakeResult(self._rows)

    async def __aenter__(self):
        if self._fail:
            raise RuntimeError("database is down")
        return self

    async def __aexit__(self, *_exc):
        return False


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


class FakeEngine:
    def __init__(self, rows=None, fail=False):
        self._rows = rows or []
        self._fail = fail

    def connect(self):
        return FakeConnection(self._rows, self._fail)


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_settings_dep] = lambda: Settings()
    app.dependency_overrides[get_engine] = lambda: FakeEngine()
    with TestClient(app) as test_client:
        yield test_client


def test_home_page_is_served(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "isos-data-worker" in response.text
    assert "text/html" in response.headers["content-type"]


def test_health_touches_nothing_else(client):
    """Liveness must not depend on Postgres, or a brief outage restarts the pod."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_db_reports_the_database(client):
    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_db_returns_503_when_the_database_is_down():
    app = create_app()
    app.dependency_overrides[get_engine] = lambda: FakeEngine(fail=True)

    with TestClient(app) as test_client:
        response = test_client.get("/health/db")

    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"


def test_jobs_lists_ingestion_runs(client):
    response = client.get("/jobs")

    assert response.status_code == 200
    assert response.json() == []


def test_openapi_is_generated(client):
    """The front consumes the schema; a broken schema breaks the front."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    for expected in ("/", "/health", "/health/db", "/jobs", "/collect/{dataset}"):
        assert expected in paths, f"{expected} is missing from the OpenAPI schema"


def test_every_trigger_route_is_a_post(client):
    paths = client.get("/openapi.json").json()["paths"]
    for route in (
        "/collect/{dataset}",
        "/project/{dataset}",
        "/sync/{dataset}",
        "/sync/all",
        "/refresh",
    ):
        assert "post" in paths[route], f"{route} must be a POST"


def test_unknown_dataset_is_a_404(client):
    assert client.post("/project/senators").status_code == 404
    assert client.post("/collect/senators").status_code == 404


def test_read_routes_are_exposed(client):
    paths = client.get("/openapi.json").json()["paths"]
    for route in (
        "/agenda/today",
        "/agenda/upcoming",
        "/laws/{uid}",
        "/laws/{uid}/amendments",
        "/laws/{uid}/articles/{article_ref}",
        "/deputies/{uid}/votes",
    ):
        assert "get" in paths[route], f"{route} must be a GET"


def test_agenda_read_routes(client):
    for route in ("/agenda/today", "/agenda/upcoming"):
        response = client.get(route)
        assert response.status_code == 200, route
        assert response.json() == []

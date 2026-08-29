"""
Fixtures partagées.

Une règle vaut d'être posée ici plutôt que rappelée dans chaque test : AUCUN
test ne doit pouvoir sortir de la machine. La fixture `settings` ci-dessous ne
configure aucun S3, donc la composition injecte `NoopStorage` ; et les appels
HTTP passent tous par respx, qui échoue si une requête n'est pas simulée.
"""
import pytest

from src.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """
    `get_settings` est mis en cache. Sans ce nettoyage, le premier test qui
    l'appelle fige la configuration pour toute la session, et les tests qui
    modifient l'environnement ensuite n'ont aucun effet — panne classique, et
    pénible à diagnostiquer.
    """
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings() -> Settings:
    """Configuration de test : rien qui sorte de la machine."""
    return Settings(
        an_base_url="https://data.assemblee-nationale.fr",
        an_legislature=17,
        database_url="postgresql+asyncpg://test:test@localhost:5432/test",
        s3_endpoint=None,
        log_level="WARNING",
    )

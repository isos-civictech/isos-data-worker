"""
Port : la piste d'audit de la collecte.

Deux niveaux, deux questions différentes :

  - `raw.ingestion_run`  : « quand a-t-on collecté les députés pour la dernière
    fois, et comment ça s'est passé ? » — une ligne par exécution. C'est ce que
    la route GET /jobs affiche.
  - `raw.ingestion_log`  : « d'où vient cette entité précise, quel fichier brut,
    quelle empreinte ? » — une ligne par entité réellement ingérée.

Règle : une entité inchangée n'écrit PAS de ligne de log. Sinon le journal se
remplit de « rien n'a changé » et ne répond plus à la question qu'on lui pose.
"""
from abc import ABC, abstractmethod

from src.domain.shared.results import SyncReport


class IngestionLogRepository(ABC):
    @abstractmethod
    async def start_run(self, entity_type: str, source_url: str | None = None) -> int:
        """Ouvre une exécution et renvoie son identifiant."""
        ...

    @abstractmethod
    async def finish_run(self, run_id: int, report: SyncReport) -> None:
        """Clôt l'exécution avec ses compteurs."""
        ...

    @abstractmethod
    async def record(
        self,
        *,
        run_id: int,
        entity_type: str,
        entity_uid: str,
        source_url: str | None = None,
        s3_key: str | None = None,
        checksum: str | None = None,
    ) -> None:
        ...

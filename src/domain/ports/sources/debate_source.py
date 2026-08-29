"""
Port : lire les comptes rendus de séance chez l'Assemblée nationale.

Source : syceron.xml.zip. C'est le format le moins régulier des trois — les noms
de balises varient d'un compte rendu à l'autre. L'irrégularité est absorbée par
l'adaptateur, jamais par le domaine : ce port ne promet que des `Debate`.
"""
from abc import ABC, abstractmethod

from src.domain.entities.debate import Debate
from src.domain.shared.validators import Legislature


class DebateSource(ABC):
    @abstractmethod
    async def fetch_all(
        self,
        legislature: Legislature,
        limit: int | None = None,
    ) -> list[Debate]:
        """
        Toutes les séances de la législature, avec leurs points d'ordre du jour
        et leurs interventions — les trois niveaux, conservés tels quels.
        """
        ...

    @abstractmethod
    async def fetch_by_uid(
        self,
        uid: str,
        legislature: Legislature,
    ) -> Debate | None:
        """Une seule séance par son uid AN. None si inconnue."""
        ...

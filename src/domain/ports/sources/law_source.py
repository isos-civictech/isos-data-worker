"""
Port : lire les dossiers législatifs chez l'Assemblée nationale.

Source : Dossiers_Legislatifs.json.zip (JSON, contrairement aux acteurs en XML).
"""
from abc import ABC, abstractmethod

from src.domain.entities.law import Law
from src.domain.shared.validators import Legislature


class LawSource(ABC):
    @abstractmethod
    async def fetch_all(
        self,
        legislature: Legislature,
        limit: int | None = None,
    ) -> list[Law]:
        """Tous les dossiers législatifs de la législature, étapes comprises."""
        ...

    @abstractmethod
    async def fetch_by_uid(
        self,
        dossier_uid: str,
        legislature: Legislature,
    ) -> Law | None:
        """Un seul dossier par son uid AN (« DLR5L17N47390 »). None si inconnu."""
        ...

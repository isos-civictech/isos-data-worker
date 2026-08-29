"""
Port : projeter les lois de `raw` vers le schéma d'affichage.

Deux pièges que cette projection absorbe, et que la collecte ignore :

  - le titre d'un dossier dépasse souvent 255 caractères alors que la colonne
    `name` est bornée ; le titre entier va dans `title`, la version courte
    dans `name` ;
  - seuls deux types de dossiers ont une représentation à l'affichage. Les
    autres (rapports d'information, par exemple) restent dans `raw` et sont
    comptés comme ignorés, jamais forcés dans un type qui ne leur convient pas.
"""
from abc import ABC, abstractmethod

from src.domain.shared.results import SyncReport
from src.domain.shared.validators import Legislature


class LawProjection(ABC):
    @abstractmethod
    async def project_all(self, legislature: Legislature) -> SyncReport:
        """Projette les dossiers et leurs lectures."""
        ...

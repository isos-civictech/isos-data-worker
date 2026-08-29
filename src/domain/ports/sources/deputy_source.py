"""
Port : lire les députés chez l'Assemblée nationale.

C'est une SOURCE, pas un dépôt : elle ne fait que lire, chez quelqu'un d'autre.
L'implémentation concrète (`infrastructure/adapters/an_deputy_adapter.py`) sait
télécharger un ZIP et parser du XML ; cette interface, elle, ne connaît que des
entités du domaine. C'est ce qui permet de tester les cas d'usage sans réseau,
en injectant un faux.
"""
from abc import ABC, abstractmethod

from src.domain.entities.deputy import Deputy
from src.domain.entities.political_group import PoliticalGroupRef
from src.domain.shared.validators import Legislature


class DeputySource(ABC):
    @abstractmethod
    async def fetch_political_groups(
        self,
        legislature: Legislature,
    ) -> list[PoliticalGroupRef]:
        """
        Tous les groupes politiques de la législature.

        À appeler AVANT `fetch_all` : un mandat référence son groupe par uid, et
        côté projection `deputy_mandate.political_group_id` est NOT NULL. Ce
        n'est donc pas une optimisation, c'est le seul ordre qui fonctionne.
        """
        ...

    @abstractmethod
    async def fetch_all(
        self,
        legislature: Legislature,
        limit: int | None = None,
    ) -> list[Deputy]:
        """
        Tous les députés de la législature, mandats compris.

        `limit` sert au développement et aux tests : itérer sur 5 députés au
        lieu de 600 change une boucle de rétroaction de 3 minutes en 2 secondes.
        """
        ...

    @abstractmethod
    async def fetch_by_uid(
        self,
        uid: str,
        legislature: Legislature,
    ) -> Deputy | None:
        """
        Un seul député par son uid AN (« PA1592 »). None si inconnu.

        Sert la route POST /collect/deputies/{uid} : rejouer un enregistrement
        qui a échoué sans relancer tout le run.
        """
        ...

"""
Port : écrire les députés dans le schéma `raw`.

C'est un DÉPÔT : il persiste, chez nous. La différence avec `sources/` n'est pas
cosmétique — une source peut échouer, être lente, changer de format sans
prévenir ; un dépôt écrit dans un schéma dont nous sommes propriétaires.

Ce que ce port promet, et qui vaut d'être connu du domaine :
  - l'écriture est IDEMPOTENTE (upsert sur l'uid AN) ;
  - elle ne supprime jamais rien ;
  - un député et ses mandats forment une seule unité — le cas d'usage ouvre une
    transaction par député, donc `save` ne doit pas en ouvrir une autre.
"""
from abc import ABC, abstractmethod

from src.domain.entities.deputy import Deputy
from src.domain.entities.political_group import PoliticalGroupRef
from src.domain.shared.results import SaveOutcome


class DeputyRepository(ABC):
    @abstractmethod
    async def save(self, deputy: Deputy) -> SaveOutcome:
        """
        Insère ou met à jour un député et tous ses mandats.

        `SaveOutcome.created` vaut faux si la ligne existait déjà : c'est ce qui
        permet au compte-rendu de distinguer une première collecte d'un
        deuxième run, et donc de vérifier l'idempotence.
        """
        ...

    @abstractmethod
    async def save_political_groups(
        self,
        groups: list[PoliticalGroupRef],
    ) -> int:
        """Insère ou met à jour les groupes politiques. Renvoie le nombre traité."""
        ...

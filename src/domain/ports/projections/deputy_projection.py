"""
Port : projeter les députés de `raw` vers le schéma d'affichage.

Une projection ne touche JAMAIS au réseau. Elle lit des faits déjà collectés et
les adapte à un schéma qui ne nous appartient pas : identifiants entiers,
slugs obligatoires et uniques, enums en anglais, clés étrangères à résoudre.

C'est le bénéfice quotidien de la séparation : quand une correspondance est
fausse — un mauvais libellé, un slug mal construit — on relance la projection
seule, en quelques secondes, sans redemander quoi que ce soit à l'Assemblée.
"""
from abc import ABC, abstractmethod

from src.domain.shared.results import SyncReport
from src.domain.shared.validators import Legislature


class DeputyProjection(ABC):
    @abstractmethod
    async def project_all(self, legislature: Legislature) -> SyncReport:
        """
        Projette groupes, députés et mandats, dans cet ordre.

        L'ordre est imposé par le schéma cible : `deputy_mandate` référence un
        groupe politique en NOT NULL, donc les groupes doivent exister avant.
        """
        ...

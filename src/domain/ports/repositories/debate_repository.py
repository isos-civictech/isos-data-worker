"""
Port : écrire les séances dans le schéma `raw`.

Une séance est un agrégat à trois niveaux : la séance, ses points d'ordre du
jour, et les interventions de chaque point. `save` écrit les trois ensemble ou
n'écrit rien — d'où une transaction par séance côté cas d'usage.

C'est ce découpage par point qui rendra possible un résumé sujet par sujet
(« questions au gouvernement », « discussion du projet de loi X ») alors que le
schéma d'affichage, lui, ne connaît que la séance entière.
"""
from abc import ABC, abstractmethod

from src.domain.entities.debate import Debate
from src.domain.shared.results import SaveOutcome


class DebateRepository(ABC):
    @abstractmethod
    async def save(self, debate: Debate) -> SaveOutcome:
        """Insère ou met à jour une séance, ses points et ses interventions."""
        ...

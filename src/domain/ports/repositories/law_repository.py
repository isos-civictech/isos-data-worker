"""
Port : écrire les lois dans le schéma `raw`.

`save_article` porte la règle métier la plus importante du projet : le texte
d'un article n'est JAMAIS écrasé. Quand il change, une nouvelle version est
créée et l'ancienne est marquée non courante, sans être supprimée.

Pourquoi cette règle vit ici, dans le domaine, et pas dans l'infrastructure :
c'est une promesse faite au moteur de recherche sémantique. Un chunk indexé
pointe sur une ligne précise ; si cette ligne est modifiée en place, la
recherche renvoie un texte qui n'a jamais été celui qui a été indexé.
"""
from abc import ABC, abstractmethod

from src.domain.entities.law import Law
from src.domain.entities.law_article import LawArticle
from src.domain.shared.results import SaveOutcome


class LawRepository(ABC):
    @abstractmethod
    async def save(self, law: Law) -> SaveOutcome:
        """Insère ou met à jour un dossier législatif et ses étapes."""
        ...

    @abstractmethod
    async def save_article(self, article: LawArticle) -> SaveOutcome:
        """
        Enregistre une version d'article.

        Trois cas, et un seul écrit quelque chose :
          - inconnu            → version 1 ;
          - contenu identique  → rien (comparaison par empreinte) ;
          - contenu différent  → l'ancienne version passe à `is_current = false`
                                 et une nouvelle ligne est insérée.

        `SaveOutcome.created` est vrai dans les deux cas où une ligne naît.
        """
        ...

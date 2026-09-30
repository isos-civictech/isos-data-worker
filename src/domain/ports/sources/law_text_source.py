"""Port: read the text of a law, article by article, from the Assemblée nationale website."""

from abc import ABC, abstractmethod

from src.domain.entities.law_text import LawText
from src.domain.shared.validators import Legislature


class LawTextSource(ABC):
    @abstractmethod
    async def fetch(self, texte_uid: str, legislature: Legislature) -> LawText | None:
        """None when the website does not serve this text (Sénat, provisional)."""
        ...

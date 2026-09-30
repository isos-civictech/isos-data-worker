"""Port: project law texts from `raw` into `public.law_text` / `public.law_article`."""

from abc import ABC, abstractmethod

from src.domain.shared.results import SyncReport


class LawTextProjection(ABC):
    @abstractmethod
    async def project_all(self, legislature: int) -> SyncReport:
        """
        One public.law_text per version, one public.law_article per article,
        and public.amendment.law_article_id set from (texte, article_ref).
        """
        ...

"""Port: project scrutins from `raw` into `public.ballot` and `public.deputy_vote`."""

from abc import ABC, abstractmethod

from src.domain.shared.results import SyncReport


class BallotProjection(ABC):
    @abstractmethod
    async def project_all(self, legislature: int) -> SyncReport:
        """
        One public.ballot per scrutin, linked to its sitting, its law, its
        reading and — when the vote is on an amendment — the amendment. One
        public.deputy_vote per deputy and scrutin.
        """
        ...

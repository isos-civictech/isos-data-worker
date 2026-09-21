"""Port: read amendments from the Assemblée nationale."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from datetime import date

from src.domain.entities.amendment import Amendment
from src.domain.shared.validators import Legislature


class AmendmentSource(ABC):
    @abstractmethod
    def iter_all(
        self,
        legislature: Legislature,
        *,
        dossier_uid: str | None = None,
        since: date | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[Amendment]:
        """
        Streams: ~125 000 amendments per legislature is too many to hold as a
        list. `since` filters on the deposit date, `dossier_uid` on one dossier.
        """
        ...

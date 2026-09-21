"""
AgendaItem — one public sitting (séance publique) as scheduled by the Assemblée.

It exists BEFORE the sitting happens, which is what makes "what is on today"
and "upcoming sittings" possible. Once the sitting has taken place, its
compte rendu (Debate) is linked through `debate_uid`.

Source: Agenda XML
    ZIP: https://data.assemblee-nationale.fr/static/openData/repository/{legislature}/vp/reunions/Agenda.xml.zip
    Members: xml/reunion/RUANR5L{legislature}S{year}IDS{n}.xml
             Only xsi:type="seance_type" with a RUAN uid (Assemblée). The same
             archive holds commissions (IDC), parliamentary initiatives (IDFL)
             and Sénat sittings (RUSN); all are skipped.

XML field mapping (default namespace http://schemas.assemblee-nationale.fr/referentiel):
    uid            → reunion/uid                       ("RUANR5L17S2024IDS28538")
    start_at       → reunion/timeStampDebut            ISO 8601 with offset
    end_at         → reunion/timeStampFin
    location       → reunion/lieu/libelleLong
    state          → reunion/cycleDeVie/etat           "Confirmé" | "Supprimé"
    debate_uid     → reunion/compteRenduRef            ("CRSANR5L17S2024D1N002"), absent until held
    session_rank   → reunion/identifiants/quantieme    "Première" | "Deuxième" | "Unique"…
    session_number → reunion/identifiants/numSeanceJO
    points         → reunion/ODJ/pointsODJ/pointODJ[]

S3 key: raw/agenda/{legislature}/Agenda.xml.zip
"""

from datetime import UTC, datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, computed_field

from src.domain.entities.agenda_point import AgendaPoint
from src.domain.shared.validators import Legislature, NotBlankStr

CANCELLED_STATE = "Supprimé"
# A sitting with no end time is over once this much time has passed since it
# started: no sitting lasts a full day.
MAX_SITTING_DURATION = timedelta(hours=12)


class SessionStatus(StrEnum):
    SCHEDULED = "scheduled"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AgendaItem(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    uid: NotBlankStr
    legislature: Legislature
    start_at: datetime
    end_at: datetime | None = None
    location: str | None = None
    state: str | None = None
    debate_uid: str | None = None
    session_rank: str | None = None
    session_number: int | None = None
    points: list[AgendaPoint] = []

    @computed_field
    @property
    def cancelled(self) -> bool:
        return self.state == CANCELLED_STATE

    @computed_field
    @property
    def status(self) -> SessionStatus:
        """Where the sitting stands right now — the value public.calendar_status wants."""
        if self.cancelled:
            return SessionStatus.CANCELLED
        now = datetime.now(tz=UTC)
        if now < self.start_at:
            return SessionStatus.SCHEDULED
        if self.debate_uid:
            return SessionStatus.COMPLETED
        end = self.end_at or self.start_at + MAX_SITTING_DURATION
        return SessionStatus.COMPLETED if now > end else SessionStatus.ONGOING

    @computed_field
    @property
    def dossier_refs(self) -> list[str]:
        """Every law dossier on the agenda, in order, deduplicated."""
        seen: set[str] = set()
        out: list[str] = []
        for point in self.points:
            for ref in point.dossier_refs:
                if ref not in seen:
                    seen.add(ref)
                    out.append(ref)
        return out

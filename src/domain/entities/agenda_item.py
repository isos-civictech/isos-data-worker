"""
AgendaItem — a planned or ongoing parliamentary session.

Source: Agenda XML
    ZIP : https://data.assemblee-nationale.fr/static/openData/repository/
        {legislature}/vp/reunions/Agenda.xml.zip
    JSON: same path with .json.zip extension
    Public sessions CSV:
        https://data.assemblee-nationale.fr/static/openData/repository/
        {legislature}/vp/seances/seances_publique_libre_office.csv

XML field mapping :
    uid          → reunion/uid
    legislature  → derived from URL / settings
    start_date   → reunion/timestampDebut
    end_date     → reunion/timestampFin
    location     → reunion/lieu/salle
    meeting_type → reunion/xsiType
    title        → reunion/libelle
    text_refs    → reunion/odj/pointOdj[]/texte/textesAssocies/texteAssocie/texteRef

Lifecycle:
    status = SCHEDULED ("prévue")   → session not yet started
    status = ONGOING ("en cours")   → session in progress (start_date passed, end_date not yet)
    status = COMPLETED ("terminée") → session ended, Syceron XML should be available soon
    status = CANCELLED ("annulée")  → session was cancelled before taking place

S3 path: raw/agenda/{legislature}/{year}/{month}/Agenda.xml.zip (full ZIP)
"""

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field

from src.domain.shared.validators import Legislature, NotBlankStr


class SessionStatus(StrEnum):
    SCHEDULED = "prévue"
    ONGOING = "en cours"
    COMPLETED = "terminée"
    CANCELLED = "annulée"


class AgendaItem(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    uid: NotBlankStr
    legislature: Legislature
    start_date: datetime = Field(alias="date_debut")
    end_date: datetime | None = Field(default=None, alias="date_fin")
    title: str | None = None
    location: str | None = Field(default=None, alias="lieu")
    meeting_type: str | None = Field(default=None, alias="type_reunion")
    text_refs: list[str] = Field(default_factory=list, alias="texte_refs")
    debate_uid: str | None = None
    cancelled: bool = False

    @computed_field
    @property
    def status(self) -> SessionStatus:
        if self.cancelled:
            return SessionStatus.CANCELLED
        now = datetime.now(tz=UTC)
        start = self.start_date if self.start_date.tzinfo else self.start_date.replace(tzinfo=UTC)
        end = None
        if self.end_date:
            end = self.end_date if self.end_date.tzinfo else self.end_date.replace(tzinfo=UTC)
        if now < start:
            return SessionStatus.SCHEDULED
        if end and now > end:
            return SessionStatus.COMPLETED
        return SessionStatus.ONGOING

    @computed_field
    @property
    def is_ready_to_scrape(self) -> bool:
        return self.status == SessionStatus.COMPLETED and self.debate_uid is None

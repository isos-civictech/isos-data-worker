"""Scheduled-sitting persistence in `raw`. One transaction per sitting."""

from sqlalchemy.ext.asyncio import AsyncEngine

from src.domain.entities.agenda_item import AgendaItem
from src.domain.ports.repositories.agenda_repository import AgendaRepository
from src.domain.shared.results import SaveOutcome
from src.infrastructure.persistence.engine import transaction
from src.infrastructure.persistence.raw import tables
from src.infrastructure.persistence.raw.debate_repository import _bulk_upsert
from src.infrastructure.persistence.raw.deputy_repository import _upsert
from src.infrastructure.persistence.raw.mappers.agenda_mapper import (
    agenda_item_row,
    agenda_point_row,
)


class SqlRawAgendaRepository(AgendaRepository):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def save(
        self, item: AgendaItem, *, run_id: int, s3_key: str | None = None
    ) -> SaveOutcome:
        row = agenda_item_row(item) | {"ingestion_run_id": run_id, "s3_key": s3_key}
        async with transaction(self._engine) as connection:
            item_id, created = (
                await connection.execute(_upsert(tables.agenda_item, row, key="uid"))
            ).one()
            points = [agenda_point_row(p, agenda_uid=item.uid) for p in item.points if p.uid]
            if points:
                await connection.execute(_bulk_upsert(tables.agenda_point, points, key="point_uid"))
        return SaveOutcome(entity_id=item_id, created=created)

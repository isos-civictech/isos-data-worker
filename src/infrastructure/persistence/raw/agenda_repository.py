"""Scheduled-sitting persistence in `raw`. One transaction per sitting."""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from src.domain.entities.agenda_item import AgendaItem
from src.domain.ports.repositories.agenda_repository import AgendaRepository, SittingLink
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

    async def latest_held(
        self, legislature: int, count: int, before: datetime
    ) -> list[SittingLink]:
        item, point = tables.agenda_item, tables.agenda_point
        latest = (
            sa.select(item.c.uid, item.c.compte_rendu_uid)
            .where(item.c.legislature == legislature, item.c.start_at < before)
            .order_by(item.c.start_at.desc())
            .limit(count)
        )
        async with self._engine.connect() as connection:
            sittings = (await connection.execute(latest)).all()
            uids = [uid for uid, _ in sittings]
            refs = (
                await connection.execute(
                    sa.select(point.c.agenda_uid, point.c.dossier_refs).where(
                        point.c.agenda_uid.in_(uids)
                    )
                )
            ).all()
        dossiers: dict[str, set[str]] = {}
        for agenda_uid, dossier_refs in refs:
            dossiers.setdefault(agenda_uid, set()).update(d for d in dossier_refs if d)
        return [
            SittingLink(uid, compte_rendu, frozenset(dossiers.get(uid, ())))
            for uid, compte_rendu in sittings
        ]

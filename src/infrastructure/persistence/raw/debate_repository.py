"""
Sitting persistence in `raw`. One transaction per sitting: the sitting, its
points and its speeches land together or not at all.

A sitting holds ~50 points and ~400 speeches; both are written as one
multi-row INSERT each rather than row by row.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from src.domain.entities.debate import Debate
from src.domain.ports.repositories.debate_repository import DebateRepository
from src.domain.shared.results import SaveOutcome
from src.infrastructure.persistence.engine import transaction
from src.infrastructure.persistence.raw import tables
from src.infrastructure.persistence.raw.deputy_repository import _upsert
from src.infrastructure.persistence.raw.mappers.debate_mapper import (
    debate_row,
    intervention_row,
    point_row,
)


def _bulk_upsert(table: sa.Table, rows: list[dict], *, key: str):
    """Multi-row INSERT ... ON CONFLICT (key) DO UPDATE of every other column."""
    statement = insert(table).values(rows)
    updates = {c: statement.excluded[c] for c in rows[0] if c != key}
    return statement.on_conflict_do_update(index_elements=[key], set_=updates)


class SqlRawDebateRepository(DebateRepository):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def save(self, debate: Debate, *, run_id: int, s3_key: str | None = None) -> SaveOutcome:
        row = debate_row(debate) | {"ingestion_run_id": run_id, "s3_key": s3_key}

        async with transaction(self._engine) as connection:
            debate_id, created = (
                await connection.execute(_upsert(tables.debate, row, key="uid"))
            ).one()

            points = [p for p in debate.points if p.uid]
            if not points:
                return SaveOutcome(entity_id=debate_id, created=created)

            await connection.execute(
                _bulk_upsert(
                    tables.debate_point,
                    [point_row(p, debate_uid=debate.uid) for p in points],
                    key="point_uid",
                )
            )
            # Speeches reference their point by surrogate id: read them back once.
            point_ids = dict(
                (
                    await connection.execute(
                        sa.select(tables.debate_point.c.point_uid, tables.debate_point.c.id).where(
                            tables.debate_point.c.debate_uid == debate.uid
                        )
                    )
                ).all()
            )
            speeches = [
                intervention_row(i, debate_point_id=point_ids[p.uid])
                for p in points
                for i in p.interventions
                if i.uid
            ]
            if speeches:
                await connection.execute(_bulk_upsert(tables.intervention, speeches, key="uid"))

        return SaveOutcome(entity_id=debate_id, created=created)

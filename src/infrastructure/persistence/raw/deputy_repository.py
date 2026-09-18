"""
Deputy persistence in `raw`. One transaction per deputy: the deputy and its
mandates land together or not at all.
"""
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from src.domain.entities.deputy import Deputy
from src.domain.entities.political_group import PoliticalGroupRef
from src.domain.ports.repositories.deputy_repository import DeputyRepository
from src.domain.shared.results import SaveOutcome
from src.infrastructure.persistence.engine import transaction
from src.infrastructure.persistence.raw import tables
from src.infrastructure.persistence.raw.mappers.deputy_mapper import (
    deputy_row,
    mandate_row,
    political_group_row,
)

# Bookkeeping columns: never part of the "did the content change?" comparison.
_TRACKING = {"first_seen_at", "last_seen_at", "updated_at", "last_run_id", "s3_key"}


def _upsert(table: sa.Table, row: dict[str, Any], *, key: str, tracked: bool = True):
    """
    INSERT … ON CONFLICT (key) DO UPDATE.

    `updated_at` only moves when a content column differs (IS DISTINCT FROM),
    so a re-run leaves it untouched. `(xmax = 0)` tells an insert from an update.
    """
    statement = insert(table).values(**row)
    excluded = statement.excluded
    content = [c for c in row if c != key and c not in _TRACKING]

    updates: dict[str, Any] = {c: excluded[c] for c in row if c != key}
    if tracked:
        changed = sa.tuple_(*(table.c[c] for c in content)).is_distinct_from(
            sa.tuple_(*(excluded[c] for c in content))
        )
        updates["last_seen_at"] = sa.func.now()
        updates["updated_at"] = sa.case((changed, sa.func.now()), else_=table.c.updated_at)

    return statement.on_conflict_do_update(index_elements=[key], set_=updates).returning(
        table.c.id, (sa.column("xmax") == 0).label("created")
    )


class SqlRawDeputyRepository(DeputyRepository):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def save(
        self,
        deputy: Deputy,
        *,
        legislature: int,
        run_id: int,
        s3_key: str | None = None,
    ) -> SaveOutcome:
        tracking = {"last_run_id": run_id, "s3_key": s3_key}
        row = deputy_row(deputy, legislature=legislature) | tracking
        async with transaction(self._engine) as connection:
            deputy_id, created = (
                await connection.execute(_upsert(tables.deputy, row, key="uid"))
            ).one()
            for mandate in deputy.mandates:
                await connection.execute(
                    _upsert(tables.mandate, mandate_row(mandate), key="uid", tracked=False)
                )
        return SaveOutcome(entity_id=deputy_id, created=created)

    async def save_political_groups(
        self, groups: list[PoliticalGroupRef], *, run_id: int, s3_key: str | None = None
    ) -> int:
        if not groups:
            return 0
        async with transaction(self._engine) as connection:
            for group in groups:
                row = political_group_row(group) | {"last_run_id": run_id, "s3_key": s3_key}
                await connection.execute(_upsert(tables.political_group, row, key="uid"))
        return len(groups)

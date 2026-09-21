"""Amendment persistence in `raw`. One transaction per batch."""

from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from src.domain.entities.amendment import Amendment
from src.domain.ports.repositories.amendment_repository import AmendmentRepository
from src.domain.shared.results import BatchOutcome
from src.infrastructure.persistence.engine import transaction
from src.infrastructure.persistence.raw import tables
from src.infrastructure.persistence.raw.deputy_repository import _TRACKING
from src.infrastructure.persistence.raw.mappers.amendment_mapper import amendment_row


def _bulk_upsert_tracked(table: sa.Table, rows: list[dict[str, Any]], *, key: str):
    """
    Multi-row version of deputy_repository._upsert: updated_at moves only when
    a content column differs. Returns one `created` flag per row.
    """
    statement = insert(table).values(rows)
    excluded = statement.excluded
    content = [c for c in rows[0] if c != key and c not in _TRACKING]
    changed = sa.tuple_(*(table.c[c] for c in content)).is_distinct_from(
        sa.tuple_(*(excluded[c] for c in content))
    )
    updates: dict[str, Any] = {c: excluded[c] for c in rows[0] if c != key}
    updates["updated_at"] = sa.case((changed, sa.func.now()), else_=table.c.updated_at)
    return statement.on_conflict_do_update(index_elements=[key], set_=updates).returning(
        (sa.column("xmax") == 0).label("created")
    )


class SqlRawAmendmentRepository(AmendmentRepository):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def save_batch(
        self, amendments: list[Amendment], *, run_id: int, s3_key: str | None = None
    ) -> BatchOutcome:
        if not amendments:
            return BatchOutcome(created=0, updated=0)
        rows = [
            amendment_row(a) | {"ingestion_run_id": run_id, "s3_key": s3_key} for a in amendments
        ]
        async with transaction(self._engine) as connection:
            flags = (
                (await connection.execute(_bulk_upsert_tracked(tables.amendment, rows, key="uid")))
                .scalars()
                .all()
            )
        created = sum(flags)
        return BatchOutcome(created=created, updated=len(flags) - created)

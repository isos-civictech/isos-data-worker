"""
raw -> public projection for sittings: one public.debate per compte rendu.

debate_law is not written here: Syceron carries text NUMBERS, and the number
-> law resolution needs laws in raw first. deputy_quote is not written either
(no unique key in public to make it idempotent).
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from src.domain.ports.projections.debate_projection import DebateProjection
from src.domain.shared.results import SyncReport
from src.infrastructure.persistence.engine import transaction
from src.infrastructure.persistence.raw import tables as raw
from src.infrastructure.persistence.serving import tables as pub
from src.infrastructure.persistence.serving.mappers.debate_mapper import debate_row

WRITE_ONCE = ("slug",)


class SqlDebateProjection(DebateProjection):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def project_all(self, legislature: int) -> SyncReport:
        report = SyncReport(entity="debate-projection")

        async with self._engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        sa.select(raw.debate)
                        .where(raw.debate.c.legislature == legislature)
                        .order_by(raw.debate.c.date)
                    )
                )
                .mappings()
                .all()
            )

        for sitting in rows:
            report.processed += 1
            row = debate_row(dict(sitting))
            async with transaction(self._engine) as connection:
                # public.debate.external_id is UNIQUE since isos-api's e7a3c9d1f5b2.
                statement = (
                    insert(pub.debate)
                    .values(**row)
                    .on_conflict_do_update(
                        index_elements=["external_id"],
                        set_={k: v for k, v in row.items() if k not in WRITE_ONCE}
                        | {"updated_at": sa.func.now()},
                    )
                    .returning(pub.debate.c.id, (sa.column("xmax") == 0).label("created"))
                )
                _, created = (await connection.execute(statement)).one()
            report.created += int(created)
            report.updated += int(not created)

        return report.finish()

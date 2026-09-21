"""
raw -> public projection for laws.

public.law      one row per dossier that is a projet / proposition de loi
public.law_reading   one row per reading stage (AN1, SN1, CMP…)
public.debate_law    one link per public sitting the law was discussed in, from
                     raw.law_stage.sitting_refs and raw.agenda_point.dossier_refs
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from src.domain.entities.law import Law
from src.domain.ports.projections.law_projection import LawProjection
from src.domain.shared.results import SyncReport
from src.infrastructure.persistence.engine import transaction
from src.infrastructure.persistence.raw import tables as raw
from src.infrastructure.persistence.serving import tables as pub
from src.infrastructure.persistence.serving.deputy_projection import ensure_legislature
from src.infrastructure.persistence.serving.mappers.law_mapper import (
    law_from_raw,
    law_reading_row,
    law_row,
)
from src.infrastructure.persistence.serving.slug import unique_slug

WRITE_ONCE = ("slug",)


class SqlLawProjection(LawProjection):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def project_all(self, legislature: int) -> SyncReport:
        report = SyncReport(entity="law-projection")

        async with transaction(self._engine) as connection:
            dossiers = (
                (
                    await connection.execute(
                        sa.select(raw.law)
                        # Older dossiers still alive are projected under their own legislature.
                        .where(raw.law.c.legislature <= legislature)
                        .order_by(raw.law.c.id)
                    )
                )
                .mappings()
                .all()
            )

        for dossier in dossiers:
            report.processed += 1
            async with transaction(self._engine) as connection:
                stages = (
                    (
                        await connection.execute(
                            sa.select(raw.law_stage)
                            .where(raw.law_stage.c.dossier_uid == dossier["dossier_uid"])
                            .order_by(raw.law_stage.c.position)
                        )
                    )
                    .mappings()
                    .all()
                )
                law = law_from_raw(dict(dossier), [dict(s) for s in stages])
                if not law.is_law:
                    report.skipped += 1
                    continue
                legislature_id = await ensure_legislature(connection, law.legislature)
                law_id, created = await self._upsert_law(connection, law, legislature_id)
                reading_ids = await self._upsert_readings(connection, law, law_id)
                await self._link_debates(connection, law, law_id, reading_ids)
            report.created += int(created)
            report.updated += int(not created)

        return report.finish()

    async def _upsert_law(
        self, connection: AsyncConnection, law: Law, legislature_id: int
    ) -> tuple[int, bool]:
        row = law_row(law, legislature_id=legislature_id)
        row["slug"] = await unique_slug(connection, pub.law, row["slug"], row["external_id"])
        statement = (
            insert(pub.law)
            .values(**row)
            .on_conflict_do_update(
                index_elements=["external_id"],
                set_={k: v for k, v in row.items() if k not in WRITE_ONCE}
                | {"updated_at": sa.func.now()},
            )
            .returning(pub.law.c.id, (sa.column("xmax") == 0).label("created"))
        )
        return (await connection.execute(statement)).one()

    async def _upsert_readings(
        self, connection: AsyncConnection, law: Law, law_id: int
    ) -> dict[str, int]:
        """No unique key on law_reading: lookup on (law, chamber, number). Returns uid -> id."""
        ids: dict[str, int] = {}
        for stage in law.stages:
            row = law_reading_row(stage, law_id=law_id)
            if row is None:
                continue
            existing = (
                await connection.execute(
                    sa.select(pub.law_reading.c.id).where(
                        pub.law_reading.c.law_id == law_id,
                        pub.law_reading.c.chamber == row["chamber"],
                        pub.law_reading.c.reading_number == row["reading_number"],
                    )
                )
            ).scalar()
            if existing is None:
                existing = (
                    await connection.execute(
                        insert(pub.law_reading).values(**row).returning(pub.law_reading.c.id)
                    )
                ).scalar_one()
            else:
                await connection.execute(
                    sa.update(pub.law_reading).where(pub.law_reading.c.id == existing).values(**row)
                )
            ids[stage.uid] = existing
        return ids

    async def _link_debates(
        self, connection: AsyncConnection, law: Law, law_id: int, reading_ids: dict[str, int]
    ) -> None:
        # Sitting uid -> reading id, from the dossier's own acts…
        sittings: dict[str, int | None] = {
            ref: reading_ids.get(stage.uid) for stage in law.stages for ref in stage.sitting_refs
        }
        # …plus sittings whose agenda lists this dossier (no reading known).
        agenda_uids = (
            await connection.execute(
                sa.select(raw.agenda_point.c.agenda_uid).where(
                    raw.agenda_point.c.dossier_refs.any(law.dossier_uid)
                )
            )
        ).scalars()
        for uid in agenda_uids:
            sittings.setdefault(uid, None)
        if not sittings:
            return

        debate_ids = dict(
            (
                await connection.execute(
                    sa.select(pub.debate.c.external_id, pub.debate.c.id).where(
                        pub.debate.c.external_id.in_(list(sittings))
                    )
                )
            ).all()
        )
        rows = [
            {"debate_id": debate_ids[uid], "law_id": law_id, "law_reading_id": reading_id}
            for uid, reading_id in sittings.items()
            if uid in debate_ids  # Sénat sittings are not in public.debate
        ]
        if not rows:
            return
        statement = insert(pub.debate_law).values(rows)
        await connection.execute(
            statement.on_conflict_do_update(
                index_elements=["debate_id", "law_id"],
                set_={
                    "law_reading_id": sa.func.coalesce(
                        statement.excluded.law_reading_id, pub.debate_law.c.law_reading_id
                    )
                },
            )
        )

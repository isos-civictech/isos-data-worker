"""
raw -> public projection for the agenda: one public.debate per Assemblée sitting.

The row is keyed by the AGENDA uid and carries calendar_status. It exists
before the sitting happens (scheduled), then flips to completed or cancelled.
The compte rendu projection enriches the same row later, found through
raw.agenda_item.compte_rendu_uid.
"""

from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from src.domain.entities.agenda_item import CANCELLED_STATE, MAX_SITTING_DURATION
from src.domain.ports.projections.agenda_projection import AgendaProjection
from src.domain.shared.results import SyncReport
from src.infrastructure.persistence.engine import transaction
from src.infrastructure.persistence.raw import tables as raw
from src.infrastructure.persistence.serving import tables as pub
from src.infrastructure.persistence.serving.mappers.agenda_mapper import debate_row_from_agenda
from src.infrastructure.persistence.serving.slug import unique_slug

WRITE_ONCE = ("slug",)


def calendar_status(row, now: datetime) -> str:
    """Same rule as AgendaItem.status, on a raw row."""
    if row["state"] == CANCELLED_STATE:
        return "cancelled"
    if now < row["start_at"]:
        return "scheduled"
    if row["compte_rendu_uid"]:
        return "completed"
    end = row["end_at"] or row["start_at"] + MAX_SITTING_DURATION
    return "completed" if now > end else "ongoing"


class SqlAgendaProjection(AgendaProjection):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def project_all(self, legislature: int) -> SyncReport:
        report = SyncReport(entity="agenda-projection")
        now = datetime.now(tz=UTC)

        async with self._engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        sa.select(raw.agenda_item)
                        .where(raw.agenda_item.c.legislature == legislature)
                        # Confirmed sittings first: they get the clean slug, a
                        # cancelled twin the same day gets its uid appended.
                        .order_by(
                            (raw.agenda_item.c.state == CANCELLED_STATE).asc(),
                            raw.agenda_item.c.start_at,
                        )
                    )
                )
                .mappings()
                .all()
            )

        for sitting in rows:
            report.processed += 1
            row = debate_row_from_agenda(dict(sitting), calendar_status(sitting, now))
            async with transaction(self._engine) as connection:
                row["slug"] = await unique_slug(
                    connection, pub.debate, row["slug"], row["external_id"]
                )
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

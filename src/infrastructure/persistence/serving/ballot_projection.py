"""
raw -> public projection for scrutins.

Links, in order of confidence:
  sitting    raw.ballot.sitting_uid = public.debate.external_id (always present)
  law        raw.ballot.dossier_uid when the source gives it, else the only
             dossier on the sitting's agenda, else the agenda dossier whose
             title is quoted in the scrutin's title
  reading    the law's stage whose sitting_refs contain the sitting
  amendment  the séance amendment with the number quoted in the title, on a
             text of that reading
Lookups are loaded once; ~1.3 M deputy votes go in by pages.
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from src.domain.entities.ballot import Ballot
from src.domain.ports.projections.ballot_projection import BallotProjection
from src.domain.shared.results import SyncReport
from src.infrastructure.persistence.engine import transaction
from src.infrastructure.persistence.raw import tables as raw
from src.infrastructure.persistence.serving import tables as pub
from src.infrastructure.persistence.serving.mappers.ballot_mapper import (
    ballot_row,
    deputy_vote_row,
)
from src.infrastructure.persistence.serving.mappers.law_mapper import READINGS
from src.infrastructure.persistence.serving.slug import slugify


class _Lookups:
    """Everything a ballot needs to find its public ids, loaded once per run."""

    def __init__(self) -> None:
        self.debates: dict[str, int] = {}  # agenda uid -> public.debate.id
        self.laws: dict[str, int] = {}  # dossier uid -> public.law.id
        self.law_titles: dict[str, str] = {}  # dossier uid -> slugified title
        self.deputies: dict[str, int] = {}
        self.groups: dict[str, int] = {}
        self.agenda_dossiers: dict[str, set[str]] = {}  # agenda uid -> dossier uids
        self.readings: dict[tuple[str, str], tuple[int, set[str]]] = {}
        # (dossier uid, sitting uid) -> (law_reading id, texte uids of that reading)
        self.amendments: dict[tuple[str, str], int] = {}  # (texte uid, number) -> public id
        self.amendments_by_bare: dict[tuple[str, str], list[tuple[int, object]]] = {}

    async def load(self, connection: AsyncConnection) -> None:
        self.debates = await _map(connection, pub.debate.c.external_id, pub.debate.c.id)
        self.laws = await _map(connection, pub.law.c.external_id, pub.law.c.id)
        self.law_titles = {
            uid: slugify(title)
            for uid, title in (
                await connection.execute(sa.select(raw.law.c.dossier_uid, raw.law.c.title))
            ).all()
        }
        self.deputies = await _map(connection, pub.deputy.c.external_id, pub.deputy.c.id)
        self.groups = await _map(
            connection, pub.political_group.c.external_id, pub.political_group.c.id
        )
        for agenda_uid, refs in (
            await connection.execute(
                sa.select(raw.agenda_point.c.agenda_uid, raw.agenda_point.c.dossier_refs)
            )
        ).all():
            self.agenda_dossiers.setdefault(agenda_uid, set()).update(refs)
        await self._load_readings(connection)
        rows = (
            await connection.execute(
                sa.select(
                    raw.amendment.c.texte_uid,
                    raw.amendment.c.number,
                    raw.amendment.c.sorted_at,
                    pub.amendment.c.id,
                )
                .select_from(raw.amendment)
                .join(pub.amendment, pub.amendment.c.external_id == raw.amendment.c.uid)
                .where(raw.amendment.c.examined_by == "AN")
            )
        ).all()
        for texte, number, sorted_at, amendment_id in rows:
            self.amendments[(texte, number)] = amendment_id
            # Budget bills number "I-1762" / "II-1762" while the scrutin says "1762":
            # keep both under the bare number, the decision date tells them apart.
            bare = number.rsplit("-", 1)[-1] if number and "-" in number else None
            if bare:
                self.amendments_by_bare.setdefault((texte, bare), []).append(
                    (amendment_id, sorted_at.date() if sorted_at else None)
                )

    async def _load_readings(self, connection: AsyncConnection) -> None:
        reading_ids = {
            (law_id, chamber, number): rid
            for rid, law_id, chamber, number in (
                await connection.execute(
                    sa.select(
                        pub.law_reading.c.id,
                        pub.law_reading.c.law_id,
                        sa.cast(pub.law_reading.c.chamber, sa.Text),
                        pub.law_reading.c.reading_number,
                    )
                )
            ).all()
        }
        stage = raw.law_stage
        rows = (
            await connection.execute(
                sa.select(
                    stage.c.dossier_uid,
                    stage.c.code,
                    stage.c.sitting_refs,
                    stage.c.texte_uid,
                    stage.c.commission_texte_uid,
                )
            )
        ).all()
        for dossier_uid, code, sittings, texte, commission_texte in rows:
            law_id = self.laws.get(dossier_uid)
            if law_id is None or code not in READINGS:
                continue
            rid = reading_ids.get((law_id, *READINGS[code]))
            if rid is None:
                continue
            textes = {t for t in (texte, commission_texte) if t}
            for sitting in sittings:
                self.readings[(dossier_uid, sitting)] = (rid, textes)

    # -- resolution ------------------------------------------------------------

    def law_for(self, ballot: dict) -> str | None:
        if ballot["dossier_uid"] in self.laws:
            return ballot["dossier_uid"]
        candidates = self.agenda_dossiers.get(ballot["sitting_uid"], set()) & self.laws.keys()
        if len(candidates) == 1:
            return next(iter(candidates))
        # Several laws that day: the scrutin's title quotes one of them. Titles
        # are not copied verbatim, so score by the longest opening of the law's
        # title found in the scrutin's title.
        title = slugify(ballot["title"] or "")
        scored = sorted(
            ((_matching_words(self.law_titles.get(d, ""), title), d) for d in candidates),
            reverse=True,
        )
        if not scored or scored[0][0] < MIN_TITLE_WORDS:
            return None
        if len(scored) > 1 and scored[1][0] == scored[0][0]:
            return None
        return scored[0][1]

    def amendment_for(self, ballot: Ballot, textes: set[str]) -> int | None:
        number = ballot.amendment_number
        if not number:
            return None
        for texte in textes:
            found = self.amendments.get((texte, number))
            if found is not None:
                return found
        for texte in textes:
            candidates = self.amendments_by_bare.get((texte, number), [])
            same_day = [a for a, day in candidates if day == ballot.date]
            if len(same_day) == 1:
                return same_day[0]
            if len(candidates) == 1:
                return candidates[0][0]
        return None


MIN_TITLE_WORDS = 4


def _matching_words(law_slug: str, ballot_slug: str) -> int:
    """How many leading words of the law's title appear, in order, in the scrutin's title."""
    words = law_slug.split("-")
    best = 0
    for k in range(1, len(words) + 1):
        if "-".join(words[:k]) not in ballot_slug:
            break
        best = k
    return best


async def _map(connection: AsyncConnection, key, value) -> dict:
    return dict((await connection.execute(sa.select(key, value).where(key.isnot(None)))).all())


class SqlBallotProjection(BallotProjection):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def project_all(self, legislature: int) -> SyncReport:
        report = SyncReport(entity="ballot-projection")
        lookups = _Lookups()
        async with self._engine.connect() as connection:
            await lookups.load(connection)
            ballots = (
                (
                    await connection.execute(
                        sa.select(raw.ballot)
                        .where(raw.ballot.c.legislature == legislature)
                        .order_by(raw.ballot.c.number)
                    )
                )
                .mappings()
                .all()
            )

        for row in ballots:
            report.processed += 1
            debate_id = lookups.debates.get(row["sitting_uid"])
            if debate_id is None:
                report.skipped += 1  # sitting not on the agenda we collected
                continue
            async with transaction(self._engine) as connection:
                created = await self._project_one(connection, dict(row), debate_id, lookups)
            report.created += int(created)
            report.updated += int(not created)
        return report.finish()

    async def _project_one(
        self, connection: AsyncConnection, row: dict, debate_id: int, lookups: _Lookups
    ) -> bool:
        dossier_uid = lookups.law_for(row)
        reading_id, textes = lookups.readings.get((dossier_uid, row["sitting_uid"]), (None, set()))
        ballot = Ballot(**{k: row[k] for k in Ballot.model_fields if k in row})
        public_row = ballot_row(
            row,
            debate_id=debate_id,
            law_id=lookups.laws.get(dossier_uid),
            amendment_id=lookups.amendment_for(ballot, textes),
            reading_id=reading_id,
        )
        statement = (
            insert(pub.ballot)
            .values(**public_row)
            .on_conflict_do_update(index_elements=["external_id"], set_=public_row)
            .returning(pub.ballot.c.id, (sa.column("xmax") == 0).label("created"))
        )
        ballot_id, created = (await connection.execute(statement)).one()

        votes = (
            (
                await connection.execute(
                    sa.select(raw.ballot_vote).where(raw.ballot_vote.c.ballot_uid == row["uid"])
                )
            )
            .mappings()
            .all()
        )
        rows = [
            deputy_vote_row(
                dict(v),
                ballot_id=ballot_id,
                deputy_id=lookups.deputies[v["deputy_uid"]],
                group_id=lookups.groups.get(v["group_uid"]),
            )
            for v in votes
            if v["deputy_uid"] in lookups.deputies
        ]
        if rows:
            statement = insert(pub.deputy_vote).values(rows)
            await connection.execute(
                statement.on_conflict_do_update(
                    index_elements=["ballot_id", "deputy_id"],
                    set_={
                        "political_group_id": statement.excluded.political_group_id,
                        "position": statement.excluded.position,
                        "updated_at": sa.func.now(),
                    },
                )
            )
        return created

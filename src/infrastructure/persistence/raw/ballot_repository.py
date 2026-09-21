"""Scrutin persistence in `raw`. One transaction per scrutin: header, groups, votes."""

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from src.domain.entities.ballot import Ballot
from src.domain.ports.repositories.ballot_repository import BallotRepository
from src.domain.shared.results import SaveOutcome
from src.infrastructure.persistence.engine import transaction
from src.infrastructure.persistence.raw import tables
from src.infrastructure.persistence.raw.deputy_repository import _upsert
from src.infrastructure.persistence.raw.mappers.ballot_mapper import (
    ballot_group_row,
    ballot_row,
    ballot_vote_row,
)


def _bulk_upsert_on(table, rows: list[dict], *, keys: list[str]):
    """Multi-row INSERT ... ON CONFLICT (composite key) DO UPDATE of the other columns."""
    statement = insert(table).values(rows)
    updates = {c: statement.excluded[c] for c in rows[0] if c not in keys}
    return statement.on_conflict_do_update(index_elements=keys, set_=updates)


class SqlRawBallotRepository(BallotRepository):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def save(self, ballot: Ballot, *, run_id: int, s3_key: str | None = None) -> SaveOutcome:
        row = ballot_row(ballot) | {"ingestion_run_id": run_id, "s3_key": s3_key}
        async with transaction(self._engine) as connection:
            ballot_id, created = (
                await connection.execute(_upsert(tables.ballot, row, key="uid"))
            ).one()
            groups = [ballot_group_row(g, ballot_uid=ballot.uid) for g in ballot.groups]
            if groups:
                await connection.execute(
                    _bulk_upsert_on(tables.ballot_group, groups, keys=["ballot_uid", "group_uid"])
                )
            votes = [ballot_vote_row(v, ballot_uid=ballot.uid) for v in ballot.votes]
            if votes:
                await connection.execute(
                    _bulk_upsert_on(tables.ballot_vote, votes, keys=["ballot_uid", "deputy_uid"])
                )
        return SaveOutcome(entity_id=ballot_id, created=created)

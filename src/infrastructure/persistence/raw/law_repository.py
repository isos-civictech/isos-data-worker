"""Dossier persistence in `raw`. One transaction per dossier."""

from sqlalchemy.ext.asyncio import AsyncEngine

from src.domain.entities.law import Law
from src.domain.ports.repositories.law_repository import LawRepository
from src.domain.shared.results import SaveOutcome
from src.infrastructure.persistence.engine import transaction
from src.infrastructure.persistence.raw import tables
from src.infrastructure.persistence.raw.debate_repository import _bulk_upsert
from src.infrastructure.persistence.raw.deputy_repository import _upsert
from src.infrastructure.persistence.raw.mappers.law_mapper import (
    law_row,
    law_stage_row,
    law_texte_row,
)


class SqlRawLawRepository(LawRepository):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def save(self, law: Law, *, run_id: int, s3_key: str | None = None) -> SaveOutcome:
        row = law_row(law) | {"ingestion_run_id": run_id, "s3_key": s3_key}
        async with transaction(self._engine) as connection:
            law_id, created = (
                await connection.execute(_upsert(tables.law, row, key="dossier_uid"))
            ).one()
            stages = [law_stage_row(s, dossier_uid=law.dossier_uid) for s in law.stages]
            if stages:
                await connection.execute(_bulk_upsert(tables.law_stage, stages, key="stage_uid"))
            textes = [law_texte_row(t) for t in law.textes]
            if textes:
                await connection.execute(_bulk_upsert(tables.law_texte, textes, key="uid"))
        return SaveOutcome(entity_id=law_id, created=created)

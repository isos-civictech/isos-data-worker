"""Law text persistence in `raw`. One transaction per text: header and articles."""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from src.domain.entities.law_text import LawText, text_kind
from src.domain.ports.repositories.law_text_repository import LawTextRepository
from src.domain.shared.results import SaveOutcome
from src.infrastructure.persistence.engine import transaction
from src.infrastructure.persistence.raw import tables
from src.infrastructure.persistence.raw.ballot_repository import _bulk_upsert_on
from src.infrastructure.persistence.raw.deputy_repository import _upsert
from src.infrastructure.persistence.raw.mappers.law_text_mapper import (
    law_article_row,
    law_text_row,
)

LAW_TEXT_KINDS = ("PRJL", "PION")


class SqlRawLawTextRepository(LawTextRepository):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def pending_texte_uids(
        self, legislature: int, *, dossier_uid: str | None = None
    ) -> list[str]:
        """Assemblée projets/propositions (B, BTC, BTA) with no raw.law_text row yet."""
        texte, fetched = tables.law_texte, tables.law_text
        query = (
            sa.select(texte.c.uid)
            .select_from(texte.outerjoin(fetched, fetched.c.texte_uid == texte.c.uid))
            .where(
                texte.c.kind.in_(LAW_TEXT_KINDS),
                sa.func.substr(texte.c.uid, 5, 2) == "AN",
                fetched.c.id.is_(None),
            )
            .order_by(texte.c.deposited_at.desc().nulls_last(), texte.c.uid)
        )
        if dossier_uid:
            query = query.where(texte.c.dossier_uid == dossier_uid)
        async with self._engine.connect() as connection:
            uids = (await connection.execute(query)).scalars().all()
        return [u for u in uids if text_kind(u) is not None]

    async def save(
        self, law_text: LawText, *, run_id: int, s3_key: str | None = None
    ) -> SaveOutcome:
        row = law_text_row(law_text) | {"ingestion_run_id": run_id, "s3_key": s3_key}
        async with transaction(self._engine) as connection:
            text_id, created = (
                await connection.execute(_upsert(tables.law_text, row, key="texte_uid"))
            ).one()
            # The website page does not say which dossier: raw.law_texte does.
            if law_text.dossier_uid is None:
                await connection.execute(
                    sa.update(tables.law_text)
                    .where(tables.law_text.c.id == text_id)
                    .values(
                        dossier_uid=sa.select(tables.law_texte.c.dossier_uid)
                        .where(tables.law_texte.c.uid == law_text.texte_uid)
                        .scalar_subquery()
                    )
                )
            articles = [law_article_row(a) for a in law_text.articles]
            if articles:
                await connection.execute(
                    _bulk_upsert_on(tables.law_article, articles, keys=["texte_uid", "position"])
                )
        return SaveOutcome(entity_id=text_id, created=created)

    async def mark_unavailable(self, texte_uid: str, *, run_id: int) -> None:
        row = {
            "texte_uid": texte_uid,
            "legislature": int(texte_uid[9:11]) if texte_uid[9:11].isdigit() else 0,
            "kind": (text_kind(texte_uid) or "").value or None,
            "available": False,
            "ingestion_run_id": run_id,
        }
        async with transaction(self._engine) as connection:
            await connection.execute(
                insert(tables.law_text)
                .values(**row)
                .on_conflict_do_update(index_elements=["texte_uid"], set_={"available": False})
            )

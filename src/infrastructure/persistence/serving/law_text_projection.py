"""
raw -> public projection for law texts.

public.law_text     one row per fetched version, ordered along the navette
public.law_article  one row per article of each version
amendment.law_article_id  the article named by the amendment, in the version it targets
"""

from datetime import date

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from src.domain.ports.projections.law_text_projection import LawTextProjection
from src.domain.shared.results import SyncReport
from src.infrastructure.persistence.engine import transaction
from src.infrastructure.persistence.raw import tables as raw
from src.infrastructure.persistence.serving import tables as pub
from src.infrastructure.persistence.serving.mappers.law_mapper import READINGS

KIND_ORDER = {"deposited": 0, "commission": 1, "adopted": 2}


class SqlLawTextProjection(LawTextProjection):
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def project_all(self, legislature: int) -> SyncReport:
        report = SyncReport(entity="law-text-projection")
        async with self._engine.connect() as connection:
            laws = dict(
                (await connection.execute(sa.select(pub.law.c.external_id, pub.law.c.id))).all()
            )
            readings = await self._readings(connection, laws)
            documents = {
                uid: (number, deposited_at)
                for uid, number, deposited_at in (
                    await connection.execute(
                        sa.select(
                            raw.law_texte.c.uid,
                            raw.law_texte.c.number,
                            raw.law_texte.c.deposited_at,
                        )
                    )
                ).all()
            }
            texts = (
                (
                    await connection.execute(
                        sa.select(raw.law_text)
                        .where(raw.law_text.c.legislature == legislature, raw.law_text.c.available)
                        .order_by(raw.law_text.c.dossier_uid, raw.law_text.c.texte_uid)
                    )
                )
                .mappings()
                .all()
            )

        # Version order inside a dossier: deposit date, then deposited < commission < adopted.
        by_dossier: dict[str, list] = {}
        for t in texts:
            by_dossier.setdefault(t["dossier_uid"], []).append(t)

        for dossier_uid, versions in by_dossier.items():
            law_id = laws.get(dossier_uid)
            if law_id is None:
                report.skipped += len(versions)
                continue
            versions.sort(
                key=lambda t: (
                    documents.get(t["texte_uid"], (None, None))[1] or date.max,
                    KIND_ORDER.get(t["kind"], 9),
                )
            )
            for position, t in enumerate(versions, 1):
                report.processed += 1
                async with transaction(self._engine) as connection:
                    created = await self._project_text(
                        connection,
                        dict(t),
                        law_id=law_id,
                        reading_id=readings.get((dossier_uid, t["texte_uid"])),
                        texte_number=documents.get(t["texte_uid"], (None, None))[0],
                        position=position,
                    )
                report.created += int(created)
                report.updated += int(not created)

        async with transaction(self._engine) as connection:
            await self._link_amendments(connection)
        return report.finish()

    @staticmethod
    async def _readings(connection: AsyncConnection, laws: dict) -> dict:
        """(dossier uid, texte uid) -> law_reading id."""
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
        s = raw.law_stage
        out = {}
        for dossier_uid, code, texte, commission_texte, adopted_texte in (
            await connection.execute(
                sa.select(
                    s.c.dossier_uid,
                    s.c.code,
                    s.c.texte_uid,
                    s.c.commission_texte_uid,
                    s.c.adopted_texte_uid,
                )
            )
        ).all():
            law_id = laws.get(dossier_uid)
            if law_id is None or code not in READINGS:
                continue
            rid = reading_ids.get((law_id, *READINGS[code]))
            for uid in (texte, commission_texte, adopted_texte):
                if uid:
                    out[(dossier_uid, uid)] = rid
        return out

    @staticmethod
    async def _project_text(
        connection: AsyncConnection,
        t: dict,
        *,
        law_id: int,
        reading_id: int | None,
        texte_number: int | None,
        position: int,
    ) -> bool:
        row = {
            "law_id": law_id,
            "law_reading_id": reading_id,
            "kind": t["kind"],
            "texte_number": texte_number,
            "position": position,
            "source_url": t["source_url"],
            "external_id": t["texte_uid"],
        }
        text_id, created = (
            await connection.execute(
                insert(pub.law_text)
                .values(**row)
                .on_conflict_do_update(
                    index_elements=["external_id"], set_=row | {"updated_at": sa.func.now()}
                )
                .returning(pub.law_text.c.id, (sa.column("xmax") == 0).label("created"))
            )
        ).one()
        articles = (
            (
                await connection.execute(
                    sa.select(raw.law_article).where(raw.law_article.c.texte_uid == t["texte_uid"])
                )
            )
            .mappings()
            .all()
        )
        if articles:
            rows = [
                {
                    "law_text_id": text_id,
                    "article_ref": a["article_ref"][:255],
                    "position": a["position"],
                    "section": (a["section"] or "")[:255] or None,
                    "content": a["content"],
                    "mention": a["mention"],
                    "is_new": a["is_new"],
                }
                for a in articles
            ]
            statement = insert(pub.law_article).values(rows)
            await connection.execute(
                statement.on_conflict_do_update(
                    index_elements=["law_text_id", "position"],
                    set_={c: statement.excluded[c] for c in rows[0] if c != "law_text_id"},
                )
            )
        return created

    @staticmethod
    async def _link_amendments(connection: AsyncConnection) -> None:
        """amendment.law_article_id from (raw texte uid, article_ref), in one UPDATE."""
        a, ra, lt, la = pub.amendment, raw.amendment, pub.law_text, pub.law_article
        target = (
            sa.select(la.c.id)
            .select_from(la.join(lt, lt.c.id == la.c.law_text_id))
            .where(lt.c.external_id == ra.c.texte_uid, la.c.article_ref == ra.c.division_title)
            .order_by(la.c.position)
            .limit(1)
            .scalar_subquery()
        )
        await connection.execute(
            sa.update(a)
            .where(a.c.external_id == ra.c.uid, ra.c.division_type == "ARTICLE")
            .values(law_article_id=target)
        )

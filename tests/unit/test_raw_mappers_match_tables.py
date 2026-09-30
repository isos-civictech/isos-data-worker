"""Every raw mapper must produce exactly the columns its table has (minus bookkeeping)."""

from datetime import date

from src.domain.entities.agenda_item import AgendaItem
from src.domain.entities.amendment import Amendment
from src.domain.entities.ballot import Ballot
from src.domain.entities.deputy import Deputy
from src.domain.entities.law import Law
from src.domain.entities.law_text import LawText
from src.infrastructure.persistence.raw import tables
from src.infrastructure.persistence.raw.mappers import (
    agenda_mapper,
    amendment_mapper,
    ballot_mapper,
    deputy_mapper,
    law_mapper,
    law_text_mapper,
)

BOOKKEEPING = {"id", "created_at", "updated_at", "ingestion_run_id", "s3_key"}


def _columns(table) -> set[str]:
    return {c.name for c in table.c} - BOOKKEEPING


def test_root_mappers_cover_their_tables():
    cases = [
        (
            tables.deputy,
            deputy_mapper.deputy_row(
                Deputy(uid="PA1", first_name="A", last_name="B"), legislature=17
            ),
        ),
        (
            tables.law,
            law_mapper.law_row(Law(dossier_uid="D", legislature=17, title="t", procedure_code="2")),
        ),
        (
            tables.agenda_item,
            agenda_mapper.agenda_item_row(
                AgendaItem(uid="RU", legislature=17, start_at=date(2025, 1, 1))
            ),
        ),
        (
            tables.amendment,
            amendment_mapper.amendment_row(
                Amendment(uid="AM", legislature=17, texte_uid="T", author_type="Député")
            ),
        ),
        (
            tables.ballot,
            ballot_mapper.ballot_row(
                Ballot(
                    uid="V",
                    legislature=17,
                    number=1,
                    agenda_uid="RU",
                    date=date(2025, 1, 1),
                    kind="SPO",
                )  # fmt: skip
            ),
        ),
        (
            tables.law_text,
            law_text_mapper.law_text_row(LawText(texte_uid="PRJLANR5L17B1", legislature=17)),
        ),
    ]
    for table, row in cases:
        unknown = set(row) - {c.name for c in table.c}
        assert not unknown, f"{table.name}: mapper writes columns the table lacks: {unknown}"
        missing = _columns(table) - set(row) - RESOLVED.get(table.name, set())
        assert not missing, f"{table.name}: columns the mapper never fills: {missing}"


# Filled later by the projection, not by the mapper.
RESOLVED = {"ballot": {"resolved_dossier_uid", "resolved_amendment_uid"}}

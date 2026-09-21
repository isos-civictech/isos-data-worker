"""
`raw` schema — facts as published by the Assemblée nationale. Source of truth
for the worker's Alembic.

Conventions: BIGSERIAL id + AN uid as UNIQUE natural key; nothing is ever
deleted. On every root table:
    created_at         first insert
    updated_at         last time the content actually changed
    ingestion_run_id   the run that last touched the row — join ingestion_run
                       for its date and its raw file (s3_key)
    s3_key             the archive this row was parsed from
Column names follow the source vocabulary; translation is the projection's job.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

SCHEMA = "raw"

# Every constraint gets a deterministic name, or Alembic cannot drop it later.
metadata = sa.MetaData(
    schema=SCHEMA,
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_N_name)s",
        "uq": "uq_%(table_name)s_%(column_0_N_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s",
        "pk": "pk_%(table_name)s",
    },
)


def _seen_columns() -> list[sa.Column]:
    """Ingestion tracking, identical on every root table."""
    return [
        sa.Column("s3_key", sa.Text),
        sa.Column(
            "ingestion_run_id",
            sa.BigInteger,
            sa.ForeignKey("raw.ingestion_run.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    ]


# ── Audit ─────────────────────────────────────────────────────────────────────

ingestion_run = sa.Table(
    "ingestion_run",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("entity_type", sa.String(50), nullable=False),
    sa.Column("status", sa.String(20), nullable=False, server_default="running"),
    sa.Column("source_url", sa.Text),
    sa.Column("s3_key", sa.Text),
    sa.Column("processed", sa.Integer, nullable=False, server_default="0"),
    sa.Column("created", sa.Integer, nullable=False, server_default="0"),
    sa.Column("updated", sa.Integer, nullable=False, server_default="0"),
    sa.Column("skipped", sa.Integer, nullable=False, server_default="0"),
    sa.Column("failed", sa.Integer, nullable=False, server_default="0"),
    sa.Column(
        "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    ),
    sa.Column("finished_at", sa.DateTime(timezone=True)),
)


# ── Referential ───────────────────────────────────────────────────────────────

political_group = sa.Table(
    "political_group",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("uid", sa.String(100), nullable=False, unique=True),  # "PO845401"
    sa.Column("legislature", sa.Integer),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("short_name", sa.String(50)),
    *_seen_columns(),
)

deputy = sa.Table(
    "deputy",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("uid", sa.String(100), nullable=False, unique=True),  # "PA1592"
    sa.Column("legislature", sa.Integer, nullable=False),
    sa.Column("first_name", sa.Text, nullable=False),
    sa.Column("last_name", sa.Text, nullable=False),
    sa.Column("birth_date", sa.Date),
    # No column for these in the display schema; raw keeps them anyway.
    sa.Column("gender", sa.String(1)),
    sa.Column("profession", sa.Text),
    sa.Column("photo_url", sa.Text),
    *_seen_columns(),
    sa.Index("ix_raw_deputy_legislature", "legislature"),
)

mandate = sa.Table(
    "mandate",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("uid", sa.String(100), nullable=False, unique=True),
    sa.Column(
        "deputy_uid",
        sa.String(100),
        sa.ForeignKey("raw.deputy.uid", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("legislature", sa.Integer, nullable=False),
    sa.Column("mandate_start", sa.Date),
    sa.Column("mandate_end", sa.Date),
    # From the GP mandat (see mandate.py).
    sa.Column("group_uid", sa.String(100)),  # name and acronym: join political_group
    sa.Column("constituency_number", sa.Integer),
    sa.Column("department_name", sa.Text),
    sa.Column("department_number", sa.String(10)),
    sa.Column("seat_number", sa.Integer),
    sa.Index("ix_raw_mandate_deputy", "deputy_uid"),
)


# ── Laws ──────────────────────────────────────────────────────────────────────

law = sa.Table(
    "law",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("dossier_uid", sa.String(100), nullable=False, unique=True),  # "DLR5L17N53940"
    sa.Column("legislature", sa.Integer, nullable=False),
    # Never truncated here.
    sa.Column("title", sa.Text, nullable=False),
    sa.Column("senate_url", sa.Text),
    # procedureParlementaire: "1" projet, "2" proposition, "19" rapport, "8" résolution…
    sa.Column("procedure_code", sa.String(10), nullable=False),
    sa.Column("procedure_label", sa.Text),
    # Deputies (PA…) who signed the initiative; empty for government texts.
    sa.Column("initiator_uids", pg.ARRAY(sa.Text), nullable=False, server_default="{}"),
    sa.Column("withdrawn", sa.Boolean, nullable=False, server_default=sa.false()),
    *_seen_columns(),
)

# One row per top-level acte: a reading in a chamber, the CMP, the CC, the
# promulgation. The nested acts are summarised into dates and a decision.
law_stage = sa.Table(
    "law_stage",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("stage_uid", sa.String(100), nullable=False, unique=True),  # "DLR5L17N53940-AN1"
    sa.Column(
        "dossier_uid",
        sa.String(100),
        sa.ForeignKey("raw.law.dossier_uid", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("code", sa.String(50), nullable=False),  # "AN1", "SN1", "CMP", "PROM"…
    sa.Column("label", sa.Text, nullable=False),
    sa.Column("organe_ref", sa.String(100)),
    sa.Column("position", sa.Integer, nullable=False, server_default="0"),
    sa.Column("started_at", sa.Date),
    sa.Column("examined_at", sa.Date),
    sa.Column("concluded_at", sa.Date),
    sa.Column("decision", sa.Text),  # "adopté", "rejeté", "modifié"
    sa.Column("decision_code", sa.String(20)),  # "TSORTF01", "TSORTF07"…
    sa.Column("texte_uid", sa.String(100)),  # text deposited for this reading
    # Agenda uids of the public sittings (RUAN… / RUSN…): the law -> debate join.
    sa.Column("sitting_refs", pg.ARRAY(sa.Text), nullable=False, server_default="{}"),
    sa.Index("ix_raw_law_stage_dossier", "dossier_uid"),
)

# ── Sittings ──────────────────────────────────────────────────────────────────

debate = sa.Table(
    "debate",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("uid", sa.String(100), nullable=False, unique=True),
    sa.Column("legislature", sa.Integer, nullable=False),
    # Nullable here; the projection provides a fallback.
    sa.Column("session_number", sa.Integer),
    sa.Column("session_type", sa.String(50)),
    sa.Column("date", sa.DateTime(timezone=True), nullable=False),
    sa.Column("title", sa.Text),
    *_seen_columns(),
)

# Agenda item ("point d'ordre du jour"): the per-topic level. Points nest.
debate_point = sa.Table(
    "debate_point",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column(
        "debate_uid",
        sa.String(100),
        sa.ForeignKey("raw.debate.uid", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("point_uid", sa.String(100), nullable=False, unique=True),  # id_syceron
    sa.Column("parent_uid", sa.String(100)),
    sa.Column("title", sa.Text),
    sa.Column("kind", sa.String(50)),  # code_grammaire: QG_1_1, DISC_ARTICLES_3_1, …
    sa.Column("position", sa.Integer, nullable=False, server_default="0"),
    # Text NUMBERS (bibard), not uids: the join to a law goes through the number.
    sa.Column("texte_refs", pg.ARRAY(sa.Text), nullable=False, server_default="{}"),
    sa.Index("ix_raw_debate_point_debate", "debate_uid"),
)

intervention = sa.Table(
    "intervention",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column(
        "debate_point_id",
        sa.BigInteger,
        sa.ForeignKey("raw.debate_point.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("uid", sa.String(100), nullable=False, unique=True),  # id_syceron
    sa.Column("deputy_uid", sa.String(100)),
    sa.Column("speaker_name", sa.Text),
    sa.Column("speaker_type", sa.String(50)),
    sa.Column("content", sa.Text),
    sa.Column("order_in_debate", sa.Integer),
    sa.Index("ix_raw_intervention_point", "debate_point_id"),
)


# ── Agenda ────────────────────────────────────────────────────────────────────

# One public sitting as scheduled. Exists before the sitting happens; once held,
# compte_rendu_uid points at raw.debate.uid.
agenda_item = sa.Table(
    "agenda_item",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("uid", sa.String(100), nullable=False, unique=True),  # "RUANR5L17S2024IDS28538"
    sa.Column("legislature", sa.Integer, nullable=False),
    sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("end_at", sa.DateTime(timezone=True)),
    sa.Column("location", sa.Text),
    sa.Column("state", sa.String(50)),  # "Confirmé" | "Supprimé"
    sa.Column("compte_rendu_uid", sa.String(100)),  # -> raw.debate.uid, once held
    sa.Column("session_rank", sa.String(20)),  # "Première" | "Deuxième" | "Unique"
    sa.Column("session_number", sa.Integer),
    *_seen_columns(),
    sa.Index("ix_raw_agenda_item_start", "start_at"),
    sa.Index("ix_raw_agenda_item_cr", "compte_rendu_uid"),
)

agenda_point = sa.Table(
    "agenda_point",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column(
        "agenda_uid",
        sa.String(100),
        sa.ForeignKey("raw.agenda_item.uid", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("point_uid", sa.String(100), nullable=False, unique=True),
    sa.Column("title", sa.Text),
    sa.Column("kind", sa.String(100)),  # typePointODJ
    sa.Column("state", sa.String(50)),
    sa.Column("position", sa.Integer, nullable=False, server_default="0"),
    # Law dossier uids ("DLR5L17N53818"): the clean debate -> law join.
    sa.Column("dossier_refs", pg.ARRAY(sa.Text), nullable=False, server_default="{}"),
    sa.Index("ix_raw_agenda_point_agenda", "agenda_uid"),
)

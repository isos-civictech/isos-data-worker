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
    sa.Column("dossier_uid", sa.String(100), nullable=False, unique=True),  # "DLR5L17N47390"
    # Join key for debates, which reference texte uids.
    sa.Column("texte_uid", sa.String(100)),
    sa.Column("legislature", sa.Integer, nullable=False),
    # Never truncated here.
    sa.Column("title", sa.Text, nullable=False),
    sa.Column("law_type", sa.String(50)),
    sa.Column("initiateur_uid", sa.String(100)),
    sa.Column("closure_status", sa.String(50)),
    *_seen_columns(),
    sa.Index("ix_raw_law_texte_uid", "texte_uid"),
)

law_stage = sa.Table(
    "law_stage",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column(
        "dossier_uid",
        sa.String(100),
        sa.ForeignKey("raw.law.dossier_uid", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("code", sa.String(50), nullable=False),
    sa.Column("label", sa.Text, nullable=False),
    sa.Column("updated_stage_date", sa.Date),
    sa.Column("position", sa.Integer, nullable=False, server_default="0"),
    sa.UniqueConstraint("dossier_uid", "code", "position", name="uq_raw_law_stage"),
)

# Versioned: a changed text inserts a new row, the old one gets is_current=false.
law_article = sa.Table(
    "law_article",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column("texte_uid", sa.String(100), nullable=False),
    sa.Column("article_ref", sa.String(100), nullable=False),
    sa.Column("article_number", sa.Integer),
    sa.Column("legislature", sa.Integer, nullable=False),
    sa.Column("content", sa.Text, nullable=False),
    sa.Column("content_checksum", sa.String(64), nullable=False),
    sa.Column("version_number", sa.Integer, nullable=False, server_default="1"),
    sa.Column("is_current", sa.Boolean, nullable=False, server_default=sa.true()),
    sa.Column("superseded_at", sa.DateTime(timezone=True)),
    sa.Column("amendment_uid", sa.String(100)),
    sa.Column("s3_key", sa.Text),
    sa.Column(
        "scraped_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    ),
    # One current version per article.
    sa.Index(
        "uq_raw_law_article_current",
        "texte_uid",
        "article_ref",
        unique=True,
        postgresql_where=sa.text("is_current"),
    ),
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

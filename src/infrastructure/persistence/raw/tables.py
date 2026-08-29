"""
The `raw` schema — the facts, as the Assemblée nationale publishes them.

THIS FILE IS THE SOURCE OF TRUTH. The worker owns this schema
(`CREATE SCHEMA raw AUTHORIZATION isos_ingestion`), and its Alembic autogenerate
compares the database against this metadata. Change a column here, generate a
revision, done — no coordination with another repository.

Three conventions apply to every table:

  1. `id BIGSERIAL` primary key, AN uid as a UNIQUE natural key. The surrogate
     key is what lets a future view in `public` expose integer ids to the front
     without a join.
  2. `first_seen_at` / `last_seen_at` / `checksum` on every root table. The
     checksum answers "did the AN republish the same thing?" without reading the
     content; `last_seen_at` answers "is this entity still in the export?"
     without ever deleting a row.
  3. NOTHING IS EVER DELETED. No DELETE, no TRUNCATE, and the role has no DELETE
     grant. An entity that vanishes from the export keeps its row, with a
     `last_seen_at` that stops moving.

Field names deliberately mirror the source vocabulary (`texte_uid`,
`dossier_uid`, `sort`), even where the display schema uses different words.
Translation is the projection's job, not the collector's.
"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

SCHEMA = "raw"

metadata = sa.MetaData(schema=SCHEMA)


def _seen_columns() -> list[sa.Column]:
    """Ingestion tracking, identical on every root table."""
    return [
        sa.Column("checksum", sa.String(64)),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at",
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

# One row per entity actually ingested. An unchanged entity writes NOTHING here:
# a log full of "nothing changed" no longer answers the question it exists for.
ingestion_log = sa.Table(
    "ingestion_log",
    metadata,
    sa.Column("id", sa.BigInteger, primary_key=True),
    sa.Column(
        "run_id",
        sa.BigInteger,
        sa.ForeignKey("raw.ingestion_run.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("entity_type", sa.String(50), nullable=False),
    sa.Column("entity_uid", sa.String(100), nullable=False),
    sa.Column("source_url", sa.Text),
    sa.Column("s3_key", sa.Text),
    sa.Column("checksum", sa.String(64)),
    sa.Column(
        "fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
    ),
    sa.Index("ix_raw_ingestion_log_entity", "entity_type", "entity_uid"),
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
    # Kept even though the display schema has no column for them: raw records
    # what was published, not what is currently shown.
    sa.Column("gender", sa.String(1)),
    sa.Column("profession", sa.Text),
    sa.Column("photo_url", sa.Text),
    sa.Column("s3_key", sa.Text),
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
    # From the GP mandat, not the ASSEMBLEE one — see mandate.py's docstring.
    sa.Column("group_uid", sa.String(100)),
    sa.Column("group_acronym", sa.String(50)),
    sa.Column("group_name", sa.Text),
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
    # The join key debates need: a sitting references TEXTE uids, not dossier ones.
    sa.Column("texte_uid", sa.String(100)),
    sa.Column("legislature", sa.Integer, nullable=False),
    # Full title, never truncated. Shortening to 255 is the projection's problem.
    sa.Column("title", sa.Text, nullable=False),
    sa.Column("law_type", sa.String(50)),
    sa.Column("initiateur_uid", sa.String(100)),
    sa.Column("closure_status", sa.String(50)),
    sa.Column("s3_key", sa.Text),
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

# The one versioned table. A text that changes never overwrites the previous
# version: the old row stays, marked is_current = false. See law_repository.
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
    # PARTIAL unique index: only one current version per article. It is also
    # what forces the old row to be flipped to false BEFORE inserting the new one.
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
    # Nullable here although the display schema requires it: raw stays faithful,
    # the projection is responsible for finding a fallback.
    sa.Column("session_number", sa.Integer),
    sa.Column("session_type", sa.String(50)),
    sa.Column("date", sa.DateTime(timezone=True), nullable=False),
    sa.Column("s3_key", sa.Text),
    *_seen_columns(),
)

# The "subject" level — this is what makes a per-topic summary possible, and it
# had no table anywhere before the raw schema existed.
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
    sa.Column("point_uid", sa.String(100)),
    sa.Column("title", sa.Text),
    sa.Column("position", sa.Integer, nullable=False, server_default="0"),
    # A Postgres array, because that is what the source holds. Flattening is the
    # projection's job.
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
    sa.Column("uid", sa.String(100)),
    sa.Column("deputy_uid", sa.String(100)),
    sa.Column("speaker_name", sa.Text),
    sa.Column("speaker_type", sa.String(50)),
    sa.Column("content", sa.Text),
    sa.Column("order_in_debate", sa.Integer),
    sa.Index("ix_raw_intervention_point", "debate_point_id"),
)

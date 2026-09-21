"""
PARTIAL mirror of isos-api's `public` schema — only the columns the worker
reads or writes. Source of truth: isos-api, alembic head 9f3ac1e5d47b.

Never passed to Alembic, never create_all()'d: this repo does not own it.
Columns deliberately absent (editorial or computed by the API):
deputy.picture is ours (photo), but participation_count / presence_rate are not.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

metadata = sa.MetaData(schema="public")

legislature = sa.Table(
    "legislature",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("number", sa.Integer, nullable=False, unique=True),
    sa.Column("started_at", sa.Date, nullable=False),
    sa.Column("ended_at", sa.Date),
)

political_group = sa.Table(
    "political_group",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("legislature_id", sa.Integer, nullable=False),
    sa.Column("name", sa.String(255), nullable=False),
    sa.Column("short_name", sa.String(50)),
    sa.Column("external_id", sa.String(100)),
)

deputy = sa.Table(
    "deputy",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("first_name", sa.String(255), nullable=False),
    sa.Column("last_name", sa.String(255), nullable=False),
    sa.Column("slug", sa.Text, nullable=False),
    sa.Column("picture", sa.Text),
    sa.Column("birth_date", sa.Date),
    sa.Column("constituency", sa.String(255)),
    sa.Column("department", sa.String(255)),
    sa.Column("external_id", sa.String(100)),
    sa.Column("source_url", sa.Text),
    sa.Column("updated_at", sa.DateTime(timezone=True)),  # no trigger: set by hand
)

deputy_mandate = sa.Table(
    "deputy_mandate",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("deputy_id", sa.Integer, nullable=False),
    sa.Column("legislature_id", sa.Integer, nullable=False),
    sa.Column("political_group_id", sa.Integer, nullable=False),
    sa.Column("started_at", sa.Date, nullable=False),
    sa.Column("ended_at", sa.Date),
)

debate = sa.Table(
    "debate",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("session_number", sa.Integer, nullable=False),
    sa.Column("title", sa.Text),
    sa.Column("session_date", sa.DateTime(timezone=True), nullable=False),
    # Postgres enum: declared as such, or asyncpg sends text and Postgres refuses.
    sa.Column("calendar_status", pg.ENUM(name="event_status", create_type=False), nullable=False),
    sa.Column("slug", sa.String(255), nullable=False),
    sa.Column("source_url", sa.Text),
    sa.Column("external_id", sa.String(100)),
    sa.Column("updated_at", sa.DateTime(timezone=True)),
)

law = sa.Table(
    "law",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("legislature_id", sa.Integer, nullable=False),
    sa.Column("type", pg.ENUM(name="law_type", create_type=False), nullable=False),
    sa.Column("texte_number", sa.Integer),  # the "n° 2681" of the deposited text
    sa.Column("name", sa.String(255), nullable=False),  # short, truncated
    sa.Column("title", sa.Text),  # full dossier title
    sa.Column("slug", sa.Text, nullable=False),
    sa.Column("status", pg.ENUM(name="law_status", create_type=False), nullable=False),
    sa.Column("deposited_at", sa.DateTime(timezone=True)),
    sa.Column("source_url", sa.Text),
    sa.Column("external_id", sa.String(100)),
    sa.Column("updated_at", sa.DateTime(timezone=True)),
)

law_reading = sa.Table(
    "law_reading",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("law_id", sa.Integer, nullable=False),
    sa.Column("chamber", pg.ENUM(name="reading_chamber", create_type=False), nullable=False),
    sa.Column("reading_number", sa.Integer, nullable=False),
    sa.Column("status", pg.ENUM(name="law_status", create_type=False), nullable=False),
    sa.Column("calendar_status", pg.ENUM(name="event_status", create_type=False), nullable=False),
    sa.Column("started_at", sa.Date),
    sa.Column("concluded_at", sa.Date),
)

debate_law = sa.Table(
    "debate_law",
    metadata,
    sa.Column("debate_id", sa.Integer, primary_key=True),
    sa.Column("law_id", sa.Integer, primary_key=True),
    sa.Column("law_reading_id", sa.Integer),
)

amendment = sa.Table(
    "amendment",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("law_id", sa.Integer, nullable=False),
    sa.Column("law_reading_id", sa.Integer),
    sa.Column("number", sa.String(20)),
    sa.Column("examined_by", sa.String(50)),
    sa.Column("article_ref", sa.String(255)),
    sa.Column(
        "author_type", pg.ENUM(name="amendment_author_type", create_type=False), nullable=False
    ),
    sa.Column("deputy_id", sa.Integer),
    sa.Column("political_group_id", sa.Integer),
    sa.Column("content", sa.Text),
    sa.Column("summary", sa.Text),
    sa.Column("status", pg.ENUM(name="amendment_status", create_type=False), nullable=False),
    sa.Column("deposited_at", sa.Date),
    sa.Column("external_id", sa.String(100)),
    sa.Column("updated_at", sa.DateTime(timezone=True)),
)

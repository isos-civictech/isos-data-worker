"""
PARTIAL mirror of isos-api's `public` schema — only the columns the worker
reads or writes. Source of truth: isos-api, alembic head 9f3ac1e5d47b.

Never passed to Alembic, never create_all()'d: this repo does not own it.
Columns deliberately absent (editorial or computed by the API):
deputy.picture is ours (photo), but participation_count / presence_rate are not.
"""

import sqlalchemy as sa

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

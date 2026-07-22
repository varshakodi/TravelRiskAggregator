"""Alembic environment — the bridge between Alembic and this app.

It answers three questions every time you run an alembic command:
  1. WHERE is the database?   -> DATABASE_URL from backend/.env
  2. WHAT should it look like? -> models.py's Base.metadata (autogenerate
     diffs the real DB against this to draft migrations)
  3. Any special types?        -> GeoAlchemy2 helpers so PostGIS geometry
     columns, spatial indexes, and the spatial_ref_sys system table are
     handled correctly instead of confusing the autogenerate diff.
"""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from geoalchemy2 import alembic_helpers
from sqlalchemy import create_engine, pool

# Make `import models` work: add backend/ (this file's grandparent) to the path.
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

load_dotenv(dotenv_path=BACKEND_DIR / ".env")

from models import Base  # noqa: E402  (import after sys.path fix)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The schema autogenerate compares the live database against.
target_metadata = Base.metadata


def _database_url() -> str:
    try:
        return os.environ["DATABASE_URL"]
    except KeyError:
        raise RuntimeError(
            "DATABASE_URL is not set. Create backend/.env (see .env.example)."
        )


def run_migrations_offline() -> None:
    """Emit the SQL as text without connecting (alembic upgrade head --sql)."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=alembic_helpers.include_object,
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the database and apply migrations directly."""
    connectable = create_engine(_database_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=alembic_helpers.include_object,
            process_revision_directives=alembic_helpers.writer,
            render_item=alembic_helpers.render_item,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

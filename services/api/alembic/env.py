# services/api/alembic/env.py
from logging.config import fileConfig
from pathlib import Path
import os
import sys

from alembic import context
from sqlalchemy import engine_from_config, pool

# ------------------------------------------------------------
# Alembic config & logging
# ------------------------------------------------------------
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ------------------------------------------------------------
# Make sure we can import from services/api/
# (env.py is in services/api/alembic/, so go one level up)
# ------------------------------------------------------------
API_DIR = Path(__file__).resolve().parents[1]  # .../services/api
if str(API_DIR) not in sys.path:
    sys.path.append(str(API_DIR))

# ------------------------------------------------------------
# Import your SQLAlchemy Base metadata (for --autogenerate)
# ------------------------------------------------------------
from db import Base  # services/api/db.py
target_metadata = Base.metadata

# ------------------------------------------------------------
# Prefer env var for DB URL; fallback to alembic.ini
# If app uses async URL, swap to sync driver for Alembic.
# ------------------------------------------------------------
db_url = os.getenv("DATABASE_URL")
if db_url:
    if "+asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "+psycopg")
    config.set_main_option("sqlalchemy.url", db_url)

# ------------------------------------------------------------
# Ignore TimescaleDB internals during autogenerate
# ------------------------------------------------------------
def include_object(object_, name, type_, reflected, compare_to):
    schema = getattr(object_, "schema", None)
    if schema and (
        schema.startswith("_timescaledb")
        or schema == "timescaledb_catalog"
        or schema == "timescaledb_information"
    ):
        return False
    return True

# Avoid empty autogenerate revisions
def process_revision_directives(context_, revision, directives):
    if getattr(context_.config.cmd_opts, "autogenerate", False):
        script = directives[0]
        if script.upgrade_ops.is_empty():
            directives[:] = []

# ------------------------------------------------------------
# Offline / Online runners
# ------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode'."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
        process_revision_directives=process_revision_directives,
        # version_table_schema="public",  # uncomment if you store alembic_version outside default
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode'."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_object=include_object,
            process_revision_directives=process_revision_directives,
            # version_table_schema="public",
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

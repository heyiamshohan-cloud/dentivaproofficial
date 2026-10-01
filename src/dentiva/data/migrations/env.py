"""Alembic environment for Dentiva Pro.

Migrations run through :func:`dentiva.data.engine.upgrade`, which builds the
configuration programmatically; this module only needs to resolve the database
URL and expose the target metadata.
"""

from __future__ import annotations

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import Engine, create_engine

from dentiva.data.base import Base
from dentiva.data.engine import database_url

config = context.config

if config.config_file_name is not None and Path(config.config_file_name).exists():
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    default_path = os.environ.get("DENTIVA_DATABASE")
    if default_path:
        return database_url(default_path)
    raise RuntimeError("No database URL configured for Alembic")


def _engine() -> Engine:
    return create_engine(_database_url(), future=True)


def run_migrations_offline() -> None:
    """Emit SQL to the script output (used for review and support)."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations inside a transaction against a live connection."""
    engine = _engine()
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

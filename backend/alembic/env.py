from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.core.db import Base
import app.db.models  # noqa: F401  # ensure all models are imported/registered on Base

# Alembic Config object (reads alembic.ini)
config = context.config

# Logging config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate
target_metadata = Base.metadata


def _normalize_url(url: str) -> str:
    """
    Make Railway/Heroku-style URLs and SQLAlchemy driver selection consistent.

    - Railway may provide postgres://...; SQLAlchemy expects postgresql://...
    - Your runtime traceback shows psycopg, so enforce postgresql+psycopg://...
    """
    url = (url or "").strip()

    # Normalize scheme
    url = url.replace("postgres://", "postgresql://")

    # Force psycopg driver if using postgres
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)

    return url


def get_url() -> str:
    """
    Source of truth for Alembic DB URL.
    Prefer settings.database_url (which should read from env in production).
    """
    url = _normalize_url(settings.database_url)

    if not url:
        raise RuntimeError(
            "Database URL is empty. Check your settings.database_url and env vars (e.g. DATABASE_URL)."
        )

    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Build a fresh engine from Alembic config + our URL
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

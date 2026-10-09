"""Verify cart-index repair DDL and preservation of existing cart/order data."""

import importlib.util
from io import StringIO
from pathlib import Path
from types import ModuleType

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError


def load_migration() -> ModuleType:
    """Load the standalone Alembic revision without importing the backend app.

    Params:
        None. Resolves the migration relative to this test module.

    Returns:
        ModuleType containing the cart-index upgrade and downgrade functions.
    """
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/c5e9a4d8b731_fix_active_cart_index_postgresql.py"
    )
    spec = importlib.util.spec_from_file_location("active_cart_index_repair", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_emits_partial_unique_index_for_postgresql() -> None:
    """Compile the repair using Alembic's production PostgreSQL dialect.

    Params:
        None.

    Returns:
        None. The emitted DDL replaces the broken index with the active-only predicate.
    """
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    with Operations.context(context):
        load_migration().upgrade()

    sql = output.getvalue()
    assert "DROP INDEX ux_carts_one_active_per_user" in sql
    assert (
        "CREATE UNIQUE INDEX ux_carts_one_active_per_user ON carts (user_id) WHERE user_id IS NOT NULL AND status = 'active'"
        in sql
    )


def test_migration_preserves_existing_cart_and_allows_historical_orders() -> None:
    """Repair an existing unfiltered unique index while retaining the active-cart rule.

    Params:
        None. Uses an isolated in-memory SQLite migration connection.

    Returns:
        None. Existing rows survive, multiple orders work, and duplicate active carts fail.
    """
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(
                "CREATE TABLE carts (id TEXT PRIMARY KEY, user_id TEXT, status TEXT)"
            )
            connection.exec_driver_sql(
                "CREATE UNIQUE INDEX ux_carts_one_active_per_user ON carts (user_id)"
            )
            connection.exec_driver_sql(
                "INSERT INTO carts VALUES ('existing', 'demo-user', 'active')"
            )
            with Operations.context(MigrationContext.configure(connection)):
                load_migration().upgrade()
            connection.exec_driver_sql(
                "INSERT INTO carts VALUES ('order-one', 'demo-user', 'ordered')"
            )
            connection.exec_driver_sql(
                "INSERT INTO carts VALUES ('order-two', 'demo-user', 'ordered')"
            )
            assert (
                connection.exec_driver_sql("SELECT COUNT(*) FROM carts").scalar_one()
                == 3
            )
            with pytest.raises(IntegrityError):
                connection.exec_driver_sql(
                    "INSERT INTO carts VALUES ('second-active', 'demo-user', 'active')"
                )
    finally:
        engine.dispose()

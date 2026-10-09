"""Restrict the active-cart unique index on PostgreSQL as well as SQLite."""

from alembic import op
import sqlalchemy as sa


revision = "c5e9a4d8b731"
down_revision = "bb4c1f2a9d44"
branch_labels = None
depends_on = None

INDEX_NAME = "ux_carts_one_active_per_user"
ACTIVE_CART = sa.text("user_id IS NOT NULL AND status = 'active'")


def upgrade() -> None:
    """Repair existing databases so historical orders do not occupy the active-cart slot.

    Params:
        None. Uses Alembic's active migration connection.

    Returns:
        None. Replaces the index without changing any user, cart, order, or payment row.
    """
    op.drop_index(INDEX_NAME, table_name="carts")
    op.create_index(
        INDEX_NAME,
        "carts",
        ["user_id"],
        unique=True,
        sqlite_where=ACTIVE_CART,
        postgresql_where=ACTIVE_CART,
    )


def downgrade() -> None:
    """Restore the preceding revision's index definition without deleting cart data.

    Params:
        None. Uses Alembic's active migration connection.

    Returns:
        None. Restores the SQLite-only predicate. PostgreSQL rejects the rollback
        if multiple historical carts now exist for a user, preserving those rows.
    """
    op.drop_index(INDEX_NAME, table_name="carts")
    op.create_index(
        INDEX_NAME, "carts", ["user_id"], unique=True, sqlite_where=ACTIVE_CART
    )

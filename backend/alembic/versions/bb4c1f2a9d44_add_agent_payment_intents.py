"""add agent payment intents

Revision ID: bb4c1f2a9d44
Revises: 4ccba6d6ee2a
Create Date: 2026-10-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bb4c1f2a9d44"
down_revision: Union[str, Sequence[str], None] = "4ccba6d6ee2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create the payment_intents table for agent checkout orders.

    Params:
        None.

    Returns:
        None. Applies schema changes through Alembic operations.
    """
    op.create_table(
        "payment_intents",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("cart_id", sa.String(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("pay_to", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="requires_payment", nullable=False),
        sa.Column("tx_hash", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint("amount_cents >= 0", name="ck_payment_intents_amount_cents"),
        sa.CheckConstraint(
            "status IN ('requires_payment','paid','canceled')",
            name="ck_payment_intents_status",
        ),
        sa.ForeignKeyConstraint(["cart_id"], ["carts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tx_hash", name="ux_payment_intents_tx_hash"),
    )
    op.create_index(op.f("ix_payment_intents_cart_id"), "payment_intents", ["cart_id"], unique=False)


def downgrade() -> None:
    """
    Drop the payment_intents table.

    Params:
        None.

    Returns:
        None. Reverts schema changes through Alembic operations.
    """
    op.drop_index(op.f("ix_payment_intents_cart_id"), table_name="payment_intents")
    op.drop_table("payment_intents")

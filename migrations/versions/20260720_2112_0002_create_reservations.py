"""create reservations

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-20 21:12:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reservations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("table_id", sa.Integer(), nullable=False),
        sa.Column("guest_count", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.CheckConstraint("guest_count > 0", name="ck_reservation_guest_count_positive"),
        sa.ForeignKeyConstraint(["table_id"], ["tables.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reservations_table_id", "reservations", ["table_id"])
    op.create_index("ix_reservations_user_id", "reservations", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_reservations_user_id", table_name="reservations")
    op.drop_index("ix_reservations_table_id", table_name="reservations")
    op.drop_table("reservations")

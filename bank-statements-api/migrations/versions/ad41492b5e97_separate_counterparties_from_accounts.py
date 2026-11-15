"""separate counterparties from accounts

Revision ID: ad41492b5e97
Revises: b19fb1cb1c1c
Create Date: 2026-09-24 08:46:07.773427

Accounts were doing double duty as counterparties. This splits the concepts:
the other side of a transaction is now either one of the user's own accounts
(transfer_account_id) or a counterparty (counterparty_id), never both.

Existing counterparty_account_id values are renamed to transfer_account_id,
which preserves every reference. Deciding which of those referenced accounts
are really people or companies needs knowledge the database does not hold, so
it is done afterwards per account via the convert-to-counterparty endpoint.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ad41492b5e97"
down_revision: Union[str, None] = "b19fb1cb1c1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "counterparties",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column(
            "type",
            sa.Enum("person", "company", "merchant", "other", name="counterpartytype"),
            server_default="other",
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_counterparties_user_name"),
    )
    op.create_index(op.f("ix_counterparties_user_id"), "counterparties", ["user_id"], unique=False)

    op.execute("ALTER TYPE counterpartystatus RENAME TO othersidestatus")

    op.alter_column("transactions", "counterparty_status", new_column_name="other_side_status")
    op.alter_column("transactions", "counterparty_account_id", new_column_name="transfer_account_id")
    op.execute(
        "ALTER TABLE transactions "
        "RENAME CONSTRAINT transactions_counterparty_account_id_fkey TO transactions_transfer_account_id_fkey"
    )
    op.add_column("transactions", sa.Column("counterparty_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "transactions_counterparty_id_fkey",
        "transactions",
        "counterparties",
        ["counterparty_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_transactions_single_other_side",
        "transactions",
        "counterparty_id IS NULL OR transfer_account_id IS NULL",
    )

    op.alter_column("enhancement_rules", "counterparty_account_id", new_column_name="transfer_account_id")
    op.execute(
        "ALTER TABLE enhancement_rules "
        "RENAME CONSTRAINT enhancement_rules_counterparty_account_id_fkey TO enhancement_rules_transfer_account_id_fkey"
    )
    op.add_column("enhancement_rules", sa.Column("counterparty_id", sa.UUID(), nullable=True))
    op.create_foreign_key(
        "enhancement_rules_counterparty_id_fkey",
        "enhancement_rules",
        "counterparties",
        ["counterparty_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_enhancement_rules_single_other_side",
        "enhancement_rules",
        "counterparty_id IS NULL OR transfer_account_id IS NULL",
    )

    op.execute("UPDATE enhancement_rules SET ai_suggested_counterparty_id = NULL, ai_counterparty_confidence = NULL")
    op.drop_constraint("enhancement_rules_ai_suggested_counterparty_id_fkey", "enhancement_rules", type_="foreignkey")
    op.create_foreign_key(
        "enhancement_rules_ai_suggested_counterparty_id_fkey",
        "enhancement_rules",
        "counterparties",
        ["ai_suggested_counterparty_id"],
        ["id"],
    )


def downgrade() -> None:
    op.execute("UPDATE enhancement_rules SET ai_suggested_counterparty_id = NULL, ai_counterparty_confidence = NULL")
    op.drop_constraint("enhancement_rules_ai_suggested_counterparty_id_fkey", "enhancement_rules", type_="foreignkey")
    op.create_foreign_key(
        "enhancement_rules_ai_suggested_counterparty_id_fkey",
        "enhancement_rules",
        "accounts",
        ["ai_suggested_counterparty_id"],
        ["id"],
    )

    op.drop_constraint("ck_enhancement_rules_single_other_side", "enhancement_rules", type_="check")
    op.drop_constraint("enhancement_rules_counterparty_id_fkey", "enhancement_rules", type_="foreignkey")
    op.drop_column("enhancement_rules", "counterparty_id")
    op.execute(
        "ALTER TABLE enhancement_rules "
        "RENAME CONSTRAINT enhancement_rules_transfer_account_id_fkey TO enhancement_rules_counterparty_account_id_fkey"
    )
    op.alter_column("enhancement_rules", "transfer_account_id", new_column_name="counterparty_account_id")

    op.drop_constraint("ck_transactions_single_other_side", "transactions", type_="check")
    op.drop_constraint("transactions_counterparty_id_fkey", "transactions", type_="foreignkey")
    op.drop_column("transactions", "counterparty_id")
    op.execute(
        "ALTER TABLE transactions "
        "RENAME CONSTRAINT transactions_transfer_account_id_fkey TO transactions_counterparty_account_id_fkey"
    )
    op.alter_column("transactions", "transfer_account_id", new_column_name="counterparty_account_id")
    op.alter_column("transactions", "other_side_status", new_column_name="counterparty_status")

    op.execute("ALTER TYPE othersidestatus RENAME TO counterpartystatus")

    op.drop_index(op.f("ix_counterparties_user_id"), table_name="counterparties")
    op.drop_table("counterparties")
    postgresql.ENUM(name="counterpartytype").drop(op.get_bind(), checkfirst=True)

"""reclassify known accounts as counterparties

Revision ID: c7d2e9f41a08
Revises: ad41492b5e97
Create Date: 2026-11-15

A data-only follow-up to ad41492b5e97, which separated the two concepts but
deliberately left every existing reference in transfer_account_id, because the
database cannot tell a tenant from a savings account.

These are the accounts the owner identified as people or companies. Each one is
converted only if it owns nothing — no transactions, statements, initial balance
or import configs — so a real account can never be destroyed by a name clash.
An account that is absent, already converted, or owns something is skipped,
which makes this a no-op on a fresh or test database.

Matching is by name rather than user so that no email address is committed here;
the ownership check is what makes that safe.
"""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "c7d2e9f41a08"
down_revision: Union[str, None] = "ad41492b5e97"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RECLASSIFIED = (
    ("Carla", "person"),
    ("Filipe", "person"),
    ("1D", "person"),
    ("1E", "person"),
    ("R/C D", "person"),
    ("R/C E", "person"),
    ("2 E", "person"),
    ("EE", "company"),
)

OWNERSHIP_TABLES = ("transactions", "statements", "initial_balances", "file_analysis_metadata")


def _owns_anything(bind, account_id) -> bool:
    for table in OWNERSHIP_TABLES:
        count = bind.execute(sa.text(f"SELECT count(*) FROM {table} WHERE account_id = :id"), {"id": account_id}).scalar()
        if count:
            return True
    return False


def _repoint(bind, table, from_column, to_column, from_id, to_id) -> int:
    return bind.execute(
        sa.text(f"UPDATE {table} SET {to_column} = :to_id, {from_column} = NULL WHERE {from_column} = :from_id"),
        {"to_id": to_id, "from_id": from_id},
    ).rowcount


def upgrade() -> None:
    bind = op.get_bind()

    for name, counterparty_type in RECLASSIFIED:
        accounts = bind.execute(sa.text("SELECT id, user_id FROM accounts WHERE name = :name"), {"name": name}).fetchall()

        for account_id, user_id in accounts:
            if _owns_anything(bind, account_id):
                continue

            counterparty_id = bind.execute(
                sa.text("SELECT id FROM counterparties WHERE user_id = :user_id AND name = :name"),
                {"user_id": user_id, "name": name},
            ).scalar()

            if counterparty_id is None:
                counterparty_id = uuid4()
                bind.execute(
                    sa.text("INSERT INTO counterparties (id, user_id, name, type) " "VALUES (:id, :user_id, :name, :type)"),
                    {"id": counterparty_id, "user_id": user_id, "name": name, "type": counterparty_type},
                )

            _repoint(bind, "transactions", "transfer_account_id", "counterparty_id", account_id, counterparty_id)
            _repoint(bind, "enhancement_rules", "transfer_account_id", "counterparty_id", account_id, counterparty_id)

            bind.execute(sa.text("DELETE FROM accounts WHERE id = :id"), {"id": account_id})


def downgrade() -> None:
    bind = op.get_bind()

    for name, _ in RECLASSIFIED:
        counterparties = bind.execute(
            sa.text("SELECT id, user_id FROM counterparties WHERE name = :name"), {"name": name}
        ).fetchall()

        for counterparty_id, user_id in counterparties:
            account_id = bind.execute(
                sa.text("SELECT id FROM accounts WHERE user_id = :user_id AND name = :name"),
                {"user_id": user_id, "name": name},
            ).scalar()

            if account_id is None:
                account_id = uuid4()
                bind.execute(
                    sa.text("INSERT INTO accounts (id, user_id, name, currency) " "VALUES (:id, :user_id, :name, 'EUR')"),
                    {"id": account_id, "user_id": user_id, "name": name},
                )

            _repoint(bind, "transactions", "counterparty_id", "transfer_account_id", counterparty_id, account_id)
            _repoint(bind, "enhancement_rules", "counterparty_id", "transfer_account_id", counterparty_id, account_id)

            bind.execute(sa.text("DELETE FROM counterparties WHERE id = :id"), {"id": counterparty_id})

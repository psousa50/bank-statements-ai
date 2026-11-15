from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domain.models.account import Account
from app.domain.models.initial_balance import InitialBalance
from app.domain.models.statement import Statement
from app.domain.models.transaction import Transaction
from app.domain.models.uploaded_file import FileAnalysisMetadata
from app.ports.repositories.account import AccountRepository


class SQLAlchemyAccountRepository(AccountRepository):
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create(self, account: Account) -> Account:
        self.db_session.add(account)
        self.db_session.commit()
        self.db_session.refresh(account)
        return account

    def get_by_id(self, account_id: UUID, user_id: UUID) -> Optional[Account]:
        return self.db_session.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()

    def get_by_name(self, name: str, user_id: UUID) -> Optional[Account]:
        return self.db_session.query(Account).filter(Account.name == name, Account.user_id == user_id).first()

    def get_all(self, user_id: UUID) -> List[Account]:
        return self.db_session.query(Account).filter(Account.user_id == user_id).all()

    def update(self, account: Account) -> Account:
        self.db_session.commit()
        self.db_session.refresh(account)
        return account

    def delete(self, account_id: UUID, user_id: UUID) -> None:
        account = self.get_by_id(account_id, user_id)
        if account:
            self.db_session.delete(account)
            self.db_session.commit()

    def count_ownership_records(self, account_id: UUID) -> Dict[str, int]:
        owners = {
            "transactions": Transaction.account_id,
            "statements": Statement.account_id,
            "initial_balances": InitialBalance.account_id,
            "import_configs": FileAnalysisMetadata.account_id,
        }
        return {
            label: self.db_session.query(func.count()).filter(column == account_id).scalar() or 0
            for label, column in owners.items()
        }

from dataclasses import dataclass
from typing import Dict, List
from uuid import UUID

from app.domain.models.counterparty import Counterparty, CounterpartyType
from app.ports.repositories.account import AccountRepository
from app.ports.repositories.counterparty import CounterpartyRepository
from app.ports.repositories.enhancement_rule import EnhancementRuleRepository
from app.ports.repositories.transaction import TransactionRepository

_OWNERSHIP_LABELS = {
    "transactions": "owns transactions",
    "statements": "has statements",
    "initial_balances": "has an initial balance",
    "import_configs": "has saved import configs",
}


class AccountIsRealAccount(Exception):
    def __init__(self, account_name: str, reasons: List[str]):
        self.account_name = account_name
        self.reasons = reasons
        super().__init__(f"Account '{account_name}' is a real account: {', '.join(reasons)}")


@dataclass
class AccountConversionResult:
    counterparty: Counterparty
    transactions_repointed: int
    rules_repointed: int


class AccountConversionService:
    def __init__(
        self,
        account_repository: AccountRepository,
        counterparty_repository: CounterpartyRepository,
        transaction_repository: TransactionRepository,
        enhancement_rule_repository: EnhancementRuleRepository,
    ):
        self.account_repository = account_repository
        self.counterparty_repository = counterparty_repository
        self.transaction_repository = transaction_repository
        self.enhancement_rule_repository = enhancement_rule_repository

    def describe_conversion_blockers(self, account_id: UUID) -> List[str]:
        counts = self.account_repository.count_ownership_records(account_id)
        return [f"{_OWNERSHIP_LABELS[key]} ({count})" for key, count in counts.items() if count]

    def convert_to_counterparty(
        self,
        account_id: UUID,
        user_id: UUID,
        type: CounterpartyType = CounterpartyType.OTHER,
    ) -> AccountConversionResult:
        account = self.account_repository.get_by_id(account_id, user_id)
        if not account:
            raise ValueError(f"Account with ID {account_id} not found")

        blockers = self.describe_conversion_blockers(account_id)
        if blockers:
            raise AccountIsRealAccount(account.name, blockers)

        counterparty = self.counterparty_repository.get_by_name(account.name, user_id) or self.counterparty_repository.create(
            Counterparty(name=account.name, user_id=user_id, type=type)
        )

        transactions_repointed = self.transaction_repository.repoint_transfer_account_to_counterparty(
            account_id, counterparty.id, user_id
        )
        rules_repointed = self.enhancement_rule_repository.repoint_transfer_account_to_counterparty(
            account_id, counterparty.id, user_id
        )

        self.account_repository.delete(account_id, user_id)

        return AccountConversionResult(
            counterparty=counterparty,
            transactions_repointed=transactions_repointed,
            rules_repointed=rules_repointed,
        )

    def list_conversion_candidates(self, user_id: UUID) -> List[Dict]:
        candidates = []
        for account in self.account_repository.get_all(user_id):
            blockers = self.describe_conversion_blockers(account.id)
            if blockers:
                continue
            candidates.append(
                {
                    "account_id": account.id,
                    "name": account.name,
                    "referenced_as_other_side": self.transaction_repository.count_by_transfer_account(account.id, user_id),
                }
            )
        return candidates

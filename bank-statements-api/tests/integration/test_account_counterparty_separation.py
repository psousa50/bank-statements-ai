from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.adapters.repositories.account import SQLAlchemyAccountRepository
from app.adapters.repositories.counterparty import SQLAlchemyCounterpartyRepository
from app.adapters.repositories.enhancement_rule import SQLAlchemyEnhancementRuleRepository
from app.adapters.repositories.transaction import SQLAlchemyTransactionRepository
from app.domain.models.account import Account
from app.domain.models.counterparty import Counterparty, CounterpartyType
from app.domain.models.enhancement_rule import EnhancementRule, EnhancementRuleSource, MatchType
from app.domain.models.enhancement_rule_pattern import EnhancementRulePattern
from app.domain.models.statement import Statement
from app.domain.models.transaction import CategorizationStatus, SourceType, Transaction
from app.services.account_conversion import AccountConversionService, AccountIsRealAccount


@pytest.fixture
def conversion_service(db_session):
    return AccountConversionService(
        account_repository=SQLAlchemyAccountRepository(db_session),
        counterparty_repository=SQLAlchemyCounterpartyRepository(db_session),
        transaction_repository=SQLAlchemyTransactionRepository(db_session),
        enhancement_rule_repository=SQLAlchemyEnhancementRuleRepository(db_session),
    )


def _account(db_session, user_id, name):
    account = Account(id=uuid4(), user_id=user_id, name=name, currency="EUR")
    db_session.add(account)
    db_session.flush()
    return account


def _transaction(db_session, account, **overrides):
    defaults = dict(
        id=uuid4(),
        user_id=account.user_id,
        date=date(2023, 6, 15),
        description="Test Transaction",
        normalized_description="test transaction",
        amount=Decimal("-10.00"),
        account_id=account.id,
        source_type=SourceType.UPLOAD,
        categorization_status=CategorizationStatus.UNCATEGORIZED,
        row_index=0,
        sort_index=0,
    )
    defaults.update(overrides)
    transaction = Transaction(**defaults)
    db_session.add(transaction)
    db_session.flush()
    return transaction


def _rule(db_session, user_id, pattern, **overrides):
    rule = EnhancementRule(
        id=uuid4(),
        user_id=user_id,
        source=EnhancementRuleSource.MANUAL,
        **overrides,
    )
    rule.patterns = [EnhancementRulePattern(normalized_description=pattern, match_type=MatchType.EXACT, sort_order=0)]
    db_session.add(rule)
    db_session.flush()
    return rule


class TestOtherSideExclusivity:
    def test_transaction_rejects_both_counterparty_and_transfer_account(self, db_session, user_a, account_for_user_a):
        counterparty = Counterparty(id=uuid4(), user_id=user_a.id, name="Filipe", type=CounterpartyType.PERSON)
        db_session.add(counterparty)
        other_account = _account(db_session, user_a.id, "Savings")

        with pytest.raises(IntegrityError):
            _transaction(
                db_session,
                account_for_user_a,
                counterparty_id=counterparty.id,
                transfer_account_id=other_account.id,
            )

    def test_transaction_accepts_a_counterparty_alone(self, db_session, user_a, account_for_user_a):
        counterparty = Counterparty(id=uuid4(), user_id=user_a.id, name="Carla", type=CounterpartyType.PERSON)
        db_session.add(counterparty)

        transaction = _transaction(db_session, account_for_user_a, counterparty_id=counterparty.id)

        assert transaction.counterparty_id == counterparty.id
        assert transaction.transfer_account_id is None

    def test_transaction_accepts_a_transfer_account_alone(self, db_session, user_a, account_for_user_a):
        savings = _account(db_session, user_a.id, "Savings")

        transaction = _transaction(db_session, account_for_user_a, transfer_account_id=savings.id)

        assert transaction.transfer_account_id == savings.id
        assert transaction.counterparty_id is None

    def test_rule_rejects_both_counterparty_and_transfer_account(self, db_session, user_a):
        counterparty = Counterparty(id=uuid4(), user_id=user_a.id, name="Landlord", type=CounterpartyType.PERSON)
        db_session.add(counterparty)
        savings = _account(db_session, user_a.id, "Savings")

        with pytest.raises(IntegrityError):
            _rule(db_session, user_a.id, "rent", counterparty_id=counterparty.id, transfer_account_id=savings.id)

    def test_assigning_a_counterparty_clears_the_transfer_account(self, db_session, user_a, account_for_user_a):
        savings = _account(db_session, user_a.id, "Savings")
        counterparty = Counterparty(id=uuid4(), user_id=user_a.id, name="Filipe", type=CounterpartyType.PERSON)
        db_session.add(counterparty)
        transaction = _transaction(db_session, account_for_user_a, transfer_account_id=savings.id)

        transaction.assign_counterparty(counterparty.id)
        db_session.flush()

        assert transaction.counterparty_id == counterparty.id
        assert transaction.transfer_account_id is None

    def test_assigning_a_transfer_account_clears_the_counterparty(self, db_session, user_a, account_for_user_a):
        savings = _account(db_session, user_a.id, "Savings")
        counterparty = Counterparty(id=uuid4(), user_id=user_a.id, name="Filipe", type=CounterpartyType.PERSON)
        db_session.add(counterparty)
        transaction = _transaction(db_session, account_for_user_a, counterparty_id=counterparty.id)

        transaction.assign_transfer_account(savings.id)
        db_session.flush()

        assert transaction.transfer_account_id == savings.id
        assert transaction.counterparty_id is None


class TestAccountConversion:
    def test_converts_a_phantom_account_and_repoints_its_references(
        self, db_session, user_a, account_for_user_a, conversion_service
    ):
        landlord = _account(db_session, user_a.id, "Landlord")
        _transaction(db_session, account_for_user_a, transfer_account_id=landlord.id)
        _transaction(db_session, account_for_user_a, transfer_account_id=landlord.id)
        _rule(db_session, user_a.id, "rent payment", transfer_account_id=landlord.id)
        db_session.commit()

        result = conversion_service.convert_to_counterparty(landlord.id, user_a.id, CounterpartyType.PERSON)

        assert result.counterparty.name == "Landlord"
        assert result.counterparty.type == CounterpartyType.PERSON
        assert result.transactions_repointed == 2
        assert result.rules_repointed == 1

        assert SQLAlchemyAccountRepository(db_session).get_by_id(landlord.id, user_a.id) is None

        repointed = db_session.query(Transaction).filter(Transaction.counterparty_id == result.counterparty.id).all()
        assert len(repointed) == 2
        assert all(t.transfer_account_id is None for t in repointed)

    def test_refuses_to_convert_an_account_that_owns_transactions(
        self, db_session, user_a, account_for_user_a, conversion_service
    ):
        _transaction(db_session, account_for_user_a)
        db_session.commit()

        with pytest.raises(AccountIsRealAccount) as excinfo:
            conversion_service.convert_to_counterparty(account_for_user_a.id, user_a.id)

        assert "owns transactions" in str(excinfo.value)
        assert SQLAlchemyAccountRepository(db_session).get_by_id(account_for_user_a.id, user_a.id) is not None

    def test_refuses_to_convert_an_account_that_has_statements(self, db_session, user_a, conversion_service):
        account = _account(db_session, user_a.id, "Has Statements")
        db_session.add(
            Statement(
                id=uuid4(),
                filename="test.csv",
                file_type="CSV",
                content=b"test",
                account_id=account.id,
            )
        )
        db_session.commit()

        with pytest.raises(AccountIsRealAccount) as excinfo:
            conversion_service.convert_to_counterparty(account.id, user_a.id)

        assert "has statements" in str(excinfo.value)

    def test_reuses_an_existing_counterparty_of_the_same_name(self, db_session, user_a, account_for_user_a, conversion_service):
        existing = Counterparty(id=uuid4(), user_id=user_a.id, name="Filipe", type=CounterpartyType.PERSON)
        db_session.add(existing)
        phantom = _account(db_session, user_a.id, "Filipe")
        _transaction(db_session, account_for_user_a, transfer_account_id=phantom.id)
        db_session.commit()

        result = conversion_service.convert_to_counterparty(phantom.id, user_a.id)

        assert result.counterparty.id == existing.id
        assert result.transactions_repointed == 1

    def test_lists_only_accounts_that_own_nothing_as_candidates(
        self, db_session, user_a, account_for_user_a, conversion_service
    ):
        phantom = _account(db_session, user_a.id, "Phantom")
        _transaction(db_session, account_for_user_a, transfer_account_id=phantom.id)
        db_session.commit()

        candidates = conversion_service.list_conversion_candidates(user_a.id)
        names = {c["name"] for c in candidates}

        assert "Phantom" in names
        assert account_for_user_a.name not in names
        assert next(c for c in candidates if c["name"] == "Phantom")["referenced_as_other_side"] == 1

    def test_does_not_convert_another_users_account(self, db_session, user_a, user_b, conversion_service):
        other = _account(db_session, user_b.id, "Not Mine")
        db_session.commit()

        with pytest.raises(ValueError):
            conversion_service.convert_to_counterparty(other.id, user_a.id)


class TestFilteringByCounterparty:
    def test_filters_transactions_down_to_one_counterparty(self, db_session, user_a, account_for_user_a):
        landlord = Counterparty(id=uuid4(), user_id=user_a.id, name="Landlord", type=CounterpartyType.PERSON)
        shop = Counterparty(id=uuid4(), user_id=user_a.id, name="Shop", type=CounterpartyType.MERCHANT)
        db_session.add_all([landlord, shop])
        db_session.flush()

        _transaction(db_session, account_for_user_a, counterparty_id=landlord.id, amount=Decimal("-750.00"))
        _transaction(db_session, account_for_user_a, counterparty_id=landlord.id, amount=Decimal("-750.00"))
        _transaction(db_session, account_for_user_a, counterparty_id=shop.id, amount=Decimal("-20.00"))
        _transaction(db_session, account_for_user_a)
        db_session.commit()

        repository = SQLAlchemyTransactionRepository(db_session)
        transactions, total, _ = repository.get_paginated(user_id=user_a.id, counterparty_id=landlord.id)

        assert total == 2
        assert {t.counterparty_id for t in transactions} == {landlord.id}

    def test_without_the_filter_every_transaction_is_returned(self, db_session, user_a, account_for_user_a):
        shop = Counterparty(id=uuid4(), user_id=user_a.id, name="Shop", type=CounterpartyType.MERCHANT)
        db_session.add(shop)
        db_session.flush()
        _transaction(db_session, account_for_user_a, counterparty_id=shop.id)
        _transaction(db_session, account_for_user_a)
        db_session.commit()

        repository = SQLAlchemyTransactionRepository(db_session)
        _, total, _ = repository.get_paginated(user_id=user_a.id)

        assert total == 2

    def test_does_not_leak_another_users_transactions(self, db_session, user_a, user_b, account_for_user_a):
        shared_name = Counterparty(id=uuid4(), user_id=user_a.id, name="Shop", type=CounterpartyType.MERCHANT)
        db_session.add(shared_name)
        db_session.flush()
        _transaction(db_session, account_for_user_a, counterparty_id=shared_name.id)
        db_session.commit()

        repository = SQLAlchemyTransactionRepository(db_session)
        _, total, _ = repository.get_paginated(user_id=user_b.id, counterparty_id=shared_name.id)

        assert total == 0


class TestCounterpartyIsolation:
    def test_counterparty_names_are_unique_per_user(self, db_session, user_a):
        db_session.add(Counterparty(id=uuid4(), user_id=user_a.id, name="Filipe", type=CounterpartyType.PERSON))
        db_session.flush()
        db_session.add(Counterparty(id=uuid4(), user_id=user_a.id, name="Filipe", type=CounterpartyType.COMPANY))

        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_the_same_name_is_allowed_for_different_users(self, db_session, user_a, user_b):
        db_session.add(Counterparty(id=uuid4(), user_id=user_a.id, name="Filipe", type=CounterpartyType.PERSON))
        db_session.add(Counterparty(id=uuid4(), user_id=user_b.id, name="Filipe", type=CounterpartyType.PERSON))

        db_session.flush()

        assert db_session.query(Counterparty).filter(Counterparty.name == "Filipe").count() == 2

    def test_an_account_and_a_counterparty_may_share_a_name(self, db_session, user_a):
        _account(db_session, user_a.id, "Revolut - Savings")
        db_session.add(Counterparty(id=uuid4(), user_id=user_a.id, name="Revolut - Savings", type=CounterpartyType.COMPANY))

        db_session.flush()

        assert db_session.query(Counterparty).filter(Counterparty.name == "Revolut - Savings").count() == 1

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class CategorizationStatus(str, Enum):
    UNCATEGORIZED = "UNCATEGORIZED"
    RULE_BASED = "RULE_BASED"
    MANUAL = "MANUAL"
    FAILURE = "FAILURE"


class SourceType(str, Enum):
    UPLOAD = "upload"
    MANUAL = "manual"


class OtherSideStatus(str, Enum):
    UNPROCESSED = "UNPROCESSED"
    RULE_BASED = "RULE_BASED"
    MANUAL = "MANUAL"
    FAILURE = "FAILURE"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date = Column(Date, nullable=False, index=True)
    description = Column(String, nullable=False)
    normalized_description = Column(String, nullable=False, index=True)
    amount = Column(Numeric(precision=10, scale=2), nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    statement_id = Column(
        UUID(as_uuid=True),
        ForeignKey("statements.id", ondelete="CASCADE"),
        nullable=True,
    )
    statement = relationship("Statement", back_populates="transactions")

    category_id = Column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),
        nullable=True,
    )
    category = relationship("Category")

    account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        nullable=False,
    )
    account = relationship(
        "Account",
        foreign_keys=[account_id],
        back_populates="transactions",
    )

    counterparty_id = Column(
        UUID(as_uuid=True),
        ForeignKey("counterparties.id"),
        nullable=True,
    )
    counterparty = relationship(
        "Counterparty",
        back_populates="transactions",
    )

    transfer_account_id = Column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        nullable=True,
    )
    transfer_account = relationship(
        "Account",
        foreign_keys=[transfer_account_id],
        back_populates="transfer_transactions",
    )

    tags = relationship(
        "Tag",
        secondary="transaction_tags",
        back_populates="transactions",
        lazy="selectin",
    )

    categorization_status = Column(
        SQLAlchemyEnum(CategorizationStatus),
        default=CategorizationStatus.UNCATEGORIZED,
        nullable=False,
    )

    categorization_confidence = Column(Numeric(precision=5, scale=4), nullable=True)

    other_side_status = Column(
        SQLAlchemyEnum(OtherSideStatus, name="othersidestatus"),
        default=OtherSideStatus.UNPROCESSED,
        nullable=False,
    )

    # New ordering fields
    row_index = Column(Integer, nullable=True)
    sort_index = Column(Integer, nullable=False, default=0)
    source_type = Column(
        SQLAlchemyEnum(
            SourceType,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=SourceType.UPLOAD,
        nullable=False,
    )
    manual_position_after = Column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id"),
        nullable=True,
    )

    exclude_from_analytics = Column(Boolean, default=False, nullable=False, server_default="false")

    parent_transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id"),
        nullable=True,
        index=True,
    )

    __table_args__ = (
        Index("ix_transactions_account_id_date", "account_id", "date"),
        Index("ix_transactions_user_id_category_id", "user_id", "category_id"),
        Index("ix_transactions_user_id_date", "user_id", "date"),
        CheckConstraint(
            "counterparty_id IS NULL OR transfer_account_id IS NULL",
            name="ck_transactions_single_other_side",
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._running_balance: Optional[Decimal] = None
        self._is_split_parent: bool = False
        if self.exclude_from_analytics is None:
            self.exclude_from_analytics = False

    @property
    def running_balance(self) -> Optional[Decimal]:
        return getattr(self, "_running_balance", None)

    @running_balance.setter
    def running_balance(self, value: Optional[Decimal]):
        self._running_balance = value

    @property
    def is_split_parent(self) -> bool:
        return getattr(self, "_is_split_parent", False)

    @is_split_parent.setter
    def is_split_parent(self, value: bool):
        self._is_split_parent = value

    @property
    def is_split_child(self) -> bool:
        return self.parent_transaction_id is not None

    def mark_categorized(self):
        """Mark the transaction as categorized (for backward compatibility)"""
        self.categorization_status = CategorizationStatus.RULE_BASED

    def mark_rule_based_categorization(self):
        """Mark the transaction as categorized by a rule"""
        self.categorization_status = CategorizationStatus.RULE_BASED

    def mark_manual_categorization(self):
        """Mark the transaction as manually categorized"""
        self.categorization_status = CategorizationStatus.MANUAL

    def mark_rule_based_other_side(self):
        """Mark the other side as assigned by a rule"""
        self.other_side_status = OtherSideStatus.RULE_BASED

    def mark_manual_other_side(self):
        """Mark the other side as manually assigned"""
        self.other_side_status = OtherSideStatus.MANUAL

    def assign_counterparty(self, counterparty_id):
        self.counterparty_id = counterparty_id
        self.transfer_account_id = None

    def assign_transfer_account(self, transfer_account_id):
        self.transfer_account_id = transfer_account_id
        self.counterparty_id = None

    def __repr__(self):
        return f"<Transaction(id={self.id}, date={self.date}, amount={self.amount}, category_id={self.category_id}, sort_index={self.sort_index})>"

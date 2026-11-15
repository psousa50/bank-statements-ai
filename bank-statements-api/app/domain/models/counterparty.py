from enum import Enum
from uuid import uuid4

from sqlalchemy import Column
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class CounterpartyType(str, Enum):
    PERSON = "person"
    COMPANY = "company"
    MERCHANT = "merchant"
    OTHER = "other"

    def __str__(self):
        return self.value


class Counterparty(Base):
    __tablename__ = "counterparties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    type = Column(
        SQLAlchemyEnum(
            CounterpartyType,
            name="counterpartytype",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=CounterpartyType.OTHER,
        server_default=CounterpartyType.OTHER.value,
    )

    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_counterparties_user_name"),)

    user = relationship("User", back_populates="counterparties")

    transactions = relationship("Transaction", back_populates="counterparty")

    def __repr__(self):
        return f"<Counterparty(id={self.id}, name={self.name}, type={self.type})>"

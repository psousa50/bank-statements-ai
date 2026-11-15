from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.models.counterparty import Counterparty
from app.ports.repositories.counterparty import CounterpartyRepository


class SQLAlchemyCounterpartyRepository(CounterpartyRepository):
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create(self, counterparty: Counterparty) -> Counterparty:
        self.db_session.add(counterparty)
        self.db_session.commit()
        self.db_session.refresh(counterparty)
        return counterparty

    def get_by_id(self, counterparty_id: UUID, user_id: UUID) -> Optional[Counterparty]:
        return (
            self.db_session.query(Counterparty)
            .filter(Counterparty.id == counterparty_id, Counterparty.user_id == user_id)
            .first()
        )

    def get_by_name(self, name: str, user_id: UUID) -> Optional[Counterparty]:
        return self.db_session.query(Counterparty).filter(Counterparty.name == name, Counterparty.user_id == user_id).first()

    def get_all(self, user_id: UUID) -> List[Counterparty]:
        return self.db_session.query(Counterparty).filter(Counterparty.user_id == user_id).order_by(Counterparty.name).all()

    def update(self, counterparty: Counterparty) -> Counterparty:
        self.db_session.commit()
        self.db_session.refresh(counterparty)
        return counterparty

    def delete(self, counterparty_id: UUID, user_id: UUID) -> None:
        counterparty = self.get_by_id(counterparty_id, user_id)
        if counterparty:
            self.db_session.delete(counterparty)
            self.db_session.commit()

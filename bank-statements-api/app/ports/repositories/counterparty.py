from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from app.domain.models.counterparty import Counterparty


class CounterpartyRepository(ABC):
    @abstractmethod
    def create(self, counterparty: Counterparty) -> Counterparty:
        pass

    @abstractmethod
    def get_by_id(self, counterparty_id: UUID, user_id: UUID) -> Optional[Counterparty]:
        pass

    @abstractmethod
    def get_by_name(self, name: str, user_id: UUID) -> Optional[Counterparty]:
        pass

    @abstractmethod
    def get_all(self, user_id: UUID) -> List[Counterparty]:
        pass

    @abstractmethod
    def update(self, counterparty: Counterparty) -> Counterparty:
        pass

    @abstractmethod
    def delete(self, counterparty_id: UUID, user_id: UUID) -> None:
        pass

import csv
import io
from typing import List, Optional
from uuid import UUID

from app.api.errors import ValidationError
from app.domain.models.counterparty import Counterparty, CounterpartyType
from app.ports.repositories.counterparty import CounterpartyRepository


class CounterpartyService:
    def __init__(self, counterparty_repository: CounterpartyRepository):
        self.counterparty_repository = counterparty_repository

    def create_counterparty(
        self,
        name: str,
        user_id: UUID,
        type: CounterpartyType = CounterpartyType.OTHER,
    ) -> Counterparty:
        counterparty = Counterparty(name=name, user_id=user_id, type=type)
        return self.counterparty_repository.create(counterparty)

    def get_counterparty(self, counterparty_id: UUID, user_id: UUID) -> Optional[Counterparty]:
        return self.counterparty_repository.get_by_id(counterparty_id, user_id)

    def get_counterparty_by_name(self, name: str, user_id: UUID) -> Optional[Counterparty]:
        return self.counterparty_repository.get_by_name(name, user_id)

    def get_all_counterparties(self, user_id: UUID) -> List[Counterparty]:
        return self.counterparty_repository.get_all(user_id)

    def update_counterparty(
        self,
        counterparty_id: UUID,
        name: str,
        user_id: UUID,
        type: CounterpartyType = CounterpartyType.OTHER,
    ) -> Optional[Counterparty]:
        counterparty = self.counterparty_repository.get_by_id(counterparty_id, user_id)
        if counterparty:
            counterparty.name = name
            counterparty.type = type
            return self.counterparty_repository.update(counterparty)
        return None

    def delete_counterparty(self, counterparty_id: UUID, user_id: UUID) -> bool:
        counterparty = self.counterparty_repository.get_by_id(counterparty_id, user_id)
        if counterparty:
            self.counterparty_repository.delete(counterparty_id, user_id)
            return True
        return False

    def upsert_counterparties_from_csv(self, csv_content: str, user_id: UUID) -> List[Counterparty]:
        counterparties = []
        csv_reader = csv.DictReader(io.StringIO(csv_content))

        for row in csv_reader:
            if "name" not in row:
                raise ValidationError("CSV must contain 'name' column")

            name = row["name"].strip()
            if not name:
                continue

            existing = self.counterparty_repository.get_by_name(name, user_id)
            if existing:
                counterparties.append(existing)
            else:
                counterparties.append(
                    self.counterparty_repository.create(
                        Counterparty(name=name, user_id=user_id, type=self._parse_type(row.get("type")))
                    )
                )

        return counterparties

    def _parse_type(self, raw: Optional[str]) -> CounterpartyType:
        if not raw:
            return CounterpartyType.OTHER
        try:
            return CounterpartyType(raw.strip().lower())
        except ValueError:
            raise ValidationError(f"Unknown counterparty type '{raw}'")

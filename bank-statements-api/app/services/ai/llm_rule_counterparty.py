import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from app.adapters.repositories.counterparty import SQLAlchemyCounterpartyRepository
from app.ai.llm_client import LLMClient
from app.ai.prompts import rule_counterparty_prompt
from app.common.json_utils import sanitize_json
from app.domain.models.categorization import RuleCounterpartyResult
from app.domain.models.enhancement_rule import EnhancementRule

logger = logging.getLogger(__name__)


@dataclass
class LLMCounterpartyResult:
    pattern: str
    counterparty_id: Optional[str]
    confidence: float


class LLMRuleCounterparty:
    def __init__(
        self,
        counterparty_repository: SQLAlchemyCounterpartyRepository,
        llm_client: LLMClient,
    ):
        self.counterparty_repository = counterparty_repository
        self.llm_client = llm_client

    def suggest_counterparties(
        self,
        rules: list[EnhancementRule],
        user_id: UUID,
    ) -> list[RuleCounterpartyResult]:
        if not rules:
            return []

        counterparties = self.counterparty_repository.get_all(user_id)
        if not counterparties:
            return [
                RuleCounterpartyResult(
                    rule_id=rule.id,
                    suggested_counterparty_id=None,
                    confidence=None,
                    error_message="No counterparties available",
                )
                for rule in rules
            ]

        try:
            patterns = [rule.normalized_description_pattern for rule in rules]
            prompt = rule_counterparty_prompt(patterns, counterparties)

            logger.debug(f"Sending {len(rules)} rules to LLM for counterparty identification")
            response = self.llm_client.generate(prompt)

            json_result = sanitize_json(response)
            if not json_result:
                return [
                    RuleCounterpartyResult(
                        rule_id=rule.id,
                        suggested_counterparty_id=None,
                        confidence=None,
                        error_message="Invalid JSON response from LLM",
                    )
                    for rule in rules
                ]

            llm_results = [
                LLMCounterpartyResult(
                    pattern=str(result.get("pattern", "")),
                    counterparty_id=result.get("counterparty_id"),
                    confidence=float(result.get("confidence", 0.0)),
                )
                for result in json_result
                if isinstance(result, dict)
            ]

            results = []
            for rule in rules:
                matching_result = self._find_matching_result(rule.normalized_description_pattern, llm_results)

                if matching_result and matching_result.counterparty_id:
                    counterparty_id = self._resolve_counterparty_id(matching_result.counterparty_id, counterparties)
                    if counterparty_id:
                        results.append(
                            RuleCounterpartyResult(
                                rule_id=rule.id,
                                suggested_counterparty_id=counterparty_id,
                                confidence=matching_result.confidence,
                            )
                        )
                    else:
                        results.append(
                            RuleCounterpartyResult(
                                rule_id=rule.id,
                                suggested_counterparty_id=None,
                                confidence=None,
                                error_message=f"Counterparty {matching_result.counterparty_id} not found",
                            )
                        )
                else:
                    results.append(
                        RuleCounterpartyResult(
                            rule_id=rule.id,
                            suggested_counterparty_id=None,
                            confidence=None,
                            error_message="No counterparty identified by LLM",
                        )
                    )

            return results

        except Exception as e:
            logger.error(f"Error in LLM rule counterparty identification: {str(e)}")
            return [
                RuleCounterpartyResult(
                    rule_id=rule.id,
                    suggested_counterparty_id=None,
                    confidence=None,
                    error_message=f"LLM error: {str(e)}",
                )
                for rule in rules
            ]

    def _find_matching_result(self, pattern: str, llm_results: list[LLMCounterpartyResult]) -> Optional[LLMCounterpartyResult]:
        for result in llm_results:
            if result.pattern == pattern:
                return result
        return None

    def _resolve_counterparty_id(self, counterparty_id_str: str, counterparties: list) -> Optional[UUID]:
        match = next(
            (c for c in counterparties if str(c.id) == counterparty_id_str),
            None,
        )
        return match.id if match else None

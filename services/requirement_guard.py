from ...catalog.services.normalization import normalize_category
from .clarification import ProcurementClarificationService
from .intake import RequirementIntakeService


class RequirementGuardService:
    def __init__(self, intake_service=None, clarification_service=None):
        self.intake_service = intake_service or RequirementIntakeService()
        self.clarification_service = clarification_service or ProcurementClarificationService()

    def validate(self, requirements) -> dict:
        normalized = self.intake_service.normalize_state_requirements(requirements or {})
        blocking = self.blocking_reasons(normalized)
        readiness = self.clarification_service.assess(normalized)
        return {
            "requirements": normalized,
            "is_ready": not bool(blocking) and bool(readiness.get("is_ready")),
            "blocking_reasons": blocking,
            "highest_impact_gap": self.highest_impact_gap(normalized),
            "readiness": readiness,
        }

    def is_ready(self, requirements) -> bool:
        return bool(self.validate(requirements).get("is_ready"))

    def highest_impact_gap(self, requirements) -> str | None:
        readiness = self.clarification_service.assess(requirements or {})
        return readiness.get("highest_priority_missing_field")

    def blocking_reasons(self, requirements) -> list[str]:
        requirements = dict(requirements or {})
        reasons = []
        preferred_categories = list(requirements.get("preferred_categories") or [])
        normalized_categories = [
            normalize_category(category)
            for category in preferred_categories
            if normalize_category(category)
        ]
        if preferred_categories and not normalized_categories:
            reasons.append("invalid_category")
        budget = requirements.get("budget")
        if budget is not None and float(budget) < 0:
            reasons.append("invalid_budget")
        quantity = requirements.get("quantity")
        if quantity is not None and int(quantity) <= 0:
            reasons.append("invalid_quantity")
        intent_groups = list(requirements.get("intent_groups") or [])
        if intent_groups:
            for group in intent_groups:
                if not isinstance(group, dict) or not group.get("preferred_category"):
                    reasons.append("invalid_intent_groups")
                    break
        return reasons


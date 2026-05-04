from dataclasses import dataclass, field
from uuid import uuid4


@dataclass(frozen=True)
class PreparedProcurementContext:
    decision_trace_id: str
    source_mode: str
    extracted_schema: dict
    normalized_payload: dict
    requirements: dict
    target_profile: dict
    readiness: dict
    template_candidates: list
    selected_template: dict
    raw_intake_snapshot: dict = field(default_factory=dict)
    channel: str = ""
    prepared_catalog_state: object = None


@dataclass(frozen=True)
class PreparedCatalogState:
    cache_key: str
    raw_products: tuple
    normalized_products: tuple
    eligible_products: tuple
    catalog_validation_result: dict
    category_subsets: dict
    retrieval_assets_by_subset: dict
    currency_fallback_used: bool
    catalog_source_snapshot: dict
    store_scope_applied: bool = False


@dataclass(frozen=True)
class RecommendationCoreResult:
    ranking_deferred: bool
    shortlisted_product_ids: list
    ranked_recommendations: list
    fallback_reason: str
    stage_timings_ms: dict


class RecommendationContextBuilder:
    def __init__(self, service):
        self.service = service

    def prepare_from_raw_payload(self, payload, feature_flags=None, decision_trace_id=None):
        payload = dict(payload or {})
        extracted_schema = dict(self.service._extract_schema(payload))
        return self.prepare_from_extracted_schema(
            payload=payload,
            extracted_schema=extracted_schema,
            feature_flags=feature_flags,
            decision_trace_id=decision_trace_id,
            source_mode="raw_payload",
        )

    def prepare_from_extracted_schema(
        self,
        payload,
        extracted_schema,
        feature_flags=None,
        decision_trace_id=None,
        source_mode="extracted_schema",
        prepared_catalog_state=None,
    ):
        payload = dict(payload or {})
        extracted_schema = dict(extracted_schema or {})
        # Planner-state follow-ups carry normalized spec fields like
        # requested_ram_gb/requested_storage_gb. Preserve them by backfilling
        # the extractor-facing aliases before rebuilding the payload.
        if extracted_schema.get("requested_ram_gb") is not None and extracted_schema.get("requested_ram") in (None, ""):
            extracted_schema["requested_ram"] = extracted_schema.get("requested_ram_gb")
        if extracted_schema.get("requested_storage_gb") is not None and extracted_schema.get("requested_storage") in (None, ""):
            extracted_schema["requested_storage"] = extracted_schema.get("requested_storage_gb")
        if payload.get("requested_ram_gb") is not None and payload.get("requested_ram") in (None, ""):
            payload["requested_ram"] = payload.get("requested_ram_gb")
        if payload.get("requested_storage_gb") is not None and payload.get("requested_storage") in (None, ""):
            payload["requested_storage"] = payload.get("requested_storage_gb")
        normalized_payload = self.service.extraction_service.build_procurement_payload(extracted_schema, payload)
        requirements = self.service.intake_service.normalize(normalized_payload)
        target_profile = self.service.rules_engine.build_target_profile(requirements)
        readiness = self.service.clarification_service.assess(requirements)
        template_candidates = self.service.template_service.select_candidates(requirements, target_profile)
        selected_template = self.service._selected_template(template_candidates)
        prepared_catalog_state = prepared_catalog_state or self.service._resolve_prepared_catalog_state(requirements)
        return PreparedProcurementContext(
            decision_trace_id=decision_trace_id or str(uuid4()),
            source_mode=str(source_mode or "extracted_schema"),
            extracted_schema=extracted_schema,
            normalized_payload=normalized_payload,
            requirements=requirements,
            target_profile=target_profile,
            readiness=readiness,
            template_candidates=template_candidates,
            selected_template=selected_template,
            raw_intake_snapshot=self.service._build_raw_intake_snapshot(payload),
            channel=str(payload.get("channel") or requirements.get("channel") or "").strip(),
            prepared_catalog_state=prepared_catalog_state,
        )

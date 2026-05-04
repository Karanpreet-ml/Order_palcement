# import os
# from concurrent.futures import ThreadPoolExecutor
# from time import perf_counter
# from uuid import uuid4

# from ...catalog.services.normalization import normalize_product_document
# from ...catalog.services.repository import build_runtime_catalog_repository
# from ...catalog.services.semantic_retriever import SemanticProductRetriever

# from .explanations import ProcurementExplanationService
# from .feature_flags import ProcurementFeatureFlagService
# from .followup_generation import AdaptiveFollowUpService
# from .intake import RequirementIntakeService
# from .observability import ProcurementRuntimeObservabilityService
# from .policy import ProcurementPolicyService
# from .ranking import ProductRankingService
# from .recommendation_context import (
#     PreparedCatalogState,
#     PreparedProcurementContext,
#     RecommendationContextBuilder,
#     RecommendationCoreResult,
# )
# from .recommendation_core import RecommendationCoreEngine
# from .recommendation_presenter import RecommendationPresenter
# from .review_support import ProcurementReviewSupportService
# from .requirement_extraction import RequirementExtractionService
# from .rules_engine import ProcurementRulesEngine
# from .clarification import ProcurementClarificationService
# from .bundle_service import ProcurementBundleService
# from .compatibility import ProcurementCompatibilityService
# from .config_service import ProcurementConfigService
# from .multi_intent import ProcurementMultiIntentService
# from .multi_intent_policy import ProcurementMultiIntentPolicyService
# from .template_service import ProcurementTemplateService


# ENGINE_VERSION = "phase1-v8"

# class ProcurementRecommendationService:
#     _persistence_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="procurement-persist")

#     def __init__(
#         self,
#         catalog_repository=None,
#         config_service=None,
#         intake_service=None,
#         rules_engine=None,
#         ranking_service=None,
#         policy_service=None,
#         compatibility_service=None,
#         explanation_service=None,
#         clarification_service=None,
#         extraction_service=None,
#         semantic_retriever=None,
#         followup_service=None,
#         feature_flag_service=None,
#         multi_intent_service=None,
#         multi_intent_policy_service=None,
#         observability_service=None,
#         bundle_service=None,
#         template_service=None,
#         review_support_service=None,
#     ):
#         self.catalog_repository = catalog_repository or build_runtime_catalog_repository()
#         self.config_service = config_service or ProcurementConfigService()
#         self.intake_service = intake_service or RequirementIntakeService()
#         self.rules_engine = rules_engine or ProcurementRulesEngine(config_service=self.config_service)
#         self.ranking_service = ranking_service or ProductRankingService(config_service=self.config_service)
#         self.policy_service = policy_service or ProcurementPolicyService(config_service=self.config_service)
#         self.compatibility_service = compatibility_service or ProcurementCompatibilityService(config_service=self.config_service)
#         self.explanation_service = explanation_service or ProcurementExplanationService(config_service=self.config_service)
#         self.clarification_service = clarification_service or ProcurementClarificationService(config_service=self.config_service)
#         self.extraction_service = extraction_service or RequirementExtractionService()
#         self.semantic_retriever = semantic_retriever or SemanticProductRetriever()
#         self.followup_service = followup_service or AdaptiveFollowUpService()
#         self.feature_flag_service = feature_flag_service or ProcurementFeatureFlagService()
#         self.multi_intent_service = multi_intent_service or ProcurementMultiIntentService(
#             extraction_service=self.extraction_service
#         )
#         self.multi_intent_policy_service = multi_intent_policy_service or ProcurementMultiIntentPolicyService()
#         self.observability_service = observability_service or ProcurementRuntimeObservabilityService(
#             config_service=self.config_service
#         )
#         self.bundle_service = bundle_service or ProcurementBundleService(
#             compatibility_service=self.compatibility_service
#         )
#         self.template_service = template_service or ProcurementTemplateService(config_service=self.config_service)
#         self.review_support_service = review_support_service or ProcurementReviewSupportService()
#         self._prepared_catalog_state_cache = {}
#         self.context_builder = RecommendationContextBuilder(self)
#         self.core_engine = RecommendationCoreEngine(self)
#         self.presenter = RecommendationPresenter(self)

#     def has_minimum_context(self, payload):
#         requirements = self.intake_service.normalize(payload)
#         readiness = self.clarification_service.assess(requirements)
#         return bool(requirements.get("budget") is not None and not self.clarification_service.should_defer_ranking(readiness))

#     def _new_top_level_timings(self, source_mode=""):
#         prepare_ms = {"total_ms": 0.0}
#         if source_mode:
#             prepare_ms["source_mode"] = str(source_mode)
#         return {
#             "prepare_ms": prepare_ms,
#             "core_ms": {
#                 "total_ms": 0.0,
#                 "multi_intent_detect_ms": 0.0,
#                 "catalog_fetch_ms": 0.0,
#                 "compatibility_ms": 0.0,
#                 "policy_ms": 0.0,
#                 "ranking_ms": 0.0,
#                 "explanations_ms": 0.0,
#                 "response_assembly_ms": 0.0,
#             },
#             "presentation_ms": {
#                 "assembly_ms": 0.0,
#                 "question_generation_ms": 0.0,
#                 "narrative_ms": 0.0,
#                 "persistence_dispatch_ms": 0.0,
#                 "total_ms": 0.0,
#             },
#             "pipeline_ms": {"total_ms": 0.0},
#         }

#     def _finalize_top_level_timings(self, top_level_timings, pipeline_started_at=None, response=None):
#         top_level_timings = dict(top_level_timings or {})
#         core_ms = dict(top_level_timings.get("core_ms") or {})
#         presentation_ms = dict(top_level_timings.get("presentation_ms") or {})
#         stage_timings = dict((((response or {}).get("meta") or {}).get("stage_timings_ms") or {}))
#         core_ms["catalog_fetch_ms"] = round(float(stage_timings.get("catalog_fetch_ms") or core_ms.get("catalog_fetch_ms") or 0.0), 2)
#         core_ms["compatibility_ms"] = round(float(stage_timings.get("compatibility_ms") or core_ms.get("compatibility_ms") or 0.0), 2)
#         core_ms["policy_ms"] = round(float(stage_timings.get("policy_ms") or core_ms.get("policy_ms") or 0.0), 2)
#         core_ms["ranking_ms"] = round(float(stage_timings.get("ranking_ms") or core_ms.get("ranking_ms") or 0.0), 2)
#         core_ms["explanations_ms"] = round(float(stage_timings.get("explanations_ms") or core_ms.get("explanations_ms") or 0.0), 2)
#         core_ms["response_assembly_ms"] = round(
#             float(stage_timings.get("response_assembly_ms") or core_ms.get("response_assembly_ms") or 0.0),
#             2,
#         )
#         top_level_timings["core_ms"] = core_ms
#         question_generation_ms = float(stage_timings.get("question_generation_ms") or presentation_ms.get("question_generation_ms") or 0.0)
#         presentation_ms["question_generation_ms"] = round(question_generation_ms, 2)
#         presentation_ms["total_ms"] = round(
#             sum(
#                 float(presentation_ms.get(key) or 0.0)
#                 for key in ("assembly_ms", "question_generation_ms", "narrative_ms", "persistence_dispatch_ms")
#             ),
#             2,
#         )
#         top_level_timings["presentation_ms"] = presentation_ms
#         if pipeline_started_at is not None:
#             self._mark_stage(top_level_timings.setdefault("pipeline_ms", {}), "total_ms", pipeline_started_at)
#         return top_level_timings

#     def recommend(self, payload, user_id="", business_id="", persist=True):
#         payload = dict(payload or {})
#         feature_flags = dict(self.feature_flag_service.get_flags())
#         if str(payload.get("channel") or "").strip().lower() == "websocket":
#             persist = False
#         pipeline_started_at = perf_counter()
#         top_level_timings = self._new_top_level_timings()

#         prepare_started_at = perf_counter()
#         prepared = self.prepare_from_raw_payload(payload, feature_flags=feature_flags)
#         self._mark_stage(top_level_timings["prepare_ms"], "total_ms", prepare_started_at)

#         detect_started_at = perf_counter()
#         multi_intent_result = self.multi_intent_service.detect(payload, prepared.extracted_schema)
#         self._mark_stage(top_level_timings["core_ms"], "multi_intent_detect_ms", detect_started_at)
#         if multi_intent_result.get("is_multi_intent"):
#             response = self._recommend_multi_intent(
#                 payload=payload,
#                 multi_intent_result=multi_intent_result,
#                 extracted_schema=prepared.extracted_schema,
#                 feature_flags=feature_flags,
#                 user_id=user_id,
#                 business_id=business_id,
#                 persist=persist,
#                 prepared_context=prepared,
#                 top_level_timings=top_level_timings,
#             )
#         else:
#             response = self._recommend_single(
#                 payload=payload,
#                 extracted_schema=prepared.extracted_schema,
#                 prepared_context=prepared,
#                 feature_flags=feature_flags,
#                 user_id=user_id,
#                 business_id=business_id,
#                 persist=persist,
#                 top_level_timings=top_level_timings,
#             )
#         top_level_timings = self._finalize_top_level_timings(
#             top_level_timings,
#             pipeline_started_at=pipeline_started_at,
#             response=response,
#         )
#         response.setdefault("meta", {})
#         response["meta"]["top_level_timings_ms"] = top_level_timings
#         return response

#     def prepare_from_raw_payload(self, payload, feature_flags=None, decision_trace_id=None):
#         return self.context_builder.prepare_from_raw_payload(
#             payload=payload,
#             feature_flags=feature_flags,
#             decision_trace_id=decision_trace_id,
#         )

#     def prepare_from_extracted_schema(
#         self,
#         payload,
#         extracted_schema,
#         feature_flags=None,
#         decision_trace_id=None,
#         source_mode="extracted_schema",
#         prepared_catalog_state=None,
#     ):
#         return self.context_builder.prepare_from_extracted_schema(
#             payload=payload,
#             extracted_schema=extracted_schema,
#             feature_flags=feature_flags,
#             decision_trace_id=decision_trace_id,
#             source_mode=source_mode,
#             prepared_catalog_state=prepared_catalog_state,
#         )

#     def recommend_prepared_context(
#         self,
#         prepared_context,
#         feature_flags=None,
#         user_id="",
#         business_id="",
#         persist=True,
#         capture_runtime_observability=True,
#     ):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         pipeline_started_at = perf_counter()
#         top_level_timings = self._new_top_level_timings(source_mode=prepared_context.source_mode)
#         if str(prepared_context.channel or "").strip().lower() == "websocket":
#             persist = False
#         detect_started_at = perf_counter()
#         multi_intent_result = self.core_engine.detect_multi_intent(
#             prepared_context.normalized_payload,
#             prepared_context.extracted_schema,
#         )
#         self._mark_stage(top_level_timings["core_ms"], "multi_intent_detect_ms", detect_started_at)
#         if multi_intent_result.get("is_multi_intent"):
#             response = self._recommend_multi_intent(
#                 payload=prepared_context.normalized_payload,
#                 multi_intent_result=multi_intent_result,
#                 extracted_schema=prepared_context.extracted_schema,
#                 prepared_context=prepared_context,
#                 feature_flags=feature_flags,
#                 user_id=user_id,
#                 business_id=business_id,
#                 persist=persist,
#                 top_level_timings=top_level_timings,
#             )
#         else:
#             response = self._recommend_single_from_prepared(
#                 prepared_context=prepared_context,
#                 feature_flags=feature_flags,
#                 user_id=user_id,
#                 business_id=business_id,
#                 persist=persist,
#                 capture_runtime_observability=capture_runtime_observability,
#                 top_level_timings=top_level_timings,
#             )
#         top_level_timings = self._finalize_top_level_timings(
#             top_level_timings,
#             pipeline_started_at=pipeline_started_at,
#             response=response,
#         )
#         response.setdefault("meta", {})
#         response["meta"]["top_level_timings_ms"] = top_level_timings
#         return response

#     def recommend_from_chat_preferences(self, chat_preferences, store_id="", persist=False):
#         chat_preferences = dict(chat_preferences or {})
#         payload = {
#             "store_id": chat_preferences.get("store_id") or store_id or "",
#             "channel": "websocket",
#             "currency": chat_preferences.get("currency", "INR"),
#             "category": chat_preferences.get("category") or chat_preferences.get("preferred_category"),
#             "industry": chat_preferences.get("industry"),
#             "business_type": chat_preferences.get("business_type"),
#             "team_size": chat_preferences.get("team_size"),
#             "workload_types": chat_preferences.get("workloads") or chat_preferences.get("workload_types"),
#             "application_signals": chat_preferences.get("application_signals") or [],
#             "capability_tags": chat_preferences.get("capability_tags") or [],
#             "budget": chat_preferences.get("budget"),
#             "budget_scope": chat_preferences.get("budget_scope"),
#             "growth_expectation": chat_preferences.get("growth_expectation"),
#             "existing_infrastructure": chat_preferences.get("existing_infrastructure") or [],
#             "preferred_manufacturers": chat_preferences.get("preferred_manufacturers") or [],
#             "blocked_manufacturers": chat_preferences.get("blocked_manufacturers") or [],
#             "preferred_sellers": chat_preferences.get("preferred_sellers") or [],
#             "blocked_sellers": chat_preferences.get("blocked_sellers") or [],
#             "requested_ram": chat_preferences.get("specifications.ram_size"),
#             "requested_storage": chat_preferences.get("specifications.storage_size"),
#             "requested_ram_is_minimum": chat_preferences.get("requested_ram_is_minimum"),
#             "requested_storage_is_minimum": chat_preferences.get("requested_storage_is_minimum"),
#             "minimum_warranty_years": chat_preferences.get("minimum_warranty_years"),
#             "required_port_count": chat_preferences.get("required_port_count"),
#             "required_throughput_mbps": chat_preferences.get("required_throughput_mbps"),
#             "required_duplex_printing": chat_preferences.get("required_duplex_printing"),
#             "required_scanner": chat_preferences.get("required_scanner"),
#             "min_print_speed_ppm": chat_preferences.get("min_print_speed_ppm"),
#             "required_printer_type": chat_preferences.get("required_printer_type"),
#             "required_print_technology": chat_preferences.get("required_print_technology"),
#             "required_color_output": chat_preferences.get("required_color_output"),
#             "min_monthly_duty_cycle_pages": chat_preferences.get("min_monthly_duty_cycle_pages"),
#             "required_automatic_document_feeder": chat_preferences.get("required_automatic_document_feeder"),
#             "required_paper_sizes": chat_preferences.get("required_paper_sizes"),
#             "required_network_roles": chat_preferences.get("required_network_roles"),
#             "required_vpn_user_capacity": chat_preferences.get("required_vpn_user_capacity"),
#             "required_virtualization_ready": chat_preferences.get("required_virtualization_ready"),
#             "required_virtualization_platforms": chat_preferences.get("required_virtualization_platforms"),
#             "max_rack_units": chat_preferences.get("max_rack_units"),
#             "max_power_draw_watts": chat_preferences.get("max_power_draw_watts"),
#             "battery_life_hours_min": chat_preferences.get("battery_life_hours_min"),
#             "cpu_preference": chat_preferences.get("cpu_preference"),
#             "gpu_requirement": chat_preferences.get("gpu_requirement"),
#             "screen_size_preference": chat_preferences.get("screen_size_preference"),
#             "weight_kg_max": chat_preferences.get("weight_kg_max"),
#             "warranty_type_preference": chat_preferences.get("warranty_type_preference"),
#             "performance_priority": chat_preferences.get("performance_priority"),
#             "portability_need": chat_preferences.get("portability_need"),
#             "support_expectation": chat_preferences.get("support_expectation"),
#             "availability_need": chat_preferences.get("availability_need"),
#             "require_returnable": chat_preferences.get("require_returnable"),
#             "quantity": chat_preferences.get("quantity"),
#             "purchase_scope": chat_preferences.get("purchase_scope"),
#             "timeline": chat_preferences.get("timeline"),
#             "raw_chat": chat_preferences.get("raw_chat", ""),
#             "notes": chat_preferences.get("notes", ""),
#             "extracted_schema": dict(chat_preferences),
#         }
#         prepared_context = self.prepare_from_extracted_schema(
#             payload=payload,
#             extracted_schema=dict(chat_preferences),
#             source_mode="chat_preferences",
#         )
#         return self.recommend_prepared_context(prepared_context, persist=persist)

#     def _recommend_single(
#         self,
#         payload,
#         extracted_schema=None,
#         prepared_context=None,
#         feature_flags=None,
#         user_id="",
#         business_id="",
#         persist=True,
#         decision_trace_id=None,
#         capture_runtime_observability=True,
#         top_level_timings=None,
#     ):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         payload = dict(payload or {})
#         top_level_timings = top_level_timings or self._new_top_level_timings()
#         if prepared_context is None:
#             prepare_started_at = perf_counter()
#             prepared_context = self.prepare_from_extracted_schema(
#                 payload=payload,
#                 extracted_schema=dict(extracted_schema or self._extract_schema(payload)),
#                 feature_flags=feature_flags,
#                 decision_trace_id=decision_trace_id,
#             )
#             self._mark_stage(top_level_timings["prepare_ms"], "total_ms", prepare_started_at)
#         return self._recommend_single_from_prepared(
#             prepared_context=prepared_context,
#             feature_flags=feature_flags,
#             user_id=user_id,
#             business_id=business_id,
#             persist=persist,
#             capture_runtime_observability=capture_runtime_observability,
#             top_level_timings=top_level_timings,
#         )

#     def _recommend_single_from_prepared(
#         self,
#         prepared_context,
#         feature_flags=None,
#         user_id="",
#         business_id="",
#         persist=True,
#         capture_runtime_observability=True,
#         top_level_timings=None,
#     ):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         top_level_timings = top_level_timings or self._new_top_level_timings()
#         started_at = self.observability_service.start_timer() if capture_runtime_observability else None
#         core_started_at = perf_counter()
#         core_result, debug_trace = self.core_engine.run(
#             prepared_context,
#             feature_flags=feature_flags,
#             defer_explanations=bool(prepared_context.normalized_payload.get("_defer_explanations")),
#         )
#         self._mark_stage(top_level_timings["core_ms"], "total_ms", core_started_at)
#         assembly_started_at = perf_counter()
#         response = self.presenter.assemble(
#             prepared_context=prepared_context,
#             core_result=core_result,
#             debug_trace=debug_trace,
#             feature_flags=feature_flags,
#             started_at=started_at,
#             capture_runtime_observability=capture_runtime_observability,
#         )
#         self._mark_stage(top_level_timings["presentation_ms"], "assembly_ms", assembly_started_at)
#         question_generation_ms = float(
#             (((response.get("meta") or {}).get("stage_timings_ms") or {}).get("question_generation_ms"))
#             or 0.0
#         )
#         top_level_timings["presentation_ms"]["question_generation_ms"] = round(question_generation_ms, 2)
#         if question_generation_ms:
#             top_level_timings["presentation_ms"]["assembly_ms"] = max(
#                 round(float(top_level_timings["presentation_ms"]["assembly_ms"]) - question_generation_ms, 2),
#                 0.0,
#             )
#         narrative_started_at = perf_counter()
#         response = self.presenter.enrich(
#             prepared_context=prepared_context,
#             response=response,
#             feature_flags=feature_flags,
#         )
#         self._mark_stage(top_level_timings["presentation_ms"], "narrative_ms", narrative_started_at)
#         persistence_started_at = perf_counter()
#         if persist:
#             self._dispatch_persistence_from_outputs(
#                 prepared_context=prepared_context,
#                 response=response,
#                 user_id=user_id,
#                 business_id=business_id,
#             )
#         self._mark_stage(top_level_timings["presentation_ms"], "persistence_dispatch_ms", persistence_started_at)
#         top_level_timings["presentation_ms"]["total_ms"] = round(
#             sum(
#                 float(top_level_timings["presentation_ms"].get(key) or 0.0)
#                 for key in ("assembly_ms", "question_generation_ms", "narrative_ms", "persistence_dispatch_ms")
#             ),
#             2,
#         )
#         return response

#     def recommend_from_state(
#         self,
#         state: dict,
#         user_id="",
#         business_id="",
#         persist=False,
#     ):
#         state = dict(state or {})
#         payload = dict(state)
#         payload.setdefault("channel", "websocket")
#         payload.setdefault("_defer_explanations", True)
#         prepared_context = self.prepare_from_extracted_schema(
#             payload=payload,
#             extracted_schema=state,
#             source_mode="planner_state",
#         )
#         return self.recommend_prepared_context(
#             prepared_context,
#             user_id=user_id,
#             business_id=business_id,
#             persist=persist,
#         )

#     def _build_budget_fit_summary(self, requirements, recommendations):
#         budget = requirements.get("budget")
#         if budget is None:
#             return {
#                 "budget_present": False,
#                 "within_budget_count": 0,
#                 "over_budget_count": 0,
#                 "no_exact_budget_fit": False,
#             }
#         quantity = requirements.get("quantity") or requirements.get("team_size") or 1
#         budget_scope = requirements.get("budget_scope")
#         within_budget_count = 0
#         over_budget_count = 0
#         for recommendation in list(recommendations or []):
#             price = recommendation.get("price")
#             total_cost = recommendation.get("estimated_total_cost")
#             reference = self.ranking_service._budget_reference(price, budget_scope, quantity, total_cost)
#             if reference is None:
#                 continue
#             if reference <= budget:
#                 within_budget_count += 1
#             else:
#                 over_budget_count += 1
#         return {
#             "budget_present": True,
#             "within_budget_count": within_budget_count,
#             "over_budget_count": over_budget_count,
#             "no_exact_budget_fit": bool(recommendations) and within_budget_count == 0,
#         }

#     def _prefix_no_exact_budget_fit_summary(self, summary, requirements, recommendations):
#         if not recommendations:
#             return str(summary or "").strip()
#         currency = str(requirements.get("currency") or "INR").strip() or "INR"
#         budget = requirements.get("budget")
#         budget_scope = str(requirements.get("budget_scope") or "budget").replace("_", " ").strip() or "budget"
#         base = f"No exact in-catalog fit was found within the stated {budget_scope} budget of {budget} {currency}. Showing the closest stretch options and their trade-offs."
#         summary = str(summary or "").strip()
#         if not summary:
#             return base
#         if summary.lower().startswith("no exact in-catalog fit was found within the stated"):
#             return summary
#         return f"{base} {summary}".strip()

#     def _mark_stage(self, stage_timings, stage_name, started_at):
#         stage_timings[stage_name] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)

#     def _set_stage_total(self, stage_timings, stage_name, values):
#         values = [float(value or 0.0) for value in list(values or [])]
#         stage_timings[stage_name] = round(sum(values), 2)

#     def _hydrate_stage_aliases(self, stage_timings):
#         stage_timings = dict(stage_timings or {})
#         self._set_stage_total(
#             stage_timings,
#             "catalog_fetch_ms",
#             [
#                 stage_timings.get("catalog_state_access_ms"),
#                 stage_timings.get("category_subset_resolution_ms"),
#                 stage_timings.get("candidate_selection_ms"),
#             ],
#         )
#         self._set_stage_total(
#             stage_timings,
#             "compatibility_policy_ms",
#             [
#                 stage_timings.get("compatibility_ms"),
#                 stage_timings.get("policy_ms"),
#             ],
#         )
#         return stage_timings

#     def run_recommendation_core(self, prepared_context, feature_flags=None, defer_explanations=False):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         requirements = dict(prepared_context.requirements or {})
#         target_profile = dict(prepared_context.target_profile or {})
#         readiness = dict(prepared_context.readiness or {})
#         prepared_catalog_state = prepared_context.prepared_catalog_state or self._resolve_prepared_catalog_state(requirements)
#         stage_timings = {}
#         ranking_deferred = self.clarification_service.should_defer_ranking(readiness)
#         deferred_reason = ""
#         normalized_products = []
#         candidate_ids = []
#         retrieval_result = {"candidate_ids": [], "scored_candidates": [], "fallback_reason": None}
#         compatibility_result = {"eligible_products": [], "rejected_products": [], "summary": {}, "reports_by_product_id": {}}
#         policy_result = {"eligible_products": [], "rejected_products": [], "summary": {}}
#         rankable_products = []
#         recommendations = []
#         fallback_reason = ""
#         catalog_validation_result = {"eligible_products": [], "rejected_products": [], "summary": {}}
#         raw_products = []
#         all_normalized_products = []
#         currency_fallback_used = False
#         catalog_source_snapshot = {}
#         store_scope_applied = False

#         if ranking_deferred:
#             deferred_reason = "blocking_clarification_required"
#             fallback_reason = deferred_reason
#         else:
#             stage_started_at = perf_counter()
#             raw_products = list(prepared_catalog_state.raw_products or [])
#             all_normalized_products = list(prepared_catalog_state.normalized_products or [])
#             catalog_validation_result = dict(prepared_catalog_state.catalog_validation_result or {})
#             currency_fallback_used = bool(prepared_catalog_state.currency_fallback_used)
#             catalog_source_snapshot = dict(prepared_catalog_state.catalog_source_snapshot or {})
#             store_scope_applied = bool(prepared_catalog_state.store_scope_applied)
#             self._mark_stage(stage_timings, "catalog_state_access_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             category_filtered_products, subset_key = self._resolve_category_subset_from_state(
#                 prepared_catalog_state,
#                 target_profile.get("categories"),
#             )
#             self._mark_stage(stage_timings, "category_subset_resolution_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             if feature_flags.get("semantic_retrieval", True):
#                 retrieval_assets = (prepared_catalog_state.retrieval_assets_by_subset or {}).get(subset_key)
#                 if retrieval_assets is None and subset_key != "__all__":
#                     retrieval_assets = self.semantic_retriever.build_retrieval_assets(category_filtered_products)
#                 retrieval_result = self.semantic_retriever.retrieve_candidates_from_assets(
#                     retrieval_assets,
#                     requirements,
#                     target_profile,
#                     top_k=40,
#                     allow_broadening=feature_flags.get("retrieval_broadening", True),
#                 )
#                 candidate_ids = list(retrieval_result.get("candidate_ids") or [])
#                 normalized_products = self._filter_normalized_products(
#                     category_filtered_products,
#                     None,
#                     candidate_ids,
#                 )
#             else:
#                 retrieval_result = self._deterministic_candidate_pool(category_filtered_products, top_k=40)
#                 candidate_ids = list(retrieval_result.get("candidate_ids") or [])
#                 normalized_products = category_filtered_products[:40]
#             self._mark_stage(stage_timings, "candidate_selection_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             if feature_flags.get("compatibility_filtering", True):
#                 compatibility_result = self.compatibility_service.evaluate(
#                     normalized_products,
#                     requirements,
#                     target_profile,
#                 )
#             else:
#                 compatibility_result = self._compatibility_bypass(normalized_products)
#             self._mark_stage(stage_timings, "compatibility_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             policy_result = self.policy_service.apply_filters(
#                 compatibility_result.get("eligible_products") or [],
#                 requirements,
#                 target_profile,
#             )
#             rankable_products = policy_result.get("eligible_products") or []
#             self._mark_stage(stage_timings, "policy_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             recommendations = self.ranking_service.rank_products(
#                 rankable_products,
#                 requirements,
#                 target_profile,
#             )
#             self._mark_stage(stage_timings, "ranking_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             if not defer_explanations:
#                 recommendations = self.explanation_service.enrich_recommendations(
#                     requirements,
#                     target_profile,
#                     recommendations,
#                     allow_llm=feature_flags.get("explanation_llm", False),
#                 )
#             self._mark_stage(stage_timings, "explanations_ms", stage_started_at)

#             fallback_reason = str(retrieval_result.get("fallback_reason") or "")
#             if not recommendations:
#                 if compatibility_result.get("rejected_products") and not compatibility_result.get("eligible_products"):
#                     fallback_reason = "compatibility_blocked_all"
#                 elif policy_result.get("rejected_products") and not rankable_products:
#                     fallback_reason = "policy_rejected_all"
#                 elif not rankable_products:
#                     fallback_reason = fallback_reason or "no_exact_fit"

#         stage_timings = self._hydrate_stage_aliases(stage_timings)

#         debug_trace = {
#             "deferred_reason": deferred_reason,
#             "retrieval_result": retrieval_result,
#             "compatibility_result": compatibility_result,
#             "policy_result": policy_result,
#             "catalog_validation_result": catalog_validation_result,
#             "raw_products": raw_products,
#             "all_normalized_products": all_normalized_products,
#             "currency_fallback_used": currency_fallback_used,
#             "catalog_source_snapshot": catalog_source_snapshot,
#             "store_scope_applied": store_scope_applied,
#             "rankable_products": rankable_products,
#             "prepared_catalog_cache_key": getattr(prepared_catalog_state, "cache_key", ""),
#         }
#         return RecommendationCoreResult(
#             ranking_deferred=bool(ranking_deferred),
#             shortlisted_product_ids=list(candidate_ids),
#             ranked_recommendations=list(recommendations),
#             fallback_reason=str(fallback_reason or ""),
#             stage_timings_ms=stage_timings,
#         ), debug_trace

#     def assemble_response(
#         self,
#         prepared_context,
#         core_result,
#         debug_trace,
#         feature_flags=None,
#         started_at=None,
#         capture_runtime_observability=True,
#     ):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         requirements = dict(prepared_context.requirements or {})
#         target_profile = dict(prepared_context.target_profile or {})
#         readiness = dict(prepared_context.readiness or {})
#         recommendations = [dict(item) for item in list(core_result.ranked_recommendations or [])]
#         stage_timings = dict(core_result.stage_timings_ms or {})
#         stage_started_at = perf_counter()
#         for recommendation in recommendations:
#             recommendation["buy_url"] = self._build_buy_url(recommendation.get("product_id"))

#         compatibility_result = dict(debug_trace.get("compatibility_result") or {})
#         policy_result = dict(debug_trace.get("policy_result") or {})
#         retrieval_result = dict(debug_trace.get("retrieval_result") or {})
#         catalog_validation_result = dict(debug_trace.get("catalog_validation_result") or {})
#         raw_products = list(debug_trace.get("raw_products") or [])
#         all_normalized_products = list(debug_trace.get("all_normalized_products") or [])
#         currency_fallback_used = bool(debug_trace.get("currency_fallback_used"))
#         catalog_source_snapshot = dict(debug_trace.get("catalog_source_snapshot") or {})
#         store_scope_applied = bool(debug_trace.get("store_scope_applied"))
#         deferred_reason = str(debug_trace.get("deferred_reason") or "")
#         rankable_products = list(debug_trace.get("rankable_products") or [])

#         summary = (
#             target_profile.get("summary")
#             if core_result.ranking_deferred
#             else self.explanation_service.build_summary(requirements, target_profile, recommendations)
#         )
#         budget_fit_summary = self._build_budget_fit_summary(requirements, recommendations)
#         if budget_fit_summary.get("no_exact_budget_fit"):
#             summary = self._prefix_no_exact_budget_fit_summary(summary, requirements, recommendations)
#         expert_review_reason = self._expert_review_reason(
#             readiness,
#             core_result.ranking_deferred,
#             core_result.fallback_reason,
#             compatibility_result,
#             recommendations,
#         )
#         expert_review_reason = self._apply_template_review_reason(prepared_context.selected_template, expert_review_reason)
#         clarification_required_reasons = self._clarification_required_reasons(readiness)
#         decision_policy_profile = self.config_service.get_decision_policy_profile()
#         recommendation_mode = self._recommendation_mode(
#             readiness=readiness,
#             recommendations=recommendations,
#             fallback_reason=core_result.fallback_reason,
#             expert_review_reason=expert_review_reason,
#             clarification_required_reasons=clarification_required_reasons,
#             candidate_pool_size=len(rankable_products),
#         )
#         recommendation_mode = self._apply_template_selection_mode(prepared_context.selected_template, recommendation_mode)
#         requirements["review_state"] = self.review_support_service.enrich_review_state(
#             requirements=requirements,
#             readiness=readiness,
#             template_candidates=prepared_context.template_candidates,
#             recommendation_mode=recommendation_mode,
#         )
#         check_requirement_summary = self.review_support_service.build_check_requirement_summary(
#             requirements=requirements,
#             readiness=readiness,
#             template_candidates=prepared_context.template_candidates,
#             recommendation_mode=recommendation_mode,
#         )
#         editable_inferred_values = self.review_support_service.build_editable_inferred_values(requirements)
#         catalog_observability = self._build_catalog_observability(
#             raw_products=raw_products,
#             normalized_products=all_normalized_products,
#             catalog_validation_result=catalog_validation_result,
#             requirements=requirements,
#             currency_fallback_used=currency_fallback_used,
#             catalog_source_snapshot=catalog_source_snapshot,
#             store_scope_applied=store_scope_applied,
#         )
#         self._mark_stage(stage_timings, "response_assembly_ms", stage_started_at)
#         response = {
#             "decision_trace_id": prepared_context.decision_trace_id,
#             "requirements": requirements,
#             "field_state": requirements.get("field_state") or {},
#             "field_source": requirements.get("field_source") or {},
#             "assumption_severity": requirements.get("assumption_severity") or {},
#             "recommendation_mode": recommendation_mode,
#             "clarification_required_reasons": clarification_required_reasons,
#             "review_state": requirements.get("review_state") or {},
#             "check_requirement_summary": check_requirement_summary,
#             "editable_inferred_values": editable_inferred_values,
#             "template_candidates": prepared_context.template_candidates,
#             "target_profile": target_profile,
#             "recommendations": recommendations,
#             "summary": summary,
#             "assumptions": self.explanation_service.build_assumptions(requirements),
#             "comparison": "",
#             "extracted_schema": prepared_context.extracted_schema,
#             "readiness": readiness,
#             "compatibility_report": self._build_compatibility_report(compatibility_result),
#             "fallback_reason": core_result.fallback_reason or ("no_exact_fit" if budget_fit_summary.get("no_exact_budget_fit") else ""),
#             "expert_review_eligible": bool(expert_review_reason) and feature_flags.get("expert_review", True),
#             "meta": {
#                 "engine_version": ENGINE_VERSION,
#                 "config_versions": self.config_service.get_versions(),
#                 "config_bundle_version": self.config_service.get_bundle_version(),
#                 "feature_flags": feature_flags,
#                 "source_product_count": len(raw_products),
#                 "catalog_validation_summary": catalog_validation_result.get("summary") or {},
#                 "catalog_validation_rejections_sample": (catalog_validation_result.get("rejected_products") or [])[:5],
#                 "eligible_product_count": len(rankable_products),
#                 "recommended_count": len(recommendations),
#                 "budget_fit_summary": budget_fit_summary,
#                 "catalog_observability": catalog_observability,
#                 "filtered_categories": target_profile.get("categories") or [],
#                 "semantic_candidate_ids": list(core_result.shortlisted_product_ids or [])[:10],
#                 "semantic_candidate_count": len(list(core_result.shortlisted_product_ids or [])),
#                 "retrieval_summary": {
#                     "candidate_count": len(list(core_result.shortlisted_product_ids or [])),
#                     "fallback_reason": retrieval_result.get("fallback_reason"),
#                     "top_candidates": (retrieval_result.get("scored_candidates") or [])[:10],
#                 },
#                 "compatibility_summary": compatibility_result.get("summary") or {},
#                 "compatibility_rejections_sample": (compatibility_result.get("rejected_products") or [])[:5],
#                 "policy_summary": policy_result.get("summary") or {},
#                 "policy_rejections_sample": (policy_result.get("rejected_products") or [])[:5],
#                 "applied_rules_count": len(target_profile.get("applied_rules") or []),
#                 "ranking_deferred": core_result.ranking_deferred,
#                 "ranking_deferred_reason": deferred_reason,
#                 "expert_review_reason": expert_review_reason,
#                 "decision_policy_profile": decision_policy_profile,
#                 "stage_timings_ms": stage_timings,
#             },
#         }
#         if not readiness.get("is_ready"):
#             question_started_at = perf_counter()
#             response["next_question"] = (
#                 str(readiness.get("next_question") or "").strip()
#                 or self.clarification_service._context_aware_prompt(
#                     readiness.get("highest_priority_missing_field"),
#                     requirements,
#                 )
#             )
#             self._mark_stage(stage_timings, "question_generation_ms", question_started_at)
#         else:
#             stage_timings["question_generation_ms"] = 0.0
#         response["meta"]["decision_trace"] = self._build_decision_trace(
#             decision_trace_id=prepared_context.decision_trace_id,
#             requirements=requirements,
#             extracted_schema=prepared_context.extracted_schema,
#             target_profile=target_profile,
#             readiness=readiness,
#             retrieval_result=retrieval_result,
#             catalog_validation_result=catalog_validation_result,
#             compatibility_result=compatibility_result,
#             policy_result=policy_result,
#             recommendations=recommendations,
#             fallback_reason=core_result.fallback_reason,
#             recommendation_mode=recommendation_mode,
#             clarification_required_reasons=clarification_required_reasons,
#             expert_review_reason=expert_review_reason,
#             feature_flags=feature_flags,
#             decision_policy_profile=decision_policy_profile,
#             check_requirement_summary=check_requirement_summary,
#             editable_inferred_values=editable_inferred_values,
#             template_candidates=prepared_context.template_candidates,
#             selected_template=prepared_context.selected_template,
#         )
#         if capture_runtime_observability:
#             self._attach_runtime_observability(
#                 response=response,
#                 started_at=started_at,
#                 decision_trace_id=prepared_context.decision_trace_id,
#                 requirements=requirements,
#                 readiness=readiness,
#                 recommendation_mode=recommendation_mode,
#                 clarification_required_reasons=clarification_required_reasons,
#                 fallback_reason=core_result.fallback_reason,
#                 next_question=response.get("next_question"),
#             )
#         return response

#     def generate_narrative_enrichment(self, prepared_context, response, feature_flags=None):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         response = dict(response or {})
#         response["comparison"] = self.explanation_service.build_comparison(
#             response.get("requirements") or prepared_context.requirements,
#             response.get("recommendations") or [],
#             allow_llm=feature_flags.get("comparison_llm", False),
#         )
#         return response

#     def _dispatch_persistence_from_outputs(self, prepared_context, response, user_id="", business_id=""):
#         persistence_payload = {
#             "raw_intake_snapshot": prepared_context.raw_intake_snapshot,
#             "requirements": response.get("requirements") or prepared_context.requirements,
#             "target_profile": response.get("target_profile") or prepared_context.target_profile,
#             "recommendations": response.get("recommendations") or [],
#             "summary": response.get("summary") or "",
#             "assumptions": response.get("assumptions") or [],
#             "meta": {
#                 **dict(response.get("meta") or {}),
#                 "raw_chat": (response.get("requirements") or {}).get("raw_chat", ""),
#                 "extracted_schema": prepared_context.extracted_schema,
#             },
#             "user_id": user_id,
#             "business_id": business_id,
#         }
#         session_id = str(uuid4())
#         response["session_id"] = session_id
#         async_persistence_enabled = str(os.getenv("PROCUREMENT_ASYNC_PERSISTENCE", "true")).strip().lower() != "false"
#         if not async_persistence_enabled:
#             session, persistence_error = self._persist_session(session_id=session_id, **persistence_payload)
#             if session is None and persistence_error:
#                 response.setdefault("meta", {})
#                 response["meta"]["persistence_warning"] = persistence_error
#             return

#         self._persistence_executor.submit(
#             self._persist_session,
#             session_id=session_id,
#             **persistence_payload,
#         )

#     def _recommend_multi_intent(
#         self,
#         payload,
#         multi_intent_result,
#         extracted_schema=None,
#         prepared_context=None,
#         feature_flags=None,
#         user_id="",
#         business_id="",
#         persist=True,
#         top_level_timings=None,
#     ):
#         payload = dict(payload or {})
#         top_level_timings = top_level_timings or self._new_top_level_timings()
#         decision_trace_id = str(uuid4())
#         started_at = self.observability_service.start_timer()
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         if prepared_context is None:
#             prepare_started_at = perf_counter()
#             prepared_context = self.prepare_from_extracted_schema(
#                 payload=payload,
#                 extracted_schema=dict(extracted_schema or self._extract_schema(payload)),
#                 feature_flags=feature_flags,
#                 decision_trace_id=decision_trace_id,
#             )
#             self._mark_stage(top_level_timings["prepare_ms"], "total_ms", prepare_started_at)
#         extracted_schema = dict(prepared_context.extracted_schema or {})
#         raw_intake_snapshot = dict(prepared_context.raw_intake_snapshot or {})
#         requirements = dict(prepared_context.requirements or {})
#         target_profile = dict(prepared_context.target_profile or {})
#         base_readiness = dict(prepared_context.readiness or {})
#         template_candidates = self.template_service.select_candidates(
#             requirements,
#             target_profile,
#             multi_intent_result=multi_intent_result,
#         )
#         selected_template = self._selected_template(template_candidates)
#         selected_template_for_workflow = selected_template if selected_template.get("selection_allowed", True) else {}
#         multi_intent_policy = self.multi_intent_policy_service.evaluate(
#             payload=payload,
#             extracted_schema=extracted_schema,
#             requirements=requirements,
#             multi_intent_result=multi_intent_result,
#             selected_template=selected_template_for_workflow,
#         )

#         recommendation_groups = []
#         group_traces = []
#         flattened_recommendations = []
#         merged_assumptions = []
#         group_next_questions = []

#         for intent in multi_intent_result.get("intents") or []:
#             group_policy = dict((multi_intent_policy.get("groups_by_id") or {}).get(intent.get("group_id")) or {})
#             group_payload = self._apply_multi_intent_shared_context(
#                 intent.get("payload") or {},
#                 requirements,
#                 group_policy=group_policy,
#             )
#             group_prepared = self.prepare_from_extracted_schema(
#                 payload=group_payload,
#                 extracted_schema=intent.get("extracted_schema") or {},
#                 feature_flags=feature_flags,
#                 decision_trace_id=str(uuid4()),
#                 source_mode="multi_intent_group",
#                 prepared_catalog_state=prepared_context.prepared_catalog_state,
#             )
#             group_response = self._recommend_single_from_prepared(
#                 prepared_context=group_prepared,
#                 feature_flags=feature_flags,
#                 persist=False,
#                 capture_runtime_observability=False,
#             )
#             group_meta = dict(group_response.get("meta") or {})
#             group_decision_trace = group_meta.pop("decision_trace", None)
#             group_selected_template = dict(group_meta.get("selected_template") or {})
#             group_entry = {
#                 "group_id": intent.get("group_id"),
#                 "label": intent.get("label"),
#                 "intent_text": intent.get("intent_text"),
#                 "category": intent.get("category"),
#                 "workloads": intent.get("workloads") or [],
#                 "shared_constraints": group_policy.get("shared_constraints") or [],
#                 "warnings": group_policy.get("warnings") or [],
#                 "shared_budget": group_policy.get("shared_budget") or {},
#                 "decision_trace_id": group_response.get("decision_trace_id"),
#                 "requirements": group_response.get("requirements") or {},
#                 "field_state": group_response.get("field_state") or {},
#                 "field_source": group_response.get("field_source") or {},
#                 "assumption_severity": group_response.get("assumption_severity") or {},
#                 "recommendation_mode": group_response.get("recommendation_mode"),
#                 "clarification_required_reasons": group_response.get("clarification_required_reasons") or [],
#                 "check_requirement_summary": group_response.get("check_requirement_summary") or {},
#                 "editable_inferred_values": group_response.get("editable_inferred_values") or {},
#                 "selected_template": group_selected_template,
#                 "template_candidates": group_response.get("template_candidates") or [],
#                 "target_profile": group_response.get("target_profile") or {},
#                 "recommendations": group_response.get("recommendations") or [],
#                 "summary": group_response.get("summary", ""),
#                 "assumptions": group_response.get("assumptions") or [],
#                 "comparison": group_response.get("comparison", ""),
#                 "readiness": group_response.get("readiness") or {},
#                 "compatibility_report": group_response.get("compatibility_report") or {},
#                 "fallback_reason": group_response.get("fallback_reason"),
#                 "expert_review_eligible": group_response.get("expert_review_eligible", False),
#                 "next_question": group_response.get("next_question"),
#                 "meta": group_meta,
#             }
#             recommendation_groups.append(group_entry)
#             if group_decision_trace:
#                 group_traces.append(
#                     {
#                         "group_id": group_entry["group_id"],
#                         "label": group_entry["label"],
#                         "decision_trace": group_decision_trace,
#                     }
#                 )
#             if group_entry["recommendations"]:
#                 top_recommendation = dict(group_entry["recommendations"][0])
#                 top_recommendation["recommendation_group_id"] = group_entry["group_id"]
#                 top_recommendation["recommendation_group_label"] = group_entry["label"]
#                 flattened_recommendations.append(top_recommendation)
#             merged_assumptions.extend(group_entry["assumptions"])
#             if group_entry["next_question"]:
#                 group_next_questions.append(
#                     {
#                         "group_id": group_entry["group_id"],
#                         "label": group_entry["label"],
#                         "prompt": group_entry["next_question"],
#                     }
#                 )

#         bundle_result = self.bundle_service.build_bundle_result(
#             requirements=requirements,
#             recommendation_groups=recommendation_groups,
#             multi_intent_policy=multi_intent_policy,
#             selected_template=selected_template_for_workflow,
#         )
#         combined_merge_rules = list(multi_intent_policy.get("merge_rules") or []) + list(
#             bundle_result.get("merge_rules") or []
#         )
#         policy_trace = list(multi_intent_policy.get("split_rules") or []) + combined_merge_rules
#         bundle_trace = self._build_bundle_trace(bundle_result, selected_template)
#         bundle_validated = bool(bundle_result.get("bundle_validated"))
#         grouped_readiness = self._build_grouped_readiness(
#             base_readiness,
#             recommendation_groups,
#             multi_intent_policy=multi_intent_policy,
#         )
#         compatibility_report = self._build_grouped_compatibility_report(recommendation_groups)
#         fallback_reason = self._grouped_fallback_reason(recommendation_groups)
#         clarification_required_reasons = self._clarification_required_reasons(grouped_readiness)
#         expert_review_reason = self._grouped_expert_review_reason(recommendation_groups, fallback_reason)
#         if not bundle_validated and not clarification_required_reasons:
#             expert_review_reason = expert_review_reason or "bundle_validation_rejected"
#         expert_review_reason = self._apply_template_review_reason(selected_template, expert_review_reason)
#         decision_policy_profile = self.config_service.get_decision_policy_profile()
#         recommendation_mode = self._recommendation_mode(
#             readiness=grouped_readiness,
#             recommendations=flattened_recommendations,
#             fallback_reason=fallback_reason,
#             expert_review_reason=expert_review_reason,
#             clarification_required_reasons=clarification_required_reasons,
#             candidate_pool_size=sum(group["meta"].get("eligible_product_count", 0) for group in recommendation_groups),
#         )
#         recommendation_mode = self._apply_template_selection_mode(selected_template, recommendation_mode)
#         requirements["review_state"] = self.review_support_service.enrich_review_state(
#             requirements=requirements,
#             readiness=grouped_readiness,
#             template_candidates=template_candidates,
#             recommendation_mode=recommendation_mode,
#         )
#         check_requirement_summary = self.review_support_service.build_check_requirement_summary(
#             requirements=requirements,
#             readiness=grouped_readiness,
#             template_candidates=template_candidates,
#             recommendation_mode=recommendation_mode,
#         )
#         editable_inferred_values = self.review_support_service.build_editable_inferred_values(requirements)
#         template_id = bundle_trace.get("template_id")
#         template_version = bundle_trace.get("template_version")
#         response = {
#             "decision_trace_id": decision_trace_id,
#             "requirements": requirements,
#             "field_state": requirements.get("field_state") or {},
#             "field_source": requirements.get("field_source") or {},
#             "assumption_severity": requirements.get("assumption_severity") or {},
#             "recommendation_mode": recommendation_mode,
#             "clarification_required_reasons": clarification_required_reasons,
#             "review_state": requirements.get("review_state") or {},
#             "check_requirement_summary": check_requirement_summary,
#             "editable_inferred_values": editable_inferred_values,
#             "template_candidates": template_candidates,
#             "target_profile": target_profile,
#             "recommendations": flattened_recommendations,
#             "recommendation_groups": recommendation_groups,
#             "summary": self._build_release_4a_summary(
#                 recommendation_groups,
#                 multi_intent_policy=multi_intent_policy,
#                 bundle_result=bundle_result,
#             ),
#             "assumptions": self._dedupe_strings(merged_assumptions),
#             "comparison": self.explanation_service.build_comparison(
#                 requirements,
#                 flattened_recommendations,
#                 allow_llm=feature_flags.get("comparison_llm", False),
#             ),
#             "extracted_schema": extracted_schema,
#             "readiness": grouped_readiness,
#             "compatibility_report": compatibility_report,
#             "bundle_compatibility_report": bundle_result.get("bundle_compatibility_report") or {},
#             "bundle_conflict_codes": list(bundle_result.get("bundle_conflict_codes") or []),
#             "bundle_capacity_summary": bundle_result.get("bundle_capacity_summary") or {},
#             "bundle_options": list(bundle_result.get("bundle_options") or []),
#             "architecture_graph": bundle_result.get("architecture_graph") or {},
#             "template_id": template_id,
#             "template_version": template_version,
#             "fallback_reason": fallback_reason,
#             "expert_review_eligible": bool(expert_review_reason) and feature_flags.get("expert_review", True),
#             "meta": {
#                 "engine_version": ENGINE_VERSION,
#                 "config_versions": self.config_service.get_versions(),
#                 "config_bundle_version": self.config_service.get_bundle_version(),
#                 "feature_flags": feature_flags,
#                 "source_product_count": sum(group["meta"].get("source_product_count", 0) for group in recommendation_groups),
#                 "catalog_validation_summary": {
#                     "group_count": len(recommendation_groups),
#                     "rejected_count": sum(
#                         (group["meta"].get("catalog_validation_summary") or {}).get("rejected_count", 0)
#                         for group in recommendation_groups
#                     ),
#                 },
#                 "eligible_product_count": sum(group["meta"].get("eligible_product_count", 0) for group in recommendation_groups),
#                 "recommended_count": len(flattened_recommendations),
#                 "catalog_observability": self._aggregate_catalog_observability(recommendation_groups),
#                 "filtered_categories": self._dedupe_strings(
#                     [
#                         category
#                         for group in recommendation_groups
#                         for category in (group.get("target_profile", {}).get("categories") or [])
#                     ]
#                 ),
#                 "semantic_candidate_ids": self._dedupe_strings(
#                     [
#                         candidate_id
#                         for group in recommendation_groups
#                         for candidate_id in (group["meta"].get("semantic_candidate_ids") or [])
#                     ]
#                 )[:10],
#                 "semantic_candidate_count": sum(group["meta"].get("semantic_candidate_count", 0) for group in recommendation_groups),
#                 "retrieval_summary": {
#                     "candidate_count": sum(
#                         (group["meta"].get("retrieval_summary") or {}).get("candidate_count", 0)
#                         for group in recommendation_groups
#                     ),
#                     "fallback_reason": fallback_reason,
#                     "top_candidates": [
#                         {
#                             "group_id": group["group_id"],
#                             "label": group["label"],
#                             "top_candidates": (group["meta"].get("retrieval_summary") or {}).get("top_candidates") or [],
#                         }
#                         for group in recommendation_groups
#                     ],
#                 },
#                 "compatibility_summary": compatibility_report.get("summary") or {},
#                 "compatibility_rejections_sample": compatibility_report.get("rejected_products") or [],
#                 "policy_summary": {
#                     "group_count": len(recommendation_groups),
#                     "rejected_count": sum(
#                         (group["meta"].get("policy_summary") or {}).get("rejected_count", 0)
#                         for group in recommendation_groups
#                     ),
#                 },
#                 "policy_rejections_sample": [
#                     {
#                         "group_id": group["group_id"],
#                         "label": group["label"],
#                         "rejected_products": (group["meta"].get("policy_rejections_sample") or [])[:3],
#                     }
#                     for group in recommendation_groups
#                     if group["meta"].get("policy_rejections_sample")
#                 ][:5],
#                 "applied_rules_count": sum(group["meta"].get("applied_rules_count", 0) for group in recommendation_groups),
#                 "ranking_deferred": all(group["meta"].get("ranking_deferred", False) for group in recommendation_groups),
#                 "ranking_deferred_reason": (
#                     "multi_intent_group_clarification_required"
#                     if any(group["meta"].get("ranking_deferred", False) for group in recommendation_groups)
#                     else None
#                 ),
#                 "expert_review_reason": expert_review_reason,
#                 "decision_policy_profile": decision_policy_profile,
#                 "bundle_trace": bundle_trace,
#                 "multi_intent": {
#                     "is_multi_intent": True,
#                     "is_grouped": True,
#                     "bundle_validated": bundle_validated,
#                     "policy_version": multi_intent_policy.get("policy_version"),
#                     "split_source": multi_intent_result.get("split_source"),
#                     "shared_budget_reused": multi_intent_result.get("shared_budget_reused", False),
#                     "shared_constraints": multi_intent_policy.get("shared_constraints") or [],
#                     "shared_budget": multi_intent_policy.get("shared_budget") or {},
#                     "warnings": multi_intent_policy.get("warnings") or [],
#                     "split_rules": multi_intent_policy.get("split_rules") or [],
#                     "merge_rules": combined_merge_rules,
#                     "policy_trace": policy_trace,
#                     "bundle_conflict_codes": list(bundle_result.get("bundle_conflict_codes") or []),
#                     "validation_outcome": bundle_trace.get("validation_outcome"),
#                     "template_id": template_id,
#                     "template_version": template_version,
#                     "group_count": len(recommendation_groups),
#                     "group_labels": [group["label"] for group in recommendation_groups],
#                     "group_decision_trace_ids": [
#                         group.get("decision_trace_id")
#                         for group in recommendation_groups
#                         if group.get("decision_trace_id")
#                     ],
#                     "group_next_questions": group_next_questions,
#                     "group_templates": self._build_group_template_summary(recommendation_groups),
#                 },
#             },
#         }
#         if grouped_readiness.get("next_question"):
#             response["next_question"] = grouped_readiness.get("next_question")
#         elif group_next_questions:
#             response["next_question"] = group_next_questions[0]["prompt"]

#         response["meta"]["decision_trace"] = {
#             "decision_trace_id": decision_trace_id,
            
#             "compatibility": {
#                 "scope": compatibility_report.get("scope") or "item",
#                 "summary": compatibility_report.get("summary") or {},
#                 "rejected_products": compatibility_report.get("rejected_products") or [],
#             },
#             "bundle_validation": bundle_trace,
#             "expert_review_reason": expert_review_reason,
#             "feature_flags": feature_flags,
#             "config_versions": self.config_service.get_versions(),
         
#             "multi_intent": {
#                 "is_multi_intent": True,
#                 "policy_version": multi_intent_policy.get("policy_version"),
#                 "split_source": multi_intent_result.get("split_source"),
#                 "shared_budget_reused": multi_intent_result.get("shared_budget_reused", False),
#                 "bundle_validated": bundle_validated,
#                 "shared_constraints": multi_intent_policy.get("shared_constraints") or [],
#                 "shared_budget": multi_intent_policy.get("shared_budget") or {},
#                 "warnings": multi_intent_policy.get("warnings") or [],
#                 "split_rules": multi_intent_policy.get("split_rules") or [],
#                 "merge_rules": combined_merge_rules,
#                 "policy_trace": policy_trace,
#                 "bundle_conflict_codes": list(bundle_result.get("bundle_conflict_codes") or []),
#                 "validation_outcome": bundle_trace.get("validation_outcome"),
#                 "template_id": template_id,
#                 "template_version": template_version,
#                 "groups": group_traces,
#                 "group_templates": self._build_group_template_summary(recommendation_groups),
#             },
#         }
#         self._attach_runtime_observability(
#             response=response,
#             started_at=started_at,
#             decision_trace_id=decision_trace_id,
#             requirements=requirements,
#             readiness=grouped_readiness,
#             recommendation_mode=recommendation_mode,
#             clarification_required_reasons=clarification_required_reasons,
#             fallback_reason=fallback_reason,
#             next_question=response.get("next_question"),
#         )

#         if persist:
#             self._dispatch_persistence_from_outputs(
#                 prepared_context=prepared_context,
#                 response={
#                     **response,
#                     "recommendations": flattened_recommendations,
#                     "target_profile": target_profile,
#                     "assumptions": response["assumptions"],
#                     "meta": {
#                         **response["meta"],
#                         "recommendation_groups": recommendation_groups,
#                     },
#                 },
#                 user_id=user_id,
#                 business_id=business_id,
#             )

#         return response

#     def _attach_runtime_observability(
#         self,
#         response,
#         started_at,
#         decision_trace_id,
#         requirements,
#         readiness,
#         recommendation_mode,
#         clarification_required_reasons,
#         fallback_reason,
#         next_question=None,
#     ):
#         response = dict(response or {})
#         runtime_observability = self.observability_service.build_runtime_observability(
#             started_at=started_at,
#             decision_trace_id=decision_trace_id,
#             requirements=requirements,
#             readiness=readiness,
#             recommendation_mode=recommendation_mode,
#             clarification_required_reasons=clarification_required_reasons,
#             fallback_reason=fallback_reason,
#             next_question=next_question,
#             response_payload=response,
#         )
#         response.setdefault("meta", {})
#         response["meta"]["runtime_observability"] = runtime_observability
#         decision_trace = response["meta"].get("decision_trace")
#         if isinstance(decision_trace, dict):
#             pass
#         return response

#     def _apply_multi_intent_shared_context(self, payload, requirements, group_policy=None):
#         payload = dict(payload or {})
#         requirements = dict(requirements or {})
#         group_policy = dict(group_policy or {})
#         explicit_payload_fields = list(payload.get("_explicit_payload_fields") or [])
#         field_source_hints = dict(payload.get("_field_source_hints") or {})
#         shared_constraints = set(group_policy.get("shared_constraints") or [])

#         if (
#             requirements.get("budget_scope")
#             and "budget_scope" in shared_constraints
#             and not payload.get("budget_scope")
#         ):
#             payload["budget_scope"] = requirements.get("budget_scope")
#             field_source_hints.setdefault("budget_scope", "context_explicit")

#         if explicit_payload_fields:
#             payload["_explicit_payload_fields"] = explicit_payload_fields
#         if field_source_hints:
#             payload["_field_source_hints"] = field_source_hints
#         return payload

#     def _normalize_products(self, raw_products, requested_currency, allowed_categories=None, currency_fallback_used=False):
#         normalized_products = []
#         seen_ids = set()
#         allowed_categories = set(allowed_categories or [])
#         for product in raw_products:
#             inventory_offers = list(product.get("inventory_offers") or [])
#             if not inventory_offers:
#                 inventory = product.get("inventory")
#                 inventory_offers = [inventory] if inventory else [None]

#             for inventory in inventory_offers:
#                 candidate = dict(product)
#                 candidate.pop("inventory_offers", None)
#                 if inventory:
#                     candidate["inventory"] = inventory
#                 else:
#                     candidate.pop("inventory", None)
#                 normalized = normalize_product_document(candidate, requested_currency=requested_currency)
#                 product_id = normalized.get("id")
#                 if product_id in seen_ids:
#                     continue
#                 seen_ids.add(product_id)
#                 normalized["offer_count"] = len(inventory_offers)
#                 normalized["alternate_offer_count"] = max(len(inventory_offers) - 1, 0)
#                 normalized["currency_fallback_used"] = bool(
#                     currency_fallback_used
#                     and requested_currency
#                     and str(normalized.get("currency") or "").strip().upper()
#                     != str(requested_currency or "").strip().upper()
#                 )
#                 normalized_products.append(normalized)
#         return normalized_products

#     def _filter_normalized_products(self, normalized_products, allowed_categories=None, candidate_ids=None):
#         normalized_products = list(normalized_products or [])
#         category_filter_enabled = bool(allowed_categories)
#         candidate_filter_enabled = candidate_ids is not None
#         allowed_categories = set(allowed_categories or [])
#         candidate_ids = set(candidate_ids or [])
#         if not category_filter_enabled and not candidate_filter_enabled:
#             return normalized_products
#         filtered = []
#         for product in normalized_products:
#             if category_filter_enabled and product.get("category") not in allowed_categories:
#                 continue
#             if candidate_filter_enabled and product.get("id") not in candidate_ids:
#                 continue
#             filtered.append(product)
#         return filtered

#     def _build_grouped_readiness(self, base_readiness, recommendation_groups, multi_intent_policy=None):
#         base_readiness = dict(base_readiness or {})
#         multi_intent_policy = dict(multi_intent_policy or {})
#         readiness_items = [dict(group.get("readiness") or {}) for group in recommendation_groups]
#         if not readiness_items:
#             return base_readiness

#         confidence_rank = {"low": 0, "medium": 1, "high": 2}
#         band_rank = {"low": 0, "medium": 1, "high": 2}
#         question_candidates = []
#         missing_signals = []
#         for group in recommendation_groups:
#             readiness = dict(group.get("readiness") or {})
#             for signal in readiness.get("missing_signals") or []:
#                 if signal not in missing_signals:
#                     missing_signals.append(signal)
#             for candidate in readiness.get("question_candidates") or []:
#                 candidate_copy = dict(candidate)
#                 candidate_copy["group_id"] = group.get("group_id")
#                 candidate_copy["group_label"] = group.get("label")
#                 question_candidates.append(candidate_copy)

#         shared_budget = dict(multi_intent_policy.get("shared_budget") or {})
#         if shared_budget.get("allocation_required"):
#             missing_signals.append(shared_budget.get("clarification_key"))
#             question_candidates.append(
#                 {
#                     "key": shared_budget.get("clarification_key"),
#                     "prompt": shared_budget.get("clarification_prompt"),
#                     "rationale": shared_budget.get("clarification_rationale"),
#                     "impact": 0.98,
#                 }
#             )

#         question_candidates.sort(key=lambda item: item.get("impact", 0), reverse=True)
#         top_question = question_candidates[0] if question_candidates else None
#         threshold = self.clarification_service.question_impact_threshold()
#         should_ask_top_question = bool(top_question and float(top_question.get("impact", 0.0)) >= threshold)
#         grouped_confidence = min(
#             (item.get("confidence") or "medium" for item in readiness_items),
#             key=lambda value: confidence_rank.get(value, 1),
#         )
#         grouped_band = min(
#             (item.get("decision_confidence_band") or "medium" for item in readiness_items),
#             key=lambda value: band_rank.get(value, 1),
#         )
#         grouped_score = round(
#             sum(item.get("decision_confidence_score", 0.0) for item in readiness_items) / len(readiness_items),
#             4,
#         )

#         return {
#             **base_readiness,
#             "is_ready": all(bool(item.get("is_ready")) for item in readiness_items),
#             "confidence": grouped_confidence,
#             "missing_signals": missing_signals,
#             "highest_priority_missing_field": top_question.get("key") if top_question else None,
#             "next_question": top_question.get("prompt") if should_ask_top_question else None,
#             "follow_up_questions": question_candidates[:3],
#             "decision_confidence_score": grouped_score,
#             "decision_confidence_band": grouped_band,
#             "recommended_question_budget": 1 if should_ask_top_question else 0,
#             "routing_recommendation": (
#                 "clarify_before_ranking"
#                 if not all(bool(item.get("is_ready")) for item in readiness_items)
#                 else "recommend_with_one_refinement"
#                 if should_ask_top_question
#                 else base_readiness.get("routing_recommendation", "recommend_now")
#             ),
#             "recommended_refinement_question": top_question.get("prompt") if should_ask_top_question else None,
#             "question_strategy": (
#                 "grouped_single_question"
#                 if should_ask_top_question
#                 else base_readiness.get("question_strategy", "proceed")
#             ),
#             "question_candidates": question_candidates[:3],
#         }

#     def _build_grouped_compatibility_report(self, recommendation_groups):
#         group_reports = []
#         rejected_products = []
#         eligible_count = 0
#         rejected_count = 0
#         for group in recommendation_groups:
#             report = dict(group.get("compatibility_report") or {})
#             report_summary = dict(report.get("summary") or {})
#             eligible_count += report_summary.get("eligible_count", 0)
#             rejected_count += report_summary.get("rejected_count", 0)
#             group_rejections = list(report.get("rejected_products") or [])
#             rejected_products.extend(group_rejections[:3])
#             group_reports.append(
#                 {
#                     "group_id": group.get("group_id"),
#                     "label": group.get("label"),
#                     "scope": report.get("scope") or "item",
#                     "summary": report_summary,
#                     "rejected_products": group_rejections[:3],
#                 }
#             )

#         return {
#             "scope": "item",
#             "summary": {
#                 "compatibility_scope": "item",
#                 "grouped": True,
#                 "group_count": len(recommendation_groups),
#                 "eligible_count": eligible_count,
#                 "rejected_count": rejected_count,
#             },
#             "rejected_products": rejected_products[:5],
#             "groups": group_reports,
#         }

#     def _build_grouped_summary(self, recommendation_groups, multi_intent_policy=None):
#         multi_intent_policy = dict(multi_intent_policy or {})
#         if not recommendation_groups:
#             return "No grouped recommendations were generated."

#         parts = []
#         for group in recommendation_groups:
#             recommendations = list(group.get("recommendations") or [])
#             label = group.get("label") or group.get("group_id") or "Intent"
#             if recommendations:
#                 top_name = recommendations[0].get("name") or "Recommendation ready"
#                 parts.append(f"{label}: {top_name}")
#             elif group.get("next_question"):
#                 parts.append(f"{label}: clarification needed")
#             else:
#                 parts.append(f"{label}: no exact fit")
#         summary = "Grouped recommendations prepared for {} intents. {}".format(
#             len(recommendation_groups),
#             " | ".join(parts),
#         )
#         shared_budget = dict(multi_intent_policy.get("shared_budget") or {})
#         if shared_budget.get("allocation_required"):
#             summary += " Shared project budget allocation still needs confirmation before the groups can be treated as budget-valid together."
#         return summary

#     def _build_release_4a_summary(self, recommendation_groups, multi_intent_policy=None, bundle_result=None):
#         bundle_result = dict(bundle_result or {})
#         grouped_summary = self._build_grouped_summary(
#             recommendation_groups,
#             multi_intent_policy=multi_intent_policy,
#         )
#         bundle_summary = str(bundle_result.get("summary") or "").strip()
#         if bundle_result.get("bundle_validated"):
#             return bundle_summary or grouped_summary
#         if not bundle_summary:
#             return grouped_summary
#         if recommendation_groups and any(group.get("recommendations") for group in recommendation_groups):
#             return (
#                 bundle_summary
#                 + " Constrained per-role recommendations remain available while the bundle is not yet valid."
#             )
#         return bundle_summary

#     def _build_bundle_trace(self, bundle_result, selected_template=None):
#         bundle_result = dict(bundle_result or {})
#         selected_template = dict(selected_template or {})
#         bundle_candidate = dict(bundle_result.get("bundle_candidate") or {})
#         bundle_report = dict(bundle_result.get("bundle_compatibility_report") or {})
#         return {
#             "template_id": bundle_candidate.get("template_id") or selected_template.get("template_id"),
#             "template_version": bundle_candidate.get("template_version") or selected_template.get("template_version"),
#             "bundle_validated": bool(bundle_result.get("bundle_validated")),
#             "validation_outcome": "passed" if bundle_result.get("bundle_validated") else "rejected",
#             "bundle_candidate": bundle_candidate,
#             "bundle_compatibility_report": bundle_report,
#             "bundle_conflict_codes": list(bundle_result.get("bundle_conflict_codes") or []),
#             "bundle_capacity_summary": bundle_result.get("bundle_capacity_summary") or {},
#             "bundle_options": list(bundle_result.get("bundle_options") or []),
#             "architecture_graph": bundle_result.get("architecture_graph") or {},
#             "merge_rules": list(bundle_result.get("merge_rules") or []),
#         }

#     def _build_group_template_summary(self, recommendation_groups):
#         summary = []
#         for group in list(recommendation_groups or []):
#             selected_template = dict(group.get("selected_template") or {})
#             template_candidates = list(group.get("template_candidates") or [])
#             if not selected_template and template_candidates:
#                 selected_template = self._selected_template(template_candidates)
#             summary.append(
#                 {
#                     "group_id": group.get("group_id"),
#                     "label": group.get("label"),
#                     "category": group.get("category"),
#                     "template_id": selected_template.get("template_id"),
#                     "template_version": selected_template.get("template_version"),
#                     "template_match_quality": selected_template.get("template_match_quality"),
#                     "required_roles": list(selected_template.get("required_roles") or []),
#                     "quantity_strategy": selected_template.get("quantity_strategy"),
#                     "budget_strategy": selected_template.get("budget_strategy"),
#                     "selection_allowed": bool(selected_template.get("selection_allowed", True))
#                     if selected_template
#                     else False,
#                 }
#             )
#         return summary

#     def _grouped_fallback_reason(self, recommendation_groups):
#         if not recommendation_groups:
#             return "no_exact_fit"
#         fallback_reasons = [
#             group.get("fallback_reason")
#             for group in recommendation_groups
#             if group.get("fallback_reason")
#         ]
#         if not fallback_reasons:
#             return ""
#         if len(fallback_reasons) == len(recommendation_groups):
#             return fallback_reasons[0] if len(set(fallback_reasons)) == 1 else "multi_intent_partial_fallback"
#         return "multi_intent_partial_fallback"

#     def _grouped_expert_review_reason(self, recommendation_groups, fallback_reason):
#         if any(group.get("expert_review_eligible") for group in recommendation_groups):
#             return "multi_intent_group_requires_review"
#         if fallback_reason in {"compatibility_blocked_all", "policy_rejected_all", "no_exact_fit", "multi_intent_partial_fallback"}:
#             return fallback_reason
#         return ""

#     def _selected_template(self, template_candidates):
#         template_candidates = list(template_candidates or [])
#         if not template_candidates:
#             return {}
#         selected = dict(template_candidates[0])
#         return {
#             "template_id": selected.get("template_id"),
#             "template_version": selected.get("template_version"),
#             "scenario_family": selected.get("scenario_family"),
#             "variant": selected.get("variant"),
#             "template_match_quality": selected.get("template_match_quality"),
#             "match_score": selected.get("match_score"),
#             "selection_allowed": bool(selected.get("selection_allowed", True)),
#             "selection_rejection_reason": selected.get("selection_rejection_reason") or "",
#             "matched_template_signals": selected.get("matched_template_signals") or {},
#             "coverage_gap_reasons": list(selected.get("coverage_gap_reasons") or []),
#             "gap_type": selected.get("gap_type") or "",
#             "hard_gate_failures": list(selected.get("hard_gate_failures") or []),
#             "contradiction_codes": list(selected.get("contradiction_codes") or []),
#             "soft_fit_gaps": list(selected.get("soft_fit_gaps") or []),
#             "template_selection_debug": dict(selected.get("template_selection_debug") or {}),
#             "required_roles": list(selected.get("required_roles") or []),
#             "quantity_strategy": selected.get("quantity_strategy"),
#             "budget_strategy": selected.get("budget_strategy"),
#             "compatibility_profile": selected.get("compatibility_profile"),
#             "scoring_profile": selected.get("scoring_profile"),
#             "urgency_profile": selected.get("urgency_profile"),
#             "site_scope_profile": selected.get("site_scope_profile"),
#             "rollout_type": selected.get("rollout_type"),
#             "replacement_mode": selected.get("replacement_mode"),
#             "support_preference": selected.get("support_preference"),
#             "existing_infra_dependency": selected.get("existing_infra_dependency"),
#             "acceptable_downgrade_path": selected.get("acceptable_downgrade_path"),
#         }

#     def _apply_template_review_reason(self, selected_template, expert_review_reason):
#         selected_template = dict(selected_template or {})
#         expert_review_reason = str(expert_review_reason or "").strip()
#         template_quality = str(selected_template.get("template_match_quality") or "").strip().lower()
#         if template_quality == "coverage_gap":
#             return expert_review_reason or "template_coverage_gap"
#         return expert_review_reason

#     def _apply_template_selection_mode(self, selected_template, recommendation_mode):
#         selected_template = dict(selected_template or {})
#         template_quality = str(selected_template.get("template_match_quality") or "").strip().lower()
#         if template_quality == "coverage_gap":
#             return "expert_review_recommended"
#         if template_quality == "closest_match" and recommendation_mode == "firm_recommendation":
#             return "provisional_recommendation"
#         return recommendation_mode

#     def _dedupe_strings(self, values):
#         deduped = []
#         seen = set()
#         for value in list(values or []):
#             normalized = str(value or "").strip()
#             if not normalized:
#                 continue
#             lowered = normalized.lower()
#             if lowered in seen:
#                 continue
#             seen.add(lowered)
#             deduped.append(normalized)
#         return deduped

#     def _persist_session(
#         self,
#         raw_intake_snapshot,
#         requirements,
#         target_profile,
#         recommendations,
#         summary,
#         assumptions,
#         meta,
#         user_id="",
#         business_id="",
#         session_id=None,
#     ):
#         try:
#             from ..models import ProcurementSession

#             session = ProcurementSession.objects.create(
#                 session_id=str(session_id or uuid4()),
#                 user_id=str(user_id or ""),
#                 business_id=str(business_id or ""),
#                 store_id=requirements.get("store_id", ""),
#                 channel=requirements.get("channel", "api"),
#                 currency=requirements.get("currency", ""),
#                 raw_intake_snapshot=dict(raw_intake_snapshot or {}),
#                 requirements=requirements,
#                 target_profile=target_profile,
#                 recommendations=recommendations,
#                 summary=summary,
#                 assumptions=assumptions,
#                 meta=meta,
#                 engine_version=ENGINE_VERSION,
#             )
#             return session, None
#         except Exception as exc:
#             return None, str(exc)

#     def _build_raw_intake_snapshot(self, payload):
#         snapshot = {}
#         for key, value in dict(payload or {}).items():
#             if str(key).startswith("_") or key == "persist":
#                 continue
#             snapshot[key] = value
#         return snapshot

#     def _build_buy_url(self, product_id, store_id=""):
#         if not product_id:
#             return ""

#         base_url = os.getenv("SHOP_PRODUCT_BASE_URL", "https://dev.techpay.ai/shop/#/products").rstrip("/")
#         return f"{base_url}/{product_id}"

#     def _resolve_prepared_catalog_state(self, requirements):
#         requirements = dict(requirements or {})
#         cache_key = self._prepared_catalog_state_cache_key(requirements)
#         cached = self._prepared_catalog_state_cache.get(cache_key)
#         if cached is not None:
#             return cached

#         raw_products = self.catalog_repository.fetch_products(
#             store_id="",
#             currency=requirements.get("currency", ""),
#         )
#         currency_fallback_used = False
#         if not raw_products and requirements.get("currency"):
#             raw_products = self.catalog_repository.fetch_products(store_id="", currency="")
#             currency_fallback_used = bool(raw_products)
#         catalog_source_snapshot = self._catalog_source_snapshot()
#         normalized_products = self._normalize_products(
#             raw_products,
#             requirements.get("currency"),
#             allowed_categories=None,
#             currency_fallback_used=currency_fallback_used,
#         )
#         catalog_validation_result = self._screen_catalog_metadata(normalized_products)
#         eligible_products = list(catalog_validation_result.get("eligible_products") or [])
#         category_subsets = self._build_category_indexed_subsets(eligible_products)
#         retrieval_assets_by_subset = {
#             "__all__": self._resolve_precomputed_retrieval_assets(
#                 eligible_products,
#                 subset_key="__all__",
#                 cache_key=cache_key,
#             ),
#         }
#         for category_key, subset in category_subsets.items():
#             retrieval_assets_by_subset[category_key] = self._resolve_precomputed_retrieval_assets(
#                 subset,
#                 subset_key=category_key,
#                 cache_key=cache_key,
#             )

#         prepared = PreparedCatalogState(
#             cache_key=cache_key,
#             raw_products=tuple(raw_products),
#             normalized_products=tuple(normalized_products),
#             eligible_products=tuple(eligible_products),
#             catalog_validation_result=dict(catalog_validation_result or {}),
#             category_subsets={key: tuple(value) for key, value in category_subsets.items()},
#             retrieval_assets_by_subset=retrieval_assets_by_subset,
#             currency_fallback_used=bool(currency_fallback_used),
#             catalog_source_snapshot=dict(catalog_source_snapshot or {}),
#             store_scope_applied=False,
#         )
#         self._prepared_catalog_state_cache[cache_key] = prepared
#         return prepared

#     def _resolve_precomputed_retrieval_assets(self, normalized_products, subset_key="__all__", cache_key=""):
#         getter = getattr(self.catalog_repository, "get_precomputed_retrieval_assets", None)
#         if callable(getter):
#             try:
#                 assets = getter(
#                     subset_key=subset_key,
#                     cache_key=cache_key,
#                     normalized_products=list(normalized_products or []),
#                 )
#             except TypeError:
#                 assets = getter(subset_key, cache_key)
#             except Exception:
#                 assets = None
#             if assets:
#                 return assets
#         return self.semantic_retriever.build_retrieval_assets(
#             normalized_products,
#             include_semantic=False,
#         )

#     def _prepared_catalog_state_cache_key(self, requirements):
#         requirements = dict(requirements or {})
#         currency = str(requirements.get("currency") or "").strip().upper()
#         store_id = str(requirements.get("store_id") or "").strip().lower()
#         source_snapshot = self._catalog_source_snapshot()
#         source_name = str(source_snapshot.get("source_name") or getattr(self.catalog_repository, "source_name", "")).strip()
#         source_path = str(source_snapshot.get("source_path") or "").strip()
#         source_success = bool(source_snapshot.get("source_load_success", True))
#         catalog_version = str(source_snapshot.get("catalog_version") or "").strip()
#         return "|".join(
#             [
#                 source_name,
#                 source_path,
#                 catalog_version,
#                 str(source_success).lower(),
#                 currency,
#                 store_id,
#             ]
#         )

#     def _build_category_indexed_subsets(self, eligible_products):
#         subsets = {}
#         for product in list(eligible_products or []):
#             category = str(product.get("category") or "").strip().lower()
#             if not category:
#                 continue
#             subsets.setdefault(category, []).append(product)
#         return subsets

#     def _resolve_category_subset_from_state(self, prepared_catalog_state, categories):
#         prepared_catalog_state = prepared_catalog_state or PreparedCatalogState(
#             cache_key="",
#             raw_products=tuple(),
#             normalized_products=tuple(),
#             eligible_products=tuple(),
#             catalog_validation_result={},
#             category_subsets={},
#             retrieval_assets_by_subset={},
#             currency_fallback_used=False,
#             catalog_source_snapshot={},
#         )
#         categories = [str(value or "").strip().lower() for value in list(categories or []) if str(value or "").strip()]
#         if not categories:
#             return list(prepared_catalog_state.eligible_products or []), "__all__"
#         subset = []
#         for category in categories:
#             subset.extend(list((prepared_catalog_state.category_subsets or {}).get(category) or []))
#         if not subset:
#             return [], "__all__"
#         seen = set()
#         deduped = []
#         for product in subset:
#             product_id = product.get("id")
#             if not product_id or product_id in seen:
#                 continue
#             seen.add(product_id)
#             deduped.append(product)
#         subset_key = "__".join(sorted(categories))
#         return deduped, subset_key

#     def _extract_schema(self, payload):
#         chat_text = str(payload.get("chat_text") or payload.get("raw_chat") or "").strip()
#         extraction_context = payload.get("extracted_schema") or {}
#         if extraction_context and extraction_context.get("intake_confidence") is not None:
#             context_schema = dict(extraction_context)
#             if chat_text and not context_schema.get("raw_chat"):
#                 context_schema["raw_chat"] = chat_text
#             return dict(self.extraction_service.extract("", context=context_schema))
#         if chat_text:
#             return dict(self.extraction_service.extract(chat_text, context=extraction_context))

#         fallback_schema = {
#             "raw_chat": chat_text,
#             "company_size": None,
#             "industry": payload.get("industry"),
#             "business_type": payload.get("business_type"),
#             "team_size": payload.get("team_size"),
#             "workload_types": payload.get("workload_types") or payload.get("workloads") or [],
#             "application_signals": payload.get("application_signals") or [],
#             "capability_tags": payload.get("capability_tags") or [],
#             "budget": payload.get("budget"),
#             "growth_expectation": payload.get("growth_expectation"),
#             "existing_infrastructure": payload.get("existing_infrastructure") or [],
#             "preferred_manufacturers": payload.get("preferred_manufacturers") or [],
#             "blocked_manufacturers": payload.get("blocked_manufacturers") or [],
#             "preferred_sellers": payload.get("preferred_sellers") or [],
#             "blocked_sellers": payload.get("blocked_sellers") or [],
#             "preferred_category": payload.get("preferred_category") or payload.get("category"),
#             "performance_priority": payload.get("performance_priority"),
#             "portability_need": payload.get("portability_need"),
#             "support_expectation": payload.get("support_expectation"),
#             "availability_need": payload.get("availability_need"),
#             "require_returnable": payload.get("require_returnable"),
#             "quantity": payload.get("quantity"),
#             "purchase_scope": payload.get("purchase_scope"),
#             "timeline": payload.get("timeline"),
#             "requested_ram": payload.get("requested_ram"),
#             "requested_storage": payload.get("requested_storage"),
#             "requested_ram_is_minimum": payload.get("requested_ram_is_minimum"),
#             "requested_storage_is_minimum": payload.get("requested_storage_is_minimum"),
#             "notes": payload.get("notes", ""),
#             "missing_fields": [],
#             "intake_confidence": 1.0,
#         }
#         return dict(self.extraction_service.extract("", context=fallback_schema))

#     def _build_compatibility_report(self, compatibility_result):
#         compatibility_result = compatibility_result or {}
#         summary = compatibility_result.get("summary") or {}
#         return {
#             "scope": summary.get("compatibility_scope") or "item",
#             "summary": summary,
#             "rejected_products": (compatibility_result.get("rejected_products") or [])[:5],
#         }

#     def _deterministic_candidate_pool(self, normalized_products, top_k=40):
#         candidates = []
#         for product in list(normalized_products or [])[:top_k]:
#             product_id = product.get("id")
#             if not product_id:
#                 continue
#             candidates.append(
#                 {
#                     "product_id": product_id,
#                     "base_product_id": product.get("base_product_id") or product_id,
#                     "manufacturer": str(product.get("manufacturer") or "").strip().lower(),
#                     "candidate_score": 1.0,
#                     "semantic_norm": 0.0,
#                     "lexical_norm": 0.0,
#                     "business_boost": 1.0,
#                 }
#             )
#         return {
#             "candidate_ids": [item["product_id"] for item in candidates],
#             "scored_candidates": candidates,
#             "fallback_reason": "semantic_retrieval_disabled",
#         }

#     def _screen_catalog_metadata(self, normalized_products):
#         eligible_products = []
#         rejected_products = []
#         for product in list(normalized_products or []):
#             metadata_validation = dict(product.get("metadata_validation") or {})
#             category = product.get("category")
#             missing_required_fields = list(metadata_validation.get("missing_required_fields") or [])
#             readiness_state = str(
#                 product.get("readiness_state") or metadata_validation.get("readiness_state") or ""
#             ).strip()
#             if readiness_state == "insufficient":
#                 rejected_products.append(
#                     {
#                         "product_id": product.get("id"),
#                         "name": product.get("name"),
#                         "category": category,
#                         "manufacturer": product.get("manufacturer"),
#                         "reasons": list(metadata_validation.get("parse_warnings") or [])
#                         or ["Missing required metadata: " + ", ".join(missing_required_fields)],
#                         "readiness_state": readiness_state,
#                         "missing_required_fields": missing_required_fields,
#                         "missing_critical_fields": list(metadata_validation.get("missing_critical_fields") or []),
#                     }
#                 )
#                 continue
#             eligible_products.append(product)
#         return {
#             "eligible_products": eligible_products,
#             "rejected_products": rejected_products,
#             "summary": {
#                 "input_count": len(list(normalized_products or [])),
#                 "eligible_count": len(eligible_products),
#                 "rejected_count": len(rejected_products),
#             },
#         }

#     def _catalog_source_snapshot(self):
#         getter = getattr(self.catalog_repository, "get_observability_snapshot", None)
#         if callable(getter):
#             try:
#                 snapshot = dict(getter() or {})
#             except Exception:
#                 snapshot = {}
#         else:
#             snapshot = {}
#         if snapshot:
#             return snapshot
#         return {
#             "source_name": getattr(self.catalog_repository, "source_name", self.catalog_repository.__class__.__name__),
#             "source_load_success": True,
#             "unmatched_inventory_count": 0,
#         }

#     def _build_catalog_observability(
#         self,
#         raw_products,
#         normalized_products,
#         catalog_validation_result,
#         requirements,
#         currency_fallback_used=False,
#         catalog_source_snapshot=None,
#         store_scope_applied=False,
#     ):
#         raw_products = list(raw_products or [])
#         normalized_products = list(normalized_products or [])
#         catalog_validation_result = dict(catalog_validation_result or {})
#         requirements = dict(requirements or {})
#         catalog_source_snapshot = dict(catalog_source_snapshot or {})
#         readiness_state_counts = {}
#         parse_warning_count = 0
#         provisional_count = 0
#         for product in normalized_products:
#             readiness_state = str(product.get("readiness_state") or "unknown").strip() or "unknown"
#             readiness_state_counts[readiness_state] = readiness_state_counts.get(readiness_state, 0) + 1
#             parse_warning_count += len(product.get("parse_warnings") or [])
#             if readiness_state == "provisional":
#                 provisional_count += 1
#         return {
#             "source_name": catalog_source_snapshot.get("source_name")
#             or getattr(self.catalog_repository, "source_name", self.catalog_repository.__class__.__name__),
#             "source_load_success": bool(catalog_source_snapshot.get("source_load_success", True)),
#             "source_path": catalog_source_snapshot.get("source_path"),
#             "requested_store_id": str(requirements.get("store_id") or ""),
#             "applied_store_id": str(catalog_source_snapshot.get("requested_store_id") or ""),
#             "store_scope_applied": bool(store_scope_applied),
#             "requested_currency": str(requirements.get("currency") or ""),
#             "matched_product_count": int(catalog_source_snapshot.get("matched_product_count") or len(raw_products)),
#             "normalized_candidate_count": len(normalized_products),
#             "unmatched_inventory_count": int(catalog_source_snapshot.get("unmatched_inventory_count") or 0),
#             "readiness_state_counts": readiness_state_counts,
#             "parse_warning_count": parse_warning_count,
#             "currency_fallback_count": 1 if currency_fallback_used else 0,
#             "currency_fallback_used": bool(currency_fallback_used),
#             "provisional_count": provisional_count,
#             "store_filter_miss": bool(
#                 store_scope_applied
#                 and (
#                     catalog_source_snapshot.get("store_filter_miss")
#                     or (requirements.get("store_id") and not raw_products)
#                 )
#             ),
#             "validation_block_count": len(catalog_validation_result.get("rejected_products") or []),
#         }

#     def _aggregate_catalog_observability(self, recommendation_groups):
#         recommendation_groups = list(recommendation_groups or [])
#         readiness_state_counts = {}
#         source_names = []
#         source_paths = []
#         total_unmatched_inventory = 0
#         total_normalized_candidate_count = 0
#         total_parse_warning_count = 0
#         total_currency_fallback_count = 0
#         total_provisional_count = 0
#         total_validation_block_count = 0
#         any_store_filter_miss = False
#         any_store_scope_applied = False
#         all_load_success = True
#         for group in recommendation_groups:
#             group_observability = dict((group.get("meta") or {}).get("catalog_observability") or {})
#             if not group_observability:
#                 continue
#             source_name = group_observability.get("source_name")
#             source_path = group_observability.get("source_path")
#             if source_name and source_name not in source_names:
#                 source_names.append(source_name)
#             if source_path and source_path not in source_paths:
#                 source_paths.append(source_path)
#             for readiness_state, count in dict(group_observability.get("readiness_state_counts") or {}).items():
#                 readiness_state_counts[readiness_state] = readiness_state_counts.get(readiness_state, 0) + int(count or 0)
#             total_unmatched_inventory += int(group_observability.get("unmatched_inventory_count") or 0)
#             total_normalized_candidate_count += int(group_observability.get("normalized_candidate_count") or 0)
#             total_parse_warning_count += int(group_observability.get("parse_warning_count") or 0)
#             total_currency_fallback_count += int(group_observability.get("currency_fallback_count") or 0)
#             total_provisional_count += int(group_observability.get("provisional_count") or 0)
#             total_validation_block_count += int(group_observability.get("validation_block_count") or 0)
#             any_store_filter_miss = any_store_filter_miss or bool(group_observability.get("store_filter_miss"))
#             any_store_scope_applied = any_store_scope_applied or bool(group_observability.get("store_scope_applied"))
#             all_load_success = all_load_success and bool(group_observability.get("source_load_success", True))
#         return {
#             "source_names": source_names,
#             "source_paths": source_paths,
#             "source_load_success": all_load_success,
#             "unmatched_inventory_count": total_unmatched_inventory,
#             "normalized_candidate_count": total_normalized_candidate_count,
#             "readiness_state_counts": readiness_state_counts,
#             "parse_warning_count": total_parse_warning_count,
#             "currency_fallback_count": total_currency_fallback_count,
#             "currency_fallback_used": bool(total_currency_fallback_count),
#             "provisional_count": total_provisional_count,
#             "store_scope_applied": any_store_scope_applied,
#             "store_filter_miss": any_store_filter_miss,
#             "validation_block_count": total_validation_block_count,
#         }

#     def _compatibility_bypass(self, normalized_products):
#         products = list(normalized_products or [])
#         return {
#             "eligible_products": products,
#             "rejected_products": [],
#             "reports_by_product_id": {},
#             "summary": {
#                 "compatibility_scope": "item",
#                 "evaluated_count": len(products),
#                 "eligible_count": len(products),
#                 "rejected_count": 0,
#                 "skipped_by_flag": True,
#             },
#         }

#     def _expert_review_reason(self, readiness, ranking_deferred, fallback_reason, compatibility_result, recommendations):
#         if ranking_deferred:
#             return "low_confidence_clarification_required"
#         if fallback_reason in {"compatibility_blocked_all", "policy_rejected_all", "no_exact_fit"}:
#             return fallback_reason
#         if (readiness or {}).get("decision_confidence_band") == "low":
#             return "low_confidence_routing"
#         if compatibility_result.get("rejected_products") and not recommendations:
#             return "hard_conflict_detected"
#         return ""

#     def _clarification_required_reasons(self, readiness):
#         readiness = dict(readiness or {})
#         question_candidates = list(readiness.get("question_candidates") or [])
#         threshold = self.clarification_service.question_impact_threshold()
#         reasons = [
#             str(item.get("key") or "").strip()
#             for item in question_candidates
#             if str(item.get("key") or "").strip() and float(item.get("impact") or 0.0) >= threshold
#         ]
#         if reasons:
#             return self._dedupe_strings(reasons)

#         critical_missing = [
#             signal
#             for signal in list(readiness.get("missing_signals") or [])
#             if signal in self._hard_critical_signals()
#         ]
#         if critical_missing:
#             return self._dedupe_strings(critical_missing)
#         return []

#     def _recommendation_mode(
#         self,
#         readiness,
#         recommendations,
#         fallback_reason,
#         expert_review_reason,
#         clarification_required_reasons,
#         candidate_pool_size=0,
#     ):
#         readiness = dict(readiness or {})
#         recommendations = list(recommendations or [])
#         clarification_required_reasons = list(clarification_required_reasons or [])
#         mode_policy = self.config_service.get_recommendation_mode_policy()
#         expert_review_fallback_reasons = set(mode_policy.get("expert_review_fallback_reasons") or [])
#         minimum_safe_candidate_count = int(mode_policy.get("minimum_safe_candidate_count") or 0)
#         max_hard_critical_for_clarification = int(
#             mode_policy.get("max_hard_critical_reasons_for_clarification") or 0
#         )
#         max_hard_critical_for_provisional = int(
#             mode_policy.get("max_hard_critical_reasons_for_provisional") or 0
#         )
#         hard_critical_reasons = self._hard_critical_reasons(readiness, clarification_required_reasons)
#         ranking_deferred = self.clarification_service.should_defer_ranking(readiness)
#         insufficient_candidates = minimum_safe_candidate_count > 0 and int(candidate_pool_size or 0) < minimum_safe_candidate_count

#         if not recommendations:
#             if fallback_reason in expert_review_fallback_reasons:
#                 return "expert_review_recommended"
#             if insufficient_candidates:
#                 return "expert_review_recommended"
#             if ranking_deferred:
#                 return (
#                     "clarification_required"
#                     if clarification_required_reasons and len(hard_critical_reasons) <= max_hard_critical_for_clarification
#                     else "expert_review_recommended"
#                 )
#             if expert_review_reason:
#                 return "expert_review_recommended"
#             return (
#                 "clarification_required"
#                 if clarification_required_reasons and len(hard_critical_reasons) <= max_hard_critical_for_clarification
#                 else "expert_review_recommended"
#             )

#         if clarification_required_reasons:
#             if insufficient_candidates:
#                 return "expert_review_recommended"
#             if len(hard_critical_reasons) > max_hard_critical_for_provisional:
#                 return "expert_review_recommended"
#             return "provisional_recommendation"
#         if expert_review_reason or insufficient_candidates:
#             return "expert_review_recommended"
#         return "firm_recommendation"

#     def _build_decision_trace(
#         self,
#         decision_trace_id,
#         requirements,
#         extracted_schema,
#         target_profile,
#         readiness,
#         retrieval_result,
#         catalog_validation_result,
#         compatibility_result,
#         policy_result,
#         recommendations,
#         fallback_reason,
#         recommendation_mode,
#         clarification_required_reasons,
#         expert_review_reason,
#         feature_flags,
#         decision_policy_profile,
#         check_requirement_summary,
#         editable_inferred_values,
#         template_candidates,
#         selected_template,
#     ):
#         return {
#             "decision_trace_id": decision_trace_id,
            
#             "catalog_validation": {
#                 "summary": catalog_validation_result.get("summary") or {},
#                 "rejected_products": catalog_validation_result.get("rejected_products") or [],
#             },
#             "retrieval": retrieval_result,
#             "compatibility": {
#                 "scope": (compatibility_result.get("summary") or {}).get("compatibility_scope") or "item",
#                 "summary": compatibility_result.get("summary") or {},
#                 "rejected_products": compatibility_result.get("rejected_products") or [],
#             },
#             "policy": {
#                 "summary": policy_result.get("summary") or {},
#                 "rejected_products": policy_result.get("rejected_products") or [],
#             },
#             "expert_review_reason": expert_review_reason,
#             "feature_flags": feature_flags,
#             "config_versions": self.config_service.get_versions(),
#         }

#     def _hard_critical_signals(self):
#         signals = self.config_service.get_recommendation_mode_policy().get("hard_critical_signals") or []
#         return set(self._dedupe_strings(signals))

#     def _hard_critical_reasons(self, readiness, clarification_required_reasons):
#         hard_critical_signals = self._hard_critical_signals()
#         return self._dedupe_strings(
#             [
#                 reason
#                 for reason in (clarification_required_reasons or []) + list((readiness or {}).get("missing_signals") or [])
#                 if reason in hard_critical_signals
#             ]
#         )


##################################################################################
###################################################################################
###################################################################################

# import os
# from concurrent.futures import ThreadPoolExecutor
# from time import perf_counter
# from uuid import uuid4

# from ...catalog.services.normalization import normalize_product_document
# from ...catalog.services.repository import build_runtime_catalog_repository
# from ...catalog.services.semantic_retriever import SemanticProductRetriever

# from .explanations import ProcurementExplanationService
# from .feature_flags import ProcurementFeatureFlagService
# from .followup_generation import AdaptiveFollowUpService
# from .intake import RequirementIntakeService
# from .observability import ProcurementRuntimeObservabilityService
# from .policy import ProcurementPolicyService
# from .ranking import ProductRankingService
# from .recommendation_context import (
#     PreparedCatalogState,
#     PreparedProcurementContext,
#     RecommendationContextBuilder,
#     RecommendationCoreResult,
# )
# from .recommendation_core import RecommendationCoreEngine
# from .recommendation_presenter import RecommendationPresenter
# from .review_support import ProcurementReviewSupportService
# from .requirement_extraction import RequirementExtractionService
# from .rules_engine import ProcurementRulesEngine
# from .clarification import ProcurementClarificationService
# from .bundle_service import ProcurementBundleService
# from .compatibility import ProcurementCompatibilityService
# from .config_service import ProcurementConfigService
# from .multi_intent import ProcurementMultiIntentService
# from .multi_intent_policy import ProcurementMultiIntentPolicyService
# from .template_service import ProcurementTemplateService


# ENGINE_VERSION = "phase1-v8"

# class ProcurementRecommendationService:
#     _persistence_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="procurement-persist")

#     def __init__(
#         self,
#         catalog_repository=None,
#         config_service=None,
#         intake_service=None,
#         rules_engine=None,
#         ranking_service=None,
#         policy_service=None,
#         compatibility_service=None,
#         explanation_service=None,
#         clarification_service=None,
#         extraction_service=None,
#         semantic_retriever=None,
#         followup_service=None,
#         feature_flag_service=None,
#         multi_intent_service=None,
#         multi_intent_policy_service=None,
#         observability_service=None,
#         bundle_service=None,
#         template_service=None,
#         review_support_service=None,
#     ):
#         self.catalog_repository = catalog_repository or build_runtime_catalog_repository()
#         self.config_service = config_service or ProcurementConfigService()
#         self.intake_service = intake_service or RequirementIntakeService()
#         self.rules_engine = rules_engine or ProcurementRulesEngine(config_service=self.config_service)
#         self.ranking_service = ranking_service or ProductRankingService(config_service=self.config_service)
#         self.policy_service = policy_service or ProcurementPolicyService(config_service=self.config_service)
#         self.compatibility_service = compatibility_service or ProcurementCompatibilityService(config_service=self.config_service)
#         self.explanation_service = explanation_service or ProcurementExplanationService(config_service=self.config_service)
#         self.clarification_service = clarification_service or ProcurementClarificationService(config_service=self.config_service)
#         self.extraction_service = extraction_service or RequirementExtractionService()
#         self.semantic_retriever = semantic_retriever or SemanticProductRetriever()
#         self.followup_service = followup_service or AdaptiveFollowUpService()
#         self.feature_flag_service = feature_flag_service or ProcurementFeatureFlagService()
#         self.multi_intent_service = multi_intent_service or ProcurementMultiIntentService(
#             extraction_service=self.extraction_service
#         )
#         self.multi_intent_policy_service = multi_intent_policy_service or ProcurementMultiIntentPolicyService()
#         self.observability_service = observability_service or ProcurementRuntimeObservabilityService(
#             config_service=self.config_service
#         )
#         self.bundle_service = bundle_service or ProcurementBundleService(
#             compatibility_service=self.compatibility_service
#         )
#         self.template_service = template_service or ProcurementTemplateService(config_service=self.config_service)
#         self.review_support_service = review_support_service or ProcurementReviewSupportService()
#         self._prepared_catalog_state_cache = {}
#         self.context_builder = RecommendationContextBuilder(self)
#         self.core_engine = RecommendationCoreEngine(self)
#         self.presenter = RecommendationPresenter(self)

#     def has_minimum_context(self, payload):
#         requirements = self.intake_service.normalize(payload)
#         readiness = self.clarification_service.assess(requirements)
#         return bool(requirements.get("budget") is not None and not self.clarification_service.should_defer_ranking(readiness))

#     def _new_top_level_timings(self, source_mode=""):
#         prepare_ms = {"total_ms": 0.0}
#         if source_mode:
#             prepare_ms["source_mode"] = str(source_mode)
#         return {
#             "prepare_ms": prepare_ms,
#             "core_ms": {
#                 "total_ms": 0.0,
#                 "multi_intent_detect_ms": 0.0,
#                 "catalog_fetch_ms": 0.0,
#                 "compatibility_ms": 0.0,
#                 "policy_ms": 0.0,
#                 "ranking_ms": 0.0,
#                 "explanations_ms": 0.0,
#                 "response_assembly_ms": 0.0,
#             },
#             "presentation_ms": {
#                 "assembly_ms": 0.0,
#                 "question_generation_ms": 0.0,
#                 "narrative_ms": 0.0,
#                 "persistence_dispatch_ms": 0.0,
#                 "total_ms": 0.0,
#             },
#             "pipeline_ms": {"total_ms": 0.0},
#         }

#     def _finalize_top_level_timings(self, top_level_timings, pipeline_started_at=None, response=None):
#         top_level_timings = dict(top_level_timings or {})
#         core_ms = dict(top_level_timings.get("core_ms") or {})
#         presentation_ms = dict(top_level_timings.get("presentation_ms") or {})
#         stage_timings = dict((((response or {}).get("meta") or {}).get("stage_timings_ms") or {}))
#         core_ms["catalog_fetch_ms"] = round(float(stage_timings.get("catalog_fetch_ms") or core_ms.get("catalog_fetch_ms") or 0.0), 2)
#         core_ms["compatibility_ms"] = round(float(stage_timings.get("compatibility_ms") or core_ms.get("compatibility_ms") or 0.0), 2)
#         core_ms["policy_ms"] = round(float(stage_timings.get("policy_ms") or core_ms.get("policy_ms") or 0.0), 2)
#         core_ms["ranking_ms"] = round(float(stage_timings.get("ranking_ms") or core_ms.get("ranking_ms") or 0.0), 2)
#         core_ms["explanations_ms"] = round(float(stage_timings.get("explanations_ms") or core_ms.get("explanations_ms") or 0.0), 2)
#         core_ms["response_assembly_ms"] = round(
#             float(stage_timings.get("response_assembly_ms") or core_ms.get("response_assembly_ms") or 0.0),
#             2,
#         )
#         top_level_timings["core_ms"] = core_ms
#         question_generation_ms = float(stage_timings.get("question_generation_ms") or presentation_ms.get("question_generation_ms") or 0.0)
#         presentation_ms["question_generation_ms"] = round(question_generation_ms, 2)
#         presentation_ms["total_ms"] = round(
#             sum(
#                 float(presentation_ms.get(key) or 0.0)
#                 for key in ("assembly_ms", "question_generation_ms", "narrative_ms", "persistence_dispatch_ms")
#             ),
#             2,
#         )
#         top_level_timings["presentation_ms"] = presentation_ms
#         if pipeline_started_at is not None:
#             self._mark_stage(top_level_timings.setdefault("pipeline_ms", {}), "total_ms", pipeline_started_at)
#         return top_level_timings

#     def recommend(self, payload, user_id="", business_id="", persist=True):
#         payload = dict(payload or {})
#         feature_flags = dict(self.feature_flag_service.get_flags())
#         if str(payload.get("channel") or "").strip().lower() == "websocket":
#             persist = False
#         pipeline_started_at = perf_counter()
#         top_level_timings = self._new_top_level_timings()

#         prepare_started_at = perf_counter()
#         prepared = self.prepare_from_raw_payload(payload, feature_flags=feature_flags)
#         self._mark_stage(top_level_timings["prepare_ms"], "total_ms", prepare_started_at)

#         detect_started_at = perf_counter()
#         multi_intent_result = self.multi_intent_service.detect(payload, prepared.extracted_schema)
#         self._mark_stage(top_level_timings["core_ms"], "multi_intent_detect_ms", detect_started_at)
#         if multi_intent_result.get("is_multi_intent"):
#             response = self._recommend_multi_intent(
#                 payload=payload,
#                 multi_intent_result=multi_intent_result,
#                 extracted_schema=prepared.extracted_schema,
#                 feature_flags=feature_flags,
#                 user_id=user_id,
#                 business_id=business_id,
#                 persist=persist,
#                 prepared_context=prepared,
#                 top_level_timings=top_level_timings,
#             )
#         else:
#             response = self._recommend_single(
#                 payload=payload,
#                 extracted_schema=prepared.extracted_schema,
#                 prepared_context=prepared,
#                 feature_flags=feature_flags,
#                 user_id=user_id,
#                 business_id=business_id,
#                 persist=persist,
#                 top_level_timings=top_level_timings,
#             )
#         top_level_timings = self._finalize_top_level_timings(
#             top_level_timings,
#             pipeline_started_at=pipeline_started_at,
#             response=response,
#         )
#         response.setdefault("meta", {})
#         response["meta"]["top_level_timings_ms"] = top_level_timings
#         return response

#     def prepare_from_raw_payload(self, payload, feature_flags=None, decision_trace_id=None):
#         return self.context_builder.prepare_from_raw_payload(
#             payload=payload,
#             feature_flags=feature_flags,
#             decision_trace_id=decision_trace_id,
#         )

#     def prepare_from_extracted_schema(
#         self,
#         payload,
#         extracted_schema,
#         feature_flags=None,
#         decision_trace_id=None,
#         source_mode="extracted_schema",
#         prepared_catalog_state=None,
#     ):
#         return self.context_builder.prepare_from_extracted_schema(
#             payload=payload,
#             extracted_schema=extracted_schema,
#             feature_flags=feature_flags,
#             decision_trace_id=decision_trace_id,
#             source_mode=source_mode,
#             prepared_catalog_state=prepared_catalog_state,
#         )

#     def recommend_prepared_context(
#         self,
#         prepared_context,
#         feature_flags=None,
#         user_id="",
#         business_id="",
#         persist=True,
#         capture_runtime_observability=True,
#     ):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         pipeline_started_at = perf_counter()
#         top_level_timings = self._new_top_level_timings(source_mode=prepared_context.source_mode)
#         if str(prepared_context.channel or "").strip().lower() == "websocket":
#             persist = False
#         detect_started_at = perf_counter()
#         multi_intent_result = self.core_engine.detect_multi_intent(
#             prepared_context.normalized_payload,
#             prepared_context.extracted_schema,
#         )
#         self._mark_stage(top_level_timings["core_ms"], "multi_intent_detect_ms", detect_started_at)
#         if multi_intent_result.get("is_multi_intent"):
#             response = self._recommend_multi_intent(
#                 payload=prepared_context.normalized_payload,
#                 multi_intent_result=multi_intent_result,
#                 extracted_schema=prepared_context.extracted_schema,
#                 prepared_context=prepared_context,
#                 feature_flags=feature_flags,
#                 user_id=user_id,
#                 business_id=business_id,
#                 persist=persist,
#                 top_level_timings=top_level_timings,
#             )
#         else:
#             response = self._recommend_single_from_prepared(
#                 prepared_context=prepared_context,
#                 feature_flags=feature_flags,
#                 user_id=user_id,
#                 business_id=business_id,
#                 persist=persist,
#                 capture_runtime_observability=capture_runtime_observability,
#                 top_level_timings=top_level_timings,
#             )
#         top_level_timings = self._finalize_top_level_timings(
#             top_level_timings,
#             pipeline_started_at=pipeline_started_at,
#             response=response,
#         )
#         response.setdefault("meta", {})
#         response["meta"]["top_level_timings_ms"] = top_level_timings
#         return response

#     def recommend_from_chat_preferences(self, chat_preferences, store_id="", persist=False):
#         chat_preferences = dict(chat_preferences or {})
#         payload = {
#             "store_id": chat_preferences.get("store_id") or store_id or "",
#             "channel": "websocket",
#             "currency": chat_preferences.get("currency", "INR"),
#             "category": chat_preferences.get("category") or chat_preferences.get("preferred_category"),
#             "industry": chat_preferences.get("industry"),
#             "business_type": chat_preferences.get("business_type"),
#             "team_size": chat_preferences.get("team_size"),
#             "workload_types": chat_preferences.get("workloads") or chat_preferences.get("workload_types"),
#             "application_signals": chat_preferences.get("application_signals") or [],
#             "capability_tags": chat_preferences.get("capability_tags") or [],
#             "budget": chat_preferences.get("budget"),
#             "budget_scope": chat_preferences.get("budget_scope"),
#             "growth_expectation": chat_preferences.get("growth_expectation"),
#             "existing_infrastructure": chat_preferences.get("existing_infrastructure") or [],
#             "preferred_manufacturers": chat_preferences.get("preferred_manufacturers") or [],
#             "blocked_manufacturers": chat_preferences.get("blocked_manufacturers") or [],
#             "preferred_sellers": chat_preferences.get("preferred_sellers") or [],
#             "blocked_sellers": chat_preferences.get("blocked_sellers") or [],
#             "requested_ram": chat_preferences.get("specifications.ram_size"),
#             "requested_storage": chat_preferences.get("specifications.storage_size"),
#             "requested_ram_is_minimum": chat_preferences.get("requested_ram_is_minimum"),
#             "requested_storage_is_minimum": chat_preferences.get("requested_storage_is_minimum"),
#             "minimum_warranty_years": chat_preferences.get("minimum_warranty_years"),
#             "required_port_count": chat_preferences.get("required_port_count"),
#             "required_throughput_mbps": chat_preferences.get("required_throughput_mbps"),
#             "required_duplex_printing": chat_preferences.get("required_duplex_printing"),
#             "required_scanner": chat_preferences.get("required_scanner"),
#             "min_print_speed_ppm": chat_preferences.get("min_print_speed_ppm"),
#             "required_printer_type": chat_preferences.get("required_printer_type"),
#             "required_print_technology": chat_preferences.get("required_print_technology"),
#             "required_color_output": chat_preferences.get("required_color_output"),
#             "min_monthly_duty_cycle_pages": chat_preferences.get("min_monthly_duty_cycle_pages"),
#             "required_automatic_document_feeder": chat_preferences.get("required_automatic_document_feeder"),
#             "required_paper_sizes": chat_preferences.get("required_paper_sizes"),
#             "required_network_roles": chat_preferences.get("required_network_roles"),
#             "required_vpn_user_capacity": chat_preferences.get("required_vpn_user_capacity"),
#             "required_virtualization_ready": chat_preferences.get("required_virtualization_ready"),
#             "required_virtualization_platforms": chat_preferences.get("required_virtualization_platforms"),
#             "max_rack_units": chat_preferences.get("max_rack_units"),
#             "max_power_draw_watts": chat_preferences.get("max_power_draw_watts"),
#             "battery_life_hours_min": chat_preferences.get("battery_life_hours_min"),
#             "cpu_preference": chat_preferences.get("cpu_preference"),
#             "gpu_requirement": chat_preferences.get("gpu_requirement"),
#             "screen_size_preference": chat_preferences.get("screen_size_preference"),
#             "weight_kg_max": chat_preferences.get("weight_kg_max"),
#             "warranty_type_preference": chat_preferences.get("warranty_type_preference"),
#             "performance_priority": chat_preferences.get("performance_priority"),
#             "portability_need": chat_preferences.get("portability_need"),
#             "support_expectation": chat_preferences.get("support_expectation"),
#             "availability_need": chat_preferences.get("availability_need"),
#             "require_returnable": chat_preferences.get("require_returnable"),
#             "quantity": chat_preferences.get("quantity"),
#             "purchase_scope": chat_preferences.get("purchase_scope"),
#             "timeline": chat_preferences.get("timeline"),
#             "raw_chat": chat_preferences.get("raw_chat", ""),
#             "notes": chat_preferences.get("notes", ""),
#             "extracted_schema": dict(chat_preferences),
#         }
#         prepared_context = self.prepare_from_extracted_schema(
#             payload=payload,
#             extracted_schema=dict(chat_preferences),
#             source_mode="chat_preferences",
#         )
#         return self.recommend_prepared_context(prepared_context, persist=persist)

#     def _recommend_single(
#         self,
#         payload,
#         extracted_schema=None,
#         prepared_context=None,
#         feature_flags=None,
#         user_id="",
#         business_id="",
#         persist=True,
#         decision_trace_id=None,
#         capture_runtime_observability=True,
#         top_level_timings=None,
#     ):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         payload = dict(payload or {})
#         top_level_timings = top_level_timings or self._new_top_level_timings()
#         if prepared_context is None:
#             prepare_started_at = perf_counter()
#             prepared_context = self.prepare_from_extracted_schema(
#                 payload=payload,
#                 extracted_schema=dict(extracted_schema or self._extract_schema(payload)),
#                 feature_flags=feature_flags,
#                 decision_trace_id=decision_trace_id,
#             )
#             self._mark_stage(top_level_timings["prepare_ms"], "total_ms", prepare_started_at)
#         return self._recommend_single_from_prepared(
#             prepared_context=prepared_context,
#             feature_flags=feature_flags,
#             user_id=user_id,
#             business_id=business_id,
#             persist=persist,
#             capture_runtime_observability=capture_runtime_observability,
#             top_level_timings=top_level_timings,
#         )

#     def _recommend_single_from_prepared(
#         self,
#         prepared_context,
#         feature_flags=None,
#         user_id="",
#         business_id="",
#         persist=True,
#         capture_runtime_observability=True,
#         top_level_timings=None,
#     ):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         top_level_timings = top_level_timings or self._new_top_level_timings()
#         started_at = self.observability_service.start_timer() if capture_runtime_observability else None
#         core_started_at = perf_counter()
#         core_result, debug_trace = self.core_engine.run(
#             prepared_context,
#             feature_flags=feature_flags,
#             defer_explanations=bool(prepared_context.normalized_payload.get("_defer_explanations")),
#         )
#         self._mark_stage(top_level_timings["core_ms"], "total_ms", core_started_at)
#         assembly_started_at = perf_counter()
#         response = self.presenter.assemble(
#             prepared_context=prepared_context,
#             core_result=core_result,
#             debug_trace=debug_trace,
#             feature_flags=feature_flags,
#             started_at=started_at,
#             capture_runtime_observability=capture_runtime_observability,
#         )
#         self._mark_stage(top_level_timings["presentation_ms"], "assembly_ms", assembly_started_at)
#         question_generation_ms = float(
#             (((response.get("meta") or {}).get("stage_timings_ms") or {}).get("question_generation_ms"))
#             or 0.0
#         )
#         top_level_timings["presentation_ms"]["question_generation_ms"] = round(question_generation_ms, 2)
#         if question_generation_ms:
#             top_level_timings["presentation_ms"]["assembly_ms"] = max(
#                 round(float(top_level_timings["presentation_ms"]["assembly_ms"]) - question_generation_ms, 2),
#                 0.0,
#             )
#         narrative_started_at = perf_counter()
#         response = self.presenter.enrich(
#             prepared_context=prepared_context,
#             response=response,
#             feature_flags=feature_flags,
#         )
#         self._mark_stage(top_level_timings["presentation_ms"], "narrative_ms", narrative_started_at)
#         persistence_started_at = perf_counter()
#         if persist:
#             self._dispatch_persistence_from_outputs(
#                 prepared_context=prepared_context,
#                 response=response,
#                 user_id=user_id,
#                 business_id=business_id,
#             )
#         self._mark_stage(top_level_timings["presentation_ms"], "persistence_dispatch_ms", persistence_started_at)
#         top_level_timings["presentation_ms"]["total_ms"] = round(
#             sum(
#                 float(top_level_timings["presentation_ms"].get(key) or 0.0)
#                 for key in ("assembly_ms", "question_generation_ms", "narrative_ms", "persistence_dispatch_ms")
#             ),
#             2,
#         )
#         return response

#     def recommend_from_state(
#         self,
#         state: dict,
#         user_id="",
#         business_id="",
#         persist=False,
#     ):
#         raw_state = dict(state or {})
#         requirements = dict(raw_state.get("requirements") or raw_state)
#         conversation_meta = dict(raw_state.get("conversation_meta") or {})

#         for field in ("intent_groups", "preferred_categories", "preferred_category", "budget", "budget_scope", "team_size", "quantity"):
#             value = raw_state.get(field)
#             if value not in (None, "", [], {}) and requirements.get(field) in (None, "", [], {}):
#                 requirements[field] = value

#         if requirements.get("raw_chat") in (None, ""):
#             brief = str(conversation_meta.get("conversation_brief") or "").strip()
#             if brief:
#                 requirements["raw_chat"] = brief

#         payload = dict(requirements)
#         payload.setdefault("channel", "websocket")
#         payload.setdefault("_defer_explanations", True)
#         prepared_context = self.prepare_from_extracted_schema(
#             payload=payload,
#             extracted_schema=requirements,
#             source_mode="planner_state",
#         )
#         return self.recommend_prepared_context(
#             prepared_context,
#             user_id=user_id,
#             business_id=business_id,
#             persist=persist,
#         )

#     def _build_budget_fit_summary(self, requirements, recommendations):
#         budget = requirements.get("budget")
#         if budget is None:
#             return {
#                 "budget_present": False,
#                 "within_budget_count": 0,
#                 "over_budget_count": 0,
#                 "no_exact_budget_fit": False,
#             }
#         quantity = requirements.get("quantity") or requirements.get("team_size") or 1
#         budget_scope = requirements.get("budget_scope")
#         within_budget_count = 0
#         over_budget_count = 0
#         for recommendation in list(recommendations or []):
#             price = recommendation.get("price")
#             total_cost = recommendation.get("estimated_total_cost")
#             reference = self.ranking_service._budget_reference(price, budget_scope, quantity, total_cost)
#             if reference is None:
#                 continue
#             if reference <= budget:
#                 within_budget_count += 1
#             else:
#                 over_budget_count += 1
#         return {
#             "budget_present": True,
#             "within_budget_count": within_budget_count,
#             "over_budget_count": over_budget_count,
#             "no_exact_budget_fit": bool(recommendations) and within_budget_count == 0,
#         }

#     def _prefix_no_exact_budget_fit_summary(self, summary, requirements, recommendations):
#         if not recommendations:
#             return str(summary or "").strip()
#         currency = str(requirements.get("currency") or "INR").strip() or "INR"
#         budget = requirements.get("budget")
#         quantity = requirements.get("quantity") or requirements.get("team_size") or 1
#         budget_scope = str(requirements.get("budget_scope") or "").replace("_", " ").strip()
#         if not budget_scope and int(quantity or 1) > 1:
#             base = (
#                 f"No exact fit could be validated against the stated budget of {budget} {currency} because the budget scope is ambiguous for {quantity} units. "
#                 "Showing the closest stretch options until you confirm whether the budget is per unit or project total."
#             )
#         else:
#             budget_scope = budget_scope or "budget"
#             base = f"No exact in-catalog fit was found within the stated {budget_scope} budget of {budget} {currency}. Showing the closest stretch options and their trade-offs."
#         summary = str(summary or "").strip()
#         if not summary:
#             return base
#         if summary.lower().startswith("no exact in-catalog fit") or summary.lower().startswith("no exact fit could be validated"):
#             return summary
#         return f"{base} {summary}".strip()

#     def _annotate_no_exact_budget_fit_recommendations(self, requirements, recommendations):
#         requirements = dict(requirements or {})
#         currency = str(requirements.get("currency") or "INR").strip() or "INR"
#         budget = requirements.get("budget")
#         quantity = requirements.get("quantity") or requirements.get("team_size") or 1
#         budget_scope = requirements.get("budget_scope")
#         annotated = []
#         for recommendation in list(recommendations or []):
#             item = dict(recommendation or {})
#             price = item.get("price")
#             total_cost = item.get("estimated_total_cost")
#             reference = self.ranking_service._budget_reference(price, budget_scope, quantity, total_cost)
#             note = ""
#             if reference is None:
#                 if int(quantity or 1) > 1 and not budget_scope:
#                     note = (
#                         f"Budget scope is ambiguous for {quantity} units; this is shown as a closest option until you confirm whether {budget} {currency} is per unit or project total."
#                     )
#             elif budget is not None and reference > budget:
#                 scope_label = str(budget_scope or ("project_total" if int(quantity or 1) > 1 else "budget")).replace("_", " ")
#                 note = f"Exceeds the stated {scope_label} budget of {budget} {currency}; shown as a closest stretch option."
#             if note:
#                 reasons = list(item.get("reasons") or [])
#                 if note not in reasons:
#                     reasons.insert(0, note)
#                 item["reasons"] = reasons
#                 item["fit_status"] = "stretch"
#             annotated.append(item)
#         return annotated

#     def _mark_stage(self, stage_timings, stage_name, started_at):
#         stage_timings[stage_name] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)

#     def _set_stage_total(self, stage_timings, stage_name, values):
#         values = [float(value or 0.0) for value in list(values or [])]
#         stage_timings[stage_name] = round(sum(values), 2)

#     def _hydrate_stage_aliases(self, stage_timings):
#         stage_timings = dict(stage_timings or {})
#         self._set_stage_total(
#             stage_timings,
#             "catalog_fetch_ms",
#             [
#                 stage_timings.get("catalog_state_access_ms"),
#                 stage_timings.get("category_subset_resolution_ms"),
#                 stage_timings.get("candidate_selection_ms"),
#             ],
#         )
#         self._set_stage_total(
#             stage_timings,
#             "compatibility_policy_ms",
#             [
#                 stage_timings.get("compatibility_ms"),
#                 stage_timings.get("policy_ms"),
#             ],
#         )
#         return stage_timings

#     def run_recommendation_core(self, prepared_context, feature_flags=None, defer_explanations=False):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         requirements = dict(prepared_context.requirements or {})
#         target_profile = dict(prepared_context.target_profile or {})
#         readiness = dict(prepared_context.readiness or {})
#         prepared_catalog_state = prepared_context.prepared_catalog_state or self._resolve_prepared_catalog_state(requirements)
#         stage_timings = {}
#         ranking_deferred = self.clarification_service.should_defer_ranking(readiness)
#         deferred_reason = ""
#         normalized_products = []
#         candidate_ids = []
#         retrieval_result = {"candidate_ids": [], "scored_candidates": [], "fallback_reason": None}
#         compatibility_result = {"eligible_products": [], "rejected_products": [], "summary": {}, "reports_by_product_id": {}}
#         policy_result = {"eligible_products": [], "rejected_products": [], "summary": {}}
#         rankable_products = []
#         recommendations = []
#         fallback_reason = ""
#         catalog_validation_result = {"eligible_products": [], "rejected_products": [], "summary": {}}
#         raw_products = []
#         all_normalized_products = []
#         currency_fallback_used = False
#         catalog_source_snapshot = {}
#         store_scope_applied = False

#         if ranking_deferred:
#             deferred_reason = "blocking_clarification_required"
#             fallback_reason = deferred_reason
#         else:
#             stage_started_at = perf_counter()
#             raw_products = list(prepared_catalog_state.raw_products or [])
#             all_normalized_products = list(prepared_catalog_state.normalized_products or [])
#             catalog_validation_result = dict(prepared_catalog_state.catalog_validation_result or {})
#             currency_fallback_used = bool(prepared_catalog_state.currency_fallback_used)
#             catalog_source_snapshot = dict(prepared_catalog_state.catalog_source_snapshot or {})
#             store_scope_applied = bool(prepared_catalog_state.store_scope_applied)
#             self._mark_stage(stage_timings, "catalog_state_access_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             category_filtered_products, subset_key = self._resolve_category_subset_from_state(
#                 prepared_catalog_state,
#                 target_profile.get("categories"),
#             )
#             self._mark_stage(stage_timings, "category_subset_resolution_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             if feature_flags.get("semantic_retrieval", True):
#                 retrieval_assets = (prepared_catalog_state.retrieval_assets_by_subset or {}).get(subset_key)
#                 if retrieval_assets is None and subset_key != "__all__":
#                     retrieval_assets = self.semantic_retriever.build_retrieval_assets(category_filtered_products)
#                 retrieval_result = self.semantic_retriever.retrieve_candidates_from_assets(
#                     retrieval_assets,
#                     requirements,
#                     target_profile,
#                     top_k=40,
#                     allow_broadening=feature_flags.get("retrieval_broadening", True),
#                 )
#                 candidate_ids = list(retrieval_result.get("candidate_ids") or [])
#                 normalized_products = self._filter_normalized_products(
#                     category_filtered_products,
#                     None,
#                     candidate_ids,
#                 )
#             else:
#                 retrieval_result = self._deterministic_candidate_pool(category_filtered_products, top_k=40)
#                 candidate_ids = list(retrieval_result.get("candidate_ids") or [])
#                 normalized_products = category_filtered_products[:40]
#             self._mark_stage(stage_timings, "candidate_selection_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             if feature_flags.get("compatibility_filtering", True):
#                 compatibility_result = self.compatibility_service.evaluate(
#                     normalized_products,
#                     requirements,
#                     target_profile,
#                 )
#             else:
#                 compatibility_result = self._compatibility_bypass(normalized_products)
#             self._mark_stage(stage_timings, "compatibility_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             policy_result = self.policy_service.apply_filters(
#                 compatibility_result.get("eligible_products") or [],
#                 requirements,
#                 target_profile,
#             )
#             rankable_products = policy_result.get("eligible_products") or []
#             self._mark_stage(stage_timings, "policy_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             recommendations = self.ranking_service.rank_products(
#                 rankable_products,
#                 requirements,
#                 target_profile,
#             )
#             self._mark_stage(stage_timings, "ranking_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             if not defer_explanations:
#                 recommendations = self.explanation_service.enrich_recommendations(
#                     requirements,
#                     target_profile,
#                     recommendations,
#                     allow_llm=feature_flags.get("explanation_llm", False),
#                 )
#             self._mark_stage(stage_timings, "explanations_ms", stage_started_at)

#             fallback_reason = str(retrieval_result.get("fallback_reason") or "")
#             if not recommendations:
#                 if compatibility_result.get("rejected_products") and not compatibility_result.get("eligible_products"):
#                     fallback_reason = "compatibility_blocked_all"
#                 elif policy_result.get("rejected_products") and not rankable_products:
#                     fallback_reason = "policy_rejected_all"
#                 elif not rankable_products:
#                     fallback_reason = fallback_reason or "no_exact_fit"

#         stage_timings = self._hydrate_stage_aliases(stage_timings)

#         debug_trace = {
#             "deferred_reason": deferred_reason,
#             "retrieval_result": retrieval_result,
#             "compatibility_result": compatibility_result,
#             "policy_result": policy_result,
#             "catalog_validation_result": catalog_validation_result,
#             "raw_products": raw_products,
#             "all_normalized_products": all_normalized_products,
#             "currency_fallback_used": currency_fallback_used,
#             "catalog_source_snapshot": catalog_source_snapshot,
#             "store_scope_applied": store_scope_applied,
#             "rankable_products": rankable_products,
#             "prepared_catalog_cache_key": getattr(prepared_catalog_state, "cache_key", ""),
#         }
#         return RecommendationCoreResult(
#             ranking_deferred=bool(ranking_deferred),
#             shortlisted_product_ids=list(candidate_ids),
#             ranked_recommendations=list(recommendations),
#             fallback_reason=str(fallback_reason or ""),
#             stage_timings_ms=stage_timings,
#         ), debug_trace

#     def assemble_response(
#         self,
#         prepared_context,
#         core_result,
#         debug_trace,
#         feature_flags=None,
#         started_at=None,
#         capture_runtime_observability=True,
#     ):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         requirements = dict(prepared_context.requirements or {})
#         target_profile = dict(prepared_context.target_profile or {})
#         readiness = dict(prepared_context.readiness or {})
#         recommendations = [dict(item) for item in list(core_result.ranked_recommendations or [])]
#         stage_timings = dict(core_result.stage_timings_ms or {})
#         stage_started_at = perf_counter()
#         for recommendation in recommendations:
#             recommendation["buy_url"] = self._build_buy_url(recommendation.get("product_id"))

#         compatibility_result = dict(debug_trace.get("compatibility_result") or {})
#         policy_result = dict(debug_trace.get("policy_result") or {})
#         retrieval_result = dict(debug_trace.get("retrieval_result") or {})
#         catalog_validation_result = dict(debug_trace.get("catalog_validation_result") or {})
#         raw_products = list(debug_trace.get("raw_products") or [])
#         all_normalized_products = list(debug_trace.get("all_normalized_products") or [])
#         currency_fallback_used = bool(debug_trace.get("currency_fallback_used"))
#         catalog_source_snapshot = dict(debug_trace.get("catalog_source_snapshot") or {})
#         store_scope_applied = bool(debug_trace.get("store_scope_applied"))
#         deferred_reason = str(debug_trace.get("deferred_reason") or "")
#         rankable_products = list(debug_trace.get("rankable_products") or [])

#         summary = (
#             target_profile.get("summary")
#             if core_result.ranking_deferred
#             else self.explanation_service.build_summary(requirements, target_profile, recommendations)
#         )
#         budget_fit_summary = self._build_budget_fit_summary(requirements, recommendations)
#         if budget_fit_summary.get("no_exact_budget_fit"):
#             recommendations = self._annotate_no_exact_budget_fit_recommendations(requirements, recommendations)
#             summary = self._prefix_no_exact_budget_fit_summary(summary, requirements, recommendations)
#         expert_review_reason = self._expert_review_reason(
#             readiness,
#             core_result.ranking_deferred,
#             core_result.fallback_reason,
#             compatibility_result,
#             recommendations,
#         )
#         expert_review_reason = self._apply_template_review_reason(prepared_context.selected_template, expert_review_reason)
#         clarification_required_reasons = self._clarification_required_reasons(readiness)
#         decision_policy_profile = self.config_service.get_decision_policy_profile()
#         recommendation_mode = self._recommendation_mode(
#             readiness=readiness,
#             recommendations=recommendations,
#             fallback_reason=core_result.fallback_reason,
#             expert_review_reason=expert_review_reason,
#             clarification_required_reasons=clarification_required_reasons,
#             candidate_pool_size=len(rankable_products),
#         )
#         recommendation_mode = self._apply_template_selection_mode(prepared_context.selected_template, recommendation_mode)
#         requirements["review_state"] = self.review_support_service.enrich_review_state(
#             requirements=requirements,
#             readiness=readiness,
#             template_candidates=prepared_context.template_candidates,
#             recommendation_mode=recommendation_mode,
#         )
#         check_requirement_summary = self.review_support_service.build_check_requirement_summary(
#             requirements=requirements,
#             readiness=readiness,
#             template_candidates=prepared_context.template_candidates,
#             recommendation_mode=recommendation_mode,
#         )
#         editable_inferred_values = self.review_support_service.build_editable_inferred_values(requirements)
#         catalog_observability = self._build_catalog_observability(
#             raw_products=raw_products,
#             normalized_products=all_normalized_products,
#             catalog_validation_result=catalog_validation_result,
#             requirements=requirements,
#             currency_fallback_used=currency_fallback_used,
#             catalog_source_snapshot=catalog_source_snapshot,
#             store_scope_applied=store_scope_applied,
#         )
#         self._mark_stage(stage_timings, "response_assembly_ms", stage_started_at)
#         response = {
#             "decision_trace_id": prepared_context.decision_trace_id,
#             "requirements": requirements,
#             "field_state": requirements.get("field_state") or {},
#             "field_source": requirements.get("field_source") or {},
#             "assumption_severity": requirements.get("assumption_severity") or {},
#             "recommendation_mode": recommendation_mode,
#             "clarification_required_reasons": clarification_required_reasons,
#             "review_state": requirements.get("review_state") or {},
#             "check_requirement_summary": check_requirement_summary,
#             "editable_inferred_values": editable_inferred_values,
#             "template_candidates": prepared_context.template_candidates,
#             "target_profile": target_profile,
#             "recommendations": recommendations,
#             "summary": summary,
#             "assumptions": self.explanation_service.build_assumptions(requirements),
#             "comparison": "",
#             "extracted_schema": prepared_context.extracted_schema,
#             "readiness": readiness,
#             "compatibility_report": self._build_compatibility_report(compatibility_result),
#             "fallback_reason": core_result.fallback_reason or ("no_exact_fit" if budget_fit_summary.get("no_exact_budget_fit") else ""),
#             "expert_review_eligible": bool(expert_review_reason) and feature_flags.get("expert_review", True),
#             "meta": {
#                 "engine_version": ENGINE_VERSION,
#                 "config_versions": self.config_service.get_versions(),
#                 "config_bundle_version": self.config_service.get_bundle_version(),
#                 "feature_flags": feature_flags,
#                 "source_product_count": len(raw_products),
#                 "catalog_validation_summary": catalog_validation_result.get("summary") or {},
#                 "catalog_validation_rejections_sample": (catalog_validation_result.get("rejected_products") or [])[:5],
#                 "eligible_product_count": len(rankable_products),
#                 "recommended_count": len(recommendations),
#                 "budget_fit_summary": budget_fit_summary,
#                 "catalog_observability": catalog_observability,
#                 "filtered_categories": target_profile.get("categories") or [],
#                 "semantic_candidate_ids": list(core_result.shortlisted_product_ids or [])[:10],
#                 "semantic_candidate_count": len(list(core_result.shortlisted_product_ids or [])),
#                 "retrieval_summary": {
#                     "candidate_count": len(list(core_result.shortlisted_product_ids or [])),
#                     "fallback_reason": retrieval_result.get("fallback_reason"),
#                     "top_candidates": (retrieval_result.get("scored_candidates") or [])[:10],
#                 },
#                 "compatibility_summary": compatibility_result.get("summary") or {},
#                 "compatibility_rejections_sample": (compatibility_result.get("rejected_products") or [])[:5],
#                 "policy_summary": policy_result.get("summary") or {},
#                 "policy_rejections_sample": (policy_result.get("rejected_products") or [])[:5],
#                 "applied_rules_count": len(target_profile.get("applied_rules") or []),
#                 "ranking_deferred": core_result.ranking_deferred,
#                 "ranking_deferred_reason": deferred_reason,
#                 "expert_review_reason": expert_review_reason,
#                 "decision_policy_profile": decision_policy_profile,
#                 "stage_timings_ms": stage_timings,
#             },
#         }
#         if not readiness.get("is_ready"):
#             question_started_at = perf_counter()
#             response["next_question"] = (
#                 str(readiness.get("next_question") or "").strip()
#                 or self.clarification_service._context_aware_prompt(
#                     readiness.get("highest_priority_missing_field"),
#                     requirements,
#                 )
#             )
#             self._mark_stage(stage_timings, "question_generation_ms", question_started_at)
#         else:
#             stage_timings["question_generation_ms"] = 0.0
#         response["meta"]["decision_trace"] = self._build_decision_trace(
#             decision_trace_id=prepared_context.decision_trace_id,
#             requirements=requirements,
#             extracted_schema=prepared_context.extracted_schema,
#             target_profile=target_profile,
#             readiness=readiness,
#             retrieval_result=retrieval_result,
#             catalog_validation_result=catalog_validation_result,
#             compatibility_result=compatibility_result,
#             policy_result=policy_result,
#             recommendations=recommendations,
#             fallback_reason=core_result.fallback_reason,
#             recommendation_mode=recommendation_mode,
#             clarification_required_reasons=clarification_required_reasons,
#             expert_review_reason=expert_review_reason,
#             feature_flags=feature_flags,
#             decision_policy_profile=decision_policy_profile,
#             check_requirement_summary=check_requirement_summary,
#             editable_inferred_values=editable_inferred_values,
#             template_candidates=prepared_context.template_candidates,
#             selected_template=prepared_context.selected_template,
#         )
#         if capture_runtime_observability:
#             self._attach_runtime_observability(
#                 response=response,
#                 started_at=started_at,
#                 decision_trace_id=prepared_context.decision_trace_id,
#                 requirements=requirements,
#                 readiness=readiness,
#                 recommendation_mode=recommendation_mode,
#                 clarification_required_reasons=clarification_required_reasons,
#                 fallback_reason=core_result.fallback_reason,
#                 next_question=response.get("next_question"),
#             )
#         return response

#     def generate_narrative_enrichment(self, prepared_context, response, feature_flags=None):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         response = dict(response or {})
#         response["comparison"] = self.explanation_service.build_comparison(
#             response.get("requirements") or prepared_context.requirements,
#             response.get("recommendations") or [],
#             allow_llm=feature_flags.get("comparison_llm", False),
#         )
#         return response

#     def _dispatch_persistence_from_outputs(self, prepared_context, response, user_id="", business_id=""):
#         persistence_payload = {
#             "raw_intake_snapshot": prepared_context.raw_intake_snapshot,
#             "requirements": response.get("requirements") or prepared_context.requirements,
#             "target_profile": response.get("target_profile") or prepared_context.target_profile,
#             "recommendations": response.get("recommendations") or [],
#             "summary": response.get("summary") or "",
#             "assumptions": response.get("assumptions") or [],
#             "meta": {
#                 **dict(response.get("meta") or {}),
#                 "raw_chat": (response.get("requirements") or {}).get("raw_chat", ""),
#                 "extracted_schema": prepared_context.extracted_schema,
#             },
#             "user_id": user_id,
#             "business_id": business_id,
#         }
#         session_id = str(uuid4())
#         response["session_id"] = session_id
#         async_persistence_enabled = str(os.getenv("PROCUREMENT_ASYNC_PERSISTENCE", "true")).strip().lower() != "false"
#         if not async_persistence_enabled:
#             session, persistence_error = self._persist_session(session_id=session_id, **persistence_payload)
#             if session is None and persistence_error:
#                 response.setdefault("meta", {})
#                 response["meta"]["persistence_warning"] = persistence_error
#             return

#         self._persistence_executor.submit(
#             self._persist_session,
#             session_id=session_id,
#             **persistence_payload,
#         )

#     def _recommend_multi_intent(
#         self,
#         payload,
#         multi_intent_result,
#         extracted_schema=None,
#         prepared_context=None,
#         feature_flags=None,
#         user_id="",
#         business_id="",
#         persist=True,
#         top_level_timings=None,
#     ):
#         payload = dict(payload or {})
#         top_level_timings = top_level_timings or self._new_top_level_timings()
#         decision_trace_id = str(uuid4())
#         started_at = self.observability_service.start_timer()
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         if prepared_context is None:
#             prepare_started_at = perf_counter()
#             prepared_context = self.prepare_from_extracted_schema(
#                 payload=payload,
#                 extracted_schema=dict(extracted_schema or self._extract_schema(payload)),
#                 feature_flags=feature_flags,
#                 decision_trace_id=decision_trace_id,
#             )
#             self._mark_stage(top_level_timings["prepare_ms"], "total_ms", prepare_started_at)
#         extracted_schema = dict(prepared_context.extracted_schema or {})
#         raw_intake_snapshot = dict(prepared_context.raw_intake_snapshot or {})
#         requirements = dict(prepared_context.requirements or {})
#         target_profile = dict(prepared_context.target_profile or {})
#         base_readiness = dict(prepared_context.readiness or {})
#         template_candidates = self.template_service.select_candidates(
#             requirements,
#             target_profile,
#             multi_intent_result=multi_intent_result,
#         )
#         selected_template = self._selected_template(template_candidates)
#         selected_template_for_workflow = selected_template if selected_template.get("selection_allowed", True) else {}
#         multi_intent_policy = self.multi_intent_policy_service.evaluate(
#             payload=payload,
#             extracted_schema=extracted_schema,
#             requirements=requirements,
#             multi_intent_result=multi_intent_result,
#             selected_template=selected_template_for_workflow,
#         )

#         recommendation_groups = []
#         group_traces = []
#         flattened_recommendations = []
#         merged_assumptions = []
#         group_next_questions = []

#         for intent in multi_intent_result.get("intents") or []:
#             group_policy = dict((multi_intent_policy.get("groups_by_id") or {}).get(intent.get("group_id")) or {})
#             group_payload = self._apply_multi_intent_shared_context(
#                 intent.get("payload") or {},
#                 requirements,
#                 group_policy=group_policy,
#             )
#             group_prepared = self.prepare_from_extracted_schema(
#                 payload=group_payload,
#                 extracted_schema=intent.get("extracted_schema") or {},
#                 feature_flags=feature_flags,
#                 decision_trace_id=str(uuid4()),
#                 source_mode="multi_intent_group",
#                 prepared_catalog_state=prepared_context.prepared_catalog_state,
#             )
#             group_response = self._recommend_single_from_prepared(
#                 prepared_context=group_prepared,
#                 feature_flags=feature_flags,
#                 persist=False,
#                 capture_runtime_observability=False,
#             )
#             group_meta = dict(group_response.get("meta") or {})
#             group_decision_trace = group_meta.pop("decision_trace", None)
#             group_selected_template = dict(group_meta.get("selected_template") or {})
#             group_entry = {
#                 "group_id": intent.get("group_id"),
#                 "label": intent.get("label"),
#                 "intent_text": intent.get("intent_text"),
#                 "category": intent.get("category"),
#                 "workloads": intent.get("workloads") or [],
#                 "shared_constraints": group_policy.get("shared_constraints") or [],
#                 "warnings": group_policy.get("warnings") or [],
#                 "shared_budget": group_policy.get("shared_budget") or {},
#                 "decision_trace_id": group_response.get("decision_trace_id"),
#                 "requirements": group_response.get("requirements") or {},
#                 "field_state": group_response.get("field_state") or {},
#                 "field_source": group_response.get("field_source") or {},
#                 "assumption_severity": group_response.get("assumption_severity") or {},
#                 "recommendation_mode": group_response.get("recommendation_mode"),
#                 "clarification_required_reasons": group_response.get("clarification_required_reasons") or [],
#                 "check_requirement_summary": group_response.get("check_requirement_summary") or {},
#                 "editable_inferred_values": group_response.get("editable_inferred_values") or {},
#                 "selected_template": group_selected_template,
#                 "template_candidates": group_response.get("template_candidates") or [],
#                 "target_profile": group_response.get("target_profile") or {},
#                 "recommendations": group_response.get("recommendations") or [],
#                 "summary": group_response.get("summary", ""),
#                 "assumptions": group_response.get("assumptions") or [],
#                 "comparison": group_response.get("comparison", ""),
#                 "readiness": group_response.get("readiness") or {},
#                 "compatibility_report": group_response.get("compatibility_report") or {},
#                 "fallback_reason": group_response.get("fallback_reason"),
#                 "expert_review_eligible": group_response.get("expert_review_eligible", False),
#                 "next_question": group_response.get("next_question"),
#                 "meta": group_meta,
#             }
#             recommendation_groups.append(group_entry)
#             if group_decision_trace:
#                 group_traces.append(
#                     {
#                         "group_id": group_entry["group_id"],
#                         "label": group_entry["label"],
#                         "decision_trace": group_decision_trace,
#                     }
#                 )
#             if group_entry["recommendations"]:
#                 top_recommendation = dict(group_entry["recommendations"][0])
#                 top_recommendation["recommendation_group_id"] = group_entry["group_id"]
#                 top_recommendation["recommendation_group_label"] = group_entry["label"]
#                 flattened_recommendations.append(top_recommendation)
#             merged_assumptions.extend(group_entry["assumptions"])
#             if group_entry["next_question"]:
#                 group_next_questions.append(
#                     {
#                         "group_id": group_entry["group_id"],
#                         "label": group_entry["label"],
#                         "prompt": group_entry["next_question"],
#                     }
#                 )

#         bundle_result = self.bundle_service.build_bundle_result(
#             requirements=requirements,
#             recommendation_groups=recommendation_groups,
#             multi_intent_policy=multi_intent_policy,
#             selected_template=selected_template_for_workflow,
#         )
#         combined_merge_rules = list(multi_intent_policy.get("merge_rules") or []) + list(
#             bundle_result.get("merge_rules") or []
#         )
#         policy_trace = list(multi_intent_policy.get("split_rules") or []) + combined_merge_rules
#         bundle_trace = self._build_bundle_trace(bundle_result, selected_template)
#         bundle_validated = bool(bundle_result.get("bundle_validated"))
#         grouped_readiness = self._build_grouped_readiness(
#             base_readiness,
#             recommendation_groups,
#             multi_intent_policy=multi_intent_policy,
#         )
#         compatibility_report = self._build_grouped_compatibility_report(recommendation_groups)
#         fallback_reason = self._grouped_fallback_reason(recommendation_groups)
#         clarification_required_reasons = self._clarification_required_reasons(grouped_readiness)
#         expert_review_reason = self._grouped_expert_review_reason(recommendation_groups, fallback_reason)
#         if not bundle_validated and not clarification_required_reasons:
#             expert_review_reason = expert_review_reason or "bundle_validation_rejected"
#         expert_review_reason = self._apply_template_review_reason(selected_template, expert_review_reason)
#         decision_policy_profile = self.config_service.get_decision_policy_profile()
#         recommendation_mode = self._recommendation_mode(
#             readiness=grouped_readiness,
#             recommendations=flattened_recommendations,
#             fallback_reason=fallback_reason,
#             expert_review_reason=expert_review_reason,
#             clarification_required_reasons=clarification_required_reasons,
#             candidate_pool_size=sum(group["meta"].get("eligible_product_count", 0) for group in recommendation_groups),
#         )
#         recommendation_mode = self._apply_template_selection_mode(selected_template, recommendation_mode)
#         requirements["review_state"] = self.review_support_service.enrich_review_state(
#             requirements=requirements,
#             readiness=grouped_readiness,
#             template_candidates=template_candidates,
#             recommendation_mode=recommendation_mode,
#         )
#         check_requirement_summary = self.review_support_service.build_check_requirement_summary(
#             requirements=requirements,
#             readiness=grouped_readiness,
#             template_candidates=template_candidates,
#             recommendation_mode=recommendation_mode,
#         )
#         editable_inferred_values = self.review_support_service.build_editable_inferred_values(requirements)
#         template_id = bundle_trace.get("template_id")
#         template_version = bundle_trace.get("template_version")
#         response = {
#             "decision_trace_id": decision_trace_id,
#             "requirements": requirements,
#             "field_state": requirements.get("field_state") or {},
#             "field_source": requirements.get("field_source") or {},
#             "assumption_severity": requirements.get("assumption_severity") or {},
#             "recommendation_mode": recommendation_mode,
#             "clarification_required_reasons": clarification_required_reasons,
#             "review_state": requirements.get("review_state") or {},
#             "check_requirement_summary": check_requirement_summary,
#             "editable_inferred_values": editable_inferred_values,
#             "template_candidates": template_candidates,
#             "target_profile": target_profile,
#             "recommendations": flattened_recommendations,
#             "recommendation_groups": recommendation_groups,
#             "summary": self._build_release_4a_summary(
#                 recommendation_groups,
#                 multi_intent_policy=multi_intent_policy,
#                 bundle_result=bundle_result,
#             ),
#             "assumptions": self._dedupe_strings(merged_assumptions),
#             "comparison": self.explanation_service.build_comparison(
#                 requirements,
#                 flattened_recommendations,
#                 allow_llm=feature_flags.get("comparison_llm", False),
#             ),
#             "extracted_schema": extracted_schema,
#             "readiness": grouped_readiness,
#             "compatibility_report": compatibility_report,
#             "bundle_compatibility_report": bundle_result.get("bundle_compatibility_report") or {},
#             "bundle_conflict_codes": list(bundle_result.get("bundle_conflict_codes") or []),
#             "bundle_capacity_summary": bundle_result.get("bundle_capacity_summary") or {},
#             "bundle_options": list(bundle_result.get("bundle_options") or []),
#             "architecture_graph": bundle_result.get("architecture_graph") or {},
#             "template_id": template_id,
#             "template_version": template_version,
#             "fallback_reason": fallback_reason,
#             "expert_review_eligible": bool(expert_review_reason) and feature_flags.get("expert_review", True),
#             "meta": {
#                 "engine_version": ENGINE_VERSION,
#                 "config_versions": self.config_service.get_versions(),
#                 "config_bundle_version": self.config_service.get_bundle_version(),
#                 "feature_flags": feature_flags,
#                 "source_product_count": sum(group["meta"].get("source_product_count", 0) for group in recommendation_groups),
#                 "catalog_validation_summary": {
#                     "group_count": len(recommendation_groups),
#                     "rejected_count": sum(
#                         (group["meta"].get("catalog_validation_summary") or {}).get("rejected_count", 0)
#                         for group in recommendation_groups
#                     ),
#                 },
#                 "eligible_product_count": sum(group["meta"].get("eligible_product_count", 0) for group in recommendation_groups),
#                 "recommended_count": len(flattened_recommendations),
#                 "catalog_observability": self._aggregate_catalog_observability(recommendation_groups),
#                 "filtered_categories": self._dedupe_strings(
#                     [
#                         category
#                         for group in recommendation_groups
#                         for category in (group.get("target_profile", {}).get("categories") or [])
#                     ]
#                 ),
#                 "semantic_candidate_ids": self._dedupe_strings(
#                     [
#                         candidate_id
#                         for group in recommendation_groups
#                         for candidate_id in (group["meta"].get("semantic_candidate_ids") or [])
#                     ]
#                 )[:10],
#                 "semantic_candidate_count": sum(group["meta"].get("semantic_candidate_count", 0) for group in recommendation_groups),
#                 "retrieval_summary": {
#                     "candidate_count": sum(
#                         (group["meta"].get("retrieval_summary") or {}).get("candidate_count", 0)
#                         for group in recommendation_groups
#                     ),
#                     "fallback_reason": fallback_reason,
#                     "top_candidates": [
#                         {
#                             "group_id": group["group_id"],
#                             "label": group["label"],
#                             "top_candidates": (group["meta"].get("retrieval_summary") or {}).get("top_candidates") or [],
#                         }
#                         for group in recommendation_groups
#                     ],
#                 },
#                 "compatibility_summary": compatibility_report.get("summary") or {},
#                 "compatibility_rejections_sample": compatibility_report.get("rejected_products") or [],
#                 "policy_summary": {
#                     "group_count": len(recommendation_groups),
#                     "rejected_count": sum(
#                         (group["meta"].get("policy_summary") or {}).get("rejected_count", 0)
#                         for group in recommendation_groups
#                     ),
#                 },
#                 "policy_rejections_sample": [
#                     {
#                         "group_id": group["group_id"],
#                         "label": group["label"],
#                         "rejected_products": (group["meta"].get("policy_rejections_sample") or [])[:3],
#                     }
#                     for group in recommendation_groups
#                     if group["meta"].get("policy_rejections_sample")
#                 ][:5],
#                 "applied_rules_count": sum(group["meta"].get("applied_rules_count", 0) for group in recommendation_groups),
#                 "ranking_deferred": all(group["meta"].get("ranking_deferred", False) for group in recommendation_groups),
#                 "ranking_deferred_reason": (
#                     "multi_intent_group_clarification_required"
#                     if any(group["meta"].get("ranking_deferred", False) for group in recommendation_groups)
#                     else None
#                 ),
#                 "expert_review_reason": expert_review_reason,
#                 "decision_policy_profile": decision_policy_profile,
#                 "bundle_trace": bundle_trace,
#                 "multi_intent": {
#                     "is_multi_intent": True,
#                     "is_grouped": True,
#                     "bundle_validated": bundle_validated,
#                     "policy_version": multi_intent_policy.get("policy_version"),
#                     "split_source": multi_intent_result.get("split_source"),
#                     "shared_budget_reused": multi_intent_result.get("shared_budget_reused", False),
#                     "shared_constraints": multi_intent_policy.get("shared_constraints") or [],
#                     "shared_budget": multi_intent_policy.get("shared_budget") or {},
#                     "warnings": multi_intent_policy.get("warnings") or [],
#                     "split_rules": multi_intent_policy.get("split_rules") or [],
#                     "merge_rules": combined_merge_rules,
#                     "policy_trace": policy_trace,
#                     "bundle_conflict_codes": list(bundle_result.get("bundle_conflict_codes") or []),
#                     "validation_outcome": bundle_trace.get("validation_outcome"),
#                     "template_id": template_id,
#                     "template_version": template_version,
#                     "group_count": len(recommendation_groups),
#                     "group_labels": [group["label"] for group in recommendation_groups],
#                     "group_decision_trace_ids": [
#                         group.get("decision_trace_id")
#                         for group in recommendation_groups
#                         if group.get("decision_trace_id")
#                     ],
#                     "group_next_questions": group_next_questions,
#                     "group_templates": self._build_group_template_summary(recommendation_groups),
#                 },
#             },
#         }
#         if grouped_readiness.get("next_question"):
#             response["next_question"] = grouped_readiness.get("next_question")
#         elif group_next_questions:
#             response["next_question"] = group_next_questions[0]["prompt"]

#         response["meta"]["decision_trace"] = {
#             "decision_trace_id": decision_trace_id,
            
#             "compatibility": {
#                 "scope": compatibility_report.get("scope") or "item",
#                 "summary": compatibility_report.get("summary") or {},
#                 "rejected_products": compatibility_report.get("rejected_products") or [],
#             },
#             "bundle_validation": bundle_trace,
#             "expert_review_reason": expert_review_reason,
#             "feature_flags": feature_flags,
#             "config_versions": self.config_service.get_versions(),
         
#             "multi_intent": {
#                 "is_multi_intent": True,
#                 "policy_version": multi_intent_policy.get("policy_version"),
#                 "split_source": multi_intent_result.get("split_source"),
#                 "shared_budget_reused": multi_intent_result.get("shared_budget_reused", False),
#                 "bundle_validated": bundle_validated,
#                 "shared_constraints": multi_intent_policy.get("shared_constraints") or [],
#                 "shared_budget": multi_intent_policy.get("shared_budget") or {},
#                 "warnings": multi_intent_policy.get("warnings") or [],
#                 "split_rules": multi_intent_policy.get("split_rules") or [],
#                 "merge_rules": combined_merge_rules,
#                 "policy_trace": policy_trace,
#                 "bundle_conflict_codes": list(bundle_result.get("bundle_conflict_codes") or []),
#                 "validation_outcome": bundle_trace.get("validation_outcome"),
#                 "template_id": template_id,
#                 "template_version": template_version,
#                 "groups": group_traces,
#                 "group_templates": self._build_group_template_summary(recommendation_groups),
#             },
#         }
#         self._attach_runtime_observability(
#             response=response,
#             started_at=started_at,
#             decision_trace_id=decision_trace_id,
#             requirements=requirements,
#             readiness=grouped_readiness,
#             recommendation_mode=recommendation_mode,
#             clarification_required_reasons=clarification_required_reasons,
#             fallback_reason=fallback_reason,
#             next_question=response.get("next_question"),
#         )

#         if persist:
#             self._dispatch_persistence_from_outputs(
#                 prepared_context=prepared_context,
#                 response={
#                     **response,
#                     "recommendations": flattened_recommendations,
#                     "target_profile": target_profile,
#                     "assumptions": response["assumptions"],
#                     "meta": {
#                         **response["meta"],
#                         "recommendation_groups": recommendation_groups,
#                     },
#                 },
#                 user_id=user_id,
#                 business_id=business_id,
#             )

#         return response

#     def _attach_runtime_observability(
#         self,
#         response,
#         started_at,
#         decision_trace_id,
#         requirements,
#         readiness,
#         recommendation_mode,
#         clarification_required_reasons,
#         fallback_reason,
#         next_question=None,
#     ):
#         response = dict(response or {})
#         runtime_observability = self.observability_service.build_runtime_observability(
#             started_at=started_at,
#             decision_trace_id=decision_trace_id,
#             requirements=requirements,
#             readiness=readiness,
#             recommendation_mode=recommendation_mode,
#             clarification_required_reasons=clarification_required_reasons,
#             fallback_reason=fallback_reason,
#             next_question=next_question,
#             response_payload=response,
#         )
#         response.setdefault("meta", {})
#         response["meta"]["runtime_observability"] = runtime_observability
#         decision_trace = response["meta"].get("decision_trace")
#         if isinstance(decision_trace, dict):
#             pass
#         return response

#     def _apply_multi_intent_shared_context(self, payload, requirements, group_policy=None):
#         payload = dict(payload or {})
#         requirements = dict(requirements or {})
#         group_policy = dict(group_policy or {})
#         explicit_payload_fields = list(payload.get("_explicit_payload_fields") or [])
#         field_source_hints = dict(payload.get("_field_source_hints") or {})
#         shared_constraints = set(group_policy.get("shared_constraints") or [])

#         if (
#             requirements.get("budget_scope")
#             and "budget_scope" in shared_constraints
#             and not payload.get("budget_scope")
#         ):
#             payload["budget_scope"] = requirements.get("budget_scope")
#             field_source_hints.setdefault("budget_scope", "context_explicit")

#         if explicit_payload_fields:
#             payload["_explicit_payload_fields"] = explicit_payload_fields
#         if field_source_hints:
#             payload["_field_source_hints"] = field_source_hints
#         return payload

#     def _normalize_products(self, raw_products, requested_currency, allowed_categories=None, currency_fallback_used=False):
#         normalized_products = []
#         seen_ids = set()
#         allowed_categories = set(allowed_categories or [])
#         for product in raw_products:
#             inventory_offers = list(product.get("inventory_offers") or [])
#             if not inventory_offers:
#                 inventory = product.get("inventory")
#                 inventory_offers = [inventory] if inventory else [None]

#             for inventory in inventory_offers:
#                 candidate = dict(product)
#                 candidate.pop("inventory_offers", None)
#                 if inventory:
#                     candidate["inventory"] = inventory
#                 else:
#                     candidate.pop("inventory", None)
#                 normalized = normalize_product_document(candidate, requested_currency=requested_currency)
#                 product_id = normalized.get("id")
#                 if product_id in seen_ids:
#                     continue
#                 seen_ids.add(product_id)
#                 normalized["offer_count"] = len(inventory_offers)
#                 normalized["alternate_offer_count"] = max(len(inventory_offers) - 1, 0)
#                 normalized["currency_fallback_used"] = bool(
#                     currency_fallback_used
#                     and requested_currency
#                     and str(normalized.get("currency") or "").strip().upper()
#                     != str(requested_currency or "").strip().upper()
#                 )
#                 normalized_products.append(normalized)
#         return normalized_products

#     def _filter_normalized_products(self, normalized_products, allowed_categories=None, candidate_ids=None):
#         normalized_products = list(normalized_products or [])
#         category_filter_enabled = bool(allowed_categories)
#         candidate_filter_enabled = candidate_ids is not None
#         allowed_categories = set(allowed_categories or [])
#         candidate_ids = set(candidate_ids or [])
#         if not category_filter_enabled and not candidate_filter_enabled:
#             return normalized_products
#         filtered = []
#         for product in normalized_products:
#             if category_filter_enabled and product.get("category") not in allowed_categories:
#                 continue
#             if candidate_filter_enabled and product.get("id") not in candidate_ids:
#                 continue
#             filtered.append(product)
#         return filtered

#     def _build_grouped_readiness(self, base_readiness, recommendation_groups, multi_intent_policy=None):
#         base_readiness = dict(base_readiness or {})
#         multi_intent_policy = dict(multi_intent_policy or {})
#         readiness_items = [dict(group.get("readiness") or {}) for group in recommendation_groups]
#         if not readiness_items:
#             return base_readiness

#         confidence_rank = {"low": 0, "medium": 1, "high": 2}
#         band_rank = {"low": 0, "medium": 1, "high": 2}
#         question_candidates = []
#         missing_signals = []
#         for group in recommendation_groups:
#             readiness = dict(group.get("readiness") or {})
#             for signal in readiness.get("missing_signals") or []:
#                 if signal not in missing_signals:
#                     missing_signals.append(signal)
#             for candidate in readiness.get("question_candidates") or []:
#                 candidate_copy = dict(candidate)
#                 candidate_copy["group_id"] = group.get("group_id")
#                 candidate_copy["group_label"] = group.get("label")
#                 question_candidates.append(candidate_copy)

#         shared_budget = dict(multi_intent_policy.get("shared_budget") or {})
#         if shared_budget.get("allocation_required"):
#             missing_signals.append(shared_budget.get("clarification_key"))
#             question_candidates.append(
#                 {
#                     "key": shared_budget.get("clarification_key"),
#                     "prompt": shared_budget.get("clarification_prompt"),
#                     "rationale": shared_budget.get("clarification_rationale"),
#                     "impact": 0.98,
#                 }
#             )

#         question_candidates.sort(key=lambda item: item.get("impact", 0), reverse=True)
#         top_question = question_candidates[0] if question_candidates else None
#         threshold = self.clarification_service.question_impact_threshold()
#         should_ask_top_question = bool(top_question and float(top_question.get("impact", 0.0)) >= threshold)
#         grouped_confidence = min(
#             (item.get("confidence") or "medium" for item in readiness_items),
#             key=lambda value: confidence_rank.get(value, 1),
#         )
#         grouped_band = min(
#             (item.get("decision_confidence_band") or "medium" for item in readiness_items),
#             key=lambda value: band_rank.get(value, 1),
#         )
#         grouped_score = round(
#             sum(item.get("decision_confidence_score", 0.0) for item in readiness_items) / len(readiness_items),
#             4,
#         )

#         return {
#             **base_readiness,
#             "is_ready": all(bool(item.get("is_ready")) for item in readiness_items),
#             "confidence": grouped_confidence,
#             "missing_signals": missing_signals,
#             "highest_priority_missing_field": top_question.get("key") if top_question else None,
#             "next_question": top_question.get("prompt") if should_ask_top_question else None,
#             "follow_up_questions": question_candidates[:3],
#             "decision_confidence_score": grouped_score,
#             "decision_confidence_band": grouped_band,
#             "recommended_question_budget": 1 if should_ask_top_question else 0,
#             "routing_recommendation": (
#                 "clarify_before_ranking"
#                 if not all(bool(item.get("is_ready")) for item in readiness_items)
#                 else "recommend_with_one_refinement"
#                 if should_ask_top_question
#                 else base_readiness.get("routing_recommendation", "recommend_now")
#             ),
#             "recommended_refinement_question": top_question.get("prompt") if should_ask_top_question else None,
#             "question_strategy": (
#                 "grouped_single_question"
#                 if should_ask_top_question
#                 else base_readiness.get("question_strategy", "proceed")
#             ),
#             "question_candidates": question_candidates[:3],
#         }

#     def _build_grouped_compatibility_report(self, recommendation_groups):
#         group_reports = []
#         rejected_products = []
#         eligible_count = 0
#         rejected_count = 0
#         for group in recommendation_groups:
#             report = dict(group.get("compatibility_report") or {})
#             report_summary = dict(report.get("summary") or {})
#             eligible_count += report_summary.get("eligible_count", 0)
#             rejected_count += report_summary.get("rejected_count", 0)
#             group_rejections = list(report.get("rejected_products") or [])
#             rejected_products.extend(group_rejections[:3])
#             group_reports.append(
#                 {
#                     "group_id": group.get("group_id"),
#                     "label": group.get("label"),
#                     "scope": report.get("scope") or "item",
#                     "summary": report_summary,
#                     "rejected_products": group_rejections[:3],
#                 }
#             )

#         return {
#             "scope": "item",
#             "summary": {
#                 "compatibility_scope": "item",
#                 "grouped": True,
#                 "group_count": len(recommendation_groups),
#                 "eligible_count": eligible_count,
#                 "rejected_count": rejected_count,
#             },
#             "rejected_products": rejected_products[:5],
#             "groups": group_reports,
#         }

#     def _build_grouped_summary(self, recommendation_groups, multi_intent_policy=None):
#         multi_intent_policy = dict(multi_intent_policy or {})
#         if not recommendation_groups:
#             return "No grouped recommendations were generated."

#         parts = []
#         for group in recommendation_groups:
#             recommendations = list(group.get("recommendations") or [])
#             label = group.get("label") or group.get("group_id") or "Intent"
#             if recommendations:
#                 top_name = recommendations[0].get("name") or "Recommendation ready"
#                 parts.append(f"{label}: {top_name}")
#             elif group.get("next_question"):
#                 parts.append(f"{label}: clarification needed")
#             else:
#                 parts.append(f"{label}: no exact fit")
#         summary = "Grouped recommendations prepared for {} intents. {}".format(
#             len(recommendation_groups),
#             " | ".join(parts),
#         )
#         shared_budget = dict(multi_intent_policy.get("shared_budget") or {})
#         if shared_budget.get("allocation_required"):
#             summary += " Shared project budget allocation still needs confirmation before the groups can be treated as budget-valid together."
#         return summary

#     def _build_release_4a_summary(self, recommendation_groups, multi_intent_policy=None, bundle_result=None):
#         bundle_result = dict(bundle_result or {})
#         grouped_summary = self._build_grouped_summary(
#             recommendation_groups,
#             multi_intent_policy=multi_intent_policy,
#         )
#         bundle_summary = str(bundle_result.get("summary") or "").strip()
#         if bundle_result.get("bundle_validated"):
#             return bundle_summary or grouped_summary
#         if not bundle_summary:
#             return grouped_summary
#         if recommendation_groups and any(group.get("recommendations") for group in recommendation_groups):
#             return (
#                 bundle_summary
#                 + " Constrained per-role recommendations remain available while the bundle is not yet valid."
#             )
#         return bundle_summary

#     def _build_bundle_trace(self, bundle_result, selected_template=None):
#         bundle_result = dict(bundle_result or {})
#         selected_template = dict(selected_template or {})
#         bundle_candidate = dict(bundle_result.get("bundle_candidate") or {})
#         bundle_report = dict(bundle_result.get("bundle_compatibility_report") or {})
#         return {
#             "template_id": bundle_candidate.get("template_id") or selected_template.get("template_id"),
#             "template_version": bundle_candidate.get("template_version") or selected_template.get("template_version"),
#             "bundle_validated": bool(bundle_result.get("bundle_validated")),
#             "validation_outcome": "passed" if bundle_result.get("bundle_validated") else "rejected",
#             "bundle_candidate": bundle_candidate,
#             "bundle_compatibility_report": bundle_report,
#             "bundle_conflict_codes": list(bundle_result.get("bundle_conflict_codes") or []),
#             "bundle_capacity_summary": bundle_result.get("bundle_capacity_summary") or {},
#             "bundle_options": list(bundle_result.get("bundle_options") or []),
#             "architecture_graph": bundle_result.get("architecture_graph") or {},
#             "merge_rules": list(bundle_result.get("merge_rules") or []),
#         }

#     def _build_group_template_summary(self, recommendation_groups):
#         summary = []
#         for group in list(recommendation_groups or []):
#             selected_template = dict(group.get("selected_template") or {})
#             template_candidates = list(group.get("template_candidates") or [])
#             if not selected_template and template_candidates:
#                 selected_template = self._selected_template(template_candidates)
#             summary.append(
#                 {
#                     "group_id": group.get("group_id"),
#                     "label": group.get("label"),
#                     "category": group.get("category"),
#                     "template_id": selected_template.get("template_id"),
#                     "template_version": selected_template.get("template_version"),
#                     "template_match_quality": selected_template.get("template_match_quality"),
#                     "required_roles": list(selected_template.get("required_roles") or []),
#                     "quantity_strategy": selected_template.get("quantity_strategy"),
#                     "budget_strategy": selected_template.get("budget_strategy"),
#                     "selection_allowed": bool(selected_template.get("selection_allowed", True))
#                     if selected_template
#                     else False,
#                 }
#             )
#         return summary

#     def _grouped_fallback_reason(self, recommendation_groups):
#         if not recommendation_groups:
#             return "no_exact_fit"
#         fallback_reasons = [
#             group.get("fallback_reason")
#             for group in recommendation_groups
#             if group.get("fallback_reason")
#         ]
#         if not fallback_reasons:
#             return ""
#         if len(fallback_reasons) == len(recommendation_groups):
#             return fallback_reasons[0] if len(set(fallback_reasons)) == 1 else "multi_intent_partial_fallback"
#         return "multi_intent_partial_fallback"

#     def _grouped_expert_review_reason(self, recommendation_groups, fallback_reason):
#         if any(group.get("expert_review_eligible") for group in recommendation_groups):
#             return "multi_intent_group_requires_review"
#         if fallback_reason in {"compatibility_blocked_all", "policy_rejected_all", "no_exact_fit", "multi_intent_partial_fallback"}:
#             return fallback_reason
#         return ""

#     def _selected_template(self, template_candidates):
#         template_candidates = list(template_candidates or [])
#         if not template_candidates:
#             return {}
#         selected = dict(template_candidates[0])
#         return {
#             "template_id": selected.get("template_id"),
#             "template_version": selected.get("template_version"),
#             "scenario_family": selected.get("scenario_family"),
#             "variant": selected.get("variant"),
#             "template_match_quality": selected.get("template_match_quality"),
#             "match_score": selected.get("match_score"),
#             "selection_allowed": bool(selected.get("selection_allowed", True)),
#             "selection_rejection_reason": selected.get("selection_rejection_reason") or "",
#             "matched_template_signals": selected.get("matched_template_signals") or {},
#             "coverage_gap_reasons": list(selected.get("coverage_gap_reasons") or []),
#             "gap_type": selected.get("gap_type") or "",
#             "hard_gate_failures": list(selected.get("hard_gate_failures") or []),
#             "contradiction_codes": list(selected.get("contradiction_codes") or []),
#             "soft_fit_gaps": list(selected.get("soft_fit_gaps") or []),
#             "template_selection_debug": dict(selected.get("template_selection_debug") or {}),
#             "required_roles": list(selected.get("required_roles") or []),
#             "quantity_strategy": selected.get("quantity_strategy"),
#             "budget_strategy": selected.get("budget_strategy"),
#             "compatibility_profile": selected.get("compatibility_profile"),
#             "scoring_profile": selected.get("scoring_profile"),
#             "urgency_profile": selected.get("urgency_profile"),
#             "site_scope_profile": selected.get("site_scope_profile"),
#             "rollout_type": selected.get("rollout_type"),
#             "replacement_mode": selected.get("replacement_mode"),
#             "support_preference": selected.get("support_preference"),
#             "existing_infra_dependency": selected.get("existing_infra_dependency"),
#             "acceptable_downgrade_path": selected.get("acceptable_downgrade_path"),
#         }

#     def _apply_template_review_reason(self, selected_template, expert_review_reason):
#         selected_template = dict(selected_template or {})
#         expert_review_reason = str(expert_review_reason or "").strip()
#         template_quality = str(selected_template.get("template_match_quality") or "").strip().lower()
#         if template_quality == "coverage_gap":
#             return expert_review_reason or "template_coverage_gap"
#         return expert_review_reason

#     def _apply_template_selection_mode(self, selected_template, recommendation_mode):
#         selected_template = dict(selected_template or {})
#         template_quality = str(selected_template.get("template_match_quality") or "").strip().lower()
#         if template_quality == "coverage_gap":
#             return "expert_review_recommended"
#         if template_quality == "closest_match" and recommendation_mode == "firm_recommendation":
#             return "provisional_recommendation"
#         return recommendation_mode

#     def _dedupe_strings(self, values):
#         deduped = []
#         seen = set()
#         for value in list(values or []):
#             normalized = str(value or "").strip()
#             if not normalized:
#                 continue
#             lowered = normalized.lower()
#             if lowered in seen:
#                 continue
#             seen.add(lowered)
#             deduped.append(normalized)
#         return deduped

#     def _persist_session(
#         self,
#         raw_intake_snapshot,
#         requirements,
#         target_profile,
#         recommendations,
#         summary,
#         assumptions,
#         meta,
#         user_id="",
#         business_id="",
#         session_id=None,
#     ):
#         try:
#             from ..models import ProcurementSession

#             session = ProcurementSession.objects.create(
#                 session_id=str(session_id or uuid4()),
#                 user_id=str(user_id or ""),
#                 business_id=str(business_id or ""),
#                 store_id=requirements.get("store_id", ""),
#                 channel=requirements.get("channel", "api"),
#                 currency=requirements.get("currency", ""),
#                 raw_intake_snapshot=dict(raw_intake_snapshot or {}),
#                 requirements=requirements,
#                 target_profile=target_profile,
#                 recommendations=recommendations,
#                 summary=summary,
#                 assumptions=assumptions,
#                 meta=meta,
#                 engine_version=ENGINE_VERSION,
#             )
#             return session, None
#         except Exception as exc:
#             return None, str(exc)

#     def _build_raw_intake_snapshot(self, payload):
#         snapshot = {}
#         for key, value in dict(payload or {}).items():
#             if str(key).startswith("_") or key == "persist":
#                 continue
#             snapshot[key] = value
#         return snapshot

#     def _build_buy_url(self, product_id, store_id=""):
#         if not product_id:
#             return ""

#         base_url = os.getenv("SHOP_PRODUCT_BASE_URL", "https://dev.techpay.ai/shop/#/products").rstrip("/")
#         return f"{base_url}/{product_id}"

#     def _resolve_prepared_catalog_state(self, requirements):
#         requirements = dict(requirements or {})
#         cache_key = self._prepared_catalog_state_cache_key(requirements)
#         cached = self._prepared_catalog_state_cache.get(cache_key)
#         if cached is not None:
#             return cached

#         raw_products = self.catalog_repository.fetch_products(
#             store_id="",
#             currency=requirements.get("currency", ""),
#         )
#         currency_fallback_used = False
#         if not raw_products and requirements.get("currency"):
#             raw_products = self.catalog_repository.fetch_products(store_id="", currency="")
#             currency_fallback_used = bool(raw_products)
#         catalog_source_snapshot = self._catalog_source_snapshot()
#         normalized_products = self._normalize_products(
#             raw_products,
#             requirements.get("currency"),
#             allowed_categories=None,
#             currency_fallback_used=currency_fallback_used,
#         )
#         catalog_validation_result = self._screen_catalog_metadata(normalized_products)
#         eligible_products = list(catalog_validation_result.get("eligible_products") or [])
#         category_subsets = self._build_category_indexed_subsets(eligible_products)
#         retrieval_assets_by_subset = {
#             "__all__": self._resolve_precomputed_retrieval_assets(
#                 eligible_products,
#                 subset_key="__all__",
#                 cache_key=cache_key,
#             ),
#         }
#         for category_key, subset in category_subsets.items():
#             retrieval_assets_by_subset[category_key] = self._resolve_precomputed_retrieval_assets(
#                 subset,
#                 subset_key=category_key,
#                 cache_key=cache_key,
#             )

#         prepared = PreparedCatalogState(
#             cache_key=cache_key,
#             raw_products=tuple(raw_products),
#             normalized_products=tuple(normalized_products),
#             eligible_products=tuple(eligible_products),
#             catalog_validation_result=dict(catalog_validation_result or {}),
#             category_subsets={key: tuple(value) for key, value in category_subsets.items()},
#             retrieval_assets_by_subset=retrieval_assets_by_subset,
#             currency_fallback_used=bool(currency_fallback_used),
#             catalog_source_snapshot=dict(catalog_source_snapshot or {}),
#             store_scope_applied=False,
#         )
#         self._prepared_catalog_state_cache[cache_key] = prepared
#         return prepared

#     def _resolve_precomputed_retrieval_assets(self, normalized_products, subset_key="__all__", cache_key=""):
#         getter = getattr(self.catalog_repository, "get_precomputed_retrieval_assets", None)
#         if callable(getter):
#             try:
#                 assets = getter(
#                     subset_key=subset_key,
#                     cache_key=cache_key,
#                     normalized_products=list(normalized_products or []),
#                 )
#             except TypeError:
#                 assets = getter(subset_key, cache_key)
#             except Exception:
#                 assets = None
#             if assets:
#                 return assets
#         return self.semantic_retriever.build_retrieval_assets(
#             normalized_products,
#             include_semantic=False,
#         )

#     def _prepared_catalog_state_cache_key(self, requirements):
#         requirements = dict(requirements or {})
#         currency = str(requirements.get("currency") or "").strip().upper()
#         store_id = str(requirements.get("store_id") or "").strip().lower()
#         source_snapshot = self._catalog_source_snapshot()
#         source_name = str(source_snapshot.get("source_name") or getattr(self.catalog_repository, "source_name", "")).strip()
#         source_path = str(source_snapshot.get("source_path") or "").strip()
#         source_success = bool(source_snapshot.get("source_load_success", True))
#         catalog_version = str(source_snapshot.get("catalog_version") or "").strip()
#         return "|".join(
#             [
#                 source_name,
#                 source_path,
#                 catalog_version,
#                 str(source_success).lower(),
#                 currency,
#                 store_id,
#             ]
#         )

#     def _build_category_indexed_subsets(self, eligible_products):
#         subsets = {}
#         for product in list(eligible_products or []):
#             category = str(product.get("category") or "").strip().lower()
#             if not category:
#                 continue
#             subsets.setdefault(category, []).append(product)
#         return subsets

#     def _resolve_category_subset_from_state(self, prepared_catalog_state, categories):
#         prepared_catalog_state = prepared_catalog_state or PreparedCatalogState(
#             cache_key="",
#             raw_products=tuple(),
#             normalized_products=tuple(),
#             eligible_products=tuple(),
#             catalog_validation_result={},
#             category_subsets={},
#             retrieval_assets_by_subset={},
#             currency_fallback_used=False,
#             catalog_source_snapshot={},
#         )
#         categories = [str(value or "").strip().lower() for value in list(categories or []) if str(value or "").strip()]
#         if not categories:
#             return list(prepared_catalog_state.eligible_products or []), "__all__"
#         subset = []
#         for category in categories:
#             subset.extend(list((prepared_catalog_state.category_subsets or {}).get(category) or []))
#         if not subset:
#             return [], "__all__"
#         seen = set()
#         deduped = []
#         for product in subset:
#             product_id = product.get("id")
#             if not product_id or product_id in seen:
#                 continue
#             seen.add(product_id)
#             deduped.append(product)
#         subset_key = "__".join(sorted(categories))
#         return deduped, subset_key

#     def _extract_schema(self, payload):
#         chat_text = str(payload.get("chat_text") or payload.get("raw_chat") or "").strip()
#         extraction_context = payload.get("extracted_schema") or {}
#         if extraction_context and extraction_context.get("intake_confidence") is not None:
#             context_schema = dict(extraction_context)
#             if chat_text and not context_schema.get("raw_chat"):
#                 context_schema["raw_chat"] = chat_text
#             return dict(self.extraction_service.extract("", context=context_schema))
#         if chat_text:
#             return dict(self.extraction_service.extract(chat_text, context=extraction_context))

#         fallback_schema = {
#             "raw_chat": chat_text,
#             "company_size": None,
#             "industry": payload.get("industry"),
#             "business_type": payload.get("business_type"),
#             "team_size": payload.get("team_size"),
#             "workload_types": payload.get("workload_types") or payload.get("workloads") or [],
#             "application_signals": payload.get("application_signals") or [],
#             "capability_tags": payload.get("capability_tags") or [],
#             "budget": payload.get("budget"),
#             "growth_expectation": payload.get("growth_expectation"),
#             "existing_infrastructure": payload.get("existing_infrastructure") or [],
#             "preferred_manufacturers": payload.get("preferred_manufacturers") or [],
#             "blocked_manufacturers": payload.get("blocked_manufacturers") or [],
#             "preferred_sellers": payload.get("preferred_sellers") or [],
#             "blocked_sellers": payload.get("blocked_sellers") or [],
#             "preferred_category": payload.get("preferred_category") or payload.get("category"),
#             "performance_priority": payload.get("performance_priority"),
#             "portability_need": payload.get("portability_need"),
#             "support_expectation": payload.get("support_expectation"),
#             "availability_need": payload.get("availability_need"),
#             "require_returnable": payload.get("require_returnable"),
#             "quantity": payload.get("quantity"),
#             "purchase_scope": payload.get("purchase_scope"),
#             "timeline": payload.get("timeline"),
#             "requested_ram": payload.get("requested_ram"),
#             "requested_storage": payload.get("requested_storage"),
#             "requested_ram_is_minimum": payload.get("requested_ram_is_minimum"),
#             "requested_storage_is_minimum": payload.get("requested_storage_is_minimum"),
#             "notes": payload.get("notes", ""),
#             "missing_fields": [],
#             "intake_confidence": 1.0,
#         }
#         return dict(self.extraction_service.extract("", context=fallback_schema))

#     def _build_compatibility_report(self, compatibility_result):
#         compatibility_result = compatibility_result or {}
#         summary = compatibility_result.get("summary") or {}
#         return {
#             "scope": summary.get("compatibility_scope") or "item",
#             "summary": summary,
#             "rejected_products": (compatibility_result.get("rejected_products") or [])[:5],
#         }

#     def _deterministic_candidate_pool(self, normalized_products, top_k=40):
#         candidates = []
#         for product in list(normalized_products or [])[:top_k]:
#             product_id = product.get("id")
#             if not product_id:
#                 continue
#             candidates.append(
#                 {
#                     "product_id": product_id,
#                     "base_product_id": product.get("base_product_id") or product_id,
#                     "manufacturer": str(product.get("manufacturer") or "").strip().lower(),
#                     "candidate_score": 1.0,
#                     "semantic_norm": 0.0,
#                     "lexical_norm": 0.0,
#                     "business_boost": 1.0,
#                 }
#             )
#         return {
#             "candidate_ids": [item["product_id"] for item in candidates],
#             "scored_candidates": candidates,
#             "fallback_reason": "semantic_retrieval_disabled",
#         }

#     def _screen_catalog_metadata(self, normalized_products):
#         eligible_products = []
#         rejected_products = []
#         for product in list(normalized_products or []):
#             metadata_validation = dict(product.get("metadata_validation") or {})
#             category = product.get("category")
#             missing_required_fields = list(metadata_validation.get("missing_required_fields") or [])
#             readiness_state = str(
#                 product.get("readiness_state") or metadata_validation.get("readiness_state") or ""
#             ).strip()
#             if readiness_state == "insufficient":
#                 rejected_products.append(
#                     {
#                         "product_id": product.get("id"),
#                         "name": product.get("name"),
#                         "category": category,
#                         "manufacturer": product.get("manufacturer"),
#                         "reasons": list(metadata_validation.get("parse_warnings") or [])
#                         or ["Missing required metadata: " + ", ".join(missing_required_fields)],
#                         "readiness_state": readiness_state,
#                         "missing_required_fields": missing_required_fields,
#                         "missing_critical_fields": list(metadata_validation.get("missing_critical_fields") or []),
#                     }
#                 )
#                 continue
#             eligible_products.append(product)
#         return {
#             "eligible_products": eligible_products,
#             "rejected_products": rejected_products,
#             "summary": {
#                 "input_count": len(list(normalized_products or [])),
#                 "eligible_count": len(eligible_products),
#                 "rejected_count": len(rejected_products),
#             },
#         }

#     def _catalog_source_snapshot(self):
#         getter = getattr(self.catalog_repository, "get_observability_snapshot", None)
#         if callable(getter):
#             try:
#                 snapshot = dict(getter() or {})
#             except Exception:
#                 snapshot = {}
#         else:
#             snapshot = {}
#         if snapshot:
#             return snapshot
#         return {
#             "source_name": getattr(self.catalog_repository, "source_name", self.catalog_repository.__class__.__name__),
#             "source_load_success": True,
#             "unmatched_inventory_count": 0,
#         }

#     def _build_catalog_observability(
#         self,
#         raw_products,
#         normalized_products,
#         catalog_validation_result,
#         requirements,
#         currency_fallback_used=False,
#         catalog_source_snapshot=None,
#         store_scope_applied=False,
#     ):
#         raw_products = list(raw_products or [])
#         normalized_products = list(normalized_products or [])
#         catalog_validation_result = dict(catalog_validation_result or {})
#         requirements = dict(requirements or {})
#         catalog_source_snapshot = dict(catalog_source_snapshot or {})
#         readiness_state_counts = {}
#         parse_warning_count = 0
#         provisional_count = 0
#         for product in normalized_products:
#             readiness_state = str(product.get("readiness_state") or "unknown").strip() or "unknown"
#             readiness_state_counts[readiness_state] = readiness_state_counts.get(readiness_state, 0) + 1
#             parse_warning_count += len(product.get("parse_warnings") or [])
#             if readiness_state == "provisional":
#                 provisional_count += 1
#         return {
#             "source_name": catalog_source_snapshot.get("source_name")
#             or getattr(self.catalog_repository, "source_name", self.catalog_repository.__class__.__name__),
#             "source_load_success": bool(catalog_source_snapshot.get("source_load_success", True)),
#             "source_path": catalog_source_snapshot.get("source_path"),
#             "requested_store_id": str(requirements.get("store_id") or ""),
#             "applied_store_id": str(catalog_source_snapshot.get("requested_store_id") or ""),
#             "store_scope_applied": bool(store_scope_applied),
#             "requested_currency": str(requirements.get("currency") or ""),
#             "matched_product_count": int(catalog_source_snapshot.get("matched_product_count") or len(raw_products)),
#             "normalized_candidate_count": len(normalized_products),
#             "unmatched_inventory_count": int(catalog_source_snapshot.get("unmatched_inventory_count") or 0),
#             "readiness_state_counts": readiness_state_counts,
#             "parse_warning_count": parse_warning_count,
#             "currency_fallback_count": 1 if currency_fallback_used else 0,
#             "currency_fallback_used": bool(currency_fallback_used),
#             "provisional_count": provisional_count,
#             "store_filter_miss": bool(
#                 store_scope_applied
#                 and (
#                     catalog_source_snapshot.get("store_filter_miss")
#                     or (requirements.get("store_id") and not raw_products)
#                 )
#             ),
#             "validation_block_count": len(catalog_validation_result.get("rejected_products") or []),
#         }

#     def _aggregate_catalog_observability(self, recommendation_groups):
#         recommendation_groups = list(recommendation_groups or [])
#         readiness_state_counts = {}
#         source_names = []
#         source_paths = []
#         total_unmatched_inventory = 0
#         total_normalized_candidate_count = 0
#         total_parse_warning_count = 0
#         total_currency_fallback_count = 0
#         total_provisional_count = 0
#         total_validation_block_count = 0
#         any_store_filter_miss = False
#         any_store_scope_applied = False
#         all_load_success = True
#         for group in recommendation_groups:
#             group_observability = dict((group.get("meta") or {}).get("catalog_observability") or {})
#             if not group_observability:
#                 continue
#             source_name = group_observability.get("source_name")
#             source_path = group_observability.get("source_path")
#             if source_name and source_name not in source_names:
#                 source_names.append(source_name)
#             if source_path and source_path not in source_paths:
#                 source_paths.append(source_path)
#             for readiness_state, count in dict(group_observability.get("readiness_state_counts") or {}).items():
#                 readiness_state_counts[readiness_state] = readiness_state_counts.get(readiness_state, 0) + int(count or 0)
#             total_unmatched_inventory += int(group_observability.get("unmatched_inventory_count") or 0)
#             total_normalized_candidate_count += int(group_observability.get("normalized_candidate_count") or 0)
#             total_parse_warning_count += int(group_observability.get("parse_warning_count") or 0)
#             total_currency_fallback_count += int(group_observability.get("currency_fallback_count") or 0)
#             total_provisional_count += int(group_observability.get("provisional_count") or 0)
#             total_validation_block_count += int(group_observability.get("validation_block_count") or 0)
#             any_store_filter_miss = any_store_filter_miss or bool(group_observability.get("store_filter_miss"))
#             any_store_scope_applied = any_store_scope_applied or bool(group_observability.get("store_scope_applied"))
#             all_load_success = all_load_success and bool(group_observability.get("source_load_success", True))
#         return {
#             "source_names": source_names,
#             "source_paths": source_paths,
#             "source_load_success": all_load_success,
#             "unmatched_inventory_count": total_unmatched_inventory,
#             "normalized_candidate_count": total_normalized_candidate_count,
#             "readiness_state_counts": readiness_state_counts,
#             "parse_warning_count": total_parse_warning_count,
#             "currency_fallback_count": total_currency_fallback_count,
#             "currency_fallback_used": bool(total_currency_fallback_count),
#             "provisional_count": total_provisional_count,
#             "store_scope_applied": any_store_scope_applied,
#             "store_filter_miss": any_store_filter_miss,
#             "validation_block_count": total_validation_block_count,
#         }

#     def _compatibility_bypass(self, normalized_products):
#         products = list(normalized_products or [])
#         return {
#             "eligible_products": products,
#             "rejected_products": [],
#             "reports_by_product_id": {},
#             "summary": {
#                 "compatibility_scope": "item",
#                 "evaluated_count": len(products),
#                 "eligible_count": len(products),
#                 "rejected_count": 0,
#                 "skipped_by_flag": True,
#             },
#         }

#     def _expert_review_reason(self, readiness, ranking_deferred, fallback_reason, compatibility_result, recommendations):
#         if ranking_deferred:
#             return "low_confidence_clarification_required"
#         if fallback_reason in {"compatibility_blocked_all", "policy_rejected_all", "no_exact_fit"}:
#             return fallback_reason
#         if (readiness or {}).get("decision_confidence_band") == "low":
#             return "low_confidence_routing"
#         if compatibility_result.get("rejected_products") and not recommendations:
#             return "hard_conflict_detected"
#         return ""

#     def _clarification_required_reasons(self, readiness):
#         readiness = dict(readiness or {})
#         question_candidates = list(readiness.get("question_candidates") or [])
#         threshold = self.clarification_service.question_impact_threshold()
#         reasons = [
#             str(item.get("key") or "").strip()
#             for item in question_candidates
#             if str(item.get("key") or "").strip() and float(item.get("impact") or 0.0) >= threshold
#         ]
#         if reasons:
#             return self._dedupe_strings(reasons)

#         critical_missing = [
#             signal
#             for signal in list(readiness.get("missing_signals") or [])
#             if signal in self._hard_critical_signals()
#         ]
#         if critical_missing:
#             return self._dedupe_strings(critical_missing)
#         return []

#     def _recommendation_mode(
#         self,
#         readiness,
#         recommendations,
#         fallback_reason,
#         expert_review_reason,
#         clarification_required_reasons,
#         candidate_pool_size=0,
#     ):
#         readiness = dict(readiness or {})
#         recommendations = list(recommendations or [])
#         clarification_required_reasons = list(clarification_required_reasons or [])
#         mode_policy = self.config_service.get_recommendation_mode_policy()
#         expert_review_fallback_reasons = set(mode_policy.get("expert_review_fallback_reasons") or [])
#         minimum_safe_candidate_count = int(mode_policy.get("minimum_safe_candidate_count") or 0)
#         max_hard_critical_for_clarification = int(
#             mode_policy.get("max_hard_critical_reasons_for_clarification") or 0
#         )
#         max_hard_critical_for_provisional = int(
#             mode_policy.get("max_hard_critical_reasons_for_provisional") or 0
#         )
#         hard_critical_reasons = self._hard_critical_reasons(readiness, clarification_required_reasons)
#         ranking_deferred = self.clarification_service.should_defer_ranking(readiness)
#         insufficient_candidates = minimum_safe_candidate_count > 0 and int(candidate_pool_size or 0) < minimum_safe_candidate_count

#         if not recommendations:
#             if fallback_reason in expert_review_fallback_reasons:
#                 return "expert_review_recommended"
#             if insufficient_candidates:
#                 return "expert_review_recommended"
#             if ranking_deferred:
#                 return (
#                     "clarification_required"
#                     if clarification_required_reasons and len(hard_critical_reasons) <= max_hard_critical_for_clarification
#                     else "expert_review_recommended"
#                 )
#             if expert_review_reason:
#                 return "expert_review_recommended"
#             return (
#                 "clarification_required"
#                 if clarification_required_reasons and len(hard_critical_reasons) <= max_hard_critical_for_clarification
#                 else "expert_review_recommended"
#             )

#         if clarification_required_reasons:
#             if insufficient_candidates:
#                 return "expert_review_recommended"
#             if len(hard_critical_reasons) > max_hard_critical_for_provisional:
#                 return "expert_review_recommended"
#             return "provisional_recommendation"
#         if expert_review_reason or insufficient_candidates:
#             return "expert_review_recommended"
#         return "firm_recommendation"

#     def _build_decision_trace(
#         self,
#         decision_trace_id,
#         requirements,
#         extracted_schema,
#         target_profile,
#         readiness,
#         retrieval_result,
#         catalog_validation_result,
#         compatibility_result,
#         policy_result,
#         recommendations,
#         fallback_reason,
#         recommendation_mode,
#         clarification_required_reasons,
#         expert_review_reason,
#         feature_flags,
#         decision_policy_profile,
#         check_requirement_summary,
#         editable_inferred_values,
#         template_candidates,
#         selected_template,
#     ):
#         return {
#             "decision_trace_id": decision_trace_id,
            
#             "catalog_validation": {
#                 "summary": catalog_validation_result.get("summary") or {},
#                 "rejected_products": catalog_validation_result.get("rejected_products") or [],
#             },
#             "retrieval": retrieval_result,
#             "compatibility": {
#                 "scope": (compatibility_result.get("summary") or {}).get("compatibility_scope") or "item",
#                 "summary": compatibility_result.get("summary") or {},
#                 "rejected_products": compatibility_result.get("rejected_products") or [],
#             },
#             "policy": {
#                 "summary": policy_result.get("summary") or {},
#                 "rejected_products": policy_result.get("rejected_products") or [],
#             },
#             "expert_review_reason": expert_review_reason,
#             "feature_flags": feature_flags,
#             "config_versions": self.config_service.get_versions(),
#         }

#     def _hard_critical_signals(self):
#         signals = self.config_service.get_recommendation_mode_policy().get("hard_critical_signals") or []
#         return set(self._dedupe_strings(signals))

#     def _hard_critical_reasons(self, readiness, clarification_required_reasons):
#         hard_critical_signals = self._hard_critical_signals()
#         return self._dedupe_strings(
#             [
#                 reason
#                 for reason in (clarification_required_reasons or []) + list((readiness or {}).get("missing_signals") or [])
#                 if reason in hard_critical_signals
#             ]
#         )





# import os
# from concurrent.futures import ThreadPoolExecutor
# from time import perf_counter
# from uuid import uuid4

# from ...catalog.services.normalization import normalize_product_document
# from ...catalog.services.repository import build_runtime_catalog_repository
# from ...catalog.services.semantic_retriever import SemanticProductRetriever

# from .explanations import ProcurementExplanationService
# from .feature_flags import ProcurementFeatureFlagService
# from .followup_generation import AdaptiveFollowUpService
# from .intake import RequirementIntakeService
# from .observability import ProcurementRuntimeObservabilityService
# from .policy import ProcurementPolicyService
# from .ranking import ProductRankingService
# from .recommendation_context import (
#     PreparedCatalogState,
#     PreparedProcurementContext,
#     RecommendationContextBuilder,
#     RecommendationCoreResult,
# )
# from .recommendation_core import RecommendationCoreEngine
# from .recommendation_presenter import RecommendationPresenter
# from .review_support import ProcurementReviewSupportService
# from .requirement_extraction import RequirementExtractionService
# from .rules_engine import ProcurementRulesEngine
# from .clarification import ProcurementClarificationService
# from .bundle_service import ProcurementBundleService
# from .compatibility import ProcurementCompatibilityService
# from .config_service import ProcurementConfigService
# from .multi_intent import ProcurementMultiIntentService
# from .multi_intent_policy import ProcurementMultiIntentPolicyService
# from .template_service import ProcurementTemplateService


# ENGINE_VERSION = "phase1-v8"

# class ProcurementRecommendationService:
#     _persistence_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="procurement-persist")

#     def __init__(
#         self,
#         catalog_repository=None,
#         config_service=None,
#         intake_service=None,
#         rules_engine=None,
#         ranking_service=None,
#         policy_service=None,
#         compatibility_service=None,
#         explanation_service=None,
#         clarification_service=None,
#         extraction_service=None,
#         semantic_retriever=None,
#         followup_service=None,
#         feature_flag_service=None,
#         multi_intent_service=None,
#         multi_intent_policy_service=None,
#         observability_service=None,
#         bundle_service=None,
#         template_service=None,
#         review_support_service=None,
#     ):
#         self.catalog_repository = catalog_repository or build_runtime_catalog_repository()
#         self.config_service = config_service or ProcurementConfigService()
#         self.intake_service = intake_service or RequirementIntakeService()
#         self.rules_engine = rules_engine or ProcurementRulesEngine(config_service=self.config_service)
#         self.ranking_service = ranking_service or ProductRankingService(config_service=self.config_service)
#         self.policy_service = policy_service or ProcurementPolicyService(config_service=self.config_service)
#         self.compatibility_service = compatibility_service or ProcurementCompatibilityService(config_service=self.config_service)
#         self.explanation_service = explanation_service or ProcurementExplanationService(config_service=self.config_service)
#         self.clarification_service = clarification_service or ProcurementClarificationService(config_service=self.config_service)
#         self.extraction_service = extraction_service or RequirementExtractionService()
#         self.semantic_retriever = semantic_retriever or SemanticProductRetriever()
#         self.followup_service = followup_service or AdaptiveFollowUpService()
#         self.feature_flag_service = feature_flag_service or ProcurementFeatureFlagService()
#         self.multi_intent_service = multi_intent_service or ProcurementMultiIntentService(
#             extraction_service=self.extraction_service
#         )
#         self.multi_intent_policy_service = multi_intent_policy_service or ProcurementMultiIntentPolicyService()
#         self.observability_service = observability_service or ProcurementRuntimeObservabilityService(
#             config_service=self.config_service
#         )
#         self.bundle_service = bundle_service or ProcurementBundleService(
#             compatibility_service=self.compatibility_service
#         )
#         self.template_service = template_service or ProcurementTemplateService(config_service=self.config_service)
#         self.review_support_service = review_support_service or ProcurementReviewSupportService()
#         self._prepared_catalog_state_cache = {}
#         self.context_builder = RecommendationContextBuilder(self)
#         self.core_engine = RecommendationCoreEngine(self)
#         self.presenter = RecommendationPresenter(self)

#     def has_minimum_context(self, payload):
#         requirements = self.intake_service.normalize(payload)
#         readiness = self.clarification_service.assess(requirements)
#         return bool(requirements.get("budget") is not None and not self.clarification_service.should_defer_ranking(readiness))

#     def _new_top_level_timings(self, source_mode=""):
#         prepare_ms = {"total_ms": 0.0}
#         if source_mode:
#             prepare_ms["source_mode"] = str(source_mode)
#         return {
#             "prepare_ms": prepare_ms,
#             "core_ms": {
#                 "total_ms": 0.0,
#                 "multi_intent_detect_ms": 0.0,
#                 "catalog_fetch_ms": 0.0,
#                 "compatibility_ms": 0.0,
#                 "policy_ms": 0.0,
#                 "ranking_ms": 0.0,
#                 "explanations_ms": 0.0,
#                 "response_assembly_ms": 0.0,
#             },
#             "presentation_ms": {
#                 "assembly_ms": 0.0,
#                 "question_generation_ms": 0.0,
#                 "narrative_ms": 0.0,
#                 "persistence_dispatch_ms": 0.0,
#                 "total_ms": 0.0,
#             },
#             "pipeline_ms": {"total_ms": 0.0},
#         }

#     def _finalize_top_level_timings(self, top_level_timings, pipeline_started_at=None, response=None):
#         top_level_timings = dict(top_level_timings or {})
#         core_ms = dict(top_level_timings.get("core_ms") or {})
#         presentation_ms = dict(top_level_timings.get("presentation_ms") or {})
#         stage_timings = dict((((response or {}).get("meta") or {}).get("stage_timings_ms") or {}))
#         core_ms["catalog_fetch_ms"] = round(float(stage_timings.get("catalog_fetch_ms") or core_ms.get("catalog_fetch_ms") or 0.0), 2)
#         core_ms["compatibility_ms"] = round(float(stage_timings.get("compatibility_ms") or core_ms.get("compatibility_ms") or 0.0), 2)
#         core_ms["policy_ms"] = round(float(stage_timings.get("policy_ms") or core_ms.get("policy_ms") or 0.0), 2)
#         core_ms["ranking_ms"] = round(float(stage_timings.get("ranking_ms") or core_ms.get("ranking_ms") or 0.0), 2)
#         core_ms["explanations_ms"] = round(float(stage_timings.get("explanations_ms") or core_ms.get("explanations_ms") or 0.0), 2)
#         core_ms["response_assembly_ms"] = round(
#             float(stage_timings.get("response_assembly_ms") or core_ms.get("response_assembly_ms") or 0.0),
#             2,
#         )
#         top_level_timings["core_ms"] = core_ms
#         question_generation_ms = float(stage_timings.get("question_generation_ms") or presentation_ms.get("question_generation_ms") or 0.0)
#         presentation_ms["question_generation_ms"] = round(question_generation_ms, 2)
#         presentation_ms["total_ms"] = round(
#             sum(
#                 float(presentation_ms.get(key) or 0.0)
#                 for key in ("assembly_ms", "question_generation_ms", "narrative_ms", "persistence_dispatch_ms")
#             ),
#             2,
#         )
#         top_level_timings["presentation_ms"] = presentation_ms
#         if pipeline_started_at is not None:
#             self._mark_stage(top_level_timings.setdefault("pipeline_ms", {}), "total_ms", pipeline_started_at)
#         return top_level_timings

#     def recommend(self, payload, user_id="", business_id="", persist=True):
#         payload = dict(payload or {})
#         feature_flags = dict(self.feature_flag_service.get_flags())
#         if str(payload.get("channel") or "").strip().lower() == "websocket":
#             persist = False
#         pipeline_started_at = perf_counter()
#         top_level_timings = self._new_top_level_timings()

#         prepare_started_at = perf_counter()
#         prepared = self.prepare_from_raw_payload(payload, feature_flags=feature_flags)
#         self._mark_stage(top_level_timings["prepare_ms"], "total_ms", prepare_started_at)

#         detect_started_at = perf_counter()
#         multi_intent_result = self.multi_intent_service.detect(payload, prepared.extracted_schema)
#         self._mark_stage(top_level_timings["core_ms"], "multi_intent_detect_ms", detect_started_at)
#         if multi_intent_result.get("is_multi_intent"):
#             response = self._recommend_multi_intent(
#                 payload=payload,
#                 multi_intent_result=multi_intent_result,
#                 extracted_schema=prepared.extracted_schema,
#                 feature_flags=feature_flags,
#                 user_id=user_id,
#                 business_id=business_id,
#                 persist=persist,
#                 prepared_context=prepared,
#                 top_level_timings=top_level_timings,
#             )
#         else:
#             response = self._recommend_single(
#                 payload=payload,
#                 extracted_schema=prepared.extracted_schema,
#                 prepared_context=prepared,
#                 feature_flags=feature_flags,
#                 user_id=user_id,
#                 business_id=business_id,
#                 persist=persist,
#                 top_level_timings=top_level_timings,
#             )
#         top_level_timings = self._finalize_top_level_timings(
#             top_level_timings,
#             pipeline_started_at=pipeline_started_at,
#             response=response,
#         )
#         response.setdefault("meta", {})
#         response["meta"]["top_level_timings_ms"] = top_level_timings
#         return response

#     def prepare_from_raw_payload(self, payload, feature_flags=None, decision_trace_id=None):
#         return self.context_builder.prepare_from_raw_payload(
#             payload=payload,
#             feature_flags=feature_flags,
#             decision_trace_id=decision_trace_id,
#         )

#     def prepare_from_extracted_schema(
#         self,
#         payload,
#         extracted_schema,
#         feature_flags=None,
#         decision_trace_id=None,
#         source_mode="extracted_schema",
#         prepared_catalog_state=None,
#     ):
#         return self.context_builder.prepare_from_extracted_schema(
#             payload=payload,
#             extracted_schema=extracted_schema,
#             feature_flags=feature_flags,
#             decision_trace_id=decision_trace_id,
#             source_mode=source_mode,
#             prepared_catalog_state=prepared_catalog_state,
#         )

#     def recommend_prepared_context(
#         self,
#         prepared_context,
#         feature_flags=None,
#         user_id="",
#         business_id="",
#         persist=True,
#         capture_runtime_observability=True,
#     ):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         pipeline_started_at = perf_counter()
#         top_level_timings = self._new_top_level_timings(source_mode=prepared_context.source_mode)
#         if str(prepared_context.channel or "").strip().lower() == "websocket":
#             persist = False
#         detect_started_at = perf_counter()
#         multi_intent_result = self.core_engine.detect_multi_intent(
#             prepared_context.normalized_payload,
#             prepared_context.extracted_schema,
#         )
#         self._mark_stage(top_level_timings["core_ms"], "multi_intent_detect_ms", detect_started_at)
#         if multi_intent_result.get("is_multi_intent"):
#             response = self._recommend_multi_intent(
#                 payload=prepared_context.normalized_payload,
#                 multi_intent_result=multi_intent_result,
#                 extracted_schema=prepared_context.extracted_schema,
#                 prepared_context=prepared_context,
#                 feature_flags=feature_flags,
#                 user_id=user_id,
#                 business_id=business_id,
#                 persist=persist,
#                 top_level_timings=top_level_timings,
#             )
#         else:
#             response = self._recommend_single_from_prepared(
#                 prepared_context=prepared_context,
#                 feature_flags=feature_flags,
#                 user_id=user_id,
#                 business_id=business_id,
#                 persist=persist,
#                 capture_runtime_observability=capture_runtime_observability,
#                 top_level_timings=top_level_timings,
#             )
#         top_level_timings = self._finalize_top_level_timings(
#             top_level_timings,
#             pipeline_started_at=pipeline_started_at,
#             response=response,
#         )
#         response.setdefault("meta", {})
#         response["meta"]["top_level_timings_ms"] = top_level_timings
#         return response

#     def recommend_from_chat_preferences(self, chat_preferences, store_id="", persist=False):
#         chat_preferences = dict(chat_preferences or {})
#         payload = {
#             "store_id": chat_preferences.get("store_id") or store_id or "",
#             "channel": "websocket",
#             "currency": chat_preferences.get("currency", "INR"),
#             "category": chat_preferences.get("category") or chat_preferences.get("preferred_category"),
#             "industry": chat_preferences.get("industry"),
#             "business_type": chat_preferences.get("business_type"),
#             "team_size": chat_preferences.get("team_size"),
#             "workload_types": chat_preferences.get("workloads") or chat_preferences.get("workload_types"),
#             "application_signals": chat_preferences.get("application_signals") or [],
#             "capability_tags": chat_preferences.get("capability_tags") or [],
#             "budget": chat_preferences.get("budget"),
#             "budget_scope": chat_preferences.get("budget_scope"),
#             "growth_expectation": chat_preferences.get("growth_expectation"),
#             "existing_infrastructure": chat_preferences.get("existing_infrastructure") or [],
#             "preferred_manufacturers": chat_preferences.get("preferred_manufacturers") or [],
#             "blocked_manufacturers": chat_preferences.get("blocked_manufacturers") or [],
#             "preferred_sellers": chat_preferences.get("preferred_sellers") or [],
#             "blocked_sellers": chat_preferences.get("blocked_sellers") or [],
#             "requested_ram": chat_preferences.get("specifications.ram_size"),
#             "requested_storage": chat_preferences.get("specifications.storage_size"),
#             "requested_ram_is_minimum": chat_preferences.get("requested_ram_is_minimum"),
#             "requested_storage_is_minimum": chat_preferences.get("requested_storage_is_minimum"),
#             "minimum_warranty_years": chat_preferences.get("minimum_warranty_years"),
#             "required_port_count": chat_preferences.get("required_port_count"),
#             "required_throughput_mbps": chat_preferences.get("required_throughput_mbps"),
#             "required_duplex_printing": chat_preferences.get("required_duplex_printing"),
#             "required_scanner": chat_preferences.get("required_scanner"),
#             "min_print_speed_ppm": chat_preferences.get("min_print_speed_ppm"),
#             "required_printer_type": chat_preferences.get("required_printer_type"),
#             "required_print_technology": chat_preferences.get("required_print_technology"),
#             "required_color_output": chat_preferences.get("required_color_output"),
#             "min_monthly_duty_cycle_pages": chat_preferences.get("min_monthly_duty_cycle_pages"),
#             "required_automatic_document_feeder": chat_preferences.get("required_automatic_document_feeder"),
#             "required_paper_sizes": chat_preferences.get("required_paper_sizes"),
#             "required_network_roles": chat_preferences.get("required_network_roles"),
#             "required_vpn_user_capacity": chat_preferences.get("required_vpn_user_capacity"),
#             "required_virtualization_ready": chat_preferences.get("required_virtualization_ready"),
#             "required_virtualization_platforms": chat_preferences.get("required_virtualization_platforms"),
#             "max_rack_units": chat_preferences.get("max_rack_units"),
#             "max_power_draw_watts": chat_preferences.get("max_power_draw_watts"),
#             "battery_life_hours_min": chat_preferences.get("battery_life_hours_min"),
#             "cpu_preference": chat_preferences.get("cpu_preference"),
#             "gpu_requirement": chat_preferences.get("gpu_requirement"),
#             "screen_size_preference": chat_preferences.get("screen_size_preference"),
#             "weight_kg_max": chat_preferences.get("weight_kg_max"),
#             "warranty_type_preference": chat_preferences.get("warranty_type_preference"),
#             "performance_priority": chat_preferences.get("performance_priority"),
#             "portability_need": chat_preferences.get("portability_need"),
#             "support_expectation": chat_preferences.get("support_expectation"),
#             "availability_need": chat_preferences.get("availability_need"),
#             "require_returnable": chat_preferences.get("require_returnable"),
#             "quantity": chat_preferences.get("quantity"),
#             "purchase_scope": chat_preferences.get("purchase_scope"),
#             "timeline": chat_preferences.get("timeline"),
#             "raw_chat": chat_preferences.get("raw_chat", ""),
#             "notes": chat_preferences.get("notes", ""),
#             "extracted_schema": dict(chat_preferences),
#         }
#         prepared_context = self.prepare_from_extracted_schema(
#             payload=payload,
#             extracted_schema=dict(chat_preferences),
#             source_mode="chat_preferences",
#         )
#         return self.recommend_prepared_context(prepared_context, persist=persist)

#     def _recommend_single(
#         self,
#         payload,
#         extracted_schema=None,
#         prepared_context=None,
#         feature_flags=None,
#         user_id="",
#         business_id="",
#         persist=True,
#         decision_trace_id=None,
#         capture_runtime_observability=True,
#         top_level_timings=None,
#     ):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         payload = dict(payload or {})
#         top_level_timings = top_level_timings or self._new_top_level_timings()
#         if prepared_context is None:
#             prepare_started_at = perf_counter()
#             prepared_context = self.prepare_from_extracted_schema(
#                 payload=payload,
#                 extracted_schema=dict(extracted_schema or self._extract_schema(payload)),
#                 feature_flags=feature_flags,
#                 decision_trace_id=decision_trace_id,
#             )
#             self._mark_stage(top_level_timings["prepare_ms"], "total_ms", prepare_started_at)
#         return self._recommend_single_from_prepared(
#             prepared_context=prepared_context,
#             feature_flags=feature_flags,
#             user_id=user_id,
#             business_id=business_id,
#             persist=persist,
#             capture_runtime_observability=capture_runtime_observability,
#             top_level_timings=top_level_timings,
#         )

#     def _recommend_single_from_prepared(
#         self,
#         prepared_context,
#         feature_flags=None,
#         user_id="",
#         business_id="",
#         persist=True,
#         capture_runtime_observability=True,
#         top_level_timings=None,
#     ):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         top_level_timings = top_level_timings or self._new_top_level_timings()
#         started_at = self.observability_service.start_timer() if capture_runtime_observability else None
#         core_started_at = perf_counter()
#         core_result, debug_trace = self.core_engine.run(
#             prepared_context,
#             feature_flags=feature_flags,
#             defer_explanations=bool(prepared_context.normalized_payload.get("_defer_explanations")),
#         )
#         self._mark_stage(top_level_timings["core_ms"], "total_ms", core_started_at)
#         assembly_started_at = perf_counter()
#         response = self.presenter.assemble(
#             prepared_context=prepared_context,
#             core_result=core_result,
#             debug_trace=debug_trace,
#             feature_flags=feature_flags,
#             started_at=started_at,
#             capture_runtime_observability=capture_runtime_observability,
#         )
#         self._mark_stage(top_level_timings["presentation_ms"], "assembly_ms", assembly_started_at)
#         question_generation_ms = float(
#             (((response.get("meta") or {}).get("stage_timings_ms") or {}).get("question_generation_ms"))
#             or 0.0
#         )
#         top_level_timings["presentation_ms"]["question_generation_ms"] = round(question_generation_ms, 2)
#         if question_generation_ms:
#             top_level_timings["presentation_ms"]["assembly_ms"] = max(
#                 round(float(top_level_timings["presentation_ms"]["assembly_ms"]) - question_generation_ms, 2),
#                 0.0,
#             )
#         narrative_started_at = perf_counter()
#         response = self.presenter.enrich(
#             prepared_context=prepared_context,
#             response=response,
#             feature_flags=feature_flags,
#         )
#         self._mark_stage(top_level_timings["presentation_ms"], "narrative_ms", narrative_started_at)
#         persistence_started_at = perf_counter()
#         if persist:
#             self._dispatch_persistence_from_outputs(
#                 prepared_context=prepared_context,
#                 response=response,
#                 user_id=user_id,
#                 business_id=business_id,
#             )
#         self._mark_stage(top_level_timings["presentation_ms"], "persistence_dispatch_ms", persistence_started_at)
#         top_level_timings["presentation_ms"]["total_ms"] = round(
#             sum(
#                 float(top_level_timings["presentation_ms"].get(key) or 0.0)
#                 for key in ("assembly_ms", "question_generation_ms", "narrative_ms", "persistence_dispatch_ms")
#             ),
#             2,
#         )
#         return response

#     def recommend_from_state(
#         self,
#         state: dict,
#         user_id="",
#         business_id="",
#         persist=False,
#     ):
#         raw_state = dict(state or {})
#         requirements = dict(raw_state.get("requirements") or raw_state)
#         conversation_meta = dict(raw_state.get("conversation_meta") or {})

#         for field in ("intent_groups", "preferred_categories", "preferred_category", "budget", "budget_scope", "team_size", "quantity"):
#             value = raw_state.get(field)
#             if value not in (None, "", [], {}) and requirements.get(field) in (None, "", [], {}):
#                 requirements[field] = value

#         if requirements.get("raw_chat") in (None, ""):
#             brief = str(conversation_meta.get("conversation_brief") or "").strip()
#             if brief:
#                 requirements["raw_chat"] = brief

#         payload = dict(requirements)
#         payload.setdefault("channel", "websocket")
#         payload.setdefault("_defer_explanations", True)
#         prepared_context = self.prepare_from_extracted_schema(
#             payload=payload,
#             extracted_schema=requirements,
#             source_mode="planner_state",
#         )
#         return self.recommend_prepared_context(
#             prepared_context,
#             user_id=user_id,
#             business_id=business_id,
#             persist=persist,
#         )

#     def _build_budget_fit_summary(self, requirements, recommendations):
#         budget = requirements.get("budget")
#         if budget is None:
#             return {
#                 "budget_present": False,
#                 "within_budget_count": 0,
#                 "over_budget_count": 0,
#                 "no_exact_budget_fit": False,
#             }
#         quantity = requirements.get("quantity") or requirements.get("team_size") or 1
#         budget_scope = requirements.get("budget_scope")
#         within_budget_count = 0
#         over_budget_count = 0
#         for recommendation in list(recommendations or []):
#             price = recommendation.get("price")
#             total_cost = recommendation.get("estimated_total_cost")
#             reference = self.ranking_service._budget_reference(price, budget_scope, quantity, total_cost)
#             if reference is None:
#                 continue
#             if reference <= budget:
#                 within_budget_count += 1
#             else:
#                 over_budget_count += 1
#         return {
#             "budget_present": True,
#             "within_budget_count": within_budget_count,
#             "over_budget_count": over_budget_count,
#             "no_exact_budget_fit": bool(recommendations) and within_budget_count == 0,
#         }

#     def _prefix_no_exact_budget_fit_summary(self, summary, requirements, recommendations):
#         currency = str(requirements.get("currency") or "INR").strip() or "INR"
#         budget = requirements.get("budget")
#         quantity = requirements.get("quantity") or requirements.get("team_size") or 1
#         budget_scope = str(requirements.get("budget_scope") or "").replace("_", " ").strip()
#         if not budget_scope and int(quantity or 1) > 1:
#             base = (
#                 f"No exact fit could be validated against the stated budget of {budget} {currency} because the budget scope is ambiguous for {quantity} units. "
#                 "No recommendations are shown until you confirm whether the budget is per unit or project total."
#             )
#         else:
#             budget_scope = budget_scope or "budget"
#             base = f"No exact in-catalog fit was found within the stated {budget_scope} budget of {budget} {currency}. No recommendations are shown until you raise the budget or relax the constraints."
#         summary = str(summary or "").strip()
#         if not summary:
#             return base
#         if summary.lower().startswith("no exact in-catalog fit") or summary.lower().startswith("no exact fit could be validated"):
#             return summary
#         return f"{base} {summary}".strip()

#     def _annotate_no_exact_budget_fit_recommendations(self, requirements, recommendations):
#         requirements = dict(requirements or {})
#         currency = str(requirements.get("currency") or "INR").strip() or "INR"
#         budget = requirements.get("budget")
#         quantity = requirements.get("quantity") or requirements.get("team_size") or 1
#         budget_scope = requirements.get("budget_scope")
#         annotated = []
#         for recommendation in list(recommendations or []):
#             item = dict(recommendation or {})
#             price = item.get("price")
#             total_cost = item.get("estimated_total_cost")
#             reference = self.ranking_service._budget_reference(price, budget_scope, quantity, total_cost)
#             note = ""
#             if reference is None:
#                 if int(quantity or 1) > 1 and not budget_scope:
#                     note = (
#                         f"Budget scope is ambiguous for {quantity} units; this is shown as a closest option until you confirm whether {budget} {currency} is per unit or project total."
#                     )
#             elif budget is not None and reference > budget:
#                 scope_label = str(budget_scope or ("project_total" if int(quantity or 1) > 1 else "budget")).replace("_", " ")
#                 note = f"Exceeds the stated {scope_label} budget of {budget} {currency}; shown as a closest stretch option."
#             if note:
#                 reasons = list(item.get("reasons") or [])
#                 if note not in reasons:
#                     reasons.insert(0, note)
#                 item["reasons"] = reasons
#                 item["fit_status"] = "stretch"
#             annotated.append(item)
#         return annotated

#     def _mark_stage(self, stage_timings, stage_name, started_at):
#         stage_timings[stage_name] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)

#     def _set_stage_total(self, stage_timings, stage_name, values):
#         values = [float(value or 0.0) for value in list(values or [])]
#         stage_timings[stage_name] = round(sum(values), 2)

#     def _hydrate_stage_aliases(self, stage_timings):
#         stage_timings = dict(stage_timings or {})
#         self._set_stage_total(
#             stage_timings,
#             "catalog_fetch_ms",
#             [
#                 stage_timings.get("catalog_state_access_ms"),
#                 stage_timings.get("category_subset_resolution_ms"),
#                 stage_timings.get("candidate_selection_ms"),
#             ],
#         )
#         self._set_stage_total(
#             stage_timings,
#             "compatibility_policy_ms",
#             [
#                 stage_timings.get("compatibility_ms"),
#                 stage_timings.get("policy_ms"),
#             ],
#         )
#         return stage_timings

#     def run_recommendation_core(self, prepared_context, feature_flags=None, defer_explanations=False):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         requirements = dict(prepared_context.requirements or {})
#         target_profile = dict(prepared_context.target_profile or {})
#         readiness = dict(prepared_context.readiness or {})
#         prepared_catalog_state = prepared_context.prepared_catalog_state or self._resolve_prepared_catalog_state(requirements)
#         stage_timings = {}
#         ranking_deferred = self.clarification_service.should_defer_ranking(readiness)
#         deferred_reason = ""
#         normalized_products = []
#         candidate_ids = []
#         retrieval_result = {"candidate_ids": [], "scored_candidates": [], "fallback_reason": None}
#         compatibility_result = {"eligible_products": [], "rejected_products": [], "summary": {}, "reports_by_product_id": {}}
#         policy_result = {"eligible_products": [], "rejected_products": [], "summary": {}}
#         rankable_products = []
#         recommendations = []
#         fallback_reason = ""
#         catalog_validation_result = {"eligible_products": [], "rejected_products": [], "summary": {}}
#         raw_products = []
#         all_normalized_products = []
#         currency_fallback_used = False
#         catalog_source_snapshot = {}
#         store_scope_applied = False

#         if ranking_deferred:
#             deferred_reason = "blocking_clarification_required"
#             fallback_reason = deferred_reason
#         else:
#             stage_started_at = perf_counter()
#             raw_products = list(prepared_catalog_state.raw_products or [])
#             all_normalized_products = list(prepared_catalog_state.normalized_products or [])
#             catalog_validation_result = dict(prepared_catalog_state.catalog_validation_result or {})
#             currency_fallback_used = bool(prepared_catalog_state.currency_fallback_used)
#             catalog_source_snapshot = dict(prepared_catalog_state.catalog_source_snapshot or {})
#             store_scope_applied = bool(prepared_catalog_state.store_scope_applied)
#             self._mark_stage(stage_timings, "catalog_state_access_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             category_filtered_products, subset_key = self._resolve_category_subset_from_state(
#                 prepared_catalog_state,
#                 target_profile.get("categories"),
#             )
#             self._mark_stage(stage_timings, "category_subset_resolution_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             if feature_flags.get("semantic_retrieval", True):
#                 retrieval_assets = (prepared_catalog_state.retrieval_assets_by_subset or {}).get(subset_key)
#                 if retrieval_assets is None and subset_key != "__all__":
#                     retrieval_assets = self.semantic_retriever.build_retrieval_assets(category_filtered_products)
#                 retrieval_result = self.semantic_retriever.retrieve_candidates_from_assets(
#                     retrieval_assets,
#                     requirements,
#                     target_profile,
#                     top_k=40,
#                     allow_broadening=feature_flags.get("retrieval_broadening", True),
#                 )
#                 candidate_ids = list(retrieval_result.get("candidate_ids") or [])
#                 normalized_products = self._filter_normalized_products(
#                     category_filtered_products,
#                     None,
#                     candidate_ids,
#                 )
#             else:
#                 retrieval_result = self._deterministic_candidate_pool(category_filtered_products, top_k=40)
#                 candidate_ids = list(retrieval_result.get("candidate_ids") or [])
#                 normalized_products = category_filtered_products[:40]
#             self._mark_stage(stage_timings, "candidate_selection_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             if feature_flags.get("compatibility_filtering", True):
#                 compatibility_result = self.compatibility_service.evaluate(
#                     normalized_products,
#                     requirements,
#                     target_profile,
#                 )
#             else:
#                 compatibility_result = self._compatibility_bypass(normalized_products)
#             self._mark_stage(stage_timings, "compatibility_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             policy_result = self.policy_service.apply_filters(
#                 compatibility_result.get("eligible_products") or [],
#                 requirements,
#                 target_profile,
#             )
#             rankable_products = policy_result.get("eligible_products") or []
#             self._mark_stage(stage_timings, "policy_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             recommendations = self.ranking_service.rank_products(
#                 rankable_products,
#                 requirements,
#                 target_profile,
#             )
#             self._mark_stage(stage_timings, "ranking_ms", stage_started_at)

#             stage_started_at = perf_counter()
#             if not defer_explanations:
#                 recommendations = self.explanation_service.enrich_recommendations(
#                     requirements,
#                     target_profile,
#                     recommendations,
#                     allow_llm=feature_flags.get("explanation_llm", False),
#                 )
#             self._mark_stage(stage_timings, "explanations_ms", stage_started_at)

#             fallback_reason = str(retrieval_result.get("fallback_reason") or "")
#             if not recommendations:
#                 if compatibility_result.get("rejected_products") and not compatibility_result.get("eligible_products"):
#                     fallback_reason = "compatibility_blocked_all"
#                 elif policy_result.get("rejected_products") and not rankable_products:
#                     fallback_reason = "policy_rejected_all"
#                 elif not rankable_products:
#                     fallback_reason = fallback_reason or "no_exact_fit"

#         stage_timings = self._hydrate_stage_aliases(stage_timings)

#         debug_trace = {
#             "deferred_reason": deferred_reason,
#             "retrieval_result": retrieval_result,
#             "compatibility_result": compatibility_result,
#             "policy_result": policy_result,
#             "catalog_validation_result": catalog_validation_result,
#             "raw_products": raw_products,
#             "all_normalized_products": all_normalized_products,
#             "currency_fallback_used": currency_fallback_used,
#             "catalog_source_snapshot": catalog_source_snapshot,
#             "store_scope_applied": store_scope_applied,
#             "rankable_products": rankable_products,
#             "prepared_catalog_cache_key": getattr(prepared_catalog_state, "cache_key", ""),
#         }
#         return RecommendationCoreResult(
#             ranking_deferred=bool(ranking_deferred),
#             shortlisted_product_ids=list(candidate_ids),
#             ranked_recommendations=list(recommendations),
#             fallback_reason=str(fallback_reason or ""),
#             stage_timings_ms=stage_timings,
#         ), debug_trace

#     def assemble_response(
#         self,
#         prepared_context,
#         core_result,
#         debug_trace,
#         feature_flags=None,
#         started_at=None,
#         capture_runtime_observability=True,
#     ):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         requirements = dict(prepared_context.requirements or {})
#         target_profile = dict(prepared_context.target_profile or {})
#         readiness = dict(prepared_context.readiness or {})
#         recommendations = [dict(item) for item in list(core_result.ranked_recommendations or [])]
#         stage_timings = dict(core_result.stage_timings_ms or {})
#         stage_started_at = perf_counter()
#         for recommendation in recommendations:
#             recommendation["buy_url"] = self._build_buy_url(recommendation.get("product_id"))

#         compatibility_result = dict(debug_trace.get("compatibility_result") or {})
#         policy_result = dict(debug_trace.get("policy_result") or {})
#         retrieval_result = dict(debug_trace.get("retrieval_result") or {})
#         catalog_validation_result = dict(debug_trace.get("catalog_validation_result") or {})
#         raw_products = list(debug_trace.get("raw_products") or [])
#         all_normalized_products = list(debug_trace.get("all_normalized_products") or [])
#         currency_fallback_used = bool(debug_trace.get("currency_fallback_used"))
#         catalog_source_snapshot = dict(debug_trace.get("catalog_source_snapshot") or {})
#         store_scope_applied = bool(debug_trace.get("store_scope_applied"))
#         deferred_reason = str(debug_trace.get("deferred_reason") or "")
#         rankable_products = list(debug_trace.get("rankable_products") or [])

#         summary = (
#             target_profile.get("summary")
#             if core_result.ranking_deferred
#             else self.explanation_service.build_summary(requirements, target_profile, recommendations)
#         )
#         budget_fit_summary = self._build_budget_fit_summary(requirements, recommendations)
#         if budget_fit_summary.get("no_exact_budget_fit"):
#             summary = self._prefix_no_exact_budget_fit_summary(summary, requirements, recommendations)
#             recommendations = []
#         expert_review_reason = self._expert_review_reason(
#             readiness,
#             core_result.ranking_deferred,
#             core_result.fallback_reason,
#             compatibility_result,
#             recommendations,
#         )
#         expert_review_reason = self._apply_template_review_reason(prepared_context.selected_template, expert_review_reason)
#         clarification_required_reasons = self._clarification_required_reasons(readiness)
#         decision_policy_profile = self.config_service.get_decision_policy_profile()
#         recommendation_mode = self._recommendation_mode(
#             readiness=readiness,
#             recommendations=recommendations,
#             fallback_reason=core_result.fallback_reason,
#             expert_review_reason=expert_review_reason,
#             clarification_required_reasons=clarification_required_reasons,
#             candidate_pool_size=len(rankable_products),
#         )
#         recommendation_mode = self._apply_template_selection_mode(prepared_context.selected_template, recommendation_mode)
#         requirements["review_state"] = self.review_support_service.enrich_review_state(
#             requirements=requirements,
#             readiness=readiness,
#             template_candidates=prepared_context.template_candidates,
#             recommendation_mode=recommendation_mode,
#         )
#         check_requirement_summary = self.review_support_service.build_check_requirement_summary(
#             requirements=requirements,
#             readiness=readiness,
#             template_candidates=prepared_context.template_candidates,
#             recommendation_mode=recommendation_mode,
#         )
#         editable_inferred_values = self.review_support_service.build_editable_inferred_values(requirements)
#         catalog_observability = self._build_catalog_observability(
#             raw_products=raw_products,
#             normalized_products=all_normalized_products,
#             catalog_validation_result=catalog_validation_result,
#             requirements=requirements,
#             currency_fallback_used=currency_fallback_used,
#             catalog_source_snapshot=catalog_source_snapshot,
#             store_scope_applied=store_scope_applied,
#         )
#         self._mark_stage(stage_timings, "response_assembly_ms", stage_started_at)
#         response = {
#             "decision_trace_id": prepared_context.decision_trace_id,
#             "requirements": requirements,
#             "field_state": requirements.get("field_state") or {},
#             "field_source": requirements.get("field_source") or {},
#             "assumption_severity": requirements.get("assumption_severity") or {},
#             "recommendation_mode": recommendation_mode,
#             "clarification_required_reasons": clarification_required_reasons,
#             "review_state": requirements.get("review_state") or {},
#             "check_requirement_summary": check_requirement_summary,
#             "editable_inferred_values": editable_inferred_values,
#             "template_candidates": prepared_context.template_candidates,
#             "target_profile": target_profile,
#             "recommendations": recommendations,
#             "summary": summary,
#             "assumptions": self.explanation_service.build_assumptions(requirements),
#             "comparison": "",
#             "extracted_schema": prepared_context.extracted_schema,
#             "readiness": readiness,
#             "compatibility_report": self._build_compatibility_report(compatibility_result),
#             "fallback_reason": core_result.fallback_reason or ("no_exact_fit" if budget_fit_summary.get("no_exact_budget_fit") else ""),
#             "expert_review_eligible": bool(expert_review_reason) and feature_flags.get("expert_review", True),
#             "meta": {
#                 "engine_version": ENGINE_VERSION,
#                 "config_versions": self.config_service.get_versions(),
#                 "config_bundle_version": self.config_service.get_bundle_version(),
#                 "feature_flags": feature_flags,
#                 "source_product_count": len(raw_products),
#                 "catalog_validation_summary": catalog_validation_result.get("summary") or {},
#                 "catalog_validation_rejections_sample": (catalog_validation_result.get("rejected_products") or [])[:5],
#                 "eligible_product_count": len(rankable_products),
#                 "recommended_count": len(recommendations),
#                 "budget_fit_summary": budget_fit_summary,
#                 "catalog_observability": catalog_observability,
#                 "filtered_categories": target_profile.get("categories") or [],
#                 "semantic_candidate_ids": list(core_result.shortlisted_product_ids or [])[:10],
#                 "semantic_candidate_count": len(list(core_result.shortlisted_product_ids or [])),
#                 "retrieval_summary": {
#                     "candidate_count": len(list(core_result.shortlisted_product_ids or [])),
#                     "fallback_reason": retrieval_result.get("fallback_reason"),
#                     "top_candidates": (retrieval_result.get("scored_candidates") or [])[:10],
#                 },
#                 "compatibility_summary": compatibility_result.get("summary") or {},
#                 "compatibility_rejections_sample": (compatibility_result.get("rejected_products") or [])[:5],
#                 "policy_summary": policy_result.get("summary") or {},
#                 "policy_rejections_sample": (policy_result.get("rejected_products") or [])[:5],
#                 "applied_rules_count": len(target_profile.get("applied_rules") or []),
#                 "ranking_deferred": core_result.ranking_deferred,
#                 "ranking_deferred_reason": deferred_reason,
#                 "expert_review_reason": expert_review_reason,
#                 "decision_policy_profile": decision_policy_profile,
#                 "stage_timings_ms": stage_timings,
#             },
#         }
#         if not readiness.get("is_ready"):
#             question_started_at = perf_counter()
#             response["next_question"] = (
#                 str(readiness.get("next_question") or "").strip()
#                 or self.clarification_service._context_aware_prompt(
#                     readiness.get("highest_priority_missing_field"),
#                     requirements,
#                 )
#             )
#             self._mark_stage(stage_timings, "question_generation_ms", question_started_at)
#         else:
#             stage_timings["question_generation_ms"] = 0.0
#         response["meta"]["decision_trace"] = self._build_decision_trace(
#             decision_trace_id=prepared_context.decision_trace_id,
#             requirements=requirements,
#             extracted_schema=prepared_context.extracted_schema,
#             target_profile=target_profile,
#             readiness=readiness,
#             retrieval_result=retrieval_result,
#             catalog_validation_result=catalog_validation_result,
#             compatibility_result=compatibility_result,
#             policy_result=policy_result,
#             recommendations=recommendations,
#             fallback_reason=core_result.fallback_reason,
#             recommendation_mode=recommendation_mode,
#             clarification_required_reasons=clarification_required_reasons,
#             expert_review_reason=expert_review_reason,
#             feature_flags=feature_flags,
#             decision_policy_profile=decision_policy_profile,
#             check_requirement_summary=check_requirement_summary,
#             editable_inferred_values=editable_inferred_values,
#             template_candidates=prepared_context.template_candidates,
#             selected_template=prepared_context.selected_template,
#         )
#         if capture_runtime_observability:
#             self._attach_runtime_observability(
#                 response=response,
#                 started_at=started_at,
#                 decision_trace_id=prepared_context.decision_trace_id,
#                 requirements=requirements,
#                 readiness=readiness,
#                 recommendation_mode=recommendation_mode,
#                 clarification_required_reasons=clarification_required_reasons,
#                 fallback_reason=core_result.fallback_reason,
#                 next_question=response.get("next_question"),
#             )
#         return response

#     def generate_narrative_enrichment(self, prepared_context, response, feature_flags=None):
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         response = dict(response or {})
#         response["comparison"] = self.explanation_service.build_comparison(
#             response.get("requirements") or prepared_context.requirements,
#             response.get("recommendations") or [],
#             allow_llm=feature_flags.get("comparison_llm", False),
#         )
#         return response

#     def _dispatch_persistence_from_outputs(self, prepared_context, response, user_id="", business_id=""):
#         persistence_payload = {
#             "raw_intake_snapshot": prepared_context.raw_intake_snapshot,
#             "requirements": response.get("requirements") or prepared_context.requirements,
#             "target_profile": response.get("target_profile") or prepared_context.target_profile,
#             "recommendations": response.get("recommendations") or [],
#             "summary": response.get("summary") or "",
#             "assumptions": response.get("assumptions") or [],
#             "meta": {
#                 **dict(response.get("meta") or {}),
#                 "raw_chat": (response.get("requirements") or {}).get("raw_chat", ""),
#                 "extracted_schema": prepared_context.extracted_schema,
#             },
#             "user_id": user_id,
#             "business_id": business_id,
#         }
#         session_id = str(uuid4())
#         response["session_id"] = session_id
#         async_persistence_enabled = str(os.getenv("PROCUREMENT_ASYNC_PERSISTENCE", "true")).strip().lower() != "false"
#         if not async_persistence_enabled:
#             session, persistence_error = self._persist_session(session_id=session_id, **persistence_payload)
#             if session is None and persistence_error:
#                 response.setdefault("meta", {})
#                 response["meta"]["persistence_warning"] = persistence_error
#             return

#         self._persistence_executor.submit(
#             self._persist_session,
#             session_id=session_id,
#             **persistence_payload,
#         )

#     def _recommend_multi_intent(
#         self,
#         payload,
#         multi_intent_result,
#         extracted_schema=None,
#         prepared_context=None,
#         feature_flags=None,
#         user_id="",
#         business_id="",
#         persist=True,
#         top_level_timings=None,
#     ):
#         payload = dict(payload or {})
#         top_level_timings = top_level_timings or self._new_top_level_timings()
#         decision_trace_id = str(uuid4())
#         started_at = self.observability_service.start_timer()
#         feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
#         if prepared_context is None:
#             prepare_started_at = perf_counter()
#             prepared_context = self.prepare_from_extracted_schema(
#                 payload=payload,
#                 extracted_schema=dict(extracted_schema or self._extract_schema(payload)),
#                 feature_flags=feature_flags,
#                 decision_trace_id=decision_trace_id,
#             )
#             self._mark_stage(top_level_timings["prepare_ms"], "total_ms", prepare_started_at)
#         extracted_schema = dict(prepared_context.extracted_schema or {})
#         raw_intake_snapshot = dict(prepared_context.raw_intake_snapshot or {})
#         requirements = dict(prepared_context.requirements or {})
#         target_profile = dict(prepared_context.target_profile or {})
#         base_readiness = dict(prepared_context.readiness or {})
#         template_candidates = self.template_service.select_candidates(
#             requirements,
#             target_profile,
#             multi_intent_result=multi_intent_result,
#         )
#         selected_template = self._selected_template(template_candidates)
#         selected_template_for_workflow = selected_template if selected_template.get("selection_allowed", True) else {}
#         multi_intent_policy = self.multi_intent_policy_service.evaluate(
#             payload=payload,
#             extracted_schema=extracted_schema,
#             requirements=requirements,
#             multi_intent_result=multi_intent_result,
#             selected_template=selected_template_for_workflow,
#         )

#         recommendation_groups = []
#         group_traces = []
#         flattened_recommendations = []
#         merged_assumptions = []
#         group_next_questions = []

#         for intent in multi_intent_result.get("intents") or []:
#             group_policy = dict((multi_intent_policy.get("groups_by_id") or {}).get(intent.get("group_id")) or {})
#             group_payload = self._apply_multi_intent_shared_context(
#                 intent.get("payload") or {},
#                 requirements,
#                 group_policy=group_policy,
#             )
#             group_prepared = self.prepare_from_extracted_schema(
#                 payload=group_payload,
#                 extracted_schema=intent.get("extracted_schema") or {},
#                 feature_flags=feature_flags,
#                 decision_trace_id=str(uuid4()),
#                 source_mode="multi_intent_group",
#                 prepared_catalog_state=prepared_context.prepared_catalog_state,
#             )
#             group_response = self._recommend_single_from_prepared(
#                 prepared_context=group_prepared,
#                 feature_flags=feature_flags,
#                 persist=False,
#                 capture_runtime_observability=False,
#             )
#             group_meta = dict(group_response.get("meta") or {})
#             group_decision_trace = group_meta.pop("decision_trace", None)
#             group_selected_template = dict(group_meta.get("selected_template") or {})
#             group_entry = {
#                 "group_id": intent.get("group_id"),
#                 "label": intent.get("label"),
#                 "intent_text": intent.get("intent_text"),
#                 "category": intent.get("category"),
#                 "workloads": intent.get("workloads") or [],
#                 "shared_constraints": group_policy.get("shared_constraints") or [],
#                 "warnings": group_policy.get("warnings") or [],
#                 "shared_budget": group_policy.get("shared_budget") or {},
#                 "decision_trace_id": group_response.get("decision_trace_id"),
#                 "requirements": group_response.get("requirements") or {},
#                 "field_state": group_response.get("field_state") or {},
#                 "field_source": group_response.get("field_source") or {},
#                 "assumption_severity": group_response.get("assumption_severity") or {},
#                 "recommendation_mode": group_response.get("recommendation_mode"),
#                 "clarification_required_reasons": group_response.get("clarification_required_reasons") or [],
#                 "check_requirement_summary": group_response.get("check_requirement_summary") or {},
#                 "editable_inferred_values": group_response.get("editable_inferred_values") or {},
#                 "selected_template": group_selected_template,
#                 "template_candidates": group_response.get("template_candidates") or [],
#                 "target_profile": group_response.get("target_profile") or {},
#                 "recommendations": group_response.get("recommendations") or [],
#                 "summary": group_response.get("summary", ""),
#                 "assumptions": group_response.get("assumptions") or [],
#                 "comparison": group_response.get("comparison", ""),
#                 "readiness": group_response.get("readiness") or {},
#                 "compatibility_report": group_response.get("compatibility_report") or {},
#                 "fallback_reason": group_response.get("fallback_reason"),
#                 "expert_review_eligible": group_response.get("expert_review_eligible", False),
#                 "next_question": group_response.get("next_question"),
#                 "meta": group_meta,
#             }
#             recommendation_groups.append(group_entry)
#             if group_decision_trace:
#                 group_traces.append(
#                     {
#                         "group_id": group_entry["group_id"],
#                         "label": group_entry["label"],
#                         "decision_trace": group_decision_trace,
#                     }
#                 )
#             if group_entry["recommendations"]:
#                 top_recommendation = dict(group_entry["recommendations"][0])
#                 top_recommendation["recommendation_group_id"] = group_entry["group_id"]
#                 top_recommendation["recommendation_group_label"] = group_entry["label"]
#                 flattened_recommendations.append(top_recommendation)
#             merged_assumptions.extend(group_entry["assumptions"])
#             if group_entry["next_question"]:
#                 group_next_questions.append(
#                     {
#                         "group_id": group_entry["group_id"],
#                         "label": group_entry["label"],
#                         "prompt": group_entry["next_question"],
#                     }
#                 )

#         bundle_result = self.bundle_service.build_bundle_result(
#             requirements=requirements,
#             recommendation_groups=recommendation_groups,
#             multi_intent_policy=multi_intent_policy,
#             selected_template=selected_template_for_workflow,
#         )
#         combined_merge_rules = list(multi_intent_policy.get("merge_rules") or []) + list(
#             bundle_result.get("merge_rules") or []
#         )
#         policy_trace = list(multi_intent_policy.get("split_rules") or []) + combined_merge_rules
#         bundle_trace = self._build_bundle_trace(bundle_result, selected_template)
#         bundle_validated = bool(bundle_result.get("bundle_validated"))
#         grouped_readiness = self._build_grouped_readiness(
#             base_readiness,
#             recommendation_groups,
#             multi_intent_policy=multi_intent_policy,
#         )
#         compatibility_report = self._build_grouped_compatibility_report(recommendation_groups)
#         fallback_reason = self._grouped_fallback_reason(recommendation_groups)
#         clarification_required_reasons = self._clarification_required_reasons(grouped_readiness)
#         expert_review_reason = self._grouped_expert_review_reason(recommendation_groups, fallback_reason)
#         if not bundle_validated and not clarification_required_reasons:
#             expert_review_reason = expert_review_reason or "bundle_validation_rejected"
#         expert_review_reason = self._apply_template_review_reason(selected_template, expert_review_reason)
#         decision_policy_profile = self.config_service.get_decision_policy_profile()
#         recommendation_mode = self._recommendation_mode(
#             readiness=grouped_readiness,
#             recommendations=flattened_recommendations,
#             fallback_reason=fallback_reason,
#             expert_review_reason=expert_review_reason,
#             clarification_required_reasons=clarification_required_reasons,
#             candidate_pool_size=sum(group["meta"].get("eligible_product_count", 0) for group in recommendation_groups),
#         )
#         recommendation_mode = self._apply_template_selection_mode(selected_template, recommendation_mode)
#         requirements["review_state"] = self.review_support_service.enrich_review_state(
#             requirements=requirements,
#             readiness=grouped_readiness,
#             template_candidates=template_candidates,
#             recommendation_mode=recommendation_mode,
#         )
#         check_requirement_summary = self.review_support_service.build_check_requirement_summary(
#             requirements=requirements,
#             readiness=grouped_readiness,
#             template_candidates=template_candidates,
#             recommendation_mode=recommendation_mode,
#         )
#         editable_inferred_values = self.review_support_service.build_editable_inferred_values(requirements)
#         template_id = bundle_trace.get("template_id")
#         template_version = bundle_trace.get("template_version")
#         response = {
#             "decision_trace_id": decision_trace_id,
#             "requirements": requirements,
#             "field_state": requirements.get("field_state") or {},
#             "field_source": requirements.get("field_source") or {},
#             "assumption_severity": requirements.get("assumption_severity") or {},
#             "recommendation_mode": recommendation_mode,
#             "clarification_required_reasons": clarification_required_reasons,
#             "review_state": requirements.get("review_state") or {},
#             "check_requirement_summary": check_requirement_summary,
#             "editable_inferred_values": editable_inferred_values,
#             "template_candidates": template_candidates,
#             "target_profile": target_profile,
#             "recommendations": flattened_recommendations,
#             "recommendation_groups": recommendation_groups,
#             "summary": self._build_release_4a_summary(
#                 recommendation_groups,
#                 multi_intent_policy=multi_intent_policy,
#                 bundle_result=bundle_result,
#             ),
#             "assumptions": self._dedupe_strings(merged_assumptions),
#             "comparison": self.explanation_service.build_comparison(
#                 requirements,
#                 flattened_recommendations,
#                 allow_llm=feature_flags.get("comparison_llm", False),
#             ),
#             "extracted_schema": extracted_schema,
#             "readiness": grouped_readiness,
#             "compatibility_report": compatibility_report,
#             "bundle_compatibility_report": bundle_result.get("bundle_compatibility_report") or {},
#             "bundle_conflict_codes": list(bundle_result.get("bundle_conflict_codes") or []),
#             "bundle_capacity_summary": bundle_result.get("bundle_capacity_summary") or {},
#             "bundle_options": list(bundle_result.get("bundle_options") or []),
#             "architecture_graph": bundle_result.get("architecture_graph") or {},
#             "template_id": template_id,
#             "template_version": template_version,
#             "fallback_reason": fallback_reason,
#             "expert_review_eligible": bool(expert_review_reason) and feature_flags.get("expert_review", True),
#             "meta": {
#                 "engine_version": ENGINE_VERSION,
#                 "config_versions": self.config_service.get_versions(),
#                 "config_bundle_version": self.config_service.get_bundle_version(),
#                 "feature_flags": feature_flags,
#                 "source_product_count": sum(group["meta"].get("source_product_count", 0) for group in recommendation_groups),
#                 "catalog_validation_summary": {
#                     "group_count": len(recommendation_groups),
#                     "rejected_count": sum(
#                         (group["meta"].get("catalog_validation_summary") or {}).get("rejected_count", 0)
#                         for group in recommendation_groups
#                     ),
#                 },
#                 "eligible_product_count": sum(group["meta"].get("eligible_product_count", 0) for group in recommendation_groups),
#                 "recommended_count": len(flattened_recommendations),
#                 "catalog_observability": self._aggregate_catalog_observability(recommendation_groups),
#                 "filtered_categories": self._dedupe_strings(
#                     [
#                         category
#                         for group in recommendation_groups
#                         for category in (group.get("target_profile", {}).get("categories") or [])
#                     ]
#                 ),
#                 "semantic_candidate_ids": self._dedupe_strings(
#                     [
#                         candidate_id
#                         for group in recommendation_groups
#                         for candidate_id in (group["meta"].get("semantic_candidate_ids") or [])
#                     ]
#                 )[:10],
#                 "semantic_candidate_count": sum(group["meta"].get("semantic_candidate_count", 0) for group in recommendation_groups),
#                 "retrieval_summary": {
#                     "candidate_count": sum(
#                         (group["meta"].get("retrieval_summary") or {}).get("candidate_count", 0)
#                         for group in recommendation_groups
#                     ),
#                     "fallback_reason": fallback_reason,
#                     "top_candidates": [
#                         {
#                             "group_id": group["group_id"],
#                             "label": group["label"],
#                             "top_candidates": (group["meta"].get("retrieval_summary") or {}).get("top_candidates") or [],
#                         }
#                         for group in recommendation_groups
#                     ],
#                 },
#                 "compatibility_summary": compatibility_report.get("summary") or {},
#                 "compatibility_rejections_sample": compatibility_report.get("rejected_products") or [],
#                 "policy_summary": {
#                     "group_count": len(recommendation_groups),
#                     "rejected_count": sum(
#                         (group["meta"].get("policy_summary") or {}).get("rejected_count", 0)
#                         for group in recommendation_groups
#                     ),
#                 },
#                 "policy_rejections_sample": [
#                     {
#                         "group_id": group["group_id"],
#                         "label": group["label"],
#                         "rejected_products": (group["meta"].get("policy_rejections_sample") or [])[:3],
#                     }
#                     for group in recommendation_groups
#                     if group["meta"].get("policy_rejections_sample")
#                 ][:5],
#                 "applied_rules_count": sum(group["meta"].get("applied_rules_count", 0) for group in recommendation_groups),
#                 "ranking_deferred": all(group["meta"].get("ranking_deferred", False) for group in recommendation_groups),
#                 "ranking_deferred_reason": (
#                     "multi_intent_group_clarification_required"
#                     if any(group["meta"].get("ranking_deferred", False) for group in recommendation_groups)
#                     else None
#                 ),
#                 "expert_review_reason": expert_review_reason,
#                 "decision_policy_profile": decision_policy_profile,
#                 "bundle_trace": bundle_trace,
#                 "multi_intent": {
#                     "is_multi_intent": True,
#                     "is_grouped": True,
#                     "bundle_validated": bundle_validated,
#                     "policy_version": multi_intent_policy.get("policy_version"),
#                     "split_source": multi_intent_result.get("split_source"),
#                     "shared_budget_reused": multi_intent_result.get("shared_budget_reused", False),
#                     "shared_constraints": multi_intent_policy.get("shared_constraints") or [],
#                     "shared_budget": multi_intent_policy.get("shared_budget") or {},
#                     "warnings": multi_intent_policy.get("warnings") or [],
#                     "split_rules": multi_intent_policy.get("split_rules") or [],
#                     "merge_rules": combined_merge_rules,
#                     "policy_trace": policy_trace,
#                     "bundle_conflict_codes": list(bundle_result.get("bundle_conflict_codes") or []),
#                     "validation_outcome": bundle_trace.get("validation_outcome"),
#                     "template_id": template_id,
#                     "template_version": template_version,
#                     "group_count": len(recommendation_groups),
#                     "group_labels": [group["label"] for group in recommendation_groups],
#                     "group_decision_trace_ids": [
#                         group.get("decision_trace_id")
#                         for group in recommendation_groups
#                         if group.get("decision_trace_id")
#                     ],
#                     "group_next_questions": group_next_questions,
#                     "group_templates": self._build_group_template_summary(recommendation_groups),
#                 },
#             },
#         }
#         if grouped_readiness.get("next_question"):
#             response["next_question"] = grouped_readiness.get("next_question")
#         elif group_next_questions:
#             response["next_question"] = group_next_questions[0]["prompt"]

#         response["meta"]["decision_trace"] = {
#             "decision_trace_id": decision_trace_id,
            
#             "compatibility": {
#                 "scope": compatibility_report.get("scope") or "item",
#                 "summary": compatibility_report.get("summary") or {},
#                 "rejected_products": compatibility_report.get("rejected_products") or [],
#             },
#             "bundle_validation": bundle_trace,
#             "expert_review_reason": expert_review_reason,
#             "feature_flags": feature_flags,
#             "config_versions": self.config_service.get_versions(),
         
#             "multi_intent": {
#                 "is_multi_intent": True,
#                 "policy_version": multi_intent_policy.get("policy_version"),
#                 "split_source": multi_intent_result.get("split_source"),
#                 "shared_budget_reused": multi_intent_result.get("shared_budget_reused", False),
#                 "bundle_validated": bundle_validated,
#                 "shared_constraints": multi_intent_policy.get("shared_constraints") or [],
#                 "shared_budget": multi_intent_policy.get("shared_budget") or {},
#                 "warnings": multi_intent_policy.get("warnings") or [],
#                 "split_rules": multi_intent_policy.get("split_rules") or [],
#                 "merge_rules": combined_merge_rules,
#                 "policy_trace": policy_trace,
#                 "bundle_conflict_codes": list(bundle_result.get("bundle_conflict_codes") or []),
#                 "validation_outcome": bundle_trace.get("validation_outcome"),
#                 "template_id": template_id,
#                 "template_version": template_version,
#                 "groups": group_traces,
#                 "group_templates": self._build_group_template_summary(recommendation_groups),
#             },
#         }
#         self._attach_runtime_observability(
#             response=response,
#             started_at=started_at,
#             decision_trace_id=decision_trace_id,
#             requirements=requirements,
#             readiness=grouped_readiness,
#             recommendation_mode=recommendation_mode,
#             clarification_required_reasons=clarification_required_reasons,
#             fallback_reason=fallback_reason,
#             next_question=response.get("next_question"),
#         )

#         if persist:
#             self._dispatch_persistence_from_outputs(
#                 prepared_context=prepared_context,
#                 response={
#                     **response,
#                     "recommendations": flattened_recommendations,
#                     "target_profile": target_profile,
#                     "assumptions": response["assumptions"],
#                     "meta": {
#                         **response["meta"],
#                         "recommendation_groups": recommendation_groups,
#                     },
#                 },
#                 user_id=user_id,
#                 business_id=business_id,
#             )

#         return response

#     def _attach_runtime_observability(
#         self,
#         response,
#         started_at,
#         decision_trace_id,
#         requirements,
#         readiness,
#         recommendation_mode,
#         clarification_required_reasons,
#         fallback_reason,
#         next_question=None,
#     ):
#         response = dict(response or {})
#         runtime_observability = self.observability_service.build_runtime_observability(
#             started_at=started_at,
#             decision_trace_id=decision_trace_id,
#             requirements=requirements,
#             readiness=readiness,
#             recommendation_mode=recommendation_mode,
#             clarification_required_reasons=clarification_required_reasons,
#             fallback_reason=fallback_reason,
#             next_question=next_question,
#             response_payload=response,
#         )
#         response.setdefault("meta", {})
#         response["meta"]["runtime_observability"] = runtime_observability
#         decision_trace = response["meta"].get("decision_trace")
#         if isinstance(decision_trace, dict):
#             pass
#         return response

#     def _apply_multi_intent_shared_context(self, payload, requirements, group_policy=None):
#         payload = dict(payload or {})
#         requirements = dict(requirements or {})
#         group_policy = dict(group_policy or {})
#         explicit_payload_fields = list(payload.get("_explicit_payload_fields") or [])
#         field_source_hints = dict(payload.get("_field_source_hints") or {})
#         shared_constraints = set(group_policy.get("shared_constraints") or [])

#         if (
#             requirements.get("budget_scope")
#             and "budget_scope" in shared_constraints
#             and not payload.get("budget_scope")
#         ):
#             payload["budget_scope"] = requirements.get("budget_scope")
#             field_source_hints.setdefault("budget_scope", "context_explicit")

#         if explicit_payload_fields:
#             payload["_explicit_payload_fields"] = explicit_payload_fields
#         if field_source_hints:
#             payload["_field_source_hints"] = field_source_hints
#         return payload

#     def _normalize_products(self, raw_products, requested_currency, allowed_categories=None, currency_fallback_used=False):
#         normalized_products = []
#         seen_ids = set()
#         allowed_categories = set(allowed_categories or [])
#         for product in raw_products:
#             inventory_offers = list(product.get("inventory_offers") or [])
#             if not inventory_offers:
#                 inventory = product.get("inventory")
#                 inventory_offers = [inventory] if inventory else [None]

#             for inventory in inventory_offers:
#                 candidate = dict(product)
#                 candidate.pop("inventory_offers", None)
#                 if inventory:
#                     candidate["inventory"] = inventory
#                 else:
#                     candidate.pop("inventory", None)
#                 normalized = normalize_product_document(candidate, requested_currency=requested_currency)
#                 product_id = normalized.get("id")
#                 if product_id in seen_ids:
#                     continue
#                 seen_ids.add(product_id)
#                 normalized["offer_count"] = len(inventory_offers)
#                 normalized["alternate_offer_count"] = max(len(inventory_offers) - 1, 0)
#                 normalized["currency_fallback_used"] = bool(
#                     currency_fallback_used
#                     and requested_currency
#                     and str(normalized.get("currency") or "").strip().upper()
#                     != str(requested_currency or "").strip().upper()
#                 )
#                 normalized_products.append(normalized)
#         return normalized_products

#     def _filter_normalized_products(self, normalized_products, allowed_categories=None, candidate_ids=None):
#         normalized_products = list(normalized_products or [])
#         category_filter_enabled = bool(allowed_categories)
#         candidate_filter_enabled = candidate_ids is not None
#         allowed_categories = set(allowed_categories or [])
#         candidate_ids = set(candidate_ids or [])
#         if not category_filter_enabled and not candidate_filter_enabled:
#             return normalized_products
#         filtered = []
#         for product in normalized_products:
#             if category_filter_enabled and product.get("category") not in allowed_categories:
#                 continue
#             if candidate_filter_enabled and product.get("id") not in candidate_ids:
#                 continue
#             filtered.append(product)
#         return filtered

#     def _build_grouped_readiness(self, base_readiness, recommendation_groups, multi_intent_policy=None):
#         base_readiness = dict(base_readiness or {})
#         multi_intent_policy = dict(multi_intent_policy or {})
#         readiness_items = [dict(group.get("readiness") or {}) for group in recommendation_groups]
#         if not readiness_items:
#             return base_readiness

#         confidence_rank = {"low": 0, "medium": 1, "high": 2}
#         band_rank = {"low": 0, "medium": 1, "high": 2}
#         question_candidates = []
#         missing_signals = []
#         for group in recommendation_groups:
#             readiness = dict(group.get("readiness") or {})
#             for signal in readiness.get("missing_signals") or []:
#                 if signal not in missing_signals:
#                     missing_signals.append(signal)
#             for candidate in readiness.get("question_candidates") or []:
#                 candidate_copy = dict(candidate)
#                 candidate_copy["group_id"] = group.get("group_id")
#                 candidate_copy["group_label"] = group.get("label")
#                 question_candidates.append(candidate_copy)

#         shared_budget = dict(multi_intent_policy.get("shared_budget") or {})
#         if shared_budget.get("allocation_required"):
#             missing_signals.append(shared_budget.get("clarification_key"))
#             question_candidates.append(
#                 {
#                     "key": shared_budget.get("clarification_key"),
#                     "prompt": shared_budget.get("clarification_prompt"),
#                     "rationale": shared_budget.get("clarification_rationale"),
#                     "impact": 0.98,
#                 }
#             )

#         question_candidates.sort(key=lambda item: item.get("impact", 0), reverse=True)
#         top_question = question_candidates[0] if question_candidates else None
#         threshold = self.clarification_service.question_impact_threshold()
#         should_ask_top_question = bool(top_question and float(top_question.get("impact", 0.0)) >= threshold)
#         grouped_confidence = min(
#             (item.get("confidence") or "medium" for item in readiness_items),
#             key=lambda value: confidence_rank.get(value, 1),
#         )
#         grouped_band = min(
#             (item.get("decision_confidence_band") or "medium" for item in readiness_items),
#             key=lambda value: band_rank.get(value, 1),
#         )
#         grouped_score = round(
#             sum(item.get("decision_confidence_score", 0.0) for item in readiness_items) / len(readiness_items),
#             4,
#         )

#         return {
#             **base_readiness,
#             "is_ready": all(bool(item.get("is_ready")) for item in readiness_items),
#             "confidence": grouped_confidence,
#             "missing_signals": missing_signals,
#             "highest_priority_missing_field": top_question.get("key") if top_question else None,
#             "next_question": top_question.get("prompt") if should_ask_top_question else None,
#             "follow_up_questions": question_candidates[:3],
#             "decision_confidence_score": grouped_score,
#             "decision_confidence_band": grouped_band,
#             "recommended_question_budget": 1 if should_ask_top_question else 0,
#             "routing_recommendation": (
#                 "clarify_before_ranking"
#                 if not all(bool(item.get("is_ready")) for item in readiness_items)
#                 else "recommend_with_one_refinement"
#                 if should_ask_top_question
#                 else base_readiness.get("routing_recommendation", "recommend_now")
#             ),
#             "recommended_refinement_question": top_question.get("prompt") if should_ask_top_question else None,
#             "question_strategy": (
#                 "grouped_single_question"
#                 if should_ask_top_question
#                 else base_readiness.get("question_strategy", "proceed")
#             ),
#             "question_candidates": question_candidates[:3],
#         }

#     def _build_grouped_compatibility_report(self, recommendation_groups):
#         group_reports = []
#         rejected_products = []
#         eligible_count = 0
#         rejected_count = 0
#         for group in recommendation_groups:
#             report = dict(group.get("compatibility_report") or {})
#             report_summary = dict(report.get("summary") or {})
#             eligible_count += report_summary.get("eligible_count", 0)
#             rejected_count += report_summary.get("rejected_count", 0)
#             group_rejections = list(report.get("rejected_products") or [])
#             rejected_products.extend(group_rejections[:3])
#             group_reports.append(
#                 {
#                     "group_id": group.get("group_id"),
#                     "label": group.get("label"),
#                     "scope": report.get("scope") or "item",
#                     "summary": report_summary,
#                     "rejected_products": group_rejections[:3],
#                 }
#             )

#         return {
#             "scope": "item",
#             "summary": {
#                 "compatibility_scope": "item",
#                 "grouped": True,
#                 "group_count": len(recommendation_groups),
#                 "eligible_count": eligible_count,
#                 "rejected_count": rejected_count,
#             },
#             "rejected_products": rejected_products[:5],
#             "groups": group_reports,
#         }

#     def _build_grouped_summary(self, recommendation_groups, multi_intent_policy=None):
#         multi_intent_policy = dict(multi_intent_policy or {})
#         if not recommendation_groups:
#             return "No grouped recommendations were generated."

#         parts = []
#         for group in recommendation_groups:
#             recommendations = list(group.get("recommendations") or [])
#             label = group.get("label") or group.get("group_id") or "Intent"
#             if recommendations:
#                 top_name = recommendations[0].get("name") or "Recommendation ready"
#                 parts.append(f"{label}: {top_name}")
#             elif group.get("next_question"):
#                 parts.append(f"{label}: clarification needed")
#             else:
#                 parts.append(f"{label}: no exact fit")
#         summary = "Grouped recommendations prepared for {} intents. {}".format(
#             len(recommendation_groups),
#             " | ".join(parts),
#         )
#         shared_budget = dict(multi_intent_policy.get("shared_budget") or {})
#         if shared_budget.get("allocation_required"):
#             summary += " Shared project budget allocation still needs confirmation before the groups can be treated as budget-valid together."
#         return summary

#     def _build_release_4a_summary(self, recommendation_groups, multi_intent_policy=None, bundle_result=None):
#         bundle_result = dict(bundle_result or {})
#         grouped_summary = self._build_grouped_summary(
#             recommendation_groups,
#             multi_intent_policy=multi_intent_policy,
#         )
#         bundle_summary = str(bundle_result.get("summary") or "").strip()
#         if bundle_result.get("bundle_validated"):
#             return bundle_summary or grouped_summary
#         if not bundle_summary:
#             return grouped_summary
#         if recommendation_groups and any(group.get("recommendations") for group in recommendation_groups):
#             return (
#                 bundle_summary
#                 + " Constrained per-role recommendations remain available while the bundle is not yet valid."
#             )
#         return bundle_summary

#     def _build_bundle_trace(self, bundle_result, selected_template=None):
#         bundle_result = dict(bundle_result or {})
#         selected_template = dict(selected_template or {})
#         bundle_candidate = dict(bundle_result.get("bundle_candidate") or {})
#         bundle_report = dict(bundle_result.get("bundle_compatibility_report") or {})
#         return {
#             "template_id": bundle_candidate.get("template_id") or selected_template.get("template_id"),
#             "template_version": bundle_candidate.get("template_version") or selected_template.get("template_version"),
#             "bundle_validated": bool(bundle_result.get("bundle_validated")),
#             "validation_outcome": "passed" if bundle_result.get("bundle_validated") else "rejected",
#             "bundle_candidate": bundle_candidate,
#             "bundle_compatibility_report": bundle_report,
#             "bundle_conflict_codes": list(bundle_result.get("bundle_conflict_codes") or []),
#             "bundle_capacity_summary": bundle_result.get("bundle_capacity_summary") or {},
#             "bundle_options": list(bundle_result.get("bundle_options") or []),
#             "architecture_graph": bundle_result.get("architecture_graph") or {},
#             "merge_rules": list(bundle_result.get("merge_rules") or []),
#         }

#     def _build_group_template_summary(self, recommendation_groups):
#         summary = []
#         for group in list(recommendation_groups or []):
#             selected_template = dict(group.get("selected_template") or {})
#             template_candidates = list(group.get("template_candidates") or [])
#             if not selected_template and template_candidates:
#                 selected_template = self._selected_template(template_candidates)
#             summary.append(
#                 {
#                     "group_id": group.get("group_id"),
#                     "label": group.get("label"),
#                     "category": group.get("category"),
#                     "template_id": selected_template.get("template_id"),
#                     "template_version": selected_template.get("template_version"),
#                     "template_match_quality": selected_template.get("template_match_quality"),
#                     "required_roles": list(selected_template.get("required_roles") or []),
#                     "quantity_strategy": selected_template.get("quantity_strategy"),
#                     "budget_strategy": selected_template.get("budget_strategy"),
#                     "selection_allowed": bool(selected_template.get("selection_allowed", True))
#                     if selected_template
#                     else False,
#                 }
#             )
#         return summary

#     def _grouped_fallback_reason(self, recommendation_groups):
#         if not recommendation_groups:
#             return "no_exact_fit"
#         fallback_reasons = [
#             group.get("fallback_reason")
#             for group in recommendation_groups
#             if group.get("fallback_reason")
#         ]
#         if not fallback_reasons:
#             return ""
#         if len(fallback_reasons) == len(recommendation_groups):
#             return fallback_reasons[0] if len(set(fallback_reasons)) == 1 else "multi_intent_partial_fallback"
#         return "multi_intent_partial_fallback"

#     def _grouped_expert_review_reason(self, recommendation_groups, fallback_reason):
#         if any(group.get("expert_review_eligible") for group in recommendation_groups):
#             return "multi_intent_group_requires_review"
#         if fallback_reason in {"compatibility_blocked_all", "policy_rejected_all", "no_exact_fit", "multi_intent_partial_fallback"}:
#             return fallback_reason
#         return ""

#     def _selected_template(self, template_candidates):
#         template_candidates = list(template_candidates or [])
#         if not template_candidates:
#             return {}
#         selected = dict(template_candidates[0])
#         return {
#             "template_id": selected.get("template_id"),
#             "template_version": selected.get("template_version"),
#             "scenario_family": selected.get("scenario_family"),
#             "variant": selected.get("variant"),
#             "template_match_quality": selected.get("template_match_quality"),
#             "match_score": selected.get("match_score"),
#             "selection_allowed": bool(selected.get("selection_allowed", True)),
#             "selection_rejection_reason": selected.get("selection_rejection_reason") or "",
#             "matched_template_signals": selected.get("matched_template_signals") or {},
#             "coverage_gap_reasons": list(selected.get("coverage_gap_reasons") or []),
#             "gap_type": selected.get("gap_type") or "",
#             "hard_gate_failures": list(selected.get("hard_gate_failures") or []),
#             "contradiction_codes": list(selected.get("contradiction_codes") or []),
#             "soft_fit_gaps": list(selected.get("soft_fit_gaps") or []),
#             "template_selection_debug": dict(selected.get("template_selection_debug") or {}),
#             "required_roles": list(selected.get("required_roles") or []),
#             "quantity_strategy": selected.get("quantity_strategy"),
#             "budget_strategy": selected.get("budget_strategy"),
#             "compatibility_profile": selected.get("compatibility_profile"),
#             "scoring_profile": selected.get("scoring_profile"),
#             "urgency_profile": selected.get("urgency_profile"),
#             "site_scope_profile": selected.get("site_scope_profile"),
#             "rollout_type": selected.get("rollout_type"),
#             "replacement_mode": selected.get("replacement_mode"),
#             "support_preference": selected.get("support_preference"),
#             "existing_infra_dependency": selected.get("existing_infra_dependency"),
#             "acceptable_downgrade_path": selected.get("acceptable_downgrade_path"),
#         }

#     def _apply_template_review_reason(self, selected_template, expert_review_reason):
#         selected_template = dict(selected_template or {})
#         expert_review_reason = str(expert_review_reason or "").strip()
#         template_quality = str(selected_template.get("template_match_quality") or "").strip().lower()
#         if template_quality == "coverage_gap":
#             return expert_review_reason or "template_coverage_gap"
#         return expert_review_reason

#     def _apply_template_selection_mode(self, selected_template, recommendation_mode):
#         selected_template = dict(selected_template or {})
#         template_quality = str(selected_template.get("template_match_quality") or "").strip().lower()
#         if template_quality == "coverage_gap":
#             return "expert_review_recommended"
#         if template_quality == "closest_match" and recommendation_mode == "firm_recommendation":
#             return "provisional_recommendation"
#         return recommendation_mode

#     def _dedupe_strings(self, values):
#         deduped = []
#         seen = set()
#         for value in list(values or []):
#             normalized = str(value or "").strip()
#             if not normalized:
#                 continue
#             lowered = normalized.lower()
#             if lowered in seen:
#                 continue
#             seen.add(lowered)
#             deduped.append(normalized)
#         return deduped

#     def _persist_session(
#         self,
#         raw_intake_snapshot,
#         requirements,
#         target_profile,
#         recommendations,
#         summary,
#         assumptions,
#         meta,
#         user_id="",
#         business_id="",
#         session_id=None,
#     ):
#         try:
#             from ..models import ProcurementSession

#             session = ProcurementSession.objects.create(
#                 session_id=str(session_id or uuid4()),
#                 user_id=str(user_id or ""),
#                 business_id=str(business_id or ""),
#                 store_id=requirements.get("store_id", ""),
#                 channel=requirements.get("channel", "api"),
#                 currency=requirements.get("currency", ""),
#                 raw_intake_snapshot=dict(raw_intake_snapshot or {}),
#                 requirements=requirements,
#                 target_profile=target_profile,
#                 recommendations=recommendations,
#                 summary=summary,
#                 assumptions=assumptions,
#                 meta=meta,
#                 engine_version=ENGINE_VERSION,
#             )
#             return session, None
#         except Exception as exc:
#             return None, str(exc)

#     def _build_raw_intake_snapshot(self, payload):
#         snapshot = {}
#         for key, value in dict(payload or {}).items():
#             if str(key).startswith("_") or key == "persist":
#                 continue
#             snapshot[key] = value
#         return snapshot

#     def _build_buy_url(self, product_id, store_id=""):
#         if not product_id:
#             return ""

#         base_url = os.getenv("SHOP_PRODUCT_BASE_URL", "https://dev.techpay.ai/shop/#/products").rstrip("/")
#         return f"{base_url}/{product_id}"

#     def _resolve_prepared_catalog_state(self, requirements):
#         requirements = dict(requirements or {})
#         cache_key = self._prepared_catalog_state_cache_key(requirements)
#         cached = self._prepared_catalog_state_cache.get(cache_key)
#         if cached is not None:
#             return cached

#         raw_products = self.catalog_repository.fetch_products(
#             store_id="",
#             currency=requirements.get("currency", ""),
#         )
#         currency_fallback_used = False
#         if not raw_products and requirements.get("currency"):
#             raw_products = self.catalog_repository.fetch_products(store_id="", currency="")
#             currency_fallback_used = bool(raw_products)
#         catalog_source_snapshot = self._catalog_source_snapshot()
#         normalized_products = self._normalize_products(
#             raw_products,
#             requirements.get("currency"),
#             allowed_categories=None,
#             currency_fallback_used=currency_fallback_used,
#         )
#         catalog_validation_result = self._screen_catalog_metadata(normalized_products)
#         eligible_products = list(catalog_validation_result.get("eligible_products") or [])
#         category_subsets = self._build_category_indexed_subsets(eligible_products)
#         retrieval_assets_by_subset = {
#             "__all__": self._resolve_precomputed_retrieval_assets(
#                 eligible_products,
#                 subset_key="__all__",
#                 cache_key=cache_key,
#             ),
#         }
#         for category_key, subset in category_subsets.items():
#             retrieval_assets_by_subset[category_key] = self._resolve_precomputed_retrieval_assets(
#                 subset,
#                 subset_key=category_key,
#                 cache_key=cache_key,
#             )

#         prepared = PreparedCatalogState(
#             cache_key=cache_key,
#             raw_products=tuple(raw_products),
#             normalized_products=tuple(normalized_products),
#             eligible_products=tuple(eligible_products),
#             catalog_validation_result=dict(catalog_validation_result or {}),
#             category_subsets={key: tuple(value) for key, value in category_subsets.items()},
#             retrieval_assets_by_subset=retrieval_assets_by_subset,
#             currency_fallback_used=bool(currency_fallback_used),
#             catalog_source_snapshot=dict(catalog_source_snapshot or {}),
#             store_scope_applied=False,
#         )
#         self._prepared_catalog_state_cache[cache_key] = prepared
#         return prepared

#     def _resolve_precomputed_retrieval_assets(self, normalized_products, subset_key="__all__", cache_key=""):
#         getter = getattr(self.catalog_repository, "get_precomputed_retrieval_assets", None)
#         if callable(getter):
#             try:
#                 assets = getter(
#                     subset_key=subset_key,
#                     cache_key=cache_key,
#                     normalized_products=list(normalized_products or []),
#                 )
#             except TypeError:
#                 assets = getter(subset_key, cache_key)
#             except Exception:
#                 assets = None
#             if assets:
#                 return assets
#         return self.semantic_retriever.build_retrieval_assets(
#             normalized_products,
#             include_semantic=False,
#         )

#     def _prepared_catalog_state_cache_key(self, requirements):
#         requirements = dict(requirements or {})
#         currency = str(requirements.get("currency") or "").strip().upper()
#         store_id = str(requirements.get("store_id") or "").strip().lower()
#         source_snapshot = self._catalog_source_snapshot()
#         source_name = str(source_snapshot.get("source_name") or getattr(self.catalog_repository, "source_name", "")).strip()
#         source_path = str(source_snapshot.get("source_path") or "").strip()
#         source_success = bool(source_snapshot.get("source_load_success", True))
#         catalog_version = str(source_snapshot.get("catalog_version") or "").strip()
#         return "|".join(
#             [
#                 source_name,
#                 source_path,
#                 catalog_version,
#                 str(source_success).lower(),
#                 currency,
#                 store_id,
#             ]
#         )

#     def _build_category_indexed_subsets(self, eligible_products):
#         subsets = {}
#         for product in list(eligible_products or []):
#             category = str(product.get("category") or "").strip().lower()
#             if not category:
#                 continue
#             subsets.setdefault(category, []).append(product)
#         return subsets

#     def _resolve_category_subset_from_state(self, prepared_catalog_state, categories):
#         prepared_catalog_state = prepared_catalog_state or PreparedCatalogState(
#             cache_key="",
#             raw_products=tuple(),
#             normalized_products=tuple(),
#             eligible_products=tuple(),
#             catalog_validation_result={},
#             category_subsets={},
#             retrieval_assets_by_subset={},
#             currency_fallback_used=False,
#             catalog_source_snapshot={},
#         )
#         categories = [str(value or "").strip().lower() for value in list(categories or []) if str(value or "").strip()]
#         if not categories:
#             return list(prepared_catalog_state.eligible_products or []), "__all__"
#         subset = []
#         for category in categories:
#             subset.extend(list((prepared_catalog_state.category_subsets or {}).get(category) or []))
#         if not subset:
#             return [], "__all__"
#         seen = set()
#         deduped = []
#         for product in subset:
#             product_id = product.get("id")
#             if not product_id or product_id in seen:
#                 continue
#             seen.add(product_id)
#             deduped.append(product)
#         subset_key = "__".join(sorted(categories))
#         return deduped, subset_key

#     def _extract_schema(self, payload):
#         chat_text = str(payload.get("chat_text") or payload.get("raw_chat") or "").strip()
#         extraction_context = payload.get("extracted_schema") or {}
#         if extraction_context and extraction_context.get("intake_confidence") is not None:
#             context_schema = dict(extraction_context)
#             if chat_text and not context_schema.get("raw_chat"):
#                 context_schema["raw_chat"] = chat_text
#             return dict(self.extraction_service.extract("", context=context_schema))
#         if chat_text:
#             return dict(self.extraction_service.extract(chat_text, context=extraction_context))

#         fallback_schema = {
#             "raw_chat": chat_text,
#             "company_size": None,
#             "industry": payload.get("industry"),
#             "business_type": payload.get("business_type"),
#             "team_size": payload.get("team_size"),
#             "workload_types": payload.get("workload_types") or payload.get("workloads") or [],
#             "application_signals": payload.get("application_signals") or [],
#             "capability_tags": payload.get("capability_tags") or [],
#             "budget": payload.get("budget"),
#             "growth_expectation": payload.get("growth_expectation"),
#             "existing_infrastructure": payload.get("existing_infrastructure") or [],
#             "preferred_manufacturers": payload.get("preferred_manufacturers") or [],
#             "blocked_manufacturers": payload.get("blocked_manufacturers") or [],
#             "preferred_sellers": payload.get("preferred_sellers") or [],
#             "blocked_sellers": payload.get("blocked_sellers") or [],
#             "preferred_category": payload.get("preferred_category") or payload.get("category"),
#             "performance_priority": payload.get("performance_priority"),
#             "portability_need": payload.get("portability_need"),
#             "support_expectation": payload.get("support_expectation"),
#             "availability_need": payload.get("availability_need"),
#             "require_returnable": payload.get("require_returnable"),
#             "quantity": payload.get("quantity"),
#             "purchase_scope": payload.get("purchase_scope"),
#             "timeline": payload.get("timeline"),
#             "requested_ram": payload.get("requested_ram"),
#             "requested_storage": payload.get("requested_storage"),
#             "requested_ram_is_minimum": payload.get("requested_ram_is_minimum"),
#             "requested_storage_is_minimum": payload.get("requested_storage_is_minimum"),
#             "notes": payload.get("notes", ""),
#             "missing_fields": [],
#             "intake_confidence": 1.0,
#         }
#         return dict(self.extraction_service.extract("", context=fallback_schema))

#     def _build_compatibility_report(self, compatibility_result):
#         compatibility_result = compatibility_result or {}
#         summary = compatibility_result.get("summary") or {}
#         return {
#             "scope": summary.get("compatibility_scope") or "item",
#             "summary": summary,
#             "rejected_products": (compatibility_result.get("rejected_products") or [])[:5],
#         }

#     def _deterministic_candidate_pool(self, normalized_products, top_k=40):
#         candidates = []
#         for product in list(normalized_products or [])[:top_k]:
#             product_id = product.get("id")
#             if not product_id:
#                 continue
#             candidates.append(
#                 {
#                     "product_id": product_id,
#                     "base_product_id": product.get("base_product_id") or product_id,
#                     "manufacturer": str(product.get("manufacturer") or "").strip().lower(),
#                     "candidate_score": 1.0,
#                     "semantic_norm": 0.0,
#                     "lexical_norm": 0.0,
#                     "business_boost": 1.0,
#                 }
#             )
#         return {
#             "candidate_ids": [item["product_id"] for item in candidates],
#             "scored_candidates": candidates,
#             "fallback_reason": "semantic_retrieval_disabled",
#         }

#     def _screen_catalog_metadata(self, normalized_products):
#         eligible_products = []
#         rejected_products = []
#         for product in list(normalized_products or []):
#             metadata_validation = dict(product.get("metadata_validation") or {})
#             category = product.get("category")
#             missing_required_fields = list(metadata_validation.get("missing_required_fields") or [])
#             readiness_state = str(
#                 product.get("readiness_state") or metadata_validation.get("readiness_state") or ""
#             ).strip()
#             if readiness_state == "insufficient":
#                 rejected_products.append(
#                     {
#                         "product_id": product.get("id"),
#                         "name": product.get("name"),
#                         "category": category,
#                         "manufacturer": product.get("manufacturer"),
#                         "reasons": list(metadata_validation.get("parse_warnings") or [])
#                         or ["Missing required metadata: " + ", ".join(missing_required_fields)],
#                         "readiness_state": readiness_state,
#                         "missing_required_fields": missing_required_fields,
#                         "missing_critical_fields": list(metadata_validation.get("missing_critical_fields") or []),
#                     }
#                 )
#                 continue
#             eligible_products.append(product)
#         return {
#             "eligible_products": eligible_products,
#             "rejected_products": rejected_products,
#             "summary": {
#                 "input_count": len(list(normalized_products or [])),
#                 "eligible_count": len(eligible_products),
#                 "rejected_count": len(rejected_products),
#             },
#         }

#     def _catalog_source_snapshot(self):
#         getter = getattr(self.catalog_repository, "get_observability_snapshot", None)
#         if callable(getter):
#             try:
#                 snapshot = dict(getter() or {})
#             except Exception:
#                 snapshot = {}
#         else:
#             snapshot = {}
#         if snapshot:
#             return snapshot
#         return {
#             "source_name": getattr(self.catalog_repository, "source_name", self.catalog_repository.__class__.__name__),
#             "source_load_success": True,
#             "unmatched_inventory_count": 0,
#         }

#     def _build_catalog_observability(
#         self,
#         raw_products,
#         normalized_products,
#         catalog_validation_result,
#         requirements,
#         currency_fallback_used=False,
#         catalog_source_snapshot=None,
#         store_scope_applied=False,
#     ):
#         raw_products = list(raw_products or [])
#         normalized_products = list(normalized_products or [])
#         catalog_validation_result = dict(catalog_validation_result or {})
#         requirements = dict(requirements or {})
#         catalog_source_snapshot = dict(catalog_source_snapshot or {})
#         readiness_state_counts = {}
#         parse_warning_count = 0
#         provisional_count = 0
#         for product in normalized_products:
#             readiness_state = str(product.get("readiness_state") or "unknown").strip() or "unknown"
#             readiness_state_counts[readiness_state] = readiness_state_counts.get(readiness_state, 0) + 1
#             parse_warning_count += len(product.get("parse_warnings") or [])
#             if readiness_state == "provisional":
#                 provisional_count += 1
#         return {
#             "source_name": catalog_source_snapshot.get("source_name")
#             or getattr(self.catalog_repository, "source_name", self.catalog_repository.__class__.__name__),
#             "source_load_success": bool(catalog_source_snapshot.get("source_load_success", True)),
#             "source_path": catalog_source_snapshot.get("source_path"),
#             "requested_store_id": str(requirements.get("store_id") or ""),
#             "applied_store_id": str(catalog_source_snapshot.get("requested_store_id") or ""),
#             "store_scope_applied": bool(store_scope_applied),
#             "requested_currency": str(requirements.get("currency") or ""),
#             "matched_product_count": int(catalog_source_snapshot.get("matched_product_count") or len(raw_products)),
#             "normalized_candidate_count": len(normalized_products),
#             "unmatched_inventory_count": int(catalog_source_snapshot.get("unmatched_inventory_count") or 0),
#             "readiness_state_counts": readiness_state_counts,
#             "parse_warning_count": parse_warning_count,
#             "currency_fallback_count": 1 if currency_fallback_used else 0,
#             "currency_fallback_used": bool(currency_fallback_used),
#             "provisional_count": provisional_count,
#             "store_filter_miss": bool(
#                 store_scope_applied
#                 and (
#                     catalog_source_snapshot.get("store_filter_miss")
#                     or (requirements.get("store_id") and not raw_products)
#                 )
#             ),
#             "validation_block_count": len(catalog_validation_result.get("rejected_products") or []),
#         }

#     def _aggregate_catalog_observability(self, recommendation_groups):
#         recommendation_groups = list(recommendation_groups or [])
#         readiness_state_counts = {}
#         source_names = []
#         source_paths = []
#         total_unmatched_inventory = 0
#         total_normalized_candidate_count = 0
#         total_parse_warning_count = 0
#         total_currency_fallback_count = 0
#         total_provisional_count = 0
#         total_validation_block_count = 0
#         any_store_filter_miss = False
#         any_store_scope_applied = False
#         all_load_success = True
#         for group in recommendation_groups:
#             group_observability = dict((group.get("meta") or {}).get("catalog_observability") or {})
#             if not group_observability:
#                 continue
#             source_name = group_observability.get("source_name")
#             source_path = group_observability.get("source_path")
#             if source_name and source_name not in source_names:
#                 source_names.append(source_name)
#             if source_path and source_path not in source_paths:
#                 source_paths.append(source_path)
#             for readiness_state, count in dict(group_observability.get("readiness_state_counts") or {}).items():
#                 readiness_state_counts[readiness_state] = readiness_state_counts.get(readiness_state, 0) + int(count or 0)
#             total_unmatched_inventory += int(group_observability.get("unmatched_inventory_count") or 0)
#             total_normalized_candidate_count += int(group_observability.get("normalized_candidate_count") or 0)
#             total_parse_warning_count += int(group_observability.get("parse_warning_count") or 0)
#             total_currency_fallback_count += int(group_observability.get("currency_fallback_count") or 0)
#             total_provisional_count += int(group_observability.get("provisional_count") or 0)
#             total_validation_block_count += int(group_observability.get("validation_block_count") or 0)
#             any_store_filter_miss = any_store_filter_miss or bool(group_observability.get("store_filter_miss"))
#             any_store_scope_applied = any_store_scope_applied or bool(group_observability.get("store_scope_applied"))
#             all_load_success = all_load_success and bool(group_observability.get("source_load_success", True))
#         return {
#             "source_names": source_names,
#             "source_paths": source_paths,
#             "source_load_success": all_load_success,
#             "unmatched_inventory_count": total_unmatched_inventory,
#             "normalized_candidate_count": total_normalized_candidate_count,
#             "readiness_state_counts": readiness_state_counts,
#             "parse_warning_count": total_parse_warning_count,
#             "currency_fallback_count": total_currency_fallback_count,
#             "currency_fallback_used": bool(total_currency_fallback_count),
#             "provisional_count": total_provisional_count,
#             "store_scope_applied": any_store_scope_applied,
#             "store_filter_miss": any_store_filter_miss,
#             "validation_block_count": total_validation_block_count,
#         }

#     def _compatibility_bypass(self, normalized_products):
#         products = list(normalized_products or [])
#         return {
#             "eligible_products": products,
#             "rejected_products": [],
#             "reports_by_product_id": {},
#             "summary": {
#                 "compatibility_scope": "item",
#                 "evaluated_count": len(products),
#                 "eligible_count": len(products),
#                 "rejected_count": 0,
#                 "skipped_by_flag": True,
#             },
#         }

#     def _expert_review_reason(self, readiness, ranking_deferred, fallback_reason, compatibility_result, recommendations):
#         if ranking_deferred:
#             return "low_confidence_clarification_required"
#         if fallback_reason in {"compatibility_blocked_all", "policy_rejected_all", "no_exact_fit"}:
#             return fallback_reason
#         if (readiness or {}).get("decision_confidence_band") == "low":
#             return "low_confidence_routing"
#         if compatibility_result.get("rejected_products") and not recommendations:
#             return "hard_conflict_detected"
#         return ""

#     def _clarification_required_reasons(self, readiness):
#         readiness = dict(readiness or {})
#         question_candidates = list(readiness.get("question_candidates") or [])
#         threshold = self.clarification_service.question_impact_threshold()
#         reasons = [
#             str(item.get("key") or "").strip()
#             for item in question_candidates
#             if str(item.get("key") or "").strip() and float(item.get("impact") or 0.0) >= threshold
#         ]
#         if reasons:
#             return self._dedupe_strings(reasons)

#         critical_missing = [
#             signal
#             for signal in list(readiness.get("missing_signals") or [])
#             if signal in self._hard_critical_signals()
#         ]
#         if critical_missing:
#             return self._dedupe_strings(critical_missing)
#         return []

#     def _recommendation_mode(
#         self,
#         readiness,
#         recommendations,
#         fallback_reason,
#         expert_review_reason,
#         clarification_required_reasons,
#         candidate_pool_size=0,
#     ):
#         readiness = dict(readiness or {})
#         recommendations = list(recommendations or [])
#         clarification_required_reasons = list(clarification_required_reasons or [])
#         mode_policy = self.config_service.get_recommendation_mode_policy()
#         expert_review_fallback_reasons = set(mode_policy.get("expert_review_fallback_reasons") or [])
#         minimum_safe_candidate_count = int(mode_policy.get("minimum_safe_candidate_count") or 0)
#         max_hard_critical_for_clarification = int(
#             mode_policy.get("max_hard_critical_reasons_for_clarification") or 0
#         )
#         max_hard_critical_for_provisional = int(
#             mode_policy.get("max_hard_critical_reasons_for_provisional") or 0
#         )
#         hard_critical_reasons = self._hard_critical_reasons(readiness, clarification_required_reasons)
#         ranking_deferred = self.clarification_service.should_defer_ranking(readiness)
#         insufficient_candidates = minimum_safe_candidate_count > 0 and int(candidate_pool_size or 0) < minimum_safe_candidate_count

#         if not recommendations:
#             if fallback_reason in expert_review_fallback_reasons:
#                 return "expert_review_recommended"
#             if insufficient_candidates:
#                 return "expert_review_recommended"
#             if ranking_deferred:
#                 return (
#                     "clarification_required"
#                     if clarification_required_reasons and len(hard_critical_reasons) <= max_hard_critical_for_clarification
#                     else "expert_review_recommended"
#                 )
#             if expert_review_reason:
#                 return "expert_review_recommended"
#             return (
#                 "clarification_required"
#                 if clarification_required_reasons and len(hard_critical_reasons) <= max_hard_critical_for_clarification
#                 else "expert_review_recommended"
#             )

#         if clarification_required_reasons:
#             if insufficient_candidates:
#                 return "expert_review_recommended"
#             if len(hard_critical_reasons) > max_hard_critical_for_provisional:
#                 return "expert_review_recommended"
#             return "provisional_recommendation"
#         if expert_review_reason or insufficient_candidates:
#             return "expert_review_recommended"
#         return "firm_recommendation"

#     def _build_decision_trace(
#         self,
#         decision_trace_id,
#         requirements,
#         extracted_schema,
#         target_profile,
#         readiness,
#         retrieval_result,
#         catalog_validation_result,
#         compatibility_result,
#         policy_result,
#         recommendations,
#         fallback_reason,
#         recommendation_mode,
#         clarification_required_reasons,
#         expert_review_reason,
#         feature_flags,
#         decision_policy_profile,
#         check_requirement_summary,
#         editable_inferred_values,
#         template_candidates,
#         selected_template,
#     ):
#         return {
#             "decision_trace_id": decision_trace_id,
            
#             "catalog_validation": {
#                 "summary": catalog_validation_result.get("summary") or {},
#                 "rejected_products": catalog_validation_result.get("rejected_products") or [],
#             },
#             "retrieval": retrieval_result,
#             "compatibility": {
#                 "scope": (compatibility_result.get("summary") or {}).get("compatibility_scope") or "item",
#                 "summary": compatibility_result.get("summary") or {},
#                 "rejected_products": compatibility_result.get("rejected_products") or [],
#             },
#             "policy": {
#                 "summary": policy_result.get("summary") or {},
#                 "rejected_products": policy_result.get("rejected_products") or [],
#             },
#             "expert_review_reason": expert_review_reason,
#             "feature_flags": feature_flags,
#             "config_versions": self.config_service.get_versions(),
#         }

#     def _hard_critical_signals(self):
#         signals = self.config_service.get_recommendation_mode_policy().get("hard_critical_signals") or []
#         return set(self._dedupe_strings(signals))

#     def _hard_critical_reasons(self, readiness, clarification_required_reasons):
#         hard_critical_signals = self._hard_critical_signals()
#         return self._dedupe_strings(
#             [
#                 reason
#                 for reason in (clarification_required_reasons or []) + list((readiness or {}).get("missing_signals") or [])
#                 if reason in hard_critical_signals
#             ]
#         )






import os
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from uuid import uuid4

from ...catalog.services.normalization import normalize_product_document
from ...catalog.services.repository import build_runtime_catalog_repository
from ...catalog.services.semantic_retriever import SemanticProductRetriever

from .explanations import ProcurementExplanationService
from .feature_flags import ProcurementFeatureFlagService
from .followup_generation import AdaptiveFollowUpService
from .intake import RequirementIntakeService
from .observability import ProcurementRuntimeObservabilityService
from .policy import ProcurementPolicyService
from .ranking import ProductRankingService
from .recommendation_context import (
    PreparedCatalogState,
    PreparedProcurementContext,
    RecommendationContextBuilder,
    RecommendationCoreResult,
)
from .recommendation_core import RecommendationCoreEngine
from .recommendation_presenter import RecommendationPresenter
from .review_support import ProcurementReviewSupportService
from .requirement_extraction import RequirementExtractionService
from .rules_engine import ProcurementRulesEngine
from .clarification import ProcurementClarificationService
from .bundle_service import ProcurementBundleService
from .compatibility import ProcurementCompatibilityService
from .config_service import ProcurementConfigService
from .multi_intent import ProcurementMultiIntentService
from .multi_intent_policy import ProcurementMultiIntentPolicyService
from .template_service import ProcurementTemplateService


ENGINE_VERSION = "phase1-v8"

class ProcurementRecommendationService:
    _persistence_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="procurement-persist")

    def __init__(
        self,
        catalog_repository=None,
        config_service=None,
        intake_service=None,
        rules_engine=None,
        ranking_service=None,
        policy_service=None,
        compatibility_service=None,
        explanation_service=None,
        clarification_service=None,
        extraction_service=None,
        semantic_retriever=None,
        followup_service=None,
        feature_flag_service=None,
        multi_intent_service=None,
        multi_intent_policy_service=None,
        observability_service=None,
        bundle_service=None,
        template_service=None,
        review_support_service=None,
    ):
        self.catalog_repository = catalog_repository or build_runtime_catalog_repository()
        self.config_service = config_service or ProcurementConfigService()
        self.intake_service = intake_service or RequirementIntakeService()
        self.rules_engine = rules_engine or ProcurementRulesEngine(config_service=self.config_service)
        self.ranking_service = ranking_service or ProductRankingService(config_service=self.config_service)
        self.policy_service = policy_service or ProcurementPolicyService(config_service=self.config_service)
        self.compatibility_service = compatibility_service or ProcurementCompatibilityService(config_service=self.config_service)
        self.explanation_service = explanation_service or ProcurementExplanationService(config_service=self.config_service)
        self.clarification_service = clarification_service or ProcurementClarificationService(config_service=self.config_service)
        self.extraction_service = extraction_service or RequirementExtractionService()
        self.semantic_retriever = semantic_retriever or SemanticProductRetriever()
        self.followup_service = followup_service or AdaptiveFollowUpService()
        self.feature_flag_service = feature_flag_service or ProcurementFeatureFlagService()
        self.multi_intent_service = multi_intent_service or ProcurementMultiIntentService(
            extraction_service=self.extraction_service
        )
        self.multi_intent_policy_service = multi_intent_policy_service or ProcurementMultiIntentPolicyService()
        self.observability_service = observability_service or ProcurementRuntimeObservabilityService(
            config_service=self.config_service
        )
        self.bundle_service = bundle_service or ProcurementBundleService(
            compatibility_service=self.compatibility_service
        )
        self.template_service = template_service or ProcurementTemplateService(config_service=self.config_service)
        self.review_support_service = review_support_service or ProcurementReviewSupportService()
        self._prepared_catalog_state_cache = {}
        self.context_builder = RecommendationContextBuilder(self)
        self.core_engine = RecommendationCoreEngine(self)
        self.presenter = RecommendationPresenter(self)

    def has_minimum_context(self, payload):
        requirements = self.intake_service.normalize(payload)
        readiness = self.clarification_service.assess(requirements)
        return bool(requirements.get("budget") is not None and not self.clarification_service.should_defer_ranking(readiness))

    def _new_top_level_timings(self, source_mode=""):
        prepare_ms = {"total_ms": 0.0}
        if source_mode:
            prepare_ms["source_mode"] = str(source_mode)
        return {
            "prepare_ms": prepare_ms,
            "core_ms": {
                "total_ms": 0.0,
                "multi_intent_detect_ms": 0.0,
                "catalog_fetch_ms": 0.0,
                "compatibility_ms": 0.0,
                "policy_ms": 0.0,
                "ranking_ms": 0.0,
                "explanations_ms": 0.0,
                "response_assembly_ms": 0.0,
            },
            "presentation_ms": {
                "assembly_ms": 0.0,
                "question_generation_ms": 0.0,
                "narrative_ms": 0.0,
                "persistence_dispatch_ms": 0.0,
                "total_ms": 0.0,
            },
            "pipeline_ms": {"total_ms": 0.0},
        }

    def _finalize_top_level_timings(self, top_level_timings, pipeline_started_at=None, response=None):
        top_level_timings = dict(top_level_timings or {})
        core_ms = dict(top_level_timings.get("core_ms") or {})
        presentation_ms = dict(top_level_timings.get("presentation_ms") or {})
        stage_timings = dict((((response or {}).get("meta") or {}).get("stage_timings_ms") or {}))
        core_ms["catalog_fetch_ms"] = round(float(stage_timings.get("catalog_fetch_ms") or core_ms.get("catalog_fetch_ms") or 0.0), 2)
        core_ms["compatibility_ms"] = round(float(stage_timings.get("compatibility_ms") or core_ms.get("compatibility_ms") or 0.0), 2)
        core_ms["policy_ms"] = round(float(stage_timings.get("policy_ms") or core_ms.get("policy_ms") or 0.0), 2)
        core_ms["ranking_ms"] = round(float(stage_timings.get("ranking_ms") or core_ms.get("ranking_ms") or 0.0), 2)
        core_ms["explanations_ms"] = round(float(stage_timings.get("explanations_ms") or core_ms.get("explanations_ms") or 0.0), 2)
        core_ms["response_assembly_ms"] = round(
            float(stage_timings.get("response_assembly_ms") or core_ms.get("response_assembly_ms") or 0.0),
            2,
        )
        top_level_timings["core_ms"] = core_ms
        question_generation_ms = float(stage_timings.get("question_generation_ms") or presentation_ms.get("question_generation_ms") or 0.0)
        presentation_ms["question_generation_ms"] = round(question_generation_ms, 2)
        presentation_ms["total_ms"] = round(
            sum(
                float(presentation_ms.get(key) or 0.0)
                for key in ("assembly_ms", "question_generation_ms", "narrative_ms", "persistence_dispatch_ms")
            ),
            2,
        )
        top_level_timings["presentation_ms"] = presentation_ms
        if pipeline_started_at is not None:
            self._mark_stage(top_level_timings.setdefault("pipeline_ms", {}), "total_ms", pipeline_started_at)
        return top_level_timings

    def recommend(self, payload, user_id="", business_id="", persist=True):
        payload = dict(payload or {})
        feature_flags = dict(self.feature_flag_service.get_flags())
        if str(payload.get("channel") or "").strip().lower() == "websocket":
            persist = False
        pipeline_started_at = perf_counter()
        top_level_timings = self._new_top_level_timings()

        prepare_started_at = perf_counter()
        prepared = self.prepare_from_raw_payload(payload, feature_flags=feature_flags)
        self._mark_stage(top_level_timings["prepare_ms"], "total_ms", prepare_started_at)

        detect_started_at = perf_counter()
        multi_intent_result = self.multi_intent_service.detect(payload, prepared.extracted_schema)
        self._mark_stage(top_level_timings["core_ms"], "multi_intent_detect_ms", detect_started_at)
        if multi_intent_result.get("is_multi_intent"):
            response = self._recommend_multi_intent(
                payload=payload,
                multi_intent_result=multi_intent_result,
                extracted_schema=prepared.extracted_schema,
                feature_flags=feature_flags,
                user_id=user_id,
                business_id=business_id,
                persist=persist,
                prepared_context=prepared,
                top_level_timings=top_level_timings,
            )
        else:
            response = self._recommend_single(
                payload=payload,
                extracted_schema=prepared.extracted_schema,
                prepared_context=prepared,
                feature_flags=feature_flags,
                user_id=user_id,
                business_id=business_id,
                persist=persist,
                top_level_timings=top_level_timings,
            )
        top_level_timings = self._finalize_top_level_timings(
            top_level_timings,
            pipeline_started_at=pipeline_started_at,
            response=response,
        )
        response.setdefault("meta", {})
        response["meta"]["top_level_timings_ms"] = top_level_timings
        return response

    def prepare_from_raw_payload(self, payload, feature_flags=None, decision_trace_id=None):
        return self.context_builder.prepare_from_raw_payload(
            payload=payload,
            feature_flags=feature_flags,
            decision_trace_id=decision_trace_id,
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
        return self.context_builder.prepare_from_extracted_schema(
            payload=payload,
            extracted_schema=extracted_schema,
            feature_flags=feature_flags,
            decision_trace_id=decision_trace_id,
            source_mode=source_mode,
            prepared_catalog_state=prepared_catalog_state,
        )

    def recommend_prepared_context(
        self,
        prepared_context,
        feature_flags=None,
        user_id="",
        business_id="",
        persist=True,
        capture_runtime_observability=True,
    ):
        feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
        pipeline_started_at = perf_counter()
        top_level_timings = self._new_top_level_timings(source_mode=prepared_context.source_mode)
        if str(prepared_context.channel or "").strip().lower() == "websocket":
            persist = False
        detect_started_at = perf_counter()
        multi_intent_result = self.core_engine.detect_multi_intent(
            prepared_context.normalized_payload,
            prepared_context.extracted_schema,
        )
        self._mark_stage(top_level_timings["core_ms"], "multi_intent_detect_ms", detect_started_at)
        if multi_intent_result.get("is_multi_intent"):
            response = self._recommend_multi_intent(
                payload=prepared_context.normalized_payload,
                multi_intent_result=multi_intent_result,
                extracted_schema=prepared_context.extracted_schema,
                prepared_context=prepared_context,
                feature_flags=feature_flags,
                user_id=user_id,
                business_id=business_id,
                persist=persist,
                top_level_timings=top_level_timings,
            )
        else:
            response = self._recommend_single_from_prepared(
                prepared_context=prepared_context,
                feature_flags=feature_flags,
                user_id=user_id,
                business_id=business_id,
                persist=persist,
                capture_runtime_observability=capture_runtime_observability,
                top_level_timings=top_level_timings,
            )
        top_level_timings = self._finalize_top_level_timings(
            top_level_timings,
            pipeline_started_at=pipeline_started_at,
            response=response,
        )
        response.setdefault("meta", {})
        response["meta"]["top_level_timings_ms"] = top_level_timings
        return response

    def recommend_from_chat_preferences(self, chat_preferences, store_id="", persist=False):
        chat_preferences = dict(chat_preferences or {})
        payload = {
            "store_id": chat_preferences.get("store_id") or store_id or "",
            "channel": "websocket",
            "currency": chat_preferences.get("currency", "INR"),
            "category": chat_preferences.get("category") or chat_preferences.get("preferred_category"),
            "industry": chat_preferences.get("industry"),
            "business_type": chat_preferences.get("business_type"),
            "team_size": chat_preferences.get("team_size"),
            "workload_types": chat_preferences.get("workloads") or chat_preferences.get("workload_types"),
            "application_signals": chat_preferences.get("application_signals") or [],
            "capability_tags": chat_preferences.get("capability_tags") or [],
            "budget": chat_preferences.get("budget"),
            "budget_scope": chat_preferences.get("budget_scope"),
            "growth_expectation": chat_preferences.get("growth_expectation"),
            "existing_infrastructure": chat_preferences.get("existing_infrastructure") or [],
            "preferred_manufacturers": chat_preferences.get("preferred_manufacturers") or [],
            "blocked_manufacturers": chat_preferences.get("blocked_manufacturers") or [],
            "preferred_sellers": chat_preferences.get("preferred_sellers") or [],
            "blocked_sellers": chat_preferences.get("blocked_sellers") or [],
            "requested_ram": (
                chat_preferences.get("requested_ram")
                or chat_preferences.get("requested_ram_gb")
                or chat_preferences.get("specifications.ram_size")
            ),
            "requested_storage": (
                chat_preferences.get("requested_storage")
                or chat_preferences.get("requested_storage_gb")
                or chat_preferences.get("specifications.storage_size")
            ),
            "requested_ram_is_minimum": chat_preferences.get("requested_ram_is_minimum"),
            "requested_storage_is_minimum": chat_preferences.get("requested_storage_is_minimum"),
            "minimum_warranty_years": chat_preferences.get("minimum_warranty_years"),
            "required_port_count": chat_preferences.get("required_port_count"),
            "required_throughput_mbps": chat_preferences.get("required_throughput_mbps"),
            "required_duplex_printing": chat_preferences.get("required_duplex_printing"),
            "required_scanner": chat_preferences.get("required_scanner"),
            "min_print_speed_ppm": chat_preferences.get("min_print_speed_ppm"),
            "required_printer_type": chat_preferences.get("required_printer_type"),
            "required_print_technology": chat_preferences.get("required_print_technology"),
            "required_color_output": chat_preferences.get("required_color_output"),
            "min_monthly_duty_cycle_pages": chat_preferences.get("min_monthly_duty_cycle_pages"),
            "required_automatic_document_feeder": chat_preferences.get("required_automatic_document_feeder"),
            "required_paper_sizes": chat_preferences.get("required_paper_sizes"),
            "required_network_roles": chat_preferences.get("required_network_roles"),
            "required_vpn_user_capacity": chat_preferences.get("required_vpn_user_capacity"),
            "required_virtualization_ready": chat_preferences.get("required_virtualization_ready"),
            "required_virtualization_platforms": chat_preferences.get("required_virtualization_platforms"),
            "max_rack_units": chat_preferences.get("max_rack_units"),
            "max_power_draw_watts": chat_preferences.get("max_power_draw_watts"),
            "battery_life_hours_min": chat_preferences.get("battery_life_hours_min"),
            "cpu_preference": chat_preferences.get("cpu_preference"),
            "gpu_requirement": chat_preferences.get("gpu_requirement"),
            "screen_size_preference": chat_preferences.get("screen_size_preference"),
            "weight_kg_max": chat_preferences.get("weight_kg_max"),
            "warranty_type_preference": chat_preferences.get("warranty_type_preference"),
            "performance_priority": chat_preferences.get("performance_priority"),
            "portability_need": chat_preferences.get("portability_need"),
            "support_expectation": chat_preferences.get("support_expectation"),
            "availability_need": chat_preferences.get("availability_need"),
            "require_returnable": chat_preferences.get("require_returnable"),
            "quantity": chat_preferences.get("quantity"),
            "purchase_scope": chat_preferences.get("purchase_scope"),
            "timeline": chat_preferences.get("timeline"),
            "raw_chat": chat_preferences.get("raw_chat", ""),
            "notes": chat_preferences.get("notes", ""),
            "extracted_schema": dict(chat_preferences),
        }
        prepared_context = self.prepare_from_extracted_schema(
            payload=payload,
            extracted_schema=dict(chat_preferences),
            source_mode="chat_preferences",
        )
        return self.recommend_prepared_context(prepared_context, persist=persist)

    def _recommend_single(
        self,
        payload,
        extracted_schema=None,
        prepared_context=None,
        feature_flags=None,
        user_id="",
        business_id="",
        persist=True,
        decision_trace_id=None,
        capture_runtime_observability=True,
        top_level_timings=None,
    ):
        feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
        payload = dict(payload or {})
        top_level_timings = top_level_timings or self._new_top_level_timings()
        if prepared_context is None:
            prepare_started_at = perf_counter()
            prepared_context = self.prepare_from_extracted_schema(
                payload=payload,
                extracted_schema=dict(extracted_schema or self._extract_schema(payload)),
                feature_flags=feature_flags,
                decision_trace_id=decision_trace_id,
            )
            self._mark_stage(top_level_timings["prepare_ms"], "total_ms", prepare_started_at)
        return self._recommend_single_from_prepared(
            prepared_context=prepared_context,
            feature_flags=feature_flags,
            user_id=user_id,
            business_id=business_id,
            persist=persist,
            capture_runtime_observability=capture_runtime_observability,
            top_level_timings=top_level_timings,
        )

    def _recommend_single_from_prepared(
        self,
        prepared_context,
        feature_flags=None,
        user_id="",
        business_id="",
        persist=True,
        capture_runtime_observability=True,
        top_level_timings=None,
    ):
        feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
        top_level_timings = top_level_timings or self._new_top_level_timings()
        started_at = self.observability_service.start_timer() if capture_runtime_observability else None
        core_started_at = perf_counter()
        core_result, debug_trace = self.core_engine.run(
            prepared_context,
            feature_flags=feature_flags,
            defer_explanations=bool(prepared_context.normalized_payload.get("_defer_explanations")),
        )
        self._mark_stage(top_level_timings["core_ms"], "total_ms", core_started_at)
        assembly_started_at = perf_counter()
        response = self.presenter.assemble(
            prepared_context=prepared_context,
            core_result=core_result,
            debug_trace=debug_trace,
            feature_flags=feature_flags,
            started_at=started_at,
            capture_runtime_observability=capture_runtime_observability,
        )
        self._mark_stage(top_level_timings["presentation_ms"], "assembly_ms", assembly_started_at)
        question_generation_ms = float(
            (((response.get("meta") or {}).get("stage_timings_ms") or {}).get("question_generation_ms"))
            or 0.0
        )
        top_level_timings["presentation_ms"]["question_generation_ms"] = round(question_generation_ms, 2)
        if question_generation_ms:
            top_level_timings["presentation_ms"]["assembly_ms"] = max(
                round(float(top_level_timings["presentation_ms"]["assembly_ms"]) - question_generation_ms, 2),
                0.0,
            )
        narrative_started_at = perf_counter()
        response = self.presenter.enrich(
            prepared_context=prepared_context,
            response=response,
            feature_flags=feature_flags,
        )
        self._mark_stage(top_level_timings["presentation_ms"], "narrative_ms", narrative_started_at)
        persistence_started_at = perf_counter()
        if persist:
            self._dispatch_persistence_from_outputs(
                prepared_context=prepared_context,
                response=response,
                user_id=user_id,
                business_id=business_id,
            )
        self._mark_stage(top_level_timings["presentation_ms"], "persistence_dispatch_ms", persistence_started_at)
        top_level_timings["presentation_ms"]["total_ms"] = round(
            sum(
                float(top_level_timings["presentation_ms"].get(key) or 0.0)
                for key in ("assembly_ms", "question_generation_ms", "narrative_ms", "persistence_dispatch_ms")
            ),
            2,
        )
        return response

    def recommend_from_state(
        self,
        state: dict,
        user_id="",
        business_id="",
        persist=False,
    ):
        raw_state = dict(state or {})
        requirements = dict(raw_state.get("requirements") or raw_state)
        conversation_meta = dict(raw_state.get("conversation_meta") or {})

        for field in ("intent_groups", "preferred_categories", "preferred_category", "budget", "budget_scope", "team_size", "quantity"):
            value = raw_state.get(field)
            if value not in (None, "", [], {}) and requirements.get(field) in (None, "", [], {}):
                requirements[field] = value

        if requirements.get("raw_chat") in (None, ""):
            brief = str(conversation_meta.get("conversation_brief") or "").strip()
            if brief:
                requirements["raw_chat"] = brief

        payload = dict(requirements)
        payload.setdefault("channel", "websocket")
        payload.setdefault("_defer_explanations", False)
        prepared_context = self.prepare_from_extracted_schema(
            payload=payload,
            extracted_schema=requirements,
            source_mode="planner_state",
        )
        return self.recommend_prepared_context(
            prepared_context,
            user_id=user_id,
            business_id=business_id,
            persist=persist,
        )

    def _build_budget_fit_summary(self, requirements, recommendations):
        budget = requirements.get("budget")
        if budget is None:
            return {
                "budget_present": False,
                "within_budget_count": 0,
                "over_budget_count": 0,
                "no_exact_budget_fit": False,
            }
        quantity = requirements.get("quantity") or requirements.get("team_size") or 1
        budget_scope = requirements.get("budget_scope")
        within_budget_count = 0
        over_budget_count = 0
        for recommendation in list(recommendations or []):
            price = recommendation.get("price")
            total_cost = recommendation.get("estimated_total_cost")
            reference = self.ranking_service._budget_reference(price, budget_scope, quantity, total_cost)
            if reference is None:
                continue
            if reference <= budget:
                within_budget_count += 1
            else:
                over_budget_count += 1
        return {
            "budget_present": True,
            "within_budget_count": within_budget_count,
            "over_budget_count": over_budget_count,
            "no_exact_budget_fit": bool(recommendations) and within_budget_count == 0,
        }

    def _prefix_no_exact_budget_fit_summary(self, summary, requirements, recommendations):
        if not recommendations:
            return str(summary or "").strip()
        currency = str(requirements.get("currency") or "INR").strip() or "INR"
        budget = requirements.get("budget")
        quantity = requirements.get("quantity") or requirements.get("team_size") or 1
        budget_scope = str(requirements.get("budget_scope") or "").replace("_", " ").strip()
        if not budget_scope and int(quantity or 1) > 1:
            base = (
                f"No exact fit could be validated against the stated budget of {budget} {currency} because the budget scope is ambiguous for {quantity} units. "
                "Showing the closest stretch options until you confirm whether the budget is per unit or project total."
            )
        else:
            budget_scope = budget_scope or "budget"
            base = f"No exact in-catalog fit was found within the stated {budget_scope} budget of {budget} {currency}. Showing the closest stretch options and their trade-offs."
        summary = str(summary or "").strip()
        if not summary:
            return base
        if summary.lower().startswith("no exact in-catalog fit") or summary.lower().startswith("no exact fit could be validated"):
            return summary
        return f"{base} {summary}".strip()

    def _annotate_no_exact_budget_fit_recommendations(self, requirements, recommendations):
        requirements = dict(requirements or {})
        currency = str(requirements.get("currency") or "INR").strip() or "INR"
        budget = requirements.get("budget")
        quantity = requirements.get("quantity") or requirements.get("team_size") or 1
        budget_scope = requirements.get("budget_scope")
        annotated = []
        for recommendation in list(recommendations or []):
            item = dict(recommendation or {})
            price = item.get("price")
            total_cost = item.get("estimated_total_cost")
            reference = self.ranking_service._budget_reference(price, budget_scope, quantity, total_cost)
            note = ""
            if reference is None:
                if int(quantity or 1) > 1 and not budget_scope:
                    note = (
                        f"Budget scope is ambiguous for {quantity} units; this is shown as a closest option until you confirm whether {budget} {currency} is per unit or project total."
                    )
            elif budget is not None and reference > budget:
                scope_label = str(budget_scope or ("project_total" if int(quantity or 1) > 1 else "budget")).replace("_", " ")
                note = f"Exceeds the stated {scope_label} budget of {budget} {currency}; shown as a closest stretch option."
            if note:
                reasons = list(item.get("reasons") or [])
                if note not in reasons:
                    reasons.insert(0, note)
                item["reasons"] = reasons
                item["fit_status"] = "stretch"
            annotated.append(item)
        return annotated

    def _build_no_match_summary(self, requirements, reason_code=""):
        requirements = dict(requirements or {})
        categories = [str(c or "").strip() for c in list(requirements.get("preferred_categories") or []) if str(c or "").strip()]
        category_text = ", ".join(categories) if categories else "the requested category"
        currency = str(requirements.get("currency") or "INR").strip() or "INR"
        budget = requirements.get("budget")
        if str(reason_code or "").strip() == "no_exact_budget_fit" and budget is not None:
            return f"No exact match was found for {category_text} within the stated budget of {budget} {currency}."
        return f"No exact match was found for {category_text} with the current requirements."

    def _build_no_match_prompt(self, requirements, reason_code=""):
        requirements = dict(requirements or {})
        budget = requirements.get("budget")
        if str(reason_code or "").strip() == "no_exact_budget_fit" and budget is not None:
            return "I could not find an exact match within the current budget. Do you want to raise the budget, change the category, or relax the requirements?"
        return "I could not find an exact match for the current requirements. Do you want to relax the requirements, change the category, or adjust the budget?"

    def _mark_stage(self, stage_timings, stage_name, started_at):
        stage_timings[stage_name] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)

    def _set_stage_total(self, stage_timings, stage_name, values):
        values = [float(value or 0.0) for value in list(values or [])]
        stage_timings[stage_name] = round(sum(values), 2)

    def _hydrate_stage_aliases(self, stage_timings):
        stage_timings = dict(stage_timings or {})
        self._set_stage_total(
            stage_timings,
            "catalog_fetch_ms",
            [
                stage_timings.get("catalog_state_access_ms"),
                stage_timings.get("category_subset_resolution_ms"),
                stage_timings.get("candidate_selection_ms"),
            ],
        )
        self._set_stage_total(
            stage_timings,
            "compatibility_policy_ms",
            [
                stage_timings.get("compatibility_ms"),
                stage_timings.get("policy_ms"),
            ],
        )
        return stage_timings

    def run_recommendation_core(self, prepared_context, feature_flags=None, defer_explanations=False):
        feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
        requirements = dict(prepared_context.requirements or {})
        target_profile = dict(prepared_context.target_profile or {})
        readiness = dict(prepared_context.readiness or {})
        prepared_catalog_state = prepared_context.prepared_catalog_state or self._resolve_prepared_catalog_state(requirements)
        stage_timings = {}
        ranking_deferred = self.clarification_service.should_defer_ranking(readiness)
        deferred_reason = ""
        normalized_products = []
        candidate_ids = []
        retrieval_result = {"candidate_ids": [], "scored_candidates": [], "fallback_reason": None}
        compatibility_result = {"eligible_products": [], "rejected_products": [], "summary": {}, "reports_by_product_id": {}}
        policy_result = {"eligible_products": [], "rejected_products": [], "summary": {}}
        rankable_products = []
        recommendations = []
        fallback_reason = ""
        catalog_validation_result = {"eligible_products": [], "rejected_products": [], "summary": {}}
        raw_products = []
        all_normalized_products = []
        currency_fallback_used = False
        catalog_source_snapshot = {}
        store_scope_applied = False

        if ranking_deferred:
            deferred_reason = "blocking_clarification_required"
            fallback_reason = deferred_reason
        else:
            stage_started_at = perf_counter()
            raw_products = list(prepared_catalog_state.raw_products or [])
            all_normalized_products = list(prepared_catalog_state.normalized_products or [])
            catalog_validation_result = dict(prepared_catalog_state.catalog_validation_result or {})
            currency_fallback_used = bool(prepared_catalog_state.currency_fallback_used)
            catalog_source_snapshot = dict(prepared_catalog_state.catalog_source_snapshot or {})
            store_scope_applied = bool(prepared_catalog_state.store_scope_applied)
            self._mark_stage(stage_timings, "catalog_state_access_ms", stage_started_at)

            stage_started_at = perf_counter()
            category_filtered_products, subset_key = self._resolve_category_subset_from_state(
                prepared_catalog_state,
                target_profile.get("categories"),
            )
            self._mark_stage(stage_timings, "category_subset_resolution_ms", stage_started_at)

            stage_started_at = perf_counter()
            if feature_flags.get("semantic_retrieval", True):
                retrieval_assets = (prepared_catalog_state.retrieval_assets_by_subset or {}).get(subset_key)
                if retrieval_assets is None and subset_key != "__all__":
                    retrieval_assets = self.semantic_retriever.build_retrieval_assets(category_filtered_products)
                retrieval_result = self.semantic_retriever.retrieve_candidates_from_assets(
                    retrieval_assets,
                    requirements,
                    target_profile,
                    top_k=40,
                    allow_broadening=feature_flags.get("retrieval_broadening", True),
                )
                candidate_ids = list(retrieval_result.get("candidate_ids") or [])
                normalized_products = self._filter_normalized_products(
                    category_filtered_products,
                    None,
                    candidate_ids,
                )
            else:
                retrieval_result = self._deterministic_candidate_pool(category_filtered_products, top_k=40)
                candidate_ids = list(retrieval_result.get("candidate_ids") or [])
                normalized_products = category_filtered_products[:40]
            self._mark_stage(stage_timings, "candidate_selection_ms", stage_started_at)

            stage_started_at = perf_counter()
            if feature_flags.get("compatibility_filtering", True):
                compatibility_result = self.compatibility_service.evaluate(
                    normalized_products,
                    requirements,
                    target_profile,
                )
            else:
                compatibility_result = self._compatibility_bypass(normalized_products)
            self._mark_stage(stage_timings, "compatibility_ms", stage_started_at)

            stage_started_at = perf_counter()
            policy_result = self.policy_service.apply_filters(
                compatibility_result.get("eligible_products") or [],
                requirements,
                target_profile,
            )
            rankable_products = policy_result.get("eligible_products") or []
            self._mark_stage(stage_timings, "policy_ms", stage_started_at)

            stage_started_at = perf_counter()
            recommendations = self.ranking_service.rank_products(
                rankable_products,
                requirements,
                target_profile,
            )
            self._mark_stage(stage_timings, "ranking_ms", stage_started_at)

            stage_started_at = perf_counter()
            if not defer_explanations:
                recommendations = self.explanation_service.enrich_recommendations(
                    requirements,
                    target_profile,
                    recommendations,
                    allow_llm=feature_flags.get("explanation_llm", False),
                )
            self._mark_stage(stage_timings, "explanations_ms", stage_started_at)

            fallback_reason = str(retrieval_result.get("fallback_reason") or "")
            if not recommendations:
                if compatibility_result.get("rejected_products") and not compatibility_result.get("eligible_products"):
                    fallback_reason = "compatibility_blocked_all"
                elif policy_result.get("rejected_products") and not rankable_products:
                    fallback_reason = "policy_rejected_all"
                elif not rankable_products:
                    fallback_reason = fallback_reason or "no_exact_fit"

        stage_timings = self._hydrate_stage_aliases(stage_timings)

        debug_trace = {
            "deferred_reason": deferred_reason,
            "retrieval_result": retrieval_result,
            "compatibility_result": compatibility_result,
            "policy_result": policy_result,
            "catalog_validation_result": catalog_validation_result,
            "raw_products": raw_products,
            "all_normalized_products": all_normalized_products,
            "currency_fallback_used": currency_fallback_used,
            "catalog_source_snapshot": catalog_source_snapshot,
            "store_scope_applied": store_scope_applied,
            "rankable_products": rankable_products,
            "prepared_catalog_cache_key": getattr(prepared_catalog_state, "cache_key", ""),
        }
        return RecommendationCoreResult(
            ranking_deferred=bool(ranking_deferred),
            shortlisted_product_ids=list(candidate_ids),
            ranked_recommendations=list(recommendations),
            fallback_reason=str(fallback_reason or ""),
            stage_timings_ms=stage_timings,
        ), debug_trace

    def assemble_response(
        self,
        prepared_context,
        core_result,
        debug_trace,
        feature_flags=None,
        started_at=None,
        capture_runtime_observability=True,
    ):
        feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
        requirements = dict(prepared_context.requirements or {})
        target_profile = dict(prepared_context.target_profile or {})
        readiness = dict(prepared_context.readiness or {})
        recommendations = [dict(item) for item in list(core_result.ranked_recommendations or [])]
        stage_timings = dict(core_result.stage_timings_ms or {})
        stage_started_at = perf_counter()
        for recommendation in recommendations:
            recommendation["buy_url"] = self._build_buy_url(recommendation.get("product_id"))

        compatibility_result = dict(debug_trace.get("compatibility_result") or {})
        policy_result = dict(debug_trace.get("policy_result") or {})
        retrieval_result = dict(debug_trace.get("retrieval_result") or {})
        catalog_validation_result = dict(debug_trace.get("catalog_validation_result") or {})
        raw_products = list(debug_trace.get("raw_products") or [])
        all_normalized_products = list(debug_trace.get("all_normalized_products") or [])
        currency_fallback_used = bool(debug_trace.get("currency_fallback_used"))
        catalog_source_snapshot = dict(debug_trace.get("catalog_source_snapshot") or {})
        store_scope_applied = bool(debug_trace.get("store_scope_applied"))
        deferred_reason = str(debug_trace.get("deferred_reason") or "")
        rankable_products = list(debug_trace.get("rankable_products") or [])

        summary = (
            target_profile.get("summary")
            if core_result.ranking_deferred
            else self.explanation_service.build_summary(requirements, target_profile, recommendations)
        )
        budget_fit_summary = self._build_budget_fit_summary(requirements, recommendations)
        ui_state_hint = "recommendation_ready"
        blocking_reason_code = ""
        next_question_override = ""
        if budget_fit_summary.get("no_exact_budget_fit"):
            recommendations = self._annotate_no_exact_budget_fit_recommendations(requirements, recommendations)
            summary = self._build_no_match_summary(requirements, reason_code="no_exact_budget_fit")
            ui_state_hint = "no_match_found"
            blocking_reason_code = "no_exact_budget_fit"
            next_question_override = self._build_no_match_prompt(requirements, reason_code="no_exact_budget_fit")
            recommendations = []
        elif not recommendations and not core_result.ranking_deferred:
            blocking_reason_code = str(core_result.fallback_reason or "no_match_found").strip() or "no_match_found"
            summary = self._build_no_match_summary(requirements, reason_code=blocking_reason_code)
            ui_state_hint = "no_match_found"
            next_question_override = self._build_no_match_prompt(requirements, reason_code=blocking_reason_code)
        expert_review_reason = self._expert_review_reason(
            readiness,
            core_result.ranking_deferred,
            core_result.fallback_reason,
            compatibility_result,
            recommendations,
        )
        expert_review_reason = self._apply_template_review_reason(prepared_context.selected_template, expert_review_reason)
        clarification_required_reasons = self._clarification_required_reasons(readiness)
        decision_policy_profile = self.config_service.get_decision_policy_profile()
        recommendation_mode = self._recommendation_mode(
            readiness=readiness,
            recommendations=recommendations,
            fallback_reason=core_result.fallback_reason,
            expert_review_reason=expert_review_reason,
            clarification_required_reasons=clarification_required_reasons,
            candidate_pool_size=len(rankable_products),
        )
        recommendation_mode = self._apply_template_selection_mode(prepared_context.selected_template, recommendation_mode)
        requirements["review_state"] = self.review_support_service.enrich_review_state(
            requirements=requirements,
            readiness=readiness,
            template_candidates=prepared_context.template_candidates,
            recommendation_mode=recommendation_mode,
        )
        check_requirement_summary = self.review_support_service.build_check_requirement_summary(
            requirements=requirements,
            readiness=readiness,
            template_candidates=prepared_context.template_candidates,
            recommendation_mode=recommendation_mode,
        )
        editable_inferred_values = self.review_support_service.build_editable_inferred_values(requirements)
        catalog_observability = self._build_catalog_observability(
            raw_products=raw_products,
            normalized_products=all_normalized_products,
            catalog_validation_result=catalog_validation_result,
            requirements=requirements,
            currency_fallback_used=currency_fallback_used,
            catalog_source_snapshot=catalog_source_snapshot,
            store_scope_applied=store_scope_applied,
        )
        self._mark_stage(stage_timings, "response_assembly_ms", stage_started_at)
        response = {
            "decision_trace_id": prepared_context.decision_trace_id,
            "requirements": requirements,
            "field_state": requirements.get("field_state") or {},
            "field_source": requirements.get("field_source") or {},
            "assumption_severity": requirements.get("assumption_severity") or {},
            "recommendation_mode": recommendation_mode,
            "clarification_required_reasons": clarification_required_reasons,
            "review_state": requirements.get("review_state") or {},
            "check_requirement_summary": check_requirement_summary,
            "editable_inferred_values": editable_inferred_values,
            "template_candidates": prepared_context.template_candidates,
            "target_profile": target_profile,
            "recommendations": recommendations,
            "summary": summary,
            "assumptions": self.explanation_service.build_assumptions(requirements),
            "comparison": "",
            "extracted_schema": prepared_context.extracted_schema,
            "readiness": readiness,
            "compatibility_report": self._build_compatibility_report(compatibility_result),
            "fallback_reason": core_result.fallback_reason or ("no_exact_fit" if budget_fit_summary.get("no_exact_budget_fit") else ""),
            "ui_state_hint": ui_state_hint,
            "blocking_reason_code": blocking_reason_code,
            "expert_review_eligible": bool(expert_review_reason) and feature_flags.get("expert_review", True),
            "meta": {
                "engine_version": ENGINE_VERSION,
                "config_versions": self.config_service.get_versions(),
                "config_bundle_version": self.config_service.get_bundle_version(),
                "feature_flags": feature_flags,
                "source_product_count": len(raw_products),
                "catalog_validation_summary": catalog_validation_result.get("summary") or {},
                "catalog_validation_rejections_sample": (catalog_validation_result.get("rejected_products") or [])[:5],
                "eligible_product_count": len(rankable_products),
                "recommended_count": len(recommendations),
                "budget_fit_summary": budget_fit_summary,
                "catalog_observability": catalog_observability,
                "filtered_categories": target_profile.get("categories") or [],
                "semantic_candidate_ids": list(core_result.shortlisted_product_ids or [])[:10],
                "semantic_candidate_count": len(list(core_result.shortlisted_product_ids or [])),
                "retrieval_summary": {
                    "candidate_count": len(list(core_result.shortlisted_product_ids or [])),
                    "fallback_reason": retrieval_result.get("fallback_reason"),
                    "top_candidates": (retrieval_result.get("scored_candidates") or [])[:10],
                },
                "compatibility_summary": compatibility_result.get("summary") or {},
                "compatibility_rejections_sample": (compatibility_result.get("rejected_products") or [])[:5],
                "policy_summary": policy_result.get("summary") or {},
                "policy_rejections_sample": (policy_result.get("rejected_products") or [])[:5],
                "applied_rules_count": len(target_profile.get("applied_rules") or []),
                "ranking_deferred": core_result.ranking_deferred,
                "ranking_deferred_reason": deferred_reason,
                "expert_review_reason": expert_review_reason,
                "decision_policy_profile": decision_policy_profile,
                "stage_timings_ms": stage_timings,
            },
        }
        if next_question_override:
            question_started_at = perf_counter()
            response["next_question"] = str(next_question_override or "").strip()
            self._mark_stage(stage_timings, "question_generation_ms", question_started_at)
        elif not readiness.get("is_ready"):
            question_started_at = perf_counter()
            response["next_question"] = (
                str(readiness.get("next_question") or "").strip()
                or self.clarification_service._context_aware_prompt(
                    readiness.get("highest_priority_missing_field"),
                    requirements,
                )
            )
            self._mark_stage(stage_timings, "question_generation_ms", question_started_at)
        else:
            stage_timings["question_generation_ms"] = 0.0
        response["meta"]["decision_trace"] = self._build_decision_trace(
            decision_trace_id=prepared_context.decision_trace_id,
            requirements=requirements,
            extracted_schema=prepared_context.extracted_schema,
            target_profile=target_profile,
            readiness=readiness,
            retrieval_result=retrieval_result,
            catalog_validation_result=catalog_validation_result,
            compatibility_result=compatibility_result,
            policy_result=policy_result,
            recommendations=recommendations,
            fallback_reason=core_result.fallback_reason,
            recommendation_mode=recommendation_mode,
            clarification_required_reasons=clarification_required_reasons,
            expert_review_reason=expert_review_reason,
            feature_flags=feature_flags,
            decision_policy_profile=decision_policy_profile,
            check_requirement_summary=check_requirement_summary,
            editable_inferred_values=editable_inferred_values,
            template_candidates=prepared_context.template_candidates,
            selected_template=prepared_context.selected_template,
        )
        if capture_runtime_observability:
            self._attach_runtime_observability(
                response=response,
                started_at=started_at,
                decision_trace_id=prepared_context.decision_trace_id,
                requirements=requirements,
                readiness=readiness,
                recommendation_mode=recommendation_mode,
                clarification_required_reasons=clarification_required_reasons,
                fallback_reason=core_result.fallback_reason,
                next_question=response.get("next_question"),
            )
        return response

    def generate_narrative_enrichment(self, prepared_context, response, feature_flags=None):
        feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
        response = dict(response or {})
        response["comparison"] = self.explanation_service.build_comparison(
            response.get("requirements") or prepared_context.requirements,
            response.get("recommendations") or [],
            allow_llm=feature_flags.get("comparison_llm", False),
        )
        return response

    def _dispatch_persistence_from_outputs(self, prepared_context, response, user_id="", business_id=""):
        persistence_payload = {
            "raw_intake_snapshot": prepared_context.raw_intake_snapshot,
            "requirements": response.get("requirements") or prepared_context.requirements,
            "target_profile": response.get("target_profile") or prepared_context.target_profile,
            "recommendations": response.get("recommendations") or [],
            "summary": response.get("summary") or "",
            "assumptions": response.get("assumptions") or [],
            "meta": {
                **dict(response.get("meta") or {}),
                "raw_chat": (response.get("requirements") or {}).get("raw_chat", ""),
                "extracted_schema": prepared_context.extracted_schema,
            },
            "user_id": user_id,
            "business_id": business_id,
        }
        session_id = str(uuid4())
        response["session_id"] = session_id
        async_persistence_enabled = str(os.getenv("PROCUREMENT_ASYNC_PERSISTENCE", "true")).strip().lower() != "false"
        if not async_persistence_enabled:
            session, persistence_error = self._persist_session(session_id=session_id, **persistence_payload)
            if session is None and persistence_error:
                response.setdefault("meta", {})
                response["meta"]["persistence_warning"] = persistence_error
            return

        self._persistence_executor.submit(
            self._persist_session,
            session_id=session_id,
            **persistence_payload,
        )

    def _recommend_multi_intent(
        self,
        payload,
        multi_intent_result,
        extracted_schema=None,
        prepared_context=None,
        feature_flags=None,
        user_id="",
        business_id="",
        persist=True,
        top_level_timings=None,
    ):
        payload = dict(payload or {})
        top_level_timings = top_level_timings or self._new_top_level_timings()
        decision_trace_id = str(uuid4())
        started_at = self.observability_service.start_timer()
        feature_flags = dict(feature_flags or self.feature_flag_service.get_flags())
        if prepared_context is None:
            prepare_started_at = perf_counter()
            prepared_context = self.prepare_from_extracted_schema(
                payload=payload,
                extracted_schema=dict(extracted_schema or self._extract_schema(payload)),
                feature_flags=feature_flags,
                decision_trace_id=decision_trace_id,
            )
            self._mark_stage(top_level_timings["prepare_ms"], "total_ms", prepare_started_at)
        extracted_schema = dict(prepared_context.extracted_schema or {})
        raw_intake_snapshot = dict(prepared_context.raw_intake_snapshot or {})
        requirements = dict(prepared_context.requirements or {})
        target_profile = dict(prepared_context.target_profile or {})
        base_readiness = dict(prepared_context.readiness or {})
        template_candidates = self.template_service.select_candidates(
            requirements,
            target_profile,
            multi_intent_result=multi_intent_result,
        )
        selected_template = self._selected_template(template_candidates)
        selected_template_for_workflow = selected_template if selected_template.get("selection_allowed", True) else {}
        multi_intent_policy = self.multi_intent_policy_service.evaluate(
            payload=payload,
            extracted_schema=extracted_schema,
            requirements=requirements,
            multi_intent_result=multi_intent_result,
            selected_template=selected_template_for_workflow,
        )

        recommendation_groups = []
        group_traces = []
        flattened_recommendations = []
        merged_assumptions = []
        group_next_questions = []

        for intent in multi_intent_result.get("intents") or []:
            group_policy = dict((multi_intent_policy.get("groups_by_id") or {}).get(intent.get("group_id")) or {})
            group_payload = self._apply_multi_intent_shared_context(
                intent.get("payload") or {},
                requirements,
                group_policy=group_policy,
            )
            group_prepared = self.prepare_from_extracted_schema(
                payload=group_payload,
                extracted_schema=intent.get("extracted_schema") or {},
                feature_flags=feature_flags,
                decision_trace_id=str(uuid4()),
                source_mode="multi_intent_group",
                prepared_catalog_state=prepared_context.prepared_catalog_state,
            )
            group_response = self._recommend_single_from_prepared(
                prepared_context=group_prepared,
                feature_flags=feature_flags,
                persist=False,
                capture_runtime_observability=False,
            )
            group_meta = dict(group_response.get("meta") or {})
            group_decision_trace = group_meta.pop("decision_trace", None)
            group_selected_template = dict(group_meta.get("selected_template") or {})
            group_entry = {
                "group_id": intent.get("group_id"),
                "label": intent.get("label"),
                "intent_text": intent.get("intent_text"),
                "category": intent.get("category"),
                "workloads": intent.get("workloads") or [],
                "shared_constraints": group_policy.get("shared_constraints") or [],
                "warnings": group_policy.get("warnings") or [],
                "shared_budget": group_policy.get("shared_budget") or {},
                "decision_trace_id": group_response.get("decision_trace_id"),
                "requirements": group_response.get("requirements") or {},
                "field_state": group_response.get("field_state") or {},
                "field_source": group_response.get("field_source") or {},
                "assumption_severity": group_response.get("assumption_severity") or {},
                "recommendation_mode": group_response.get("recommendation_mode"),
                "clarification_required_reasons": group_response.get("clarification_required_reasons") or [],
                "check_requirement_summary": group_response.get("check_requirement_summary") or {},
                "editable_inferred_values": group_response.get("editable_inferred_values") or {},
                "selected_template": group_selected_template,
                "template_candidates": group_response.get("template_candidates") or [],
                "target_profile": group_response.get("target_profile") or {},
                "recommendations": group_response.get("recommendations") or [],
                "summary": group_response.get("summary", ""),
                "assumptions": group_response.get("assumptions") or [],
                "comparison": group_response.get("comparison", ""),
                "readiness": group_response.get("readiness") or {},
                "compatibility_report": group_response.get("compatibility_report") or {},
                "fallback_reason": group_response.get("fallback_reason"),
                "expert_review_eligible": group_response.get("expert_review_eligible", False),
                "next_question": group_response.get("next_question"),
                "meta": group_meta,
            }
            recommendation_groups.append(group_entry)
            if group_decision_trace:
                group_traces.append(
                    {
                        "group_id": group_entry["group_id"],
                        "label": group_entry["label"],
                        "decision_trace": group_decision_trace,
                    }
                )
            if group_entry["recommendations"]:
                top_recommendation = dict(group_entry["recommendations"][0])
                top_recommendation["recommendation_group_id"] = group_entry["group_id"]
                top_recommendation["recommendation_group_label"] = group_entry["label"]
                flattened_recommendations.append(top_recommendation)
            merged_assumptions.extend(group_entry["assumptions"])
            if group_entry["next_question"]:
                group_next_questions.append(
                    {
                        "group_id": group_entry["group_id"],
                        "label": group_entry["label"],
                        "prompt": group_entry["next_question"],
                    }
                )

        bundle_result = self.bundle_service.build_bundle_result(
            requirements=requirements,
            recommendation_groups=recommendation_groups,
            multi_intent_policy=multi_intent_policy,
            selected_template=selected_template_for_workflow,
        )
        combined_merge_rules = list(multi_intent_policy.get("merge_rules") or []) + list(
            bundle_result.get("merge_rules") or []
        )
        policy_trace = list(multi_intent_policy.get("split_rules") or []) + combined_merge_rules
        bundle_trace = self._build_bundle_trace(bundle_result, selected_template)
        bundle_validated = bool(bundle_result.get("bundle_validated"))
        grouped_readiness = self._build_grouped_readiness(
            base_readiness,
            recommendation_groups,
            multi_intent_policy=multi_intent_policy,
        )
        compatibility_report = self._build_grouped_compatibility_report(recommendation_groups)
        fallback_reason = self._grouped_fallback_reason(recommendation_groups)
        clarification_required_reasons = self._clarification_required_reasons(grouped_readiness)
        expert_review_reason = self._grouped_expert_review_reason(recommendation_groups, fallback_reason)
        if not bundle_validated and not clarification_required_reasons:
            expert_review_reason = expert_review_reason or "bundle_validation_rejected"
        expert_review_reason = self._apply_template_review_reason(selected_template, expert_review_reason)
        decision_policy_profile = self.config_service.get_decision_policy_profile()
        recommendation_mode = self._recommendation_mode(
            readiness=grouped_readiness,
            recommendations=flattened_recommendations,
            fallback_reason=fallback_reason,
            expert_review_reason=expert_review_reason,
            clarification_required_reasons=clarification_required_reasons,
            candidate_pool_size=sum(group["meta"].get("eligible_product_count", 0) for group in recommendation_groups),
        )
        recommendation_mode = self._apply_template_selection_mode(selected_template, recommendation_mode)
        requirements["review_state"] = self.review_support_service.enrich_review_state(
            requirements=requirements,
            readiness=grouped_readiness,
            template_candidates=template_candidates,
            recommendation_mode=recommendation_mode,
        )
        check_requirement_summary = self.review_support_service.build_check_requirement_summary(
            requirements=requirements,
            readiness=grouped_readiness,
            template_candidates=template_candidates,
            recommendation_mode=recommendation_mode,
        )
        editable_inferred_values = self.review_support_service.build_editable_inferred_values(requirements)
        template_id = bundle_trace.get("template_id")
        template_version = bundle_trace.get("template_version")
        shared_budget_requires_allocation = bool((multi_intent_policy.get("shared_budget") or {}).get("allocation_required"))
        response = {
            "decision_trace_id": decision_trace_id,
            "requirements": requirements,
            "field_state": requirements.get("field_state") or {},
            "field_source": requirements.get("field_source") or {},
            "assumption_severity": requirements.get("assumption_severity") or {},
            "recommendation_mode": recommendation_mode,
            "clarification_required_reasons": clarification_required_reasons,
            "review_state": requirements.get("review_state") or {},
            "check_requirement_summary": check_requirement_summary,
            "editable_inferred_values": editable_inferred_values,
            "template_candidates": template_candidates,
            "target_profile": target_profile,
            "recommendations": flattened_recommendations,
            "recommendation_groups": recommendation_groups,
            "summary": self._build_release_4a_summary(
                recommendation_groups,
                multi_intent_policy=multi_intent_policy,
                bundle_result=bundle_result,
            ),
            "assumptions": self._dedupe_strings(merged_assumptions),
            "comparison": self.explanation_service.build_comparison(
                requirements,
                flattened_recommendations,
                allow_llm=feature_flags.get("comparison_llm", False),
            ),
            "extracted_schema": extracted_schema,
            "readiness": grouped_readiness,
            "compatibility_report": compatibility_report,
            "bundle_compatibility_report": bundle_result.get("bundle_compatibility_report") or {},
            "bundle_conflict_codes": list(bundle_result.get("bundle_conflict_codes") or []),
            "bundle_capacity_summary": bundle_result.get("bundle_capacity_summary") or {},
            "bundle_options": list(bundle_result.get("bundle_options") or []),
            "architecture_graph": bundle_result.get("architecture_graph") or {},
            "template_id": template_id,
            "template_version": template_version,
            "fallback_reason": fallback_reason,
            "ui_state_hint": (
                "shared_budget_allocation_required"
                if shared_budget_requires_allocation
                else "grouped_recommendation_ready"
                if recommendation_groups and flattened_recommendations
                else "no_match_found"
            ),
            "blocking_reason_code": (
                "shared_budget_allocation_required"
                if shared_budget_requires_allocation
                else (fallback_reason or "no_match_found") if not flattened_recommendations else ""
            ),
            "expert_review_eligible": bool(expert_review_reason) and feature_flags.get("expert_review", True),
            "meta": {
                "engine_version": ENGINE_VERSION,
                "config_versions": self.config_service.get_versions(),
                "config_bundle_version": self.config_service.get_bundle_version(),
                "feature_flags": feature_flags,
                "source_product_count": sum(group["meta"].get("source_product_count", 0) for group in recommendation_groups),
                "catalog_validation_summary": {
                    "group_count": len(recommendation_groups),
                    "rejected_count": sum(
                        (group["meta"].get("catalog_validation_summary") or {}).get("rejected_count", 0)
                        for group in recommendation_groups
                    ),
                },
                "eligible_product_count": sum(group["meta"].get("eligible_product_count", 0) for group in recommendation_groups),
                "recommended_count": len(flattened_recommendations),
                "catalog_observability": self._aggregate_catalog_observability(recommendation_groups),
                "filtered_categories": self._dedupe_strings(
                    [
                        category
                        for group in recommendation_groups
                        for category in (group.get("target_profile", {}).get("categories") or [])
                    ]
                ),
                "semantic_candidate_ids": self._dedupe_strings(
                    [
                        candidate_id
                        for group in recommendation_groups
                        for candidate_id in (group["meta"].get("semantic_candidate_ids") or [])
                    ]
                )[:10],
                "semantic_candidate_count": sum(group["meta"].get("semantic_candidate_count", 0) for group in recommendation_groups),
                "retrieval_summary": {
                    "candidate_count": sum(
                        (group["meta"].get("retrieval_summary") or {}).get("candidate_count", 0)
                        for group in recommendation_groups
                    ),
                    "fallback_reason": fallback_reason,
                    "top_candidates": [
                        {
                            "group_id": group["group_id"],
                            "label": group["label"],
                            "top_candidates": (group["meta"].get("retrieval_summary") or {}).get("top_candidates") or [],
                        }
                        for group in recommendation_groups
                    ],
                },
                "compatibility_summary": compatibility_report.get("summary") or {},
                "compatibility_rejections_sample": compatibility_report.get("rejected_products") or [],
                "policy_summary": {
                    "group_count": len(recommendation_groups),
                    "rejected_count": sum(
                        (group["meta"].get("policy_summary") or {}).get("rejected_count", 0)
                        for group in recommendation_groups
                    ),
                },
                "policy_rejections_sample": [
                    {
                        "group_id": group["group_id"],
                        "label": group["label"],
                        "rejected_products": (group["meta"].get("policy_rejections_sample") or [])[:3],
                    }
                    for group in recommendation_groups
                    if group["meta"].get("policy_rejections_sample")
                ][:5],
                "applied_rules_count": sum(group["meta"].get("applied_rules_count", 0) for group in recommendation_groups),
                "ranking_deferred": all(group["meta"].get("ranking_deferred", False) for group in recommendation_groups),
                "ranking_deferred_reason": (
                    "multi_intent_group_clarification_required"
                    if any(group["meta"].get("ranking_deferred", False) for group in recommendation_groups)
                    else None
                ),
                "expert_review_reason": expert_review_reason,
                "decision_policy_profile": decision_policy_profile,
                "bundle_trace": bundle_trace,
                "multi_intent": {
                    "is_multi_intent": True,
                    "is_grouped": True,
                    "bundle_validated": bundle_validated,
                    "policy_version": multi_intent_policy.get("policy_version"),
                    "split_source": multi_intent_result.get("split_source"),
                    "shared_budget_reused": multi_intent_result.get("shared_budget_reused", False),
                    "shared_constraints": multi_intent_policy.get("shared_constraints") or [],
                    "shared_budget": multi_intent_policy.get("shared_budget") or {},
                    "warnings": multi_intent_policy.get("warnings") or [],
                    "split_rules": multi_intent_policy.get("split_rules") or [],
                    "merge_rules": combined_merge_rules,
                    "policy_trace": policy_trace,
                    "bundle_conflict_codes": list(bundle_result.get("bundle_conflict_codes") or []),
                    "validation_outcome": bundle_trace.get("validation_outcome"),
                    "template_id": template_id,
                    "template_version": template_version,
                    "group_count": len(recommendation_groups),
                    "group_labels": [group["label"] for group in recommendation_groups],
                    "group_decision_trace_ids": [
                        group.get("decision_trace_id")
                        for group in recommendation_groups
                        if group.get("decision_trace_id")
                    ],
                    "group_next_questions": group_next_questions,
                    "group_templates": self._build_group_template_summary(recommendation_groups),
                },
            },
        }
        if grouped_readiness.get("next_question"):
            response["next_question"] = grouped_readiness.get("next_question")
        elif group_next_questions:
            response["next_question"] = group_next_questions[0]["prompt"]

        response["meta"]["decision_trace"] = {
            "decision_trace_id": decision_trace_id,
            
            "compatibility": {
                "scope": compatibility_report.get("scope") or "item",
                "summary": compatibility_report.get("summary") or {},
                "rejected_products": compatibility_report.get("rejected_products") or [],
            },
            "bundle_validation": bundle_trace,
            "expert_review_reason": expert_review_reason,
            "feature_flags": feature_flags,
            "config_versions": self.config_service.get_versions(),
         
            "multi_intent": {
                "is_multi_intent": True,
                "policy_version": multi_intent_policy.get("policy_version"),
                "split_source": multi_intent_result.get("split_source"),
                "shared_budget_reused": multi_intent_result.get("shared_budget_reused", False),
                "bundle_validated": bundle_validated,
                "shared_constraints": multi_intent_policy.get("shared_constraints") or [],
                "shared_budget": multi_intent_policy.get("shared_budget") or {},
                "warnings": multi_intent_policy.get("warnings") or [],
                "split_rules": multi_intent_policy.get("split_rules") or [],
                "merge_rules": combined_merge_rules,
                "policy_trace": policy_trace,
                "bundle_conflict_codes": list(bundle_result.get("bundle_conflict_codes") or []),
                "validation_outcome": bundle_trace.get("validation_outcome"),
                "template_id": template_id,
                "template_version": template_version,
                "groups": group_traces,
                "group_templates": self._build_group_template_summary(recommendation_groups),
            },
        }
        self._attach_runtime_observability(
            response=response,
            started_at=started_at,
            decision_trace_id=decision_trace_id,
            requirements=requirements,
            readiness=grouped_readiness,
            recommendation_mode=recommendation_mode,
            clarification_required_reasons=clarification_required_reasons,
            fallback_reason=fallback_reason,
            next_question=response.get("next_question"),
        )

        if persist:
            self._dispatch_persistence_from_outputs(
                prepared_context=prepared_context,
                response={
                    **response,
                    "recommendations": flattened_recommendations,
                    "target_profile": target_profile,
                    "assumptions": response["assumptions"],
                    "meta": {
                        **response["meta"],
                        "recommendation_groups": recommendation_groups,
                    },
                },
                user_id=user_id,
                business_id=business_id,
            )

        return response

    def _attach_runtime_observability(
        self,
        response,
        started_at,
        decision_trace_id,
        requirements,
        readiness,
        recommendation_mode,
        clarification_required_reasons,
        fallback_reason,
        next_question=None,
    ):
        response = dict(response or {})
        runtime_observability = self.observability_service.build_runtime_observability(
            started_at=started_at,
            decision_trace_id=decision_trace_id,
            requirements=requirements,
            readiness=readiness,
            recommendation_mode=recommendation_mode,
            clarification_required_reasons=clarification_required_reasons,
            fallback_reason=fallback_reason,
            next_question=next_question,
            response_payload=response,
        )
        response.setdefault("meta", {})
        response["meta"]["runtime_observability"] = runtime_observability
        decision_trace = response["meta"].get("decision_trace")
        if isinstance(decision_trace, dict):
            pass
        return response

    def _apply_multi_intent_shared_context(self, payload, requirements, group_policy=None):
        payload = dict(payload or {})
        requirements = dict(requirements or {})
        group_policy = dict(group_policy or {})
        explicit_payload_fields = list(payload.get("_explicit_payload_fields") or [])
        field_source_hints = dict(payload.get("_field_source_hints") or {})
        shared_constraints = set(group_policy.get("shared_constraints") or [])

        if (
            requirements.get("budget_scope")
            and "budget_scope" in shared_constraints
            and not payload.get("budget_scope")
        ):
            payload["budget_scope"] = requirements.get("budget_scope")
            field_source_hints.setdefault("budget_scope", "context_explicit")

        if explicit_payload_fields:
            payload["_explicit_payload_fields"] = explicit_payload_fields
        if field_source_hints:
            payload["_field_source_hints"] = field_source_hints
        return payload

    def _normalize_products(self, raw_products, requested_currency, allowed_categories=None, currency_fallback_used=False):
        normalized_products = []
        seen_ids = set()
        allowed_categories = set(allowed_categories or [])
        for product in raw_products:
            inventory_offers = list(product.get("inventory_offers") or [])
            if not inventory_offers:
                inventory = product.get("inventory")
                inventory_offers = [inventory] if inventory else [None]

            for inventory in inventory_offers:
                candidate = dict(product)
                candidate.pop("inventory_offers", None)
                if inventory:
                    candidate["inventory"] = inventory
                else:
                    candidate.pop("inventory", None)
                normalized = normalize_product_document(candidate, requested_currency=requested_currency)
                product_id = normalized.get("id")
                if product_id in seen_ids:
                    continue
                seen_ids.add(product_id)
                normalized["offer_count"] = len(inventory_offers)
                normalized["alternate_offer_count"] = max(len(inventory_offers) - 1, 0)
                normalized["currency_fallback_used"] = bool(
                    currency_fallback_used
                    and requested_currency
                    and str(normalized.get("currency") or "").strip().upper()
                    != str(requested_currency or "").strip().upper()
                )
                normalized_products.append(normalized)
        return normalized_products

    def _filter_normalized_products(self, normalized_products, allowed_categories=None, candidate_ids=None):
        normalized_products = list(normalized_products or [])
        category_filter_enabled = bool(allowed_categories)
        candidate_filter_enabled = candidate_ids is not None
        allowed_categories = set(allowed_categories or [])
        candidate_ids = set(candidate_ids or [])
        if not category_filter_enabled and not candidate_filter_enabled:
            return normalized_products
        filtered = []
        for product in normalized_products:
            if category_filter_enabled and product.get("category") not in allowed_categories:
                continue
            if candidate_filter_enabled and product.get("id") not in candidate_ids:
                continue
            filtered.append(product)
        return filtered

    def _build_grouped_readiness(self, base_readiness, recommendation_groups, multi_intent_policy=None):
        base_readiness = dict(base_readiness or {})
        multi_intent_policy = dict(multi_intent_policy or {})
        readiness_items = [dict(group.get("readiness") or {}) for group in recommendation_groups]
        if not readiness_items:
            return base_readiness

        confidence_rank = {"low": 0, "medium": 1, "high": 2}
        band_rank = {"low": 0, "medium": 1, "high": 2}
        question_candidates = []
        missing_signals = []
        for group in recommendation_groups:
            readiness = dict(group.get("readiness") or {})
            for signal in readiness.get("missing_signals") or []:
                if signal not in missing_signals:
                    missing_signals.append(signal)
            for candidate in readiness.get("question_candidates") or []:
                candidate_copy = dict(candidate)
                candidate_copy["group_id"] = group.get("group_id")
                candidate_copy["group_label"] = group.get("label")
                question_candidates.append(candidate_copy)

        shared_budget = dict(multi_intent_policy.get("shared_budget") or {})
        if shared_budget.get("allocation_required"):
            missing_signals.append(shared_budget.get("clarification_key"))
            question_candidates.append(
                {
                    "key": shared_budget.get("clarification_key"),
                    "prompt": shared_budget.get("clarification_prompt"),
                    "rationale": shared_budget.get("clarification_rationale"),
                    "impact": 0.98,
                }
            )

        question_candidates.sort(key=lambda item: item.get("impact", 0), reverse=True)
        top_question = question_candidates[0] if question_candidates else None
        threshold = self.clarification_service.question_impact_threshold()
        should_ask_top_question = bool(top_question and float(top_question.get("impact", 0.0)) >= threshold)
        grouped_confidence = min(
            (item.get("confidence") or "medium" for item in readiness_items),
            key=lambda value: confidence_rank.get(value, 1),
        )
        grouped_band = min(
            (item.get("decision_confidence_band") or "medium" for item in readiness_items),
            key=lambda value: band_rank.get(value, 1),
        )
        grouped_score = round(
            sum(item.get("decision_confidence_score", 0.0) for item in readiness_items) / len(readiness_items),
            4,
        )

        grouped_is_ready = all(bool(item.get("is_ready")) for item in readiness_items) and not bool(shared_budget.get("allocation_required"))
        return {
            **base_readiness,
            "is_ready": grouped_is_ready,
            "confidence": grouped_confidence,
            "missing_signals": missing_signals,
            "highest_priority_missing_field": top_question.get("key") if top_question else None,
            "next_question": top_question.get("prompt") if should_ask_top_question else None,
            "follow_up_questions": question_candidates[:3],
            "decision_confidence_score": grouped_score,
            "decision_confidence_band": grouped_band,
            "recommended_question_budget": 1 if should_ask_top_question else 0,
            "routing_recommendation": (
                "clarify_before_recommendation"
                if not grouped_is_ready
                else "recommend_with_optional_refinement"
                if should_ask_top_question
                else base_readiness.get("routing_recommendation", "recommend_now")
            ),
            "recommended_refinement_question": top_question.get("prompt") if should_ask_top_question else None,
            "question_strategy": (
                "grouped_single_question"
                if should_ask_top_question
                else base_readiness.get("question_strategy", "proceed")
            ),
            "question_candidates": question_candidates[:3],
        }

    def _build_grouped_compatibility_report(self, recommendation_groups):
        group_reports = []
        rejected_products = []
        eligible_count = 0
        rejected_count = 0
        for group in recommendation_groups:
            report = dict(group.get("compatibility_report") or {})
            report_summary = dict(report.get("summary") or {})
            eligible_count += report_summary.get("eligible_count", 0)
            rejected_count += report_summary.get("rejected_count", 0)
            group_rejections = list(report.get("rejected_products") or [])
            rejected_products.extend(group_rejections[:3])
            group_reports.append(
                {
                    "group_id": group.get("group_id"),
                    "label": group.get("label"),
                    "scope": report.get("scope") or "item",
                    "summary": report_summary,
                    "rejected_products": group_rejections[:3],
                }
            )

        return {
            "scope": "item",
            "summary": {
                "compatibility_scope": "item",
                "grouped": True,
                "group_count": len(recommendation_groups),
                "eligible_count": eligible_count,
                "rejected_count": rejected_count,
            },
            "rejected_products": rejected_products[:5],
            "groups": group_reports,
        }

    def _build_grouped_summary(self, recommendation_groups, multi_intent_policy=None):
        multi_intent_policy = dict(multi_intent_policy or {})
        if not recommendation_groups:
            return "No grouped recommendations were generated."

        parts = []
        for group in recommendation_groups:
            recommendations = list(group.get("recommendations") or [])
            label = group.get("label") or group.get("group_id") or "Intent"
            if recommendations:
                top_name = recommendations[0].get("name") or "Recommendation ready"
                parts.append(f"{label}: {top_name}")
            elif group.get("next_question"):
                parts.append(f"{label}: clarification needed")
            else:
                parts.append(f"{label}: no exact fit")
        summary = "Grouped recommendations prepared for {} intents. {}".format(
            len(recommendation_groups),
            " | ".join(parts),
        )
        shared_budget = dict(multi_intent_policy.get("shared_budget") or {})
        if shared_budget.get("allocation_required"):
            summary += " Shared project budget allocation still needs confirmation before the groups can be treated as budget-valid together."
        return summary

    def _build_release_4a_summary(self, recommendation_groups, multi_intent_policy=None, bundle_result=None):
        bundle_result = dict(bundle_result or {})
        grouped_summary = self._build_grouped_summary(
            recommendation_groups,
            multi_intent_policy=multi_intent_policy,
        )
        bundle_summary = str(bundle_result.get("summary") or "").strip()
        if bundle_result.get("bundle_validated"):
            return bundle_summary or grouped_summary
        if not bundle_summary:
            return grouped_summary
        if recommendation_groups and any(group.get("recommendations") for group in recommendation_groups):
            return (
                bundle_summary
                + " Constrained per-role recommendations remain available while the bundle is not yet valid."
            )
        return bundle_summary

    def _build_bundle_trace(self, bundle_result, selected_template=None):
        bundle_result = dict(bundle_result or {})
        selected_template = dict(selected_template or {})
        bundle_candidate = dict(bundle_result.get("bundle_candidate") or {})
        bundle_report = dict(bundle_result.get("bundle_compatibility_report") or {})
        return {
            "template_id": bundle_candidate.get("template_id") or selected_template.get("template_id"),
            "template_version": bundle_candidate.get("template_version") or selected_template.get("template_version"),
            "bundle_validated": bool(bundle_result.get("bundle_validated")),
            "validation_outcome": "passed" if bundle_result.get("bundle_validated") else "rejected",
            "bundle_candidate": bundle_candidate,
            "bundle_compatibility_report": bundle_report,
            "bundle_conflict_codes": list(bundle_result.get("bundle_conflict_codes") or []),
            "bundle_capacity_summary": bundle_result.get("bundle_capacity_summary") or {},
            "bundle_options": list(bundle_result.get("bundle_options") or []),
            "architecture_graph": bundle_result.get("architecture_graph") or {},
            "merge_rules": list(bundle_result.get("merge_rules") or []),
        }

    def _build_group_template_summary(self, recommendation_groups):
        summary = []
        for group in list(recommendation_groups or []):
            selected_template = dict(group.get("selected_template") or {})
            template_candidates = list(group.get("template_candidates") or [])
            if not selected_template and template_candidates:
                selected_template = self._selected_template(template_candidates)
            summary.append(
                {
                    "group_id": group.get("group_id"),
                    "label": group.get("label"),
                    "category": group.get("category"),
                    "template_id": selected_template.get("template_id"),
                    "template_version": selected_template.get("template_version"),
                    "template_match_quality": selected_template.get("template_match_quality"),
                    "required_roles": list(selected_template.get("required_roles") or []),
                    "quantity_strategy": selected_template.get("quantity_strategy"),
                    "budget_strategy": selected_template.get("budget_strategy"),
                    "selection_allowed": bool(selected_template.get("selection_allowed", True))
                    if selected_template
                    else False,
                }
            )
        return summary

    def _grouped_fallback_reason(self, recommendation_groups):
        if not recommendation_groups:
            return "no_exact_fit"
        fallback_reasons = [
            group.get("fallback_reason")
            for group in recommendation_groups
            if group.get("fallback_reason")
        ]
        if not fallback_reasons:
            return ""
        if len(fallback_reasons) == len(recommendation_groups):
            return fallback_reasons[0] if len(set(fallback_reasons)) == 1 else "multi_intent_partial_fallback"
        return "multi_intent_partial_fallback"

    def _grouped_expert_review_reason(self, recommendation_groups, fallback_reason):
        if any(group.get("expert_review_eligible") for group in recommendation_groups):
            return "multi_intent_group_requires_review"
        if fallback_reason in {"compatibility_blocked_all", "policy_rejected_all", "no_exact_fit", "multi_intent_partial_fallback"}:
            return fallback_reason
        return ""

    def _selected_template(self, template_candidates):
        template_candidates = list(template_candidates or [])
        if not template_candidates:
            return {}
        selected = dict(template_candidates[0])
        return {
            "template_id": selected.get("template_id"),
            "template_version": selected.get("template_version"),
            "scenario_family": selected.get("scenario_family"),
            "variant": selected.get("variant"),
            "template_match_quality": selected.get("template_match_quality"),
            "match_score": selected.get("match_score"),
            "selection_allowed": bool(selected.get("selection_allowed", True)),
            "selection_rejection_reason": selected.get("selection_rejection_reason") or "",
            "matched_template_signals": selected.get("matched_template_signals") or {},
            "coverage_gap_reasons": list(selected.get("coverage_gap_reasons") or []),
            "gap_type": selected.get("gap_type") or "",
            "hard_gate_failures": list(selected.get("hard_gate_failures") or []),
            "contradiction_codes": list(selected.get("contradiction_codes") or []),
            "soft_fit_gaps": list(selected.get("soft_fit_gaps") or []),
            "template_selection_debug": dict(selected.get("template_selection_debug") or {}),
            "required_roles": list(selected.get("required_roles") or []),
            "quantity_strategy": selected.get("quantity_strategy"),
            "budget_strategy": selected.get("budget_strategy"),
            "compatibility_profile": selected.get("compatibility_profile"),
            "scoring_profile": selected.get("scoring_profile"),
            "urgency_profile": selected.get("urgency_profile"),
            "site_scope_profile": selected.get("site_scope_profile"),
            "rollout_type": selected.get("rollout_type"),
            "replacement_mode": selected.get("replacement_mode"),
            "support_preference": selected.get("support_preference"),
            "existing_infra_dependency": selected.get("existing_infra_dependency"),
            "acceptable_downgrade_path": selected.get("acceptable_downgrade_path"),
        }

    def _apply_template_review_reason(self, selected_template, expert_review_reason):
        selected_template = dict(selected_template or {})
        expert_review_reason = str(expert_review_reason or "").strip()
        template_quality = str(selected_template.get("template_match_quality") or "").strip().lower()
        if template_quality == "coverage_gap":
            return expert_review_reason or "template_coverage_gap"
        return expert_review_reason

    def _apply_template_selection_mode(self, selected_template, recommendation_mode):
        selected_template = dict(selected_template or {})
        template_quality = str(selected_template.get("template_match_quality") or "").strip().lower()
        if template_quality == "coverage_gap":
            return "expert_review_recommended"
        if template_quality == "closest_match" and recommendation_mode == "firm_recommendation":
            return "provisional_recommendation"
        return recommendation_mode

    def _dedupe_strings(self, values):
        deduped = []
        seen = set()
        for value in list(values or []):
            normalized = str(value or "").strip()
            if not normalized:
                continue
            lowered = normalized.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            deduped.append(normalized)
        return deduped

    def _persist_session(
        self,
        raw_intake_snapshot,
        requirements,
        target_profile,
        recommendations,
        summary,
        assumptions,
        meta,
        user_id="",
        business_id="",
        session_id=None,
    ):
        try:
            from ..models import ProcurementSession

            session = ProcurementSession.objects.create(
                session_id=str(session_id or uuid4()),
                user_id=str(user_id or ""),
                business_id=str(business_id or ""),
                store_id=requirements.get("store_id", ""),
                channel=requirements.get("channel", "api"),
                currency=requirements.get("currency", ""),
                raw_intake_snapshot=dict(raw_intake_snapshot or {}),
                requirements=requirements,
                target_profile=target_profile,
                recommendations=recommendations,
                summary=summary,
                assumptions=assumptions,
                meta=meta,
                engine_version=ENGINE_VERSION,
            )
            return session, None
        except Exception as exc:
            return None, str(exc)

    def _build_raw_intake_snapshot(self, payload):
        snapshot = {}
        for key, value in dict(payload or {}).items():
            if str(key).startswith("_") or key == "persist":
                continue
            snapshot[key] = value
        return snapshot

    def _build_buy_url(self, product_id, store_id=""):
        if not product_id:
            return ""

        base_url = os.getenv("SHOP_PRODUCT_BASE_URL", "https://dev.techpay.ai/shop/#/products").rstrip("/")
        return f"{base_url}/{product_id}"

    def _resolve_prepared_catalog_state(self, requirements):
        requirements = dict(requirements or {})
        cache_key = self._prepared_catalog_state_cache_key(requirements)
        cached = self._prepared_catalog_state_cache.get(cache_key)
        if cached is not None:
            return cached

        raw_products = self.catalog_repository.fetch_products(
            store_id="",
            currency=requirements.get("currency", ""),
        )
        currency_fallback_used = False
        if not raw_products and requirements.get("currency"):
            raw_products = self.catalog_repository.fetch_products(store_id="", currency="")
            currency_fallback_used = bool(raw_products)
        catalog_source_snapshot = self._catalog_source_snapshot()
        normalized_products = self._normalize_products(
            raw_products,
            requirements.get("currency"),
            allowed_categories=None,
            currency_fallback_used=currency_fallback_used,
        )
        catalog_validation_result = self._screen_catalog_metadata(normalized_products)
        eligible_products = list(catalog_validation_result.get("eligible_products") or [])
        category_subsets = self._build_category_indexed_subsets(eligible_products)
        retrieval_assets_by_subset = {
            "__all__": self._resolve_precomputed_retrieval_assets(
                eligible_products,
                subset_key="__all__",
                cache_key=cache_key,
            ),
        }
        for category_key, subset in category_subsets.items():
            retrieval_assets_by_subset[category_key] = self._resolve_precomputed_retrieval_assets(
                subset,
                subset_key=category_key,
                cache_key=cache_key,
            )

        prepared = PreparedCatalogState(
            cache_key=cache_key,
            raw_products=tuple(raw_products),
            normalized_products=tuple(normalized_products),
            eligible_products=tuple(eligible_products),
            catalog_validation_result=dict(catalog_validation_result or {}),
            category_subsets={key: tuple(value) for key, value in category_subsets.items()},
            retrieval_assets_by_subset=retrieval_assets_by_subset,
            currency_fallback_used=bool(currency_fallback_used),
            catalog_source_snapshot=dict(catalog_source_snapshot or {}),
            store_scope_applied=False,
        )
        self._prepared_catalog_state_cache[cache_key] = prepared
        return prepared

    def _resolve_precomputed_retrieval_assets(self, normalized_products, subset_key="__all__", cache_key=""):
        getter = getattr(self.catalog_repository, "get_precomputed_retrieval_assets", None)
        if callable(getter):
            try:
                assets = getter(
                    subset_key=subset_key,
                    cache_key=cache_key,
                    normalized_products=list(normalized_products or []),
                )
            except TypeError:
                assets = getter(subset_key, cache_key)
            except Exception:
                assets = None
            if assets:
                return assets
        return self.semantic_retriever.build_retrieval_assets(
            normalized_products,
            include_semantic=False,
        )

    def _prepared_catalog_state_cache_key(self, requirements):
        requirements = dict(requirements or {})
        currency = str(requirements.get("currency") or "").strip().upper()
        store_id = str(requirements.get("store_id") or "").strip().lower()
        source_snapshot = self._catalog_source_snapshot()
        source_name = str(source_snapshot.get("source_name") or getattr(self.catalog_repository, "source_name", "")).strip()
        source_path = str(source_snapshot.get("source_path") or "").strip()
        source_success = bool(source_snapshot.get("source_load_success", True))
        catalog_version = str(source_snapshot.get("catalog_version") or "").strip()
        return "|".join(
            [
                source_name,
                source_path,
                catalog_version,
                str(source_success).lower(),
                currency,
                store_id,
            ]
        )

    def _build_category_indexed_subsets(self, eligible_products):
        subsets = {}
        for product in list(eligible_products or []):
            category = str(product.get("category") or "").strip().lower()
            if not category:
                continue
            subsets.setdefault(category, []).append(product)
        return subsets

    def _resolve_category_subset_from_state(self, prepared_catalog_state, categories):
        prepared_catalog_state = prepared_catalog_state or PreparedCatalogState(
            cache_key="",
            raw_products=tuple(),
            normalized_products=tuple(),
            eligible_products=tuple(),
            catalog_validation_result={},
            category_subsets={},
            retrieval_assets_by_subset={},
            currency_fallback_used=False,
            catalog_source_snapshot={},
        )
        categories = [str(value or "").strip().lower() for value in list(categories or []) if str(value or "").strip()]
        if not categories:
            return list(prepared_catalog_state.eligible_products or []), "__all__"
        subset = []
        for category in categories:
            subset.extend(list((prepared_catalog_state.category_subsets or {}).get(category) or []))
        if not subset:
            return [], "__all__"
        seen = set()
        deduped = []
        for product in subset:
            product_id = product.get("id")
            if not product_id or product_id in seen:
                continue
            seen.add(product_id)
            deduped.append(product)
        subset_key = "__".join(sorted(categories))
        return deduped, subset_key

    def _extract_schema(self, payload):
        chat_text = str(payload.get("chat_text") or payload.get("raw_chat") or "").strip()
        extraction_context = payload.get("extracted_schema") or {}
        if extraction_context and extraction_context.get("intake_confidence") is not None:
            context_schema = dict(extraction_context)
            if chat_text and not context_schema.get("raw_chat"):
                context_schema["raw_chat"] = chat_text
            return dict(self.extraction_service.extract("", context=context_schema))
        if chat_text:
            return dict(self.extraction_service.extract(chat_text, context=extraction_context))

        fallback_schema = {
            "raw_chat": chat_text,
            "company_size": None,
            "industry": payload.get("industry"),
            "business_type": payload.get("business_type"),
            "team_size": payload.get("team_size"),
            "workload_types": payload.get("workload_types") or payload.get("workloads") or [],
            "application_signals": payload.get("application_signals") or [],
            "capability_tags": payload.get("capability_tags") or [],
            "budget": payload.get("budget"),
            "growth_expectation": payload.get("growth_expectation"),
            "existing_infrastructure": payload.get("existing_infrastructure") or [],
            "preferred_manufacturers": payload.get("preferred_manufacturers") or [],
            "blocked_manufacturers": payload.get("blocked_manufacturers") or [],
            "preferred_sellers": payload.get("preferred_sellers") or [],
            "blocked_sellers": payload.get("blocked_sellers") or [],
            "preferred_category": payload.get("preferred_category") or payload.get("category"),
            "performance_priority": payload.get("performance_priority"),
            "portability_need": payload.get("portability_need"),
            "support_expectation": payload.get("support_expectation"),
            "availability_need": payload.get("availability_need"),
            "require_returnable": payload.get("require_returnable"),
            "quantity": payload.get("quantity"),
            "purchase_scope": payload.get("purchase_scope"),
            "timeline": payload.get("timeline"),
            "requested_ram": payload.get("requested_ram"),
            "requested_storage": payload.get("requested_storage"),
            "requested_ram_is_minimum": payload.get("requested_ram_is_minimum"),
            "requested_storage_is_minimum": payload.get("requested_storage_is_minimum"),
            "notes": payload.get("notes", ""),
            "missing_fields": [],
            "intake_confidence": 1.0,
        }
        return dict(self.extraction_service.extract("", context=fallback_schema))

    def _build_compatibility_report(self, compatibility_result):
        compatibility_result = compatibility_result or {}
        summary = compatibility_result.get("summary") or {}
        return {
            "scope": summary.get("compatibility_scope") or "item",
            "summary": summary,
            "rejected_products": (compatibility_result.get("rejected_products") or [])[:5],
        }

    def _deterministic_candidate_pool(self, normalized_products, top_k=40):
        candidates = []
        for product in list(normalized_products or [])[:top_k]:
            product_id = product.get("id")
            if not product_id:
                continue
            candidates.append(
                {
                    "product_id": product_id,
                    "base_product_id": product.get("base_product_id") or product_id,
                    "manufacturer": str(product.get("manufacturer") or "").strip().lower(),
                    "candidate_score": 1.0,
                    "semantic_norm": 0.0,
                    "lexical_norm": 0.0,
                    "business_boost": 1.0,
                }
            )
        return {
            "candidate_ids": [item["product_id"] for item in candidates],
            "scored_candidates": candidates,
            "fallback_reason": "semantic_retrieval_disabled",
        }

    def _screen_catalog_metadata(self, normalized_products):
        eligible_products = []
        rejected_products = []
        for product in list(normalized_products or []):
            metadata_validation = dict(product.get("metadata_validation") or {})
            category = product.get("category")
            missing_required_fields = list(metadata_validation.get("missing_required_fields") or [])
            readiness_state = str(
                product.get("readiness_state") or metadata_validation.get("readiness_state") or ""
            ).strip()
            if readiness_state == "insufficient":
                rejected_products.append(
                    {
                        "product_id": product.get("id"),
                        "name": product.get("name"),
                        "category": category,
                        "manufacturer": product.get("manufacturer"),
                        "reasons": list(metadata_validation.get("parse_warnings") or [])
                        or ["Missing required metadata: " + ", ".join(missing_required_fields)],
                        "readiness_state": readiness_state,
                        "missing_required_fields": missing_required_fields,
                        "missing_critical_fields": list(metadata_validation.get("missing_critical_fields") or []),
                    }
                )
                continue
            eligible_products.append(product)
        return {
            "eligible_products": eligible_products,
            "rejected_products": rejected_products,
            "summary": {
                "input_count": len(list(normalized_products or [])),
                "eligible_count": len(eligible_products),
                "rejected_count": len(rejected_products),
            },
        }

    def _catalog_source_snapshot(self):
        getter = getattr(self.catalog_repository, "get_observability_snapshot", None)
        if callable(getter):
            try:
                snapshot = dict(getter() or {})
            except Exception:
                snapshot = {}
        else:
            snapshot = {}
        if snapshot:
            return snapshot
        return {
            "source_name": getattr(self.catalog_repository, "source_name", self.catalog_repository.__class__.__name__),
            "source_load_success": True,
            "unmatched_inventory_count": 0,
        }

    def _build_catalog_observability(
        self,
        raw_products,
        normalized_products,
        catalog_validation_result,
        requirements,
        currency_fallback_used=False,
        catalog_source_snapshot=None,
        store_scope_applied=False,
    ):
        raw_products = list(raw_products or [])
        normalized_products = list(normalized_products or [])
        catalog_validation_result = dict(catalog_validation_result or {})
        requirements = dict(requirements or {})
        catalog_source_snapshot = dict(catalog_source_snapshot or {})
        readiness_state_counts = {}
        parse_warning_count = 0
        provisional_count = 0
        for product in normalized_products:
            readiness_state = str(product.get("readiness_state") or "unknown").strip() or "unknown"
            readiness_state_counts[readiness_state] = readiness_state_counts.get(readiness_state, 0) + 1
            parse_warning_count += len(product.get("parse_warnings") or [])
            if readiness_state == "provisional":
                provisional_count += 1
        return {
            "source_name": catalog_source_snapshot.get("source_name")
            or getattr(self.catalog_repository, "source_name", self.catalog_repository.__class__.__name__),
            "source_load_success": bool(catalog_source_snapshot.get("source_load_success", True)),
            "source_path": catalog_source_snapshot.get("source_path"),
            "requested_store_id": str(requirements.get("store_id") or ""),
            "applied_store_id": str(catalog_source_snapshot.get("requested_store_id") or ""),
            "store_scope_applied": bool(store_scope_applied),
            "requested_currency": str(requirements.get("currency") or ""),
            "matched_product_count": int(catalog_source_snapshot.get("matched_product_count") or len(raw_products)),
            "normalized_candidate_count": len(normalized_products),
            "unmatched_inventory_count": int(catalog_source_snapshot.get("unmatched_inventory_count") or 0),
            "readiness_state_counts": readiness_state_counts,
            "parse_warning_count": parse_warning_count,
            "currency_fallback_count": 1 if currency_fallback_used else 0,
            "currency_fallback_used": bool(currency_fallback_used),
            "provisional_count": provisional_count,
            "store_filter_miss": bool(
                store_scope_applied
                and (
                    catalog_source_snapshot.get("store_filter_miss")
                    or (requirements.get("store_id") and not raw_products)
                )
            ),
            "validation_block_count": len(catalog_validation_result.get("rejected_products") or []),
        }

    def _aggregate_catalog_observability(self, recommendation_groups):
        recommendation_groups = list(recommendation_groups or [])
        readiness_state_counts = {}
        source_names = []
        source_paths = []
        total_unmatched_inventory = 0
        total_normalized_candidate_count = 0
        total_parse_warning_count = 0
        total_currency_fallback_count = 0
        total_provisional_count = 0
        total_validation_block_count = 0
        any_store_filter_miss = False
        any_store_scope_applied = False
        all_load_success = True
        for group in recommendation_groups:
            group_observability = dict((group.get("meta") or {}).get("catalog_observability") or {})
            if not group_observability:
                continue
            source_name = group_observability.get("source_name")
            source_path = group_observability.get("source_path")
            if source_name and source_name not in source_names:
                source_names.append(source_name)
            if source_path and source_path not in source_paths:
                source_paths.append(source_path)
            for readiness_state, count in dict(group_observability.get("readiness_state_counts") or {}).items():
                readiness_state_counts[readiness_state] = readiness_state_counts.get(readiness_state, 0) + int(count or 0)
            total_unmatched_inventory += int(group_observability.get("unmatched_inventory_count") or 0)
            total_normalized_candidate_count += int(group_observability.get("normalized_candidate_count") or 0)
            total_parse_warning_count += int(group_observability.get("parse_warning_count") or 0)
            total_currency_fallback_count += int(group_observability.get("currency_fallback_count") or 0)
            total_provisional_count += int(group_observability.get("provisional_count") or 0)
            total_validation_block_count += int(group_observability.get("validation_block_count") or 0)
            any_store_filter_miss = any_store_filter_miss or bool(group_observability.get("store_filter_miss"))
            any_store_scope_applied = any_store_scope_applied or bool(group_observability.get("store_scope_applied"))
            all_load_success = all_load_success and bool(group_observability.get("source_load_success", True))
        return {
            "source_names": source_names,
            "source_paths": source_paths,
            "source_load_success": all_load_success,
            "unmatched_inventory_count": total_unmatched_inventory,
            "normalized_candidate_count": total_normalized_candidate_count,
            "readiness_state_counts": readiness_state_counts,
            "parse_warning_count": total_parse_warning_count,
            "currency_fallback_count": total_currency_fallback_count,
            "currency_fallback_used": bool(total_currency_fallback_count),
            "provisional_count": total_provisional_count,
            "store_scope_applied": any_store_scope_applied,
            "store_filter_miss": any_store_filter_miss,
            "validation_block_count": total_validation_block_count,
        }

    def _compatibility_bypass(self, normalized_products):
        products = list(normalized_products or [])
        return {
            "eligible_products": products,
            "rejected_products": [],
            "reports_by_product_id": {},
            "summary": {
                "compatibility_scope": "item",
                "evaluated_count": len(products),
                "eligible_count": len(products),
                "rejected_count": 0,
                "skipped_by_flag": True,
            },
        }

    def _expert_review_reason(self, readiness, ranking_deferred, fallback_reason, compatibility_result, recommendations):
        if ranking_deferred:
            return "low_confidence_clarification_required"
        if fallback_reason in {"compatibility_blocked_all", "policy_rejected_all", "no_exact_fit"}:
            return fallback_reason
        if (readiness or {}).get("decision_confidence_band") == "low":
            return "low_confidence_routing"
        if compatibility_result.get("rejected_products") and not recommendations:
            return "hard_conflict_detected"
        return ""

    def _clarification_required_reasons(self, readiness):
        readiness = dict(readiness or {})
        question_candidates = list(readiness.get("question_candidates") or [])
        threshold = self.clarification_service.question_impact_threshold()
        reasons = [
            str(item.get("key") or "").strip()
            for item in question_candidates
            if str(item.get("key") or "").strip() and float(item.get("impact") or 0.0) >= threshold
        ]
        if reasons:
            return self._dedupe_strings(reasons)

        critical_missing = [
            signal
            for signal in list(readiness.get("missing_signals") or [])
            if signal in self._hard_critical_signals()
        ]
        if critical_missing:
            return self._dedupe_strings(critical_missing)
        return []

    def _recommendation_mode(
        self,
        readiness,
        recommendations,
        fallback_reason,
        expert_review_reason,
        clarification_required_reasons,
        candidate_pool_size=0,
    ):
        readiness = dict(readiness or {})
        recommendations = list(recommendations or [])
        clarification_required_reasons = list(clarification_required_reasons or [])
        mode_policy = self.config_service.get_recommendation_mode_policy()
        expert_review_fallback_reasons = set(mode_policy.get("expert_review_fallback_reasons") or [])
        minimum_safe_candidate_count = int(mode_policy.get("minimum_safe_candidate_count") or 0)
        max_hard_critical_for_clarification = int(
            mode_policy.get("max_hard_critical_reasons_for_clarification") or 0
        )
        max_hard_critical_for_provisional = int(
            mode_policy.get("max_hard_critical_reasons_for_provisional") or 0
        )
        hard_critical_reasons = self._hard_critical_reasons(readiness, clarification_required_reasons)
        ranking_deferred = self.clarification_service.should_defer_ranking(readiness)
        insufficient_candidates = minimum_safe_candidate_count > 0 and int(candidate_pool_size or 0) < minimum_safe_candidate_count

        if not recommendations:
            if fallback_reason in expert_review_fallback_reasons:
                return "expert_review_recommended"
            if insufficient_candidates:
                return "expert_review_recommended"
            if ranking_deferred:
                return (
                    "clarification_required"
                    if clarification_required_reasons and len(hard_critical_reasons) <= max_hard_critical_for_clarification
                    else "expert_review_recommended"
                )
            if expert_review_reason:
                return "expert_review_recommended"
            return (
                "clarification_required"
                if clarification_required_reasons and len(hard_critical_reasons) <= max_hard_critical_for_clarification
                else "expert_review_recommended"
            )

        if clarification_required_reasons:
            if insufficient_candidates:
                return "expert_review_recommended"
            if len(hard_critical_reasons) > max_hard_critical_for_provisional:
                return "expert_review_recommended"
            return "provisional_recommendation"
        if expert_review_reason or insufficient_candidates:
            return "expert_review_recommended"
        return "firm_recommendation"

    def _build_decision_trace(
        self,
        decision_trace_id,
        requirements,
        extracted_schema,
        target_profile,
        readiness,
        retrieval_result,
        catalog_validation_result,
        compatibility_result,
        policy_result,
        recommendations,
        fallback_reason,
        recommendation_mode,
        clarification_required_reasons,
        expert_review_reason,
        feature_flags,
        decision_policy_profile,
        check_requirement_summary,
        editable_inferred_values,
        template_candidates,
        selected_template,
    ):
        return {
            "decision_trace_id": decision_trace_id,
            
            "catalog_validation": {
                "summary": catalog_validation_result.get("summary") or {},
                "rejected_products": catalog_validation_result.get("rejected_products") or [],
            },
            "retrieval": retrieval_result,
            "compatibility": {
                "scope": (compatibility_result.get("summary") or {}).get("compatibility_scope") or "item",
                "summary": compatibility_result.get("summary") or {},
                "rejected_products": compatibility_result.get("rejected_products") or [],
            },
            "policy": {
                "summary": policy_result.get("summary") or {},
                "rejected_products": policy_result.get("rejected_products") or [],
            },
            "expert_review_reason": expert_review_reason,
            "feature_flags": feature_flags,
            "config_versions": self.config_service.get_versions(),
        }

    def _hard_critical_signals(self):
        signals = self.config_service.get_recommendation_mode_policy().get("hard_critical_signals") or []
        return set(self._dedupe_strings(signals))

    def _hard_critical_reasons(self, readiness, clarification_required_reasons):
        hard_critical_signals = self._hard_critical_signals()
        return self._dedupe_strings(
            [
                reason
                for reason in (clarification_required_reasons or []) + list((readiness or {}).get("missing_signals") or [])
                if reason in hard_critical_signals
            ]
        )

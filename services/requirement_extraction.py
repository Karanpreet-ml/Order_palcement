# import json
# import re
# from difflib import get_close_matches
# from time import perf_counter

# from ..serializers import ExtractedRequirementSerializer
# from .clarification import ProcurementClarificationService
# from .config_service import ProcurementConfigService
# from .intake import RequirementIntakeService
# from .input_normalization import (
#     normalize_availability_need,
#     normalize_optional_bool,
#     normalize_purchase_scope,
#     normalize_replacement_mode,
#     normalize_rollout_type,
# )
# from .llm_client import OptionalLLMClient
# from .signal_service import ProcurementSignalService
# from ...catalog.services.normalization import (
#     get_procurement_normalization_terms,
#     normalize_budget_scope,
#     normalize_category,
#     normalize_color_output,
#     normalize_paper_sizes,
#     normalize_text_list,
#     normalize_virtualization_platforms,
#     normalize_warranty_type,
#     normalize_workloads,
#     parse_money_value,
#     parse_page_volume,
#     parse_port_count,
#     parse_power_watts,
#     parse_ram_gb,
#     parse_print_speed_ppm,
#     parse_rack_units,
#     parse_screen_size_inches_value,
#     parse_storage_gb,
#     parse_team_size,
#     parse_throughput_mbps,
#     parse_vpn_user_capacity,
#     parse_weight_kg_value,
# )


# SCHEMA_KEYS = [
#     "raw_chat",
#     "company_size",
#     "industry",
#     "business_type",
#     "team_size",
#     "workload_types",
#     "application_signals",
#     "capability_tags",
#     "budget",
#     "budget_scope",
#     "growth_expectation",
#     "existing_infrastructure",
#     "preferred_category",
#     "preferred_manufacturers",
#     "blocked_manufacturers",
#     "preferred_sellers",
#     "blocked_sellers",
#     "performance_priority",
#     "portability_need",
#     "support_expectation",
#     "availability_need",
#     "require_returnable",
#     "quantity",
#     "purchase_scope",
#     "rollout_type",
#     "replacement_mode",
#     "timeline",
#     "requested_ram",
#     "requested_storage",
#     "requested_ram_is_minimum",
#     "requested_storage_is_minimum",
#     "minimum_warranty_years",
#     "required_port_count",
#     "required_throughput_mbps",
#     "required_duplex_printing",
#     "required_scanner",
#     "min_print_speed_ppm",
#     "required_printer_type",
#     "required_print_technology",
#     "required_color_output",
#     "min_monthly_duty_cycle_pages",
#     "required_automatic_document_feeder",
#     "required_paper_sizes",
#     "required_network_roles",
#     "required_vpn_user_capacity",
#     "required_virtualization_ready",
#     "required_virtualization_platforms",
#     "max_rack_units",
#     "max_power_draw_watts",
#     "battery_life_hours_min",
#     "cpu_preference",
#     "gpu_requirement",
#     "screen_size_preference",
#     "weight_kg_max",
#     "warranty_type_preference",
#     "notes",
#     "missing_fields",
#     "intake_confidence",
# ]

# FAST_SCHEMA_KEYS = [
#     "industry",
#     "business_type",
#     "workload_types",
#     "application_signals",
#     "capability_tags",
#     "growth_expectation",
#     "existing_infrastructure",
#     "preferred_category",
#     "preferred_manufacturers",
#     "blocked_manufacturers",
#     "preferred_sellers",
#     "blocked_sellers",
#     "performance_priority",
#     "portability_need",
#     "support_expectation",
#     "availability_need",
#     "require_returnable",
#     "rollout_type",
#     "replacement_mode",
#     "timeline",
# ]

# KNOWN_MANUFACTURERS = [
#     "Dell",
#     "Lenovo",
#     "HP",
#     "HPE",
#     "Cisco",
#     "Fortinet",
#     "Acer",
#     "Asus",
#     "Aruba",
#     "TP-Link",
# ]

# KNOWN_SELLERS = [
#     "TechPay Official",
#     "TechPay Partner One",
#     "TechPay Partner Two",
#     "TechPay Alpha",
# ]


# def _parse_warranty_years_value(value):
#     if value is None or value == "":
#         return None
#     if isinstance(value, (int, float)):
#         return int(value)
#     text = str(value).strip().lower()
#     match = re.search(r"(\d+)\s*(?:year|yr)", text)
#     if match:
#         return int(match.group(1))
#     digits = re.findall(r"\d+", text)
#     return int(digits[0]) if digits else None


# def _parse_intake_integer(value):
#     if value is None or value == "":
#         return None
#     if isinstance(value, (int, float)):
#         return int(value)
#     digits = re.findall(r"\d+", str(value))
#     return int(digits[0]) if digits else None

# class RequirementExtractionService:
#     CRITICAL_FIELDS = ["preferred_category", "workload_types", "budget"]
#     DEEP_COMPLEXITY_THRESHOLD = 3
#     FAST_PATH_MAX_TOKENS = 512
#     DEEP_PATH_MAX_TOKENS = 1024
#     EXTRACTION_REASONING_EFFORT = "low"

#     def __init__(self, llm_client=None, config_service=None, signal_service=None):
#         self.llm_client = llm_client or OptionalLLMClient()
#         self.config_service = config_service or ProcurementConfigService()
#         self.signal_service = signal_service or ProcurementSignalService(config_service=self.config_service)
#         self.intake_service = RequirementIntakeService(signal_service=self.signal_service)
#         self.clarification_service = ProcurementClarificationService(config_service=self.config_service)
#         self.last_timing = {}


# class ProcurementSchemaExtractor(RequirementExtractionService):
#     """Compatibility alias for fallback and raw-chat extraction use cases."""

#     def extract(self, chat_text="", context=None):
#         context = dict(context or {})
#         chat_text = str(chat_text or "").strip()
#         timings = {}

#         started_at = perf_counter()
#         fast_path_result = self._try_direct_reply_fastpath(chat_text, context)
#         if fast_path_result is not None:
#             merged = {**context, **fast_path_result}
#             merged["raw_chat"] = self._merge_raw_chat(context.get("raw_chat", ""), chat_text)
#             merged["missing_fields"] = self._compute_missing_fields(merged)
#             merged["intake_confidence"] = self._estimate_confidence(merged, False)
#             serializer = ExtractedRequirementSerializer(data=merged)
#             serializer.is_valid(raise_exception=True)
#             validated = dict(serializer.validated_data)
#             validated["field_source_hints"] = self._build_field_source_hints(
#                 validated,
#                 context=context,
#                 deterministic_payload=fast_path_result,
#                 deterministic_field_sources={key: "direct_reply_fastpath" for key in fast_path_result.keys()},
#                 llm_payload={},
#             )
#             timings["direct_reply_fastpath_ms"] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)
#             timings["total_ms"] = round(sum(timings.values()), 2)
#             self.last_timing = {
#                 **timings,
#                 "llm_prompt_name": "",
#                 "llm_prompt_mode": "direct_reply_fastpath",
#                 "llm_route_reasons": ["direct_reply_fastpath"],
#                 "llm_schema_key_count": 0,
#                 "llm_request_options": {},
#                 "llm_skipped": True,
#             }
#             return validated

#         started_at = perf_counter()
#         deterministic, deterministic_field_sources = self._deterministic_extract(chat_text, context=context)
#         timings["deterministic_extract_ms"] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)
#         llm_skipped = self._should_skip_llm_for_clarification_turn(chat_text, context, deterministic)
#         llm_raw_payload = None
#         if llm_skipped:
#             timings["llm_extract_ms"] = 0.0
#             self.last_timing = {
#                 "llm_prompt_name": "",
#                 "llm_prompt_mode": "skipped",
#                 "llm_route_reasons": ["clarification_only_turn"],
#                 "llm_schema_key_count": 0,
#                 "llm_request_options": {},
#                 "llm_skipped": True,
#             }
#         else:
#             started_at = perf_counter()
#             llm_raw_payload = self._llm_extract(chat_text, context=context)
#             timings["llm_extract_ms"] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)
#             self.last_timing["llm_skipped"] = False
#         llm_route_metadata = {
#             "llm_prompt_name": self.last_timing.get("llm_prompt_name"),
#             "llm_prompt_mode": self.last_timing.get("llm_prompt_mode"),
#             "llm_route_reasons": list(self.last_timing.get("llm_route_reasons") or []),
#             "llm_schema_key_count": self.last_timing.get("llm_schema_key_count"),
#             "llm_request_options": dict(self.last_timing.get("llm_request_options") or {}),
#             "llm_skipped": bool(self.last_timing.get("llm_skipped")),
#         }

#         started_at = perf_counter()
#         llm_payload = self._sanitize_llm_payload(
#             llm_raw_payload,
#             chat_text=chat_text,
#             context=context,
#             deterministic_payload=deterministic,
#         )
#         timings["sanitize_llm_payload_ms"] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)

#         started_at = perf_counter()
#         merged = self._merge_payloads(context, llm_payload or {}, deterministic)
#         merged = self._canonicalize_payload(
#             merged,
#             chat_text=chat_text,
#             context=context,
#             deterministic_payload=deterministic,
#         )
#         merged["raw_chat"] = self._merge_raw_chat(context.get("raw_chat", ""), chat_text)
#         merged["missing_fields"] = self._compute_missing_fields(merged)
#         merged["intake_confidence"] = self._estimate_confidence(merged, bool(llm_payload))
#         field_source_hints = self._build_field_source_hints(
#             merged,
#             context=context,
#             deterministic_payload=deterministic,
#             deterministic_field_sources=deterministic_field_sources,
#             llm_payload=llm_payload or {},
#         )
#         timings["merge_and_enrich_ms"] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)

#         started_at = perf_counter()
#         serializer = ExtractedRequirementSerializer(data=merged)
#         if serializer.is_valid():
#             validated = dict(serializer.validated_data)
#             validated["field_source_hints"] = field_source_hints
#             timings["serializer_ms"] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)
#             timings["total_ms"] = round(sum(timings.values()), 2)
#             self.last_timing = {**timings, **llm_route_metadata}
#             return validated

#         timings["serializer_ms"] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)

#         started_at = perf_counter()
#         fallback = self._merge_payloads(context, {}, deterministic)
#         fallback["raw_chat"] = merged["raw_chat"]
#         fallback["missing_fields"] = self._compute_missing_fields(fallback)
#         fallback["intake_confidence"] = self._estimate_confidence(fallback, False)
#         serializer = ExtractedRequirementSerializer(data=fallback)
#         serializer.is_valid(raise_exception=True)
#         validated = dict(serializer.validated_data)
#         validated["field_source_hints"] = self._build_field_source_hints(
#             validated,
#             context=context,
#             deterministic_payload=deterministic,
#             deterministic_field_sources=deterministic_field_sources,
#             llm_payload={},
#         )
#         timings["fallback_serializer_ms"] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)
#         timings["total_ms"] = round(sum(timings.values()), 2)
#         self.last_timing = {**timings, **llm_route_metadata}
#         return validated

#     def build_procurement_payload(self, extracted_schema, base_payload=None):
#         extracted_schema = dict(extracted_schema or {})
#         base_payload = dict(base_payload or {})
#         payload = dict(base_payload)
#         base_field_source_hints = dict(base_payload.get("_field_source_hints") or {})
#         field_source_hints = {
#             **base_field_source_hints,
#             **dict(extracted_schema.get("field_source_hints") or {}),
#         }
#         explicit_payload_fields = set(base_payload.get("_explicit_payload_fields") or [])
#         if explicit_payload_fields:
#             payload["_explicit_payload_fields"] = sorted(
#                 key
#                 for key in explicit_payload_fields
#                 if key != "extracted_schema" and self._value_present(base_payload.get(key))
#             )
#         else:
#             payload["_explicit_payload_fields"] = sorted(
#                 key
#                 for key, value in base_payload.items()
#                 if key != "extracted_schema" and self._value_present(value)
#             )

#         preferred_category = extracted_schema.get("preferred_category")
#         if preferred_category and not payload.get("category") and not payload.get("preferred_category"):
#             payload["category"] = preferred_category

#         if extracted_schema.get("industry") and not payload.get("industry"):
#             payload["industry"] = extracted_schema["industry"]
#         if extracted_schema.get("business_type") and not payload.get("business_type"):
#             payload["business_type"] = extracted_schema["business_type"]
#         if extracted_schema.get("team_size") and not payload.get("team_size"):
#             payload["team_size"] = extracted_schema["team_size"]
#         if extracted_schema.get("workload_types") and not (payload.get("workload_types") or payload.get("workloads")):
#             payload["workload_types"] = extracted_schema["workload_types"]
#         if extracted_schema.get("application_signals") and not payload.get("application_signals"):
#             payload["application_signals"] = extracted_schema["application_signals"]
#         if extracted_schema.get("capability_tags") and not payload.get("capability_tags"):
#             payload["capability_tags"] = extracted_schema["capability_tags"]
#         if extracted_schema.get("budget") is not None and payload.get("budget") is None:
#             payload["budget"] = extracted_schema["budget"]
#         if extracted_schema.get("budget_scope") and not payload.get("budget_scope"):
#             payload["budget_scope"] = extracted_schema["budget_scope"]
#         if extracted_schema.get("growth_expectation") and not payload.get("growth_expectation"):
#             payload["growth_expectation"] = extracted_schema["growth_expectation"]
#         if extracted_schema.get("existing_infrastructure") and not payload.get("existing_infrastructure"):
#             payload["existing_infrastructure"] = extracted_schema["existing_infrastructure"]
#         if extracted_schema.get("preferred_manufacturers") and not payload.get("preferred_manufacturers"):
#             payload["preferred_manufacturers"] = extracted_schema["preferred_manufacturers"]
#         if extracted_schema.get("blocked_manufacturers") and not payload.get("blocked_manufacturers"):
#             payload["blocked_manufacturers"] = extracted_schema["blocked_manufacturers"]
#         if extracted_schema.get("preferred_sellers") and not payload.get("preferred_sellers"):
#             payload["preferred_sellers"] = extracted_schema["preferred_sellers"]
#         if extracted_schema.get("blocked_sellers") and not payload.get("blocked_sellers"):
#             payload["blocked_sellers"] = extracted_schema["blocked_sellers"]
#         if extracted_schema.get("requested_ram") and not (
#             payload.get("requested_ram") or payload.get("specifications.ram_size")
#         ):
#             payload["requested_ram"] = extracted_schema["requested_ram"]
#         if extracted_schema.get("requested_storage") and not (
#             payload.get("requested_storage") or payload.get("specifications.storage_size")
#         ):
#             payload["requested_storage"] = extracted_schema["requested_storage"]
#         if extracted_schema.get("requested_ram_is_minimum") is not None and payload.get("requested_ram_is_minimum") is None:
#             payload["requested_ram_is_minimum"] = extracted_schema["requested_ram_is_minimum"]
#         if extracted_schema.get("requested_storage_is_minimum") is not None and payload.get("requested_storage_is_minimum") is None:
#             payload["requested_storage_is_minimum"] = extracted_schema["requested_storage_is_minimum"]
#         if extracted_schema.get("minimum_warranty_years") is not None and payload.get("minimum_warranty_years") is None:
#             payload["minimum_warranty_years"] = extracted_schema["minimum_warranty_years"]
#         if extracted_schema.get("required_port_count") is not None and payload.get("required_port_count") is None:
#             payload["required_port_count"] = extracted_schema["required_port_count"]
#         if extracted_schema.get("required_throughput_mbps") is not None and payload.get("required_throughput_mbps") is None:
#             payload["required_throughput_mbps"] = extracted_schema["required_throughput_mbps"]
#         if extracted_schema.get("required_duplex_printing") is not None and payload.get("required_duplex_printing") is None:
#             payload["required_duplex_printing"] = extracted_schema["required_duplex_printing"]
#         if extracted_schema.get("required_scanner") is not None and payload.get("required_scanner") is None:
#             payload["required_scanner"] = extracted_schema["required_scanner"]
#         if extracted_schema.get("min_print_speed_ppm") is not None and payload.get("min_print_speed_ppm") is None:
#             payload["min_print_speed_ppm"] = extracted_schema["min_print_speed_ppm"]
#         if extracted_schema.get("required_printer_type") and not payload.get("required_printer_type"):
#             payload["required_printer_type"] = extracted_schema["required_printer_type"]
#         if extracted_schema.get("required_print_technology") and not payload.get("required_print_technology"):
#             payload["required_print_technology"] = extracted_schema["required_print_technology"]
#         if extracted_schema.get("required_color_output") and not payload.get("required_color_output"):
#             payload["required_color_output"] = extracted_schema["required_color_output"]
#         if extracted_schema.get("min_monthly_duty_cycle_pages") is not None and payload.get("min_monthly_duty_cycle_pages") is None:
#             payload["min_monthly_duty_cycle_pages"] = extracted_schema["min_monthly_duty_cycle_pages"]
#         if extracted_schema.get("required_automatic_document_feeder") is not None and payload.get("required_automatic_document_feeder") is None:
#             payload["required_automatic_document_feeder"] = extracted_schema["required_automatic_document_feeder"]
#         if extracted_schema.get("required_paper_sizes") and not payload.get("required_paper_sizes"):
#             payload["required_paper_sizes"] = extracted_schema["required_paper_sizes"]
#         if extracted_schema.get("required_network_roles") and not payload.get("required_network_roles"):
#             payload["required_network_roles"] = extracted_schema["required_network_roles"]
#         if extracted_schema.get("required_vpn_user_capacity") is not None and payload.get("required_vpn_user_capacity") is None:
#             payload["required_vpn_user_capacity"] = extracted_schema["required_vpn_user_capacity"]
#         if extracted_schema.get("required_virtualization_ready") is not None and payload.get("required_virtualization_ready") is None:
#             payload["required_virtualization_ready"] = extracted_schema["required_virtualization_ready"]
#         if extracted_schema.get("required_virtualization_platforms") and not payload.get("required_virtualization_platforms"):
#             payload["required_virtualization_platforms"] = extracted_schema["required_virtualization_platforms"]
#         if extracted_schema.get("max_rack_units") is not None and payload.get("max_rack_units") is None:
#             payload["max_rack_units"] = extracted_schema["max_rack_units"]
#         if extracted_schema.get("max_power_draw_watts") is not None and payload.get("max_power_draw_watts") is None:
#             payload["max_power_draw_watts"] = extracted_schema["max_power_draw_watts"]
#         if extracted_schema.get("battery_life_hours_min") is not None and payload.get("battery_life_hours_min") is None:
#             payload["battery_life_hours_min"] = extracted_schema["battery_life_hours_min"]
#         if extracted_schema.get("cpu_preference") and not payload.get("cpu_preference"):
#             payload["cpu_preference"] = extracted_schema["cpu_preference"]
#         if extracted_schema.get("gpu_requirement") and not payload.get("gpu_requirement"):
#             payload["gpu_requirement"] = extracted_schema["gpu_requirement"]
#         if extracted_schema.get("screen_size_preference") and not payload.get("screen_size_preference"):
#             payload["screen_size_preference"] = extracted_schema["screen_size_preference"]
#         if extracted_schema.get("weight_kg_max") is not None and payload.get("weight_kg_max") is None:
#             payload["weight_kg_max"] = extracted_schema["weight_kg_max"]
#         if extracted_schema.get("warranty_type_preference") and not payload.get("warranty_type_preference"):
#             payload["warranty_type_preference"] = extracted_schema["warranty_type_preference"]
#         if extracted_schema.get("performance_priority") and not payload.get("performance_priority"):
#             payload["performance_priority"] = extracted_schema["performance_priority"]
#         if extracted_schema.get("portability_need") and not payload.get("portability_need"):
#             payload["portability_need"] = extracted_schema["portability_need"]
#         if extracted_schema.get("support_expectation") and not payload.get("support_expectation"):
#             payload["support_expectation"] = extracted_schema["support_expectation"]
#         if extracted_schema.get("availability_need") and not payload.get("availability_need"):
#             payload["availability_need"] = extracted_schema["availability_need"]
#         if extracted_schema.get("require_returnable") is not None and payload.get("require_returnable") is None:
#             payload["require_returnable"] = extracted_schema["require_returnable"]
#         if extracted_schema.get("quantity") and not payload.get("quantity"):
#             payload["quantity"] = extracted_schema["quantity"]
#         if extracted_schema.get("purchase_scope") and not payload.get("purchase_scope"):
#             payload["purchase_scope"] = extracted_schema["purchase_scope"]
#         if extracted_schema.get("rollout_type") and not payload.get("rollout_type"):
#             payload["rollout_type"] = extracted_schema["rollout_type"]
#         if extracted_schema.get("replacement_mode") and not payload.get("replacement_mode"):
#             payload["replacement_mode"] = extracted_schema["replacement_mode"]
#         if extracted_schema.get("timeline") and not payload.get("timeline"):
#             payload["timeline"] = extracted_schema["timeline"]

#         existing_notes = str(payload.get("notes") or "").strip()
#         extracted_notes = str(extracted_schema.get("notes") or "").strip()
#         combined_notes = self._merge_text_fragments(existing_notes, extracted_notes, separator=" ")
#         if combined_notes:
#             payload["notes"] = combined_notes

#         payload["chat_text"] = extracted_schema.get("raw_chat", "")
#         payload["budget_scope"] = payload.get("budget_scope") or normalize_budget_scope(
#             payload.get("budget_scope"),
#             preferred_categories=[preferred_category] if preferred_category else [],
#             hint_text=payload.get("chat_text") or extracted_schema.get("notes") or "",
#             quantity=payload.get("quantity") or extracted_schema.get("quantity"),
#         )
#         payload["_field_source_hints"] = field_source_hints
#         return payload

#     def _llm_extract(self, chat_text, context):
#         if not chat_text:
#             return None

#         prompt_name, prompt_mode, route_reasons = self._select_extraction_prompt(chat_text, context=context)
#         schema_keys = self._schema_keys_for_prompt_mode(prompt_mode)
#         request_options = self._request_options_for_prompt_mode(prompt_mode)
#         variables = {
#             "known_context": json.dumps(context, ensure_ascii=True),
#             "chat_text": chat_text,
#             "schema_keys": json.dumps(schema_keys, ensure_ascii=True),
#         }
#         payload = self.llm_client.invoke_json(
#             prompt_name,
#             variables,
#             request_options=request_options,
#         )
#         self.last_timing = {
#             **dict(self.last_timing or {}),
#             "llm_prompt_name": prompt_name,
#             "llm_prompt_mode": prompt_mode,
#             "llm_route_reasons": list(route_reasons),
#             "llm_schema_key_count": len(schema_keys),
#             "llm_request_options": dict(request_options),
#         }
#         return payload if isinstance(payload, dict) else None

#     def _schema_keys_for_prompt_mode(self, prompt_mode):
#         if str(prompt_mode or "").strip().lower() == "fast":
#             return list(FAST_SCHEMA_KEYS)
#         return list(SCHEMA_KEYS)

#     def _request_options_for_prompt_mode(self, prompt_mode):
#         prompt_mode = str(prompt_mode or "").strip().lower()
#         return {
#             "reasoning_effort": self.EXTRACTION_REASONING_EFFORT,
#             "timeout_sec": OptionalLLMClient.EXTRACTION_TIMEOUT_SEC,
#             "max_tokens": self.FAST_PATH_MAX_TOKENS if prompt_mode == "fast" else self.DEEP_PATH_MAX_TOKENS,
#         }

#     def _select_extraction_prompt(self, chat_text, context=None):
#         chat_text = str(chat_text or "").strip()
#         context = dict(context or {})
#         lowered = chat_text.lower()
#         words = re.findall(r"\b\w+\b", lowered)
#         complexity = 0
#         reasons = []

#         category_hits = sum(
#             1 for pattern in ("laptop", "desktop", "server", "printer", "firewall", "switch", "router", "access point")
#             if pattern in lowered
#         )
#         multi_track_markers = (
#             " and also ",
#             " plus ",
#             " while ",
#             " along with ",
#             " as well as ",
#         )
#         ambiguity_markers = (
#             "not sure",
#             "maybe",
#             "something like",
#             "sort of",
#             "kind of",
#             "same as before",
#             "same as last time",
#             "that one",
#             "those ones",
#         )

#         if len(words) >= 35 or len(chat_text) >= 220:
#             complexity += 1
#             reasons.append("long_message")
#         if category_hits >= 2:
#             complexity += 2
#             reasons.append("multi_category_signals")
#         if sum(1 for marker in multi_track_markers if marker in lowered) >= 1:
#             complexity += 1
#             reasons.append("multi_track_language")
#         if chat_text.count(",") >= 3:
#             complexity += 1
#             reasons.append("many_clauses")
#         if any(marker in lowered for marker in ambiguity_markers):
#             complexity += 1
#             reasons.append("ambiguous_language")
#         if context and len(words) <= 8 and not self._looks_like_direct_value_reply(lowered):
#             complexity += 1
#             reasons.append("short_contextual_followup")

#         if complexity >= self.DEEP_COMPLEXITY_THRESHOLD:
#             return "requirement_extraction.txt", "deep", reasons
#         return "requirement_extraction_fast.txt", "fast", reasons or ["simple_message"]

#     def _looks_like_direct_value_reply(self, lowered):
#         lowered = str(lowered or "").lower()
#         if self._detect_budget_from_chat(lowered) is not None:
#             return True
#         if parse_team_size(lowered) is not None:
#             return True
#         if normalize_category(lowered):
#             return True
#         if normalize_workloads(lowered):
#             return True
#         direct_markers = (
#             "under ",
#             "budget",
#             "users",
#             "people",
#             "staff",
#             "developers",
#             "designers",
#             "laptops",
#             "desktops",
#             "servers",
#             "printers",
#             "networking",
#         )
#         return any(marker in lowered for marker in direct_markers)

#     def _try_direct_reply_fastpath(self, chat_text, context):
#         chat_text = str(chat_text or "").strip()
#         if not chat_text:
#             return None

#         lowered = chat_text.lower()
#         last_field = str(context.get("_last_asked_field") or "").strip().lower()

#         if last_field == "team_size":
#             parsed = parse_team_size(chat_text)
#             if parsed and len(chat_text.split()) <= 3:
#                 return {"team_size": parsed, "quantity": parsed}

#         budget = self._detect_budget_from_chat(chat_text)
#         if budget is not None and len(chat_text.split()) <= 5:
#             result = {"budget": budget}
#             budget_scope = self._detect_explicit_budget_scope(chat_text)
#             if budget_scope:
#                 result["budget_scope"] = budget_scope
#             return result

#         direct_budget = self._parse_direct_budget_value(chat_text)
#         explicit_budget_markers = (
#             "budget",
#             "rs",
#             "inr",
#             "usd",
#             "eur",
#             "gbp",
#             "myr",
#             "$",
#             "k",
#             "lakh",
#             "thousand",
#             "each",
#             "per unit",
#             "per device",
#             "per seat",
#             "total",
#             "overall",
#             "project",
#             "combined",
#         )
#         budget_word_limit = 8 if last_field in {"budget", "budget_scope"} else 5
#         if (
#             direct_budget is not None
#             and len(chat_text.split()) <= budget_word_limit
#             and any(marker in lowered for marker in explicit_budget_markers)
#         ):
#             result = {"budget": direct_budget}
#             budget_scope = self._detect_explicit_budget_scope(chat_text)
#             if budget_scope:
#                 result["budget_scope"] = budget_scope
#             return result

#         if last_field in {"budget_scope", "budget"}:
#             budget_scope = self._detect_explicit_budget_scope(chat_text)
#             if budget_scope:
#                 return {"budget_scope": budget_scope}

#         if last_field in {"preferred_category", "category_or_workload"}:
#             category = self._normalize_direct_reply_category(chat_text)
#             if category:
#                 return {"preferred_category": category}

#         if last_field == "performance_priority" and lowered in {"cost", "balanced", "performance"}:
#             return {"performance_priority": lowered}

#         return None

#     def _detect_explicit_budget_scope(self, chat_text):
#         lowered = str(chat_text or "").strip().lower()
#         if not lowered:
#             return None

#         total_markers = ("total", "overall", "project", "combined")
#         per_unit_markers = ("each", "per unit", "per device", "per seat")
#         if any(marker in lowered for marker in total_markers):
#             return "project_total"
#         if any(marker in lowered for marker in per_unit_markers):
#             return "per_unit"
#         return None

#     def _parse_direct_budget_value(self, chat_text):
#         chat_text = str(chat_text or "").strip()
#         if not chat_text:
#             return None

#         parsed = parse_money_value(chat_text)
#         if parsed is not None:
#             return parsed

#         money_match = re.search(
#             r"(\d[\d,]*(?:\.\d+)?(?:\s?(?:k|lakh|thousand|thousands))?)",
#             chat_text.lower(),
#         )
#         if not money_match:
#             return None
#         return parse_money_value(money_match.group(1))

#     def _normalize_direct_reply_category(self, chat_text):
#         category = normalize_category(chat_text)
#         if category:
#             return category

#         lowered = str(chat_text or "").strip().lower()
#         if not lowered:
#             return None

#         canonical_categories = [
#             "laptops",
#             "desktops",
#             "servers",
#             "networking",
#             "printers",
#             "accessories",
#         ]
#         closest = get_close_matches(lowered, canonical_categories, n=1, cutoff=0.7)
#         return closest[0] if closest else None

#     def _deterministic_extract(self, chat_text, context):
#         chat_text = str(chat_text or "").strip()
#         lowered = chat_text.lower()
#         merged_chat_text = self._merge_raw_chat(context.get("raw_chat", ""), chat_text)
#         signal_matches = self.signal_service.extract(chat_text)

#         team_size_from_chat = self._detect_team_size_from_chat(chat_text)
#         team_size = team_size_from_chat
#         if team_size is None and context and context.get("team_size"):
#             team_size = parse_team_size(context.get("team_size"))
#         preferred_category = self._detect_preferred_category(chat_text)
#         category_for_inference = preferred_category or normalize_category(context.get("preferred_category"))
#         explicit_workload_types = normalize_workloads(chat_text)
#         if self._is_generic_office_prompt(lowered):
#             explicit_workload_types = []
#         workload_types = self._merge_list_values(explicit_workload_types, signal_matches.get("workload_types"))
#         if (
#             "server_infrastructure" not in workload_types
#             and any(token in lowered for token in {"back-room compute", "back room compute", "back-room host", "back room host", "local host", "small host"})
#         ):
#             workload_types.append("server_infrastructure")
#         if (
#             "network_connectivity" not in workload_types
#             and any(token in lowered for token in {"connectivity", "secure connectivity", "site connectivity"})
#         ):
#             workload_types.append("network_connectivity")
#         workload_types = self._align_workloads_with_category(preferred_category, workload_types, lowered)
#         if self._is_generic_office_prompt(lowered):
#             workload_types = []
#         workloads_for_inference = self._merge_list_values(
#             normalize_workloads(context.get("workload_types") or context.get("workloads")),
#             workload_types,
#         )
#         budget_from_chat = self._detect_budget_from_chat(chat_text)
#         budget = budget_from_chat if budget_from_chat is not None else self._detect_budget(chat_text, context=context)
#         requested_ram = self._detect_requested_ram(chat_text)
#         requested_storage = self._detect_requested_storage(chat_text)
#         requested_ram_is_minimum = self._detect_spec_requirement_strength(lowered, "ram") if requested_ram else None
#         requested_storage_is_minimum = self._detect_spec_requirement_strength(lowered, "storage") if requested_storage else None
#         minimum_warranty_years = self._detect_minimum_warranty_years(chat_text)
#         required_port_count = self._detect_required_port_count(chat_text)
#         required_throughput_mbps = self._detect_required_throughput_mbps(chat_text)
#         required_duplex_printing = self._detect_required_duplex_printing(lowered)
#         required_scanner = self._detect_required_scanner(lowered)
#         min_print_speed_ppm = self._detect_min_print_speed_ppm(chat_text)
#         required_printer_type = self._detect_required_printer_type(lowered)
#         required_print_technology = self._detect_required_print_technology(lowered)
#         required_color_output = self._detect_required_color_output(lowered)
#         min_monthly_duty_cycle_pages = self._detect_min_monthly_duty_cycle_pages(chat_text)
#         required_automatic_document_feeder = self._detect_required_automatic_document_feeder(lowered)
#         required_paper_sizes = self._detect_required_paper_sizes(chat_text)
#         required_network_roles = self._detect_required_network_roles(lowered)
#         required_vpn_user_capacity = self._detect_required_vpn_user_capacity(chat_text)
#         required_virtualization_ready = self._detect_required_virtualization_ready(lowered)
#         required_virtualization_platforms = self._detect_required_virtualization_platforms(chat_text)
#         max_rack_units = self._detect_max_rack_units(chat_text)
#         max_power_draw_watts = self._detect_max_power_draw_watts(chat_text)
#         battery_life_hours_min = self._detect_battery_life_hours_min(chat_text)
#         cpu_preference = self._detect_cpu_preference(chat_text)
#         gpu_requirement = self._detect_gpu_requirement(chat_text)
#         screen_size_preference = self._detect_screen_size_preference(chat_text)
#         weight_kg_max = self._detect_weight_kg_max(chat_text)
#         warranty_type_preference = self._detect_warranty_type_preference(chat_text)
#         preferred_manufacturers, blocked_manufacturers = self._detect_manufacturer_preferences(chat_text)
#         preferred_sellers, blocked_sellers = self._detect_seller_preferences(chat_text)

#         industry = self._detect_industry(lowered)
#         business_type = self._detect_business_type(lowered, context=context)
#         performance_priority = self._detect_performance_priority(lowered)
#         portability_need = self._detect_portability_need(lowered)
#         support_expectation = self._detect_support_expectation(lowered)
#         availability_need = self._detect_availability_need(lowered)
#         rollout_type = self._detect_rollout_type(lowered)
#         replacement_mode = self._detect_replacement_mode(lowered)
#         timeline = self._detect_timeline(chat_text)
#         quantity, quantity_source = self._detect_quantity(
#             merged_chat_text,
#             team_size,
#             category_for_inference,
#             workloads_for_inference,
#         )
#         purchase_scope = normalize_purchase_scope(
#             None,
#             preferred_categories=[category_for_inference] if category_for_inference else [],
#             quantity=quantity,
#             team_size=team_size,
#             hint_text=merged_chat_text,
#         )
#         existing_infrastructure = self._detect_existing_infrastructure(chat_text)
#         require_returnable = self._detect_require_returnable(lowered)
#         application_signals = signal_matches.get("application_signals") or []
#         growth_expectation = self._detect_growth_expectation(lowered)
#         capability_tags = self._derive_capability_tags(
#             preferred_category=preferred_category,
#             workload_types=workload_types,
#             application_signals=application_signals,
#             signal_capability_tags=signal_matches.get("capability_tags"),
#             requested_ram=requested_ram,
#             requested_storage=requested_storage,
#             portability_need=portability_need,
#             support_expectation=support_expectation,
#             availability_need=availability_need,
#             existing_infrastructure=existing_infrastructure,
#             lowered=lowered,
#         )

#         team_size_source = "user_explicit" if team_size_from_chat is not None else None
#         if not team_size and category_for_inference in {"laptops", "desktops"} and quantity:
#             team_size = quantity
#             team_size_source = "rule_inferred"

#         company_size = self._company_size_from_team_size(team_size or context.get("team_size"))
#         business_type = business_type or ("smb" if industry else context.get("business_type"))

#         deterministic_payload = {
#             "company_size": company_size,
#             "industry": industry,
#             "business_type": business_type,
#             "team_size": team_size,
#             "workload_types": workload_types,
#             "application_signals": application_signals,
#             "capability_tags": capability_tags,
#             "budget": budget,
#             "growth_expectation": growth_expectation,
#             "existing_infrastructure": existing_infrastructure,
#             "preferred_category": preferred_category,
#             "preferred_manufacturers": preferred_manufacturers,
#             "blocked_manufacturers": blocked_manufacturers,
#             "preferred_sellers": preferred_sellers,
#             "blocked_sellers": blocked_sellers,
#             "performance_priority": performance_priority,
#             "portability_need": portability_need,
#             "support_expectation": support_expectation,
#             "availability_need": availability_need,
#             "require_returnable": require_returnable,
#             "quantity": quantity,
#             "purchase_scope": purchase_scope,
#             "rollout_type": rollout_type,
#             "replacement_mode": replacement_mode,
#             "timeline": timeline,
#             "requested_ram": f"{requested_ram}GB" if requested_ram else None,
#             "requested_storage": self._format_storage(requested_storage),
#             "requested_ram_is_minimum": requested_ram_is_minimum,
#             "requested_storage_is_minimum": requested_storage_is_minimum,
#             "minimum_warranty_years": minimum_warranty_years,
#             "required_port_count": required_port_count,
#             "required_throughput_mbps": required_throughput_mbps,
#             "required_duplex_printing": required_duplex_printing,
#             "required_scanner": required_scanner,
#             "min_print_speed_ppm": min_print_speed_ppm,
#             "required_printer_type": required_printer_type,
#             "required_print_technology": required_print_technology,
#             "required_color_output": required_color_output,
#             "min_monthly_duty_cycle_pages": min_monthly_duty_cycle_pages,
#             "required_automatic_document_feeder": required_automatic_document_feeder,
#             "required_paper_sizes": required_paper_sizes,
#             "required_network_roles": required_network_roles,
#             "required_vpn_user_capacity": required_vpn_user_capacity,
#             "required_virtualization_ready": required_virtualization_ready,
#             "required_virtualization_platforms": required_virtualization_platforms,
#             "max_rack_units": max_rack_units,
#             "max_power_draw_watts": max_power_draw_watts,
#             "battery_life_hours_min": battery_life_hours_min,
#             "cpu_preference": cpu_preference,
#             "gpu_requirement": gpu_requirement,
#             "screen_size_preference": screen_size_preference,
#             "weight_kg_max": weight_kg_max,
#             "warranty_type_preference": warranty_type_preference,
#             "notes": chat_text,
#         }
#         deterministic_field_sources = {
#             "company_size": "rule_inferred" if company_size else None,
#             "industry": "user_explicit" if industry else None,
#             "business_type": "rule_inferred" if business_type else None,
#             "team_size": team_size_source,
#             "workload_types": (
#                 "user_explicit"
#                 if explicit_workload_types
#                 else ("rule_inferred" if workload_types else None)
#             ),
#             "application_signals": "rule_inferred" if application_signals else None,
#             "capability_tags": "rule_inferred" if capability_tags else None,
#             "budget": "user_explicit" if budget_from_chat is not None else None,
#             "growth_expectation": "user_explicit" if growth_expectation else None,
#             "existing_infrastructure": "user_explicit" if existing_infrastructure else None,
#             "preferred_category": "user_explicit" if preferred_category else None,
#             "preferred_manufacturers": "user_explicit" if preferred_manufacturers else None,
#             "blocked_manufacturers": "user_explicit" if blocked_manufacturers else None,
#             "preferred_sellers": "user_explicit" if preferred_sellers else None,
#             "blocked_sellers": "user_explicit" if blocked_sellers else None,
#             "performance_priority": "user_explicit" if performance_priority else None,
#             "portability_need": "user_explicit" if portability_need else None,
#             "support_expectation": "user_explicit" if support_expectation else None,
#             "availability_need": "user_explicit" if availability_need else None,
#             "require_returnable": "user_explicit" if require_returnable is not None else None,
#             "quantity": quantity_source,
#             "purchase_scope": "rule_inferred" if purchase_scope else None,
#             "rollout_type": "user_explicit" if rollout_type else None,
#             "replacement_mode": "user_explicit" if replacement_mode else None,
#             "timeline": "user_explicit" if timeline else None,
#             "requested_ram": "user_explicit" if requested_ram else None,
#             "requested_storage": "user_explicit" if requested_storage else None,
#             "requested_ram_is_minimum": "rule_inferred" if requested_ram_is_minimum is not None else None,
#             "requested_storage_is_minimum": "rule_inferred" if requested_storage_is_minimum is not None else None,
#             "minimum_warranty_years": "user_explicit" if minimum_warranty_years is not None else None,
#             "required_port_count": "user_explicit" if required_port_count is not None else None,
#             "required_throughput_mbps": "user_explicit" if required_throughput_mbps is not None else None,
#             "required_duplex_printing": "user_explicit" if required_duplex_printing is not None else None,
#             "required_scanner": "user_explicit" if required_scanner is not None else None,
#             "min_print_speed_ppm": "user_explicit" if min_print_speed_ppm is not None else None,
#             "required_printer_type": "user_explicit" if required_printer_type else None,
#             "required_print_technology": "user_explicit" if required_print_technology else None,
#             "required_color_output": "user_explicit" if required_color_output else None,
#             "min_monthly_duty_cycle_pages": "user_explicit" if min_monthly_duty_cycle_pages is not None else None,
#             "required_automatic_document_feeder": "user_explicit" if required_automatic_document_feeder is not None else None,
#             "required_paper_sizes": "user_explicit" if required_paper_sizes else None,
#             "required_network_roles": "user_explicit" if required_network_roles else None,
#             "required_vpn_user_capacity": "user_explicit" if required_vpn_user_capacity is not None else None,
#             "required_virtualization_ready": "user_explicit" if required_virtualization_ready is not None else None,
#             "required_virtualization_platforms": "user_explicit" if required_virtualization_platforms else None,
#             "max_rack_units": "user_explicit" if max_rack_units is not None else None,
#             "max_power_draw_watts": "user_explicit" if max_power_draw_watts is not None else None,
#             "battery_life_hours_min": "user_explicit" if battery_life_hours_min is not None else None,
#             "cpu_preference": "user_explicit" if cpu_preference else None,
#             "gpu_requirement": "user_explicit" if gpu_requirement else None,
#             "screen_size_preference": "user_explicit" if screen_size_preference else None,
#             "weight_kg_max": "user_explicit" if weight_kg_max is not None else None,
#             "warranty_type_preference": "user_explicit" if warranty_type_preference else None,
#             "notes": "rule_inferred" if chat_text else None,
#         }
#         deterministic_field_sources = {
#             field: source
#             for field, source in deterministic_field_sources.items()
#             if source
#         }

#         return deterministic_payload, deterministic_field_sources

#     def _sanitize_llm_payload(self, llm_payload, chat_text, context, deterministic_payload):
#         if not isinstance(llm_payload, dict):
#             return None

#         sanitized = dict(llm_payload)
#         sanitized["preferred_category"] = normalize_category(sanitized.get("preferred_category"))
#         sanitized["workload_types"] = normalize_workloads(sanitized.get("workload_types"))
#         sanitized["application_signals"] = self.signal_service.sanitize_application_signals(
#             sanitized.get("application_signals")
#         )
#         sanitized["capability_tags"] = self.signal_service.sanitize_capability_tags(
#             sanitized.get("capability_tags")
#         )
#         sanitized["team_size"] = parse_team_size(sanitized.get("team_size"))
#         sanitized["quantity"] = parse_team_size(sanitized.get("quantity"))
#         sanitized["industry"] = self._normalize_nullable_text(sanitized.get("industry"))
#         sanitized["business_type"] = self._normalize_nullable_text(sanitized.get("business_type"))
#         sanitized["rollout_type"] = normalize_rollout_type(sanitized.get("rollout_type"))
#         sanitized["replacement_mode"] = normalize_replacement_mode(sanitized.get("replacement_mode"))
#         sanitized["timeline"] = self._normalize_nullable_text(sanitized.get("timeline"))
#         sanitized["notes"] = self._normalize_nullable_text(sanitized.get("notes"))
#         sanitized["preferred_manufacturers"] = self._sanitize_named_list(
#             sanitized.get("preferred_manufacturers"),
#             KNOWN_MANUFACTURERS,
#         )
#         sanitized["blocked_manufacturers"] = self._sanitize_named_list(
#             sanitized.get("blocked_manufacturers"),
#             KNOWN_MANUFACTURERS,
#         )
#         sanitized["preferred_sellers"] = self._sanitize_named_list(
#             sanitized.get("preferred_sellers"),
#             KNOWN_SELLERS,
#         )
#         sanitized["blocked_sellers"] = self._sanitize_named_list(
#             sanitized.get("blocked_sellers"),
#             KNOWN_SELLERS,
#         )
#         sanitized["availability_need"] = normalize_availability_need(sanitized.get("availability_need"))
#         sanitized["require_returnable"] = normalize_optional_bool(sanitized.get("require_returnable"))
#         sanitized["purchase_scope"] = normalize_purchase_scope(
#             sanitized.get("purchase_scope"),
#             preferred_categories=[sanitized.get("preferred_category")] if sanitized.get("preferred_category") else [],
#             quantity=sanitized.get("quantity"),
#             team_size=sanitized.get("team_size"),
#             hint_text=chat_text,
#         )
#         sanitized["budget"] = self._sanitize_budget_value(
#             sanitized.get("budget"),
#             chat_text=chat_text,
#             context=context,
#             team_size=sanitized.get("team_size") or deterministic_payload.get("team_size"),
#         )
#         sanitized["existing_infrastructure"] = self._merge_list_values(
#             context.get("existing_infrastructure"),
#             deterministic_payload.get("existing_infrastructure"),
#         )

#         requested_ram = parse_ram_gb(sanitized.get("requested_ram"))
#         sanitized["requested_ram"] = f"{requested_ram}GB" if requested_ram else None
#         sanitized["requested_ram_is_minimum"] = normalize_optional_bool(
#             sanitized.get("requested_ram_is_minimum")
#         )
#         requested_storage = parse_storage_gb(sanitized.get("requested_storage"))
#         sanitized["requested_storage"] = self._format_storage(requested_storage)
#         sanitized["requested_storage_is_minimum"] = normalize_optional_bool(
#             sanitized.get("requested_storage_is_minimum")
#         )
#         sanitized["minimum_warranty_years"] = _parse_warranty_years_value(sanitized.get("minimum_warranty_years"))
#         sanitized["required_port_count"] = parse_port_count(sanitized.get("required_port_count"))
#         sanitized["required_throughput_mbps"] = parse_throughput_mbps(sanitized.get("required_throughput_mbps"))
#         sanitized["required_duplex_printing"] = normalize_optional_bool(
#             sanitized.get("required_duplex_printing")
#         )
#         sanitized["required_scanner"] = normalize_optional_bool(sanitized.get("required_scanner"))
#         sanitized["min_print_speed_ppm"] = parse_print_speed_ppm(sanitized.get("min_print_speed_ppm"))
#         sanitized["required_printer_type"] = self._normalize_printer_type_value(sanitized.get("required_printer_type"))
#         sanitized["required_print_technology"] = self._normalize_nullable_text(sanitized.get("required_print_technology"))
#         sanitized["required_color_output"] = normalize_color_output(sanitized.get("required_color_output")) or None
#         sanitized["min_monthly_duty_cycle_pages"] = parse_page_volume(sanitized.get("min_monthly_duty_cycle_pages"))
#         sanitized["required_automatic_document_feeder"] = normalize_optional_bool(
#             sanitized.get("required_automatic_document_feeder")
#         )
#         sanitized["required_paper_sizes"] = normalize_paper_sizes(sanitized.get("required_paper_sizes"))
#         sanitized["required_network_roles"] = [
#             role
#             for role in normalize_text_list(sanitized.get("required_network_roles"))
#             if role in {"router", "firewall", "switch", "access_point"}
#         ]
#         sanitized["required_vpn_user_capacity"] = parse_vpn_user_capacity(
#             sanitized.get("required_vpn_user_capacity")
#         )
#         sanitized["required_virtualization_ready"] = normalize_optional_bool(
#             sanitized.get("required_virtualization_ready")
#         )
#         sanitized["required_virtualization_platforms"] = normalize_virtualization_platforms(
#             sanitized.get("required_virtualization_platforms")
#         )
#         sanitized["max_rack_units"] = parse_rack_units(sanitized.get("max_rack_units"))
#         sanitized["max_power_draw_watts"] = parse_power_watts(sanitized.get("max_power_draw_watts"))
#         sanitized["battery_life_hours_min"] = _parse_intake_integer(sanitized.get("battery_life_hours_min"))
#         sanitized["cpu_preference"] = self._normalize_nullable_text(sanitized.get("cpu_preference"))
#         sanitized["gpu_requirement"] = self._normalize_nullable_text(sanitized.get("gpu_requirement"))
#         sanitized["screen_size_preference"] = self._normalize_screen_size_preference(
#             sanitized.get("screen_size_preference")
#         )
#         sanitized["weight_kg_max"] = parse_weight_kg_value(sanitized.get("weight_kg_max"))
#         sanitized["warranty_type_preference"] = normalize_warranty_type(
#             sanitized.get("warranty_type_preference")
#         )
#         sanitized["preferred_category"] = self._normalize_llm_category(
#             sanitized.get("preferred_category"),
#             chat_text,
#             sanitized.get("workload_types"),
#             sanitized.get("application_signals"),
#         )
#         sanitized["workload_types"] = self._normalize_llm_workloads(
#             sanitized.get("workload_types"),
#             chat_text,
#             sanitized.get("preferred_category"),
#             sanitized.get("application_signals"),
#         )
#         return sanitized

#     def _canonicalize_payload(self, payload, chat_text, context, deterministic_payload):
#         merged = dict(payload or {})
#         merged_chat_text = self._merge_raw_chat(context.get("raw_chat", ""), chat_text)
#         merged_chat_lower = merged_chat_text.lower()
#         merged["preferred_category"] = (
#             normalize_category(merged.get("preferred_category"))
#             or deterministic_payload.get("preferred_category")
#             or normalize_category(context.get("preferred_category"))
#         )
#         merged["team_size"] = parse_team_size(merged.get("team_size"))
#         merged["quantity"] = parse_team_size(merged.get("quantity"))
#         merged["budget"] = self._sanitize_budget_value(
#             merged.get("budget"),
#             chat_text=chat_text,
#             context=context,
#             team_size=merged.get("team_size"),
#         )
#         merged["budget_scope"] = normalize_budget_scope(
#             merged.get("budget_scope") or context.get("budget_scope"),
#             preferred_categories=[merged.get("preferred_category")] if merged.get("preferred_category") else [],
#             hint_text=merged_chat_text,
#             quantity=merged.get("quantity"),
#         )
#         merged["rollout_type"] = (
#             normalize_rollout_type(merged.get("rollout_type"))
#             or deterministic_payload.get("rollout_type")
#             or normalize_rollout_type(context.get("rollout_type"))
#         )
#         merged["replacement_mode"] = (
#             normalize_replacement_mode(merged.get("replacement_mode"))
#             or deterministic_payload.get("replacement_mode")
#             or normalize_replacement_mode(context.get("replacement_mode"))
#         )
#         merged["purchase_scope"] = normalize_purchase_scope(
#             merged.get("purchase_scope") or deterministic_payload.get("purchase_scope") or context.get("purchase_scope"),
#             preferred_categories=[merged.get("preferred_category")] if merged.get("preferred_category") else [],
#             quantity=merged.get("quantity"),
#             team_size=merged.get("team_size"),
#             hint_text=merged_chat_text,
#         )

#         canonical_workloads = normalize_workloads(merged.get("workload_types"))
#         if not canonical_workloads:
#             canonical_workloads = list(deterministic_payload.get("workload_types") or [])
#         merged["workload_types"] = self._align_workloads_with_category(
#             merged.get("preferred_category"),
#             canonical_workloads,
#             merged_chat_lower,
#         )
#         merged["application_signals"] = self._merge_list_values(
#             context.get("application_signals"),
#             self.signal_service.sanitize_application_signals(merged.get("application_signals")),
#         )
#         merged["capability_tags"] = self._merge_list_values(
#             context.get("capability_tags"),
#             self.signal_service.sanitize_capability_tags(merged.get("capability_tags")),
#         )
#         merged["capability_tags"] = self._derive_capability_tags(
#             preferred_category=merged.get("preferred_category"),
#             workload_types=merged.get("workload_types"),
#             application_signals=merged.get("application_signals"),
#             signal_capability_tags=merged.get("capability_tags"),
#             requested_ram=parse_ram_gb(merged.get("requested_ram")),
#             requested_storage=parse_storage_gb(merged.get("requested_storage")),
#             portability_need=merged.get("portability_need"),
#             support_expectation=merged.get("support_expectation"),
#             availability_need=merged.get("availability_need"),
#             existing_infrastructure=self._merge_list_values(
#                 context.get("existing_infrastructure"),
#                 deterministic_payload.get("existing_infrastructure"),
#             ),
#             lowered=merged_chat_lower,
#         )
#         merged["performance_priority"] = self._normalize_performance_priority_value(
#             merged.get("performance_priority")
#             or deterministic_payload.get("performance_priority")
#             or context.get("performance_priority"),
#             merged_chat_lower,
#         )

#         merged["existing_infrastructure"] = self._merge_list_values(
#             context.get("existing_infrastructure"),
#             deterministic_payload.get("existing_infrastructure"),
#         )
#         merged["preferred_manufacturers"] = self._merge_list_values(
#             context.get("preferred_manufacturers"),
#             merged.get("preferred_manufacturers"),
#         )
#         merged["blocked_manufacturers"] = self._merge_list_values(
#             context.get("blocked_manufacturers"),
#             merged.get("blocked_manufacturers"),
#         )
#         merged["preferred_sellers"] = self._merge_list_values(
#             context.get("preferred_sellers"),
#             merged.get("preferred_sellers"),
#         )
#         merged["blocked_sellers"] = self._merge_list_values(
#             context.get("blocked_sellers"),
#             merged.get("blocked_sellers"),
#         )
#         merged["availability_need"] = (
#             normalize_availability_need(merged.get("availability_need"))
#             or deterministic_payload.get("availability_need")
#             or normalize_availability_need(context.get("availability_need"))
#         )
#         merged["require_returnable"] = self._first_non_none(
#             normalize_optional_bool(merged.get("require_returnable")),
#             deterministic_payload.get("require_returnable"),
#             normalize_optional_bool(context.get("require_returnable")),
#         )
#         merged["requested_ram_is_minimum"] = self._first_non_none(
#             normalize_optional_bool(merged.get("requested_ram_is_minimum")),
#             deterministic_payload.get("requested_ram_is_minimum"),
#             normalize_optional_bool(context.get("requested_ram_is_minimum")),
#         )
#         merged["requested_storage_is_minimum"] = self._first_non_none(
#             normalize_optional_bool(merged.get("requested_storage_is_minimum")),
#             deterministic_payload.get("requested_storage_is_minimum"),
#             normalize_optional_bool(context.get("requested_storage_is_minimum")),
#         )
#         merged["minimum_warranty_years"] = self._first_non_none(
#             _parse_warranty_years_value(merged.get("minimum_warranty_years")),
#             deterministic_payload.get("minimum_warranty_years"),
#             _parse_warranty_years_value(context.get("minimum_warranty_years")),
#         )
#         merged["required_port_count"] = self._first_non_none(
#             parse_port_count(merged.get("required_port_count")),
#             deterministic_payload.get("required_port_count"),
#             parse_port_count(context.get("required_port_count")),
#         )
#         merged["required_throughput_mbps"] = self._first_non_none(
#             parse_throughput_mbps(merged.get("required_throughput_mbps")),
#             deterministic_payload.get("required_throughput_mbps"),
#             parse_throughput_mbps(context.get("required_throughput_mbps")),
#         )
#         merged["required_duplex_printing"] = self._first_non_none(
#             normalize_optional_bool(merged.get("required_duplex_printing")),
#             deterministic_payload.get("required_duplex_printing"),
#             normalize_optional_bool(context.get("required_duplex_printing")),
#         )
#         merged["required_scanner"] = self._first_non_none(
#             normalize_optional_bool(merged.get("required_scanner")),
#             deterministic_payload.get("required_scanner"),
#             normalize_optional_bool(context.get("required_scanner")),
#         )
#         merged["min_print_speed_ppm"] = self._first_non_none(
#             parse_print_speed_ppm(merged.get("min_print_speed_ppm")),
#             deterministic_payload.get("min_print_speed_ppm"),
#             parse_print_speed_ppm(context.get("min_print_speed_ppm")),
#         )
#         merged["required_printer_type"] = self._first_non_none(
#             self._normalize_printer_type_value(merged.get("required_printer_type")),
#             self._normalize_printer_type_value(deterministic_payload.get("required_printer_type")),
#             self._normalize_printer_type_value(context.get("required_printer_type")),
#         )
#         merged["required_print_technology"] = self._first_non_none(
#             self._normalize_nullable_text(merged.get("required_print_technology")),
#             deterministic_payload.get("required_print_technology"),
#             self._normalize_nullable_text(context.get("required_print_technology")),
#         )
#         merged["required_color_output"] = self._first_non_none(
#             normalize_color_output(merged.get("required_color_output")) or None,
#             deterministic_payload.get("required_color_output"),
#             normalize_color_output(context.get("required_color_output")) or None,
#         )
#         merged["min_monthly_duty_cycle_pages"] = self._first_non_none(
#             parse_page_volume(merged.get("min_monthly_duty_cycle_pages")),
#             deterministic_payload.get("min_monthly_duty_cycle_pages"),
#             parse_page_volume(context.get("min_monthly_duty_cycle_pages")),
#         )
#         merged["required_automatic_document_feeder"] = self._first_non_none(
#             normalize_optional_bool(merged.get("required_automatic_document_feeder")),
#             deterministic_payload.get("required_automatic_document_feeder"),
#             normalize_optional_bool(context.get("required_automatic_document_feeder")),
#         )
#         merged["required_paper_sizes"] = self._merge_list_values(
#             context.get("required_paper_sizes"),
#             normalize_paper_sizes(merged.get("required_paper_sizes")),
#         )
#         merged["required_network_roles"] = self._merge_list_values(
#             context.get("required_network_roles"),
#             [
#                 role
#                 for role in normalize_text_list(merged.get("required_network_roles"))
#                 if role in {"router", "firewall", "switch", "access_point"}
#             ],
#         )
#         merged["required_vpn_user_capacity"] = self._first_non_none(
#             parse_vpn_user_capacity(merged.get("required_vpn_user_capacity")),
#             deterministic_payload.get("required_vpn_user_capacity"),
#             parse_vpn_user_capacity(context.get("required_vpn_user_capacity")),
#         )
#         merged["required_virtualization_ready"] = self._first_non_none(
#             normalize_optional_bool(merged.get("required_virtualization_ready")),
#             deterministic_payload.get("required_virtualization_ready"),
#             normalize_optional_bool(context.get("required_virtualization_ready")),
#         )
#         merged["required_virtualization_platforms"] = self._merge_list_values(
#             context.get("required_virtualization_platforms"),
#             normalize_virtualization_platforms(merged.get("required_virtualization_platforms")),
#         )
#         merged["max_rack_units"] = self._first_non_none(
#             parse_rack_units(merged.get("max_rack_units")),
#             deterministic_payload.get("max_rack_units"),
#             parse_rack_units(context.get("max_rack_units")),
#         )
#         merged["max_power_draw_watts"] = self._first_non_none(
#             parse_power_watts(merged.get("max_power_draw_watts")),
#             deterministic_payload.get("max_power_draw_watts"),
#             parse_power_watts(context.get("max_power_draw_watts")),
#         )
#         merged["battery_life_hours_min"] = self._first_non_none(
#             _parse_intake_integer(merged.get("battery_life_hours_min")),
#             deterministic_payload.get("battery_life_hours_min"),
#             _parse_intake_integer(context.get("battery_life_hours_min")),
#         )
#         merged["cpu_preference"] = self._first_non_none(
#             self._normalize_nullable_text(merged.get("cpu_preference")),
#             deterministic_payload.get("cpu_preference"),
#             self._normalize_nullable_text(context.get("cpu_preference")),
#         )
#         merged["gpu_requirement"] = self._first_non_none(
#             self._normalize_nullable_text(merged.get("gpu_requirement")),
#             deterministic_payload.get("gpu_requirement"),
#             self._normalize_nullable_text(context.get("gpu_requirement")),
#         )
#         merged["screen_size_preference"] = self._first_non_none(
#             self._normalize_screen_size_preference(merged.get("screen_size_preference")),
#             deterministic_payload.get("screen_size_preference"),
#             self._normalize_screen_size_preference(context.get("screen_size_preference")),
#         )
#         merged["weight_kg_max"] = self._first_non_none(
#             parse_weight_kg_value(merged.get("weight_kg_max")),
#             deterministic_payload.get("weight_kg_max"),
#             parse_weight_kg_value(context.get("weight_kg_max")),
#         )
#         merged["warranty_type_preference"] = self._first_non_none(
#             normalize_warranty_type(merged.get("warranty_type_preference")),
#             deterministic_payload.get("warranty_type_preference"),
#             normalize_warranty_type(context.get("warranty_type_preference")),
#         )

#         if not merged.get("company_size"):
#             merged["company_size"] = self._company_size_from_team_size(merged.get("team_size"))
#         return merged

#     def _merge_payloads(self, context, llm_payload, deterministic_payload):
#         merged = dict(context or {})

#         # LLM is the primary interpreter for free-form chat. Deterministic
#         # extraction remains attached as a guardrail and safe backfill layer.
#         for source in (llm_payload or {}, deterministic_payload or {}):
#             for key, value in source.items():
#                 if value in (None, "", []):
#                     continue
#                 if isinstance(value, list):
#                     merged[key] = self._merge_list_values(merged.get(key), value)
#                 else:
#                     merged[key] = value

#         if not merged.get("company_size"):
#             merged["company_size"] = self._company_size_from_team_size(merged.get("team_size"))
#         return merged

#     def _merge_list_values(self, existing, incoming):
#         combined = []
#         for value in list(existing or []) + list(incoming or []):
#             normalized = str(value or "").strip()
#             if normalized and normalized not in combined:
#                 combined.append(normalized)
#         return combined

#     def _merge_text_fragments(self, *values, separator="\n"):
#         merged = []
#         seen = set()
#         for value in values:
#             normalized = re.sub(r"\s+", " ", str(value or "")).strip()
#             if not normalized:
#                 continue
#             marker = normalized.lower()
#             if marker in seen:
#                 continue
#             seen.add(marker)
#             merged.append(normalized)
#         return separator.join(merged)

#     def _merge_raw_chat(self, existing, latest):
#         return self._merge_text_fragments(existing, latest, separator="\n")

#     def _should_skip_llm_for_clarification_turn(self, chat_text, context, deterministic_payload):
#         chat_text = str(chat_text or "").strip()
#         if not chat_text:
#             return False

#         lowered = chat_text.lower()
#         if self._looks_like_direct_value_reply(lowered):
#             return False

#         deterministic_payload = dict(deterministic_payload or {})
#         category = deterministic_payload.get("preferred_category")
#         workloads = list(deterministic_payload.get("workload_types") or [])
#         budget = deterministic_payload.get("budget")
#         if category and category != "not_sure":
#             return False
#         if workloads or budget is not None:
#             return False

#         concrete_signal_fields = (
#             "application_signals",
#             "capability_tags",
#             "team_size",
#             "quantity",
#             "requested_ram",
#             "requested_storage",
#             "minimum_warranty_years",
#             "required_port_count",
#             "required_throughput_mbps",
#             "required_duplex_printing",
#             "required_scanner",
#             "min_print_speed_ppm",
#             "required_printer_type",
#             "required_network_roles",
#             "required_vpn_user_capacity",
#             "required_virtualization_ready",
#             "required_virtualization_platforms",
#             "max_rack_units",
#             "max_power_draw_watts",
#             "battery_life_hours_min",
#             "cpu_preference",
#             "gpu_requirement",
#             "screen_size_preference",
#             "weight_kg_max",
#             "warranty_type_preference",
#             "preferred_manufacturers",
#             "preferred_sellers",
#             "blocked_manufacturers",
#             "blocked_sellers",
#         )
#         if any(self._value_present(deterministic_payload.get(field)) for field in concrete_signal_fields):
#             return False

#         generic_markers = {
#             "help me choose",
#             "help me decide",
#             "not sure",
#             "whatever best you suggest",
#             "whatever you suggest",
#             "best you suggest",
#             "suggest the best",
#             "what exactly do i need",
#             "what do i need",
#             "guide me",
#             "advise me",
#         }
#         setup_markers = {
#             "opening a hospital",
#             "opening a clinic",
#             "opening a business",
#             "opening an office",
#             "opening a branch",
#             "starting a hospital",
#             "starting a clinic",
#             "setting up a hospital",
#             "setting up a clinic",
#         }
#         has_generic_marker = any(marker in lowered for marker in generic_markers | setup_markers)
#         if not has_generic_marker and not deterministic_payload.get("industry"):
#             return False

#         merged_context = self._merge_payloads(context, {}, deterministic_payload)
#         merged_context["raw_chat"] = self._merge_raw_chat(context.get("raw_chat", ""), chat_text)
#         payload = self.build_procurement_payload(
#             merged_context,
#             {
#                 "channel": context.get("channel", ""),
#             },
#         )
#         requirements = self.intake_service.normalize(payload)
#         readiness = self.clarification_service.assess(requirements)
#         missing_signals = set(readiness.get("missing_signals") or [])
#         if not self.clarification_service.should_defer_ranking(readiness):
#             return False
#         return bool(
#             {"preferred_category", "category_or_workload", "workload_or_application_profile", "budget"}.intersection(
#                 missing_signals
#             )
#         )

#     def _build_field_source_hints(
#         self,
#         payload,
#         context,
#         deterministic_payload,
#         deterministic_field_sources,
#         llm_payload,
#     ):
#         hints = {}
#         payload = dict(payload or {})
#         context = dict(context or {})
#         deterministic_payload = dict(deterministic_payload or {})
#         deterministic_field_sources = dict(deterministic_field_sources or {})
#         llm_payload = dict(llm_payload or {})

#         for field in SCHEMA_KEYS + ["purchase_scope"]:
#             value = payload.get(field)
#             if not self._value_present(value):
#                 continue
#             if self._value_present(context.get(field)):
#                 hints[field] = "context_explicit"
#             elif self._value_present(llm_payload.get(field)):
#                 hints[field] = "llm_inferred"
#             elif self._value_present(deterministic_payload.get(field)):
#                 hints[field] = deterministic_field_sources.get(field, "rule_inferred")
#         return hints

#     def _compute_missing_fields(self, payload):
#         missing_fields = []
#         preferred_category = payload.get("preferred_category")
#         if preferred_category == "not_sure":
#             preferred_category = None
#         if not preferred_category and not payload.get("workload_types"):
#             missing_fields.append("preferred_category")
#         if not payload.get("workload_types"):
#             missing_fields.append("workload_types")
#         if payload.get("budget") is None:
#             missing_fields.append("budget")
#         if (
#             payload.get("team_size") is None
#             and payload.get("quantity") is None
#             and payload.get("preferred_category") in {"laptops", "desktops"}
#         ):
#             missing_fields.append("team_size")
#         if not payload.get("growth_expectation"):
#             missing_fields.append("growth_expectation")
#         if self._needs_application_profile(payload):
#             missing_fields.append("application_profile")
#         return missing_fields

#     def _estimate_confidence(self, payload, used_llm):
#         score = 0.0
#         if payload.get("preferred_category") or payload.get("workload_types"):
#             score += 0.25
#         if payload.get("budget") is not None:
#             score += 0.2
#         if payload.get("team_size") or payload.get("quantity"):
#             score += 0.15
#         if payload.get("industry"):
#             score += 0.05
#         if payload.get("growth_expectation"):
#             score += 0.05
#         if payload.get("application_signals"):
#             score += min(len(payload.get("application_signals") or []) * 0.08, 0.16)
#         if payload.get("capability_tags"):
#             score += min(len(payload.get("capability_tags") or []) * 0.05, 0.15)
#         if (
#             payload.get("requested_ram")
#             or payload.get("requested_storage")
#             or payload.get("minimum_warranty_years")
#             or payload.get("required_port_count")
#             or payload.get("required_throughput_mbps")
#             or payload.get("required_duplex_printing")
#             or payload.get("required_scanner")
#             or payload.get("min_print_speed_ppm")
#             or payload.get("required_printer_type")
#             or payload.get("required_print_technology")
#             or payload.get("required_color_output")
#             or payload.get("min_monthly_duty_cycle_pages")
#             or payload.get("required_automatic_document_feeder")
#             or payload.get("required_paper_sizes")
#             or payload.get("required_network_roles")
#             or payload.get("required_vpn_user_capacity")
#             or payload.get("required_virtualization_ready")
#             or payload.get("required_virtualization_platforms")
#             or payload.get("max_rack_units")
#             or payload.get("max_power_draw_watts")
#             or payload.get("battery_life_hours_min")
#             or payload.get("cpu_preference")
#             or payload.get("gpu_requirement")
#             or payload.get("screen_size_preference")
#             or payload.get("weight_kg_max")
#             or payload.get("warranty_type_preference")
#         ):
#             score += 0.1
#         if payload.get("performance_priority") or payload.get("portability_need") or payload.get("support_expectation"):
#             score += 0.05
#         if used_llm:
#             score += 0.04
#         return round(min(score, 1.0), 2)

#     def _needs_application_profile(self, payload):
#         workloads = set(payload.get("workload_types") or [])
#         if not workloads:
#             return False
#         if payload.get("application_signals"):
#             return False
#         if (
#             payload.get("requested_ram")
#             or payload.get("requested_storage")
#             or payload.get("minimum_warranty_years")
#             or payload.get("required_port_count")
#             or payload.get("required_throughput_mbps")
#             or payload.get("required_duplex_printing")
#             or payload.get("required_scanner")
#             or payload.get("min_print_speed_ppm")
#             or payload.get("required_printer_type")
#             or payload.get("required_print_technology")
#             or payload.get("required_color_output")
#             or payload.get("min_monthly_duty_cycle_pages")
#             or payload.get("required_automatic_document_feeder")
#             or payload.get("required_paper_sizes")
#             or payload.get("required_network_roles")
#             or payload.get("required_vpn_user_capacity")
#             or payload.get("required_virtualization_ready")
#             or payload.get("required_virtualization_platforms")
#             or payload.get("max_rack_units")
#             or payload.get("max_power_draw_watts")
#             or payload.get("battery_life_hours_min")
#             or payload.get("cpu_preference")
#             or payload.get("gpu_requirement")
#             or payload.get("screen_size_preference")
#             or payload.get("weight_kg_max")
#             or payload.get("warranty_type_preference")
#         ):
#             return False
#         capability_tags = set(payload.get("capability_tags") or [])
#         if capability_tags.intersection(
#             {"gpu_needed", "high_ram", "storage_heavy", "virtualization", "branch_connectivity", "local_compute"}
#         ):
#             return False
#         return bool(workloads.intersection({"software_development", "creative_design", "ai_analytics", "server_infrastructure"}))

#     def _derive_capability_tags(
#         self,
#         preferred_category,
#         workload_types,
#         application_signals,
#         signal_capability_tags,
#         requested_ram,
#         requested_storage,
#         portability_need,
#         support_expectation,
#         availability_need,
#         existing_infrastructure,
#         lowered,
#     ):
#         capability_tags = self.signal_service.sanitize_capability_tags(signal_capability_tags)
#         workload_set = set(workload_types or [])
#         infrastructure_set = {str(item or "").strip().lower() for item in (existing_infrastructure or []) if str(item or "").strip()}

#         if portability_need == "high" and "portable" not in capability_tags:
#             capability_tags.append("portable")
#         if requested_ram and requested_ram >= 32 and "high_ram" not in capability_tags:
#             capability_tags.append("high_ram")
#         if requested_storage and requested_storage >= 1024 and "storage_heavy" not in capability_tags:
#             capability_tags.append("storage_heavy")
#         if support_expectation == "premium" and "always_on" not in capability_tags:
#             capability_tags.append("always_on")
#         if availability_need in {"urgent", "in_stock_now"} and "always_on" not in capability_tags:
#             capability_tags.append("always_on")
#         if "virtualization" in infrastructure_set or "server_infrastructure" in workload_set:
#             if any(token in lowered for token in {"virtualization", "vmware", "proxmox", "hyper-v", "server"}) and "virtualization" not in capability_tags:
#                 capability_tags.append("virtualization")
#         if preferred_category == "networking" and any(token in lowered for token in {"branch", "remote office"}) and "branch_connectivity" not in capability_tags:
#             capability_tags.append("branch_connectivity")
#         if any(
#             signal in set(application_signals or [])
#             for signal in {"developer_toolchain", "ml_toolchain"}
#         ) and "local_compute" not in capability_tags:
#             capability_tags.append("local_compute")

#         return capability_tags

#     def _normalize_nullable_text(self, value):
#         text = str(value or "").strip()
#         return text or None

#     def _normalize_screen_size_preference(self, value):
#         parsed = parse_screen_size_inches_value(value)
#         if parsed is None:
#             return self._normalize_nullable_text(value)
#         return f"{parsed:.1f} inch"

#     def _value_present(self, value):
#         return value not in (None, "", [], {})

#     def _first_non_none(self, *values):
#         for value in values:
#             if value is not None:
#                 return value
#         return None

#     def _sanitize_named_list(self, values, allowed_names):
#         lowered_map = {name.lower(): name for name in allowed_names}
#         sanitized = []
#         for value in normalize_text_list(values):
#             key = value.lower()
#             if key in lowered_map and lowered_map[key] not in sanitized:
#                 sanitized.append(lowered_map[key])
#         return sanitized

#     def _sanitize_budget_value(self, value, chat_text, context, team_size=None):
#         parsed = self._parse_budget_value(value)
#         if parsed is None:
#             return self._parse_budget_value((context or {}).get("budget"))

#         explicit_budget = self._detect_budget(chat_text, context={})
#         if explicit_budget is not None:
#             return explicit_budget

#         existing_budget = self._parse_budget_value((context or {}).get("budget"))
#         if existing_budget is not None:
#             return existing_budget

#         if team_size and parsed == int(team_size):
#             return None
#         return parsed

#     def _detect_spec_requirement_strength(self, lowered, spec_kind):
#         lowered = str(lowered or "")
#         spec_tokens = {
#             "ram": {"ram", "memory"},
#             "storage": {"storage", "ssd", "nvme", "disk", "hdd"},
#         }.get(spec_kind, {spec_kind})

#         hard_markers = get_procurement_normalization_terms("hard_requirement_words", "hard", set())
#         soft_markers = get_procurement_normalization_terms("hard_requirement_words", "soft", set())

#         if any(marker in lowered for marker in hard_markers) and any(token in lowered for token in spec_tokens):
#             return True
#         if any(marker in lowered for marker in soft_markers) and any(token in lowered for token in spec_tokens):
#             return False
#         return False

#     def _detect_manufacturer_preferences(self, chat_text):
#         return self._detect_preference_lists(chat_text, KNOWN_MANUFACTURERS)

#     def _detect_seller_preferences(self, chat_text):
#         return self._detect_preference_lists(chat_text, KNOWN_SELLERS)

#     def _detect_preference_lists(self, chat_text, known_names):
#         text = str(chat_text or "")
#         lowered = text.lower()
#         preferred = []
#         blocked = []
#         soft_markers = {"prefer", "preferred", "ideally", "would like", "lean toward", "like"}
#         hard_block_markers = {"avoid", "exclude", "block", "not ", "don't want", "do not want", "no "}

#         for name in known_names:
#             pattern = rf"\b{re.escape(name.lower())}\b"
#             if not re.search(pattern, lowered):
#                 continue

#             position = lowered.find(name.lower())
#             window_start = max(position - 40, 0)
#             window = lowered[window_start:position]
#             if any(marker in window for marker in hard_block_markers):
#                 if name not in blocked:
#                     blocked.append(name)
#                 continue
#             if any(marker in window for marker in soft_markers) or "only" in window or "from" in window:
#                 if name not in preferred:
#                     preferred.append(name)

#         return preferred, blocked

#     def _detect_availability_need(self, lowered):
#         lowered = str(lowered or "")
#         if any(token in lowered for token in {"in stock now", "must be in stock", "available now", "ready stock"}):
#             return "in_stock_now"
#         if any(token in lowered for token in {"urgent", "immediately", "asap"}):
#             return "urgent"
#         if any(token in lowered for token in {"this week", "next week", "this month", "soon"}):
#             return "soon"
#         if any(token in lowered for token in {"standard", "normal", "not urgent", "no rush"}):
#             return "standard"
#         return None

#     def _detect_require_returnable(self, lowered):
#         lowered = str(lowered or "")
#         if any(token in lowered for token in {"must be returnable", "return policy required", "returnable only", "must have return policy"}):
#             return True
#         if any(token in lowered for token in {"final sale is fine", "return policy not important", "non-returnable is okay"}):
#             return False
#         return None

#     def _detect_preferred_category(self, chat_text):
#         chat_text = str(chat_text or "").strip()
#         lowered = chat_text.lower()
#         category = normalize_category(chat_text)
#         ambiguous_markers = {
#             "not sure",
#             "not certain",
#             "haven't decided",
#             "have not decided",
#             "either",
#         }
#         mentioned_categories = [
#             token
#             for token in (
#                 "laptop",
#                 "desktop",
#                 "server",
#                 "network",
#                 "router",
#                 "switch",
#                 "printer",
#                 "accessories",
#                 "keyboard",
#                 "mouse",
#                 "headset",
#                 "headphone",
#             )
#             if token in lowered
#         ]
#         if any(marker in lowered for marker in ambiguous_markers) and len(set(mentioned_categories)) >= 2:
#             return "not_sure"
#         if "laptops or desktops" in lowered or "desktops or laptops" in lowered:
#             return "not_sure"
#         if not category and self._looks_like_printer_need(lowered):
#             return "printers"
#         if not category and self._looks_like_server_need(lowered):
#             return "servers"
#         if not category and self._looks_like_networking_need(lowered):
#             return "networking"
#         if not category and self._looks_like_end_user_device_need(lowered):
#             return "laptops"
#         return category

#     def _looks_like_printer_need(self, lowered):
#         lowered = str(lowered or "")
#         printer_tokens = {
#             "printer",
#             "printing",
#             "print",
#             "ppm",
#             "adf",
#             "all in one",
#             "all-in-one",
#             "mfp",
#             "duplex",
#             "scanner",
#             "scan",
#             "copy",
#             "laser",
#             "inkjet",
#             "ink tank",
#             "pages per month",
#             "duty cycle",
#             "a3",
#             "a4",
#         }
#         score = sum(1 for token in printer_tokens if token in lowered)
#         return score >= 2

#     def _looks_like_server_need(self, lowered):
#         lowered = str(lowered or "")
#         server_tokens = {
#             "server",
#             "virtualization",
#             "vmware",
#             "hyper-v",
#             "proxmox",
#             "hypervisor",
#             "xeon",
#             "epyc",
#             "rack",
#             "rackmount",
#             "2u",
#             "4u",
#             "power draw",
#         }
#         score = sum(1 for token in server_tokens if token in lowered)
#         return score >= 2

#     def _looks_like_networking_need(self, lowered):
#         lowered = str(lowered or "")
#         networking_tokens = {
#             "switch",
#             "router",
#             "firewall",
#             "vpn",
#             "throughput",
#             "bandwidth",
#             "port",
#             "ports",
#             "access point",
#             "wifi",
#             "wi-fi",
#             "lan",
#             "wan",
#         }
#         score = sum(1 for token in networking_tokens if token in lowered)
#         return score >= 2


#     def _detect_requested_ram(self, chat_text):
#         text = str(chat_text or "")
#         patterns = [
#             r"(\d+)\s*gb\s*(?:ram|memory)",
#             r"(?:ram|memory)\s*(?:of|at)?\s*(\d+)\s*gb",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 return int(match.group(1))
#         return None

#     def _detect_requested_storage(self, chat_text):
#         text = str(chat_text or "")
#         patterns = [
#             r"(\d+(?:\.\d+)?)\s*(tb|gb)\s*(?:ssd|nvme|storage|disk|hdd)",
#             r"(?:ssd|nvme|storage|disk|hdd)\s*(?:of|at)?\s*(\d+(?:\.\d+)?)\s*(tb|gb)",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if not match:
#                 continue
#             value = float(match.group(1))
#             unit = match.group(2).lower()
#             storage_gb = int(value * 1024) if unit == "tb" else int(value)
#             return storage_gb
#         return None

#     def _detect_minimum_warranty_years(self, chat_text):
#         text = str(chat_text or "")
#         patterns = [
#             r"(\d+)\s*(?:year|yr|yrs)[-\s]*(?:warranty|support|coverage)",
#             r"(?:warranty|support|coverage)\s*(?:of|for|at least|minimum|min)?\s*(\d+)\s*(?:year|yr|yrs)",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 return int(match.group(1))
#         return None

#     def _detect_required_port_count(self, chat_text):
#         text = str(chat_text or "")
#         patterns = [
#             r"(?:at least|minimum|min|with|need|needs|require|requires)\s*(\d+)\s*(?:ports?|lan ports?|ethernet ports?)",
#             r"(\d+)\s*(?:ports?|lan ports?|ethernet ports?)",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 return int(match.group(1))
#         return None

#     def _detect_required_throughput_mbps(self, chat_text):
#         text = str(chat_text or "")
#         patterns = [
#             r"(?:at least|minimum|min|with|need|needs|require|requires)\s*([\d.,]+)\s*(gbps|gbit|gigabit|mbps|mbit)",
#             r"([\d.,]+)\s*(gbps|gbit|gigabit|mbps|mbit)\s*(?:throughput|speed|bandwidth)",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 return parse_throughput_mbps(f"{match.group(1)} {match.group(2)}")
#         return None

#     def _detect_required_duplex_printing(self, lowered):
#         lowered = str(lowered or "")
#         if any(token in lowered for token in {"duplex", "double-sided", "double sided"}):
#             return True
#         return None

#     def _detect_required_scanner(self, lowered):
#         lowered = str(lowered or "")
#         if any(token in lowered for token in {"scanner", "scan", "scanning", "copy", "all in one", "all-in-one", "mfp"}):
#             return True
#         return None

#     def _detect_min_print_speed_ppm(self, chat_text):
#         text = str(chat_text or "")
#         patterns = [
#             r"(?:at least|minimum|min|with|need|needs|require|requires)\s*(\d+)\s*ppm",
#             r"(\d+)\s*ppm",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 return int(match.group(1))
#         return None

#     def _detect_required_printer_type(self, lowered):
#         lowered = str(lowered or "")
#         if "label printer" in lowered:
#             return "label_printer"
#         if "photo printer" in lowered:
#             return "photo_printer"
#         if "wide format" in lowered or "plotter" in lowered:
#             return "wide_format_printer"
#         if any(token in lowered for token in {"all in one", "all-in-one", "mfp"}):
#             return "all_in_one_printer"
#         return None

#     def _detect_required_print_technology(self, lowered):
#         lowered = str(lowered or "")
#         if "ink tank" in lowered:
#             return "ink tank"
#         if "inkjet" in lowered:
#             return "inkjet"
#         if "laser" in lowered:
#             return "laser"
#         return None

#     def _detect_required_color_output(self, lowered):
#         value = normalize_color_output(lowered)
#         return value or None

#     def _detect_min_monthly_duty_cycle_pages(self, chat_text):
#         text = str(chat_text or "")
#         patterns = [
#             r"(\d+(?:\.\d+)?)\s*k?\s*(?:pages?|prints?)\s*(?:per|/)\s*month",
#             r"monthly duty cycle(?:\s+of)?\s*(\d+(?:\.\d+)?)\s*k?",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if not match:
#                 continue
#             token = match.group(0)
#             if "k" in token.lower():
#                 return int(float(match.group(1)) * 1000)
#             return int(float(match.group(1)))
#         return None

#     def _detect_required_automatic_document_feeder(self, lowered):
#         lowered = str(lowered or "")
#         if any(token in lowered for token in {"automatic document feeder", "adf"}):
#             return True
#         return None

#     def _detect_required_paper_sizes(self, chat_text):
#         matches = re.findall(r"\b(a3|a4|letter|legal)\b", str(chat_text or ""), re.IGNORECASE)
#         if not matches:
#             return []
#         return list(dict.fromkeys(match.upper() for match in matches))

#     def _detect_required_network_roles(self, lowered):
#         lowered = str(lowered or "")
#         roles = []
#         mapping = {
#             "router": {"router", "routers"},
#             "firewall": {"firewall", "firewalls"},
#             "switch": {"switch", "switches"},
#             "access_point": {"access point", "access points", "wifi", "wi-fi", "wireless ap"},
#         }
#         for role, tokens in mapping.items():
#             if any(token in lowered for token in tokens):
#                 roles.append(role)
#         return roles

#     def _detect_required_vpn_user_capacity(self, chat_text):
#         text = str(chat_text or "")
#         patterns = [
#             r"(\d+)\s*(?:vpn users?|remote users?)",
#             r"for\s*(\d+)\s*users?\s*(?:over\s+)?vpn",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 return int(match.group(1))
#         return None

#     def _detect_required_virtualization_ready(self, lowered):
#         lowered = str(lowered or "")
#         if any(token in lowered for token in {"virtualization", "hypervisor", "vmware", "hyper-v", "proxmox", "kvm"}):
#             return True
#         return None

#     def _detect_required_virtualization_platforms(self, chat_text):
#         return normalize_virtualization_platforms([chat_text])

#     def _detect_max_rack_units(self, chat_text):
#         text = str(chat_text or "")
#         patterns = [
#             r"(?:under|below|max(?:imum)?|not more than)\s*(\d+(?:\.\d+)?)\s*u\b",
#             r"(\d+(?:\.\d+)?)\s*u\b",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 return float(match.group(1))
#         return None

#     def _detect_max_power_draw_watts(self, chat_text):
#         text = str(chat_text or "")
#         patterns = [
#             r"(?:under|below|max(?:imum)?|not more than)\s*(\d+(?:\.\d+)?)\s*(?:w|watts?)",
#             r"power draw(?:\s+of)?\s*(\d+(?:\.\d+)?)\s*(?:w|watts?)",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 return int(float(match.group(1)))
#         return None

#     def _detect_battery_life_hours_min(self, chat_text):
#         text = str(chat_text or "")
#         patterns = [
#             r"(?:at least|minimum|min|needs?|requires?)\s*(\d+)\s*(?:hours?|hrs?)\s*(?:battery|battery life)",
#             r"(?:last|lasts)\s*(?:at least|min(?:imum)?)?\s*(\d+)\s*(?:hours?|hrs?)",
#             r"(\d+)\s*(?:hours?|hrs?)\s*(?:battery|battery life)",
#             r"battery(?: life)?\s*(?:of|for|at least|min|minimum)?\s*(\d+)\s*(?:hours?|hrs?)",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 return int(match.group(1))
#         return None

#     def _detect_cpu_preference(self, chat_text):
#         text = str(chat_text or "")
#         patterns = [
#             r"(intel\s+core\s+ultra\s+[3579](?:[-\s]*\d+[a-z]{0,2})?)",
#             r"(intel\s+core\s+i[3579](?:[-\s]*\d+[a-z]{0,2})?)",
#             r"(intel\s+core\s+[3579](?:[-\s]*\d+[a-z]{0,2})?)",
#             r"(amd\s+ryzen(?:\s+ai)?\s+[3579](?:[-\s]*\d+[a-z]{0,2})?)",
#             r"(apple\s+m[234](?:\s+(?:pro|max))?)",
#             r"(snapdragon\s+x\s+(?:elite|plus))",
#             r"(intel\s+xeon(?:\s+\w+)*)",
#             r"(amd\s+epyc(?:\s+\w+)*)",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 return " ".join(match.group(1).split())
#         return None

#     def _detect_gpu_requirement(self, chat_text):
#         text = str(chat_text or "")
#         lowered = text.lower()
#         patterns = [
#             r"(nvidia\s+rtx\s+\d{3,4})",
#             r"(nvidia\s+rtx\s+a\d{3,4})",
#             r"(nvidia\s+quadro\s+\w+)",
#             r"(amd\s+radeon(?:\s+pro)?\s+\w+)",
#             r"(intel\s+arc\s+\w+)",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 return " ".join(match.group(1).split())
#         if any(token in lowered for token in {"dedicated gpu", "discrete gpu", "dedicated graphics", "discrete graphics"}):
#             return "dedicated_gpu"
#         return None

#     def _detect_screen_size_preference(self, chat_text):
#         text = str(chat_text or "")
#         patterns = [
#             r"(\d+(?:\.\d+)?)\s*(?:-| )?(?:inch|inches|in)\b",
#             r"screen(?: size)?\s*(?:of|around|about|at|near)?\s*(\d+(?:\.\d+)?)",
#             r"display(?: size)?\s*(?:of|around|about|at|near)?\s*(\d+(?:\.\d+)?)",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if not match:
#                 continue
#             size = parse_screen_size_inches_value(match.group(1))
#             if size is not None:
#                 return f"{size:.1f} inch"
#         return None

#     def _detect_weight_kg_max(self, chat_text):
#         text = str(chat_text or "")
#         patterns = [
#             r"(?:under|below|max(?:imum)?|less than|lighter than|not more than|keep it under)\s*(\d+(?:\.\d+)?)\s*(kg|kilograms?|kilos?|lb|lbs|pounds?)",
#             r"(\d+(?:\.\d+)?)\s*(kg|kilograms?|kilos?|lb|lbs|pounds?)\s*(?:max|maximum|or less|or below|or lighter)",
#             r"not too bulky.*?(\d+(?:\.\d+)?)\s*(kg|kilograms?|kilos?|lb|lbs|pounds?)",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if not match:
#                 continue
#             value = parse_weight_kg_value(f"{match.group(1)} {match.group(2)}")
#             if value is not None:
#                 return value
#         return None

#     def _detect_warranty_type_preference(self, chat_text):
#         text = str(chat_text or "").lower()
#         explicit_warranty_terms = {
#             "warranty",
#             "onsite",
#             "on-site",
#             "carry-in",
#             "carry in",
#             "pickup",
#             "pick-up",
#             "return",
#             "mail-in",
#             "mail in",
#             "accidental damage",
#         }
#         if not any(term in text for term in explicit_warranty_terms):
#             return None
#         negative_patterns = [
#             r"no\s+onsite",
#             r"not\s+onsite",
#             r"avoid\s+onsite",
#             r"no\s+carry[-\s]?in",
#             r"not\s+carry[-\s]?in",
#             r"avoid\s+carry[-\s]?in",
#             r"no\s+pickup",
#             r"not\s+pickup",
#             r"avoid\s+pickup",
#         ]
#         if any(re.search(pattern, text) for pattern in negative_patterns):
#             return None
#         return normalize_warranty_type(chat_text)

#     def _company_size_from_team_size(self, team_size):
#         team_size = parse_team_size(team_size)
#         if not team_size:
#             return None
#         if team_size <= 10:
#             return "micro"
#         if team_size <= 50:
#             return "small"
#         return "growing_smb"

#     def _align_workloads_with_category(self, preferred_category, workload_types, lowered):
#         aligned = []
#         for workload in list(workload_types or []):
#             if workload not in aligned:
#                 aligned.append(workload)

#         specialized_end_user_workloads = {"software_development", "creative_design", "ai_analytics"}
#         if "office_productivity" in aligned and specialized_end_user_workloads.intersection(aligned):
#             aligned = [workload for workload in aligned if workload != "office_productivity"]

#         if preferred_category == "networking":
#             aligned = [workload for workload in aligned if workload != "office_productivity"]
#             if "network_connectivity" not in aligned:
#                 aligned.insert(0, "network_connectivity")
#         elif preferred_category == "servers":
#             aligned = [workload for workload in aligned if workload != "office_productivity"]
#             if any(token in lowered for token in {"server", "virtualization", "hosting", "on-prem", "infrastructure"}):
#                 if "server_infrastructure" not in aligned:
#                     aligned.insert(0, "server_infrastructure")
#         elif preferred_category == "printers":
#             aligned = [workload for workload in aligned if workload != "office_productivity"]
#             if "document_output" not in aligned:
#                 aligned.insert(0, "document_output")
#         elif preferred_category == "accessories":
#             aligned = [workload for workload in aligned if workload != "office_productivity"]
#             if "peripheral_accessories" not in aligned:
#                 aligned.insert(0, "peripheral_accessories")

#         return aligned

#     def _detect_industry(self, lowered):
#         mapping = {
#             "retail": {"retail", "pos", "store"},
#             "professional services": {"professional services", "consulting", "agency"},
#             "software": {"software", "developer", "engineering", "technology", "it services"},
#             "education": {"education", "school", "campus"},
#             "healthcare": {"healthcare", "clinic", "hospital", "medical"},
#             "manufacturing": {"manufacturing", "factory", "warehouse"},
#             "finance": {"finance", "financial services", "accounting", "bookkeeping"},
#         }
#         for industry, tokens in mapping.items():
#             if any(token in lowered for token in tokens):
#                 return industry
#         return None

#     def _detect_business_type(self, lowered, context=None):
#         lowered = str(lowered or "")
#         context = dict(context or {})
#         if any(
#             token in lowered
#             for token in {
#                 "startup",
#                 "start-up",
#                 "founding team",
#                 "founders",
#                 "new company",
#                 "early stage",
#             }
#         ):
#             return "startup"
#         existing = self._normalize_nullable_text(context.get("business_type"))
#         if existing:
#             return existing
#         return None

#     def _detect_performance_priority(self, lowered):
#         if any(token in lowered for token in {"fastest", "performance", "powerful", "best specs", "high performance"}):
#             return "performance"
#         if any(token in lowered for token in {"cheap", "lowest cost", "budget sensitive", "cost focused"}):
#             return "cost"
#         if any(token in lowered for token in {"balanced", "middle ground", "well rounded"}):
#             return "balanced"
#         return None

#     def _detect_portability_need(self, lowered):
#         if any(token in lowered for token in {"travel", "portable", "lightweight", "on the go", "field team"}):
#             return "high"
#         if any(token in lowered for token in {"desk-based", "fixed desk", "office only"}):
#             return "low"
#         if any(token in lowered for token in {"hybrid", "mixed"}):
#             return "medium"
#         return None

#     def _detect_support_expectation(self, lowered):
#         if any(token in lowered for token in {"24x7", "mission critical", "premium support", "white glove"}):
#             return "premium"
#         if any(token in lowered for token in {"business support", "onsite", "next business day"}):
#             return "business"
#         if any(token in lowered for token in {"basic support", "standard support"}):
#             return "basic"
#         return None

#     def _normalize_performance_priority_value(self, value, lowered):
#         priority = str(value or "").strip().lower()
#         if priority not in {"balanced", "cost", "performance"}:
#             return None
#         if priority == "cost" and not any(
#             token in str(lowered or "")
#             for token in {"cheap", "lowest cost", "budget sensitive", "cost focused"}
#         ):
#             return None
#         if priority == "performance" and not any(
#             token in str(lowered or "")
#             for token in {"fastest", "performance", "powerful", "best specs", "fast", "high performance"}
#         ):
#             return None
#         return priority

#     def _detect_rollout_type(self, lowered):
#         lowered = str(lowered or "")
#         if any(token in lowered for token in {"phased rollout", "phase 1", "phase one", "staggered rollout", "roll out in phases"}):
#             return "phased"
#         if any(token in lowered for token in {"single phase rollout", "full rollout", "all at once"}):
#             return "standard"
#         return None

#     def _detect_replacement_mode(self, lowered):
#         lowered = str(lowered or "")
#         if any(
#             token in lowered
#             for token in {
#                 "refresh",
#                 "device refresh",
#                 "replace",
#                 "replacement",
#                 "upgrade our old",
#                 "upgrade existing",
#             }
#         ):
#             return "refresh"
#         if any(
#             token in lowered
#             for token in {
#                 "net new",
#                 "new office",
#                 "new team",
#                 "new branch",
#                 "new site",
#                 "new hires",
#                 "founding team",
#             }
#         ):
#             return "net_new"
#         return None

#     def _detect_timeline(self, chat_text):
#         lowered = str(chat_text or "").lower()
#         for token in (
#             "urgent",
#             "immediately",
#             "this week",
#             "this month",
#             "next month",
#             "next quarter",
#             "quarter",
#         ):
#             if token in lowered:
#                 return token
#         return None

#     def _detect_existing_infrastructure(self, chat_text):
#         tokens = []
#         lowered = str(chat_text or "").lower()
#         candidates = {
#             "windows": {"windows", "active directory"},
#             "mac": {"mac", "macos"},
#             "linux": {"linux", "ubuntu"},
#             "virtualization": {"vmware", "virtualization", "hyper-v", "proxmox"},
#             "networking": {"switch", "router", "firewall", "wifi", "wi-fi"},
#             "cloud": {"aws", "azure", "gcp", "cloud"},
#         }
#         for label, matchers in candidates.items():
#             if any(re.search(rf"\b{re.escape(matcher)}\b", lowered) for matcher in matchers):
#                 tokens.append(label)
#         if tokens:
#             return tokens
#         if ":" in chat_text:
#             return normalize_text_list(chat_text.split(":", 1)[1])
#         return []

#     def _detect_quantity(self, chat_text, team_size, preferred_category=None, workload_types=None):
#         lowered = str(chat_text or "").lower()
#         infrastructure_context = self._is_infrastructure_context(preferred_category, workload_types)
#         if self._has_explicit_single_unit_signal(lowered):
#             return 1, "user_explicit"

#         match = re.search(
#             r"(\d+)\s+(?:\w+\s+){0,2}(units|devices|laptops|desktops|servers|switches|routers|printers|keyboards|mice|headsets|headphones)",
#             lowered,
#         )
#         if match:
#             return int(match.group(1)), "user_explicit"

#         if infrastructure_context:
#             return None, None
#         if not team_size:
#             return None, None
#         if any(token in lowered for token in {"each", "per user", "per seat"}):
#             return team_size, "rule_inferred"
#         if self._has_rollout_quantity_signal(lowered, preferred_category):
#             return team_size, "rule_inferred"
#         return None, None

#     def _has_explicit_single_unit_signal(self, lowered):
#         lowered = str(lowered or "")
#         pattern = (
#             r"\b(?:one|single|1)\s+"
#             r"(?:\w+\s+){0,2}"
#             r"(?:unit|device|laptop|desktop|server|switch|router|firewall|printer|keyboard|mouse|headset|headphones|notebook|pc|workstation)\b"
#         )
#         return bool(re.search(pattern, lowered))

#     def _has_rollout_quantity_signal(self, lowered, preferred_category=None):
#         lowered = str(lowered or "")
#         if any(
#             token in lowered
#             for token in {
#                 "rollout",
#                 "refresh",
#                 "for the team",
#                 "for all staff",
#                 "for all employees",
#                 "for all users",
#                 "all developers",
#                 "all designers",
#                 "everyone",
#             }
#         ):
#             return True

#         category = str(preferred_category or "").strip().lower()
#         if category == "laptops" and "laptops" in lowered:
#             return True
#         if category == "desktops" and "desktops" in lowered:
#             return True
#         if category == "accessories" and any(
#             token in lowered
#             for token in {"keyboard", "keyboards", "mouse", "mice", "headset", "headsets", "headphones"}
#         ):
#             return True
#         return False

#     def _is_infrastructure_context(self, preferred_category, workload_types):
#         if preferred_category in {"networking", "servers"}:
#             return True
#         workload_set = set(workload_types or [])
#         return bool(workload_set.intersection({"network_connectivity", "server_infrastructure"}))

#     def _detect_budget_from_chat(self, chat_text):
#         lowered = str(chat_text or "").lower()
#         range_budget = self._detect_budget_range_from_chat(lowered)
#         if range_budget is not None:
#             return range_budget

#         # Remove nearby non-money spec phrases so weight or screen-size numbers
#         # do not hijack budget extraction in sales-style shorthand.
#         budget_text = re.sub(
#             r"(?:under|below|max(?:imum)?|less than|lighter than|not more than)?\s*\d+(?:\.\d+)?\s*(?:kg|kilograms?|kilos?|lb|lbs|pounds?)\b",
#             " ",
#             lowered,
#         )
#         budget_text = re.sub(
#             r"\d+(?:\.\d+)?(?:\s*|-)?(?:inch|inches|in)\b",
#             " ",
#             budget_text,
#         )
#         budget_text = re.sub(
#             r"(?:under|below|max(?:imum)?|less than|not more than)?\s*\d+(?:\.\d+)?\s*(?:w|watts?)\b",
#             " ",
#             budget_text,
#         )
#         budget_text = re.sub(
#             r"\d+(?:\.\d+)?\s*u\b",
#             " ",
#             budget_text,
#         )

#         money_token = r"(\d[\d,]*(?:\.\d+)?(?:\s?(?:k|lakh|thousand|thousands))?)"
#         currency_token = r"(?:inr|rs\.?|rupees?|myr|usd|eur|gbp|rm|\$)"
#         patterns = [
#             rf"(?:under|below|budget(?:\s+(?:is|of|around|at|for))?|around|roughly|approx(?:imately)?|up to|within|total(?:\s+budget)?(?:\s+(?:is|of))?|overall(?:\s+budget)?(?:\s+(?:is|of))?|max(?:imum)?(?:\s+budget)?(?:\s+of)?|capped at|keep it at|can stretch to|stretch to|stretch up to)\s+{currency_token}?\s*{money_token}",
#             rf"{currency_token}\s*{money_token}",
#             rf"{money_token}\s*{currency_token}",
#             rf"{money_token}\s*(?:each|per unit|per seat|per device)",
#             rf"budget\s*(?:is|of|around|at|for)?\s*{currency_token}?\s*{money_token}",
#             rf"budget\s*(?:can\s+)?stretch\s*(?:to|up to)\s*{currency_token}?\s*{money_token}",
#             rf"{money_token}\s+budget",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, budget_text)
#             if not match:
#                 continue
#             trailing_text = budget_text[match.end():match.end() + 24]
#             if any(
#                 token in trailing_text
#                 for token in {
#                     "people",
#                     "users",
#                     "employees",
#                     "staff",
#                     "developers",
#                     "designers",
#                     "engineer",
#                     "engineers",
#                     "seats",
#                     "endpoints",
#                 }
#             ):
#                 continue
#             return self._parse_budget_value(match.group(1))
#         return None

#     def _detect_budget(self, chat_text, context=None):
#         budget = self._detect_budget_from_chat(chat_text)
#         if budget is not None:
#             return budget
#         if context and context.get("budget") is not None:
#             return self._parse_budget_value(context.get("budget"))
#         return None

#     def _detect_team_size_from_chat(self, chat_text):
#         original_lowered = str(chat_text or "").lower()
#         lowered = self._strip_non_headcount_numeric_expressions(self._strip_budget_expressions(chat_text))
#         patterns = [
#             r"(?:for|around|about)\s+(\d+)\s+(?:\w+\s+){0,2}(?:users|people|employees|staff|developers|designers|agents|seats|endpoints)",
#             r"for\s+around\s+(\d+)\s+(?:\w+\s+){0,2}(?:users|people|employees|staff|developers|designers|agents|seats|endpoints)",
#             r"(\d+)\s+(?:\w+\s+){0,2}(?:users|people|employees|staff|developers|designers|agents|seats|endpoints)",
#             r"(?:will be|grow to|scale to|expand to)\s+(\d+)(?:\s+(?:users|people|employees|staff|developers|designers|agents|seats|endpoints))?",
#             r"(\d+)\s+(?:in the future|in future|future users|future endpoints)",
#         ]
#         for pattern in patterns:
#             match = re.search(pattern, lowered)
#             if match:
#                 return int(match.group(1))
#         for pattern in patterns:
#             match = re.search(pattern, original_lowered)
#             if match:
#                 return int(match.group(1))

#         stripped = lowered.strip()
#         if re.fullmatch(r"\d+", stripped):
#             return int(stripped)

#         headcount_cues = get_procurement_normalization_terms("quantity_units", default=set())
#         if any(token in lowered for token in headcount_cues):
#             parsed = parse_team_size(lowered)
#             if parsed and parsed <= 500:
#                 return parsed
#         return None

#     def _strip_non_headcount_numeric_expressions(self, text):
#         lowered = str(text or "").lower()
#         battery_units = "|".join(
#             re.escape(unit)
#             for unit in sorted(get_procurement_normalization_terms("spec_units", "battery_hours", set()), key=len, reverse=True)
#         )
#         weight_units = "|".join(
#             re.escape(unit)
#             for unit in sorted(get_procurement_normalization_terms("spec_units", "weight", set()), key=len, reverse=True)
#         )
#         screen_units = "|".join(
#             re.escape(unit)
#             for unit in sorted(get_procurement_normalization_terms("spec_units", "screen", set()), key=len, reverse=True)
#         )
#         rack_units = "|".join(
#             re.escape(unit)
#             for unit in sorted(get_procurement_normalization_terms("spec_units", "rack_units", set()), key=len, reverse=True)
#         )
#         power_units = "|".join(
#             re.escape(unit)
#             for unit in sorted(get_procurement_normalization_terms("spec_units", "power", set()), key=len, reverse=True)
#         )
#         patterns = [
#             rf"\d+\s*(?:{battery_units})\s*(?:battery|battery life)?",
#             rf"\d+(?:\.\d+)?\s*(?:{weight_units})",
#             rf"\d+(?:\.\d+)?(?:\s*|-)?(?:{screen_units})\b",
#             rf"\d+(?:\.\d+)?\s*(?:{rack_units})\b",
#             rf"\d+(?:\.\d+)?\s*(?:{power_units})\b",
#             r"\d+\s*gb\s*(?:ram|memory)",
#             r"\d+(?:\.\d+)?\s*(?:tb|gb)\s*(?:ssd|nvme|storage|disk|hdd)",
#             r"(?:rtx|gtx)\s*\d{3,4}",
#             r"a\d{3,4}",
#             r"(?:i[3579]|ultra\s+[3579]|ryzen(?:\s+ai)?\s+[3579])[-\s]*\d+[a-z]{0,2}",
#         ]
#         scrubbed = lowered
#         for pattern in patterns:
#             scrubbed = re.sub(pattern, " ", scrubbed)
#         return re.sub(r"\s+", " ", scrubbed).strip()

#     def _detect_team_size(self, chat_text, context=None):
#         team_size = self._detect_team_size_from_chat(chat_text)
#         if team_size is not None:
#             return team_size

#         if context and context.get("team_size"):
#             return parse_team_size(context.get("team_size"))
#         return None

#     def _parse_budget_value(self, value):
#         if value is None or value == "":
#             return None
#         return parse_money_value(value)

#     def _normalize_money_token(self, token):
#         token = str(token or "").strip().lower().replace(",", "")
#         if not token:
#             return None
#         return parse_money_value(token)

#     def _detect_budget_range_from_chat(self, lowered):
#         lowered = str(lowered or "").lower()
#         range_patterns = [
#             r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*(k|lakh|thousand|thousands)\b",
#             r"(\d+(?:\.\d+)?)\s*(k|lakh|thousand|thousands)\s*-\s*(\d+(?:\.\d+)?)\s*(k|lakh|thousand|thousands)?\b",
#             r"(?:around|approx(?:imately)?|maybe|roughly)?\s*(\d+(?:\.\d+)?)\s*(?:to|or)\s*(\d+(?:\.\d+)?)\s*(k|lakh|thousand|thousands)\b",
#         ]
#         for pattern in range_patterns:
#             match = re.search(pattern, lowered)
#             if not match:
#                 continue
#             groups = match.groups("")
#             if len(groups) == 3:
#                 low_token = f"{groups[0]}{groups[2]}"
#                 high_token = f"{groups[1]}{groups[2]}"
#             else:
#                 low_unit = groups[1]
#                 high_unit = groups[3] or low_unit
#                 low_token = f"{groups[0]}{low_unit}"
#                 high_token = f"{groups[2]}{high_unit}"
#             low_value = self._normalize_money_token(low_token)
#             high_value = self._normalize_money_token(high_token)
#             if low_value is not None and high_value is not None:
#                 return max(low_value, high_value)
#         return None

#     def _strip_budget_expressions(self, text):
#         lowered = str(text or "").lower()
#         patterns = [
#             r"\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?\s*(?:k|lakh|thousand|thousands)\b",
#             r"\d+(?:\.\d+)?\s*(?:k|lakh|thousand|thousands)\s*-\s*\d+(?:\.\d+)?\s*(?:k|lakh|thousand|thousands)?\b",
#             r"(?:under|below|around|approx(?:imately)?|up to|within|budget(?:\s+(?:is|of|around|at|for))?|total budget(?:\s+of)?|overall budget(?:\s+of)?)\s+(?:inr|rs\.?|rupees?|myr|usd|eur|gbp|rm|\$|â‚¹)?\s*\d[\d,]*(?:\.\d+)?(?:\s?(?:k|lakh|thousand|thousands))?",
#             r"(?:inr|rs\.?|rupees?|myr|usd|eur|gbp|rm|\$|â‚¹)\s*\d[\d,]*(?:\.\d+)?(?:\s?(?:k|lakh|thousand|thousands))?",
#             r"\d[\d,]*(?:\.\d+)?(?:\s?(?:k|lakh|thousand|thousands))?\s*(?:inr|rs\.?|rupees?|myr|usd|eur|gbp|rm|\$|â‚¹)",
#         ]
#         scrubbed = lowered
#         for pattern in patterns:
#             scrubbed = re.sub(pattern, " ", scrubbed)
#         return re.sub(r"\s+", " ", scrubbed).strip()

#     def _looks_like_end_user_device_need(self, lowered):
#         lowered = str(lowered or "").lower()
#         if self._is_generic_office_prompt(lowered):
#             return False
#         if any(token in lowered for token in {"router", "switch", "firewall", "access point", "server", "printer"}):
#             return False
#         end_user_cues = {
#             "light",
#             "lightweight",
#             "carry",
#             "portable",
#             "battery",
#             "travel",
#             "roadshow",
#             "field reps",
#             "field sales",
#             "client-facing",
#             "client facing",
#             "sales people",
#             "join calls",
#             "new joiners",
#             "coders",
#             "creative team",
#             "design team",
#             "for developers",
#             "for designers",
#             "for sales",
#             "sales reps",
#             "sales team",
#             "systems for",
#             "office pcs",
#             "office pc",
#         }
#         return any(token in lowered for token in end_user_cues)

#     def _normalize_llm_category(self, category, chat_text, workload_types, application_signals):
#         category = normalize_category(category)
#         if not category:
#             return None
#         lowered = str(chat_text or "").lower()
#         if self._is_generic_office_prompt(lowered) and category in {"laptops", "desktops"}:
#             return None
#         direct_category = normalize_category(chat_text)
#         if direct_category == category:
#             return category
#         if category == "laptops" and self._looks_like_end_user_device_need(lowered):
#             return category
#         if category == "desktops" and any(
#             token in lowered for token in {"desktop", "desktops", "pc", "pcs", "office pc", "office pcs", "workstation"}
#         ):
#             return category
#         if category == "networking" and any(
#             token in lowered for token in {"network", "networking", "firewall", "switch", "router", "branch", "vpn", "wifi", "wi-fi"}
#         ):
#             return category
#         if category == "printers" and any(
#             token in lowered for token in {"printer", "printing", "scan", "scanner", "copier", "mfp"}
#         ):
#             return category
#         if category == "accessories" and any(
#             token in lowered for token in {"headset", "headsets", "keyboard", "mouse", "dock", "accessories", "monitor"}
#         ):
#             return category
#         if category == "servers" and any(
#             token in lowered for token in {"server", "servers", "virtualization", "vmware", "hyper-v", "proxmox"}
#         ):
#             return category
#         workload_set = set(workload_types or [])
#         signal_set = {str(signal or "").strip().lower() for signal in (application_signals or [])}
#         if category == "laptops" and (
#             workload_set.intersection({"software_development", "creative_design", "office_productivity"})
#             or signal_set.intersection({"developer_toolchain", "design_suite", "business_apps", "mobile_workforce"})
#         ) and not self._is_vague_prompt(lowered):
#             return category
#         return None

#     def _normalize_llm_workloads(self, workloads, chat_text, category, application_signals):
#         workloads = normalize_workloads(workloads)
#         if not workloads:
#             return []
#         lowered = str(chat_text or "").lower()
#         if self._is_generic_office_prompt(lowered):
#             return []
#         explicit_workloads = set(normalize_workloads(chat_text))
#         explicit_signals = self.signal_service.extract(chat_text)
#         if explicit_workloads:
#             return list(dict.fromkeys(list(explicit_workloads) + list(workloads)))
#         if explicit_signals.get("workload_types"):
#             return list(dict.fromkeys(list(explicit_signals.get("workload_types") or []) + list(workloads)))
#         signal_set = {str(signal or "").strip().lower() for signal in (application_signals or [])}
#         if category == "networking" or signal_set.intersection({"branch_networking"}):
#             return workloads
#         if category == "laptops" and not self._is_vague_prompt(lowered):
#             return workloads
#         if self._is_vague_prompt(lowered):
#             return []
#         return workloads

#     def _normalize_printer_type_value(self, value):
#         text = str(value or "").strip().lower().replace("-", " ").replace("_", " ")
#         if not text:
#             return None
#         mapping = {
#             "all in one": "all_in_one_printer",
#             "all in one printer": "all_in_one_printer",
#             "mfp": "all_in_one_printer",
#             "enterprise mfp": "enterprise_mfp",
#             "label printer": "label_printer",
#             "photo printer": "photo_printer",
#             "wide format": "wide_format_printer",
#             "wide format printer": "wide_format_printer",
#             "plotter": "wide_format_printer",
#             "ink tank printer": "ink_tank_printer",
#             "inkjet printer": "inkjet_printer",
#             "mono laser printer": "mono_laser_printer",
#             "color laser printer": "color_laser_printer",
#         }
#         return mapping.get(text, text.replace(" ", "_"))

#     def _is_vague_prompt(self, lowered):
#         lowered = str(lowered or "").lower()
#         if self._is_generic_office_prompt(lowered):
#             return True
#         vague_markers = {
#             "same setup as before",
#             "same as before",
#             "something workable",
#             "something decent",
#             "new team",
#             "cheaper this time",
#             "workable",
#         }
#         strong_need_markers = {
#             "developer",
#             "developers",
#             "design",
#             "designer",
#             "designers",
#             "sales",
#             "finance",
#             "network",
#             "firewall",
#             "switch",
#             "router",
#             "printer",
#             "headset",
#             "laptop",
#             "desktop",
#             "server",
#             "branch office",
#             "branch",
#             "travel",
#             "battery",
#         }
#         if any(marker in lowered for marker in strong_need_markers):
#             return False
#         return any(marker in lowered for marker in vague_markers)

#     def _is_generic_office_prompt(self, lowered):
#         lowered = str(lowered or "").lower()
#         generic_office_markers = {
#             "new office",
#             "office setup",
#             "office requirement",
#             "office needs",
#             "for the office",
#             "office budget",
#             "workable for the office",
#         }
#         if not any(marker in lowered for marker in generic_office_markers):
#             return False
#         strong_need_markers = {
#             "developer",
#             "design",
#             "sales",
#             "finance",
#             "printer",
#             "network",
#             "switch",
#             "router",
#             "firewall",
#             "server",
#             "headset",
#             "laptop",
#             "desktop",
#             "battery",
#             "travel",
#             "gpu",
#             "core ultra",
#             "ryzen",
#             "xeon",
#         }
#         return not any(marker in lowered for marker in strong_need_markers)

#     def _detect_growth_expectation(self, lowered):
#         if any(token in lowered for token in {"stable", "steady", "no growth"}):
#             return "steady"
#         if any(token in lowered for token in {"rapid", "scale", "scaling", "expansion", "aggressive"}):
#             return "rapid_growth"
#         if any(
#             token in lowered
#             for token in {
#                 "moderate",
#                 "grow",
#                 "growth",
#                 "hiring",
#                 "new branch",
#                 "more staff",
#                 "in the future",
#                 "in future",
#                 "future users",
#                 "future endpoints",
#                 "next year",
#                 "next quarter",
#                 "next month",
#                 "over the next",
#             }
#         ):
#             return "moderate_growth"
#         return None

#     def _format_storage(self, storage_gb):
#         if not storage_gb:
#             return None
#         if storage_gb >= 1024 and storage_gb % 1024 == 0:
#             return f"{storage_gb // 1024}TB"
#         return f"{storage_gb}GB"


# RequirementExtractionService = ProcurementSchemaExtractor


import json
import re
from difflib import get_close_matches
from time import perf_counter

from ..serializers import ExtractedRequirementSerializer
from .clarification import ProcurementClarificationService
from .config_service import ProcurementConfigService
from .intake import RequirementIntakeService
from .input_normalization import (
    normalize_availability_need,
    normalize_optional_bool,
    normalize_purchase_scope,
    normalize_replacement_mode,
    normalize_rollout_type,
)
from .llm_client import OptionalLLMClient
from .signal_service import ProcurementSignalService
from ...catalog.services.normalization import (
    get_procurement_normalization_terms,
    normalize_budget_scope,
    normalize_category,
    normalize_color_output,
    normalize_paper_sizes,
    normalize_text_list,
    normalize_virtualization_platforms,
    normalize_warranty_type,
    normalize_workloads,
    parse_money_value,
    parse_page_volume,
    parse_port_count,
    parse_power_watts,
    parse_ram_gb,
    parse_print_speed_ppm,
    parse_rack_units,
    parse_screen_size_inches_value,
    parse_storage_gb,
    parse_team_size,
    parse_throughput_mbps,
    parse_vpn_user_capacity,
    parse_weight_kg_value,
)


SCHEMA_KEYS = [
    "raw_chat",
    "company_size",
    "industry",
    "business_type",
    "team_size",
    "workload_types",
    "application_signals",
    "capability_tags",
    "budget",
    "budget_scope",
    "growth_expectation",
    "existing_infrastructure",
    "preferred_category",
    "preferred_manufacturers",
    "blocked_manufacturers",
    "preferred_sellers",
    "blocked_sellers",
    "performance_priority",
    "portability_need",
    "support_expectation",
    "availability_need",
    "require_returnable",
    "quantity",
    "purchase_scope",
    "rollout_type",
    "replacement_mode",
    "timeline",
    "requested_ram",
    "requested_storage",
    "requested_ram_is_minimum",
    "requested_storage_is_minimum",
    "minimum_warranty_years",
    "required_port_count",
    "required_throughput_mbps",
    "required_duplex_printing",
    "required_scanner",
    "min_print_speed_ppm",
    "required_printer_type",
    "required_print_technology",
    "required_color_output",
    "min_monthly_duty_cycle_pages",
    "required_automatic_document_feeder",
    "required_paper_sizes",
    "required_network_roles",
    "required_vpn_user_capacity",
    "required_virtualization_ready",
    "required_virtualization_platforms",
    "max_rack_units",
    "max_power_draw_watts",
    "battery_life_hours_min",
    "cpu_preference",
    "gpu_requirement",
    "screen_size_preference",
    "weight_kg_max",
    "warranty_type_preference",
    "notes",
    "missing_fields",
    "intake_confidence",
]

FAST_SCHEMA_KEYS = [
    "industry",
    "business_type",
    "workload_types",
    "application_signals",
    "capability_tags",
    "growth_expectation",
    "existing_infrastructure",
    "preferred_category",
    "preferred_manufacturers",
    "blocked_manufacturers",
    "preferred_sellers",
    "blocked_sellers",
    "performance_priority",
    "portability_need",
    "support_expectation",
    "availability_need",
    "require_returnable",
    "rollout_type",
    "replacement_mode",
    "timeline",
]

KNOWN_MANUFACTURERS = [
    "Dell",
    "Lenovo",
    "HP",
    "HPE",
    "Cisco",
    "Fortinet",
    "Acer",
    "Asus",
    "Aruba",
    "TP-Link",
]

KNOWN_SELLERS = [
    "TechPay Official",
    "TechPay Partner One",
    "TechPay Partner Two",
    "TechPay Alpha",
]


def _parse_warranty_years_value(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().lower()
    match = re.search(r"(\d+)\s*(?:year|yr)", text)
    if match:
        return int(match.group(1))
    digits = re.findall(r"\d+", text)
    return int(digits[0]) if digits else None


def _parse_intake_integer(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    digits = re.findall(r"\d+", str(value))
    return int(digits[0]) if digits else None

class RequirementExtractionService:
    CRITICAL_FIELDS = ["preferred_category", "workload_types", "budget"]
    DEEP_COMPLEXITY_THRESHOLD = 3
    FAST_PATH_MAX_TOKENS = 512
    DEEP_PATH_MAX_TOKENS = 1024
    EXTRACTION_REASONING_EFFORT = "low"

    def __init__(self, llm_client=None, config_service=None, signal_service=None):
        self.llm_client = llm_client or OptionalLLMClient()
        self.config_service = config_service or ProcurementConfigService()
        self.signal_service = signal_service or ProcurementSignalService(config_service=self.config_service)
        self.intake_service = RequirementIntakeService(signal_service=self.signal_service)
        self.clarification_service = ProcurementClarificationService(config_service=self.config_service)
        self.last_timing = {}


class ProcurementSchemaExtractor(RequirementExtractionService):
    """Compatibility alias for fallback and raw-chat extraction use cases."""

    def extract(self, chat_text="", context=None):
        context = dict(context or {})
        chat_text = str(chat_text or "").strip()
        timings = {}

        started_at = perf_counter()
        fast_path_result = self._try_direct_reply_fastpath(chat_text, context)
        if fast_path_result is not None:
            deterministic, deterministic_field_sources = self._deterministic_extract(chat_text, context=context)
            merged = {**context, **deterministic, **fast_path_result}
            merged["raw_chat"] = self._merge_raw_chat(context.get("raw_chat", ""), chat_text)
            merged["missing_fields"] = self._compute_missing_fields(merged)
            merged["intake_confidence"] = self._estimate_confidence(merged, False)
            serializer = ExtractedRequirementSerializer(data=merged)
            serializer.is_valid(raise_exception=True)
            validated = dict(serializer.validated_data)
            combined_field_sources = {
                **dict(deterministic_field_sources or {}),
                **{key: "direct_reply_fastpath" for key in fast_path_result.keys()},
            }
            validated["field_source_hints"] = self._build_field_source_hints(
                validated,
                context=context,
                deterministic_payload={**dict(deterministic or {}), **dict(fast_path_result or {})},
                deterministic_field_sources=combined_field_sources,
                llm_payload={},
            )
            timings["direct_reply_fastpath_ms"] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)
            timings["total_ms"] = round(sum(timings.values()), 2)
            self.last_timing = {
                **timings,
                "llm_prompt_name": "",
                "llm_prompt_mode": "direct_reply_fastpath",
                "llm_route_reasons": ["direct_reply_fastpath"],
                "llm_schema_key_count": 0,
                "llm_request_options": {},
                "llm_skipped": True,
            }
            return validated

        started_at = perf_counter()
        deterministic, deterministic_field_sources = self._deterministic_extract(chat_text, context=context)
        timings["deterministic_extract_ms"] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)
        llm_skipped = self._should_skip_llm_for_clarification_turn(chat_text, context, deterministic)
        llm_raw_payload = None
        if llm_skipped:
            timings["llm_extract_ms"] = 0.0
            self.last_timing = {
                "llm_prompt_name": "",
                "llm_prompt_mode": "skipped",
                "llm_route_reasons": ["clarification_only_turn"],
                "llm_schema_key_count": 0,
                "llm_request_options": {},
                "llm_skipped": True,
            }
        else:
            started_at = perf_counter()
            llm_raw_payload = self._llm_extract(chat_text, context=context)
            timings["llm_extract_ms"] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)
            self.last_timing["llm_skipped"] = False
        llm_route_metadata = {
            "llm_prompt_name": self.last_timing.get("llm_prompt_name"),
            "llm_prompt_mode": self.last_timing.get("llm_prompt_mode"),
            "llm_route_reasons": list(self.last_timing.get("llm_route_reasons") or []),
            "llm_schema_key_count": self.last_timing.get("llm_schema_key_count"),
            "llm_request_options": dict(self.last_timing.get("llm_request_options") or {}),
            "llm_skipped": bool(self.last_timing.get("llm_skipped")),
        }

        started_at = perf_counter()
        llm_payload = self._sanitize_llm_payload(
            llm_raw_payload,
            chat_text=chat_text,
            context=context,
            deterministic_payload=deterministic,
        )
        timings["sanitize_llm_payload_ms"] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)

        started_at = perf_counter()
        merged = self._merge_payloads(context, llm_payload or {}, deterministic)
        merged = self._canonicalize_payload(
            merged,
            chat_text=chat_text,
            context=context,
            deterministic_payload=deterministic,
        )
        merged["raw_chat"] = self._merge_raw_chat(context.get("raw_chat", ""), chat_text)
        merged["missing_fields"] = self._compute_missing_fields(merged)
        merged["intake_confidence"] = self._estimate_confidence(merged, bool(llm_payload))
        field_source_hints = self._build_field_source_hints(
            merged,
            context=context,
            deterministic_payload=deterministic,
            deterministic_field_sources=deterministic_field_sources,
            llm_payload=llm_payload or {},
        )
        timings["merge_and_enrich_ms"] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)

        started_at = perf_counter()
        serializer = ExtractedRequirementSerializer(data=merged)
        if serializer.is_valid():
            validated = dict(serializer.validated_data)
            validated["field_source_hints"] = field_source_hints
            timings["serializer_ms"] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)
            timings["total_ms"] = round(sum(timings.values()), 2)
            self.last_timing = {**timings, **llm_route_metadata}
            return validated

        timings["serializer_ms"] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)

        started_at = perf_counter()
        fallback = self._merge_payloads(context, {}, deterministic)
        fallback["raw_chat"] = merged["raw_chat"]
        fallback["missing_fields"] = self._compute_missing_fields(fallback)
        fallback["intake_confidence"] = self._estimate_confidence(fallback, False)
        serializer = ExtractedRequirementSerializer(data=fallback)
        serializer.is_valid(raise_exception=True)
        validated = dict(serializer.validated_data)
        validated["field_source_hints"] = self._build_field_source_hints(
            validated,
            context=context,
            deterministic_payload=deterministic,
            deterministic_field_sources=deterministic_field_sources,
            llm_payload={},
        )
        timings["fallback_serializer_ms"] = max(round((perf_counter() - started_at) * 1000, 2), 0.0)
        timings["total_ms"] = round(sum(timings.values()), 2)
        self.last_timing = {**timings, **llm_route_metadata}
        return validated

    def build_procurement_payload(self, extracted_schema, base_payload=None):
        extracted_schema = dict(extracted_schema or {})
        base_payload = dict(base_payload or {})
        payload = dict(base_payload)
        base_field_source_hints = dict(base_payload.get("_field_source_hints") or {})
        field_source_hints = {
            **base_field_source_hints,
            **dict(extracted_schema.get("field_source_hints") or {}),
        }
        explicit_payload_fields = set(base_payload.get("_explicit_payload_fields") or [])
        if explicit_payload_fields:
            payload["_explicit_payload_fields"] = sorted(
                key
                for key in explicit_payload_fields
                if key != "extracted_schema" and self._value_present(base_payload.get(key))
            )
        else:
            payload["_explicit_payload_fields"] = sorted(
                key
                for key, value in base_payload.items()
                if key != "extracted_schema" and self._value_present(value)
            )

        preferred_category = extracted_schema.get("preferred_category")
        if preferred_category and not payload.get("category") and not payload.get("preferred_category"):
            payload["category"] = preferred_category

        if extracted_schema.get("industry") and not payload.get("industry"):
            payload["industry"] = extracted_schema["industry"]
        if extracted_schema.get("business_type") and not payload.get("business_type"):
            payload["business_type"] = extracted_schema["business_type"]
        if extracted_schema.get("team_size") and not payload.get("team_size"):
            payload["team_size"] = extracted_schema["team_size"]
        if extracted_schema.get("workload_types") and not (payload.get("workload_types") or payload.get("workloads")):
            payload["workload_types"] = extracted_schema["workload_types"]
        if extracted_schema.get("application_signals") and not payload.get("application_signals"):
            payload["application_signals"] = extracted_schema["application_signals"]
        if extracted_schema.get("capability_tags") and not payload.get("capability_tags"):
            payload["capability_tags"] = extracted_schema["capability_tags"]
        if extracted_schema.get("budget") is not None and payload.get("budget") is None:
            payload["budget"] = extracted_schema["budget"]
        if extracted_schema.get("budget_scope") and not payload.get("budget_scope"):
            payload["budget_scope"] = extracted_schema["budget_scope"]
        if extracted_schema.get("growth_expectation") and not payload.get("growth_expectation"):
            payload["growth_expectation"] = extracted_schema["growth_expectation"]
        if extracted_schema.get("existing_infrastructure") and not payload.get("existing_infrastructure"):
            payload["existing_infrastructure"] = extracted_schema["existing_infrastructure"]
        if extracted_schema.get("preferred_manufacturers") and not payload.get("preferred_manufacturers"):
            payload["preferred_manufacturers"] = extracted_schema["preferred_manufacturers"]
        if extracted_schema.get("blocked_manufacturers") and not payload.get("blocked_manufacturers"):
            payload["blocked_manufacturers"] = extracted_schema["blocked_manufacturers"]
        if extracted_schema.get("preferred_sellers") and not payload.get("preferred_sellers"):
            payload["preferred_sellers"] = extracted_schema["preferred_sellers"]
        if extracted_schema.get("blocked_sellers") and not payload.get("blocked_sellers"):
            payload["blocked_sellers"] = extracted_schema["blocked_sellers"]
        if extracted_schema.get("requested_ram") and not (
            payload.get("requested_ram") or payload.get("specifications.ram_size")
        ):
            payload["requested_ram"] = extracted_schema["requested_ram"]
        if extracted_schema.get("requested_storage") and not (
            payload.get("requested_storage") or payload.get("specifications.storage_size")
        ):
            payload["requested_storage"] = extracted_schema["requested_storage"]
        if extracted_schema.get("requested_ram_is_minimum") is not None and payload.get("requested_ram_is_minimum") is None:
            payload["requested_ram_is_minimum"] = extracted_schema["requested_ram_is_minimum"]
        if extracted_schema.get("requested_storage_is_minimum") is not None and payload.get("requested_storage_is_minimum") is None:
            payload["requested_storage_is_minimum"] = extracted_schema["requested_storage_is_minimum"]
        if extracted_schema.get("minimum_warranty_years") is not None and payload.get("minimum_warranty_years") is None:
            payload["minimum_warranty_years"] = extracted_schema["minimum_warranty_years"]
        if extracted_schema.get("required_port_count") is not None and payload.get("required_port_count") is None:
            payload["required_port_count"] = extracted_schema["required_port_count"]
        if extracted_schema.get("required_throughput_mbps") is not None and payload.get("required_throughput_mbps") is None:
            payload["required_throughput_mbps"] = extracted_schema["required_throughput_mbps"]
        if extracted_schema.get("required_duplex_printing") is not None and payload.get("required_duplex_printing") is None:
            payload["required_duplex_printing"] = extracted_schema["required_duplex_printing"]
        if extracted_schema.get("required_scanner") is not None and payload.get("required_scanner") is None:
            payload["required_scanner"] = extracted_schema["required_scanner"]
        if extracted_schema.get("min_print_speed_ppm") is not None and payload.get("min_print_speed_ppm") is None:
            payload["min_print_speed_ppm"] = extracted_schema["min_print_speed_ppm"]
        if extracted_schema.get("required_printer_type") and not payload.get("required_printer_type"):
            payload["required_printer_type"] = extracted_schema["required_printer_type"]
        if extracted_schema.get("required_print_technology") and not payload.get("required_print_technology"):
            payload["required_print_technology"] = extracted_schema["required_print_technology"]
        if extracted_schema.get("required_color_output") and not payload.get("required_color_output"):
            payload["required_color_output"] = extracted_schema["required_color_output"]
        if extracted_schema.get("min_monthly_duty_cycle_pages") is not None and payload.get("min_monthly_duty_cycle_pages") is None:
            payload["min_monthly_duty_cycle_pages"] = extracted_schema["min_monthly_duty_cycle_pages"]
        if extracted_schema.get("required_automatic_document_feeder") is not None and payload.get("required_automatic_document_feeder") is None:
            payload["required_automatic_document_feeder"] = extracted_schema["required_automatic_document_feeder"]
        if extracted_schema.get("required_paper_sizes") and not payload.get("required_paper_sizes"):
            payload["required_paper_sizes"] = extracted_schema["required_paper_sizes"]
        if extracted_schema.get("required_network_roles") and not payload.get("required_network_roles"):
            payload["required_network_roles"] = extracted_schema["required_network_roles"]
        if extracted_schema.get("required_vpn_user_capacity") is not None and payload.get("required_vpn_user_capacity") is None:
            payload["required_vpn_user_capacity"] = extracted_schema["required_vpn_user_capacity"]
        if extracted_schema.get("required_virtualization_ready") is not None and payload.get("required_virtualization_ready") is None:
            payload["required_virtualization_ready"] = extracted_schema["required_virtualization_ready"]
        if extracted_schema.get("required_virtualization_platforms") and not payload.get("required_virtualization_platforms"):
            payload["required_virtualization_platforms"] = extracted_schema["required_virtualization_platforms"]
        if extracted_schema.get("max_rack_units") is not None and payload.get("max_rack_units") is None:
            payload["max_rack_units"] = extracted_schema["max_rack_units"]
        if extracted_schema.get("max_power_draw_watts") is not None and payload.get("max_power_draw_watts") is None:
            payload["max_power_draw_watts"] = extracted_schema["max_power_draw_watts"]
        if extracted_schema.get("battery_life_hours_min") is not None and payload.get("battery_life_hours_min") is None:
            payload["battery_life_hours_min"] = extracted_schema["battery_life_hours_min"]
        if extracted_schema.get("cpu_preference") and not payload.get("cpu_preference"):
            payload["cpu_preference"] = extracted_schema["cpu_preference"]
        if extracted_schema.get("gpu_requirement") and not payload.get("gpu_requirement"):
            payload["gpu_requirement"] = extracted_schema["gpu_requirement"]
        if extracted_schema.get("screen_size_preference") and not payload.get("screen_size_preference"):
            payload["screen_size_preference"] = extracted_schema["screen_size_preference"]
        if extracted_schema.get("weight_kg_max") is not None and payload.get("weight_kg_max") is None:
            payload["weight_kg_max"] = extracted_schema["weight_kg_max"]
        if extracted_schema.get("warranty_type_preference") and not payload.get("warranty_type_preference"):
            payload["warranty_type_preference"] = extracted_schema["warranty_type_preference"]
        if extracted_schema.get("performance_priority") and not payload.get("performance_priority"):
            payload["performance_priority"] = extracted_schema["performance_priority"]
        if extracted_schema.get("portability_need") and not payload.get("portability_need"):
            payload["portability_need"] = extracted_schema["portability_need"]
        if extracted_schema.get("support_expectation") and not payload.get("support_expectation"):
            payload["support_expectation"] = extracted_schema["support_expectation"]
        if extracted_schema.get("availability_need") and not payload.get("availability_need"):
            payload["availability_need"] = extracted_schema["availability_need"]
        if extracted_schema.get("require_returnable") is not None and payload.get("require_returnable") is None:
            payload["require_returnable"] = extracted_schema["require_returnable"]
        if extracted_schema.get("quantity") and not payload.get("quantity"):
            payload["quantity"] = extracted_schema["quantity"]
        if extracted_schema.get("purchase_scope") and not payload.get("purchase_scope"):
            payload["purchase_scope"] = extracted_schema["purchase_scope"]
        if extracted_schema.get("rollout_type") and not payload.get("rollout_type"):
            payload["rollout_type"] = extracted_schema["rollout_type"]
        if extracted_schema.get("replacement_mode") and not payload.get("replacement_mode"):
            payload["replacement_mode"] = extracted_schema["replacement_mode"]
        if extracted_schema.get("timeline") and not payload.get("timeline"):
            payload["timeline"] = extracted_schema["timeline"]

        existing_notes = str(payload.get("notes") or "").strip()
        extracted_notes = str(extracted_schema.get("notes") or "").strip()
        combined_notes = self._merge_text_fragments(existing_notes, extracted_notes, separator=" ")
        if combined_notes:
            payload["notes"] = combined_notes

        payload["chat_text"] = extracted_schema.get("raw_chat", "")
        payload["budget_scope"] = payload.get("budget_scope") or normalize_budget_scope(
            payload.get("budget_scope"),
            preferred_categories=[preferred_category] if preferred_category else [],
            hint_text=payload.get("chat_text") or extracted_schema.get("notes") or "",
            quantity=payload.get("quantity") or extracted_schema.get("quantity"),
        )
        payload["_field_source_hints"] = field_source_hints
        return payload

    def _llm_extract(self, chat_text, context):
        if not chat_text:
            return None

        prompt_name, prompt_mode, route_reasons = self._select_extraction_prompt(chat_text, context=context)
        schema_keys = self._schema_keys_for_prompt_mode(prompt_mode)
        request_options = self._request_options_for_prompt_mode(prompt_mode)
        variables = {
            "known_context": json.dumps(context, ensure_ascii=True),
            "chat_text": chat_text,
            "schema_keys": json.dumps(schema_keys, ensure_ascii=True),
        }
        payload = self.llm_client.invoke_json(
            prompt_name,
            variables,
            request_options=request_options,
        )
        self.last_timing = {
            **dict(self.last_timing or {}),
            "llm_prompt_name": prompt_name,
            "llm_prompt_mode": prompt_mode,
            "llm_route_reasons": list(route_reasons),
            "llm_schema_key_count": len(schema_keys),
            "llm_request_options": dict(request_options),
        }
        return payload if isinstance(payload, dict) else None

    def _schema_keys_for_prompt_mode(self, prompt_mode):
        if str(prompt_mode or "").strip().lower() == "fast":
            return list(FAST_SCHEMA_KEYS)
        return list(SCHEMA_KEYS)

    def _request_options_for_prompt_mode(self, prompt_mode):
        prompt_mode = str(prompt_mode or "").strip().lower()
        return {
            "reasoning_effort": self.EXTRACTION_REASONING_EFFORT,
            "timeout_sec": OptionalLLMClient.EXTRACTION_TIMEOUT_SEC,
            "max_tokens": self.FAST_PATH_MAX_TOKENS if prompt_mode == "fast" else self.DEEP_PATH_MAX_TOKENS,
        }

    def _select_extraction_prompt(self, chat_text, context=None):
        chat_text = str(chat_text or "").strip()
        context = dict(context or {})
        lowered = chat_text.lower()
        words = re.findall(r"\b\w+\b", lowered)
        complexity = 0
        reasons = []

        category_hits = sum(
            1 for pattern in ("laptop", "desktop", "server", "printer", "firewall", "switch", "router", "access point")
            if pattern in lowered
        )
        multi_track_markers = (
            " and also ",
            " plus ",
            " while ",
            " along with ",
            " as well as ",
        )
        ambiguity_markers = (
            "not sure",
            "maybe",
            "something like",
            "sort of",
            "kind of",
            "same as before",
            "same as last time",
            "that one",
            "those ones",
        )

        if len(words) >= 35 or len(chat_text) >= 220:
            complexity += 1
            reasons.append("long_message")
        if category_hits >= 2:
            complexity += 2
            reasons.append("multi_category_signals")
        if sum(1 for marker in multi_track_markers if marker in lowered) >= 1:
            complexity += 1
            reasons.append("multi_track_language")
        if chat_text.count(",") >= 3:
            complexity += 1
            reasons.append("many_clauses")
        if any(marker in lowered for marker in ambiguity_markers):
            complexity += 1
            reasons.append("ambiguous_language")
        if context and len(words) <= 8 and not self._looks_like_direct_value_reply(lowered):
            complexity += 1
            reasons.append("short_contextual_followup")

        if complexity >= self.DEEP_COMPLEXITY_THRESHOLD:
            return "requirement_extraction.txt", "deep", reasons
        return "requirement_extraction_fast.txt", "fast", reasons or ["simple_message"]

    def _looks_like_direct_value_reply(self, lowered):
        lowered = str(lowered or "").lower()
        if self._detect_budget_from_chat(lowered) is not None:
            return True
        if parse_team_size(lowered) is not None:
            return True
        if normalize_category(lowered):
            return True
        if normalize_workloads(lowered):
            return True
        direct_markers = (
            "under ",
            "budget",
            "users",
            "people",
            "staff",
            "developers",
            "designers",
            "laptops",
            "desktops",
            "servers",
            "printers",
            "networking",
        )
        return any(marker in lowered for marker in direct_markers)

    def _try_direct_reply_fastpath(self, chat_text, context):
        chat_text = str(chat_text or "").strip()
        if not chat_text:
            return None

        lowered = chat_text.lower()
        last_field = str(context.get("_last_asked_field") or "").strip().lower()

        if last_field == "team_size":
            parsed = parse_team_size(chat_text)
            if parsed and len(chat_text.split()) <= 3:
                return {"team_size": parsed, "quantity": parsed}

        budget = self._detect_budget_from_chat(chat_text)
        if budget is not None and len(chat_text.split()) <= 5:
            result = {"budget": budget}
            budget_scope = self._detect_explicit_budget_scope(chat_text)
            if budget_scope:
                result["budget_scope"] = budget_scope
            return result

        direct_budget = self._parse_direct_budget_value(chat_text)
        explicit_budget_markers = (
            "budget",
            "rs",
            "inr",
            "usd",
            "eur",
            "gbp",
            "myr",
            "$",
            "k",
            "lakh",
            "thousand",
            "each",
            "per unit",
            "per device",
            "per seat",
            "total",
            "overall",
            "project",
            "combined",
        )
        budget_word_limit = 8 if last_field in {"budget", "budget_scope"} else 5
        if (
            direct_budget is not None
            and len(chat_text.split()) <= budget_word_limit
            and any(marker in lowered for marker in explicit_budget_markers)
        ):
            result = {"budget": direct_budget}
            budget_scope = self._detect_explicit_budget_scope(chat_text)
            if budget_scope:
                result["budget_scope"] = budget_scope
            return result

        if last_field in {"budget_scope", "budget"}:
            budget_scope = self._detect_explicit_budget_scope(chat_text)
            if budget_scope:
                return {"budget_scope": budget_scope}

        if last_field in {"preferred_category", "category_or_workload"}:
            category = self._normalize_direct_reply_category(chat_text)
            if category:
                return {"preferred_category": category}

        if last_field == "performance_priority" and lowered in {"cost", "balanced", "performance"}:
            return {"performance_priority": lowered}

        return None

    def _detect_explicit_budget_scope(self, chat_text):
        lowered = str(chat_text or "").strip().lower()
        if not lowered:
            return None

        total_markers = ("total", "overall", "project", "combined")
        per_unit_markers = ("each", "per unit", "per device", "per seat")
        if any(marker in lowered for marker in total_markers):
            return "project_total"
        if any(marker in lowered for marker in per_unit_markers):
            return "per_unit"
        return None

    def _parse_direct_budget_value(self, chat_text):
        chat_text = str(chat_text or "").strip()
        if not chat_text:
            return None

        parsed = parse_money_value(chat_text)
        if parsed is not None:
            return parsed

        money_match = re.search(
            r"(\d[\d,]*(?:\.\d+)?(?:\s?(?:k|lakh|thousand|thousands))?)",
            chat_text.lower(),
        )
        if not money_match:
            return None
        return parse_money_value(money_match.group(1))

    def _normalize_direct_reply_category(self, chat_text):
        category = normalize_category(chat_text)
        if category:
            return category

        lowered = str(chat_text or "").strip().lower()
        if not lowered:
            return None

        canonical_categories = [
            "laptops",
            "desktops",
            "servers",
            "networking",
            "printers",
            "accessories",
        ]
        closest = get_close_matches(lowered, canonical_categories, n=1, cutoff=0.7)
        return closest[0] if closest else None

    def _deterministic_extract(self, chat_text, context):
        chat_text = str(chat_text or "").strip()
        lowered = chat_text.lower()
        merged_chat_text = self._merge_raw_chat(context.get("raw_chat", ""), chat_text)
        signal_matches = self.signal_service.extract(chat_text)

        team_size_from_chat = self._detect_team_size_from_chat(chat_text)
        team_size = team_size_from_chat
        if team_size is None and context and context.get("team_size"):
            team_size = parse_team_size(context.get("team_size"))
        preferred_category = self._detect_preferred_category(chat_text)
        category_for_inference = preferred_category or normalize_category(context.get("preferred_category"))
        explicit_workload_types = normalize_workloads(chat_text)
        if self._is_generic_office_prompt(lowered):
            explicit_workload_types = []
        workload_types = self._merge_list_values(explicit_workload_types, signal_matches.get("workload_types"))
        if (
            "server_infrastructure" not in workload_types
            and any(token in lowered for token in {"back-room compute", "back room compute", "back-room host", "back room host", "local host", "small host"})
        ):
            workload_types.append("server_infrastructure")
        if (
            "network_connectivity" not in workload_types
            and any(token in lowered for token in {"connectivity", "secure connectivity", "site connectivity"})
        ):
            workload_types.append("network_connectivity")
        workload_types = self._align_workloads_with_category(preferred_category, workload_types, lowered)
        if self._is_generic_office_prompt(lowered):
            workload_types = []
        workloads_for_inference = self._merge_list_values(
            normalize_workloads(context.get("workload_types") or context.get("workloads")),
            workload_types,
        )
        budget_from_chat = self._detect_budget_from_chat(chat_text)
        budget = budget_from_chat if budget_from_chat is not None else self._detect_budget(chat_text, context=context)
        requested_ram = self._detect_requested_ram(chat_text)
        requested_storage = self._detect_requested_storage(chat_text)
        requested_ram_is_minimum = self._detect_spec_requirement_strength(lowered, "ram") if requested_ram else None
        requested_storage_is_minimum = self._detect_spec_requirement_strength(lowered, "storage") if requested_storage else None
        minimum_warranty_years = self._detect_minimum_warranty_years(chat_text)
        required_port_count = self._detect_required_port_count(chat_text)
        required_throughput_mbps = self._detect_required_throughput_mbps(chat_text)
        required_duplex_printing = self._detect_required_duplex_printing(lowered)
        required_scanner = self._detect_required_scanner(lowered)
        min_print_speed_ppm = self._detect_min_print_speed_ppm(chat_text)
        required_printer_type = self._detect_required_printer_type(lowered)
        required_print_technology = self._detect_required_print_technology(lowered)
        required_color_output = self._detect_required_color_output(lowered)
        min_monthly_duty_cycle_pages = self._detect_min_monthly_duty_cycle_pages(chat_text)
        required_automatic_document_feeder = self._detect_required_automatic_document_feeder(lowered)
        required_paper_sizes = self._detect_required_paper_sizes(chat_text)
        required_network_roles = self._detect_required_network_roles(lowered)
        required_vpn_user_capacity = self._detect_required_vpn_user_capacity(chat_text)
        required_virtualization_ready = self._detect_required_virtualization_ready(lowered)
        required_virtualization_platforms = self._detect_required_virtualization_platforms(chat_text)
        max_rack_units = self._detect_max_rack_units(chat_text)
        max_power_draw_watts = self._detect_max_power_draw_watts(chat_text)
        battery_life_hours_min = self._detect_battery_life_hours_min(chat_text)
        cpu_preference = self._detect_cpu_preference(chat_text)
        gpu_requirement = self._detect_gpu_requirement(chat_text)
        screen_size_preference = self._detect_screen_size_preference(chat_text)
        weight_kg_max = self._detect_weight_kg_max(chat_text)
        warranty_type_preference = self._detect_warranty_type_preference(chat_text)
        preferred_manufacturers, blocked_manufacturers = self._detect_manufacturer_preferences(chat_text)
        preferred_sellers, blocked_sellers = self._detect_seller_preferences(chat_text)

        industry = self._detect_industry(lowered)
        business_type = self._detect_business_type(lowered, context=context)
        performance_priority = self._detect_performance_priority(lowered)
        portability_need = self._detect_portability_need(lowered)
        support_expectation = self._detect_support_expectation(lowered)
        availability_need = self._detect_availability_need(lowered)
        rollout_type = self._detect_rollout_type(lowered)
        replacement_mode = self._detect_replacement_mode(lowered)
        timeline = self._detect_timeline(chat_text)
        quantity, quantity_source = self._detect_quantity(
            merged_chat_text,
            team_size,
            category_for_inference,
            workloads_for_inference,
        )
        purchase_scope = normalize_purchase_scope(
            None,
            preferred_categories=[category_for_inference] if category_for_inference else [],
            quantity=quantity,
            team_size=team_size,
            hint_text=merged_chat_text,
        )
        existing_infrastructure = self._detect_existing_infrastructure(chat_text)
        require_returnable = self._detect_require_returnable(lowered)
        application_signals = signal_matches.get("application_signals") or []
        growth_expectation = self._detect_growth_expectation(lowered)
        capability_tags = self._derive_capability_tags(
            preferred_category=preferred_category,
            workload_types=workload_types,
            application_signals=application_signals,
            signal_capability_tags=signal_matches.get("capability_tags"),
            requested_ram=requested_ram,
            requested_storage=requested_storage,
            portability_need=portability_need,
            support_expectation=support_expectation,
            availability_need=availability_need,
            existing_infrastructure=existing_infrastructure,
            lowered=lowered,
        )

        team_size_source = "user_explicit" if team_size_from_chat is not None else None
        if not team_size and category_for_inference in {"laptops", "desktops"} and quantity:
            team_size = quantity
            team_size_source = "rule_inferred"

        company_size = self._company_size_from_team_size(team_size or context.get("team_size"))
        business_type = business_type or ("smb" if industry else context.get("business_type"))

        deterministic_payload = {
            "company_size": company_size,
            "industry": industry,
            "business_type": business_type,
            "team_size": team_size,
            "workload_types": workload_types,
            "application_signals": application_signals,
            "capability_tags": capability_tags,
            "budget": budget,
            "growth_expectation": growth_expectation,
            "existing_infrastructure": existing_infrastructure,
            "preferred_category": preferred_category,
            "preferred_manufacturers": preferred_manufacturers,
            "blocked_manufacturers": blocked_manufacturers,
            "preferred_sellers": preferred_sellers,
            "blocked_sellers": blocked_sellers,
            "performance_priority": performance_priority,
            "portability_need": portability_need,
            "support_expectation": support_expectation,
            "availability_need": availability_need,
            "require_returnable": require_returnable,
            "quantity": quantity,
            "purchase_scope": purchase_scope,
            "rollout_type": rollout_type,
            "replacement_mode": replacement_mode,
            "timeline": timeline,
            "requested_ram": f"{requested_ram}GB" if requested_ram else None,
            "requested_storage": self._format_storage(requested_storage),
            "requested_ram_is_minimum": requested_ram_is_minimum,
            "requested_storage_is_minimum": requested_storage_is_minimum,
            "minimum_warranty_years": minimum_warranty_years,
            "required_port_count": required_port_count,
            "required_throughput_mbps": required_throughput_mbps,
            "required_duplex_printing": required_duplex_printing,
            "required_scanner": required_scanner,
            "min_print_speed_ppm": min_print_speed_ppm,
            "required_printer_type": required_printer_type,
            "required_print_technology": required_print_technology,
            "required_color_output": required_color_output,
            "min_monthly_duty_cycle_pages": min_monthly_duty_cycle_pages,
            "required_automatic_document_feeder": required_automatic_document_feeder,
            "required_paper_sizes": required_paper_sizes,
            "required_network_roles": required_network_roles,
            "required_vpn_user_capacity": required_vpn_user_capacity,
            "required_virtualization_ready": required_virtualization_ready,
            "required_virtualization_platforms": required_virtualization_platforms,
            "max_rack_units": max_rack_units,
            "max_power_draw_watts": max_power_draw_watts,
            "battery_life_hours_min": battery_life_hours_min,
            "cpu_preference": cpu_preference,
            "gpu_requirement": gpu_requirement,
            "screen_size_preference": screen_size_preference,
            "weight_kg_max": weight_kg_max,
            "warranty_type_preference": warranty_type_preference,
            "notes": chat_text,
        }
        deterministic_field_sources = {
            "company_size": "rule_inferred" if company_size else None,
            "industry": "user_explicit" if industry else None,
            "business_type": "rule_inferred" if business_type else None,
            "team_size": team_size_source,
            "workload_types": (
                "user_explicit"
                if explicit_workload_types
                else ("rule_inferred" if workload_types else None)
            ),
            "application_signals": "rule_inferred" if application_signals else None,
            "capability_tags": "rule_inferred" if capability_tags else None,
            "budget": "user_explicit" if budget_from_chat is not None else None,
            "growth_expectation": "user_explicit" if growth_expectation else None,
            "existing_infrastructure": "user_explicit" if existing_infrastructure else None,
            "preferred_category": "user_explicit" if preferred_category else None,
            "preferred_manufacturers": "user_explicit" if preferred_manufacturers else None,
            "blocked_manufacturers": "user_explicit" if blocked_manufacturers else None,
            "preferred_sellers": "user_explicit" if preferred_sellers else None,
            "blocked_sellers": "user_explicit" if blocked_sellers else None,
            "performance_priority": "user_explicit" if performance_priority else None,
            "portability_need": "user_explicit" if portability_need else None,
            "support_expectation": "user_explicit" if support_expectation else None,
            "availability_need": "user_explicit" if availability_need else None,
            "require_returnable": "user_explicit" if require_returnable is not None else None,
            "quantity": quantity_source,
            "purchase_scope": "rule_inferred" if purchase_scope else None,
            "rollout_type": "user_explicit" if rollout_type else None,
            "replacement_mode": "user_explicit" if replacement_mode else None,
            "timeline": "user_explicit" if timeline else None,
            "requested_ram": "user_explicit" if requested_ram else None,
            "requested_storage": "user_explicit" if requested_storage else None,
            "requested_ram_is_minimum": "rule_inferred" if requested_ram_is_minimum is not None else None,
            "requested_storage_is_minimum": "rule_inferred" if requested_storage_is_minimum is not None else None,
            "minimum_warranty_years": "user_explicit" if minimum_warranty_years is not None else None,
            "required_port_count": "user_explicit" if required_port_count is not None else None,
            "required_throughput_mbps": "user_explicit" if required_throughput_mbps is not None else None,
            "required_duplex_printing": "user_explicit" if required_duplex_printing is not None else None,
            "required_scanner": "user_explicit" if required_scanner is not None else None,
            "min_print_speed_ppm": "user_explicit" if min_print_speed_ppm is not None else None,
            "required_printer_type": "user_explicit" if required_printer_type else None,
            "required_print_technology": "user_explicit" if required_print_technology else None,
            "required_color_output": "user_explicit" if required_color_output else None,
            "min_monthly_duty_cycle_pages": "user_explicit" if min_monthly_duty_cycle_pages is not None else None,
            "required_automatic_document_feeder": "user_explicit" if required_automatic_document_feeder is not None else None,
            "required_paper_sizes": "user_explicit" if required_paper_sizes else None,
            "required_network_roles": "user_explicit" if required_network_roles else None,
            "required_vpn_user_capacity": "user_explicit" if required_vpn_user_capacity is not None else None,
            "required_virtualization_ready": "user_explicit" if required_virtualization_ready is not None else None,
            "required_virtualization_platforms": "user_explicit" if required_virtualization_platforms else None,
            "max_rack_units": "user_explicit" if max_rack_units is not None else None,
            "max_power_draw_watts": "user_explicit" if max_power_draw_watts is not None else None,
            "battery_life_hours_min": "user_explicit" if battery_life_hours_min is not None else None,
            "cpu_preference": "user_explicit" if cpu_preference else None,
            "gpu_requirement": "user_explicit" if gpu_requirement else None,
            "screen_size_preference": "user_explicit" if screen_size_preference else None,
            "weight_kg_max": "user_explicit" if weight_kg_max is not None else None,
            "warranty_type_preference": "user_explicit" if warranty_type_preference else None,
            "notes": "rule_inferred" if chat_text else None,
        }
        deterministic_field_sources = {
            field: source
            for field, source in deterministic_field_sources.items()
            if source
        }

        return deterministic_payload, deterministic_field_sources

    def _sanitize_llm_payload(self, llm_payload, chat_text, context, deterministic_payload):
        if not isinstance(llm_payload, dict):
            return None

        sanitized = dict(llm_payload)
        sanitized["preferred_category"] = normalize_category(sanitized.get("preferred_category"))
        sanitized["workload_types"] = normalize_workloads(sanitized.get("workload_types"))
        sanitized["application_signals"] = self.signal_service.sanitize_application_signals(
            sanitized.get("application_signals")
        )
        sanitized["capability_tags"] = self.signal_service.sanitize_capability_tags(
            sanitized.get("capability_tags")
        )
        sanitized["team_size"] = parse_team_size(sanitized.get("team_size"))
        sanitized["quantity"] = parse_team_size(sanitized.get("quantity"))
        sanitized["industry"] = self._normalize_nullable_text(sanitized.get("industry"))
        sanitized["business_type"] = self._normalize_nullable_text(sanitized.get("business_type"))
        sanitized["rollout_type"] = normalize_rollout_type(sanitized.get("rollout_type"))
        sanitized["replacement_mode"] = normalize_replacement_mode(sanitized.get("replacement_mode"))
        sanitized["timeline"] = self._normalize_nullable_text(sanitized.get("timeline"))
        sanitized["notes"] = self._normalize_nullable_text(sanitized.get("notes"))
        sanitized["preferred_manufacturers"] = self._sanitize_named_list(
            sanitized.get("preferred_manufacturers"),
            KNOWN_MANUFACTURERS,
        )
        sanitized["blocked_manufacturers"] = self._sanitize_named_list(
            sanitized.get("blocked_manufacturers"),
            KNOWN_MANUFACTURERS,
        )
        sanitized["preferred_sellers"] = self._sanitize_named_list(
            sanitized.get("preferred_sellers"),
            KNOWN_SELLERS,
        )
        sanitized["blocked_sellers"] = self._sanitize_named_list(
            sanitized.get("blocked_sellers"),
            KNOWN_SELLERS,
        )
        sanitized["availability_need"] = normalize_availability_need(sanitized.get("availability_need"))
        sanitized["require_returnable"] = normalize_optional_bool(sanitized.get("require_returnable"))
        sanitized["purchase_scope"] = normalize_purchase_scope(
            sanitized.get("purchase_scope"),
            preferred_categories=[sanitized.get("preferred_category")] if sanitized.get("preferred_category") else [],
            quantity=sanitized.get("quantity"),
            team_size=sanitized.get("team_size"),
            hint_text=chat_text,
        )
        sanitized["budget"] = self._sanitize_budget_value(
            sanitized.get("budget"),
            chat_text=chat_text,
            context=context,
            team_size=sanitized.get("team_size") or deterministic_payload.get("team_size"),
        )
        sanitized["existing_infrastructure"] = self._merge_list_values(
            context.get("existing_infrastructure"),
            deterministic_payload.get("existing_infrastructure"),
        )

        requested_ram = parse_ram_gb(sanitized.get("requested_ram"))
        sanitized["requested_ram"] = f"{requested_ram}GB" if requested_ram else None
        sanitized["requested_ram_is_minimum"] = normalize_optional_bool(
            sanitized.get("requested_ram_is_minimum")
        )
        requested_storage = parse_storage_gb(sanitized.get("requested_storage"))
        sanitized["requested_storage"] = self._format_storage(requested_storage)
        sanitized["requested_storage_is_minimum"] = normalize_optional_bool(
            sanitized.get("requested_storage_is_minimum")
        )
        sanitized["minimum_warranty_years"] = _parse_warranty_years_value(sanitized.get("minimum_warranty_years"))
        sanitized["required_port_count"] = parse_port_count(sanitized.get("required_port_count"))
        sanitized["required_throughput_mbps"] = parse_throughput_mbps(sanitized.get("required_throughput_mbps"))
        sanitized["required_duplex_printing"] = normalize_optional_bool(
            sanitized.get("required_duplex_printing")
        )
        sanitized["required_scanner"] = normalize_optional_bool(sanitized.get("required_scanner"))
        sanitized["min_print_speed_ppm"] = parse_print_speed_ppm(sanitized.get("min_print_speed_ppm"))
        sanitized["required_printer_type"] = self._normalize_printer_type_value(sanitized.get("required_printer_type"))
        sanitized["required_print_technology"] = self._normalize_nullable_text(sanitized.get("required_print_technology"))
        sanitized["required_color_output"] = normalize_color_output(sanitized.get("required_color_output")) or None
        sanitized["min_monthly_duty_cycle_pages"] = parse_page_volume(sanitized.get("min_monthly_duty_cycle_pages"))
        sanitized["required_automatic_document_feeder"] = normalize_optional_bool(
            sanitized.get("required_automatic_document_feeder")
        )
        sanitized["required_paper_sizes"] = normalize_paper_sizes(sanitized.get("required_paper_sizes"))
        sanitized["required_network_roles"] = [
            role
            for role in normalize_text_list(sanitized.get("required_network_roles"))
            if role in {"router", "firewall", "switch", "access_point"}
        ]
        sanitized["required_vpn_user_capacity"] = parse_vpn_user_capacity(
            sanitized.get("required_vpn_user_capacity")
        )
        sanitized["required_virtualization_ready"] = normalize_optional_bool(
            sanitized.get("required_virtualization_ready")
        )
        sanitized["required_virtualization_platforms"] = normalize_virtualization_platforms(
            sanitized.get("required_virtualization_platforms")
        )
        sanitized["max_rack_units"] = parse_rack_units(sanitized.get("max_rack_units"))
        sanitized["max_power_draw_watts"] = parse_power_watts(sanitized.get("max_power_draw_watts"))
        sanitized["battery_life_hours_min"] = _parse_intake_integer(sanitized.get("battery_life_hours_min"))
        sanitized["cpu_preference"] = self._normalize_nullable_text(sanitized.get("cpu_preference"))
        sanitized["gpu_requirement"] = self._normalize_nullable_text(sanitized.get("gpu_requirement"))
        sanitized["screen_size_preference"] = self._normalize_screen_size_preference(
            sanitized.get("screen_size_preference")
        )
        sanitized["weight_kg_max"] = parse_weight_kg_value(sanitized.get("weight_kg_max"))
        sanitized["warranty_type_preference"] = normalize_warranty_type(
            sanitized.get("warranty_type_preference")
        )
        sanitized["preferred_category"] = self._normalize_llm_category(
            sanitized.get("preferred_category"),
            chat_text,
            sanitized.get("workload_types"),
            sanitized.get("application_signals"),
        )
        sanitized["workload_types"] = self._normalize_llm_workloads(
            sanitized.get("workload_types"),
            chat_text,
            sanitized.get("preferred_category"),
            sanitized.get("application_signals"),
        )
        return sanitized

    def _canonicalize_payload(self, payload, chat_text, context, deterministic_payload):
        merged = dict(payload or {})
        merged_chat_text = self._merge_raw_chat(context.get("raw_chat", ""), chat_text)
        merged_chat_lower = merged_chat_text.lower()
        merged["preferred_category"] = (
            normalize_category(merged.get("preferred_category"))
            or deterministic_payload.get("preferred_category")
            or normalize_category(context.get("preferred_category"))
        )
        merged["team_size"] = parse_team_size(merged.get("team_size"))
        merged["quantity"] = parse_team_size(merged.get("quantity"))
        merged["budget"] = self._sanitize_budget_value(
            merged.get("budget"),
            chat_text=chat_text,
            context=context,
            team_size=merged.get("team_size"),
        )
        merged["budget_scope"] = normalize_budget_scope(
            merged.get("budget_scope") or context.get("budget_scope"),
            preferred_categories=[merged.get("preferred_category")] if merged.get("preferred_category") else [],
            hint_text=merged_chat_text,
            quantity=merged.get("quantity"),
        )
        merged["rollout_type"] = (
            normalize_rollout_type(merged.get("rollout_type"))
            or deterministic_payload.get("rollout_type")
            or normalize_rollout_type(context.get("rollout_type"))
        )
        merged["replacement_mode"] = (
            normalize_replacement_mode(merged.get("replacement_mode"))
            or deterministic_payload.get("replacement_mode")
            or normalize_replacement_mode(context.get("replacement_mode"))
        )
        merged["purchase_scope"] = normalize_purchase_scope(
            merged.get("purchase_scope") or deterministic_payload.get("purchase_scope") or context.get("purchase_scope"),
            preferred_categories=[merged.get("preferred_category")] if merged.get("preferred_category") else [],
            quantity=merged.get("quantity"),
            team_size=merged.get("team_size"),
            hint_text=merged_chat_text,
        )

        canonical_workloads = normalize_workloads(merged.get("workload_types"))
        if not canonical_workloads:
            canonical_workloads = list(deterministic_payload.get("workload_types") or [])
        merged["workload_types"] = self._align_workloads_with_category(
            merged.get("preferred_category"),
            canonical_workloads,
            merged_chat_lower,
        )
        merged["application_signals"] = self._merge_list_values(
            context.get("application_signals"),
            self.signal_service.sanitize_application_signals(merged.get("application_signals")),
        )
        merged["capability_tags"] = self._merge_list_values(
            context.get("capability_tags"),
            self.signal_service.sanitize_capability_tags(merged.get("capability_tags")),
        )
        merged["capability_tags"] = self._derive_capability_tags(
            preferred_category=merged.get("preferred_category"),
            workload_types=merged.get("workload_types"),
            application_signals=merged.get("application_signals"),
            signal_capability_tags=merged.get("capability_tags"),
            requested_ram=parse_ram_gb(merged.get("requested_ram")),
            requested_storage=parse_storage_gb(merged.get("requested_storage")),
            portability_need=merged.get("portability_need"),
            support_expectation=merged.get("support_expectation"),
            availability_need=merged.get("availability_need"),
            existing_infrastructure=self._merge_list_values(
                context.get("existing_infrastructure"),
                deterministic_payload.get("existing_infrastructure"),
            ),
            lowered=merged_chat_lower,
        )
        merged["performance_priority"] = self._normalize_performance_priority_value(
            merged.get("performance_priority")
            or deterministic_payload.get("performance_priority")
            or context.get("performance_priority"),
            merged_chat_lower,
        )

        merged["existing_infrastructure"] = self._merge_list_values(
            context.get("existing_infrastructure"),
            deterministic_payload.get("existing_infrastructure"),
        )
        merged["preferred_manufacturers"] = self._merge_list_values(
            context.get("preferred_manufacturers"),
            merged.get("preferred_manufacturers"),
        )
        merged["blocked_manufacturers"] = self._merge_list_values(
            context.get("blocked_manufacturers"),
            merged.get("blocked_manufacturers"),
        )
        merged["preferred_sellers"] = self._merge_list_values(
            context.get("preferred_sellers"),
            merged.get("preferred_sellers"),
        )
        merged["blocked_sellers"] = self._merge_list_values(
            context.get("blocked_sellers"),
            merged.get("blocked_sellers"),
        )
        merged["availability_need"] = (
            normalize_availability_need(merged.get("availability_need"))
            or deterministic_payload.get("availability_need")
            or normalize_availability_need(context.get("availability_need"))
        )
        merged["require_returnable"] = self._first_non_none(
            normalize_optional_bool(merged.get("require_returnable")),
            deterministic_payload.get("require_returnable"),
            normalize_optional_bool(context.get("require_returnable")),
        )
        merged["requested_ram_is_minimum"] = self._first_non_none(
            normalize_optional_bool(merged.get("requested_ram_is_minimum")),
            deterministic_payload.get("requested_ram_is_minimum"),
            normalize_optional_bool(context.get("requested_ram_is_minimum")),
        )
        merged["requested_storage_is_minimum"] = self._first_non_none(
            normalize_optional_bool(merged.get("requested_storage_is_minimum")),
            deterministic_payload.get("requested_storage_is_minimum"),
            normalize_optional_bool(context.get("requested_storage_is_minimum")),
        )
        merged["minimum_warranty_years"] = self._first_non_none(
            _parse_warranty_years_value(merged.get("minimum_warranty_years")),
            deterministic_payload.get("minimum_warranty_years"),
            _parse_warranty_years_value(context.get("minimum_warranty_years")),
        )
        merged["required_port_count"] = self._first_non_none(
            parse_port_count(merged.get("required_port_count")),
            deterministic_payload.get("required_port_count"),
            parse_port_count(context.get("required_port_count")),
        )
        merged["required_throughput_mbps"] = self._first_non_none(
            parse_throughput_mbps(merged.get("required_throughput_mbps")),
            deterministic_payload.get("required_throughput_mbps"),
            parse_throughput_mbps(context.get("required_throughput_mbps")),
        )
        merged["required_duplex_printing"] = self._first_non_none(
            normalize_optional_bool(merged.get("required_duplex_printing")),
            deterministic_payload.get("required_duplex_printing"),
            normalize_optional_bool(context.get("required_duplex_printing")),
        )
        merged["required_scanner"] = self._first_non_none(
            normalize_optional_bool(merged.get("required_scanner")),
            deterministic_payload.get("required_scanner"),
            normalize_optional_bool(context.get("required_scanner")),
        )
        merged["min_print_speed_ppm"] = self._first_non_none(
            parse_print_speed_ppm(merged.get("min_print_speed_ppm")),
            deterministic_payload.get("min_print_speed_ppm"),
            parse_print_speed_ppm(context.get("min_print_speed_ppm")),
        )
        merged["required_printer_type"] = self._first_non_none(
            self._normalize_printer_type_value(merged.get("required_printer_type")),
            self._normalize_printer_type_value(deterministic_payload.get("required_printer_type")),
            self._normalize_printer_type_value(context.get("required_printer_type")),
        )
        merged["required_print_technology"] = self._first_non_none(
            self._normalize_nullable_text(merged.get("required_print_technology")),
            deterministic_payload.get("required_print_technology"),
            self._normalize_nullable_text(context.get("required_print_technology")),
        )
        merged["required_color_output"] = self._first_non_none(
            normalize_color_output(merged.get("required_color_output")) or None,
            deterministic_payload.get("required_color_output"),
            normalize_color_output(context.get("required_color_output")) or None,
        )
        merged["min_monthly_duty_cycle_pages"] = self._first_non_none(
            parse_page_volume(merged.get("min_monthly_duty_cycle_pages")),
            deterministic_payload.get("min_monthly_duty_cycle_pages"),
            parse_page_volume(context.get("min_monthly_duty_cycle_pages")),
        )
        merged["required_automatic_document_feeder"] = self._first_non_none(
            normalize_optional_bool(merged.get("required_automatic_document_feeder")),
            deterministic_payload.get("required_automatic_document_feeder"),
            normalize_optional_bool(context.get("required_automatic_document_feeder")),
        )
        merged["required_paper_sizes"] = self._merge_list_values(
            context.get("required_paper_sizes"),
            normalize_paper_sizes(merged.get("required_paper_sizes")),
        )
        merged["required_network_roles"] = self._merge_list_values(
            context.get("required_network_roles"),
            [
                role
                for role in normalize_text_list(merged.get("required_network_roles"))
                if role in {"router", "firewall", "switch", "access_point"}
            ],
        )
        merged["required_vpn_user_capacity"] = self._first_non_none(
            parse_vpn_user_capacity(merged.get("required_vpn_user_capacity")),
            deterministic_payload.get("required_vpn_user_capacity"),
            parse_vpn_user_capacity(context.get("required_vpn_user_capacity")),
        )
        merged["required_virtualization_ready"] = self._first_non_none(
            normalize_optional_bool(merged.get("required_virtualization_ready")),
            deterministic_payload.get("required_virtualization_ready"),
            normalize_optional_bool(context.get("required_virtualization_ready")),
        )
        merged["required_virtualization_platforms"] = self._merge_list_values(
            context.get("required_virtualization_platforms"),
            normalize_virtualization_platforms(merged.get("required_virtualization_platforms")),
        )
        merged["max_rack_units"] = self._first_non_none(
            parse_rack_units(merged.get("max_rack_units")),
            deterministic_payload.get("max_rack_units"),
            parse_rack_units(context.get("max_rack_units")),
        )
        merged["max_power_draw_watts"] = self._first_non_none(
            parse_power_watts(merged.get("max_power_draw_watts")),
            deterministic_payload.get("max_power_draw_watts"),
            parse_power_watts(context.get("max_power_draw_watts")),
        )
        merged["battery_life_hours_min"] = self._first_non_none(
            _parse_intake_integer(merged.get("battery_life_hours_min")),
            deterministic_payload.get("battery_life_hours_min"),
            _parse_intake_integer(context.get("battery_life_hours_min")),
        )
        merged["cpu_preference"] = self._first_non_none(
            self._normalize_nullable_text(merged.get("cpu_preference")),
            deterministic_payload.get("cpu_preference"),
            self._normalize_nullable_text(context.get("cpu_preference")),
        )
        merged["gpu_requirement"] = self._first_non_none(
            self._normalize_nullable_text(merged.get("gpu_requirement")),
            deterministic_payload.get("gpu_requirement"),
            self._normalize_nullable_text(context.get("gpu_requirement")),
        )
        merged["screen_size_preference"] = self._first_non_none(
            self._normalize_screen_size_preference(merged.get("screen_size_preference")),
            deterministic_payload.get("screen_size_preference"),
            self._normalize_screen_size_preference(context.get("screen_size_preference")),
        )
        merged["weight_kg_max"] = self._first_non_none(
            parse_weight_kg_value(merged.get("weight_kg_max")),
            deterministic_payload.get("weight_kg_max"),
            parse_weight_kg_value(context.get("weight_kg_max")),
        )
        merged["warranty_type_preference"] = self._first_non_none(
            normalize_warranty_type(merged.get("warranty_type_preference")),
            deterministic_payload.get("warranty_type_preference"),
            normalize_warranty_type(context.get("warranty_type_preference")),
        )

        if not merged.get("company_size"):
            merged["company_size"] = self._company_size_from_team_size(merged.get("team_size"))
        return merged

    def _merge_payloads(self, context, llm_payload, deterministic_payload):
        merged = dict(context or {})

        # LLM is the primary interpreter for free-form chat. Deterministic
        # extraction remains attached as a guardrail and safe backfill layer.
        for source in (llm_payload or {}, deterministic_payload or {}):
            for key, value in source.items():
                if value in (None, "", []):
                    continue
                if isinstance(value, list):
                    merged[key] = self._merge_list_values(merged.get(key), value)
                else:
                    merged[key] = value

        if not merged.get("company_size"):
            merged["company_size"] = self._company_size_from_team_size(merged.get("team_size"))
        return merged

    def _merge_list_values(self, existing, incoming):
        combined = []
        for value in list(existing or []) + list(incoming or []):
            normalized = str(value or "").strip()
            if normalized and normalized not in combined:
                combined.append(normalized)
        return combined

    def _merge_text_fragments(self, *values, separator="\n"):
        merged = []
        seen = set()
        for value in values:
            normalized = re.sub(r"\s+", " ", str(value or "")).strip()
            if not normalized:
                continue
            marker = normalized.lower()
            if marker in seen:
                continue
            seen.add(marker)
            merged.append(normalized)
        return separator.join(merged)

    def _merge_raw_chat(self, existing, latest):
        return self._merge_text_fragments(existing, latest, separator="\n")

    def _should_skip_llm_for_clarification_turn(self, chat_text, context, deterministic_payload):
        chat_text = str(chat_text or "").strip()
        if not chat_text:
            return False

        lowered = chat_text.lower()

        # Never skip LLM when the user appears to be giving a direct value reply —
        # these turns carry state-changing content and must be extracted accurately.
        if self._looks_like_direct_value_reply(lowered):
            return False

        # If deterministic extraction already found category, workload, or budget
        # signals, let LLM run to make sure nothing is missed.
        deterministic_payload = dict(deterministic_payload or {})
        category = deterministic_payload.get("preferred_category")
        workloads = list(deterministic_payload.get("workload_types") or [])
        budget = deterministic_payload.get("budget")
        if category and category != "not_sure":
            return False
        if workloads or budget is not None:
            return False

        # Also skip if any concrete spec signals were extracted.
        concrete_signal_fields = (
            "application_signals",
            "capability_tags",
            "team_size",
            "quantity",
            "requested_ram",
            "requested_storage",
            "minimum_warranty_years",
            "required_port_count",
            "required_throughput_mbps",
            "required_duplex_printing",
            "required_scanner",
            "min_print_speed_ppm",
            "required_printer_type",
            "required_network_roles",
            "required_vpn_user_capacity",
            "required_virtualization_ready",
            "required_virtualization_platforms",
            "max_rack_units",
            "max_power_draw_watts",
            "battery_life_hours_min",
            "cpu_preference",
            "gpu_requirement",
            "screen_size_preference",
            "weight_kg_max",
            "warranty_type_preference",
            "preferred_manufacturers",
            "preferred_sellers",
            "blocked_manufacturers",
            "blocked_sellers",
        )
        if any(self._value_present(deterministic_payload.get(field)) for field in concrete_signal_fields):
            return False

        # Only skip LLM for turns that are clearly generic/vague openers with no
        # extractable content — e.g. "help me choose", "not sure what I need".
        # In those cases the clarification service already knows the next question
        # to ask, so running the LLM extractor adds latency with no benefit.
        generic_markers = {
            "help me choose",
            "help me decide",
            "not sure",
            "whatever best you suggest",
            "whatever you suggest",
            "best you suggest",
            "suggest the best",
            "what exactly do i need",
            "what do i need",
            "guide me",
            "advise me",
        }
        setup_markers = {
            "opening a hospital",
            "opening a clinic",
            "opening a business",
            "opening an office",
            "opening a branch",
            "starting a hospital",
            "starting a clinic",
            "setting up a hospital",
            "setting up a clinic",
        }
        has_generic_marker = any(marker in lowered for marker in generic_markers | setup_markers)
        if not has_generic_marker and not deterministic_payload.get("industry"):
            return False

        merged_context = self._merge_payloads(context, {}, deterministic_payload)
        merged_context["raw_chat"] = self._merge_raw_chat(context.get("raw_chat", ""), chat_text)
        payload = self.build_procurement_payload(
            merged_context,
            {
                "channel": context.get("channel", ""),
            },
        )
        requirements = self.intake_service.normalize(payload)
        readiness = self.clarification_service.assess(requirements)
        missing_signals = set(readiness.get("missing_signals") or [])
        if not self.clarification_service.should_defer_ranking(readiness):
            return False
        return bool(
            {"preferred_category", "category_or_workload", "workload_or_application_profile", "budget"}.intersection(
                missing_signals
            )
        )

    def _build_field_source_hints(
        self,
        payload,
        context,
        deterministic_payload,
        deterministic_field_sources,
        llm_payload,
    ):
        hints = {}
        payload = dict(payload or {})
        context = dict(context or {})
        deterministic_payload = dict(deterministic_payload or {})
        deterministic_field_sources = dict(deterministic_field_sources or {})
        llm_payload = dict(llm_payload or {})

        for field in SCHEMA_KEYS + ["purchase_scope"]:
            value = payload.get(field)
            if not self._value_present(value):
                continue
            if self._value_present(context.get(field)):
                hints[field] = "context_explicit"
            elif self._value_present(llm_payload.get(field)):
                hints[field] = "llm_inferred"
            elif self._value_present(deterministic_payload.get(field)):
                hints[field] = deterministic_field_sources.get(field, "rule_inferred")
        return hints

    def _compute_missing_fields(self, payload):
        missing_fields = []
        preferred_category = payload.get("preferred_category")
        if preferred_category == "not_sure":
            preferred_category = None
        if not preferred_category and not payload.get("workload_types"):
            missing_fields.append("preferred_category")
        if not payload.get("workload_types"):
            missing_fields.append("workload_types")
        if payload.get("budget") is None:
            missing_fields.append("budget")
        if (
            payload.get("team_size") is None
            and payload.get("quantity") is None
            and payload.get("preferred_category") in {"laptops", "desktops"}
        ):
            missing_fields.append("team_size")
        if not payload.get("growth_expectation"):
            missing_fields.append("growth_expectation")
        if self._needs_application_profile(payload):
            missing_fields.append("application_profile")
        return missing_fields

    def _estimate_confidence(self, payload, used_llm):
        score = 0.0
        if payload.get("preferred_category") or payload.get("workload_types"):
            score += 0.25
        if payload.get("budget") is not None:
            score += 0.2
        if payload.get("team_size") or payload.get("quantity"):
            score += 0.15
        if payload.get("industry"):
            score += 0.05
        if payload.get("growth_expectation"):
            score += 0.05
        if payload.get("application_signals"):
            score += min(len(payload.get("application_signals") or []) * 0.08, 0.16)
        if payload.get("capability_tags"):
            score += min(len(payload.get("capability_tags") or []) * 0.05, 0.15)
        if (
            payload.get("requested_ram")
            or payload.get("requested_storage")
            or payload.get("minimum_warranty_years")
            or payload.get("required_port_count")
            or payload.get("required_throughput_mbps")
            or payload.get("required_duplex_printing")
            or payload.get("required_scanner")
            or payload.get("min_print_speed_ppm")
            or payload.get("required_printer_type")
            or payload.get("required_print_technology")
            or payload.get("required_color_output")
            or payload.get("min_monthly_duty_cycle_pages")
            or payload.get("required_automatic_document_feeder")
            or payload.get("required_paper_sizes")
            or payload.get("required_network_roles")
            or payload.get("required_vpn_user_capacity")
            or payload.get("required_virtualization_ready")
            or payload.get("required_virtualization_platforms")
            or payload.get("max_rack_units")
            or payload.get("max_power_draw_watts")
            or payload.get("battery_life_hours_min")
            or payload.get("cpu_preference")
            or payload.get("gpu_requirement")
            or payload.get("screen_size_preference")
            or payload.get("weight_kg_max")
            or payload.get("warranty_type_preference")
        ):
            score += 0.1
        if payload.get("performance_priority") or payload.get("portability_need") or payload.get("support_expectation"):
            score += 0.05
        if used_llm:
            score += 0.04
        return round(min(score, 1.0), 2)

    def _needs_application_profile(self, payload):
        workloads = set(payload.get("workload_types") or [])
        if not workloads:
            return False
        if payload.get("application_signals"):
            return False
        if (
            payload.get("requested_ram")
            or payload.get("requested_storage")
            or payload.get("minimum_warranty_years")
            or payload.get("required_port_count")
            or payload.get("required_throughput_mbps")
            or payload.get("required_duplex_printing")
            or payload.get("required_scanner")
            or payload.get("min_print_speed_ppm")
            or payload.get("required_printer_type")
            or payload.get("required_print_technology")
            or payload.get("required_color_output")
            or payload.get("min_monthly_duty_cycle_pages")
            or payload.get("required_automatic_document_feeder")
            or payload.get("required_paper_sizes")
            or payload.get("required_network_roles")
            or payload.get("required_vpn_user_capacity")
            or payload.get("required_virtualization_ready")
            or payload.get("required_virtualization_platforms")
            or payload.get("max_rack_units")
            or payload.get("max_power_draw_watts")
            or payload.get("battery_life_hours_min")
            or payload.get("cpu_preference")
            or payload.get("gpu_requirement")
            or payload.get("screen_size_preference")
            or payload.get("weight_kg_max")
            or payload.get("warranty_type_preference")
        ):
            return False
        capability_tags = set(payload.get("capability_tags") or [])
        if capability_tags.intersection(
            {"gpu_needed", "high_ram", "storage_heavy", "virtualization", "branch_connectivity", "local_compute"}
        ):
            return False
        return bool(workloads.intersection({"software_development", "creative_design", "ai_analytics", "server_infrastructure"}))

    def _derive_capability_tags(
        self,
        preferred_category,
        workload_types,
        application_signals,
        signal_capability_tags,
        requested_ram,
        requested_storage,
        portability_need,
        support_expectation,
        availability_need,
        existing_infrastructure,
        lowered,
    ):
        capability_tags = self.signal_service.sanitize_capability_tags(signal_capability_tags)
        workload_set = set(workload_types or [])
        infrastructure_set = {str(item or "").strip().lower() for item in (existing_infrastructure or []) if str(item or "").strip()}

        if portability_need == "high" and "portable" not in capability_tags:
            capability_tags.append("portable")
        if requested_ram and requested_ram >= 32 and "high_ram" not in capability_tags:
            capability_tags.append("high_ram")
        if requested_storage and requested_storage >= 1024 and "storage_heavy" not in capability_tags:
            capability_tags.append("storage_heavy")
        if support_expectation == "premium" and "always_on" not in capability_tags:
            capability_tags.append("always_on")
        if availability_need in {"urgent", "in_stock_now"} and "always_on" not in capability_tags:
            capability_tags.append("always_on")
        if "virtualization" in infrastructure_set or "server_infrastructure" in workload_set:
            if any(token in lowered for token in {"virtualization", "vmware", "proxmox", "hyper-v", "server"}) and "virtualization" not in capability_tags:
                capability_tags.append("virtualization")
        if preferred_category == "networking" and any(token in lowered for token in {"branch", "remote office"}) and "branch_connectivity" not in capability_tags:
            capability_tags.append("branch_connectivity")
        if any(
            signal in set(application_signals or [])
            for signal in {"developer_toolchain", "ml_toolchain"}
        ) and "local_compute" not in capability_tags:
            capability_tags.append("local_compute")

        return capability_tags

    def _normalize_nullable_text(self, value):
        text = str(value or "").strip()
        return text or None

    def _normalize_screen_size_preference(self, value):
        parsed = parse_screen_size_inches_value(value)
        if parsed is None:
            return self._normalize_nullable_text(value)
        return f"{parsed:.1f} inch"

    def _value_present(self, value):
        return value not in (None, "", [], {})

    def _first_non_none(self, *values):
        for value in values:
            if value is not None:
                return value
        return None

    def _sanitize_named_list(self, values, allowed_names):
        lowered_map = {name.lower(): name for name in allowed_names}
        sanitized = []
        for value in normalize_text_list(values):
            key = value.lower()
            if key in lowered_map and lowered_map[key] not in sanitized:
                sanitized.append(lowered_map[key])
        return sanitized

    def _sanitize_budget_value(self, value, chat_text, context, team_size=None):
        parsed = self._parse_budget_value(value)
        if parsed is None:
            return self._parse_budget_value((context or {}).get("budget"))

        explicit_budget = self._detect_budget(chat_text, context={})
        if explicit_budget is not None:
            return explicit_budget

        existing_budget = self._parse_budget_value((context or {}).get("budget"))
        if existing_budget is not None:
            return existing_budget

        if team_size and parsed == int(team_size):
            return None
        return parsed

    def _detect_spec_requirement_strength(self, lowered, spec_kind):
        lowered = str(lowered or "")
        spec_tokens = {
            "ram": {"ram", "memory"},
            "storage": {"storage", "ssd", "nvme", "disk", "hdd"},
        }.get(spec_kind, {spec_kind})

        hard_markers = get_procurement_normalization_terms("hard_requirement_words", "hard", set())
        soft_markers = get_procurement_normalization_terms("hard_requirement_words", "soft", set())
        request_markers = {
            "need",
            "needs",
            "require",
            "requires",
            "must",
            "make it",
            "make them",
            "make this",
        }

        if any(marker in lowered for marker in hard_markers) and any(token in lowered for token in spec_tokens):
            return True
        if any(marker in lowered for marker in soft_markers) and any(token in lowered for token in spec_tokens):
            return False
        if any(marker in lowered for marker in request_markers) and any(token in lowered for token in spec_tokens):
            return True
        return False

    def _detect_manufacturer_preferences(self, chat_text):
        return self._detect_preference_lists(chat_text, KNOWN_MANUFACTURERS)

    def _detect_seller_preferences(self, chat_text):
        return self._detect_preference_lists(chat_text, KNOWN_SELLERS)

    def _detect_preference_lists(self, chat_text, known_names):
        text = str(chat_text or "")
        lowered = text.lower()
        preferred = []
        blocked = []
        soft_markers = {"prefer", "preferred", "ideally", "would like", "lean toward", "like"}
        hard_block_markers = {"avoid", "exclude", "block", "not ", "don't want", "do not want", "no "}

        for name in known_names:
            pattern = rf"\b{re.escape(name.lower())}\b"
            if not re.search(pattern, lowered):
                continue

            position = lowered.find(name.lower())
            window_start = max(position - 40, 0)
            window = lowered[window_start:position]
            if any(marker in window for marker in hard_block_markers):
                if name not in blocked:
                    blocked.append(name)
                continue
            if any(marker in window for marker in soft_markers) or "only" in window or "from" in window:
                if name not in preferred:
                    preferred.append(name)

        return preferred, blocked

    def _detect_availability_need(self, lowered):
        lowered = str(lowered or "")
        if any(token in lowered for token in {"in stock now", "must be in stock", "available now", "ready stock"}):
            return "in_stock_now"
        if any(token in lowered for token in {"urgent", "immediately", "asap"}):
            return "urgent"
        if any(token in lowered for token in {"this week", "next week", "this month", "soon"}):
            return "soon"
        if any(token in lowered for token in {"standard", "normal", "not urgent", "no rush"}):
            return "standard"
        return None

    def _detect_require_returnable(self, lowered):
        lowered = str(lowered or "")
        if any(token in lowered for token in {"must be returnable", "return policy required", "returnable only", "must have return policy"}):
            return True
        if any(token in lowered for token in {"final sale is fine", "return policy not important", "non-returnable is okay"}):
            return False
        return None

    def _detect_preferred_category(self, chat_text):
        chat_text = str(chat_text or "").strip()
        lowered = chat_text.lower()
        category = normalize_category(chat_text)
        ambiguous_markers = {
            "not sure",
            "not certain",
            "haven't decided",
            "have not decided",
            "either",
        }
        mentioned_categories = [
            token
            for token in (
                "laptop",
                "desktop",
                "server",
                "network",
                "router",
                "switch",
                "printer",
                "accessories",
                "keyboard",
                "mouse",
                "headset",
                "headphone",
            )
            if token in lowered
        ]
        if any(marker in lowered for marker in ambiguous_markers) and len(set(mentioned_categories)) >= 2:
            return "not_sure"
        if "laptops or desktops" in lowered or "desktops or laptops" in lowered:
            return "not_sure"
        if not category and self._looks_like_printer_need(lowered):
            return "printers"
        if not category and self._looks_like_server_need(lowered):
            return "servers"
        if not category and self._looks_like_networking_need(lowered):
            return "networking"
        if not category and self._looks_like_end_user_device_need(lowered):
            return "laptops"
        return category

    def _looks_like_printer_need(self, lowered):
        lowered = str(lowered or "")
        printer_tokens = {
            "printer",
            "printing",
            "print",
            "ppm",
            "adf",
            "all in one",
            "all-in-one",
            "mfp",
            "duplex",
            "scanner",
            "scan",
            "copy",
            "laser",
            "inkjet",
            "ink tank",
            "pages per month",
            "duty cycle",
            "a3",
            "a4",
        }
        score = sum(1 for token in printer_tokens if token in lowered)
        return score >= 2

    def _looks_like_server_need(self, lowered):
        lowered = str(lowered or "")
        server_tokens = {
            "server",
            "virtualization",
            "vmware",
            "hyper-v",
            "proxmox",
            "hypervisor",
            "xeon",
            "epyc",
            "rack",
            "rackmount",
            "2u",
            "4u",
            "power draw",
        }
        score = sum(1 for token in server_tokens if token in lowered)
        return score >= 2

    def _looks_like_networking_need(self, lowered):
        lowered = str(lowered or "")
        networking_tokens = {
            "switch",
            "router",
            "firewall",
            "vpn",
            "throughput",
            "bandwidth",
            "port",
            "ports",
            "access point",
            "wifi",
            "wi-fi",
            "lan",
            "wan",
        }
        score = sum(1 for token in networking_tokens if token in lowered)
        return score >= 2


    def _detect_requested_ram(self, chat_text):
        text = str(chat_text or "")
        patterns = [
            r"(\d+)\s*gb\s*(?:ram|memory)",
            r"(?:ram|memory)\s*(?:of|at)?\s*(\d+)\s*gb",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def _detect_requested_storage(self, chat_text):
        text = str(chat_text or "")
        patterns = [
            r"(\d+(?:\.\d+)?)\s*(tb|gb)\s*(?:ssd|nvme|storage|disk|hdd)",
            r"(?:ssd|nvme|storage|disk|hdd)\s*(?:of|at)?\s*(\d+(?:\.\d+)?)\s*(tb|gb)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            value = float(match.group(1))
            unit = match.group(2).lower()
            storage_gb = int(value * 1024) if unit == "tb" else int(value)
            return storage_gb
        return None

    def _detect_minimum_warranty_years(self, chat_text):
        text = str(chat_text or "")
        patterns = [
            r"(\d+)\s*(?:year|yr|yrs)[-\s]*(?:warranty|support|coverage)",
            r"(?:warranty|support|coverage)\s*(?:of|for|at least|minimum|min)?\s*(\d+)\s*(?:year|yr|yrs)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def _detect_required_port_count(self, chat_text):
        text = str(chat_text or "")
        patterns = [
            r"(?:at least|minimum|min|with|need|needs|require|requires)\s*(\d+)\s*(?:ports?|lan ports?|ethernet ports?)",
            r"(\d+)\s*(?:ports?|lan ports?|ethernet ports?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def _detect_required_throughput_mbps(self, chat_text):
        text = str(chat_text or "")
        patterns = [
            r"(?:at least|minimum|min|with|need|needs|require|requires)\s*([\d.,]+)\s*(gbps|gbit|gigabit|mbps|mbit)",
            r"([\d.,]+)\s*(gbps|gbit|gigabit|mbps|mbit)\s*(?:throughput|speed|bandwidth)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return parse_throughput_mbps(f"{match.group(1)} {match.group(2)}")
        return None

    def _detect_required_duplex_printing(self, lowered):
        lowered = str(lowered or "")
        if any(token in lowered for token in {"duplex", "double-sided", "double sided"}):
            return True
        return None

    def _detect_required_scanner(self, lowered):
        lowered = str(lowered or "")
        if any(token in lowered for token in {"scanner", "scan", "scanning", "copy", "all in one", "all-in-one", "mfp"}):
            return True
        return None

    def _detect_min_print_speed_ppm(self, chat_text):
        text = str(chat_text or "")
        patterns = [
            r"(?:at least|minimum|min|with|need|needs|require|requires)\s*(\d+)\s*ppm",
            r"(\d+)\s*ppm",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def _detect_required_printer_type(self, lowered):
        lowered = str(lowered or "")
        if "label printer" in lowered:
            return "label_printer"
        if "photo printer" in lowered:
            return "photo_printer"
        if "wide format" in lowered or "plotter" in lowered:
            return "wide_format_printer"
        if any(token in lowered for token in {"all in one", "all-in-one", "mfp"}):
            return "all_in_one_printer"
        return None

    def _detect_required_print_technology(self, lowered):
        lowered = str(lowered or "")
        if "ink tank" in lowered:
            return "ink tank"
        if "inkjet" in lowered:
            return "inkjet"
        if "laser" in lowered:
            return "laser"
        return None

    def _detect_required_color_output(self, lowered):
        value = normalize_color_output(lowered)
        return value or None

    def _detect_min_monthly_duty_cycle_pages(self, chat_text):
        text = str(chat_text or "")
        patterns = [
            r"(\d+(?:\.\d+)?)\s*k?\s*(?:pages?|prints?)\s*(?:per|/)\s*month",
            r"monthly duty cycle(?:\s+of)?\s*(\d+(?:\.\d+)?)\s*k?",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            token = match.group(0)
            if "k" in token.lower():
                return int(float(match.group(1)) * 1000)
            return int(float(match.group(1)))
        return None

    def _detect_required_automatic_document_feeder(self, lowered):
        lowered = str(lowered or "")
        if any(token in lowered for token in {"automatic document feeder", "adf"}):
            return True
        return None

    def _detect_required_paper_sizes(self, chat_text):
        matches = re.findall(r"\b(a3|a4|letter|legal)\b", str(chat_text or ""), re.IGNORECASE)
        if not matches:
            return []
        return list(dict.fromkeys(match.upper() for match in matches))

    def _detect_required_network_roles(self, lowered):
        lowered = str(lowered or "")
        roles = []
        mapping = {
            "router": {"router", "routers"},
            "firewall": {"firewall", "firewalls"},
            "switch": {"switch", "switches"},
            "access_point": {"access point", "access points", "wifi", "wi-fi", "wireless ap"},
        }
        for role, tokens in mapping.items():
            if any(token in lowered for token in tokens):
                roles.append(role)
        return roles

    def _detect_required_vpn_user_capacity(self, chat_text):
        text = str(chat_text or "")
        patterns = [
            r"(\d+)\s*(?:vpn users?|remote users?)",
            r"for\s*(\d+)\s*users?\s*(?:over\s+)?vpn",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def _detect_required_virtualization_ready(self, lowered):
        lowered = str(lowered or "")
        if any(token in lowered for token in {"virtualization", "hypervisor", "vmware", "hyper-v", "proxmox", "kvm"}):
            return True
        return None

    def _detect_required_virtualization_platforms(self, chat_text):
        return normalize_virtualization_platforms([chat_text])

    def _detect_max_rack_units(self, chat_text):
        text = str(chat_text or "")
        patterns = [
            r"(?:under|below|max(?:imum)?|not more than)\s*(\d+(?:\.\d+)?)\s*u\b",
            r"(\d+(?:\.\d+)?)\s*u\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return None

    def _detect_max_power_draw_watts(self, chat_text):
        text = str(chat_text or "")
        patterns = [
            r"(?:under|below|max(?:imum)?|not more than)\s*(\d+(?:\.\d+)?)\s*(?:w|watts?)",
            r"power draw(?:\s+of)?\s*(\d+(?:\.\d+)?)\s*(?:w|watts?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(float(match.group(1)))
        return None

    def _detect_battery_life_hours_min(self, chat_text):
        text = str(chat_text or "")
        patterns = [
            r"(?:at least|minimum|min|needs?|requires?)\s*(\d+)\s*(?:hours?|hrs?)\s*(?:battery|battery life)",
            r"(?:last|lasts)\s*(?:at least|min(?:imum)?)?\s*(\d+)\s*(?:hours?|hrs?)",
            r"(\d+)\s*(?:hours?|hrs?)\s*(?:battery|battery life)",
            r"battery(?: life)?\s*(?:of|for|at least|min|minimum)?\s*(\d+)\s*(?:hours?|hrs?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return None

    def _detect_cpu_preference(self, chat_text):
        text = str(chat_text or "")
        patterns = [
            r"(intel\s+core\s+ultra\s+[3579](?:[-\s]*\d+[a-z]{0,2})?)",
            r"(intel\s+core\s+i[3579](?:[-\s]*\d+[a-z]{0,2})?)",
            r"(intel\s+core\s+[3579](?:[-\s]*\d+[a-z]{0,2})?)",
            r"(amd\s+ryzen(?:\s+ai)?\s+[3579](?:[-\s]*\d+[a-z]{0,2})?)",
            r"(apple\s+m[234](?:\s+(?:pro|max))?)",
            r"(snapdragon\s+x\s+(?:elite|plus))",
            r"(intel\s+xeon(?:\s+\w+)*)",
            r"(amd\s+epyc(?:\s+\w+)*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return " ".join(match.group(1).split())
        return None

    def _detect_gpu_requirement(self, chat_text):
        text = str(chat_text or "")
        lowered = text.lower()
        patterns = [
            r"(nvidia\s+rtx\s+\d{3,4})",
            r"(nvidia\s+rtx\s+a\d{3,4})",
            r"(nvidia\s+quadro\s+\w+)",
            r"(amd\s+radeon(?:\s+pro)?\s+\w+)",
            r"(intel\s+arc\s+\w+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return " ".join(match.group(1).split())
        if any(token in lowered for token in {"dedicated gpu", "discrete gpu", "dedicated graphics", "discrete graphics"}):
            return "dedicated_gpu"
        return None

    def _detect_screen_size_preference(self, chat_text):
        text = str(chat_text or "")
        patterns = [
            r"(\d+(?:\.\d+)?)\s*(?:-| )?(?:inch|inches|in)\b",
            r"screen(?: size)?\s*(?:of|around|about|at|near)?\s*(\d+(?:\.\d+)?)",
            r"display(?: size)?\s*(?:of|around|about|at|near)?\s*(\d+(?:\.\d+)?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            size = parse_screen_size_inches_value(match.group(1))
            if size is not None:
                return f"{size:.1f} inch"
        return None

    def _detect_weight_kg_max(self, chat_text):
        text = str(chat_text or "")
        patterns = [
            r"(?:under|below|max(?:imum)?|less than|lighter than|not more than|keep it under)\s*(\d+(?:\.\d+)?)\s*(kg|kilograms?|kilos?|lb|lbs|pounds?)",
            r"(\d+(?:\.\d+)?)\s*(kg|kilograms?|kilos?|lb|lbs|pounds?)\s*(?:max|maximum|or less|or below|or lighter)",
            r"not too bulky.*?(\d+(?:\.\d+)?)\s*(kg|kilograms?|kilos?|lb|lbs|pounds?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if not match:
                continue
            value = parse_weight_kg_value(f"{match.group(1)} {match.group(2)}")
            if value is not None:
                return value
        return None

    def _detect_warranty_type_preference(self, chat_text):
        text = str(chat_text or "").lower()
        explicit_warranty_terms = {
            "warranty",
            "onsite",
            "on-site",
            "carry-in",
            "carry in",
            "pickup",
            "pick-up",
            "return",
            "mail-in",
            "mail in",
            "accidental damage",
        }
        if not any(term in text for term in explicit_warranty_terms):
            return None
        negative_patterns = [
            r"no\s+onsite",
            r"not\s+onsite",
            r"avoid\s+onsite",
            r"no\s+carry[-\s]?in",
            r"not\s+carry[-\s]?in",
            r"avoid\s+carry[-\s]?in",
            r"no\s+pickup",
            r"not\s+pickup",
            r"avoid\s+pickup",
        ]
        if any(re.search(pattern, text) for pattern in negative_patterns):
            return None
        return normalize_warranty_type(chat_text)

    def _company_size_from_team_size(self, team_size):
        team_size = parse_team_size(team_size)
        if not team_size:
            return None
        if team_size <= 10:
            return "micro"
        if team_size <= 50:
            return "small"
        return "growing_smb"

    def _align_workloads_with_category(self, preferred_category, workload_types, lowered):
        aligned = []
        for workload in list(workload_types or []):
            if workload not in aligned:
                aligned.append(workload)

        specialized_end_user_workloads = {"software_development", "creative_design", "ai_analytics"}
        if "office_productivity" in aligned and specialized_end_user_workloads.intersection(aligned):
            aligned = [workload for workload in aligned if workload != "office_productivity"]

        if preferred_category == "networking":
            aligned = [workload for workload in aligned if workload != "office_productivity"]
            if "network_connectivity" not in aligned:
                aligned.insert(0, "network_connectivity")
        elif preferred_category == "servers":
            aligned = [workload for workload in aligned if workload != "office_productivity"]
            if any(token in lowered for token in {"server", "virtualization", "hosting", "on-prem", "infrastructure"}):
                if "server_infrastructure" not in aligned:
                    aligned.insert(0, "server_infrastructure")
        elif preferred_category == "printers":
            aligned = [workload for workload in aligned if workload != "office_productivity"]
            if "document_output" not in aligned:
                aligned.insert(0, "document_output")
        elif preferred_category == "accessories":
            aligned = [workload for workload in aligned if workload != "office_productivity"]
            if "peripheral_accessories" not in aligned:
                aligned.insert(0, "peripheral_accessories")

        return aligned

    def _detect_industry(self, lowered):
        mapping = {
            "retail": {"retail", "pos", "store"},
            "professional services": {"professional services", "consulting", "agency"},
            "software": {"software", "developer", "engineering", "technology", "it services"},
            "education": {"education", "school", "campus"},
            "healthcare": {"healthcare", "clinic", "hospital", "medical"},
            "manufacturing": {"manufacturing", "factory", "warehouse"},
            "finance": {"finance", "financial services", "accounting", "bookkeeping"},
        }
        for industry, tokens in mapping.items():
            if any(token in lowered for token in tokens):
                return industry
        return None

    def _detect_business_type(self, lowered, context=None):
        lowered = str(lowered or "")
        context = dict(context or {})
        if any(
            token in lowered
            for token in {
                "startup",
                "start-up",
                "founding team",
                "founders",
                "new company",
                "early stage",
            }
        ):
            return "startup"
        existing = self._normalize_nullable_text(context.get("business_type"))
        if existing:
            return existing
        return None

    def _detect_performance_priority(self, lowered):
        if any(token in lowered for token in {"fastest", "performance", "powerful", "best specs", "high performance"}):
            return "performance"
        if any(token in lowered for token in {"cheap", "lowest cost", "budget sensitive", "cost focused"}):
            return "cost"
        if any(token in lowered for token in {"balanced", "middle ground", "well rounded"}):
            return "balanced"
        return None

    def _detect_portability_need(self, lowered):
        if any(token in lowered for token in {"travel", "portable", "lightweight", "on the go", "field team"}):
            return "high"
        if any(token in lowered for token in {"desk-based", "fixed desk", "office only"}):
            return "low"
        if any(token in lowered for token in {"hybrid", "mixed"}):
            return "medium"
        return None

    def _detect_support_expectation(self, lowered):
        if any(token in lowered for token in {"24x7", "mission critical", "premium support", "white glove"}):
            return "premium"
        if any(token in lowered for token in {"business support", "onsite", "next business day"}):
            return "business"
        if any(token in lowered for token in {"basic support", "standard support"}):
            return "basic"
        return None

    def _normalize_performance_priority_value(self, value, lowered):
        priority = str(value or "").strip().lower()
        if priority not in {"balanced", "cost", "performance"}:
            return None
        if priority == "cost" and not any(
            token in str(lowered or "")
            for token in {"cheap", "lowest cost", "budget sensitive", "cost focused"}
        ):
            return None
        if priority == "performance" and not any(
            token in str(lowered or "")
            for token in {"fastest", "performance", "powerful", "best specs", "fast", "high performance"}
        ):
            return None
        return priority

    def _detect_rollout_type(self, lowered):
        lowered = str(lowered or "")
        if any(token in lowered for token in {"phased rollout", "phase 1", "phase one", "staggered rollout", "roll out in phases"}):
            return "phased"
        if any(token in lowered for token in {"single phase rollout", "full rollout", "all at once"}):
            return "standard"
        return None

    def _detect_replacement_mode(self, lowered):
        lowered = str(lowered or "")
        if any(
            token in lowered
            for token in {
                "refresh",
                "device refresh",
                "replace",
                "replacement",
                "upgrade our old",
                "upgrade existing",
            }
        ):
            return "refresh"
        if any(
            token in lowered
            for token in {
                "net new",
                "new office",
                "new team",
                "new branch",
                "new site",
                "new hires",
                "founding team",
            }
        ):
            return "net_new"
        return None

    def _detect_timeline(self, chat_text):
        lowered = str(chat_text or "").lower()
        for token in (
            "urgent",
            "immediately",
            "this week",
            "this month",
            "next month",
            "next quarter",
            "quarter",
        ):
            if token in lowered:
                return token
        return None

    def _detect_existing_infrastructure(self, chat_text):
        tokens = []
        lowered = str(chat_text or "").lower()
        candidates = {
            "windows": {"windows", "active directory"},
            "mac": {"mac", "macos"},
            "linux": {"linux", "ubuntu"},
            "virtualization": {"vmware", "virtualization", "hyper-v", "proxmox"},
            "networking": {"switch", "router", "firewall", "wifi", "wi-fi"},
            "cloud": {"aws", "azure", "gcp", "cloud"},
        }
        for label, matchers in candidates.items():
            if any(re.search(rf"\b{re.escape(matcher)}\b", lowered) for matcher in matchers):
                tokens.append(label)
        if tokens:
            return tokens
        if ":" in chat_text:
            return normalize_text_list(chat_text.split(":", 1)[1])
        return []

    def _detect_quantity(self, chat_text, team_size, preferred_category=None, workload_types=None):
        lowered = str(chat_text or "").lower()
        infrastructure_context = self._is_infrastructure_context(preferred_category, workload_types)
        if self._has_explicit_single_unit_signal(lowered):
            return 1, "user_explicit"

        match = re.search(
            r"(\d+)\s+(?:\w+\s+){0,2}(units|devices|laptops|desktops|servers|switches|routers|printers|keyboards|mice|headsets|headphones)",
            lowered,
        )
        if match:
            return int(match.group(1)), "user_explicit"

        if infrastructure_context:
            return None, None
        if not team_size:
            return None, None
        if any(token in lowered for token in {"each", "per user", "per seat"}):
            return team_size, "rule_inferred"
        if self._has_rollout_quantity_signal(lowered, preferred_category):
            return team_size, "rule_inferred"
        return None, None

    def _has_explicit_single_unit_signal(self, lowered):
        lowered = str(lowered or "")
        pattern = (
            r"\b(?:one|single|1)\s+"
            r"(?:\w+\s+){0,2}"
            r"(?:unit|device|laptop|desktop|server|switch|router|firewall|printer|keyboard|mouse|headset|headphones|notebook|pc|workstation)\b"
        )
        return bool(re.search(pattern, lowered))

    def _has_rollout_quantity_signal(self, lowered, preferred_category=None):
        lowered = str(lowered or "")
        if any(
            token in lowered
            for token in {
                "rollout",
                "refresh",
                "for the team",
                "for all staff",
                "for all employees",
                "for all users",
                "all developers",
                "all designers",
                "everyone",
            }
        ):
            return True

        category = str(preferred_category or "").strip().lower()
        if category == "laptops" and "laptops" in lowered:
            return True
        if category == "desktops" and "desktops" in lowered:
            return True
        if category == "accessories" and any(
            token in lowered
            for token in {"keyboard", "keyboards", "mouse", "mice", "headset", "headsets", "headphones"}
        ):
            return True
        return False

    def _is_infrastructure_context(self, preferred_category, workload_types):
        if preferred_category in {"networking", "servers"}:
            return True
        workload_set = set(workload_types or [])
        return bool(workload_set.intersection({"network_connectivity", "server_infrastructure"}))

    def _detect_budget_from_chat(self, chat_text):
        lowered = str(chat_text or "").lower()
        range_budget = self._detect_budget_range_from_chat(lowered)
        if range_budget is not None:
            return range_budget

        # Remove nearby non-money spec phrases so weight or screen-size numbers
        # do not hijack budget extraction in sales-style shorthand.
        budget_text = re.sub(
            r"(?:under|below|max(?:imum)?|less than|lighter than|not more than)?\s*\d+(?:\.\d+)?\s*(?:kg|kilograms?|kilos?|lb|lbs|pounds?)\b",
            " ",
            lowered,
        )
        budget_text = re.sub(
            r"\d+(?:\.\d+)?(?:\s*|-)?(?:inch|inches|in)\b",
            " ",
            budget_text,
        )
        budget_text = re.sub(
            r"(?:under|below|max(?:imum)?|less than|not more than)?\s*\d+(?:\.\d+)?\s*(?:w|watts?)\b",
            " ",
            budget_text,
        )
        budget_text = re.sub(
            r"\d+(?:\.\d+)?\s*u\b",
            " ",
            budget_text,
        )

        money_token = r"(\d[\d,]*(?:\.\d+)?(?:\s?(?:k|lakh|thousand|thousands))?)"
        currency_token = r"(?:inr|rs\.?|rupees?|myr|usd|eur|gbp|rm|\$)"
        patterns = [
            rf"(?:under|below|budget(?:\s+(?:is|of|around|at|for))?|around|roughly|approx(?:imately)?|up to|within|total(?:\s+budget)?(?:\s+(?:is|of))?|overall(?:\s+budget)?(?:\s+(?:is|of))?|max(?:imum)?(?:\s+budget)?(?:\s+of)?|capped at|keep it at|can stretch to|stretch to|stretch up to)\s+{currency_token}?\s*{money_token}",
            rf"{currency_token}\s*{money_token}",
            rf"{money_token}\s*{currency_token}",
            rf"{money_token}\s*(?:each|per unit|per seat|per device)",
            rf"budget\s*(?:is|of|around|at|for)?\s*{currency_token}?\s*{money_token}",
            rf"budget\s*(?:can\s+)?stretch\s*(?:to|up to)\s*{currency_token}?\s*{money_token}",
            rf"{money_token}\s+budget",
        ]
        for pattern in patterns:
            match = re.search(pattern, budget_text)
            if not match:
                continue
            trailing_text = budget_text[match.end():match.end() + 24]
            if any(
                token in trailing_text
                for token in {
                    "people",
                    "users",
                    "employees",
                    "staff",
                    "developers",
                    "designers",
                    "engineer",
                    "engineers",
                    "seats",
                    "endpoints",
                }
            ):
                continue
            return self._parse_budget_value(match.group(1))
        return None

    def _detect_budget(self, chat_text, context=None):
        budget = self._detect_budget_from_chat(chat_text)
        if budget is not None:
            return budget
        if context and context.get("budget") is not None:
            return self._parse_budget_value(context.get("budget"))
        return None

    def _detect_team_size_from_chat(self, chat_text):
        original_lowered = str(chat_text or "").lower()
        lowered = self._strip_non_headcount_numeric_expressions(self._strip_budget_expressions(chat_text))
        patterns = [
            r"(?:for|around|about)\s+(\d+)\s+(?:\w+\s+){0,2}(?:users|people|employees|staff|developers|designers|agents|seats|endpoints)",
            r"for\s+around\s+(\d+)\s+(?:\w+\s+){0,2}(?:users|people|employees|staff|developers|designers|agents|seats|endpoints)",
            r"(\d+)\s+(?:\w+\s+){0,2}(?:users|people|employees|staff|developers|designers|agents|seats|endpoints)",
            r"(?:will be|grow to|scale to|expand to)\s+(\d+)(?:\s+(?:users|people|employees|staff|developers|designers|agents|seats|endpoints))?",
            r"(\d+)\s+(?:in the future|in future|future users|future endpoints)",
        ]
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                return int(match.group(1))
        for pattern in patterns:
            match = re.search(pattern, original_lowered)
            if match:
                return int(match.group(1))

        stripped = lowered.strip()
        if re.fullmatch(r"\d+", stripped):
            return int(stripped)

        headcount_cues = get_procurement_normalization_terms("quantity_units", default=set())
        if any(token in lowered for token in headcount_cues):
            parsed = parse_team_size(lowered)
            if parsed and parsed <= 500:
                return parsed
        return None

    def _strip_non_headcount_numeric_expressions(self, text):
        lowered = str(text or "").lower()
        battery_units = "|".join(
            re.escape(unit)
            for unit in sorted(get_procurement_normalization_terms("spec_units", "battery_hours", set()), key=len, reverse=True)
        )
        weight_units = "|".join(
            re.escape(unit)
            for unit in sorted(get_procurement_normalization_terms("spec_units", "weight", set()), key=len, reverse=True)
        )
        screen_units = "|".join(
            re.escape(unit)
            for unit in sorted(get_procurement_normalization_terms("spec_units", "screen", set()), key=len, reverse=True)
        )
        rack_units = "|".join(
            re.escape(unit)
            for unit in sorted(get_procurement_normalization_terms("spec_units", "rack_units", set()), key=len, reverse=True)
        )
        power_units = "|".join(
            re.escape(unit)
            for unit in sorted(get_procurement_normalization_terms("spec_units", "power", set()), key=len, reverse=True)
        )
        patterns = [
            rf"\d+\s*(?:{battery_units})\s*(?:battery|battery life)?",
            rf"\d+(?:\.\d+)?\s*(?:{weight_units})",
            rf"\d+(?:\.\d+)?(?:\s*|-)?(?:{screen_units})\b",
            rf"\d+(?:\.\d+)?\s*(?:{rack_units})\b",
            rf"\d+(?:\.\d+)?\s*(?:{power_units})\b",
            r"\d+\s*gb\s*(?:ram|memory)",
            r"\d+(?:\.\d+)?\s*(?:tb|gb)\s*(?:ssd|nvme|storage|disk|hdd)",
            r"(?:rtx|gtx)\s*\d{3,4}",
            r"a\d{3,4}",
            r"(?:i[3579]|ultra\s+[3579]|ryzen(?:\s+ai)?\s+[3579])[-\s]*\d+[a-z]{0,2}",
        ]
        scrubbed = lowered
        for pattern in patterns:
            scrubbed = re.sub(pattern, " ", scrubbed)
        return re.sub(r"\s+", " ", scrubbed).strip()

    def _detect_team_size(self, chat_text, context=None):
        team_size = self._detect_team_size_from_chat(chat_text)
        if team_size is not None:
            return team_size

        if context and context.get("team_size"):
            return parse_team_size(context.get("team_size"))
        return None

    def _parse_budget_value(self, value):
        if value is None or value == "":
            return None
        return parse_money_value(value)

    def _normalize_money_token(self, token):
        token = str(token or "").strip().lower().replace(",", "")
        if not token:
            return None
        return parse_money_value(token)

    def _detect_budget_range_from_chat(self, lowered):
        lowered = str(lowered or "").lower()
        range_patterns = [
            r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*(k|lakh|thousand|thousands)\b",
            r"(\d+(?:\.\d+)?)\s*(k|lakh|thousand|thousands)\s*-\s*(\d+(?:\.\d+)?)\s*(k|lakh|thousand|thousands)?\b",
            r"(?:around|approx(?:imately)?|maybe|roughly)?\s*(\d+(?:\.\d+)?)\s*(?:to|or)\s*(\d+(?:\.\d+)?)\s*(k|lakh|thousand|thousands)\b",
        ]
        for pattern in range_patterns:
            match = re.search(pattern, lowered)
            if not match:
                continue
            groups = match.groups("")
            if len(groups) == 3:
                low_token = f"{groups[0]}{groups[2]}"
                high_token = f"{groups[1]}{groups[2]}"
            else:
                low_unit = groups[1]
                high_unit = groups[3] or low_unit
                low_token = f"{groups[0]}{low_unit}"
                high_token = f"{groups[2]}{high_unit}"
            low_value = self._normalize_money_token(low_token)
            high_value = self._normalize_money_token(high_token)
            if low_value is not None and high_value is not None:
                return max(low_value, high_value)
        return None

    def _strip_budget_expressions(self, text):
        lowered = str(text or "").lower()
        patterns = [
            r"\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?\s*(?:k|lakh|thousand|thousands)\b",
            r"\d+(?:\.\d+)?\s*(?:k|lakh|thousand|thousands)\s*-\s*\d+(?:\.\d+)?\s*(?:k|lakh|thousand|thousands)?\b",
            r"(?:under|below|around|approx(?:imately)?|up to|within|budget(?:\s+(?:is|of|around|at|for))?|total budget(?:\s+of)?|overall budget(?:\s+of)?)\s+(?:inr|rs\.?|rupees?|myr|usd|eur|gbp|rm|\$|â‚¹)?\s*\d[\d,]*(?:\.\d+)?(?:\s?(?:k|lakh|thousand|thousands))?",
            r"(?:inr|rs\.?|rupees?|myr|usd|eur|gbp|rm|\$|â‚¹)\s*\d[\d,]*(?:\.\d+)?(?:\s?(?:k|lakh|thousand|thousands))?",
            r"\d[\d,]*(?:\.\d+)?(?:\s?(?:k|lakh|thousand|thousands))?\s*(?:inr|rs\.?|rupees?|myr|usd|eur|gbp|rm|\$|â‚¹)",
        ]
        scrubbed = lowered
        for pattern in patterns:
            scrubbed = re.sub(pattern, " ", scrubbed)
        return re.sub(r"\s+", " ", scrubbed).strip()

    def _looks_like_end_user_device_need(self, lowered):
        lowered = str(lowered or "").lower()
        if self._is_generic_office_prompt(lowered):
            return False
        if any(token in lowered for token in {"router", "switch", "firewall", "access point", "server", "printer"}):
            return False
        end_user_cues = {
            "light",
            "lightweight",
            "carry",
            "portable",
            "battery",
            "travel",
            "roadshow",
            "field reps",
            "field sales",
            "client-facing",
            "client facing",
            "sales people",
            "join calls",
            "new joiners",
            "coders",
            "creative team",
            "design team",
            "for developers",
            "for designers",
            "for sales",
            "sales reps",
            "sales team",
            "systems for",
            "office pcs",
            "office pc",
        }
        return any(token in lowered for token in end_user_cues)

    def _normalize_llm_category(self, category, chat_text, workload_types, application_signals):
        category = normalize_category(category)
        if not category:
            return None
        lowered = str(chat_text or "").lower()
        if self._is_generic_office_prompt(lowered) and category in {"laptops", "desktops"}:
            return None
        direct_category = normalize_category(chat_text)
        if direct_category == category:
            return category
        if category == "laptops" and self._looks_like_end_user_device_need(lowered):
            return category
        if category == "desktops" and any(
            token in lowered for token in {"desktop", "desktops", "pc", "pcs", "office pc", "office pcs", "workstation"}
        ):
            return category
        if category == "networking" and any(
            token in lowered for token in {"network", "networking", "firewall", "switch", "router", "branch", "vpn", "wifi", "wi-fi"}
        ):
            return category
        if category == "printers" and any(
            token in lowered for token in {"printer", "printing", "scan", "scanner", "copier", "mfp"}
        ):
            return category
        if category == "accessories" and any(
            token in lowered for token in {"headset", "headsets", "keyboard", "mouse", "dock", "accessories", "monitor"}
        ):
            return category
        if category == "servers" and any(
            token in lowered for token in {"server", "servers", "virtualization", "vmware", "hyper-v", "proxmox"}
        ):
            return category
        workload_set = set(workload_types or [])
        signal_set = {str(signal or "").strip().lower() for signal in (application_signals or [])}
        if category == "laptops" and (
            workload_set.intersection({"software_development", "creative_design", "office_productivity"})
            or signal_set.intersection({"developer_toolchain", "design_suite", "business_apps", "mobile_workforce"})
        ) and not self._is_vague_prompt(lowered):
            return category
        return None

    def _normalize_llm_workloads(self, workloads, chat_text, category, application_signals):
        workloads = normalize_workloads(workloads)
        if not workloads:
            return []
        lowered = str(chat_text or "").lower()
        if self._is_generic_office_prompt(lowered):
            return []
        explicit_workloads = set(normalize_workloads(chat_text))
        explicit_signals = self.signal_service.extract(chat_text)
        if explicit_workloads:
            return list(dict.fromkeys(list(explicit_workloads) + list(workloads)))
        if explicit_signals.get("workload_types"):
            return list(dict.fromkeys(list(explicit_signals.get("workload_types") or []) + list(workloads)))
        signal_set = {str(signal or "").strip().lower() for signal in (application_signals or [])}
        if category == "networking" or signal_set.intersection({"branch_networking"}):
            return workloads
        if category == "laptops" and not self._is_vague_prompt(lowered):
            return workloads
        if self._is_vague_prompt(lowered):
            return []
        return workloads

    def _normalize_printer_type_value(self, value):
        text = str(value or "").strip().lower().replace("-", " ").replace("_", " ")
        if not text:
            return None
        mapping = {
            "all in one": "all_in_one_printer",
            "all in one printer": "all_in_one_printer",
            "mfp": "all_in_one_printer",
            "enterprise mfp": "enterprise_mfp",
            "label printer": "label_printer",
            "photo printer": "photo_printer",
            "wide format": "wide_format_printer",
            "wide format printer": "wide_format_printer",
            "plotter": "wide_format_printer",
            "ink tank printer": "ink_tank_printer",
            "inkjet printer": "inkjet_printer",
            "mono laser printer": "mono_laser_printer",
            "color laser printer": "color_laser_printer",
        }
        return mapping.get(text, text.replace(" ", "_"))

    def _is_vague_prompt(self, lowered):
        lowered = str(lowered or "").lower()
        if self._is_generic_office_prompt(lowered):
            return True
        vague_markers = {
            "same setup as before",
            "same as before",
            "something workable",
            "something decent",
            "new team",
            "cheaper this time",
            "workable",
        }
        strong_need_markers = {
            "developer",
            "developers",
            "design",
            "designer",
            "designers",
            "sales",
            "finance",
            "network",
            "firewall",
            "switch",
            "router",
            "printer",
            "headset",
            "laptop",
            "desktop",
            "server",
            "branch office",
            "branch",
            "travel",
            "battery",
        }
        if any(marker in lowered for marker in strong_need_markers):
            return False
        return any(marker in lowered for marker in vague_markers)

    def _is_generic_office_prompt(self, lowered):
        lowered = str(lowered or "").lower()
        generic_office_markers = {
            "new office",
            "office setup",
            "office requirement",
            "office needs",
            "for the office",
            "office budget",
            "workable for the office",
        }
        if not any(marker in lowered for marker in generic_office_markers):
            return False
        strong_need_markers = {
            "developer",
            "design",
            "sales",
            "finance",
            "printer",
            "network",
            "switch",
            "router",
            "firewall",
            "server",
            "headset",
            "laptop",
            "desktop",
            "battery",
            "travel",
            "gpu",
            "core ultra",
            "ryzen",
            "xeon",
        }
        return not any(marker in lowered for marker in strong_need_markers)

    def _detect_growth_expectation(self, lowered):
        if any(token in lowered for token in {"stable", "steady", "no growth"}):
            return "steady"
        if any(token in lowered for token in {"rapid", "scale", "scaling", "expansion", "aggressive"}):
            return "rapid_growth"
        if any(
            token in lowered
            for token in {
                "moderate",
                "grow",
                "growth",
                "hiring",
                "new branch",
                "more staff",
                "in the future",
                "in future",
                "future users",
                "future endpoints",
                "next year",
                "next quarter",
                "next month",
                "over the next",
            }
        ):
            return "moderate_growth"
        return None

    def _format_storage(self, storage_gb):
        if not storage_gb:
            return None
        if storage_gb >= 1024 and storage_gb % 1024 == 0:
            return f"{storage_gb // 1024}TB"
        return f"{storage_gb}GB"


RequirementExtractionService = ProcurementSchemaExtractor

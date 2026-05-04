# import re

# from ...catalog.services.normalization import (
#     normalize_budget_scope,
#     normalize_categories,
#     normalize_category,
#     normalize_color_output,
#     normalize_growth_expectation,
#     normalize_paper_sizes,
#     normalize_printer_type,
#     normalize_warranty_type,
#     normalize_text_list,
#     normalize_virtualization_platforms,
#     normalize_workloads,
#     parse_money_value,
#     parse_page_volume,
#     parse_port_count,
#     parse_ram_gb,
#     parse_print_speed_ppm,
#     parse_screen_size_inches_value,
#     parse_storage_gb,
#     parse_team_size,
#     parse_throughput_mbps,
#     parse_vpn_user_capacity,
#     parse_rack_units,
#     parse_power_watts,
#     parse_weight_kg_value,
# )
# from .input_normalization import (
#     normalize_availability_need,
#     normalize_optional_bool,
#     normalize_purchase_scope,
#     normalize_replacement_mode,
#     normalize_rollout_type,
# )
# from .signal_service import ProcurementSignalService


# TRACKED_INTAKE_FIELDS = [
#     "preferred_category",
#     "industry",
#     "business_type",
#     "team_size",
#     "workloads",
#     "application_signals",
#     "budget",
#     "budget_scope",
#     "quantity",
#     "purchase_scope",
#     "rollout_type",
#     "replacement_mode",
#     "growth_expectation",
#     "performance_priority",
#     "portability_need",
#     "support_expectation",
#     "availability_need",
#     "existing_infrastructure",
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


# def _parse_intake_float(value):
#     if value is None or value == "":
#         return None
#     if isinstance(value, (int, float)):
#         return float(value)
#     match = re.search(r"(\d+(?:\.\d+)?)", str(value))
#     return float(match.group(1)) if match else None

# ASSUMPTION_SEVERITY_BY_FIELD = {
#     "preferred_category": "compatibility_critical",
#     "workloads": "compatibility_critical",
#     "application_signals": "capacity_critical",
#     "budget_scope": "cost_critical",
#     "quantity": "capacity_critical",
#     "purchase_scope": "capacity_critical",
#     "rollout_type": "capacity_critical",
#     "replacement_mode": "capacity_critical",
#     "growth_expectation": "soft",
#     "performance_priority": "soft",
#     "portability_need": "soft",
#     "support_expectation": "soft",
#     "availability_need": "soft",
#     "minimum_warranty_years": "compatibility_critical",
#     "required_port_count": "compatibility_critical",
#     "required_throughput_mbps": "compatibility_critical",
#     "required_duplex_printing": "compatibility_critical",
#     "required_scanner": "compatibility_critical",
#     "min_print_speed_ppm": "compatibility_critical",
#     "required_printer_type": "compatibility_critical",
#     "required_print_technology": "compatibility_critical",
#     "required_color_output": "compatibility_critical",
#     "min_monthly_duty_cycle_pages": "compatibility_critical",
#     "required_automatic_document_feeder": "compatibility_critical",
#     "required_paper_sizes": "compatibility_critical",
#     "required_network_roles": "compatibility_critical",
#     "required_vpn_user_capacity": "compatibility_critical",
#     "required_virtualization_ready": "compatibility_critical",
#     "required_virtualization_platforms": "compatibility_critical",
#     "max_rack_units": "compatibility_critical",
#     "max_power_draw_watts": "compatibility_critical",
#     "battery_life_hours_min": "compatibility_critical",
#     "cpu_preference": "compatibility_critical",
#     "gpu_requirement": "compatibility_critical",
#     "screen_size_preference": "compatibility_critical",
#     "weight_kg_max": "compatibility_critical",
#     "warranty_type_preference": "compatibility_critical",
# }


# class RequirementIntakeService:
#     def __init__(self, signal_service=None):
#         self.signal_service = signal_service or ProcurementSignalService()

#     def normalize(self, payload):
#         payload = dict(payload or {})
#         explicit_payload_fields = set(payload.get("_explicit_payload_fields") or [])
#         if not explicit_payload_fields:
#             explicit_payload_fields = {
#                 key
#                 for key, value in payload.items()
#                 if not str(key).startswith("_")
#                 and key not in {"edited_inferred_values", "review_acceptance", "persist", "extracted_schema"}
#                 and self._value_present(value)
#             }
#             payload["_explicit_payload_fields"] = sorted(explicit_payload_fields)

#         review_state = self._build_review_state(payload)
#         edited_inferred_values = dict(review_state.get("edited_inferred_values") or {})
#         if edited_inferred_values:
#             payload = self._apply_review_edits(payload, edited_inferred_values)

#         preferred_categories = normalize_categories(payload.get("preferred_categories"))
#         direct_category = normalize_category(payload.get("category") or payload.get("preferred_category"))
#         if direct_category and direct_category not in preferred_categories:
#             preferred_categories.insert(0, direct_category)

#         workloads = normalize_workloads(payload.get("workload_types") or payload.get("workloads"))
#         if not workloads:
#             workloads = normalize_workloads(payload.get("use_case"))
#         application_signals = self.signal_service.sanitize_application_signals(payload.get("application_signals"))
#         if not workloads and application_signals:
#             workloads = self.signal_service.workloads_for_application_signals(application_signals)
#         industry = str(payload.get("industry") or "").strip()

#         business_type = str(payload.get("business_type") or "").strip()
#         notes = str(payload.get("notes") or "").strip()
#         growth_input = str(payload.get("growth_expectation") or "").strip()
#         availability_need = normalize_availability_need(payload.get("availability_need"))
#         rollout_type = normalize_rollout_type(payload.get("rollout_type"))
#         replacement_mode = normalize_replacement_mode(payload.get("replacement_mode"))
#         capability_tags = self.signal_service.sanitize_capability_tags(payload.get("capability_tags"))
#         capability_tags = list(
#             dict.fromkeys(
#                 capability_tags + self.signal_service.capability_tags_for_application_signals(application_signals)
#             )
#         )
#         team_size = parse_team_size(payload.get("team_size"))
#         quantity = parse_team_size(payload.get("quantity"))
#         hint_text = " ".join(
#             part
#             for part in (
#                 payload.get("chat_text"),
#                 payload.get("raw_chat"),
#                 payload.get("notes"),
#             )
#             if str(part or "").strip()
#         )
#         budget_scope = normalize_budget_scope(
#             payload.get("budget_scope"),
#             preferred_categories=preferred_categories,
#             hint_text=hint_text,
#             quantity=quantity,
#         )
#         purchase_scope = normalize_purchase_scope(
#             payload.get("purchase_scope"),
#             preferred_categories=preferred_categories,
#             quantity=quantity,
#             team_size=team_size,
#             hint_text=hint_text,
#         )
#         requested_ram_gb = parse_ram_gb(
#             payload.get("requested_ram") or payload.get("specifications.ram_size")
#         )
#         requested_storage_gb = parse_storage_gb(
#             payload.get("requested_storage") or payload.get("specifications.storage_size")
#         )
#         minimum_warranty_years = _parse_warranty_years_value(payload.get("minimum_warranty_years"))
#         required_port_count = parse_port_count(payload.get("required_port_count"))
#         required_throughput_mbps = parse_throughput_mbps(payload.get("required_throughput_mbps"))
#         required_duplex_printing = normalize_optional_bool(payload.get("required_duplex_printing"))
#         required_scanner = normalize_optional_bool(payload.get("required_scanner"))
#         min_print_speed_ppm = parse_print_speed_ppm(payload.get("min_print_speed_ppm"))
#         printer_type_value = payload.get("required_printer_type")
#         required_printer_type = normalize_printer_type(
#             {"printer_type": printer_type_value} if printer_type_value else {},
#             {},
#         ) or None
#         required_print_technology = str(payload.get("required_print_technology") or "").strip().lower() or None
#         required_color_output = normalize_color_output(payload.get("required_color_output")) or None
#         min_monthly_duty_cycle_pages = parse_page_volume(payload.get("min_monthly_duty_cycle_pages"))
#         required_automatic_document_feeder = normalize_optional_bool(payload.get("required_automatic_document_feeder"))
#         required_paper_sizes = normalize_paper_sizes(payload.get("required_paper_sizes"))
#         required_network_roles = normalize_text_list(payload.get("required_network_roles"))
#         required_vpn_user_capacity = parse_vpn_user_capacity(payload.get("required_vpn_user_capacity"))
#         required_virtualization_ready = normalize_optional_bool(payload.get("required_virtualization_ready"))
#         required_virtualization_platforms = normalize_virtualization_platforms(
#             payload.get("required_virtualization_platforms")
#         )
#         max_rack_units = parse_rack_units(payload.get("max_rack_units"))
#         max_power_draw_watts = parse_power_watts(payload.get("max_power_draw_watts"))
#         battery_life_hours_min = _parse_intake_integer(payload.get("battery_life_hours_min"))
#         cpu_preference = str(payload.get("cpu_preference") or "").strip() or None
#         gpu_requirement = str(payload.get("gpu_requirement") or "").strip() or None
#         raw_screen_size_preference = str(payload.get("screen_size_preference") or "").strip()
#         screen_size_inches = parse_screen_size_inches_value(raw_screen_size_preference)
#         screen_size_preference = (
#             f"{screen_size_inches:.1f} inch"
#             if screen_size_inches is not None
#             else (raw_screen_size_preference or None)
#         )
#         weight_kg_max = parse_weight_kg_value(payload.get("weight_kg_max"))
#         warranty_type_preference = normalize_warranty_type(payload.get("warranty_type_preference"))

#         requirements = {
#             "store_id": str(payload.get("store_id") or "").strip(),
#             "channel": str(payload.get("channel") or "api").strip() or "api",
#             "currency": str(payload.get("currency") or "INR").strip() or "INR",
#             "raw_chat": str(payload.get("chat_text") or payload.get("raw_chat") or "").strip(),
#             "preferred_categories": preferred_categories,
#             "preferred_category": preferred_categories[0] if preferred_categories else None,
#             "industry": industry,
#             "business_type": business_type,
#             "team_size": team_size,
#             "workloads": workloads,
#             "application_signals": application_signals,
#             "capability_tags": capability_tags,
#             "budget": parse_money_value(payload.get("budget")),
#             "budget_scope": budget_scope,
#             "growth_expectation": normalize_growth_expectation(growth_input) if growth_input else None,
#             "existing_infrastructure": normalize_text_list(payload.get("existing_infrastructure")),
#             "preferred_manufacturers": normalize_text_list(payload.get("preferred_manufacturers")),
#             "blocked_manufacturers": normalize_text_list(payload.get("blocked_manufacturers")),
#             "preferred_sellers": normalize_text_list(payload.get("preferred_sellers")),
#             "blocked_sellers": normalize_text_list(payload.get("blocked_sellers")),
#             "performance_priority": str(payload.get("performance_priority") or "").strip() or None,
#             "portability_need": str(payload.get("portability_need") or "").strip() or None,
#             "support_expectation": str(payload.get("support_expectation") or "").strip() or None,
#             "availability_need": availability_need,
#             "require_returnable": normalize_optional_bool(payload.get("require_returnable")),
#             "ranking_persona": self._derive_ranking_persona(payload),
#             "quantity": quantity,
#             "purchase_scope": purchase_scope,
#             "rollout_type": rollout_type,
#             "replacement_mode": replacement_mode,
#             "timeline": str(payload.get("timeline") or "").strip(),
#             "requested_ram_gb": requested_ram_gb,
#             "requested_storage_gb": requested_storage_gb,
#             "requested_ram_is_minimum": self._normalize_requirement_strength(
#                 payload.get("requested_ram_is_minimum"),
#                 default=bool(requested_ram_gb),
#             ),
#             "requested_storage_is_minimum": self._normalize_requirement_strength(
#                 payload.get("requested_storage_is_minimum"),
#                 default=bool(requested_storage_gb),
#             ),
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
#             "notes": notes,
#         }
#         field_source = self._build_field_source_map(payload, requirements)
#         field_state = {
#             field: self._field_state(requirements.get(field), field_source.get(field))
#             for field in TRACKED_INTAKE_FIELDS
#         }
#         assumption_severity = self._build_assumption_severity(field_state)
#         requirements["field_state"] = field_state
#         requirements["field_source"] = field_source
#         requirements["assumption_severity"] = assumption_severity
#         requirements["review_state"] = review_state
#         return requirements

#     def _derive_ranking_persona(self, payload):
#         lowered = " ".join(
#             str(value or "")
#             for value in (
#                 payload.get("chat_text"),
#                 payload.get("raw_chat"),
#                 payload.get("notes"),
#             )
#         ).lower()
#         availability_need = normalize_availability_need(payload.get("availability_need"))

#         if any(token in lowered for token in {"standardize", "standardise", "same brand", "approved vendor", "preferred vendor"}):
#             return "standardization-first"
#         if availability_need in {"urgent", "in_stock_now"} or any(token in lowered for token in {"urgent", "asap", "immediately", "available now", "ready stock", "in stock"}):
#             return "availability-first"
#         if normalize_text_list(payload.get("preferred_manufacturers")) or normalize_text_list(payload.get("preferred_sellers")):
#             return "standardization-first"
#         if "always_on" in normalize_text_list(payload.get("capability_tags")):
#             return "support-first"
#         if str(payload.get("performance_priority") or "").strip().lower() == "cost":
#             return "finance-first"
#         if str(payload.get("performance_priority") or "").strip().lower() == "performance":
#             return "performance-first"
#         if str(payload.get("support_expectation") or "").strip().lower() in {"business", "premium"}:
#             return "support-first"
#         return "balanced"

#     def _normalize_requirement_strength(self, value, default=False):
#         normalized = normalize_optional_bool(value)
#         if normalized is None:
#             return default
#         return normalized

#     def _build_field_source_map(self, payload, requirements):
#         sources = {}
#         payload = dict(payload or {})
#         source_hints = dict(payload.get("_field_source_hints") or {})
#         explicit_payload_fields = set(payload.get("_explicit_payload_fields") or [])

#         def was_explicit(*keys):
#             if explicit_payload_fields:
#                 return any(key in explicit_payload_fields for key in keys)
#             return any(self._value_present(payload.get(key)) for key in keys)

#         explicit_fields = {
#             "preferred_category": was_explicit("category", "preferred_category", "preferred_categories"),
#             "industry": was_explicit("industry"),
#             "business_type": was_explicit("business_type"),
#             "team_size": was_explicit("team_size"),
#             "workloads": was_explicit("workload_types", "workloads", "use_case"),
#             "application_signals": was_explicit("application_signals"),
#             "budget": was_explicit("budget"),
#             "budget_scope": was_explicit("budget_scope"),
#             "quantity": was_explicit("quantity"),
#             "purchase_scope": was_explicit("purchase_scope"),
#             "rollout_type": was_explicit("rollout_type"),
#             "replacement_mode": was_explicit("replacement_mode"),
#             "growth_expectation": was_explicit("growth_expectation"),
#             "performance_priority": was_explicit("performance_priority"),
#             "portability_need": was_explicit("portability_need"),
#             "support_expectation": was_explicit("support_expectation"),
#             "availability_need": was_explicit("availability_need"),
#             "existing_infrastructure": was_explicit("existing_infrastructure"),
#             "minimum_warranty_years": was_explicit("minimum_warranty_years"),
#             "required_port_count": was_explicit("required_port_count"),
#             "required_throughput_mbps": was_explicit("required_throughput_mbps"),
#             "required_duplex_printing": was_explicit("required_duplex_printing"),
#             "required_scanner": was_explicit("required_scanner"),
#             "min_print_speed_ppm": was_explicit("min_print_speed_ppm"),
#             "required_printer_type": was_explicit("required_printer_type"),
#             "required_print_technology": was_explicit("required_print_technology"),
#             "required_color_output": was_explicit("required_color_output"),
#             "min_monthly_duty_cycle_pages": was_explicit("min_monthly_duty_cycle_pages"),
#             "required_automatic_document_feeder": was_explicit("required_automatic_document_feeder"),
#             "required_paper_sizes": was_explicit("required_paper_sizes"),
#             "required_network_roles": was_explicit("required_network_roles"),
#             "required_vpn_user_capacity": was_explicit("required_vpn_user_capacity"),
#             "required_virtualization_ready": was_explicit("required_virtualization_ready"),
#             "required_virtualization_platforms": was_explicit("required_virtualization_platforms"),
#             "max_rack_units": was_explicit("max_rack_units"),
#             "max_power_draw_watts": was_explicit("max_power_draw_watts"),
#             "battery_life_hours_min": was_explicit("battery_life_hours_min"),
#             "cpu_preference": was_explicit("cpu_preference"),
#             "gpu_requirement": was_explicit("gpu_requirement"),
#             "screen_size_preference": was_explicit("screen_size_preference"),
#             "weight_kg_max": was_explicit("weight_kg_max"),
#             "warranty_type_preference": was_explicit("warranty_type_preference"),
#         }
#         for field, is_explicit in explicit_fields.items():
#             if is_explicit and self._value_present(requirements.get(field)):
#                 sources[field] = "user_explicit"

#         hint_key_map = {
#             "preferred_category": "preferred_category",
#             "industry": "industry",
#             "business_type": "business_type",
#             "team_size": "team_size",
#             "workload_types": "workloads",
#             "application_signals": "application_signals",
#             "budget": "budget",
#             "budget_scope": "budget_scope",
#             "growth_expectation": "growth_expectation",
#             "performance_priority": "performance_priority",
#             "portability_need": "portability_need",
#             "support_expectation": "support_expectation",
#             "availability_need": "availability_need",
#             "quantity": "quantity",
#             "purchase_scope": "purchase_scope",
#             "rollout_type": "rollout_type",
#             "replacement_mode": "replacement_mode",
#             "existing_infrastructure": "existing_infrastructure",
#             "minimum_warranty_years": "minimum_warranty_years",
#             "required_port_count": "required_port_count",
#             "required_throughput_mbps": "required_throughput_mbps",
#             "required_duplex_printing": "required_duplex_printing",
#             "required_scanner": "required_scanner",
#             "min_print_speed_ppm": "min_print_speed_ppm",
#             "required_printer_type": "required_printer_type",
#             "required_print_technology": "required_print_technology",
#             "required_color_output": "required_color_output",
#             "min_monthly_duty_cycle_pages": "min_monthly_duty_cycle_pages",
#             "required_automatic_document_feeder": "required_automatic_document_feeder",
#             "required_paper_sizes": "required_paper_sizes",
#             "required_network_roles": "required_network_roles",
#             "required_vpn_user_capacity": "required_vpn_user_capacity",
#             "required_virtualization_ready": "required_virtualization_ready",
#             "required_virtualization_platforms": "required_virtualization_platforms",
#             "max_rack_units": "max_rack_units",
#             "max_power_draw_watts": "max_power_draw_watts",
#             "battery_life_hours_min": "battery_life_hours_min",
#             "cpu_preference": "cpu_preference",
#             "gpu_requirement": "gpu_requirement",
#             "screen_size_preference": "screen_size_preference",
#             "weight_kg_max": "weight_kg_max",
#             "warranty_type_preference": "warranty_type_preference",
#         }
#         for hint_key, source in source_hints.items():
#             target_key = hint_key_map.get(hint_key)
#             if not target_key or target_key in sources:
#                 continue
#             if self._value_present(requirements.get(target_key)):
#                 sources[target_key] = source

#         if requirements.get("budget_scope") and "budget_scope" not in sources:
#             sources["budget_scope"] = "rule_inferred"
#         if requirements.get("purchase_scope") and "purchase_scope" not in sources:
#             sources["purchase_scope"] = "rule_inferred"
#         if requirements.get("rollout_type") and "rollout_type" not in sources:
#             sources["rollout_type"] = "rule_inferred"
#         if requirements.get("replacement_mode") and "replacement_mode" not in sources:
#             sources["replacement_mode"] = "rule_inferred"
#         if requirements.get("workloads") and "workloads" not in sources:
#             sources["workloads"] = "rule_inferred"
#         return sources

#     def _field_state(self, value, source):
#         if not self._value_present(value):
#             return "unknown"
#         if source in {"user_explicit", "context_explicit"}:
#             return "confirmed"
#         return "inferred"

#     def _build_assumption_severity(self, field_state):
#         severities = {}
#         for field, state in dict(field_state or {}).items():
#             if state == "confirmed":
#                 continue
#             severity = ASSUMPTION_SEVERITY_BY_FIELD.get(field)
#             if severity:
#                 severities[field] = severity
#         return severities

#     def _value_present(self, value):
#         return value not in (None, "", [], {})

#     def _build_review_state(self, payload):
#         payload = dict(payload or {})
#         review_acceptance = normalize_optional_bool(payload.get("review_acceptance"))
#         edited_inferred_values = self._normalize_review_edits(payload)
#         edited_fields = sorted(edited_inferred_values)
#         submitted = review_acceptance is not None or bool(edited_fields)
#         audit = []
#         if edited_fields:
#             audit.append(
#                 {
#                     "action": "submit_edits",
#                     "edited_fields": list(edited_fields),
#                 }
#             )
#         if review_acceptance is True:
#             audit.append({"action": "request_acceptance"})
#         elif review_acceptance is False:
#             audit.append({"action": "continue_editing"})
#         return {
#             "workflow_version": "review-v2",
#             "submitted": submitted,
#             "review_acceptance_requested": review_acceptance is True,
#             "continue_editing": review_acceptance is False,
#             "accepted": False,
#             "edited_inferred_values": edited_inferred_values,
#             "edited_fields": edited_fields,
#             "status": (
#                 "acceptance_requested"
#                 if review_acceptance is True
#                 else "edits_submitted"
#                 if edited_fields
#                 else "review_pending"
#             ),
#             "audit": audit,
#         }

#     def _normalize_review_edits(self, payload):
#         payload = dict(payload or {})
#         raw_edits = payload.get("edited_inferred_values") or {}
#         if not isinstance(raw_edits, dict):
#             return {}

#         normalized = {}
#         categories = normalize_categories(raw_edits.get("preferred_categories"))
#         direct_category = normalize_category(raw_edits.get("preferred_category") or raw_edits.get("category"))
#         if direct_category and direct_category not in categories:
#             categories.insert(0, direct_category)
#         if "preferred_category" in raw_edits or "category" in raw_edits or "preferred_categories" in raw_edits:
#             normalized["preferred_category"] = categories[0] if categories else None

#         if "industry" in raw_edits:
#             normalized["industry"] = str(raw_edits.get("industry") or "").strip() or None
#         if "business_type" in raw_edits:
#             normalized["business_type"] = str(raw_edits.get("business_type") or "").strip() or None
#         if "team_size" in raw_edits:
#             normalized["team_size"] = parse_team_size(raw_edits.get("team_size"))
#         if "workloads" in raw_edits or "workload_types" in raw_edits:
#             normalized["workloads"] = normalize_workloads(
#                 raw_edits.get("workloads") or raw_edits.get("workload_types")
#             )
#         if "application_signals" in raw_edits:
#             normalized["application_signals"] = self.signal_service.sanitize_application_signals(
#                 raw_edits.get("application_signals")
#             )
#         if "budget" in raw_edits:
#             normalized["budget"] = parse_money_value(raw_edits.get("budget"))
#         if "quantity" in raw_edits:
#             normalized["quantity"] = parse_team_size(raw_edits.get("quantity"))

#         category_hints = categories or normalize_categories(payload.get("preferred_categories"))
#         payload_category = normalize_category(payload.get("category") or payload.get("preferred_category"))
#         if payload_category and payload_category not in category_hints:
#             category_hints.insert(0, payload_category)
#         quantity_hint = normalized.get("quantity")
#         if quantity_hint is None:
#             quantity_hint = parse_team_size(raw_edits.get("quantity")) if "quantity" in raw_edits else parse_team_size(payload.get("quantity"))
#         team_size_hint = normalized.get("team_size")
#         if team_size_hint is None:
#             team_size_hint = parse_team_size(raw_edits.get("team_size")) if "team_size" in raw_edits else parse_team_size(payload.get("team_size"))
#         hint_text = " ".join(
#             part
#             for part in (
#                 payload.get("chat_text"),
#                 payload.get("raw_chat"),
#                 payload.get("notes"),
#             )
#             if str(part or "").strip()
#         )

#         if "budget_scope" in raw_edits:
#             normalized["budget_scope"] = normalize_budget_scope(
#                 raw_edits.get("budget_scope"),
#                 preferred_categories=category_hints,
#                 hint_text=hint_text,
#                 quantity=quantity_hint,
#             )
#         if "purchase_scope" in raw_edits:
#             normalized["purchase_scope"] = normalize_purchase_scope(
#                 raw_edits.get("purchase_scope"),
#                 preferred_categories=category_hints,
#                 quantity=quantity_hint,
#                 team_size=team_size_hint,
#                 hint_text=hint_text,
#             )
#         if "rollout_type" in raw_edits:
#             normalized["rollout_type"] = normalize_rollout_type(raw_edits.get("rollout_type"))
#         if "replacement_mode" in raw_edits:
#             normalized["replacement_mode"] = normalize_replacement_mode(raw_edits.get("replacement_mode"))
#         if "growth_expectation" in raw_edits:
#             growth_value = str(raw_edits.get("growth_expectation") or "").strip()
#             normalized["growth_expectation"] = normalize_growth_expectation(growth_value) if growth_value else None
#         if "performance_priority" in raw_edits:
#             normalized["performance_priority"] = str(raw_edits.get("performance_priority") or "").strip() or None
#         if "portability_need" in raw_edits:
#             normalized["portability_need"] = str(raw_edits.get("portability_need") or "").strip() or None
#         if "support_expectation" in raw_edits:
#             normalized["support_expectation"] = str(raw_edits.get("support_expectation") or "").strip() or None
#         if "availability_need" in raw_edits:
#             normalized["availability_need"] = normalize_availability_need(raw_edits.get("availability_need"))
#         if "existing_infrastructure" in raw_edits:
#             normalized["existing_infrastructure"] = normalize_text_list(raw_edits.get("existing_infrastructure"))
#         if "minimum_warranty_years" in raw_edits:
#             normalized["minimum_warranty_years"] = _parse_warranty_years_value(raw_edits.get("minimum_warranty_years"))
#         if "required_port_count" in raw_edits:
#             normalized["required_port_count"] = parse_port_count(raw_edits.get("required_port_count"))
#         if "required_throughput_mbps" in raw_edits:
#             normalized["required_throughput_mbps"] = parse_throughput_mbps(raw_edits.get("required_throughput_mbps"))
#         if "required_duplex_printing" in raw_edits:
#             normalized["required_duplex_printing"] = normalize_optional_bool(raw_edits.get("required_duplex_printing"))
#         if "required_scanner" in raw_edits:
#             normalized["required_scanner"] = normalize_optional_bool(raw_edits.get("required_scanner"))
#         if "min_print_speed_ppm" in raw_edits:
#             normalized["min_print_speed_ppm"] = parse_print_speed_ppm(raw_edits.get("min_print_speed_ppm"))
#         if "required_printer_type" in raw_edits:
#             normalized["required_printer_type"] = str(raw_edits.get("required_printer_type") or "").strip().lower() or None
#         if "required_print_technology" in raw_edits:
#             normalized["required_print_technology"] = str(raw_edits.get("required_print_technology") or "").strip().lower() or None
#         if "required_color_output" in raw_edits:
#             normalized["required_color_output"] = normalize_color_output(raw_edits.get("required_color_output")) or None
#         if "min_monthly_duty_cycle_pages" in raw_edits:
#             normalized["min_monthly_duty_cycle_pages"] = parse_page_volume(raw_edits.get("min_monthly_duty_cycle_pages"))
#         if "required_automatic_document_feeder" in raw_edits:
#             normalized["required_automatic_document_feeder"] = normalize_optional_bool(raw_edits.get("required_automatic_document_feeder"))
#         if "required_paper_sizes" in raw_edits:
#             normalized["required_paper_sizes"] = normalize_paper_sizes(raw_edits.get("required_paper_sizes"))
#         if "required_network_roles" in raw_edits:
#             normalized["required_network_roles"] = normalize_text_list(raw_edits.get("required_network_roles"))
#         if "required_vpn_user_capacity" in raw_edits:
#             normalized["required_vpn_user_capacity"] = parse_vpn_user_capacity(raw_edits.get("required_vpn_user_capacity"))
#         if "required_virtualization_ready" in raw_edits:
#             normalized["required_virtualization_ready"] = normalize_optional_bool(raw_edits.get("required_virtualization_ready"))
#         if "required_virtualization_platforms" in raw_edits:
#             normalized["required_virtualization_platforms"] = normalize_virtualization_platforms(raw_edits.get("required_virtualization_platforms"))
#         if "max_rack_units" in raw_edits:
#             normalized["max_rack_units"] = parse_rack_units(raw_edits.get("max_rack_units"))
#         if "max_power_draw_watts" in raw_edits:
#             normalized["max_power_draw_watts"] = parse_power_watts(raw_edits.get("max_power_draw_watts"))
#         if "battery_life_hours_min" in raw_edits:
#             normalized["battery_life_hours_min"] = _parse_intake_integer(raw_edits.get("battery_life_hours_min"))
#         if "cpu_preference" in raw_edits:
#             normalized["cpu_preference"] = str(raw_edits.get("cpu_preference") or "").strip() or None
#         if "gpu_requirement" in raw_edits:
#             normalized["gpu_requirement"] = str(raw_edits.get("gpu_requirement") or "").strip() or None
#         if "screen_size_preference" in raw_edits:
#             raw_screen = raw_edits.get("screen_size_preference")
#             screen_inches = parse_screen_size_inches_value(raw_screen)
#             normalized["screen_size_preference"] = (
#                 f"{screen_inches:.1f} inch" if screen_inches is not None else str(raw_screen or "").strip() or None
#             )
#         if "weight_kg_max" in raw_edits:
#             normalized["weight_kg_max"] = parse_weight_kg_value(raw_edits.get("weight_kg_max"))
#         if "warranty_type_preference" in raw_edits:
#             normalized["warranty_type_preference"] = normalize_warranty_type(raw_edits.get("warranty_type_preference"))
#         return normalized

#     def _apply_review_edits(self, payload, edited_inferred_values):
#         payload = dict(payload or {})
#         edited_inferred_values = dict(edited_inferred_values or {})
#         source_hints = dict(payload.get("_field_source_hints") or {})

#         field_mapping = {
#             "preferred_category": ("category", "preferred_category"),
#             "industry": ("industry", "industry"),
#             "business_type": ("business_type", "business_type"),
#             "team_size": ("team_size", "team_size"),
#             "workloads": ("workload_types", "workload_types"),
#             "application_signals": ("application_signals", "application_signals"),
#             "budget": ("budget", "budget"),
#             "budget_scope": ("budget_scope", "budget_scope"),
#             "quantity": ("quantity", "quantity"),
#             "purchase_scope": ("purchase_scope", "purchase_scope"),
#             "rollout_type": ("rollout_type", "rollout_type"),
#             "replacement_mode": ("replacement_mode", "replacement_mode"),
#             "growth_expectation": ("growth_expectation", "growth_expectation"),
#             "performance_priority": ("performance_priority", "performance_priority"),
#             "portability_need": ("portability_need", "portability_need"),
#             "support_expectation": ("support_expectation", "support_expectation"),
#             "availability_need": ("availability_need", "availability_need"),
#             "existing_infrastructure": ("existing_infrastructure", "existing_infrastructure"),
#             "minimum_warranty_years": ("minimum_warranty_years", "minimum_warranty_years"),
#             "required_port_count": ("required_port_count", "required_port_count"),
#             "required_throughput_mbps": ("required_throughput_mbps", "required_throughput_mbps"),
#             "required_duplex_printing": ("required_duplex_printing", "required_duplex_printing"),
#             "required_scanner": ("required_scanner", "required_scanner"),
#             "min_print_speed_ppm": ("min_print_speed_ppm", "min_print_speed_ppm"),
#             "required_printer_type": ("required_printer_type", "required_printer_type"),
#             "required_print_technology": ("required_print_technology", "required_print_technology"),
#             "required_color_output": ("required_color_output", "required_color_output"),
#             "min_monthly_duty_cycle_pages": ("min_monthly_duty_cycle_pages", "min_monthly_duty_cycle_pages"),
#             "required_automatic_document_feeder": ("required_automatic_document_feeder", "required_automatic_document_feeder"),
#             "required_paper_sizes": ("required_paper_sizes", "required_paper_sizes"),
#             "required_network_roles": ("required_network_roles", "required_network_roles"),
#             "required_vpn_user_capacity": ("required_vpn_user_capacity", "required_vpn_user_capacity"),
#             "required_virtualization_ready": ("required_virtualization_ready", "required_virtualization_ready"),
#             "required_virtualization_platforms": ("required_virtualization_platforms", "required_virtualization_platforms"),
#             "max_rack_units": ("max_rack_units", "max_rack_units"),
#             "max_power_draw_watts": ("max_power_draw_watts", "max_power_draw_watts"),
#             "battery_life_hours_min": ("battery_life_hours_min", "battery_life_hours_min"),
#             "cpu_preference": ("cpu_preference", "cpu_preference"),
#             "gpu_requirement": ("gpu_requirement", "gpu_requirement"),
#             "screen_size_preference": ("screen_size_preference", "screen_size_preference"),
#             "weight_kg_max": ("weight_kg_max", "weight_kg_max"),
#             "warranty_type_preference": ("warranty_type_preference", "warranty_type_preference"),
#         }

#         for review_field, value in edited_inferred_values.items():
#             target = field_mapping.get(review_field)
#             if not target:
#                 continue
#             payload_key, source_hint_key = target
#             payload[payload_key] = value
#             source_hints[source_hint_key] = "context_explicit"

#         payload["_field_source_hints"] = source_hints
#         return payload

#     def normalize_state_requirements(self, requirements: dict) -> dict:
#         return self.normalize(requirements or {})










import re

from ...catalog.services.normalization import (
    normalize_budget_scope,
    normalize_categories,
    normalize_category,
    normalize_color_output,
    normalize_growth_expectation,
    normalize_paper_sizes,
    normalize_printer_type,
    normalize_warranty_type,
    normalize_text_list,
    normalize_virtualization_platforms,
    normalize_workloads,
    parse_money_value,
    parse_page_volume,
    parse_port_count,
    parse_ram_gb,
    parse_print_speed_ppm,
    parse_screen_size_inches_value,
    parse_storage_gb,
    parse_team_size,
    parse_throughput_mbps,
    parse_vpn_user_capacity,
    parse_rack_units,
    parse_power_watts,
    parse_weight_kg_value,
)
from .input_normalization import (
    normalize_availability_need,
    normalize_optional_bool,
    normalize_purchase_scope,
    normalize_replacement_mode,
    normalize_rollout_type,
)
from .signal_service import ProcurementSignalService


TRACKED_INTAKE_FIELDS = [
    "preferred_category",
    "industry",
    "business_type",
    "team_size",
    "workloads",
    "application_signals",
    "budget",
    "budget_scope",
    "quantity",
    "purchase_scope",
    "rollout_type",
    "replacement_mode",
    "growth_expectation",
    "performance_priority",
    "portability_need",
    "support_expectation",
    "availability_need",
    "existing_infrastructure",
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


def _parse_intake_float(value):
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"(\d+(?:\.\d+)?)", str(value))
    return float(match.group(1)) if match else None

ASSUMPTION_SEVERITY_BY_FIELD = {
    "preferred_category": "compatibility_critical",
    "workloads": "compatibility_critical",
    "application_signals": "capacity_critical",
    "budget_scope": "cost_critical",
    "quantity": "capacity_critical",
    "purchase_scope": "capacity_critical",
    "rollout_type": "capacity_critical",
    "replacement_mode": "capacity_critical",
    "growth_expectation": "soft",
    "performance_priority": "soft",
    "portability_need": "soft",
    "support_expectation": "soft",
    "availability_need": "soft",
    "minimum_warranty_years": "compatibility_critical",
    "required_port_count": "compatibility_critical",
    "required_throughput_mbps": "compatibility_critical",
    "required_duplex_printing": "compatibility_critical",
    "required_scanner": "compatibility_critical",
    "min_print_speed_ppm": "compatibility_critical",
    "required_printer_type": "compatibility_critical",
    "required_print_technology": "compatibility_critical",
    "required_color_output": "compatibility_critical",
    "min_monthly_duty_cycle_pages": "compatibility_critical",
    "required_automatic_document_feeder": "compatibility_critical",
    "required_paper_sizes": "compatibility_critical",
    "required_network_roles": "compatibility_critical",
    "required_vpn_user_capacity": "compatibility_critical",
    "required_virtualization_ready": "compatibility_critical",
    "required_virtualization_platforms": "compatibility_critical",
    "max_rack_units": "compatibility_critical",
    "max_power_draw_watts": "compatibility_critical",
    "battery_life_hours_min": "compatibility_critical",
    "cpu_preference": "compatibility_critical",
    "gpu_requirement": "compatibility_critical",
    "screen_size_preference": "compatibility_critical",
    "weight_kg_max": "compatibility_critical",
    "warranty_type_preference": "compatibility_critical",
}


class RequirementIntakeService:
    def __init__(self, signal_service=None):
        self.signal_service = signal_service or ProcurementSignalService()

    def normalize(self, payload):
        payload = dict(payload or {})
        explicit_payload_fields = set(payload.get("_explicit_payload_fields") or [])
        if not explicit_payload_fields:
            explicit_payload_fields = {
                key
                for key, value in payload.items()
                if not str(key).startswith("_")
                and key not in {"edited_inferred_values", "review_acceptance", "persist", "extracted_schema"}
                and self._value_present(value)
            }
            payload["_explicit_payload_fields"] = sorted(explicit_payload_fields)

        review_state = self._build_review_state(payload)
        edited_inferred_values = dict(review_state.get("edited_inferred_values") or {})
        if edited_inferred_values:
            payload = self._apply_review_edits(payload, edited_inferred_values)

        preferred_categories = normalize_categories(payload.get("preferred_categories"))
        direct_category = normalize_category(payload.get("category") or payload.get("preferred_category"))
        resolved_explicit_categories = [
            category
            for category in preferred_categories
            if category and category != "not_sure"
        ]
        if direct_category == "not_sure" and len(resolved_explicit_categories) >= 2:
            direct_category = None
        if direct_category and direct_category not in preferred_categories:
            preferred_categories.insert(0, direct_category)
        if len(resolved_explicit_categories) >= 2:
            preferred_categories = resolved_explicit_categories

        workloads = normalize_workloads(payload.get("workload_types") or payload.get("workloads"))
        if not workloads:
            workloads = normalize_workloads(payload.get("use_case"))
        application_signals = self.signal_service.sanitize_application_signals(payload.get("application_signals"))
        if not workloads and application_signals:
            workloads = self.signal_service.workloads_for_application_signals(application_signals)
        industry = str(payload.get("industry") or "").strip()

        business_type = str(payload.get("business_type") or "").strip()
        notes = str(payload.get("notes") or "").strip()
        growth_input = str(payload.get("growth_expectation") or "").strip()
        availability_need = normalize_availability_need(payload.get("availability_need"))
        rollout_type = normalize_rollout_type(payload.get("rollout_type"))
        replacement_mode = normalize_replacement_mode(payload.get("replacement_mode"))
        capability_tags = self.signal_service.sanitize_capability_tags(payload.get("capability_tags"))
        capability_tags = list(
            dict.fromkeys(
                capability_tags + self.signal_service.capability_tags_for_application_signals(application_signals)
            )
        )
        team_size = parse_team_size(payload.get("team_size"))
        quantity = parse_team_size(payload.get("quantity"))
        hint_text = " ".join(
            part
            for part in (
                payload.get("chat_text"),
                payload.get("raw_chat"),
                payload.get("notes"),
            )
            if str(part or "").strip()
        )
        budget_scope = normalize_budget_scope(
            payload.get("budget_scope"),
            preferred_categories=preferred_categories,
            hint_text=hint_text,
            quantity=quantity,
        )
        purchase_scope = normalize_purchase_scope(
            payload.get("purchase_scope"),
            preferred_categories=preferred_categories,
            quantity=quantity,
            team_size=team_size,
            hint_text=hint_text,
        )
        requested_ram_gb = parse_ram_gb(
            payload.get("requested_ram_gb") or payload.get("requested_ram") or payload.get("specifications.ram_size")
        )
        requested_storage_gb = parse_storage_gb(
            payload.get("requested_storage_gb") or payload.get("requested_storage") or payload.get("specifications.storage_size")
        )
        minimum_warranty_years = _parse_warranty_years_value(payload.get("minimum_warranty_years"))
        required_port_count = parse_port_count(payload.get("required_port_count"))
        required_throughput_mbps = parse_throughput_mbps(payload.get("required_throughput_mbps"))
        required_duplex_printing = normalize_optional_bool(payload.get("required_duplex_printing"))
        required_scanner = normalize_optional_bool(payload.get("required_scanner"))
        min_print_speed_ppm = parse_print_speed_ppm(payload.get("min_print_speed_ppm"))
        printer_type_value = payload.get("required_printer_type")
        required_printer_type = normalize_printer_type(
            {"printer_type": printer_type_value} if printer_type_value else {},
            {},
        ) or None
        required_print_technology = str(payload.get("required_print_technology") or "").strip().lower() or None
        required_color_output = normalize_color_output(payload.get("required_color_output")) or None
        min_monthly_duty_cycle_pages = parse_page_volume(payload.get("min_monthly_duty_cycle_pages"))
        required_automatic_document_feeder = normalize_optional_bool(payload.get("required_automatic_document_feeder"))
        required_paper_sizes = normalize_paper_sizes(payload.get("required_paper_sizes"))
        required_network_roles = normalize_text_list(payload.get("required_network_roles"))
        required_vpn_user_capacity = parse_vpn_user_capacity(payload.get("required_vpn_user_capacity"))
        required_virtualization_ready = normalize_optional_bool(payload.get("required_virtualization_ready"))
        required_virtualization_platforms = normalize_virtualization_platforms(
            payload.get("required_virtualization_platforms")
        )
        max_rack_units = parse_rack_units(payload.get("max_rack_units"))
        max_power_draw_watts = parse_power_watts(payload.get("max_power_draw_watts"))
        battery_life_hours_min = _parse_intake_integer(payload.get("battery_life_hours_min"))
        cpu_preference = str(payload.get("cpu_preference") or "").strip() or None
        gpu_requirement = str(payload.get("gpu_requirement") or "").strip() or None
        raw_screen_size_preference = str(payload.get("screen_size_preference") or "").strip()
        screen_size_inches = parse_screen_size_inches_value(raw_screen_size_preference)
        screen_size_preference = (
            f"{screen_size_inches:.1f} inch"
            if screen_size_inches is not None
            else (raw_screen_size_preference or None)
        )
        weight_kg_max = parse_weight_kg_value(payload.get("weight_kg_max"))
        warranty_type_preference = normalize_warranty_type(payload.get("warranty_type_preference"))

        requirements = {
            "store_id": str(payload.get("store_id") or "").strip(),
            "channel": str(payload.get("channel") or "api").strip() or "api",
            "currency": str(payload.get("currency") or "INR").strip() or "INR",
            "raw_chat": str(payload.get("chat_text") or payload.get("raw_chat") or "").strip(),
            "preferred_categories": preferred_categories,
            "preferred_category": (
                next((category for category in preferred_categories if category and category != "not_sure"), None)
                if preferred_categories
                else None
            ),
            "industry": industry,
            "business_type": business_type,
            "team_size": team_size,
            "workloads": workloads,
            "application_signals": application_signals,
            "capability_tags": capability_tags,
            "budget": parse_money_value(payload.get("budget")),
            "budget_scope": budget_scope,
            "growth_expectation": normalize_growth_expectation(growth_input) if growth_input else None,
            "existing_infrastructure": normalize_text_list(payload.get("existing_infrastructure")),
            "preferred_manufacturers": normalize_text_list(payload.get("preferred_manufacturers")),
            "blocked_manufacturers": normalize_text_list(payload.get("blocked_manufacturers")),
            "preferred_sellers": normalize_text_list(payload.get("preferred_sellers")),
            "blocked_sellers": normalize_text_list(payload.get("blocked_sellers")),
            "performance_priority": str(payload.get("performance_priority") or "").strip() or None,
            "portability_need": str(payload.get("portability_need") or "").strip() or None,
            "support_expectation": str(payload.get("support_expectation") or "").strip() or None,
            "availability_need": availability_need,
            "require_returnable": normalize_optional_bool(payload.get("require_returnable")),
            "ranking_persona": self._derive_ranking_persona(payload),
            "quantity": quantity,
            "purchase_scope": purchase_scope,
            "rollout_type": rollout_type,
            "replacement_mode": replacement_mode,
            "timeline": str(payload.get("timeline") or "").strip(),
            "requested_ram_gb": requested_ram_gb,
            "requested_storage_gb": requested_storage_gb,
            "requested_ram_is_minimum": self._normalize_requirement_strength(
                payload.get("requested_ram_is_minimum"),
                default=bool(requested_ram_gb),
            ),
            "requested_storage_is_minimum": self._normalize_requirement_strength(
                payload.get("requested_storage_is_minimum"),
                default=bool(requested_storage_gb),
            ),
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
            "notes": notes,
        }
        field_source = self._build_field_source_map(payload, requirements)
        field_state = {
            field: self._field_state(requirements.get(field), field_source.get(field))
            for field in TRACKED_INTAKE_FIELDS
        }
        assumption_severity = self._build_assumption_severity(field_state)
        requirements["field_state"] = field_state
        requirements["field_source"] = field_source
        requirements["assumption_severity"] = assumption_severity
        requirements["review_state"] = review_state
        return requirements

    def _derive_ranking_persona(self, payload):
        lowered = " ".join(
            str(value or "")
            for value in (
                payload.get("chat_text"),
                payload.get("raw_chat"),
                payload.get("notes"),
            )
        ).lower()
        availability_need = normalize_availability_need(payload.get("availability_need"))

        if any(token in lowered for token in {"standardize", "standardise", "same brand", "approved vendor", "preferred vendor"}):
            return "standardization-first"
        if availability_need in {"urgent", "in_stock_now"} or any(token in lowered for token in {"urgent", "asap", "immediately", "available now", "ready stock", "in stock"}):
            return "availability-first"
        if normalize_text_list(payload.get("preferred_manufacturers")) or normalize_text_list(payload.get("preferred_sellers")):
            return "standardization-first"
        if "always_on" in normalize_text_list(payload.get("capability_tags")):
            return "support-first"
        if str(payload.get("performance_priority") or "").strip().lower() == "cost":
            return "finance-first"
        if str(payload.get("performance_priority") or "").strip().lower() == "performance":
            return "performance-first"
        if str(payload.get("support_expectation") or "").strip().lower() in {"business", "premium"}:
            return "support-first"
        return "balanced"

    def _normalize_requirement_strength(self, value, default=False):
        normalized = normalize_optional_bool(value)
        if normalized is None:
            return default
        return normalized

    def _build_field_source_map(self, payload, requirements):
        sources = {}
        payload = dict(payload or {})
        source_hints = dict(payload.get("_field_source_hints") or {})
        explicit_payload_fields = set(payload.get("_explicit_payload_fields") or [])

        def was_explicit(*keys):
            if explicit_payload_fields:
                return any(key in explicit_payload_fields for key in keys)
            return any(self._value_present(payload.get(key)) for key in keys)

        explicit_fields = {
            "preferred_category": was_explicit("category", "preferred_category", "preferred_categories"),
            "industry": was_explicit("industry"),
            "business_type": was_explicit("business_type"),
            "team_size": was_explicit("team_size"),
            "workloads": was_explicit("workload_types", "workloads", "use_case"),
            "application_signals": was_explicit("application_signals"),
            "budget": was_explicit("budget"),
            "budget_scope": was_explicit("budget_scope"),
            "preferred_manufacturers": was_explicit("preferred_manufacturers"),
            "blocked_manufacturers": was_explicit("blocked_manufacturers"),
            "preferred_sellers": was_explicit("preferred_sellers"),
            "blocked_sellers": was_explicit("blocked_sellers"),
            "quantity": was_explicit("quantity"),
            "purchase_scope": was_explicit("purchase_scope"),
            "rollout_type": was_explicit("rollout_type"),
            "replacement_mode": was_explicit("replacement_mode"),
            "growth_expectation": was_explicit("growth_expectation"),
            "performance_priority": was_explicit("performance_priority"),
            "portability_need": was_explicit("portability_need"),
            "support_expectation": was_explicit("support_expectation"),
            "availability_need": was_explicit("availability_need"),
            "existing_infrastructure": was_explicit("existing_infrastructure"),
            "requested_ram_gb": was_explicit("requested_ram", "requested_ram_gb"),
            "requested_storage_gb": was_explicit("requested_storage", "requested_storage_gb"),
            "minimum_warranty_years": was_explicit("minimum_warranty_years"),
            "required_port_count": was_explicit("required_port_count"),
            "required_throughput_mbps": was_explicit("required_throughput_mbps"),
            "required_duplex_printing": was_explicit("required_duplex_printing"),
            "required_scanner": was_explicit("required_scanner"),
            "min_print_speed_ppm": was_explicit("min_print_speed_ppm"),
            "required_printer_type": was_explicit("required_printer_type"),
            "required_print_technology": was_explicit("required_print_technology"),
            "required_color_output": was_explicit("required_color_output"),
            "min_monthly_duty_cycle_pages": was_explicit("min_monthly_duty_cycle_pages"),
            "required_automatic_document_feeder": was_explicit("required_automatic_document_feeder"),
            "required_paper_sizes": was_explicit("required_paper_sizes"),
            "required_network_roles": was_explicit("required_network_roles"),
            "required_vpn_user_capacity": was_explicit("required_vpn_user_capacity"),
            "required_virtualization_ready": was_explicit("required_virtualization_ready"),
            "required_virtualization_platforms": was_explicit("required_virtualization_platforms"),
            "max_rack_units": was_explicit("max_rack_units"),
            "max_power_draw_watts": was_explicit("max_power_draw_watts"),
            "battery_life_hours_min": was_explicit("battery_life_hours_min"),
            "cpu_preference": was_explicit("cpu_preference"),
            "gpu_requirement": was_explicit("gpu_requirement"),
            "screen_size_preference": was_explicit("screen_size_preference"),
            "weight_kg_max": was_explicit("weight_kg_max"),
            "warranty_type_preference": was_explicit("warranty_type_preference"),
        }
        for field, is_explicit in explicit_fields.items():
            if is_explicit and self._value_present(requirements.get(field)):
                sources[field] = "user_explicit"

        hint_key_map = {
            "preferred_category": "preferred_category",
            "industry": "industry",
            "business_type": "business_type",
            "team_size": "team_size",
            "workload_types": "workloads",
            "application_signals": "application_signals",
            "budget": "budget",
            "budget_scope": "budget_scope",
            "preferred_manufacturers": "preferred_manufacturers",
            "blocked_manufacturers": "blocked_manufacturers",
            "preferred_sellers": "preferred_sellers",
            "blocked_sellers": "blocked_sellers",
            "growth_expectation": "growth_expectation",
            "performance_priority": "performance_priority",
            "portability_need": "portability_need",
            "support_expectation": "support_expectation",
            "availability_need": "availability_need",
            "quantity": "quantity",
            "purchase_scope": "purchase_scope",
            "rollout_type": "rollout_type",
            "replacement_mode": "replacement_mode",
            "existing_infrastructure": "existing_infrastructure",
            "requested_ram": "requested_ram_gb",
            "requested_ram_gb": "requested_ram_gb",
            "requested_storage": "requested_storage_gb",
            "requested_storage_gb": "requested_storage_gb",
            "minimum_warranty_years": "minimum_warranty_years",
            "required_port_count": "required_port_count",
            "required_throughput_mbps": "required_throughput_mbps",
            "required_duplex_printing": "required_duplex_printing",
            "required_scanner": "required_scanner",
            "min_print_speed_ppm": "min_print_speed_ppm",
            "required_printer_type": "required_printer_type",
            "required_print_technology": "required_print_technology",
            "required_color_output": "required_color_output",
            "min_monthly_duty_cycle_pages": "min_monthly_duty_cycle_pages",
            "required_automatic_document_feeder": "required_automatic_document_feeder",
            "required_paper_sizes": "required_paper_sizes",
            "required_network_roles": "required_network_roles",
            "required_vpn_user_capacity": "required_vpn_user_capacity",
            "required_virtualization_ready": "required_virtualization_ready",
            "required_virtualization_platforms": "required_virtualization_platforms",
            "max_rack_units": "max_rack_units",
            "max_power_draw_watts": "max_power_draw_watts",
            "battery_life_hours_min": "battery_life_hours_min",
            "cpu_preference": "cpu_preference",
            "gpu_requirement": "gpu_requirement",
            "screen_size_preference": "screen_size_preference",
            "weight_kg_max": "weight_kg_max",
            "warranty_type_preference": "warranty_type_preference",
        }
        for hint_key, source in source_hints.items():
            target_key = hint_key_map.get(hint_key)
            if not target_key or target_key in sources:
                continue
            if self._value_present(requirements.get(target_key)):
                sources[target_key] = source

        if requirements.get("budget_scope") and "budget_scope" not in sources:
            sources["budget_scope"] = "rule_inferred"
        if requirements.get("purchase_scope") and "purchase_scope" not in sources:
            sources["purchase_scope"] = "rule_inferred"
        if requirements.get("rollout_type") and "rollout_type" not in sources:
            sources["rollout_type"] = "rule_inferred"
        if requirements.get("replacement_mode") and "replacement_mode" not in sources:
            sources["replacement_mode"] = "rule_inferred"
        if requirements.get("workloads") and "workloads" not in sources:
            sources["workloads"] = "rule_inferred"
        return sources

    def _field_state(self, value, source):
        if not self._value_present(value):
            return "unknown"
        if source in {"user_explicit", "context_explicit"}:
            return "confirmed"
        return "inferred"

    def _build_assumption_severity(self, field_state):
        severities = {}
        for field, state in dict(field_state or {}).items():
            if state == "confirmed":
                continue
            severity = ASSUMPTION_SEVERITY_BY_FIELD.get(field)
            if severity:
                severities[field] = severity
        return severities

    def _value_present(self, value):
        return value not in (None, "", [], {})

    def _build_review_state(self, payload):
        payload = dict(payload or {})
        review_acceptance = normalize_optional_bool(payload.get("review_acceptance"))
        edited_inferred_values = self._normalize_review_edits(payload)
        edited_fields = sorted(edited_inferred_values)
        submitted = review_acceptance is not None or bool(edited_fields)
        audit = []
        if edited_fields:
            audit.append(
                {
                    "action": "submit_edits",
                    "edited_fields": list(edited_fields),
                }
            )
        if review_acceptance is True:
            audit.append({"action": "request_acceptance"})
        elif review_acceptance is False:
            audit.append({"action": "continue_editing"})
        return {
            "workflow_version": "review-v2",
            "submitted": submitted,
            "review_acceptance_requested": review_acceptance is True,
            "continue_editing": review_acceptance is False,
            "accepted": False,
            "edited_inferred_values": edited_inferred_values,
            "edited_fields": edited_fields,
            "status": (
                "acceptance_requested"
                if review_acceptance is True
                else "edits_submitted"
                if edited_fields
                else "review_pending"
            ),
            "audit": audit,
        }

    def _normalize_review_edits(self, payload):
        payload = dict(payload or {})
        raw_edits = payload.get("edited_inferred_values") or {}
        if not isinstance(raw_edits, dict):
            return {}

        normalized = {}
        categories = normalize_categories(raw_edits.get("preferred_categories"))
        direct_category = normalize_category(raw_edits.get("preferred_category") or raw_edits.get("category"))
        if direct_category and direct_category not in categories:
            categories.insert(0, direct_category)
        if "preferred_category" in raw_edits or "category" in raw_edits or "preferred_categories" in raw_edits:
            normalized["preferred_category"] = categories[0] if categories else None

        if "industry" in raw_edits:
            normalized["industry"] = str(raw_edits.get("industry") or "").strip() or None
        if "business_type" in raw_edits:
            normalized["business_type"] = str(raw_edits.get("business_type") or "").strip() or None
        if "team_size" in raw_edits:
            normalized["team_size"] = parse_team_size(raw_edits.get("team_size"))
        if "workloads" in raw_edits or "workload_types" in raw_edits:
            normalized["workloads"] = normalize_workloads(
                raw_edits.get("workloads") or raw_edits.get("workload_types")
            )
        if "application_signals" in raw_edits:
            normalized["application_signals"] = self.signal_service.sanitize_application_signals(
                raw_edits.get("application_signals")
            )
        if "budget" in raw_edits:
            normalized["budget"] = parse_money_value(raw_edits.get("budget"))
        if "quantity" in raw_edits:
            normalized["quantity"] = parse_team_size(raw_edits.get("quantity"))

        category_hints = categories or normalize_categories(payload.get("preferred_categories"))
        payload_category = normalize_category(payload.get("category") or payload.get("preferred_category"))
        if payload_category and payload_category not in category_hints:
            category_hints.insert(0, payload_category)
        quantity_hint = normalized.get("quantity")
        if quantity_hint is None:
            quantity_hint = parse_team_size(raw_edits.get("quantity")) if "quantity" in raw_edits else parse_team_size(payload.get("quantity"))
        team_size_hint = normalized.get("team_size")
        if team_size_hint is None:
            team_size_hint = parse_team_size(raw_edits.get("team_size")) if "team_size" in raw_edits else parse_team_size(payload.get("team_size"))
        hint_text = " ".join(
            part
            for part in (
                payload.get("chat_text"),
                payload.get("raw_chat"),
                payload.get("notes"),
            )
            if str(part or "").strip()
        )

        if "budget_scope" in raw_edits:
            normalized["budget_scope"] = normalize_budget_scope(
                raw_edits.get("budget_scope"),
                preferred_categories=category_hints,
                hint_text=hint_text,
                quantity=quantity_hint,
            )
        if "purchase_scope" in raw_edits:
            normalized["purchase_scope"] = normalize_purchase_scope(
                raw_edits.get("purchase_scope"),
                preferred_categories=category_hints,
                quantity=quantity_hint,
                team_size=team_size_hint,
                hint_text=hint_text,
            )
        if "rollout_type" in raw_edits:
            normalized["rollout_type"] = normalize_rollout_type(raw_edits.get("rollout_type"))
        if "replacement_mode" in raw_edits:
            normalized["replacement_mode"] = normalize_replacement_mode(raw_edits.get("replacement_mode"))
        if "growth_expectation" in raw_edits:
            growth_value = str(raw_edits.get("growth_expectation") or "").strip()
            normalized["growth_expectation"] = normalize_growth_expectation(growth_value) if growth_value else None
        if "performance_priority" in raw_edits:
            normalized["performance_priority"] = str(raw_edits.get("performance_priority") or "").strip() or None
        if "portability_need" in raw_edits:
            normalized["portability_need"] = str(raw_edits.get("portability_need") or "").strip() or None
        if "support_expectation" in raw_edits:
            normalized["support_expectation"] = str(raw_edits.get("support_expectation") or "").strip() or None
        if "availability_need" in raw_edits:
            normalized["availability_need"] = normalize_availability_need(raw_edits.get("availability_need"))
        if "existing_infrastructure" in raw_edits:
            normalized["existing_infrastructure"] = normalize_text_list(raw_edits.get("existing_infrastructure"))
        if "minimum_warranty_years" in raw_edits:
            normalized["minimum_warranty_years"] = _parse_warranty_years_value(raw_edits.get("minimum_warranty_years"))
        if "required_port_count" in raw_edits:
            normalized["required_port_count"] = parse_port_count(raw_edits.get("required_port_count"))
        if "required_throughput_mbps" in raw_edits:
            normalized["required_throughput_mbps"] = parse_throughput_mbps(raw_edits.get("required_throughput_mbps"))
        if "required_duplex_printing" in raw_edits:
            normalized["required_duplex_printing"] = normalize_optional_bool(raw_edits.get("required_duplex_printing"))
        if "required_scanner" in raw_edits:
            normalized["required_scanner"] = normalize_optional_bool(raw_edits.get("required_scanner"))
        if "min_print_speed_ppm" in raw_edits:
            normalized["min_print_speed_ppm"] = parse_print_speed_ppm(raw_edits.get("min_print_speed_ppm"))
        if "required_printer_type" in raw_edits:
            normalized["required_printer_type"] = str(raw_edits.get("required_printer_type") or "").strip().lower() or None
        if "required_print_technology" in raw_edits:
            normalized["required_print_technology"] = str(raw_edits.get("required_print_technology") or "").strip().lower() or None
        if "required_color_output" in raw_edits:
            normalized["required_color_output"] = normalize_color_output(raw_edits.get("required_color_output")) or None
        if "min_monthly_duty_cycle_pages" in raw_edits:
            normalized["min_monthly_duty_cycle_pages"] = parse_page_volume(raw_edits.get("min_monthly_duty_cycle_pages"))
        if "required_automatic_document_feeder" in raw_edits:
            normalized["required_automatic_document_feeder"] = normalize_optional_bool(raw_edits.get("required_automatic_document_feeder"))
        if "required_paper_sizes" in raw_edits:
            normalized["required_paper_sizes"] = normalize_paper_sizes(raw_edits.get("required_paper_sizes"))
        if "required_network_roles" in raw_edits:
            normalized["required_network_roles"] = normalize_text_list(raw_edits.get("required_network_roles"))
        if "required_vpn_user_capacity" in raw_edits:
            normalized["required_vpn_user_capacity"] = parse_vpn_user_capacity(raw_edits.get("required_vpn_user_capacity"))
        if "required_virtualization_ready" in raw_edits:
            normalized["required_virtualization_ready"] = normalize_optional_bool(raw_edits.get("required_virtualization_ready"))
        if "required_virtualization_platforms" in raw_edits:
            normalized["required_virtualization_platforms"] = normalize_virtualization_platforms(raw_edits.get("required_virtualization_platforms"))
        if "max_rack_units" in raw_edits:
            normalized["max_rack_units"] = parse_rack_units(raw_edits.get("max_rack_units"))
        if "max_power_draw_watts" in raw_edits:
            normalized["max_power_draw_watts"] = parse_power_watts(raw_edits.get("max_power_draw_watts"))
        if "battery_life_hours_min" in raw_edits:
            normalized["battery_life_hours_min"] = _parse_intake_integer(raw_edits.get("battery_life_hours_min"))
        if "cpu_preference" in raw_edits:
            normalized["cpu_preference"] = str(raw_edits.get("cpu_preference") or "").strip() or None
        if "gpu_requirement" in raw_edits:
            normalized["gpu_requirement"] = str(raw_edits.get("gpu_requirement") or "").strip() or None
        if "screen_size_preference" in raw_edits:
            raw_screen = raw_edits.get("screen_size_preference")
            screen_inches = parse_screen_size_inches_value(raw_screen)
            normalized["screen_size_preference"] = (
                f"{screen_inches:.1f} inch" if screen_inches is not None else str(raw_screen or "").strip() or None
            )
        if "weight_kg_max" in raw_edits:
            normalized["weight_kg_max"] = parse_weight_kg_value(raw_edits.get("weight_kg_max"))
        if "warranty_type_preference" in raw_edits:
            normalized["warranty_type_preference"] = normalize_warranty_type(raw_edits.get("warranty_type_preference"))
        return normalized

    def _apply_review_edits(self, payload, edited_inferred_values):
        payload = dict(payload or {})
        edited_inferred_values = dict(edited_inferred_values or {})
        source_hints = dict(payload.get("_field_source_hints") or {})

        field_mapping = {
            "preferred_category": ("category", "preferred_category"),
            "industry": ("industry", "industry"),
            "business_type": ("business_type", "business_type"),
            "team_size": ("team_size", "team_size"),
            "workloads": ("workload_types", "workload_types"),
            "application_signals": ("application_signals", "application_signals"),
            "budget": ("budget", "budget"),
            "budget_scope": ("budget_scope", "budget_scope"),
            "quantity": ("quantity", "quantity"),
            "purchase_scope": ("purchase_scope", "purchase_scope"),
            "rollout_type": ("rollout_type", "rollout_type"),
            "replacement_mode": ("replacement_mode", "replacement_mode"),
            "growth_expectation": ("growth_expectation", "growth_expectation"),
            "performance_priority": ("performance_priority", "performance_priority"),
            "portability_need": ("portability_need", "portability_need"),
            "support_expectation": ("support_expectation", "support_expectation"),
            "availability_need": ("availability_need", "availability_need"),
            "existing_infrastructure": ("existing_infrastructure", "existing_infrastructure"),
            "minimum_warranty_years": ("minimum_warranty_years", "minimum_warranty_years"),
            "required_port_count": ("required_port_count", "required_port_count"),
            "required_throughput_mbps": ("required_throughput_mbps", "required_throughput_mbps"),
            "required_duplex_printing": ("required_duplex_printing", "required_duplex_printing"),
            "required_scanner": ("required_scanner", "required_scanner"),
            "min_print_speed_ppm": ("min_print_speed_ppm", "min_print_speed_ppm"),
            "required_printer_type": ("required_printer_type", "required_printer_type"),
            "required_print_technology": ("required_print_technology", "required_print_technology"),
            "required_color_output": ("required_color_output", "required_color_output"),
            "min_monthly_duty_cycle_pages": ("min_monthly_duty_cycle_pages", "min_monthly_duty_cycle_pages"),
            "required_automatic_document_feeder": ("required_automatic_document_feeder", "required_automatic_document_feeder"),
            "required_paper_sizes": ("required_paper_sizes", "required_paper_sizes"),
            "required_network_roles": ("required_network_roles", "required_network_roles"),
            "required_vpn_user_capacity": ("required_vpn_user_capacity", "required_vpn_user_capacity"),
            "required_virtualization_ready": ("required_virtualization_ready", "required_virtualization_ready"),
            "required_virtualization_platforms": ("required_virtualization_platforms", "required_virtualization_platforms"),
            "max_rack_units": ("max_rack_units", "max_rack_units"),
            "max_power_draw_watts": ("max_power_draw_watts", "max_power_draw_watts"),
            "battery_life_hours_min": ("battery_life_hours_min", "battery_life_hours_min"),
            "cpu_preference": ("cpu_preference", "cpu_preference"),
            "gpu_requirement": ("gpu_requirement", "gpu_requirement"),
            "screen_size_preference": ("screen_size_preference", "screen_size_preference"),
            "weight_kg_max": ("weight_kg_max", "weight_kg_max"),
            "warranty_type_preference": ("warranty_type_preference", "warranty_type_preference"),
        }

        for review_field, value in edited_inferred_values.items():
            target = field_mapping.get(review_field)
            if not target:
                continue
            payload_key, source_hint_key = target
            payload[payload_key] = value
            source_hints[source_hint_key] = "context_explicit"

        payload["_field_source_hints"] = source_hints
        return payload

    def normalize_state_requirements(self, requirements: dict) -> dict:
        return self.normalize(requirements or {})

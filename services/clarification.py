# from .config_service import ProcurementConfigService


# INFRASTRUCTURE_CATEGORIES = {"servers", "networking"}
# DEFAULT_BLOCKING_SIGNALS = {
#     "preferred_category",
#     "category_or_workload",
#     "budget",
# }
# # workload_or_application_profile is intentionally excluded from blocking signals.
# # The planner prompt and product spec both allow baseline recommendations once
# # category + budget are known — workload is a refinement signal, not a gating one.
# FOLLOW_UP_PRIORITY = [
#     "preferred_category",
#     "category_or_workload",
#     "budget",
#     "workload_or_application_profile",
#     "application_profile",
#     "team_size",
#     "budget_scope",
#     "purchase_scope_or_quantity",
#     "growth_expectation",
#     "performance_priority",
# ]
# FOLLOW_UP_PROMPTS = {
#     "preferred_category": "Are you mainly trying to buy laptops, desktops, servers, networking equipment, printers, or accessories?",
#     "category_or_workload": "What are you mainly trying to buy first: laptops, desktops, servers, networking, printers, accessories, or a mix?",
#     "workload_or_application_profile": (
#         "What kind of work will these systems support day to day, and which apps or tools matter most? "
#         "You can mention more than one, like Excel, browser tools, Docker, Photoshop, Premiere, or VMware."
#     ),
#     "team_size": "How many users, seats, or endpoints are in scope for this purchase?",
#     "budget": "What budget should I optimize for?",
#     "budget_scope": "Should I treat that budget as per device or as the total project budget?",
#     "purchase_scope_or_quantity": (
#         "Is this for a single device or a wider team rollout, and if it is a rollout, roughly how many units are in scope?"
#     ),
#     "application_profile": (
#         "Which apps or tools matter most here? You can mention more than one, like Excel, browser tools, "
#         "Docker, Photoshop, Premiere, or VMware."
#     ),
#     "growth_expectation": "Should the recommendation plan for a steady team, moderate growth, or rapid expansion?",
#     "performance_priority": "Should I optimize more for cost, a balanced option, or stronger performance?",
# }
# FOLLOW_UP_RATIONALES = {
#     "preferred_category": (
#         "An explicit category choice is needed before ranking when the current brief says the device type is still undecided."
#     ),
#     "category_or_workload": (
#         "The engine needs at least one product or workload signal before ranking catalog items."
#     ),
#     "workload_or_application_profile": (
#         "A device category and budget are not enough on their own. The engine still needs the day-to-day work pattern or app mix."
#     ),
#     "team_size": "Expected usage scale improves recommendation quality and capacity planning.",
#     "budget": "Budget is required to rank practical recommendations and avoid unrealistic options.",
#     "budget_scope": "Budget scope changes whether the engine evaluates a unit price or the total deployment cost.",
#     "purchase_scope_or_quantity": (
#         "Seat-based device requests need rollout scope or unit quantity before the engine can treat the result as a firm recommendation."
#     ),
#     "application_profile": (
#         "The app or tool mix changes sizing more than a broad workload label, especially for developer, creative, AI, and infrastructure briefs."
#     ),
#     "growth_expectation": (
#         "Growth expectation affects how much performance and capacity headroom the engine should reserve."
#     ),
#     "performance_priority": (
#         "Performance priority helps separate value-oriented options from premium recommendations."
#     ),
# }
# FIELD_IMPORTANCE = {
#     "preferred_category": 1.0,
#     "category_or_workload": 1.0,
#     "workload_or_application_profile": 1.0,
#     "application_profile": 0.6,
#     "budget": 0.9,
#     "budget_scope": 0.9,
#     "purchase_scope_or_quantity": 0.9,
#     "team_size": 0.7,
#     "growth_expectation": 0.4,
#     "performance_priority": 0.3,
# }
# FIELD_SENSITIVITY = {
#     "preferred_category": 1.0,
#     "category_or_workload": 1.0,
#     "workload_or_application_profile": 1.0,
#     "budget": 1.0,
#     "budget_scope": 0.9,
#     "purchase_scope_or_quantity": 1.0,
#     "team_size": 0.8,
#     "application_profile": 0.8,
#     "growth_expectation": 0.5,
#     "performance_priority": 0.5,
# }
# DEFAULT_QUESTION_IMPACT_THRESHOLD = 0.35
# DEFAULT_DECISION_CONFIDENCE_BANDS = {
#     "high_min": 0.8,
#     "medium_min": 0.55,
# }


# def highest_priority_missing_field(missing_fields):
#     missing_list = list(missing_fields or [])
#     missing_set = set(missing_list)
#     for field in FOLLOW_UP_PRIORITY:
#         if field in missing_set:
#             return field
#     return missing_list[0] if missing_list else None


# def default_follow_up_prompt(field):
#     return FOLLOW_UP_PROMPTS.get(field) or FOLLOW_UP_PROMPTS["budget"]


# class ProcurementClarificationService:
#     def __init__(self, config_service=None):
#         self.config_service = config_service or ProcurementConfigService()

#     def assess(self, requirements):
#         requirements = requirements or {}
#         missing_signals = []
#         seat_based_categories = self._seat_based_categories()
#         seat_based_workloads = self._seat_based_workloads()

#         categories = self._normalized_categories(requirements)
#         resolved_categories = [category for category in categories if category and category != "not_sure"]
#         has_ambiguous_category = any(category == "not_sure" for category in categories)
#         workloads = self._normalized_workloads(requirements)
#         has_profile_signal = bool(
#             workloads
#             or requirements.get("application_signals")
#             or requirements.get("requested_ram_gb")
#             or requirements.get("requested_storage_gb")
#             or requirements.get("existing_infrastructure")
#         )

#         if has_ambiguous_category:
#             missing_signals.append("preferred_category")

#         if not resolved_categories and not has_profile_signal:
#             missing_signals.append("category_or_workload")
#         elif not resolved_categories and len(set(workloads or [])) > 1:
#             missing_signals.append("preferred_category")
#         elif resolved_categories and not has_profile_signal:
#             missing_signals.append("workload_or_application_profile")

#         has_seat_based_category = bool(set(resolved_categories).intersection(seat_based_categories))
#         has_infrastructure_category = bool(set(resolved_categories).intersection(INFRASTRUCTURE_CATEGORIES))
#         has_seat_based_workload = bool(set(workloads).intersection(seat_based_workloads))
#         needs_team_size = has_seat_based_category or (
#             has_seat_based_workload and not has_infrastructure_category
#         )
#         if needs_team_size and not (requirements.get("team_size") or requirements.get("quantity")):
#             missing_signals.append("team_size")
#         elif self._needs_purchase_scope_or_quantity(
#             requirements=requirements,
#             resolved_categories=resolved_categories,
#             workloads=workloads,
#             seat_based_categories=seat_based_categories,
#             seat_based_workloads=seat_based_workloads,
#         ):
#             missing_signals.append("purchase_scope_or_quantity")

#         can_rank_without_budget = self._can_rank_without_budget(requirements, resolved_categories, workloads)

#         if requirements.get("budget") is None:
#             missing_signals.append("budget")
#         elif self._needs_budget_scope(
#             requirements,
#             resolved_categories,
#             workloads,
#             seat_based_categories,
#             seat_based_workloads,
#         ):
#             missing_signals.append("budget_scope")

#         if self._needs_application_profile(requirements, workloads):
#             missing_signals.append("application_profile")

#         # Soft signals: only surface them once the blocking signals are resolved.
#         # Asking about growth or priority before category/budget is locked wastes turns.
#         blocking_already_clear = not bool(
#             self._blocking_signals().intersection(set(missing_signals))
#         )
#         if blocking_already_clear and not requirements.get("growth_expectation"):
#             missing_signals.append("growth_expectation")
#         if blocking_already_clear and not requirements.get("performance_priority"):
#             missing_signals.append("performance_priority")

#         missing_signals = self._dedupe_preserve_order(missing_signals)

#         field_confidence = self._field_confidence(
#             requirements=requirements,
#             resolved_categories=resolved_categories,
#             has_profile_signal=has_profile_signal,
#             needs_team_size=needs_team_size,
#         )
#         question_candidates = self._question_candidates(
#             missing_signals=missing_signals,
#             field_confidence=field_confidence,
#             categories=categories,
#             resolved_categories=resolved_categories,
#             workloads=workloads,
#             seat_based_workloads=seat_based_workloads,
#             requirements=requirements,
#         )
#         follow_up_questions = [
#             {
#                 "key": item["key"],
#                 "prompt": item["prompt"],
#                 "rationale": item["rationale"],
#                 "impact": item["impact"],
#             }
#             for item in question_candidates
#         ]

#         is_ready = not bool(self._blocking_signals().intersection(missing_signals))
#         if not missing_signals:
#             confidence = "high"
#         elif is_ready:
#             confidence = "medium"
#         else:
#             confidence = "low"

#         decision_confidence_score = self._decision_confidence_score(
#             requirements=requirements,
#             is_ready=is_ready,
#             missing_signals=missing_signals,
#         )
#         decision_confidence_band = self._decision_confidence_band(decision_confidence_score)
#         top_question = follow_up_questions[0] if follow_up_questions else None
#         recommended_question_budget = self._recommended_question_budget(
#             is_ready,
#             decision_confidence_band,
#             question_candidates,
#         )
#         threshold = self.question_impact_threshold()
#         recommended_refinement_question = (
#             top_question["prompt"]
#             if is_ready and top_question and top_question["impact"] >= threshold
#             else None
#         )

#         return {
#             "is_ready": is_ready,
#             "confidence": confidence,
#             "can_rank_without_budget": can_rank_without_budget,
#             "missing_signals": missing_signals,
#             "highest_priority_missing_field": highest_priority_missing_field(missing_signals),
#             "recommended_question_id": top_question["key"] if top_question and recommended_question_budget else None,
#             "next_question": top_question["prompt"] if top_question and recommended_question_budget else None,
#             "follow_up_questions": follow_up_questions,
#             "decision_confidence_score": decision_confidence_score,
#             "decision_confidence_band": decision_confidence_band,
#             "recommended_question_budget": recommended_question_budget,
#             "routing_recommendation": self._routing_recommendation(is_ready, decision_confidence_band),
#             "recommended_refinement_question": recommended_refinement_question,
#             "field_confidence": field_confidence,
#             "question_strategy": self._question_strategy(is_ready, question_candidates),
#             "question_candidates": follow_up_questions[:3],
#         }

#     def should_defer_ranking(self, readiness):
#         missing = set((readiness or {}).get("missing_signals") or [])
#         if "budget" in missing and bool((readiness or {}).get("can_rank_without_budget")):
#             missing.discard("budget")
#         return bool(self._blocking_signals().intersection(missing))

#     def _question_candidates(
#         self,
#         missing_signals,
#         field_confidence,
#         categories,
#         resolved_categories,
#         workloads,
#         seat_based_workloads,
#         requirements,
#     ):
#         candidates = []
#         for field in self._sorted_missing_signals(missing_signals):
#             prompt = self._prompt_for_field(
#                 field=field,
#                 categories=categories,
#                 resolved_categories=resolved_categories,
#                 workloads=workloads,
#                 seat_based_workloads=seat_based_workloads,
#                 requirements=requirements,
#             )
#             rationale = self._rationale_for_field(
#                 field=field,
#                 categories=categories,
#                 workloads=workloads,
#                 seat_based_workloads=seat_based_workloads,
#             )
#             impact = self._question_impact(field, field_confidence)
#             candidates.append(
#                 {
#                     "key": field,
#                     "prompt": prompt,
#                     "rationale": rationale,
#                     "impact": impact,
#                 }
#             )
#         candidates.sort(
#             key=lambda item: (
#                 -float(item.get("impact") or 0.0),
#                 FOLLOW_UP_PRIORITY.index(item["key"]) if item["key"] in FOLLOW_UP_PRIORITY else 999,
#             )
#         )
#         return candidates

#     def _prompt_for_field(
#         self,
#         field,
#         categories,
#         resolved_categories,
#         workloads,
#         seat_based_workloads,
#         requirements,
#     ):
#         field = str(field or "").strip()

#         if field == "category_or_workload":
#             if not resolved_categories and not workloads:
#                 return default_follow_up_prompt("category_or_workload")
#             if workloads and not resolved_categories:
#                 return default_follow_up_prompt("preferred_category")
#             if resolved_categories and not self._has_profile_signal(requirements, workloads):
#                 return default_follow_up_prompt("workload_or_application_profile")
#             return default_follow_up_prompt("category_or_workload")

#         if field == "workload_or_application_profile":
#             return default_follow_up_prompt("workload_or_application_profile")

#         if field == "application_profile":
#             return default_follow_up_prompt("application_profile")

#         if field == "team_size":
#             return self._team_size_prompt(categories, workloads, seat_based_workloads)

#         return default_follow_up_prompt(field)

#     def _rationale_for_field(self, field, categories, workloads, seat_based_workloads):
#         if field == "team_size":
#             return self._team_size_rationale(categories, workloads, seat_based_workloads)
#         return FOLLOW_UP_RATIONALES.get(field) or FOLLOW_UP_RATIONALES["budget"]

#     def _question_impact(self, field, field_confidence):
#         importance = float(FIELD_IMPORTANCE.get(field, 0.4))
#         sensitivity = float(FIELD_SENSITIVITY.get(field, 0.5))
#         confidence = float(field_confidence.get(field, 0.0) or 0.0)
#         uncertainty = max(0.15, 1.0 - confidence)
#         return round(min(importance * sensitivity * uncertainty * 1.25, 1.0), 2)

#     def _field_confidence(self, requirements, resolved_categories, has_profile_signal, needs_team_size):
#         workloads = self._normalized_workloads(requirements)
#         application_signals = requirements.get("application_signals") or []
#         capability_tags = requirements.get("capability_tags") or []

#         return {
#             "preferred_category": 1.0 if resolved_categories else 0.2,
#             "workload_or_application": 1.0 if has_profile_signal else 0.0,
#             "budget": 1.0 if requirements.get("budget") is not None else 0.0,
#             "budget_scope": 1.0 if requirements.get("budget_scope") else 0.0,
#             "purchase_scope_or_quantity": 1.0 if (requirements.get("purchase_scope") or requirements.get("quantity")) else 0.0,
#             "team_size": 1.0 if (requirements.get("team_size") or requirements.get("quantity")) else (0.3 if needs_team_size else 0.0),
#             "application_profile": 1.0 if application_signals else (0.2 if (workloads or capability_tags) else 0.0),
#             "growth_expectation": 1.0 if requirements.get("growth_expectation") else 0.2,
#             "performance_priority": 1.0 if requirements.get("performance_priority") else 0.2,
#         }

#     def _blocking_signals(self):
#         policy = self.config_service.get_clarification_policy() or {}
#         configured = list(policy.get("blocking_signals") or [])
#         if configured:
#             return set(configured)
#         return set(DEFAULT_BLOCKING_SIGNALS)

#     def _routing_recommendation(self, is_ready, confidence_band):
#         if not is_ready:
#             return "clarify_before_recommendation"
#         if confidence_band == "low":
#             return "clarify_before_recommendation"
#         if confidence_band == "medium":
#             return "recommend_with_optional_refinement"
#         return "recommend_now"

#     def _question_strategy(self, is_ready, question_candidates):
#         if not question_candidates:
#             return "no_question_needed"
#         if is_ready:
#             return "ask_top_impact_question_if_helpful"
#         return "ask_top_impact_question"

#     def _sorted_missing_signals(self, missing_signals):
#         ordered = self._dedupe_preserve_order(missing_signals)
#         return sorted(
#             ordered,
#             key=lambda field: FOLLOW_UP_PRIORITY.index(field) if field in FOLLOW_UP_PRIORITY else 999,
#         )

#     def _dedupe_preserve_order(self, values):
#         result = []
#         for value in list(values or []):
#             if value and value not in result:
#                 result.append(value)
#         return result

#     def _normalized_categories(self, requirements):
#         categories = list(requirements.get("preferred_categories") or [])
#         preferred_category = requirements.get("preferred_category")
#         if preferred_category and preferred_category not in categories:
#             categories.insert(0, preferred_category)
#         return self._dedupe_preserve_order(categories)

#     def _normalized_workloads(self, requirements):
#         return self._dedupe_preserve_order(requirements.get("workloads") or [])

#     def _has_profile_signal(self, requirements, workloads):
#         return bool(
#             workloads
#             or requirements.get("application_signals")
#             or requirements.get("requested_ram_gb")
#             or requirements.get("requested_storage_gb")
#             or requirements.get("existing_infrastructure")
#         )

#     def _can_rank_without_budget(self, requirements, resolved_categories, workloads):
#         if requirements.get("budget") is not None:
#             return False

#         category_set = set(resolved_categories or [])
#         workload_set = set(workloads or [])
#         if not category_set and not workload_set:
#             return False

#         high_signal_spec_fields = (
#             "requested_ram_gb",
#             "requested_storage_gb",
#             "minimum_warranty_years",
#             "required_port_count",
#             "required_throughput_mbps",
#             "required_duplex_printing",
#             "required_scanner",
#             "min_print_speed_ppm",
#             "required_printer_type",
#             "required_print_technology",
#             "required_color_output",
#             "min_monthly_duty_cycle_pages",
#             "required_automatic_document_feeder",
#             "required_paper_sizes",
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
#         )
#         explicit_spec_count = 0
#         for field in high_signal_spec_fields:
#             value = requirements.get(field)
#             if value not in (None, "", [], {}, False):
#                 explicit_spec_count += 1

#         has_app_signal = bool(requirements.get("application_signals") or requirements.get("capability_tags"))
#         return explicit_spec_count >= 2 or (explicit_spec_count >= 1 and has_app_signal)

#     def question_impact_threshold(self):
#         threshold = self.config_service.get_clarification_policy().get("question_impact_threshold")
#         if isinstance(threshold, (int, float)):
#             return float(threshold)
#         return DEFAULT_QUESTION_IMPACT_THRESHOLD

#     def _team_size_prompt(self, categories, workloads, seat_based_workloads):
#         category_set = set(categories or [])
#         workload_set = set(workloads or [])
#         if "networking" in category_set:
#             return "How many users, endpoints, or branch devices should this network support?"
#         if "servers" in category_set:
#             return "How many users or workloads should this server environment support?"
#         if workload_set.intersection(seat_based_workloads):
#             return "How many users or seats are in scope for this purchase?"
#         return default_follow_up_prompt("team_size")

#     def _team_size_rationale(self, categories, workloads, seat_based_workloads):
#         category_set = set(categories or [])
#         workload_set = set(workloads or [])
#         if "networking" in category_set:
#             return "Expected user or endpoint load helps size networking recommendations without assuming one device per user."
#         if "servers" in category_set:
#             return "Expected user or workload scale helps size server recommendations without assuming one server per user."
#         if workload_set.intersection(seat_based_workloads):
#             return "Seat count affects quantity assumptions and budget fit for end-user devices."
#         return FOLLOW_UP_RATIONALES["team_size"]

#     def _seat_based_categories(self):
#         return set(self.config_service.get_rules_config().get("seat_based_categories") or [])

#     def _seat_based_workloads(self):
#         rules_config = self.config_service.get_rules_config()
#         seat_based_categories = self._seat_based_categories()
#         workload_targets = rules_config.get("workload_targets") or {}
#         return {
#             workload
#             for workload, profile in workload_targets.items()
#             if set(profile.get("categories") or []).intersection(seat_based_categories)
#             and not set(profile.get("categories") or []).intersection(INFRASTRUCTURE_CATEGORIES)
#         }

#     def _needs_application_profile(self, requirements, workloads):
#         workload_set = set(workloads or [])
#         if not workload_set.intersection({"software_development", "creative_design", "ai_analytics", "server_infrastructure"}):
#             return False
#         if requirements.get("application_signals"):
#             return False
#         if requirements.get("requested_ram_gb") or requirements.get("requested_storage_gb"):
#             return False
#         capability_tags = set(requirements.get("capability_tags") or [])
#         if capability_tags.intersection(
#             {"gpu_needed", "high_ram", "storage_heavy", "virtualization", "branch_connectivity", "local_compute"}
#         ):
#             return False
#         return True

#     def _needs_budget_scope(self, requirements, resolved_categories, workloads, seat_based_categories, seat_based_workloads):
#         if requirements.get("budget_scope"):
#             return False

#         quantity = int(requirements.get("quantity") or 0)
#         if quantity > 1:
#             return True

#         if requirements.get("purchase_scope") == "team_rollout":
#             return True

#         category_set = set(resolved_categories or [])
#         workload_set = set(workloads or [])
#         has_seat_based_category = bool(category_set.intersection(seat_based_categories))
#         has_seat_based_workload = bool(workload_set.intersection(seat_based_workloads))
#         team_size = int(requirements.get("team_size") or 0)
#         return bool(team_size > 1 and (has_seat_based_category or has_seat_based_workload))

#     def _needs_purchase_scope_or_quantity(
#         self,
#         requirements,
#         resolved_categories,
#         workloads,
#         seat_based_categories,
#         seat_based_workloads,
#     ):
#         if requirements.get("purchase_scope") or requirements.get("quantity"):
#             return False

#         team_size = int(requirements.get("team_size") or 0)
#         if team_size <= 0:
#             return False

#         category_set = set(resolved_categories or [])
#         workload_set = set(workloads or [])
#         has_seat_based_category = bool(category_set.intersection(seat_based_categories))
#         has_seat_based_workload = bool(workload_set.intersection(seat_based_workloads))
#         has_infrastructure_category = bool(category_set.intersection(INFRASTRUCTURE_CATEGORIES))
#         return bool((has_seat_based_category or has_seat_based_workload) and not has_infrastructure_category)

#     def _decision_confidence_score(self, requirements, is_ready, missing_signals):
#         score = 0.0
#         if is_ready:
#             score += 0.45
#         if requirements.get("preferred_categories") or requirements.get("workloads"):
#             score += 0.15
#         if requirements.get("budget") is not None:
#             score += 0.15
#         if requirements.get("team_size") or requirements.get("quantity"):
#             score += 0.1
#         if requirements.get("application_signals"):
#             score += min(len(requirements.get("application_signals") or []) * 0.05, 0.1)
#         if requirements.get("capability_tags"):
#             score += min(len(requirements.get("capability_tags") or []) * 0.03, 0.09)
#         if requirements.get("requested_ram_gb") or requirements.get("requested_storage_gb"):
#             score += 0.08
#         missing_set = set(missing_signals or [])
#         if "workload_or_application_profile" in missing_set:
#             score -= 0.12
#         if "budget_scope" in missing_set:
#             score -= 0.08
#         if "application_profile" in missing_set:
#             score -= 0.08
#         return round(max(min(score, 1.0), 0.0), 2)

#     def _decision_confidence_band(self, score):
#         bands = self.config_service.get_clarification_policy().get("decision_confidence_bands") or {}
#         high_min = float(bands.get("high_min", DEFAULT_DECISION_CONFIDENCE_BANDS["high_min"]))
#         medium_min = float(bands.get("medium_min", DEFAULT_DECISION_CONFIDENCE_BANDS["medium_min"]))
#         if score >= high_min:
#             return "high"
#         if score >= medium_min:
#             return "medium"
#         return "low"

#     def _recommended_question_budget(self, is_ready, confidence_band, question_candidates):
#         top_question = question_candidates[0] if question_candidates else None
#         policy = self.config_service.get_clarification_policy().get("question_budget_policy") or {}
#         threshold = self.question_impact_threshold()
#         if (
#             top_question
#             and policy.get("allow_top_question_when_impact_meets_threshold", True)
#             and top_question["impact"] >= threshold
#         ):
#             return 1
#         if (
#             not is_ready
#             and confidence_band == "low"
#             and question_candidates
#             and policy.get("allow_when_not_ready_low_confidence", True)
#         ):
#             return 1
#         if (
#             is_ready
#             and confidence_band == "medium"
#             and top_question
#             and top_question["impact"] >= threshold
#             and policy.get("allow_optional_refinement_when_ready_medium_confidence", True)
#         ):
#             return 1
#         return 0



#######################################
#######################################
##########################################
# ########################################







# from .config_service import ProcurementConfigService
# from ...catalog.services.normalization import normalize_category

# INFRASTRUCTURE_CATEGORIES = {"servers", "networking"}
# DEFAULT_BLOCKING_SIGNALS = {
#     "preferred_category",
#     "category_or_workload",
#     "workload_or_application_profile",
#     "budget",
# }
# FOLLOW_UP_PRIORITY = [
#     "preferred_category",
#     "category_or_workload",
#     "budget",
#     "workload_or_application_profile",
#     "application_profile",
#     "team_size",
#     "budget_scope",
#     "purchase_scope_or_quantity",
#     "growth_expectation",
#     "performance_priority",
# ]
# FOLLOW_UP_PROMPTS = {
#     "preferred_category": "Are you mainly trying to buy laptops, desktops, servers, networking equipment, printers, or accessories?",
#     "category_or_workload": "What are you mainly trying to buy first: laptops, desktops, servers, networking, printers, accessories, or a mix?",
#     "workload_or_application_profile": (
#         "What kind of work will these systems support day to day, and which apps or tools matter most? "
#         "You can mention more than one, like Excel, browser tools, Docker, Photoshop, Premiere, or VMware."
#     ),
#     "team_size": "How many users, seats, or endpoints are in scope for this purchase?",
#     "budget": "What budget should I optimize for?",
#     "budget_scope": "Should I treat that budget as per device or as the total project budget?",
#     "purchase_scope_or_quantity": (
#         "Is this for a single device or a wider team rollout, and if it is a rollout, roughly how many units are in scope?"
#     ),
#     "application_profile": (
#         "Which apps or tools matter most here? You can mention more than one, like Excel, browser tools, "
#         "Docker, Photoshop, Premiere, or VMware."
#     ),
#     "growth_expectation": "Should the recommendation plan for a steady team, moderate growth, or rapid expansion?",
#     "performance_priority": "Should I optimize more for cost, a balanced option, or stronger performance?",
# }
# FOLLOW_UP_RATIONALES = {
#     "preferred_category": (
#         "An explicit category choice is needed before ranking when the current brief says the device type is still undecided."
#     ),
#     "category_or_workload": (
#         "The engine needs at least one product or workload signal before ranking catalog items."
#     ),
#     "workload_or_application_profile": (
#         "A device category and budget are not enough on their own. The engine still needs the day-to-day work pattern or app mix."
#     ),
#     "team_size": "Expected usage scale improves recommendation quality and capacity planning.",
#     "budget": "Budget is required to rank practical recommendations and avoid unrealistic options.",
#     "budget_scope": "Budget scope changes whether the engine evaluates a unit price or the total deployment cost.",
#     "purchase_scope_or_quantity": (
#         "Seat-based device requests need rollout scope or unit quantity before the engine can treat the result as a firm recommendation."
#     ),
#     "application_profile": (
#         "The app or tool mix changes sizing more than a broad workload label, especially for developer, creative, AI, and infrastructure briefs."
#     ),
#     "growth_expectation": (
#         "Growth expectation affects how much performance and capacity headroom the engine should reserve."
#     ),
#     "performance_priority": (
#         "Performance priority helps separate value-oriented options from premium recommendations."
#     ),
# }
# FIELD_IMPORTANCE = {
#     "preferred_category": 1.0,
#     "category_or_workload": 1.0,
#     "workload_or_application_profile": 1.0,
#     "application_profile": 0.6,
#     "budget": 0.9,
#     "budget_scope": 0.9,
#     "purchase_scope_or_quantity": 0.9,
#     "team_size": 0.7,
#     "growth_expectation": 0.4,
#     "performance_priority": 0.3,
# }
# FIELD_SENSITIVITY = {
#     "preferred_category": 1.0,
#     "category_or_workload": 1.0,
#     "workload_or_application_profile": 1.0,
#     "budget": 1.0,
#     "budget_scope": 0.9,
#     "purchase_scope_or_quantity": 1.0,
#     "team_size": 0.8,
#     "application_profile": 0.8,
#     "growth_expectation": 0.5,
#     "performance_priority": 0.5,
# }
# DEFAULT_QUESTION_IMPACT_THRESHOLD = 0.35
# DEFAULT_DECISION_CONFIDENCE_BANDS = {
#     "high_min": 0.8,
#     "medium_min": 0.55,
# }


# def highest_priority_missing_field(missing_fields):
#     missing_list = list(missing_fields or [])
#     missing_set = set(missing_list)
#     for field in FOLLOW_UP_PRIORITY:
#         if field in missing_set:
#             return field
#     return missing_list[0] if missing_list else None


# def default_follow_up_prompt(field):
#     return FOLLOW_UP_PROMPTS.get(field) or FOLLOW_UP_PROMPTS["budget"]


# class ProcurementClarificationService:
#     def __init__(self, config_service=None):
#         self.config_service = config_service or ProcurementConfigService()

#     def assess(self, requirements):
#         requirements = requirements or {}
#         missing_signals = []
#         seat_based_categories = self._seat_based_categories()
#         seat_based_workloads = self._seat_based_workloads()

#         categories = self._normalized_categories(requirements)
#         resolved_categories = [category for category in categories if category and category != "not_sure"]
#         intent_groups = [group for group in list(requirements.get("intent_groups") or []) if isinstance(group, dict)]
#         explicit_group_categories = [
#             normalize_category(group.get("preferred_category") or group.get("category"))
#             for group in intent_groups
#             if normalize_category(group.get("preferred_category") or group.get("category"))
#         ]
#         explicit_group_categories = self._dedupe_preserve_order(explicit_group_categories)
#         has_explicit_multi_category = len(self._dedupe_preserve_order(resolved_categories + explicit_group_categories)) >= 2
#         has_ambiguous_category = any(category == "not_sure" for category in categories) and not has_explicit_multi_category
#         workloads = self._normalized_workloads(requirements)
#         has_profile_signal = bool(
#             workloads
#             or requirements.get("application_signals")
#             or requirements.get("requested_ram_gb")
#             or requirements.get("requested_storage_gb")
#             or requirements.get("existing_infrastructure")
#         )

#         if has_ambiguous_category:
#             missing_signals.append("preferred_category")

#         if not resolved_categories and not has_profile_signal:
#             missing_signals.append("category_or_workload")
#         elif not resolved_categories and len(set(workloads or [])) > 1:
#             missing_signals.append("preferred_category")
#         elif resolved_categories and not has_profile_signal and requirements.get("budget") is None:
#             missing_signals.append("workload_or_application_profile")

#         has_seat_based_category = bool(set(resolved_categories).intersection(seat_based_categories))
#         has_infrastructure_category = bool(set(resolved_categories).intersection(INFRASTRUCTURE_CATEGORIES))
#         has_seat_based_workload = bool(set(workloads).intersection(seat_based_workloads))
#         needs_team_size = has_seat_based_category or (
#             has_seat_based_workload and not has_infrastructure_category
#         )
#         if needs_team_size and not (requirements.get("team_size") or requirements.get("quantity")):
#             missing_signals.append("team_size")
#         elif self._needs_purchase_scope_or_quantity(
#             requirements=requirements,
#             resolved_categories=resolved_categories,
#             workloads=workloads,
#             seat_based_categories=seat_based_categories,
#             seat_based_workloads=seat_based_workloads,
#         ):
#             missing_signals.append("purchase_scope_or_quantity")

#         can_rank_without_budget = self._can_rank_without_budget(requirements, resolved_categories, workloads)

#         if requirements.get("budget") is None:
#             missing_signals.append("budget")
#         elif self._needs_budget_scope(
#             requirements,
#             resolved_categories,
#             workloads,
#             seat_based_categories,
#             seat_based_workloads,
#         ):
#             missing_signals.append("budget_scope")

#         if self._needs_application_profile(requirements, workloads):
#             missing_signals.append("application_profile")

#         if not requirements.get("growth_expectation"):
#             missing_signals.append("growth_expectation")

#         if not requirements.get("performance_priority"):
#             missing_signals.append("performance_priority")

#         missing_signals = self._dedupe_preserve_order(missing_signals)

#         field_confidence = self._field_confidence(
#             requirements=requirements,
#             resolved_categories=resolved_categories,
#             has_profile_signal=has_profile_signal,
#             needs_team_size=needs_team_size,
#         )
#         question_candidates = self._question_candidates(
#             missing_signals=missing_signals,
#             field_confidence=field_confidence,
#             categories=categories,
#             resolved_categories=resolved_categories,
#             workloads=workloads,
#             seat_based_workloads=seat_based_workloads,
#             requirements=requirements,
#         )
#         follow_up_questions = [
#             {
#                 "key": item["key"],
#                 "prompt": item["prompt"],
#                 "rationale": item["rationale"],
#                 "impact": item["impact"],
#             }
#             for item in question_candidates
#         ]

#         is_ready = not bool(self._blocking_signals().intersection(missing_signals))
#         if not missing_signals:
#             confidence = "high"
#         elif is_ready:
#             confidence = "medium"
#         else:
#             confidence = "low"

#         decision_confidence_score = self._decision_confidence_score(
#             requirements=requirements,
#             is_ready=is_ready,
#             missing_signals=missing_signals,
#         )
#         decision_confidence_band = self._decision_confidence_band(decision_confidence_score)
#         top_question = follow_up_questions[0] if follow_up_questions else None
#         recommended_question_budget = self._recommended_question_budget(
#             is_ready,
#             decision_confidence_band,
#             question_candidates,
#         )
#         threshold = self.question_impact_threshold()
#         recommended_refinement_question = (
#             top_question["prompt"]
#             if is_ready and top_question and top_question["impact"] >= threshold
#             else None
#         )

#         return {
#             "is_ready": is_ready,
#             "confidence": confidence,
#             "can_rank_without_budget": can_rank_without_budget,
#             "missing_signals": missing_signals,
#             "highest_priority_missing_field": highest_priority_missing_field(missing_signals),
#             "recommended_question_id": top_question["key"] if top_question and recommended_question_budget else None,
#             "next_question": top_question["prompt"] if top_question and recommended_question_budget else None,
#             "follow_up_questions": follow_up_questions,
#             "decision_confidence_score": decision_confidence_score,
#             "decision_confidence_band": decision_confidence_band,
#             "recommended_question_budget": recommended_question_budget,
#             "routing_recommendation": self._routing_recommendation(is_ready, decision_confidence_band),
#             "recommended_refinement_question": recommended_refinement_question,
#             "field_confidence": field_confidence,
#             "question_strategy": self._question_strategy(is_ready, question_candidates),
#             "question_candidates": follow_up_questions[:3],
#         }

#     def should_defer_ranking(self, readiness):
#         missing = set((readiness or {}).get("missing_signals") or [])
#         if "budget" in missing and bool((readiness or {}).get("can_rank_without_budget")):
#             missing.discard("budget")
#         return bool(self._blocking_signals().intersection(missing))

#     def _question_candidates(
#         self,
#         missing_signals,
#         field_confidence,
#         categories,
#         resolved_categories,
#         workloads,
#         seat_based_workloads,
#         requirements,
#     ):
#         candidates = []
#         for field in self._sorted_missing_signals(missing_signals):
#             prompt = self._prompt_for_field(
#                 field=field,
#                 categories=categories,
#                 resolved_categories=resolved_categories,
#                 workloads=workloads,
#                 seat_based_workloads=seat_based_workloads,
#                 requirements=requirements,
#             )
#             rationale = self._rationale_for_field(
#                 field=field,
#                 categories=categories,
#                 workloads=workloads,
#                 seat_based_workloads=seat_based_workloads,
#             )
#             impact = self._question_impact(field, field_confidence)
#             candidates.append(
#                 {
#                     "key": field,
#                     "prompt": prompt,
#                     "rationale": rationale,
#                     "impact": impact,
#                 }
#             )
#         candidates.sort(
#             key=lambda item: (
#                 -float(item.get("impact") or 0.0),
#                 FOLLOW_UP_PRIORITY.index(item["key"]) if item["key"] in FOLLOW_UP_PRIORITY else 999,
#             )
#         )
#         return candidates

#     def _prompt_for_field(
#         self,
#         field,
#         categories,
#         resolved_categories,
#         workloads,
#         seat_based_workloads,
#         requirements,
#     ):
#         field = str(field or "").strip()

#         if field == "category_or_workload":
#             if not resolved_categories and not workloads:
#                 return default_follow_up_prompt("category_or_workload")
#             if workloads and not resolved_categories:
#                 return default_follow_up_prompt("preferred_category")
#             if resolved_categories and not self._has_profile_signal(requirements, workloads):
#                 return default_follow_up_prompt("workload_or_application_profile")
#             return default_follow_up_prompt("category_or_workload")

#         if field == "workload_or_application_profile":
#             return default_follow_up_prompt("workload_or_application_profile")

#         if field == "application_profile":
#             return default_follow_up_prompt("application_profile")

#         if field == "team_size":
#             return self._team_size_prompt(categories, workloads, seat_based_workloads)

#         return default_follow_up_prompt(field)

#     def _rationale_for_field(self, field, categories, workloads, seat_based_workloads):
#         if field == "team_size":
#             return self._team_size_rationale(categories, workloads, seat_based_workloads)
#         return FOLLOW_UP_RATIONALES.get(field) or FOLLOW_UP_RATIONALES["budget"]

#     def _question_impact(self, field, field_confidence):
#         importance = float(FIELD_IMPORTANCE.get(field, 0.4))
#         sensitivity = float(FIELD_SENSITIVITY.get(field, 0.5))
#         confidence = float(field_confidence.get(field, 0.0) or 0.0)
#         uncertainty = max(0.15, 1.0 - confidence)
#         return round(min(importance * sensitivity * uncertainty * 1.25, 1.0), 2)

#     def _field_confidence(self, requirements, resolved_categories, has_profile_signal, needs_team_size):
#         workloads = self._normalized_workloads(requirements)
#         application_signals = requirements.get("application_signals") or []
#         capability_tags = requirements.get("capability_tags") or []

#         return {
#             "preferred_category": 1.0 if resolved_categories else 0.2,
#             "workload_or_application": 1.0 if has_profile_signal else 0.0,
#             "budget": 1.0 if requirements.get("budget") is not None else 0.0,
#             "budget_scope": 1.0 if requirements.get("budget_scope") else 0.0,
#             "purchase_scope_or_quantity": 1.0 if (requirements.get("purchase_scope") or requirements.get("quantity")) else 0.0,
#             "team_size": 1.0 if (requirements.get("team_size") or requirements.get("quantity")) else (0.3 if needs_team_size else 0.0),
#             "application_profile": 1.0 if application_signals else (0.2 if (workloads or capability_tags) else 0.0),
#             "growth_expectation": 1.0 if requirements.get("growth_expectation") else 0.2,
#             "performance_priority": 1.0 if requirements.get("performance_priority") else 0.2,
#         }

#     def _blocking_signals(self):
#         policy = self.config_service.get_clarification_policy() or {}
#         configured = list(policy.get("blocking_signals") or [])
#         if configured:
#             return set(configured)
#         return set(DEFAULT_BLOCKING_SIGNALS)

#     def _routing_recommendation(self, is_ready, confidence_band):
#         if not is_ready:
#             return "clarify_before_recommendation"
#         if confidence_band == "low":
#             return "clarify_before_recommendation"
#         if confidence_band == "medium":
#             return "recommend_with_optional_refinement"
#         return "recommend_now"

#     def _question_strategy(self, is_ready, question_candidates):
#         if not question_candidates:
#             return "no_question_needed"
#         if is_ready:
#             return "ask_top_impact_question_if_helpful"
#         return "ask_top_impact_question"

#     def _sorted_missing_signals(self, missing_signals):
#         ordered = self._dedupe_preserve_order(missing_signals)
#         return sorted(
#             ordered,
#             key=lambda field: FOLLOW_UP_PRIORITY.index(field) if field in FOLLOW_UP_PRIORITY else 999,
#         )

#     def _dedupe_preserve_order(self, values):
#         result = []
#         for value in list(values or []):
#             if value and value not in result:
#                 result.append(value)
#         return result

#     def _normalized_categories(self, requirements):
#         categories = list(requirements.get("preferred_categories") or [])
#         preferred_category = requirements.get("preferred_category")
#         if preferred_category and preferred_category not in categories:
#             categories.insert(0, preferred_category)
#         return self._dedupe_preserve_order(categories)

#     def _normalized_workloads(self, requirements):
#         return self._dedupe_preserve_order(requirements.get("workloads") or [])

#     def _has_profile_signal(self, requirements, workloads):
#         return bool(
#             workloads
#             or requirements.get("application_signals")
#             or requirements.get("requested_ram_gb")
#             or requirements.get("requested_storage_gb")
#             or requirements.get("existing_infrastructure")
#         )

#     def _can_rank_without_budget(self, requirements, resolved_categories, workloads):
#         if requirements.get("budget") is not None:
#             return False

#         category_set = set(resolved_categories or [])
#         workload_set = set(workloads or [])
#         if not category_set and not workload_set:
#             return False

#         high_signal_spec_fields = (
#             "requested_ram_gb",
#             "requested_storage_gb",
#             "minimum_warranty_years",
#             "required_port_count",
#             "required_throughput_mbps",
#             "required_duplex_printing",
#             "required_scanner",
#             "min_print_speed_ppm",
#             "required_printer_type",
#             "required_print_technology",
#             "required_color_output",
#             "min_monthly_duty_cycle_pages",
#             "required_automatic_document_feeder",
#             "required_paper_sizes",
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
#         )
#         explicit_spec_count = 0
#         for field in high_signal_spec_fields:
#             value = requirements.get(field)
#             if value not in (None, "", [], {}, False):
#                 explicit_spec_count += 1

#         has_app_signal = bool(requirements.get("application_signals") or requirements.get("capability_tags"))
#         return explicit_spec_count >= 2 or (explicit_spec_count >= 1 and has_app_signal)

#     def question_impact_threshold(self):
#         threshold = self.config_service.get_clarification_policy().get("question_impact_threshold")
#         if isinstance(threshold, (int, float)):
#             return float(threshold)
#         return DEFAULT_QUESTION_IMPACT_THRESHOLD

#     def _team_size_prompt(self, categories, workloads, seat_based_workloads):
#         category_set = set(categories or [])
#         workload_set = set(workloads or [])
#         if "networking" in category_set:
#             return "How many users, endpoints, or branch devices should this network support?"
#         if "servers" in category_set:
#             return "How many users or workloads should this server environment support?"
#         if workload_set.intersection(seat_based_workloads):
#             return "How many users or seats are in scope for this purchase?"
#         return default_follow_up_prompt("team_size")

#     def _team_size_rationale(self, categories, workloads, seat_based_workloads):
#         category_set = set(categories or [])
#         workload_set = set(workloads or [])
#         if "networking" in category_set:
#             return "Expected user or endpoint load helps size networking recommendations without assuming one device per user."
#         if "servers" in category_set:
#             return "Expected user or workload scale helps size server recommendations without assuming one server per user."
#         if workload_set.intersection(seat_based_workloads):
#             return "Seat count affects quantity assumptions and budget fit for end-user devices."
#         return FOLLOW_UP_RATIONALES["team_size"]

#     def _seat_based_categories(self):
#         return set(self.config_service.get_rules_config().get("seat_based_categories") or [])

#     def _seat_based_workloads(self):
#         rules_config = self.config_service.get_rules_config()
#         seat_based_categories = self._seat_based_categories()
#         workload_targets = rules_config.get("workload_targets") or {}
#         return {
#             workload
#             for workload, profile in workload_targets.items()
#             if set(profile.get("categories") or []).intersection(seat_based_categories)
#             and not set(profile.get("categories") or []).intersection(INFRASTRUCTURE_CATEGORIES)
#         }

#     def _needs_application_profile(self, requirements, workloads):
#         if requirements.get("budget") is not None:
#             return False
#         workload_set = set(workloads or [])
#         if not workload_set.intersection({"software_development", "creative_design", "ai_analytics", "server_infrastructure"}):
#             return False
#         if requirements.get("application_signals"):
#             return False
#         if requirements.get("requested_ram_gb") or requirements.get("requested_storage_gb"):
#             return False
#         capability_tags = set(requirements.get("capability_tags") or [])
#         if capability_tags.intersection(
#             {"gpu_needed", "high_ram", "storage_heavy", "virtualization", "branch_connectivity", "local_compute"}
#         ):
#             return False
#         return True

#     def _needs_budget_scope(self, requirements, resolved_categories, workloads, seat_based_categories, seat_based_workloads):
#         if requirements.get("budget_scope"):
#             return False

#         quantity = int(requirements.get("quantity") or 0)
#         if quantity > 1:
#             return True

#         if requirements.get("purchase_scope") == "team_rollout":
#             return True

#         category_set = set(resolved_categories or [])
#         workload_set = set(workloads or [])
#         has_seat_based_category = bool(category_set.intersection(seat_based_categories))
#         has_seat_based_workload = bool(workload_set.intersection(seat_based_workloads))
#         team_size = int(requirements.get("team_size") or 0)
#         return bool(team_size > 1 and (has_seat_based_category or has_seat_based_workload))

#     def _needs_purchase_scope_or_quantity(
#         self,
#         requirements,
#         resolved_categories,
#         workloads,
#         seat_based_categories,
#         seat_based_workloads,
#     ):
#         if requirements.get("purchase_scope") or requirements.get("quantity"):
#             return False

#         team_size = int(requirements.get("team_size") or 0)
#         if team_size <= 0:
#             return False

#         category_set = set(resolved_categories or [])
#         workload_set = set(workloads or [])
#         has_seat_based_category = bool(category_set.intersection(seat_based_categories))
#         has_seat_based_workload = bool(workload_set.intersection(seat_based_workloads))
#         has_infrastructure_category = bool(category_set.intersection(INFRASTRUCTURE_CATEGORIES))
#         return bool((has_seat_based_category or has_seat_based_workload) and not has_infrastructure_category)

#     def _decision_confidence_score(self, requirements, is_ready, missing_signals):
#         score = 0.0
#         if is_ready:
#             score += 0.45
#         if requirements.get("preferred_categories") or requirements.get("workloads"):
#             score += 0.15
#         if requirements.get("budget") is not None:
#             score += 0.15
#         if requirements.get("team_size") or requirements.get("quantity"):
#             score += 0.1
#         if requirements.get("application_signals"):
#             score += min(len(requirements.get("application_signals") or []) * 0.05, 0.1)
#         if requirements.get("capability_tags"):
#             score += min(len(requirements.get("capability_tags") or []) * 0.03, 0.09)
#         if requirements.get("requested_ram_gb") or requirements.get("requested_storage_gb"):
#             score += 0.08
#         missing_set = set(missing_signals or [])
#         if "workload_or_application_profile" in missing_set:
#             score -= 0.12
#         if "budget_scope" in missing_set:
#             score -= 0.08
#         if "application_profile" in missing_set:
#             score -= 0.08
#         return round(max(min(score, 1.0), 0.0), 2)

#     def _decision_confidence_band(self, score):
#         bands = self.config_service.get_clarification_policy().get("decision_confidence_bands") or {}
#         high_min = float(bands.get("high_min", DEFAULT_DECISION_CONFIDENCE_BANDS["high_min"]))
#         medium_min = float(bands.get("medium_min", DEFAULT_DECISION_CONFIDENCE_BANDS["medium_min"]))
#         if score >= high_min:
#             return "high"
#         if score >= medium_min:
#             return "medium"
#         return "low"

#     def _recommended_question_budget(self, is_ready, confidence_band, question_candidates):
#         top_question = question_candidates[0] if question_candidates else None
#         policy = self.config_service.get_clarification_policy().get("question_budget_policy") or {}
#         threshold = self.question_impact_threshold()
#         if (
#             top_question
#             and policy.get("allow_top_question_when_impact_meets_threshold", True)
#             and top_question["impact"] >= threshold
#         ):
#             return 1
#         if (
#             not is_ready
#             and confidence_band == "low"
#             and question_candidates
#             and policy.get("allow_when_not_ready_low_confidence", True)
#         ):
#             return 1
#         if (
#             is_ready
#             and confidence_band == "medium"
#             and top_question
#             and top_question["impact"] >= threshold
#             and policy.get("allow_optional_refinement_when_ready_medium_confidence", True)
#         ):
#             return 1
#         return 0





from .config_service import ProcurementConfigService
from ...catalog.services.normalization import normalize_category

INFRASTRUCTURE_CATEGORIES = {"servers", "networking"}
DEFAULT_BLOCKING_SIGNALS = {
    "preferred_category",
    "category_or_workload",
    "budget",
}
FOLLOW_UP_PRIORITY = [
    "preferred_category",
    "category_or_workload",
    "budget",
    "shared_budget_allocation",
    "workload_or_application_profile",
    "application_profile",
    "team_size",
    "budget_scope",
    "purchase_scope_or_quantity",
    "growth_expectation",
    "performance_priority",
]
FOLLOW_UP_PROMPTS = {
    "preferred_category": "Are you mainly trying to buy laptops, desktops, servers, networking equipment, printers, or accessories?",
    "category_or_workload": "What are you mainly trying to buy first: laptops, desktops, servers, networking, printers, accessories, or a mix?",
    "workload_or_application_profile": (
        "What kind of work will these systems support day to day, and which apps or tools matter most? "
        "You can mention more than one, like Excel, browser tools, Docker, Photoshop, Premiere, or VMware."
    ),
    "team_size": "How many users, seats, or endpoints are in scope for this purchase?",
    "budget": "What budget should I optimize for?",
    "shared_budget_allocation": "Is this one shared total budget for everything together, or do you want to split it between the categories?",
    "budget_scope": "Should I treat that budget as per device or as the total project budget?",
    "purchase_scope_or_quantity": (
        "Is this for a single device or a wider team rollout, and if it is a rollout, roughly how many units are in scope?"
    ),
    "application_profile": (
        "Which apps or tools matter most here? You can mention more than one, like Excel, browser tools, "
        "Docker, Photoshop, Premiere, or VMware."
    ),
    "growth_expectation": "Should the recommendation plan for a steady team, moderate growth, or rapid expansion?",
    "performance_priority": "Should I optimize more for cost, a balanced option, or stronger performance?",
}
FOLLOW_UP_RATIONALES = {
    "preferred_category": (
        "An explicit category choice is needed before ranking when the current brief says the device type is still undecided."
    ),
    "category_or_workload": (
        "The engine needs at least one product or workload signal before ranking catalog items."
    ),
    "workload_or_application_profile": (
        "A device category and budget are not enough on their own. The engine still needs the day-to-day work pattern or app mix."
    ),
    "team_size": "Expected usage scale improves recommendation quality and capacity planning.",
    "budget": "Budget is required to rank practical recommendations and avoid unrealistic options.",
    "shared_budget_allocation": "A shared multi-category budget should be split or prioritized explicitly before the grouped result can be treated as fully budget-valid.",
    "budget_scope": "Budget scope changes whether the engine evaluates a unit price or the total deployment cost.",
    "purchase_scope_or_quantity": (
        "Seat-based device requests need rollout scope or unit quantity before the engine can treat the result as a firm recommendation."
    ),
    "application_profile": (
        "The app or tool mix changes sizing more than a broad workload label, especially for developer, creative, AI, and infrastructure briefs."
    ),
    "growth_expectation": (
        "Growth expectation affects how much performance and capacity headroom the engine should reserve."
    ),
    "performance_priority": (
        "Performance priority helps separate value-oriented options from premium recommendations."
    ),
}
FIELD_IMPORTANCE = {
    "preferred_category": 1.0,
    "category_or_workload": 1.0,
    "workload_or_application_profile": 1.0,
    "application_profile": 0.6,
    "budget": 0.9,
    "shared_budget_allocation": 0.95,
    "budget_scope": 0.9,
    "purchase_scope_or_quantity": 0.9,
    "team_size": 0.7,
    "growth_expectation": 0.4,
    "performance_priority": 0.3,
}
FIELD_SENSITIVITY = {
    "preferred_category": 1.0,
    "category_or_workload": 1.0,
    "workload_or_application_profile": 1.0,
    "budget": 1.0,
    "shared_budget_allocation": 1.0,
    "budget_scope": 0.9,
    "purchase_scope_or_quantity": 1.0,
    "team_size": 0.8,
    "application_profile": 0.8,
    "growth_expectation": 0.5,
    "performance_priority": 0.5,
}
DEFAULT_QUESTION_IMPACT_THRESHOLD = 0.35
DEFAULT_DECISION_CONFIDENCE_BANDS = {
    "high_min": 0.8,
    "medium_min": 0.55,
}


def highest_priority_missing_field(missing_fields):
    missing_list = list(missing_fields or [])
    missing_set = set(missing_list)
    for field in FOLLOW_UP_PRIORITY:
        if field in missing_set:
            return field
    return missing_list[0] if missing_list else None


def default_follow_up_prompt(field):
    return FOLLOW_UP_PROMPTS.get(field) or FOLLOW_UP_PROMPTS["budget"]


class ProcurementClarificationService:
    def __init__(self, config_service=None):
        self.config_service = config_service or ProcurementConfigService()

    def assess(self, requirements):
        requirements = requirements or {}
        missing_signals = []
        seat_based_categories = self._seat_based_categories()
        seat_based_workloads = self._seat_based_workloads()

        categories = self._normalized_categories(requirements)
        resolved_categories = [category for category in categories if category and category != "not_sure"]
        intent_groups = [group for group in list(requirements.get("intent_groups") or []) if isinstance(group, dict)]
        explicit_group_categories = [
            normalize_category(group.get("preferred_category") or group.get("category"))
            for group in intent_groups
            if normalize_category(group.get("preferred_category") or group.get("category"))
        ]
        explicit_group_categories = self._dedupe_preserve_order(explicit_group_categories)
        has_explicit_multi_category = len(self._dedupe_preserve_order(resolved_categories + explicit_group_categories)) >= 2
        has_ambiguous_category = any(category == "not_sure" for category in categories) and not has_explicit_multi_category
        workloads = self._normalized_workloads(requirements)
        has_profile_signal = bool(
            workloads
            or requirements.get("application_signals")
            or requirements.get("requested_ram_gb")
            or requirements.get("requested_storage_gb")
            or requirements.get("existing_infrastructure")
        )

        if has_ambiguous_category:
            missing_signals.append("preferred_category")

        if not resolved_categories and not has_profile_signal:
            missing_signals.append("category_or_workload")
        elif not resolved_categories and len(set(workloads or [])) > 1:
            missing_signals.append("preferred_category")

        has_seat_based_category = bool(set(resolved_categories).intersection(seat_based_categories))
        has_infrastructure_category = bool(set(resolved_categories).intersection(INFRASTRUCTURE_CATEGORIES))
        has_seat_based_workload = bool(set(workloads).intersection(seat_based_workloads))
        needs_team_size = False

        can_rank_without_budget = self._can_rank_without_budget(requirements, resolved_categories, workloads)

        if requirements.get("budget") is None:
            missing_signals.append("budget")

        missing_signals = self._dedupe_preserve_order(missing_signals)

        field_confidence = self._field_confidence(
            requirements=requirements,
            resolved_categories=resolved_categories,
            has_profile_signal=has_profile_signal,
            needs_team_size=needs_team_size,
        )
        question_candidates = self._question_candidates(
            missing_signals=missing_signals,
            field_confidence=field_confidence,
            categories=categories,
            resolved_categories=resolved_categories,
            workloads=workloads,
            seat_based_workloads=seat_based_workloads,
            requirements=requirements,
        )
        follow_up_questions = [
            {
                "key": item["key"],
                "prompt": item["prompt"],
                "rationale": item["rationale"],
                "impact": item["impact"],
            }
            for item in question_candidates
        ]

        is_ready = not bool(self._blocking_signals().intersection(missing_signals))
        if not missing_signals:
            confidence = "high"
        elif is_ready:
            confidence = "medium"
        else:
            confidence = "low"

        decision_confidence_score = self._decision_confidence_score(
            requirements=requirements,
            is_ready=is_ready,
            missing_signals=missing_signals,
        )
        decision_confidence_band = self._decision_confidence_band(decision_confidence_score)
        top_question = follow_up_questions[0] if follow_up_questions else None
        recommended_question_budget = self._recommended_question_budget(
            is_ready,
            decision_confidence_band,
            question_candidates,
        )
        threshold = self.question_impact_threshold()
        recommended_refinement_question = (
            top_question["prompt"]
            if is_ready and top_question and top_question["impact"] >= threshold
            else None
        )

        return {
            "is_ready": is_ready,
            "confidence": confidence,
            "can_rank_without_budget": can_rank_without_budget,
            "missing_signals": missing_signals,
            "highest_priority_missing_field": highest_priority_missing_field(missing_signals),
            "recommended_question_id": top_question["key"] if top_question and recommended_question_budget else None,
            "next_question": top_question["prompt"] if top_question and recommended_question_budget else None,
            "follow_up_questions": follow_up_questions,
            "decision_confidence_score": decision_confidence_score,
            "decision_confidence_band": decision_confidence_band,
            "recommended_question_budget": recommended_question_budget,
            "routing_recommendation": self._routing_recommendation(is_ready, decision_confidence_band),
            "recommended_refinement_question": recommended_refinement_question,
            "field_confidence": field_confidence,
            "question_strategy": self._question_strategy(is_ready, question_candidates),
            "question_candidates": follow_up_questions[:3],
        }

    def should_defer_ranking(self, readiness):
        missing = set((readiness or {}).get("missing_signals") or [])
        if "budget" in missing and bool((readiness or {}).get("can_rank_without_budget")):
            missing.discard("budget")
        return bool(self._blocking_signals().intersection(missing))

    def _question_candidates(
        self,
        missing_signals,
        field_confidence,
        categories,
        resolved_categories,
        workloads,
        seat_based_workloads,
        requirements,
    ):
        candidates = []
        for field in self._sorted_missing_signals(missing_signals):
            prompt = self._prompt_for_field(
                field=field,
                categories=categories,
                resolved_categories=resolved_categories,
                workloads=workloads,
                seat_based_workloads=seat_based_workloads,
                requirements=requirements,
            )
            rationale = self._rationale_for_field(
                field=field,
                categories=categories,
                workloads=workloads,
                seat_based_workloads=seat_based_workloads,
            )
            impact = self._question_impact(field, field_confidence)
            candidates.append(
                {
                    "key": field,
                    "prompt": prompt,
                    "rationale": rationale,
                    "impact": impact,
                }
            )
        candidates.sort(
            key=lambda item: (
                -float(item.get("impact") or 0.0),
                FOLLOW_UP_PRIORITY.index(item["key"]) if item["key"] in FOLLOW_UP_PRIORITY else 999,
            )
        )
        return candidates

    def _prompt_for_field(
        self,
        field,
        categories,
        resolved_categories,
        workloads,
        seat_based_workloads,
        requirements,
    ):
        field = str(field or "").strip()

        if field == "category_or_workload":
            if not resolved_categories and not workloads:
                return default_follow_up_prompt("category_or_workload")
            if workloads and not resolved_categories:
                return default_follow_up_prompt("preferred_category")
            if resolved_categories and not self._has_profile_signal(requirements, workloads):
                return default_follow_up_prompt("workload_or_application_profile")
            return default_follow_up_prompt("category_or_workload")

        if field == "workload_or_application_profile":
            return default_follow_up_prompt("workload_or_application_profile")

        if field == "application_profile":
            return default_follow_up_prompt("application_profile")

        if field == "team_size":
            return self._team_size_prompt(categories, workloads, seat_based_workloads)

        return default_follow_up_prompt(field)

    def _rationale_for_field(self, field, categories, workloads, seat_based_workloads):
        if field == "team_size":
            return self._team_size_rationale(categories, workloads, seat_based_workloads)
        return FOLLOW_UP_RATIONALES.get(field) or FOLLOW_UP_RATIONALES["budget"]

    def _question_impact(self, field, field_confidence):
        importance = float(FIELD_IMPORTANCE.get(field, 0.4))
        sensitivity = float(FIELD_SENSITIVITY.get(field, 0.5))
        confidence = float(field_confidence.get(field, 0.0) or 0.0)
        uncertainty = max(0.15, 1.0 - confidence)
        return round(min(importance * sensitivity * uncertainty * 1.25, 1.0), 2)

    def _field_confidence(self, requirements, resolved_categories, has_profile_signal, needs_team_size):
        workloads = self._normalized_workloads(requirements)
        application_signals = requirements.get("application_signals") or []
        capability_tags = requirements.get("capability_tags") or []

        return {
            "preferred_category": 1.0 if resolved_categories else 0.2,
            "workload_or_application": 1.0 if has_profile_signal else 0.0,
            "budget": 1.0 if requirements.get("budget") is not None else 0.0,
            "budget_scope": 1.0 if requirements.get("budget_scope") else 0.0,
            "purchase_scope_or_quantity": 1.0 if (requirements.get("purchase_scope") or requirements.get("quantity")) else 0.0,
            "team_size": 1.0 if (requirements.get("team_size") or requirements.get("quantity")) else 0.0,
            "application_profile": 1.0 if application_signals else (0.2 if (workloads or capability_tags) else 0.0),
            "growth_expectation": 1.0 if requirements.get("growth_expectation") else 0.0,
            "performance_priority": 1.0 if requirements.get("performance_priority") else 0.0,
        }

    def _blocking_signals(self):
        policy = self.config_service.get_clarification_policy() or {}
        configured = list(
            policy.get("ranking_blocking_signals")
            or policy.get("blocking_signals")
            or []
        )
        if configured:
            return set(configured)
        return set(DEFAULT_BLOCKING_SIGNALS)

    def _routing_recommendation(self, is_ready, confidence_band):
        if not is_ready:
            return "clarify_before_recommendation"
        if confidence_band == "low":
            return "clarify_before_recommendation"
        if confidence_band == "medium":
            return "recommend_with_optional_refinement"
        return "recommend_now"

    def _question_strategy(self, is_ready, question_candidates):
        if not question_candidates:
            return "no_question_needed"
        if is_ready:
            return "ask_top_impact_question_if_helpful"
        return "ask_top_impact_question"

    def _sorted_missing_signals(self, missing_signals):
        ordered = self._dedupe_preserve_order(missing_signals)
        return sorted(
            ordered,
            key=lambda field: FOLLOW_UP_PRIORITY.index(field) if field in FOLLOW_UP_PRIORITY else 999,
        )

    def _dedupe_preserve_order(self, values):
        result = []
        for value in list(values or []):
            if value and value not in result:
                result.append(value)
        return result

    def _normalized_categories(self, requirements):
        categories = list(requirements.get("preferred_categories") or [])
        preferred_category = requirements.get("preferred_category")
        if preferred_category and preferred_category not in categories:
            categories.insert(0, preferred_category)
        return self._dedupe_preserve_order(categories)

    def _normalized_workloads(self, requirements):
        return self._dedupe_preserve_order(requirements.get("workloads") or [])

    def _has_profile_signal(self, requirements, workloads):
        return bool(
            workloads
            or requirements.get("application_signals")
            or requirements.get("requested_ram_gb")
            or requirements.get("requested_storage_gb")
            or requirements.get("existing_infrastructure")
        )

    def _can_rank_without_budget(self, requirements, resolved_categories, workloads):
        if requirements.get("budget") is not None:
            return False

        category_set = set(resolved_categories or [])
        workload_set = set(workloads or [])
        if not category_set and not workload_set:
            return False

        high_signal_spec_fields = (
            "requested_ram_gb",
            "requested_storage_gb",
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
        )
        explicit_spec_count = 0
        for field in high_signal_spec_fields:
            value = requirements.get(field)
            if value not in (None, "", [], {}, False):
                explicit_spec_count += 1

        has_app_signal = bool(requirements.get("application_signals") or requirements.get("capability_tags"))
        return explicit_spec_count >= 2 or (explicit_spec_count >= 1 and has_app_signal)

    def question_impact_threshold(self):
        threshold = self.config_service.get_clarification_policy().get("question_impact_threshold")
        if isinstance(threshold, (int, float)):
            return float(threshold)
        return DEFAULT_QUESTION_IMPACT_THRESHOLD

    def _team_size_prompt(self, categories, workloads, seat_based_workloads):
        category_set = set(categories or [])
        workload_set = set(workloads or [])
        if "networking" in category_set:
            return "How many users, endpoints, or branch devices should this network support?"
        if "servers" in category_set:
            return "How many users or workloads should this server environment support?"
        if workload_set.intersection(seat_based_workloads):
            return "How many users or seats are in scope for this purchase?"
        return default_follow_up_prompt("team_size")

    def _team_size_rationale(self, categories, workloads, seat_based_workloads):
        category_set = set(categories or [])
        workload_set = set(workloads or [])
        if "networking" in category_set:
            return "Expected user or endpoint load helps size networking recommendations without assuming one device per user."
        if "servers" in category_set:
            return "Expected user or workload scale helps size server recommendations without assuming one server per user."
        if workload_set.intersection(seat_based_workloads):
            return "Seat count affects quantity assumptions and budget fit for end-user devices."
        return FOLLOW_UP_RATIONALES["team_size"]

    def _seat_based_categories(self):
        return set(self.config_service.get_rules_config().get("seat_based_categories") or [])

    def _seat_based_workloads(self):
        rules_config = self.config_service.get_rules_config()
        seat_based_categories = self._seat_based_categories()
        workload_targets = rules_config.get("workload_targets") or {}
        return {
            workload
            for workload, profile in workload_targets.items()
            if set(profile.get("categories") or []).intersection(seat_based_categories)
            and not set(profile.get("categories") or []).intersection(INFRASTRUCTURE_CATEGORIES)
        }

    def _needs_application_profile(self, requirements, workloads):
        workload_set = set(workloads or [])
        if not workload_set.intersection({"software_development", "creative_design", "ai_analytics", "server_infrastructure"}):
            return False
        if requirements.get("application_signals"):
            return False
        if requirements.get("requested_ram_gb") or requirements.get("requested_storage_gb"):
            return False
        capability_tags = set(requirements.get("capability_tags") or [])
        if capability_tags.intersection(
            {"gpu_needed", "high_ram", "storage_heavy", "virtualization", "branch_connectivity", "local_compute"}
        ):
            return False
        return True

    def _needs_budget_scope(self, requirements, resolved_categories, workloads, seat_based_categories, seat_based_workloads):
        if requirements.get("budget_scope"):
            return False

        quantity = int(requirements.get("quantity") or 0)
        if quantity > 1:
            return True

        if requirements.get("purchase_scope") == "team_rollout":
            return True

        category_set = set(resolved_categories or [])
        workload_set = set(workloads or [])
        has_seat_based_category = bool(category_set.intersection(seat_based_categories))
        has_seat_based_workload = bool(workload_set.intersection(seat_based_workloads))
        team_size = int(requirements.get("team_size") or 0)
        return bool(team_size > 1 and (has_seat_based_category or has_seat_based_workload))

    def _needs_purchase_scope_or_quantity(
        self,
        requirements,
        resolved_categories,
        workloads,
        seat_based_categories,
        seat_based_workloads,
    ):
        if requirements.get("purchase_scope") or requirements.get("quantity"):
            return False

        team_size = int(requirements.get("team_size") or 0)
        if team_size <= 0:
            return False

        category_set = set(resolved_categories or [])
        workload_set = set(workloads or [])
        has_seat_based_category = bool(category_set.intersection(seat_based_categories))
        has_seat_based_workload = bool(workload_set.intersection(seat_based_workloads))
        has_infrastructure_category = bool(category_set.intersection(INFRASTRUCTURE_CATEGORIES))
        return bool((has_seat_based_category or has_seat_based_workload) and not has_infrastructure_category)

    def _decision_confidence_score(self, requirements, is_ready, missing_signals):
        score = 0.0
        if is_ready:
            score += 0.45
        if requirements.get("preferred_categories") or requirements.get("workloads"):
            score += 0.15
        if requirements.get("budget") is not None:
            score += 0.15
        if requirements.get("team_size") or requirements.get("quantity"):
            score += 0.1
        if requirements.get("application_signals"):
            score += min(len(requirements.get("application_signals") or []) * 0.05, 0.1)
        if requirements.get("capability_tags"):
            score += min(len(requirements.get("capability_tags") or []) * 0.03, 0.09)
        if requirements.get("requested_ram_gb") or requirements.get("requested_storage_gb"):
            score += 0.08
        missing_set = set(missing_signals or [])
        if "workload_or_application_profile" in missing_set:
            score -= 0.12
        if "budget_scope" in missing_set:
            score -= 0.08
        if "application_profile" in missing_set:
            score -= 0.08
        return round(max(min(score, 1.0), 0.0), 2)

    def _decision_confidence_band(self, score):
        bands = self.config_service.get_clarification_policy().get("decision_confidence_bands") or {}
        high_min = float(bands.get("high_min", DEFAULT_DECISION_CONFIDENCE_BANDS["high_min"]))
        medium_min = float(bands.get("medium_min", DEFAULT_DECISION_CONFIDENCE_BANDS["medium_min"]))
        if score >= high_min:
            return "high"
        if score >= medium_min:
            return "medium"
        return "low"

    def _recommended_question_budget(self, is_ready, confidence_band, question_candidates):
        top_question = question_candidates[0] if question_candidates else None
        policy = self.config_service.get_clarification_policy().get("question_budget_policy") or {}
        threshold = self.question_impact_threshold()
        if (
            top_question
            and policy.get("allow_top_question_when_impact_meets_threshold", True)
            and top_question["impact"] >= threshold
        ):
            return 1
        if (
            not is_ready
            and confidence_band == "low"
            and question_candidates
            and policy.get("allow_when_not_ready_low_confidence", True)
        ):
            return 1
        if (
            is_ready
            and confidence_band == "medium"
            and top_question
            and top_question["impact"] >= threshold
            and policy.get("allow_optional_refinement_when_ready_medium_confidence", True)
        ):
            return 1
        return 0

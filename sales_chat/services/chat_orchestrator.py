
#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################


# import re
# from copy import deepcopy
# from datetime import datetime, timezone
# from time import perf_counter
# from uuid import uuid4

# from ...catalog.services.normalization import (
#     get_procurement_normalization_terms,
#     normalize_budget_scope,
#     normalize_category,
#     normalize_categories,
#     normalize_growth_expectation,
#     normalize_workloads,
#     parse_money_value,
#     parse_team_size,
# )
# from ...procurement.services.clarification import default_follow_up_prompt
# from ...procurement.services.input_normalization import normalize_purchase_scope
# from ...procurement.services.signal_service import ProcurementSignalService
# from .ui_guidance import build_narrowing_guidance


# class ChatOrchestrator:
#     GREETING_TOKENS = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}
#     ACK_TOKENS = {"ok", "okay", "sure", "fine", "got it", "understood", "thanks", "thank you"}
#     ROUTER_CONFIDENCE_THRESHOLD = 0.78
#     PERFORMANCE_PRIORITY_MAP = {
#         "cost": {"cost", "cheapest", "budget", "value"},
#         "balanced": {"balanced", "balance", "normal", "standard"},
#         "performance": {"performance", "high performance", "fastest", "premium", "power"},
#     }
#     WORKLOAD_LABELS = {
#         "software_development": "software development",
#         "creative_design": "design work",
#         "office_productivity": "office productivity",
#         "video_editing": "video editing",
#         "data_analysis": "data analysis",
#         "ai_ml": "AI or ML workloads",
#         "ai_analytics": "AI or analytics workloads",
#         "server_infrastructure": "server infrastructure",
#     }
#     APPLICATION_SIGNAL_LABELS = {
#         "developer_toolchain": "developer tools",
#         "design_suite": "design tools",
#         "video_postproduction": "video editing",
#         "cad_workstation": "CAD work",
#         "ml_toolchain": "AI or ML work",
#         "virtualization_stack": "virtualization",
#         "branch_networking": "branch networking",
#         "business_apps": "business apps",
#         "desk_peripherals": "desk accessories",
#         "gaming_interactive": "gaming-heavy use",
#     }
#     OUT_OF_SCOPE_PATTERNS = {
#         "sing",
#         "song",
#         "joke",
#         "poem",
#         "story",
#         "weather",
#         "horoscope",
#         "translate",
#         "summarize this article",
#         "set a timer",
#         "movie",
#         "movies",
#         "weed",
#     }
#     PROCUREMENT_SCENARIO_TERMS = {
#         "opening",
#         "startup",
#         "start up",
#         "establishing",
#         "setup",
#         "set up",
#         "office",
#         "branch",
#         "clinic",
#         "hospital",
#         "warehouse",
#         "school",
#         "store",
#         "restaurant",
#     }
#     PROCUREMENT_FOLLOWUP_TERMS = {
#         "what about",
#         "instead",
#         "change to",
#         "switch to",
#         "different brand",
#         "amd",
#         "intel",
#         "ryzen",
#         "nvidia",
#         "hp",
#         "dell",
#         "lenovo",
#         "asus",
#         "acer",
#         "apple",
#         "microsoft",
#         "logitech",
#         "cisco",
#         "fortinet",
#         "juniper",
#         "canon",
#         "epson",
#         "brother",
#         "netgear",
#         "tp-link",
#     }
#     PROCUREMENT_TERMS = {
#         "buy",
#         "purchase",
#         "need",
#         "recommend",
#         "budget",
#         "price",
#         "quote",
#         "laptop",
#         "laptops",
#         "desktop",
#         "desktops",
#         "server",
#         "servers",
#         "network",
#         "networking",
#         "printer",
#         "printers",
#         "accessories",
#         "keyboard",
#         "mouse",
#         "headset",
#         "headsets",
#         "monitor",
#         "monitors",
#         "dock",
#         "webcam",
#         "ram",
#         "storage",
#         "gpu",
#         "cpu",
#         "users",
#         "seats",
#         "team",
#     }
#     RECOMMENDATION_RECALL_PATTERNS = {
#         "what did you recommend",
#         "what was the recommendation",
#         "what was the shortlist",
#         "remind me what you recommended",
#         "recommend again",
#         "shortlist again",
#         "what did you suggest",
#     }
#     RECOMMENDATION_REFINEMENT_TERMS = {
#         "cheaper",
#         "more affordable",
#         "less expensive",
#         "lower budget",
#         "cut the budget",
#         "make it cheaper",
#         "reduce the budget",
#     }
#     RECOMMENDATION_REFERENCE_TERMS = {
#         "recommendation",
#         "recommended",
#         "shortlist",
#         "option",
#         "options",
#         "suggested",
#         "cheaper",
#         "refine",
#         "change",
#         "adjust",
#         "compare",
#         "again",
#     }

#     def __init__(
#         self,
#         chat_session_service,
#         planner_service,
#         requirement_state_manager,
#         requirement_guard_service,
#         recommendation_service,
#         response_contract_adapter,
#         background_dispatcher,
#         include_llm_stats=True,
#         signal_service=None,
#     ):
#         self.chat_session_service = chat_session_service
#         self.planner_service = planner_service
#         self.requirement_state_manager = requirement_state_manager
#         self.requirement_guard_service = requirement_guard_service
#         self.recommendation_service = recommendation_service
#         self.response_contract_adapter = response_contract_adapter
#         self.background_dispatcher = background_dispatcher
#         self.include_llm_stats = bool(include_llm_stats)
#         self.signal_service = signal_service or ProcurementSignalService()

#     def start_session(self, transport_session_id, channel="websocket", store_id=""):
#         turn_metrics = self._new_turn_metrics(
#             transport_session_id=transport_session_id,
#             turn_type="welcome",
#         )
#         session_started_at = perf_counter()
#         session = self.chat_session_service.get_or_create_session(
#             transport_session_id=transport_session_id,
#             channel=channel,
#             store_id=store_id,
#         )
#         self._mark_stage(turn_metrics, "session_load_ms", session_started_at)
#         turn_metrics["conversation_id"] = session.conversation_id

#         state_started_at = perf_counter()
#         state = self.chat_session_service.load_state(session.conversation_id)
#         self._mark_stage(turn_metrics, "session_load_ms", state_started_at)
#         self._apply_cache_counters(turn_metrics)

#         guard_started_at = perf_counter()
#         readiness = self.requirement_guard_service.validate((state or {}).get("requirements") or {})
#         self._mark_stage(turn_metrics, "guard_validate_ms", guard_started_at)

#         message = (
#             "Welcome to Tech Pay's SMB procurement advisor.\n"
#             "Tell me what you need to buy, who it is for, and your budget.\n"
#             "Example: We need 15 laptops for software developers under 6500 each."
#         )
#         response_started_at = perf_counter()
#         payload = self.response_contract_adapter.build_question_payload(
#             response=message,
#             next_question=message,
#             requirements=dict((state or {}).get("requirements") or {}),
#             readiness=dict(readiness.get("readiness") or {}),
#             extracted_schema=dict((state or {}).get("requirements") or {}),
#             ui_guidance=[],
#             meta={"conversation_id": session.conversation_id},
#             llm_stats=self._build_llm_stats(),
#             response_mode="respond",
#         )
#         self._mark_stage(turn_metrics, "response_contract_ms", response_started_at)

#         persist_started_at = perf_counter()
#         self.chat_session_service.append_message(
#             session.conversation_id,
#             role="assistant",
#             content=payload["response"],
#             meta={"response_mode": "respond"},
#             message_type="question",
#         )
#         self._mark_stage(turn_metrics, "db_persist_ms", persist_started_at)

#         payload = self._attach_turn_metrics(payload, turn_metrics, response_type="question")
#         self._append_runtime_log(payload)
#         return session, payload

#     def handle_turn(self, transport_session_id, user_message):
#         turn_metrics = self._new_turn_metrics(
#             transport_session_id=transport_session_id,
#             turn_type="chat_turn",
#         )
#         session_started_at = perf_counter()
#         session = self.chat_session_service.get_or_create_session(transport_session_id=transport_session_id)
#         self._mark_stage(turn_metrics, "session_load_ms", session_started_at)
#         turn_metrics["conversation_id"] = session.conversation_id

#         state_started_at = perf_counter()
#         state = self.chat_session_service.load_state(session.conversation_id)
#         planner_recent_messages = self.chat_session_service.planner_recent_messages(session.conversation_id)
#         self._mark_stage(turn_metrics, "session_load_ms", state_started_at)
#         self._apply_cache_counters(turn_metrics)

#         persist_started_at = perf_counter()
#         self.chat_session_service.append_message(
#             session.conversation_id,
#             role="user",
#             content=user_message,
#             message_type="info",
#         )
#         self._mark_stage(turn_metrics, "db_persist_ms", persist_started_at)

#         current_requirements = dict((state or {}).get("requirements") or {})
#         guard_started_at = perf_counter()
#         readiness_result = self.requirement_guard_service.validate(current_requirements)
#         self._mark_stage(turn_metrics, "guard_validate_ms", guard_started_at)

#         recommendation_followup = self._try_recommendation_followup_turn(
#             user_message=user_message,
#             state=state,
#             readiness_result=readiness_result,
#         )
#         if recommendation_followup is not None:
#             updated_state = recommendation_followup["state"]
#             validated = recommendation_followup["validated"]
#             planner_output = recommendation_followup["planner_output"]

#             persist_started_at = perf_counter()
#             self.chat_session_service.save_state(session.conversation_id, updated_state)
#             self._mark_stage(turn_metrics, "db_persist_ms", persist_started_at)

#             if self._should_trigger_recommendation(planner_output, validated):
#                 return self._build_recommendation_response(
#                     session=session,
#                     updated_state=updated_state,
#                     validated=validated,
#                     turn_metrics=turn_metrics,
#                 )

#             return self._build_non_recommendation_response(
#                 session=session,
#                 updated_state=updated_state,
#                 validated=validated,
#                 planner_output=planner_output,
#                 turn_metrics=turn_metrics,
#             )

#         shortcut_turn = self._try_shortcut_turn(
#             user_message=user_message,
#             state=state,
#             readiness_result=readiness_result,
#             planner_recent_messages=planner_recent_messages,
#         )
#         if shortcut_turn is not None:
#             updated_state = shortcut_turn["state"]
#             validated = shortcut_turn["validated"]
#             planner_output = shortcut_turn["planner_output"]

#             persist_started_at = perf_counter()
#             self.chat_session_service.save_state(session.conversation_id, updated_state)
#             self._mark_stage(turn_metrics, "db_persist_ms", persist_started_at)

#             if self._should_trigger_recommendation(planner_output, validated):
#                 return self._build_recommendation_response(
#                     session=session,
#                     updated_state=updated_state,
#                     validated=validated,
#                     turn_metrics=turn_metrics,
#                 )

#             return self._build_non_recommendation_response(
#                 session=session,
#                 updated_state=updated_state,
#                 validated=validated,
#                 planner_output=planner_output,
#                 turn_metrics=turn_metrics,
#             )

#         planner_prepare_started_at = perf_counter()
#         extracted_turn_patch = {}
#         planner_state = deepcopy(state or {})
#         if not self._is_non_procurement_turn(user_message, state):
#             extracted_turn_patch = self._build_requirement_patch_from_text(user_message, state)
#             if extracted_turn_patch:
#                 merged_for_planner = self.requirement_state_manager.merge_requirement_patch(
#                     dict(planner_state.get("requirements") or {}),
#                     extracted_turn_patch,
#                     source="turn_extraction_preview",
#                 )
#                 planner_state["requirements"] = merged_for_planner
#         planner_inputs = {
#             "user_message": user_message,
#             "state": self._planner_state(planner_state),
#             "recent_messages": planner_recent_messages,
#             "readiness": dict(readiness_result.get("readiness") or {}),
#             "current_recommendations": self._current_recommendations(state),
#         }
#         self._mark_stage(turn_metrics, "planner_prepare_ms", planner_prepare_started_at)

#         planner_started_at = perf_counter()
#         planner_output = self.planner_service.plan_turn(**planner_inputs)
#         self._mark_stage(turn_metrics, "planner_total_ms", planner_started_at)
#         self._apply_planner_metadata(turn_metrics)

#         planner_output = self._apply_planner_safety_overrides(
#             user_message=user_message,
#             state=state,
#             planner_output=planner_output,
#             readiness_result=readiness_result,
#         )

#         planner_output = self._augment_planner_output_with_extracted_patch(
#             user_message=user_message,
#             state=state,
#             planner_output=planner_output,
#             extracted_patch=extracted_turn_patch,
#         )

#         merge_started_at = perf_counter()
#         updated_state = self.requirement_state_manager.apply_patch(state, planner_output)
#         self._mark_stage(turn_metrics, "state_merge_ms", merge_started_at)

#         updated_requirements = dict(updated_state.get("requirements") or {})
#         guard_started_at = perf_counter()
#         validated = self.requirement_guard_service.validate(updated_requirements)
#         self._mark_stage(turn_metrics, "guard_validate_ms", guard_started_at)
#         updated_state["requirements"] = dict(validated.get("requirements") or updated_requirements)
#         planner_output["question_target_field"] = self._resolve_question_target_field(validated, planner_output)
#         should_trigger_recommendation = self._should_trigger_recommendation(planner_output, validated)
#         if not should_trigger_recommendation:
#             planner_output = self._normalize_non_recommendation_planner_output(
#                 planner_output=planner_output,
#                 validated=validated,
#                 updated_state=updated_state,
#             )
#         updated_state = self._update_conversation_meta(updated_state, planner_output, validated)

#         persist_started_at = perf_counter()
#         self.chat_session_service.save_state(session.conversation_id, updated_state)
#         self._mark_stage(turn_metrics, "db_persist_ms", persist_started_at)

#         if should_trigger_recommendation:
#             return self._build_recommendation_response(
#                 session=session,
#                 updated_state=updated_state,
#                 validated=validated,
#                 turn_metrics=turn_metrics,
#             )

#         return self._build_non_recommendation_response(
#             session=session,
#             updated_state=updated_state,
#             validated=validated,
#             planner_output=planner_output,
#             turn_metrics=turn_metrics,
#         )

#     def reset_session(self, transport_session_id):
#         session = self.chat_session_service.get_or_create_session(transport_session_id=transport_session_id)
#         self.chat_session_service.reset_session(session.conversation_id)
#         _, payload = self.start_session(transport_session_id, channel=session.channel, store_id=session.store_id)
#         return payload

#     def close_session(self, transport_session_id):
#         session = self.chat_session_service.get_or_create_session(transport_session_id=transport_session_id)
#         self.chat_session_service.close_session(session.conversation_id)

#     def _current_recommendations(self, state):
#         memory = self._recommendation_memory(state)
#         return list(memory.get("recommendations") or [])

#     def _recommendation_memory(self, state):
#         return dict((state or {}).get("recommendation_memory") or {})

#     def _planner_recommendation_memory(self, state):
#         memory = self._recommendation_memory(state)
#         if not memory:
#             return {}
#         return {
#             "decision_trace_id": str(memory.get("decision_trace_id") or "").strip(),
#             "summary": str(memory.get("summary") or "").strip(),
#             "response": str(memory.get("response") or "").strip(),
#             "refinement_prompt": str(memory.get("refinement_prompt") or "").strip(),
#             "recommendation_mode": str(memory.get("recommendation_mode") or "").strip(),
#             "recommendations": list(memory.get("recommendations") or []),
#         }

#     def _try_recommendation_followup_turn(self, user_message, state, readiness_result):
#         text = str(user_message or "").strip()
#         lowered = text.lower()
#         memory = self._recommendation_memory(state)
#         if not text or not memory:
#             return None

#         if self._is_recommendation_recall_request(lowered):
#             planner_output = {
#                 "action": "respond",
#                 "assistant_message": self._build_recommendation_recap(memory),
#                 "state_patch": {},
#                 "question_target_field": "",
#                 "corrections": [],
#                 "should_trigger_recommendation": False,
#                 "intent_groups": [],
#                 "confidence": 0.94,
#             }
#             updated_state = self._update_conversation_meta(deepcopy(state or {}), planner_output, readiness_result)
#             return {
#                 "state": updated_state,
#                 "validated": readiness_result,
#                 "planner_output": planner_output,
#             }

#         if any(term in lowered for term in self.RECOMMENDATION_REFINEMENT_TERMS):
#             requirements = dict((state or {}).get("requirements") or {})
#             budget = parse_money_value(text)
#             if budget is None:
#                 planner_output = {
#                     "action": "ask_question",
#                     "assistant_message": self._budget_refinement_prompt(requirements),
#                     "state_patch": {},
#                     "question_target_field": "budget",
#                     "question_target_locked": True,
#                     "corrections": [],
#                     "should_trigger_recommendation": False,
#                     "intent_groups": [],
#                     "confidence": 0.9,
#                 }
#                 updated_state = self._update_conversation_meta(deepcopy(state or {}), planner_output, readiness_result)
#                 return {
#                     "state": updated_state,
#                     "validated": readiness_result,
#                     "planner_output": planner_output,
#                 }

#             quantity = requirements.get("quantity") or requirements.get("team_size")
#             budget_scope = normalize_budget_scope(
#                 requirements.get("budget_scope"),
#                 preferred_categories=requirements.get("preferred_categories"),
#                 hint_text=text,
#                 quantity=quantity,
#             ) or requirements.get("budget_scope")
#             patch = {"budget": budget}
#             if budget_scope:
#                 patch["budget_scope"] = budget_scope

#             updated_state = deepcopy(state or {})
#             merged_requirements = self.requirement_state_manager.merge_requirement_patch(
#                 dict(updated_state.get("requirements") or {}),
#                 patch,
#                 source="recommendation_followup",
#             )
#             updated_state["requirements"] = merged_requirements
#             validated = self.requirement_guard_service.validate(merged_requirements)
#             updated_state["requirements"] = dict(validated.get("requirements") or merged_requirements)
#             planner_output = {
#                 "action": "recommend" if validated.get("is_ready") else "ask_question",
#                 "assistant_message": "Got it. I will re-rank the shortlist for the lower budget now.",
#                 "state_patch": patch,
#                 "question_target_field": "budget",
#                 "corrections": [],
#                 "should_trigger_recommendation": bool(validated.get("is_ready")),
#                 "intent_groups": [],
#                 "confidence": 0.92,
#             }
#             planner_output["question_target_field"] = self._resolve_question_target_field(validated, planner_output)
#             updated_state = self._update_conversation_meta(updated_state, planner_output, validated)
#             return {
#                 "state": updated_state,
#                 "validated": validated,
#                 "planner_output": planner_output,
#             }

#         return None

#     def _is_recommendation_recall_request(self, lowered):
#         lowered = str(lowered or "").strip().lower()
#         return any(pattern in lowered for pattern in self.RECOMMENDATION_RECALL_PATTERNS)

#     def _is_recommendation_followup_turn(self, lowered, state):
#         lowered = str(lowered or "").strip().lower()
#         if not lowered or not self._recommendation_memory(state):
#             return False
#         if self._is_recommendation_recall_request(lowered):
#             return True
#         return any(term in lowered for term in self.RECOMMENDATION_REFERENCE_TERMS)

#     def _budget_refinement_prompt(self, requirements):
#         requirements = dict(requirements or {})
#         quantity = requirements.get("quantity") or requirements.get("team_size")
#         scope = str(requirements.get("budget_scope") or "").strip().lower()
#         if scope == "project_total" or (not scope and quantity and int(quantity or 0) > 1):
#             return "Sure. What lower total budget should I use for the revised shortlist?"
#         return "Sure. What lower per-unit budget should I use for the revised shortlist?"

#     def _build_recommendation_recap(self, memory):
#         memory = dict(memory or {})
#         names = [
#             str(item.get("name") or "").strip()
#             for item in list(memory.get("recommendations") or [])
#             if str(item.get("name") or "").strip()
#         ]
#         summary = str(memory.get("summary") or "").strip()
#         refinement_prompt = str(memory.get("refinement_prompt") or "").strip()
#         if names:
#             if len(names) == 1:
#                 names_text = names[0]
#             elif len(names) == 2:
#                 names_text = f"{names[0]} and {names[1]}"
#             else:
#                 names_text = ", ".join(names[:-1]) + f", and {names[-1]}"
#             response = f"The latest shortlist was {names_text}."
#         else:
#             response = "I still have the latest procurement shortlist in context."
#         if summary:
#             response = f"{response} {summary}"
#         if refinement_prompt:
#             response = f"{response} {refinement_prompt}"
#         return response.strip()

#     def _apply_planner_safety_overrides(self, user_message, state, planner_output, readiness_result=None):
#         planner_output = dict(planner_output or {})
#         action = str(planner_output.get("action") or "").strip()
#         assistant_message = str(planner_output.get("assistant_message") or "").strip()
#         if not self._is_non_procurement_turn(user_message, state):
#             return planner_output
#         if action == "recommend":
#             return {
#                 "action": "respond",
#                 "assistant_message": self._scope_message(active_brief=bool((state or {}).get("requirements"))),
#                 "state_patch": {},
#                 "question_target_field": "",
#                 "corrections": [],
#                 "should_trigger_recommendation": False,
#                 "intent_groups": list(planner_output.get("intent_groups") or []),
#                 "confidence": max(float(planner_output.get("confidence") or 0.0), 0.9),
#             }
#         if action in {"ask_question", "clarify"} and not assistant_message:
#             planner_output["action"] = "respond"
#             planner_output["assistant_message"] = self._scope_message(active_brief=bool((state or {}).get("requirements")))
#             planner_output["question_target_field"] = ""
#             planner_output["should_trigger_recommendation"] = False
#         return planner_output

#     def _augment_planner_output_with_extracted_patch(self, user_message, state, planner_output, extracted_patch=None):
#         planner_output = dict(planner_output or {})
#         if self._is_non_procurement_turn(user_message, state):
#             return planner_output

#         merged_patch = dict(planner_output.get("state_patch") or {})
#         corrected_fields = {
#             str(item.get("field") or "").strip()
#             for item in list(planner_output.get("corrections") or [])
#             if str(item.get("field") or "").strip()
#         }

#         candidate_patch = dict(extracted_patch or {})
#         if not candidate_patch:
#             candidate_patch = self._build_requirement_patch_from_text(user_message, state)

#         current_requirements = dict((state or {}).get("requirements") or {})
#         readiness_result = self.requirement_guard_service.validate(current_requirements)
#         binding = self._bind_direct_answer(
#             user_message=user_message,
#             state=state,
#             readiness_result=readiness_result,
#             planner_recent_messages=[],
#         )
#         if binding:
#             for field, value in dict(binding.get("state_patch") or {}).items():
#                 candidate_patch.setdefault(field, value)
#             if not str(planner_output.get("question_target_field") or "").strip() and binding.get("question_target_field"):
#                 planner_output["question_target_field"] = str(binding.get("question_target_field") or "").strip()

#         for field, value in candidate_patch.items():
#             if field in merged_patch or field in corrected_fields:
#                 continue
#             merged_patch[field] = value

#         candidate_intent_groups = list(candidate_patch.get("intent_groups") or [])
#         if candidate_intent_groups and not list(planner_output.get("intent_groups") or []):
#             planner_output["intent_groups"] = candidate_intent_groups

#         if merged_patch:
#             planner_output["state_patch"] = merged_patch
#             if not str(planner_output.get("question_target_field") or "").strip():
#                 planner_output["question_target_field"] = self._next_priority_after_binding(merged_patch, current_requirements)
#         return planner_output

#     def _build_requirement_patch_from_text(self, user_message, state):
#         current_requirements = dict((state or {}).get("requirements") or {})
#         text = str(user_message or "").strip()
#         patch = {}
#         extracted_schema = {}

#         extraction_service = getattr(self.recommendation_service, "extraction_service", None)
#         intake_service = getattr(self.recommendation_service, "intake_service", None)
#         if extraction_service and intake_service:
#             try:
#                 extracted_schema = dict(extraction_service.extract(text, context=current_requirements) or {})
#                 normalized_payload = extraction_service.build_procurement_payload(
#                     extracted_schema,
#                     base_payload=current_requirements,
#                 )
#                 normalized_requirements = intake_service.normalize(normalized_payload)
#                 extracted_schema = dict(normalized_requirements or extracted_schema)
#                 patch.update(self._diff_requirements(current_requirements, normalized_requirements))
#             except Exception:
#                 extracted_schema = {}

#         categories = normalize_categories([text])
#         category = normalize_category(text)
#         if category and category not in categories:
#             categories.insert(0, category)
#         if categories:
#             merged_categories = self._merge_categories(list(current_requirements.get("preferred_categories") or []), categories)
#             patch.setdefault("preferred_categories", merged_categories)
#             patch.setdefault("preferred_category", merged_categories[0])

#         signals = self.signal_service.extract(text)
#         workload_values = self._dedupe_strings(
#             list(patch.get("workloads") or [])
#             + list(current_requirements.get("workloads") or [])
#             + normalize_workloads([text])
#             + list(signals.get("workload_types") or [])
#         )
#         if workload_values:
#             patch["workloads"] = workload_values
#         application_values = self._dedupe_strings(
#             list(patch.get("application_signals") or [])
#             + list(current_requirements.get("application_signals") or [])
#             + list(signals.get("application_signals") or [])
#         )
#         if application_values:
#             patch["application_signals"] = application_values
#         capability_values = self._dedupe_strings(
#             list(patch.get("capability_tags") or [])
#             + list(current_requirements.get("capability_tags") or [])
#             + list(signals.get("capability_tags") or [])
#         )
#         if capability_values:
#             patch["capability_tags"] = capability_values

#         budget = parse_money_value(text)
#         if budget is not None and current_requirements.get("budget") != budget:
#             patch.setdefault("budget", budget)
#             budget_scope = normalize_budget_scope(
#                 current_requirements.get("budget_scope"),
#                 preferred_categories=patch.get("preferred_categories") or current_requirements.get("preferred_categories"),
#                 hint_text=text,
#                 quantity=current_requirements.get("quantity") or current_requirements.get("team_size"),
#             )
#             if budget_scope:
#                 patch.setdefault("budget_scope", budget_scope)

#         team_size = parse_team_size(text)
#         if team_size is not None and team_size > 0:
#             lowered = text.lower()
#             headcount_terms = set(get_procurement_normalization_terms("quantity_units", default=set()) or set())
#             headcount_terms.update({"company", "headcount", "users", "people", "staff", "employees", "team"})
#             if any(term in lowered for term in headcount_terms):
#                 if current_requirements.get("team_size") != team_size:
#                     patch.setdefault("team_size", team_size)
#                 if current_requirements.get("quantity") != team_size:
#                     patch.setdefault("quantity", team_size)

#         multi_intent_service = getattr(self.recommendation_service, "multi_intent_service", None)
#         if multi_intent_service and text:
#             try:
#                 preview_requirements = dict(current_requirements)
#                 preview_requirements.update(dict(patch))
#                 detection_payload = dict(preview_requirements)
#                 detection_payload["chat_text"] = text
#                 detection_payload["raw_chat"] = text
#                 multi_intent_result = multi_intent_service.detect(detection_payload, extracted_schema or preview_requirements)
#                 if multi_intent_result.get("is_multi_intent"):
#                     intent_groups = self._normalize_multi_intent_groups_for_state(multi_intent_result)
#                     if intent_groups:
#                         categories_from_groups = [
#                             normalize_category(group.get("preferred_category") or group.get("category"))
#                             for group in intent_groups
#                             if normalize_category(group.get("preferred_category") or group.get("category"))
#                         ]
#                         merged_categories = self._merge_categories(
#                             list(preview_requirements.get("preferred_categories") or []),
#                             categories_from_groups,
#                         )
#                         if merged_categories:
#                             patch["preferred_categories"] = merged_categories
#                             patch["preferred_category"] = merged_categories[0]
#                         patch["intent_groups"] = intent_groups
#             except Exception:
#                 pass

#         filtered_patch = {}
#         for field, value in patch.items():
#             if not self._has_meaningful_value(value):
#                 continue
#             if current_requirements.get(field) == value:
#                 continue
#             filtered_patch[field] = value
#         return filtered_patch

#     def _diff_requirements(self, current_requirements, normalized_requirements):
#         current_requirements = dict(current_requirements or {})
#         normalized_requirements = dict(normalized_requirements or {})
#         ignored_fields = {
#             "assumption_severity",
#             "channel",
#             "currency",
#             "field_source",
#             "field_state",
#             "notes",
#             "ranking_persona",
#             "raw_chat",
#             "review_state",
#             "store_id",
#         }
#         patch = {}
#         for field, value in normalized_requirements.items():
#             if field in ignored_fields:
#                 continue
#             if not self._has_meaningful_value(value):
#                 continue
#             if current_requirements.get(field) == value:
#                 continue
#             patch[field] = value
#         return patch

#     def _has_meaningful_value(self, value):
#         if value is None:
#             return False
#         if isinstance(value, str):
#             return bool(value.strip())
#         if isinstance(value, (list, tuple, set, dict)):
#             return bool(value)
#         return True

#     def _should_trigger_recommendation(self, planner_output, validated):
#         planner_output = dict(planner_output or {})
#         readiness = dict((validated or {}).get("readiness") or {})
#         action = str(planner_output.get("action") or "").strip()
#         if action in {"respond", "ask_question", "clarify"} and not planner_output.get("should_trigger_recommendation"):
#             return False
#         if bool((validated or {}).get("is_ready")):
#             return True
#         if not planner_output.get("should_trigger_recommendation"):
#             return False
#         routing_recommendation = str(readiness.get("routing_recommendation") or "").strip()
#         return routing_recommendation in {
#             "recommend_now",
#             "recommend_with_one_refinement",
#             "recommend_with_optional_refinement",
#         }

#     def _try_llm_light_turn(self, user_message, state, readiness_result, planner_recent_messages):
#         route_result = self.planner_service.route_turn(
#             user_message=user_message,
#             state=self._planner_state(state),
#             recent_messages=planner_recent_messages,
#             readiness=dict((readiness_result or {}).get("readiness") or {}),
#             current_recommendations=self._current_recommendations(state),
#         )
#         if not route_result:
#             return None

#         route = str(route_result.get("route") or "").strip().lower()
#         confidence = float(route_result.get("confidence") or 0.0)
#         if route == "planner" or confidence < self.ROUTER_CONFIDENCE_THRESHOLD:
#             return None

#         if route == "direct_answer":
#             binding = self._bind_direct_answer(
#                 user_message=str(user_message or "").strip(),
#                 state=state,
#                 readiness_result=readiness_result,
#                 planner_recent_messages=planner_recent_messages,
#             )
#             if not binding:
#                 return None
#             return self._apply_direct_answer_binding(binding, state, readiness_result)

#         message = str(route_result.get("assistant_message") or "").strip()
#         question_target_field = str(route_result.get("question_target_field") or "").strip()
#         if route == "out_of_scope":
#             planner_output = {
#                 "action": "respond",
#                 "assistant_message": message or self._scope_message(active_brief=bool((state or {}).get("requirements"))),
#                 "state_patch": {},
#                 "question_target_field": "",
#                 "corrections": [],
#                 "should_trigger_recommendation": False,
#                 "intent_groups": [],
#                 "confidence": confidence,
#             }
#             updated_state = self._update_conversation_meta(deepcopy(state or {}), planner_output, readiness_result)
#             return {"state": updated_state, "validated": readiness_result, "planner_output": planner_output}

#         planner_output = {
#             "action": "respond",
#             "assistant_message": message,
#             "state_patch": {},
#             "question_target_field": question_target_field,
#             "corrections": [],
#             "should_trigger_recommendation": False,
#             "intent_groups": [],
#             "confidence": confidence,
#         }
#         if question_target_field:
#             safe_next_question = self._safe_next_question(
#                 validated=readiness_result,
#                 planner_output={"question_target_field": question_target_field},
#                 updated_state=state,
#             )
#             if safe_next_question:
#                 planner_output["action"] = "ask_question"
#                 if not planner_output["assistant_message"]:
#                     planner_output["assistant_message"] = safe_next_question
#         if not planner_output["assistant_message"]:
#             planner_output["assistant_message"] = "Got it."
#         updated_state = self._update_conversation_meta(deepcopy(state or {}), planner_output, readiness_result)
#         return {"state": updated_state, "validated": readiness_result, "planner_output": planner_output}

#     def _apply_direct_answer_binding(self, binding, state, readiness_result):
#         updated_state = deepcopy(state or {})
#         current_requirements = dict(updated_state.get("requirements") or {})
#         current_requirements = self.requirement_state_manager.resolve_corrections(
#             current_requirements,
#             binding.get("corrections"),
#             source="direct_answer_binder",
#         )
#         current_requirements = self.requirement_state_manager.merge_requirement_patch(
#             current_requirements,
#             binding.get("state_patch"),
#             source="direct_answer_binder",
#         )
#         updated_state["requirements"] = current_requirements
#         validated = self.requirement_guard_service.validate(current_requirements)
#         updated_state["requirements"] = dict(validated.get("requirements") or current_requirements)
#         resolved_question_target_field = self._resolve_question_target_field(
#             validated,
#             {"question_target_field": binding.get("question_target_field")},
#         )

#         response = self._build_bound_response(
#             binding,
#             validated,
#             planner_output={"question_target_field": resolved_question_target_field},
#             updated_state=updated_state,
#         )
#         planner_output = {
#             "action": (
#                 "recommend"
#                 if validated.get("is_ready")
#                 else (
#                     "ask_question"
#                     if self._safe_next_question(
#                         validated,
#                         {"question_target_field": resolved_question_target_field},
#                         updated_state,
#                     )
#                     else "respond"
#                 )
#             ),
#             "assistant_message": response,
#             "state_patch": binding.get("state_patch") or {},
#             "question_target_field": resolved_question_target_field,
#             "corrections": list(binding.get("corrections") or []),
#             "should_trigger_recommendation": bool(validated.get("is_ready")),
#             "intent_groups": [],
#             "confidence": float(binding.get("confidence") or 0.86),
#         }
#         updated_state = self._update_conversation_meta(updated_state, planner_output, validated)
#         return {"state": updated_state, "validated": validated, "planner_output": planner_output}

#     def _try_scope_guard_turn(self, user_message, state, readiness_result):
#         text = str(user_message or "").strip()
#         if not self._is_non_procurement_turn(text, state):
#             return None
#         planner_output = {
#             "action": "respond",
#             "assistant_message": self._scope_message(active_brief=bool((state or {}).get("requirements"))),
#             "state_patch": {},
#             "question_target_field": "",
#             "corrections": [],
#             "should_trigger_recommendation": False,
#             "intent_groups": [],
#             "confidence": 0.95,
#         }
#         updated_state = self._update_conversation_meta(deepcopy(state or {}), planner_output, readiness_result)
#         return {
#             "state": updated_state,
#             "validated": readiness_result,
#             "planner_output": planner_output,
#         }

#     def _is_non_procurement_turn(self, user_message, state):
#         text = str(user_message or "").strip().lower()
#         if not text:
#             return False
#         if self._is_recommendation_followup_turn(text, state):
#             return False
#         if any(pattern in text for pattern in self.OUT_OF_SCOPE_PATTERNS):
#             return True
#         categories = normalize_categories([text])
#         workloads = normalize_workloads([text])
#         signals = self.signal_service.extract(text)
#         has_procurement_signal = bool(
#             categories
#             or workloads
#             or signals.get("application_signals")
#             or signals.get("capability_tags")
#             or any(term in text for term in self.PROCUREMENT_TERMS)
#             or parse_money_value(text) is not None
#             or parse_team_size(text) is not None
#         )
#         if has_procurement_signal:
#             return False
#         current_requirements = dict((state or {}).get("requirements") or {})
#         if not current_requirements:
#             return False
#         non_procurement_starts = (
#             text.startswith("can you ")
#             or text.startswith("could you ")
#             or text.startswith("write ")
#             or text.startswith("tell me a ")
#         )
#         return non_procurement_starts

#     def _scope_message(self, active_brief=False):
#         if active_brief:
#             return (
#                 "I can help with procurement for laptops, desktops, servers, networking, printers, and accessories. "
#                 "Tell me what you want to buy or how you want to refine the current recommendation."
#             )
#         return (
#             "I can help with procurement for laptops, desktops, servers, networking, printers, and accessories like keyboards, mouse, and headsets. "
#             "Tell me what you need to buy, who it is for, and your budget."
#         )

#     def _is_greeting_turn(self, lowered_text):
#         text = str(lowered_text or "").strip().lower()
#         if not text:
#             return False
#         if text in self.GREETING_TOKENS:
#             return True
#         return bool(re.match(r"^(hi|hello|hey|good\s+morning|good\s+afternoon|good\s+evening)(?:\b|[!,. ])", text))

#     def _is_ack_turn(self, lowered_text):
#         text = str(lowered_text or "").strip().lower()
#         if not text:
#             return False
#         if text in self.ACK_TOKENS:
#             return True
#         return bool(re.match(r"^(ok(?:ay)?|sure|thanks?|thank\s+you|got\s+it|understood|go\s+ahead|continue)(?:\b|[!,. ])", text))

#     def _try_shortcut_turn(self, user_message, state, readiness_result, planner_recent_messages):
#         message_text = str(user_message or "").strip()
#         binding = self._bind_direct_answer(
#             user_message=message_text,
#             state=state,
#             readiness_result=readiness_result,
#             planner_recent_messages=planner_recent_messages,
#         )
#         if binding is None:
#             return None

#         updated_state = deepcopy(state or {})
#         current_requirements = dict(updated_state.get("requirements") or {})
#         current_requirements = self.requirement_state_manager.resolve_corrections(
#             current_requirements,
#             binding.get("corrections"),
#             source="direct_answer_binder",
#         )
#         current_requirements = self.requirement_state_manager.merge_requirement_patch(
#             current_requirements,
#             binding.get("state_patch"),
#             source="direct_answer_binder",
#         )
#         updated_state["requirements"] = current_requirements
#         validated = self.requirement_guard_service.validate(current_requirements)
#         updated_state["requirements"] = dict(validated.get("requirements") or current_requirements)
#         resolved_question_target_field = self._resolve_question_target_field(
#             validated,
#             {"question_target_field": binding.get("question_target_field")},
#         )

#         response = self._build_bound_response(
#             binding,
#             validated,
#             planner_output={"question_target_field": resolved_question_target_field},
#             updated_state=updated_state,
#         )
#         planner_output = {
#             "action": (
#                 "recommend"
#                 if validated.get("is_ready")
#                 else (
#                     "ask_question"
#                     if self._safe_next_question(
#                         validated,
#                         {"question_target_field": resolved_question_target_field},
#                         updated_state,
#                     )
#                     else "respond"
#                 )
#             ),
#             "assistant_message": response,
#             "state_patch": binding.get("state_patch") or {},
#             "question_target_field": resolved_question_target_field,
#             "corrections": list(binding.get("corrections") or []),
#             "should_trigger_recommendation": bool(validated.get("is_ready")),
#             "intent_groups": [],
#             "confidence": float(binding.get("confidence") or 0.86),
#         }
#         updated_state = self._update_conversation_meta(updated_state, planner_output, validated)
#         return {
#             "state": updated_state,
#             "validated": validated,
#             "planner_output": planner_output,
#         }

#     def _bind_direct_answer(self, user_message, state, readiness_result, planner_recent_messages):
#         requirements = dict((state or {}).get("requirements") or {})
#         conversation_meta = dict((state or {}).get("conversation_meta") or {})
#         last_asked_field = str(conversation_meta.get("last_asked_field") or "").strip()
#         if not last_asked_field and planner_recent_messages:
#             last_assistant = next((msg for msg in reversed(planner_recent_messages) if msg.get("role") == "assistant"), {})
#             response_mode = str(last_assistant.get("response_mode") or "").strip()
#             if response_mode in {"ask_question", "clarify"}:
#                 last_asked_field = str(last_assistant.get("question_target_field") or "").strip()

#         text = str(user_message or "").strip()
#         lowered = text.lower()
#         if not text or not last_asked_field or lowered in {"yes", "yeah", "yep", "no", "nope"}:
#             return None

#         categories = normalize_categories([text])
#         category = normalize_category(text)
#         if category and category not in categories:
#             categories.insert(0, category)
#         existing_categories = list(requirements.get("preferred_categories") or [])
#         signal_bundle = self.signal_service.extract(text)
#         signal_workloads = list(signal_bundle.get("workload_types") or [])
#         new_application_signals = self._dedupe_strings(signal_bundle.get("application_signals") or [])
#         new_capability_tags = self._dedupe_strings(signal_bundle.get("capability_tags") or [])
#         new_workloads = self._dedupe_strings(normalize_workloads([text]) + signal_workloads)

#         if last_asked_field in {"preferred_category", "category_or_workload"}:
#             patch = {}
#             if categories:
#                 merged_categories = self._merge_categories(existing_categories, categories)
#                 patch["preferred_categories"] = merged_categories
#                 patch["preferred_category"] = merged_categories[0]
#             if new_workloads:
#                 patch["workloads"] = self._dedupe_strings(list(requirements.get("workloads") or []) + new_workloads)
#             if new_application_signals:
#                 patch["application_signals"] = self._dedupe_strings(
#                     (requirements.get("application_signals") or []) + new_application_signals
#                 )
#             if new_capability_tags:
#                 patch["capability_tags"] = self._dedupe_strings(
#                     (requirements.get("capability_tags") or []) + new_capability_tags
#                 )
#             if patch:
#                 if "gaming_interactive" in new_application_signals and not requirements.get("performance_priority"):
#                     patch["performance_priority"] = "performance"
#                 return {
#                     "state_patch": patch,
#                     "acknowledgement": self._profile_acknowledgement(patch),
#                     "question_target_field": self._next_priority_after_binding(patch, requirements),
#                     "confidence": 0.95,
#                 }

#         if last_asked_field in {"workload_or_application_profile", "application_profile"}:
#             patch = {}
#             if new_workloads:
#                 patch["workloads"] = self._dedupe_strings(list(requirements.get("workloads") or []) + new_workloads)
#             if new_application_signals:
#                 patch["application_signals"] = self._dedupe_strings(
#                     (requirements.get("application_signals") or []) + new_application_signals
#                 )
#             if new_capability_tags:
#                 patch["capability_tags"] = self._dedupe_strings(
#                     (requirements.get("capability_tags") or []) + new_capability_tags
#                 )
#             if categories:
#                 merged_categories = self._merge_categories(existing_categories, categories)
#                 patch["preferred_categories"] = merged_categories
#                 patch["preferred_category"] = merged_categories[0]
#             if patch:
#                 if "gaming_interactive" in new_application_signals and not requirements.get("performance_priority"):
#                     patch["performance_priority"] = "performance"
#                 return {
#                     "state_patch": patch,
#                     "acknowledgement": self._profile_acknowledgement(patch),
#                     "question_target_field": self._next_priority_after_binding(patch, requirements),
#                     "confidence": 0.93,
#                 }

#         if last_asked_field == "budget":
#             team_size = self._direct_reply_team_size(text)
#             if team_size is not None and not self._looks_like_budget_reply(text, last_asked_field=last_asked_field):
#                 patch = {
#                     "team_size": team_size,
#                 }
#                 if not requirements.get("quantity") and team_size > 1:
#                     patch["quantity"] = team_size
#                 purchase_scope = normalize_purchase_scope(
#                     requirements.get("purchase_scope"),
#                     preferred_categories=requirements.get("preferred_categories"),
#                     quantity=patch.get("quantity") or requirements.get("quantity") or team_size,
#                     team_size=team_size,
#                     hint_text=text,
#                 )
#                 if purchase_scope:
#                     patch["purchase_scope"] = purchase_scope
#                 return {
#                     "state_patch": patch,
#                     "acknowledgement": f"team size {team_size}",
#                     "question_target_field": self._next_priority_after_binding(patch, requirements),
#                     "confidence": 0.88,
#                 }
#             if not self._looks_like_budget_reply(text, last_asked_field=last_asked_field):
#                 return None
#             budget = parse_money_value(text)
#             if budget is not None:
#                 scope = normalize_budget_scope(
#                     requirements.get("budget_scope"),
#                     preferred_categories=requirements.get("preferred_categories"),
#                     hint_text=text,
#                     quantity=requirements.get("quantity") or requirements.get("team_size"),
#                 )
#                 patch = {"budget": budget}
#                 if scope:
#                     patch["budget_scope"] = scope
#                 return {
#                     "state_patch": patch,
#                     "acknowledgement": f"budget {budget}",
#                     "question_target_field": self._next_priority_after_binding(patch, requirements),
#                     "confidence": 0.94,
#                 }

#         if last_asked_field == "budget_scope":
#             scope = normalize_budget_scope(
#                 text,
#                 preferred_categories=requirements.get("preferred_categories"),
#                 hint_text=text,
#                 quantity=requirements.get("quantity") or requirements.get("team_size"),
#             )
#             if scope:
#                 return {
#                     "state_patch": {"budget_scope": scope},
#                     "acknowledgement": "budget scope updated",
#                     "question_target_field": self._next_priority_after_binding({"budget_scope": scope}, requirements),
#                     "confidence": 0.93,
#                 }

#         if last_asked_field in {"team_size", "purchase_scope_or_quantity"}:
#             quantity = parse_team_size(text)
#             purchase_scope = normalize_purchase_scope(
#                 requirements.get("purchase_scope"),
#                 preferred_categories=requirements.get("preferred_categories"),
#                 quantity=quantity,
#                 team_size=quantity,
#                 hint_text=text,
#             )
#             if quantity is not None or purchase_scope:
#                 patch = {}
#                 if quantity is not None:
#                     if last_asked_field == "team_size":
#                         patch["team_size"] = quantity
#                     else:
#                         patch["quantity"] = quantity
#                         if not requirements.get("team_size") and quantity > 1:
#                             patch["team_size"] = quantity
#                 if purchase_scope:
#                     patch["purchase_scope"] = purchase_scope
#                 return {
#                     "state_patch": patch,
#                     "acknowledgement": "scope updated",
#                     "question_target_field": self._next_priority_after_binding(patch, requirements),
#                     "confidence": 0.9,
#                 }

#         team_size = self._direct_reply_team_size(text)
#         if team_size is not None:
#             patch = {"team_size": team_size}
#             if not requirements.get("quantity") and team_size > 1:
#                 patch["quantity"] = team_size
#             purchase_scope = normalize_purchase_scope(
#                 requirements.get("purchase_scope"),
#                 preferred_categories=requirements.get("preferred_categories"),
#                 quantity=patch.get("quantity") or requirements.get("quantity") or team_size,
#                 team_size=team_size,
#                 hint_text=text,
#             )
#             if purchase_scope:
#                 patch["purchase_scope"] = purchase_scope
#             return {
#                 "state_patch": patch,
#                 "acknowledgement": f"team size {team_size}",
#                 "question_target_field": self._next_priority_after_binding(patch, requirements),
#                 "confidence": 0.88,
#             }

#         if self._looks_like_budget_reply(text, last_asked_field=last_asked_field):
#             budget = parse_money_value(text)
#             if budget is not None:
#                 scope = normalize_budget_scope(
#                     requirements.get("budget_scope"),
#                     preferred_categories=requirements.get("preferred_categories"),
#                     hint_text=text,
#                     quantity=requirements.get("quantity") or requirements.get("team_size"),
#                 )
#                 patch = {"budget": budget}
#                 if scope:
#                     patch["budget_scope"] = scope
#                 return {
#                     "state_patch": patch,
#                     "acknowledgement": f"budget {budget}",
#                     "question_target_field": self._next_priority_after_binding(patch, requirements),
#                     "confidence": 0.88,
#                 }

#         if last_asked_field == "growth_expectation":
#             growth = self._parse_growth_expectation(text)
#             if growth:
#                 return {
#                     "state_patch": {"growth_expectation": growth},
#                     "acknowledgement": growth.replace("_", " "),
#                     "question_target_field": self._next_priority_after_binding({"growth_expectation": growth}, requirements),
#                     "confidence": 0.9,
#                 }

#         if last_asked_field == "performance_priority":
#             priority = self._parse_performance_priority(text)
#             if priority:
#                 return {
#                     "state_patch": {"performance_priority": priority},
#                     "acknowledgement": priority,
#                     "question_target_field": self._next_priority_after_binding({"performance_priority": priority}, requirements),
#                     "confidence": 0.9,
#                 }

#         return None

#     def _direct_reply_team_size(self, text):
#         lowered = str(text or "").strip().lower()
#         if not lowered:
#             return None
#         quantity = parse_team_size(lowered)
#         if quantity is None:
#             return None
#         headcount_terms = set(get_procurement_normalization_terms("quantity_units", default=set()) or set())
#         headcount_terms.update({"company", "headcount"})
#         if any(term in lowered for term in headcount_terms):
#             return quantity
#         return None

#     def _looks_like_budget_reply(self, text, last_asked_field=""):
#         lowered = str(text or "").strip().lower()
#         if not lowered:
#             return False
#         if self._direct_reply_team_size(lowered) is not None:
#             return False
#         explicit_budget_markers = (
#             "budget",
#             "rs",
#             "inr",
#             "usd",
#             "eur",
#             "gbp",
#             "$",
#             "₹",
#             "lakh",
#             "lakhs",
#             "thousand",
#             "thousands",
#             "k",
#             "each",
#             "per unit",
#             "per device",
#             "per seat",
#             "per laptop",
#             "per desktop",
#             "per server",
#             "total",
#             "overall",
#             "project",
#             "combined",
#             "under ",
#             "within ",
#         )
#         if any(marker in lowered for marker in explicit_budget_markers):
#             return True
#         compact = lowered.replace(",", "").strip()
#         return bool(compact) and compact.replace(".", "", 1).isdigit() and str(last_asked_field or "").strip() == "budget"

#     def _normalize_non_recommendation_planner_output(self, planner_output, validated, updated_state):
#         planner_output = dict(planner_output or {})
#         action = str(planner_output.get("action") or "").strip()
#         if action != "recommend":
#             return planner_output
#         question_target_field = self._resolve_question_target_field(validated, planner_output)
#         safe_next_question = self._safe_next_question(
#             validated=validated,
#             planner_output={"question_target_field": question_target_field},
#             updated_state=updated_state,
#         )
#         if safe_next_question:
#             planner_output["action"] = "ask_question"
#             planner_output["question_target_field"] = question_target_field
#             planner_output["assistant_message"] = safe_next_question
#             planner_output["should_trigger_recommendation"] = False
#             return planner_output
#         planner_output["action"] = "respond"
#         planner_output["assistant_message"] = str(planner_output.get("assistant_message") or "").strip() or "Got it."
#         planner_output["question_target_field"] = ""
#         planner_output["should_trigger_recommendation"] = False
#         return planner_output

#     def _next_priority_after_binding(self, patch, requirements):
#         merged = dict(requirements or {})
#         merged.update(dict(patch or {}))
#         if not (merged.get("preferred_categories") or merged.get("preferred_category")):
#             return "preferred_category"
#         if merged.get("budget") is None:
#             return "budget"
#         if not (merged.get("workloads") or merged.get("application_signals") or merged.get("capability_tags")):
#             return "workload_or_application_profile"
#         if not (merged.get("team_size") or merged.get("quantity")):
#             return "team_size"
#         if not merged.get("budget_scope") and ((merged.get("team_size") or merged.get("quantity")) and int(merged.get("team_size") or merged.get("quantity") or 0) > 1):
#             return "budget_scope"
#         return ""

#     def _profile_acknowledgement(self, patch):
#         patch = dict(patch or {})
#         parts = []
#         categories = list(patch.get("preferred_categories") or [])
#         workloads = list(patch.get("workloads") or [])
#         application_signals = list(patch.get("application_signals") or [])
#         if categories:
#             parts.append(self._humanize_categories(categories))
#         detail_labels = []
#         for workload in workloads:
#             detail_labels.append(self.WORKLOAD_LABELS.get(workload, str(workload).replace("_", " ")))
#         for signal in application_signals:
#             detail_labels.append(self.APPLICATION_SIGNAL_LABELS.get(signal, str(signal).replace("_", " ")))
#         detail_labels = self._dedupe_strings(detail_labels)
#         if detail_labels:
#             parts.append(", ".join(detail_labels))
#         return " with ".join(parts) if parts else "details updated"

#     def _build_bound_response(self, binding, validated, planner_output=None, updated_state=None):
#         acknowledgement = str(binding.get("acknowledgement") or "").strip()
#         next_question = self._safe_next_question(
#             validated=validated,
#             planner_output=planner_output,
#             updated_state=updated_state,
#         )
#         if validated.get("is_ready"):
#             if acknowledgement:
#                 return f"Got it — {acknowledgement}. I have enough to put together recommendations now."
#             return "Got it. I have enough to put together recommendations now."
#         if acknowledgement and next_question:
#             return f"Got it — {acknowledgement}. {next_question}"
#         if acknowledgement:
#             return f"Got it — {acknowledgement}."
#         return next_question or "Got it."

#     def _build_non_recommendation_response(self, session, updated_state, validated, planner_output, turn_metrics):
#         response_mode = str(planner_output.get("action") or "ask_question").strip() or "ask_question"
#         response_text = str(planner_output.get("assistant_message") or "").strip()
#         question_target_field = self._resolve_question_target_field(validated, planner_output)
#         safe_next_question = self._safe_next_question(
#             validated=validated,
#             planner_output={"question_target_field": question_target_field},
#             updated_state=updated_state,
#         )
#         next_question = ""
#         if response_mode == "recommend":
#             if safe_next_question:
#                 response_mode = "ask_question"
#             else:
#                 response_mode = "respond"
#         if response_mode in {"ask_question", "clarify"}:
#             planner_question_is_usable = bool(
#                 response_text
#                 and "?" in response_text
#                 and (not question_target_field or not self._question_prompt_mismatch(question_target_field, response_text))
#             )
#             if planner_question_is_usable:
#                 next_question = response_text
#             else:
#                 acknowledgement = self._extract_acknowledgement_prefix(response_text, safe_next_question)
#                 next_question = self._polish_clarification_question(
#                     question_target_field=question_target_field,
#                     canonical_question=safe_next_question,
#                     updated_state=updated_state,
#                     acknowledgement=acknowledgement,
#                 )
#                 if acknowledgement and next_question:
#                     response_text = f"{acknowledgement} {next_question}".strip()
#                 else:
#                     response_text = next_question or response_text
#             if next_question and not response_text:
#                 response_text = next_question
#         elif not response_text:
#             response_text = safe_next_question or "Got it."

#         ui_guidance = build_narrowing_guidance(
#             dict(updated_state.get("requirements") or {}),
#             dict(validated.get("readiness") or {}),
#         )
#         payload_readiness = dict(validated.get("readiness") or {})
#         if response_mode in {"ask_question", "clarify"} and question_target_field:
#             payload_readiness["recommended_question_id"] = question_target_field
#             if next_question:
#                 payload_readiness["next_question"] = next_question

#         response_started_at = perf_counter()
#         payload = self.response_contract_adapter.build_question_payload(
#             response=response_text,
#             next_question=next_question,
#             requirements=dict(updated_state.get("requirements") or {}),
#             readiness=payload_readiness,
#             extracted_schema=dict(updated_state.get("requirements") or {}),
#             ui_guidance=ui_guidance,
#             meta={"conversation_id": session.conversation_id},
#             llm_stats=self._build_llm_stats(),
#             response_mode=response_mode,
#         )
#         self._mark_stage(turn_metrics, "response_contract_ms", response_started_at)

#         persist_started_at = perf_counter()
#         self.chat_session_service.append_message(
#             session.conversation_id,
#             role="assistant",
#             content=payload["response"],
#             meta={
#                 "response_mode": response_mode,
#                 "question_target_field": question_target_field,
#             },
#             message_type="question",
#         )
#         self._mark_stage(turn_metrics, "db_persist_ms", persist_started_at)

#         payload = self._attach_turn_metrics(payload, turn_metrics, response_type="question")
#         self._append_runtime_log(payload)
#         return payload

#     def _build_recommendation_response(self, session, updated_state, validated, turn_metrics):
#         recommendation_started_at = perf_counter()
#         state_for_recommendation = dict(updated_state.get("requirements") or {})
#         if updated_state.get("intent_groups"):
#             state_for_recommendation["intent_groups"] = deepcopy(updated_state.get("intent_groups") or [])
#         if not state_for_recommendation.get("raw_chat"):
#             brief = str((updated_state.get("conversation_meta") or {}).get("conversation_brief") or "").strip()
#             if brief:
#                 state_for_recommendation["raw_chat"] = brief
#         result = self.recommendation_service.recommend_from_state(
#             state_for_recommendation,
#             persist=False,
#         )
#         self._mark_stage(turn_metrics, "recommendation_total_ms", recommendation_started_at)

#         ui_guidance = build_narrowing_guidance(
#             dict(updated_state.get("requirements") or {}),
#             dict(validated.get("readiness") or {}),
#         )

#         recommendation_meta = dict(result.get("meta") or {})
#         runtime_obs = dict(recommendation_meta.get("runtime_observability") or {})
#         decision_trace = dict(recommendation_meta.get("decision_trace") or {})
#         multi_intent_trace = dict(decision_trace.get("multi_intent") or {})
#         shared_budget = dict(multi_intent_trace.get("shared_budget") or {})
#         no_exact_budget_fit = bool((recommendation_meta.get("budget_fit_summary") or {}).get("no_exact_budget_fit"))
#         shared_budget_allocation_required = bool(shared_budget.get("allocation_required"))
#         ask_instead_of_recommend = no_exact_budget_fit or shared_budget_allocation_required

#         response_started_at = perf_counter()
#         if ask_instead_of_recommend:
#             next_question = ""
#             response_text = str(result.get("summary") or result.get("response") or "").strip()
#             if shared_budget_allocation_required:
#                 next_question = str(shared_budget.get("clarification_prompt") or (result.get("readiness") or {}).get("next_question") or "").strip()
#                 if not response_text:
#                     response_text = next_question
#             elif no_exact_budget_fit:
#                 next_question = "Would you like to raise the budget, change the category, or relax the constraints so I can search again?"
#                 if not response_text:
#                     response_text = next_question
#             payload = self.response_contract_adapter.build_question_payload(
#                 response=response_text,
#                 next_question=next_question,
#                 requirements=result.get("requirements"),
#                 readiness=result.get("readiness"),
#                 extracted_schema=result.get("requirements"),
#                 ui_guidance=ui_guidance,
#                 meta=self._merge_meta(result.get("meta"), {"conversation_id": session.conversation_id, "response_mode": "ask_question"}),
#                 llm_stats=self._build_llm_stats(),
#                 response_mode="ask_question",
#             )
#         else:
#             payload = self.response_contract_adapter.build_recommendation_payload(
#                 response=result.get("summary") or result.get("response") or "I found the closest matches for your procurement brief.",
#                 decision_trace_id=result.get("decision_trace_id"),
#                 requirements=result.get("requirements"),
#                 recommendations=result.get("recommendations"),
#                 target_profile=result.get("target_profile"),
#                 assumptions=result.get("assumptions"),
#                 comparison=result.get("comparison"),
#                 readiness=result.get("readiness"),
#                 ui_guidance=ui_guidance,
#                 recommendation_context=result.get("recommendation_context"),
#                 refinement_prompt=result.get("refinement_prompt"),
#                 review_state=result.get("review_state"),
#                 check_requirement_summary=result.get("check_requirement_summary"),
#                 editable_inferred_values=result.get("editable_inferred_values"),
#                 template_candidates=result.get("template_candidates"),
#                 recommendation_groups=result.get("recommendation_groups"),
#                 meta=self._merge_meta(result.get("meta"), {"conversation_id": session.conversation_id}),
#                 llm_stats=self._build_llm_stats(),
#                 summary=result.get("summary"),
#             )
#         self._mark_stage(turn_metrics, "response_contract_ms", response_started_at)

#         persist_started_at = perf_counter()
#         remembered_state = self._remember_recommendation_state(
#             updated_state,
#             result=result,
#             payload=payload,
#         )
#         self.chat_session_service.save_state(session.conversation_id, remembered_state)
#         self.chat_session_service.mark_recommended(
#             session.conversation_id,
#             decision_trace_id=payload.get("decision_trace_id"),
#         )
#         self.chat_session_service.append_message(
#             session.conversation_id,
#             role="assistant",
#             content=payload["response"],
#             meta={
#                 "response_mode": "recommend",
#                 "decision_trace_id": payload.get("decision_trace_id"),
#             },
#             message_type="recommendation",
#         )
#         self._mark_stage(turn_metrics, "db_persist_ms", persist_started_at)

#         background_enqueued = self.background_dispatcher.dispatch_recommendation_update(
#             session.conversation_id,
#             payload.get("decision_trace_id"),
#             payload.get("requirements"),
#             payload.get("target_profile"),
#             payload.get("recommendations"),
#         )
#         turn_metrics["background_explanation_enqueued"] = bool(background_enqueued)
#         payload = self._attach_turn_metrics(payload, turn_metrics, response_type="recommendation")
#         self._append_runtime_log(payload)
#         return payload

#     def _planner_state(self, state):
#         state = dict(state or {})
#         requirements = dict(state.get("requirements") or {})
#         intent_groups = list(state.get("intent_groups") or requirements.get("intent_groups") or [])
#         return {
#             "requirements": requirements,
#             "conversation_meta": dict(state.get("conversation_meta") or {}),
#             "intent_groups": intent_groups,
#             "recommendation_memory": self._planner_recommendation_memory(state),
#         }

#     def _build_recommendation_memory(self, result, payload):
#         result = dict(result or {})
#         payload = dict(payload or {})
#         recommendations = []
#         for item in list(payload.get("recommendations") or result.get("recommendations") or [])[:3]:
#             recommendation = dict(item or {})
#             recommendations.append(
#                 {
#                     "name": str(recommendation.get("name") or "").strip(),
#                     "fit_status": str(recommendation.get("fit_status") or "").strip(),
#                     "price": recommendation.get("price"),
#                     "currency": str(recommendation.get("currency") or "").strip(),
#                 }
#             )
#         return {
#             "decision_trace_id": str(payload.get("decision_trace_id") or result.get("decision_trace_id") or "").strip(),
#             "summary": str(payload.get("summary") or result.get("summary") or "").strip(),
#             "response": str(payload.get("response") or result.get("response") or "").strip(),
#             "refinement_prompt": str(payload.get("refinement_prompt") or result.get("refinement_prompt") or "").strip(),
#             "recommendation_mode": str(result.get("recommendation_mode") or payload.get("recommendation_mode") or "").strip(),
#             "recommendations": recommendations,
#         }

#     def _remember_recommendation_state(self, state, result, payload):
#         state = deepcopy(state or {})
#         result = dict(result or {})
#         state["recommendation_memory"] = self._build_recommendation_memory(result, payload)
#         state["recommendations"] = list((payload or {}).get("recommendations") or [])
#         state["recommendation_context"] = dict((payload or {}).get("recommendation_context") or {})
#         state["refinement_prompt"] = str((payload or {}).get("refinement_prompt") or "").strip()
#         if result.get("recommendation_groups"):
#             state["recommendation_groups"] = deepcopy(result.get("recommendation_groups") or [])
#         if state.get("intent_groups"):
#             state["intent_groups"] = deepcopy(state.get("intent_groups") or [])
#         return self._update_conversation_meta(
#             state,
#             {
#                 "action": "recommend",
#                 "assistant_message": str((payload or {}).get("response") or "").strip(),
#                 "question_target_field": "",
#             },
#             {"readiness": dict((payload or {}).get("readiness") or (result or {}).get("readiness") or {})},
#         )

#     def _resolve_question_target_field(self, validated, planner_output=None):
#         planner_output = dict(planner_output or {})
#         readiness = dict((validated or {}).get("readiness") or {})
#         action = str(planner_output.get("action") or "").strip()
#         missing_signals = set(readiness.get("missing_signals") or [])
#         locked = bool(planner_output.get("question_target_locked"))
#         recommended_field = str(readiness.get("recommended_question_id") or "").strip()
#         field = str(planner_output.get("question_target_field") or "").strip()
#         canonical_question = str(readiness.get("next_question") or "").strip()
#         assistant_message = str(planner_output.get("assistant_message") or "").strip()
#         if field:
#             if locked:
#                 return field
#             if action not in {"ask_question", "clarify"}:
#                 return field
#             reference_prompt = assistant_message or canonical_question
#             if field in missing_signals and (not reference_prompt or not self._question_prompt_mismatch(field, reference_prompt)):
#                 return field
#             if recommended_field and field != recommended_field:
#                 if field not in missing_signals:
#                     return recommended_field
#                 if reference_prompt and self._question_prompt_mismatch(field, reference_prompt):
#                     return recommended_field
#                 return field
#             return field
#         if (not field or self._question_prompt_mismatch(field, canonical_question)) and recommended_field:
#             field = recommended_field
#         return field

#     def _extract_acknowledgement_prefix(self, response_text, canonical_question):
#         response_text = str(response_text or "").strip()
#         canonical_question = str(canonical_question or "").strip()
#         if not response_text or not canonical_question:
#             return ""
#         if "?" in response_text:
#             return ""
#         if canonical_question in response_text:
#             return response_text.split(canonical_question, 1)[0].strip()
#         return response_text

#     def _polish_clarification_question(self, question_target_field, canonical_question, updated_state=None, acknowledgement=""):
#         field = str(question_target_field or "").strip()
#         canonical = str(canonical_question or "").strip()
#         if not field or not canonical:
#             return canonical
#         planner_service = getattr(self, "planner_service", None)
#         if not planner_service or not hasattr(planner_service, "rephrase_clarification_question"):
#             return canonical
#         polished = planner_service.rephrase_clarification_question(
#             question_target_field=field,
#             canonical_question=canonical,
#             state=dict(updated_state or {}),
#             acknowledgement=str(acknowledgement or "").strip(),
#         )
#         polished = str(polished or "").strip()
#         if not polished or self._question_prompt_mismatch(field, polished):
#             return canonical
#         return polished

#     def _update_conversation_meta(self, state, planner_output, validated):
#         state = deepcopy(state or {})
#         conversation_meta = dict(state.get("conversation_meta") or {})
#         action = str((planner_output or {}).get("action") or "").strip()
#         question_target_field = str((planner_output or {}).get("question_target_field") or "").strip()
#         assistant_message = str((planner_output or {}).get("assistant_message") or "").strip()
#         readiness = dict((validated or {}).get("readiness") or {})
#         requirements = dict(state.get("requirements") or {})

#         if action in {"ask_question", "clarify"}:
#             conversation_meta["last_asked_field"] = question_target_field or str(readiness.get("recommended_question_id") or "").strip()
#             conversation_meta["recommended_question_id"] = (
#                 question_target_field or str(readiness.get("recommended_question_id") or "").strip()
#             )
#         elif action == "recommend":
#             conversation_meta["last_asked_field"] = ""
#             conversation_meta["recommended_question_id"] = str(readiness.get("recommended_question_id") or "").strip()
#         else:
#             conversation_meta["recommended_question_id"] = str(readiness.get("recommended_question_id") or "").strip()

#         conversation_meta["last_assistant_action"] = action
#         conversation_meta["last_assistant_message"] = assistant_message
#         conversation_meta["conversation_brief"] = self._build_conversation_brief(requirements)
#         state["conversation_meta"] = conversation_meta
#         return state

#     def _build_conversation_brief(self, requirements):
#         requirements = dict(requirements or {})
#         parts = []
#         categories = list(requirements.get("preferred_categories") or [])
#         if categories:
#             parts.append(self._humanize_categories(categories))
#         elif requirements.get("preferred_category"):
#             parts.append(str(requirements.get("preferred_category")).strip())
#         workloads = list(requirements.get("workloads") or [])
#         if workloads:
#             parts.append(self._humanize_workloads(workloads))
#         application_signals = list(requirements.get("application_signals") or [])
#         if application_signals:
#             labels = [self.APPLICATION_SIGNAL_LABELS.get(sig, str(sig).replace("_", " ")) for sig in application_signals]
#             parts.append(", ".join(labels))
#         team_size = requirements.get("team_size") or requirements.get("quantity")
#         if team_size:
#             parts.append(f"for {team_size} users")
#         budget = requirements.get("budget")
#         if budget is not None:
#             scope = str(requirements.get("budget_scope") or "").strip().replace("_", " ")
#             parts.append(f"budget {budget}{' ' + scope if scope else ''}")
#         return "; ".join(parts)

#     def _humanize_workloads(self, workloads):
#         items = []
#         for workload in list(workloads or []):
#             items.append(self.WORKLOAD_LABELS.get(workload, str(workload).replace("_", " ")))
#         return ", ".join(self._dedupe_strings(items))

#     def _humanize_categories(self, categories):
#         normalized = [str(category).replace("_", " ") for category in list(categories or []) if category]
#         if not normalized:
#             return ""
#         if len(normalized) == 1:
#             return normalized[0]
#         if len(normalized) == 2:
#             return f"{normalized[0]} and {normalized[1]}"
#         return ", ".join(normalized[:-1]) + f", and {normalized[-1]}"

#     def _merge_categories(self, existing_categories, new_categories):
#         merged = []
#         for item in list(existing_categories or []) + list(new_categories or []):
#             if item and item not in merged:
#                 merged.append(item)
#         return merged

#     def _normalize_multi_intent_groups_for_state(self, multi_intent_result):
#         groups = []
#         for intent in list(dict(multi_intent_result or {}).get("intents") or []):
#             schema = dict(intent.get("extracted_schema") or {})
#             category = normalize_category(intent.get("category") or schema.get("preferred_category"))
#             workloads = self._dedupe_strings(
#                 normalize_workloads(schema.get("workload_types") or intent.get("workloads") or [])
#             )
#             if not category and not workloads:
#                 continue
#             group = {
#                 "group_id": str(intent.get("group_id") or "").strip(),
#                 "label": str(intent.get("label") or "").strip(),
#                 "intent_text": str(intent.get("intent_text") or schema.get("raw_chat") or "").strip(),
#             }
#             if category:
#                 group["preferred_category"] = category
#             if workloads:
#                 group["workloads"] = workloads
#             application_signals = self._dedupe_strings(schema.get("application_signals") or [])
#             capability_tags = self._dedupe_strings(schema.get("capability_tags") or [])
#             if application_signals:
#                 group["application_signals"] = application_signals
#             if capability_tags:
#                 group["capability_tags"] = capability_tags
#             for field in ("team_size", "quantity", "budget", "budget_scope", "purchase_scope"):
#                 value = schema.get(field)
#                 if value not in (None, "", [], {}):
#                     group[field] = value
#             groups.append(group)
#         return groups

#     def _dedupe_strings(self, values):
#         items = []
#         for value in list(values or []):
#             cleaned = str(value or "").strip()
#             if cleaned and cleaned not in items:
#                 items.append(cleaned)
#         return items

#     def _safe_next_question(self, validated, planner_output=None, updated_state=None):
#         readiness = dict((validated or {}).get("readiness") or {})
#         field = str(((planner_output or {}).get("question_target_field")) or readiness.get("recommended_question_id") or "").strip()
#         next_question = str(readiness.get("next_question") or "").strip()
#         if field and (not next_question or self._question_prompt_mismatch(field, next_question)):
#             next_question = default_follow_up_prompt(field)
#         if not next_question and field:
#             next_question = default_follow_up_prompt(field)
#         return next_question

#     def _question_prompt_mismatch(self, field, prompt):
#         field = str(field or "").strip()
#         prompt_l = str(prompt or "").strip().lower()
#         if not field:
#             return False
#         if not prompt_l:
#             return True
#         if field in {"workload_or_application_profile", "application_profile"}:
#             return (
#                 "trying to buy first" in prompt_l
#                 or "laptops, desktops, servers" in prompt_l
#                 or "budget" in prompt_l
#                 or "total budget" in prompt_l
#                 or "per-unit budget" in prompt_l
#                 or "how many" in prompt_l
#             )
#         if field in {"team_size", "budget", "budget_scope", "purchase_scope_or_quantity", "growth_expectation", "performance_priority"}:
#             return (
#                 "trying to buy first" in prompt_l
#                 or "what kind of work" in prompt_l
#                 or "which apps or tools matter most" in prompt_l
#                 or "applications or tools" in prompt_l
#             )
#         if field in {"preferred_category", "category_or_workload"}:
#             return "what kind of work" in prompt_l or "which apps or tools matter most" in prompt_l
#         return False

#     def _parse_growth_expectation(self, text):
#         lowered = str(text or "").strip().lower()
#         if not lowered:
#             return None
#         if any(token in lowered for token in {"steady", "stable", "no growth"}):
#             return "steady"
#         if any(token in lowered for token in {"moderate", "grow", "hiring", "expansion"}):
#             return "moderate_growth"
#         if any(token in lowered for token in {"rapid", "fast growth", "aggressive", "scale fast"}):
#             return "rapid_growth"
#         normalized = normalize_growth_expectation(text)
#         return normalized if normalized in {"steady", "moderate_growth", "rapid_growth"} else None

#     def _parse_performance_priority(self, text):
#         lowered = str(text or "").strip().lower()
#         if not lowered:
#             return None
#         for key, aliases in self.PERFORMANCE_PRIORITY_MAP.items():
#             if lowered in aliases or any(alias in lowered for alias in aliases):
#                 return key
#         return None

#     def _attach_turn_metrics(self, payload, turn_metrics, response_type=""):
#         payload = dict(payload or {})
#         payload.setdefault("meta", {})
#         top_level_timings = dict((payload.get("meta") or {}).get("top_level_timings_ms") or {})
#         core_ms = dict(top_level_timings.get("core_ms") or {})
#         presentation_ms = dict(top_level_timings.get("presentation_ms") or {})
#         stage_timings = dict((((payload.get("meta") or {}).get("stage_timings_ms")) or {}))
#         turn_metrics["catalog_fetch_ms"] = round(float(stage_timings.get("catalog_fetch_ms") or turn_metrics.get("catalog_fetch_ms") or 0.0), 2)
#         turn_metrics["policy_ms"] = round(float(stage_timings.get("policy_ms") or turn_metrics.get("policy_ms") or 0.0), 2)
#         turn_metrics["compatibility_ms"] = round(float(stage_timings.get("compatibility_ms") or turn_metrics.get("compatibility_ms") or 0.0), 2)
#         turn_metrics["ranking_ms"] = round(float(stage_timings.get("ranking_ms") or turn_metrics.get("ranking_ms") or 0.0), 2)
#         turn_metrics["presenter_ms"] = round(float(presentation_ms.get("assembly_ms") or turn_metrics.get("presenter_ms") or 0.0), 2)
#         if not turn_metrics.get("recommendation_total_ms"):
#             turn_metrics["recommendation_total_ms"] = round(float(core_ms.get("total_ms") or 0.0), 2)
#         final_metrics = self._finalize_turn_metrics(turn_metrics, response_type=response_type, payload=payload)
#         payload["meta"] = self._merge_meta(
#             payload.get("meta"),
#             {
#                 "turn_metrics": final_metrics,
#             },
#         )
#         return payload

#     def _finalize_turn_metrics(self, turn_metrics, response_type="", payload=None):
#         final_metrics = dict(turn_metrics or {})
#         final_metrics["finished_at"] = datetime.now(timezone.utc).isoformat()
#         final_metrics["total_ms"] = round((perf_counter() - float(final_metrics.pop("_started_perf", perf_counter()))) * 1000, 2)
#         final_metrics["response_type"] = str(response_type or payload.get("response_type") or "").strip()
#         final_metrics["contract_parity_ok"] = self._payload_contract_ok(payload or {})
#         return final_metrics

#     def _build_llm_stats(self):
#         llm_client = getattr(self.planner_service, "llm_client", None)
#         stats = dict(getattr(llm_client, "stats", {}) or {})
#         planner_meta = dict(getattr(self.planner_service, "last_plan_metadata", {}) or {})
#         planner_stats = dict(stats)
#         planner_stats.update(planner_meta)
#         return {
#             "provider": str(getattr(llm_client, "provider", "") or ""),
#             "model": str(getattr(llm_client, "model_name", "") or ""),
#             "available": bool(llm_client.is_available()) if llm_client and hasattr(llm_client, "is_available") else False,
#             "extraction": {},
#             "followup": {},
#             "explanation": {},
#             "planner": planner_stats,
#         }

#     def _merge_meta(self, base, extra):
#         merged = dict(base or {})
#         for key, value in dict(extra or {}).items():
#             if isinstance(merged.get(key), dict) and isinstance(value, dict):
#                 nested = dict(merged.get(key) or {})
#                 nested.update(value)
#                 merged[key] = nested
#             else:
#                 merged[key] = value
#         return merged

#     def _new_turn_metrics(self, transport_session_id, turn_type=""):
#         return {
#             "conversation_id": "",
#             "transport_session_id": self._transport_session_label(transport_session_id),
#             "turn_id": uuid4().hex,
#             "turn_type": str(turn_type or "chat_turn"),
#             "started_at": datetime.now(timezone.utc).isoformat(),
#             "consumer_receive_ms": 0.0,
#             "session_load_ms": 0.0,
#             "planner_prepare_ms": 0.0,
#             "planner_request_ms": 0.0,
#             "planner_total_ms": 0.0,
#             "state_merge_ms": 0.0,
#             "guard_validate_ms": 0.0,
#             "recommendation_total_ms": 0.0,
#             "catalog_fetch_ms": 0.0,
#             "policy_ms": 0.0,
#             "compatibility_ms": 0.0,
#             "ranking_ms": 0.0,
#             "presenter_ms": 0.0,
#             "response_contract_ms": 0.0,
#             "db_persist_ms": 0.0,
#             "channel_send_ms": 0.0,
#             "planner_input_tokens": 0,
#             "planner_output_tokens": 0,
#             "explanation_input_tokens": 0,
#             "explanation_output_tokens": 0,
#             "llm_calls_in_turn": 0,
#             "planner_fallback_used": False,
#             "background_explanation_enqueued": False,
#             "background_explanation_completed": False,
#             "contract_parity_ok": False,
#             "cache_hit": False,
#             "cache_miss": False,
#             "_started_perf": perf_counter(),
#         }

#     def _mark_stage(self, turn_metrics, key, started_at):
#         elapsed_ms = max(round((perf_counter() - started_at) * 1000, 2), 0.0)
#         turn_metrics[key] = round(float(turn_metrics.get(key) or 0.0) + elapsed_ms, 2)

#     def _apply_cache_counters(self, turn_metrics):
#         cache_result = str(getattr(self.chat_session_service, "last_cache_result", "") or "").strip().lower()
#         if cache_result == "hit":
#             turn_metrics["cache_hit"] = True
#         elif cache_result == "miss":
#             turn_metrics["cache_miss"] = True

#     def _apply_planner_metadata(self, turn_metrics):
#         metadata = dict(getattr(self.planner_service, "last_plan_metadata", {}) or {})
#         request_ms = metadata.get("request_ms")
#         if request_ms is not None:
#             turn_metrics["planner_request_ms"] = round(float(request_ms or 0.0), 2)
#         turn_metrics["planner_input_tokens"] = int(metadata.get("input_tokens") or 0)
#         turn_metrics["planner_output_tokens"] = int(metadata.get("output_tokens") or 0)
#         turn_metrics["llm_calls_in_turn"] = int(metadata.get("llm_calls") or 0)
#         turn_metrics["planner_fallback_used"] = bool(metadata.get("fallback_used"))

#     def _payload_contract_ok(self, payload):
#         payload = dict(payload or {})
#         required_keys = {"response", "response_type", "requirements", "readiness", "meta", "llm_stats"}
#         return required_keys.issubset(set(payload.keys()))

#     def _transport_session_label(self, transport_session_id):
#         if hasattr(self.chat_session_service, "_transport_identity"):
#             identity = self.chat_session_service._transport_identity(transport_session_id)
#             return str(identity.get("transport_key") or identity.get("conversation_id") or "").strip()
#         if hasattr(transport_session_id, "channel_name"):
#             return str(getattr(transport_session_id, "channel_name") or "").strip()
#         return str(transport_session_id or "").strip()

#     def _append_runtime_log(self, payload):
#         observability_service = getattr(self.recommendation_service, "observability_service", None)
#         if not observability_service or not hasattr(observability_service, "append_runtime_log"):
#             return
#         payload = dict(payload or {})
#         meta = dict(payload.get("meta") or {})
#         turn_metrics = dict(meta.get("turn_metrics") or {})
#         if not turn_metrics:
#             return
#         observability_service.append_runtime_log(
#             {
#                 "conversation_id": meta.get("conversation_id"),
#                 "response_type": payload.get("response_type"),
#                 "turn_metrics": turn_metrics,
#             }
#         )

import re
from copy import deepcopy
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from ...catalog.services.normalization import (
    get_procurement_normalization_terms,
    normalize_budget_scope,
    normalize_category,
    normalize_categories,
    normalize_growth_expectation,
    normalize_workloads,
    parse_money_value,
    parse_team_size,
)
from ...procurement.services.clarification import default_follow_up_prompt
from ...procurement.services.input_normalization import normalize_purchase_scope
from ...procurement.services.signal_service import ProcurementSignalService
from .ui_guidance import build_narrowing_guidance


class ChatOrchestrator:
    GREETING_TOKENS = {"hi", "hello", "hey", "good morning", "good afternoon", "good evening"}
    ACK_TOKENS = {"ok", "okay", "sure", "fine", "got it", "understood", "thanks", "thank you"}
    ROUTER_CONFIDENCE_THRESHOLD = 0.78
    PERFORMANCE_PRIORITY_MAP = {
        "cost": {"cost", "cheapest", "budget", "value"},
        "balanced": {"balanced", "balance", "normal", "standard"},
        "performance": {"performance", "high performance", "fastest", "premium", "power"},
    }
    WORKLOAD_LABELS = {
        "software_development": "software development",
        "creative_design": "design work",
        "office_productivity": "office productivity",
        "video_editing": "video editing",
        "data_analysis": "data analysis",
        "ai_ml": "AI or ML workloads",
        "ai_analytics": "AI or analytics workloads",
        "server_infrastructure": "server infrastructure",
    }
    APPLICATION_SIGNAL_LABELS = {
        "developer_toolchain": "developer tools",
        "design_suite": "design tools",
        "video_postproduction": "video editing",
        "cad_workstation": "CAD work",
        "ml_toolchain": "AI or ML work",
        "virtualization_stack": "virtualization",
        "branch_networking": "branch networking",
        "business_apps": "business apps",
        "desk_peripherals": "desk accessories",
        "gaming_interactive": "gaming-heavy use",
    }
    OUT_OF_SCOPE_PATTERNS = {
        "sing",
        "song",
        "joke",
        "poem",
        "story",
        "weather",
        "horoscope",
        "translate",
        "summarize this article",
        "set a timer",
        "movie",
        "movies",
        "weed",
    }
    PROCUREMENT_SCENARIO_TERMS = {
        "opening",
        "startup",
        "start up",
        "establishing",
        "setup",
        "set up",
        "office",
        "branch",
        "clinic",
        "hospital",
        "warehouse",
        "school",
        "store",
        "restaurant",
    }
    PROCUREMENT_FOLLOWUP_TERMS = {
        "what about",
        "instead",
        "change to",
        "switch to",
        "different brand",
        "amd",
        "intel",
        "ryzen",
        "nvidia",
        "hp",
        "dell",
        "lenovo",
        "asus",
        "acer",
        "apple",
        "microsoft",
        "logitech",
        "cisco",
        "fortinet",
        "juniper",
        "canon",
        "epson",
        "brother",
        "netgear",
        "tp-link",
    }
    PROCUREMENT_TERMS = {
        "buy",
        "purchase",
        "need",
        "recommend",
        "budget",
        "price",
        "quote",
        "laptop",
        "laptops",
        "desktop",
        "desktops",
        "server",
        "servers",
        "network",
        "networking",
        "printer",
        "printers",
        "accessories",
        "keyboard",
        "mouse",
        "headset",
        "headsets",
        "monitor",
        "monitors",
        "dock",
        "webcam",
        "ram",
        "storage",
        "gpu",
        "cpu",
        "users",
        "seats",
        "team",
    }
    RECOMMENDATION_RECALL_PATTERNS = {
        "what did you recommend",
        "what was the recommendation",
        "what was the shortlist",
        "remind me what you recommended",
        "recommend again",
        "shortlist again",
        "what did you suggest",
    }
    RECOMMENDATION_REFINEMENT_TERMS = {
        "cheaper",
        "more affordable",
        "less expensive",
        "lower budget",
        "cut the budget",
        "make it cheaper",
        "reduce the budget",
    }
    RECOMMENDATION_REFERENCE_TERMS = {
        "recommendation",
        "recommended",
        "shortlist",
        "option",
        "options",
        "suggested",
        "cheaper",
        "refine",
        "change",
        "adjust",
        "compare",
        "again",
    }

    def __init__(
        self,
        chat_session_service,
        planner_service,
        requirement_state_manager,
        requirement_guard_service,
        recommendation_service,
        response_contract_adapter,
        background_dispatcher,
        include_llm_stats=True,
        signal_service=None,
    ):
        self.chat_session_service = chat_session_service
        self.planner_service = planner_service
        self.requirement_state_manager = requirement_state_manager
        self.requirement_guard_service = requirement_guard_service
        self.recommendation_service = recommendation_service
        self.response_contract_adapter = response_contract_adapter
        self.background_dispatcher = background_dispatcher
        self.include_llm_stats = bool(include_llm_stats)
        self.signal_service = signal_service or ProcurementSignalService()

    def start_session(self, transport_session_id, channel="websocket", store_id=""):
        turn_metrics = self._new_turn_metrics(
            transport_session_id=transport_session_id,
            turn_type="welcome",
        )
        allow_transport_resume = True
        # CHANGE: on websocket connect, only resume when conversation_id was explicitly supplied.
        if hasattr(transport_session_id, "scope") and hasattr(self.chat_session_service, "_transport_identity"):
            identity = self.chat_session_service._transport_identity(transport_session_id)
            allow_transport_resume = bool(identity.get("conversation_id"))

        session_started_at = perf_counter()
        session = self.chat_session_service.get_or_create_session(
            transport_session_id=transport_session_id,
            channel=channel,
            store_id=store_id,
            allow_transport_resume=allow_transport_resume,
        )
        self._mark_stage(turn_metrics, "session_load_ms", session_started_at)
        turn_metrics["conversation_id"] = session.conversation_id

        state_started_at = perf_counter()
        state = self.chat_session_service.load_state(session.conversation_id)
        self._mark_stage(turn_metrics, "session_load_ms", state_started_at)
        self._apply_cache_counters(turn_metrics)

        response_started_at = perf_counter()

        startup_requirements_raw = dict((state or {}).get("requirements") or {})
        startup_requirements = {
            "preferred_categories": startup_requirements_raw.get("preferred_categories"),
            "preferred_category": startup_requirements_raw.get("preferred_category"),
            "budget": startup_requirements_raw.get("budget"),
            "budget_scope": startup_requirements_raw.get("budget_scope"),
            "quantity": startup_requirements_raw.get("quantity"),
        }

        payload = {
            "response": None,
            "response_type": "question",
            "next_question": None,
            "requirements": startup_requirements,
            "meta": {
                "conversation_id": session.conversation_id,
                "response_mode": "respond",
            },
            "llm_stats": self._build_llm_stats(),
        }

        self._mark_stage(turn_metrics, "response_contract_ms", response_started_at)

        payload = self._attach_turn_metrics(payload, turn_metrics, response_type="question")

        final_turn_metrics = dict((payload.get("meta") or {}).get("turn_metrics") or {})
        final_turn_metrics = {
            "conversation_id": final_turn_metrics.get("conversation_id"),
            "transport_session_id": final_turn_metrics.get("transport_session_id"),
            "turn_id": final_turn_metrics.get("turn_id"),
            "turn_type": final_turn_metrics.get("turn_type"),
            "started_at": final_turn_metrics.get("started_at"),
            "cache_hit": final_turn_metrics.get("cache_hit"),
            "cache_miss": final_turn_metrics.get("cache_miss"),
            "finished_at": final_turn_metrics.get("finished_at"),
            "total_ms": final_turn_metrics.get("total_ms"),
        }

        payload["meta"] = {
            "conversation_id": session.conversation_id,
            "response_mode": "respond",
            "turn_metrics": final_turn_metrics,
        }

        self._append_runtime_log(payload)
        return session, payload

    def handle_turn(self, transport_session_id, user_message):
        turn_metrics = self._new_turn_metrics(
            transport_session_id=transport_session_id,
            turn_type="chat_turn",
        )
        session_started_at = perf_counter()
        session = self.chat_session_service.get_or_create_session(transport_session_id=transport_session_id)
        self._mark_stage(turn_metrics, "session_load_ms", session_started_at)
        turn_metrics["conversation_id"] = session.conversation_id

        state_started_at = perf_counter()
        state = self.chat_session_service.load_state(session.conversation_id)
        planner_recent_messages = self.chat_session_service.planner_recent_messages(session.conversation_id)
        self._mark_stage(turn_metrics, "session_load_ms", state_started_at)
        self._apply_cache_counters(turn_metrics)

        import json
        is_refinement = False
        refinement_changes = {}
        if isinstance(user_message, dict) and user_message.get("refinement_flag") is True:
            if str(user_message.get("session_id", "")) == session.conversation_id:
                is_refinement = True
                refinement_changes = user_message.get("changes") or {}
                refinement_changes["budget_scope"] = "per_unit"
            user_message_str = json.dumps(user_message)
        else:
            user_message_str = str(user_message)

        persist_started_at = perf_counter()
        self.chat_session_service.append_message(
            session.conversation_id,
            role="user",
            content=user_message_str,
            message_type="info",
        )
        self._mark_stage(turn_metrics, "db_persist_ms", persist_started_at)

        if is_refinement:
            updated_state = deepcopy(state or {})
            merged_requirements = self.requirement_state_manager.merge_requirement_patch(
                dict(updated_state.get("requirements") or {}),
                refinement_changes,
                source="refinement_override",
            )
            for k, v in refinement_changes.items():
                merged_requirements[k] = v

            updated_state["requirements"] = merged_requirements
            
            validated = self.requirement_guard_service.validate(merged_requirements)
            updated_state["requirements"] = dict(validated.get("requirements") or merged_requirements)
            
            planner_output = {
                "action": "recommend" if validated.get("is_ready") else "ask_question",
                "assistant_message": "Got it. I'm updating the options based on your new preferences." if validated.get("is_ready") else "I've updated your preferences.",
                "state_patch": refinement_changes,
                "question_target_field": "",
                "corrections": [],
                "should_trigger_recommendation": bool(validated.get("is_ready")),
                "intent_groups": [],
                "confidence": 1.0,
            }
            if not planner_output["should_trigger_recommendation"]:
                planner_output["question_target_field"] = self._resolve_question_target_field(validated, planner_output)

            updated_state = self._update_conversation_meta(updated_state, planner_output, validated)

            persist_started_at = perf_counter()
            self.chat_session_service.save_state(session.conversation_id, updated_state)
            self._mark_stage(turn_metrics, "db_persist_ms", persist_started_at)

            if planner_output["should_trigger_recommendation"]:
                return self._build_recommendation_response(
                    session=session,
                    updated_state=updated_state,
                    validated=validated,
                    turn_metrics=turn_metrics,
                )

            return self._build_non_recommendation_response(
                session=session,
                updated_state=updated_state,
                validated=validated,
                planner_output=planner_output,
                turn_metrics=turn_metrics,
            )

        current_requirements = dict((state or {}).get("requirements") or {})
        guard_started_at = perf_counter()
        readiness_result = self.requirement_guard_service.validate(current_requirements)
        self._mark_stage(turn_metrics, "guard_validate_ms", guard_started_at)

        recommendation_followup = self._try_recommendation_followup_turn(
            user_message=user_message,
            state=state,
            readiness_result=readiness_result,
        )
        if recommendation_followup is not None:
            updated_state = recommendation_followup["state"]
            validated = recommendation_followup["validated"]
            planner_output = recommendation_followup["planner_output"]

            persist_started_at = perf_counter()
            self.chat_session_service.save_state(session.conversation_id, updated_state)
            self._mark_stage(turn_metrics, "db_persist_ms", persist_started_at)

            if self._should_trigger_recommendation(planner_output, validated):
                return self._build_recommendation_response(
                    session=session,
                    updated_state=updated_state,
                    validated=validated,
                    turn_metrics=turn_metrics,
                )

            return self._build_non_recommendation_response(
                session=session,
                updated_state=updated_state,
                validated=validated,
                planner_output=planner_output,
                turn_metrics=turn_metrics,
            )

        shortcut_turn = self._try_shortcut_turn(
            user_message=user_message,
            state=state,
            readiness_result=readiness_result,
            planner_recent_messages=planner_recent_messages,
        )
        if shortcut_turn is not None:
            updated_state = shortcut_turn["state"]
            validated = shortcut_turn["validated"]
            planner_output = shortcut_turn["planner_output"]

            persist_started_at = perf_counter()
            self.chat_session_service.save_state(session.conversation_id, updated_state)
            self._mark_stage(turn_metrics, "db_persist_ms", persist_started_at)

            if self._should_trigger_recommendation(planner_output, validated):
                return self._build_recommendation_response(
                    session=session,
                    updated_state=updated_state,
                    validated=validated,
                    turn_metrics=turn_metrics,
                )

            return self._build_non_recommendation_response(
                session=session,
                updated_state=updated_state,
                validated=validated,
                planner_output=planner_output,
                turn_metrics=turn_metrics,
            )

        planner_prepare_started_at = perf_counter()
        extracted_turn_patch = {}
        planner_state = deepcopy(state or {})
        if not self._is_non_procurement_turn(user_message, state):
            extracted_turn_patch = self._build_requirement_patch_from_text(user_message, state)
            if extracted_turn_patch:
                merged_for_planner = self.requirement_state_manager.merge_requirement_patch(
                    dict(planner_state.get("requirements") or {}),
                    extracted_turn_patch,
                    source="turn_extraction_preview",
                )
                planner_state["requirements"] = merged_for_planner
        planner_inputs = {
            "user_message": user_message,
            "state": self._planner_state(planner_state),
            "recent_messages": planner_recent_messages,
            "readiness": dict(readiness_result.get("readiness") or {}),
            "current_recommendations": self._current_recommendations(state),
        }
        self._mark_stage(turn_metrics, "planner_prepare_ms", planner_prepare_started_at)

        planner_started_at = perf_counter()
        planner_output = self.planner_service.plan_turn(**planner_inputs)
        self._mark_stage(turn_metrics, "planner_total_ms", planner_started_at)
        self._apply_planner_metadata(turn_metrics)

        planner_output = self._apply_planner_safety_overrides(
            user_message=user_message,
            state=state,
            planner_output=planner_output,
            readiness_result=readiness_result,
        )

        planner_output = self._augment_planner_output_with_extracted_patch(
            user_message=user_message,
            state=state,
            planner_output=planner_output,
            extracted_patch=extracted_turn_patch,
        )

        merge_started_at = perf_counter()
        updated_state = self.requirement_state_manager.apply_patch(state, planner_output)
        self._mark_stage(turn_metrics, "state_merge_ms", merge_started_at)

        updated_requirements = dict(updated_state.get("requirements") or {})
        guard_started_at = perf_counter()
        validated = self.requirement_guard_service.validate(updated_requirements)
        self._mark_stage(turn_metrics, "guard_validate_ms", guard_started_at)
        updated_state["requirements"] = dict(validated.get("requirements") or updated_requirements)
        planner_output["question_target_field"] = self._resolve_question_target_field(validated, planner_output)
        should_trigger_recommendation = self._should_trigger_recommendation(planner_output, validated)
        if not should_trigger_recommendation:
            planner_output = self._normalize_non_recommendation_planner_output(
                planner_output=planner_output,
                validated=validated,
                updated_state=updated_state,
            )
        updated_state = self._update_conversation_meta(updated_state, planner_output, validated)

        persist_started_at = perf_counter()
        self.chat_session_service.save_state(session.conversation_id, updated_state)
        self._mark_stage(turn_metrics, "db_persist_ms", persist_started_at)

        if should_trigger_recommendation:
            return self._build_recommendation_response(
                session=session,
                updated_state=updated_state,
                validated=validated,
                turn_metrics=turn_metrics,
            )

        return self._build_non_recommendation_response(
            session=session,
            updated_state=updated_state,
            validated=validated,
            planner_output=planner_output,
            turn_metrics=turn_metrics,
        )

    def reset_session(self, transport_session_id):
        # CHANGE: websocket restart should rotate to a brand-new conversation_id.
        if hasattr(transport_session_id, "scope"):
            session = self.chat_session_service.get_or_create_session(transport_session_id=transport_session_id)
            rotated_session = self.chat_session_service.rotate_session(
                transport_session_id=transport_session_id,
                channel=session.channel,
                store_id=session.store_id,
                user_id=session.user_id,
                business_id=session.business_id,
            )
            _, payload = self.start_session(
                {
                    "conversation_id": rotated_session.conversation_id,
                    "transport_key": rotated_session.transport_session_key,
                },
                channel=rotated_session.channel,
                store_id=rotated_session.store_id,
            )
            return {"conversation_id": rotated_session.conversation_id, "payload": payload}

        session = self.chat_session_service.get_or_create_session(transport_session_id=transport_session_id)
        self.chat_session_service.reset_session(session.conversation_id)
        _, payload = self.start_session(transport_session_id, channel=session.channel, store_id=session.store_id)
        return {"conversation_id": session.conversation_id, "payload": payload}

    def close_session(self, transport_session_id):
        session = self.chat_session_service.get_or_create_session(transport_session_id=transport_session_id)
        self.chat_session_service.close_session(session.conversation_id)

    def _current_recommendations(self, state):
        memory = self._recommendation_memory(state)
        return list(memory.get("recommendations") or [])

    def _recommendation_memory(self, state):
        return dict((state or {}).get("recommendation_memory") or {})

    def _planner_recommendation_memory(self, state):
        memory = self._recommendation_memory(state)
        if not memory:
            return {}
        return {
            "decision_trace_id": str(memory.get("decision_trace_id") or "").strip(),
            "summary": str(memory.get("summary") or "").strip(),
            "response": str(memory.get("response") or "").strip(),
            "refinement_prompt": str(memory.get("refinement_prompt") or "").strip(),
            "recommendation_mode": str(memory.get("recommendation_mode") or "").strip(),
            "recommendations": list(memory.get("recommendations") or []),
        }

    def _try_recommendation_followup_turn(self, user_message, state, readiness_result):
        text = str(user_message or "").strip()
        lowered = text.lower()
        memory = self._recommendation_memory(state)
        if not text or not memory:
            return None

        if self._is_recommendation_recall_request(lowered):
            planner_output = {
                "action": "respond",
                "assistant_message": self._build_recommendation_recap(memory),
                "state_patch": {},
                "question_target_field": "",
                "corrections": [],
                "should_trigger_recommendation": False,
                "intent_groups": [],
                "confidence": 0.94,
            }
            updated_state = self._update_conversation_meta(deepcopy(state or {}), planner_output, readiness_result)
            return {
                "state": updated_state,
                "validated": readiness_result,
                "planner_output": planner_output,
            }

        followup_patch = self._recommendation_followup_patch(text, state)
        if followup_patch:
            updated_state = deepcopy(state or {})
            merged_requirements = self.requirement_state_manager.merge_requirement_patch(
                dict(updated_state.get("requirements") or {}),
                followup_patch,
                source="recommendation_followup",
            )
            updated_state["requirements"] = merged_requirements
            validated = self.requirement_guard_service.validate(merged_requirements)
            updated_state["requirements"] = dict(validated.get("requirements") or merged_requirements)
            planner_output = {
                "action": "recommend" if validated.get("is_ready") else "ask_question",
                "assistant_message": "Got it. I will update the shortlist with that requirement now.",
                "state_patch": followup_patch,
                "question_target_field": "",
                "corrections": [],
                "should_trigger_recommendation": bool(validated.get("is_ready")),
                "intent_groups": [],
                "confidence": 0.92,
            }
            planner_output["question_target_field"] = self._resolve_question_target_field(validated, planner_output)
            updated_state = self._update_conversation_meta(updated_state, planner_output, validated)
            return {
                "state": updated_state,
                "validated": validated,
                "planner_output": planner_output,
            }

        if any(term in lowered for term in self.RECOMMENDATION_REFINEMENT_TERMS):
            requirements = dict((state or {}).get("requirements") or {})
            budget = self._extract_budget_value(text)
            if budget is None:
                planner_output = {
                    "action": "ask_question",
                    "assistant_message": self._budget_refinement_prompt(requirements),
                    "state_patch": {},
                    "question_target_field": "budget",
                    "question_target_locked": True,
                    "corrections": [],
                    "should_trigger_recommendation": False,
                    "intent_groups": [],
                    "confidence": 0.9,
                }
                updated_state = self._update_conversation_meta(deepcopy(state or {}), planner_output, readiness_result)
                return {
                    "state": updated_state,
                    "validated": readiness_result,
                    "planner_output": planner_output,
                }

            quantity = requirements.get("quantity") or requirements.get("team_size")
            budget_scope = normalize_budget_scope(
                requirements.get("budget_scope"),
                preferred_categories=requirements.get("preferred_categories"),
                hint_text=text,
                quantity=quantity,
            ) or requirements.get("budget_scope")
            patch = {"budget": budget}
            if budget_scope:
                patch["budget_scope"] = budget_scope

            updated_state = deepcopy(state or {})
            merged_requirements = self.requirement_state_manager.merge_requirement_patch(
                dict(updated_state.get("requirements") or {}),
                patch,
                source="recommendation_followup",
            )
            updated_state["requirements"] = merged_requirements
            validated = self.requirement_guard_service.validate(merged_requirements)
            updated_state["requirements"] = dict(validated.get("requirements") or merged_requirements)
            planner_output = {
                "action": "recommend" if validated.get("is_ready") else "ask_question",
                "assistant_message": "Got it. I will re-rank the shortlist for the lower budget now.",
                "state_patch": patch,
                "question_target_field": "budget",
                "corrections": [],
                "should_trigger_recommendation": bool(validated.get("is_ready")),
                "intent_groups": [],
                "confidence": 0.92,
            }
            planner_output["question_target_field"] = self._resolve_question_target_field(validated, planner_output)
            updated_state = self._update_conversation_meta(updated_state, planner_output, validated)
            return {
                "state": updated_state,
                "validated": validated,
                "planner_output": planner_output,
            }

        return None

    def _recommendation_followup_patch(self, text, state):
        patch = self._build_requirement_patch_from_text(text, state)
        if not patch:
            return {}
        followup_fields = {
            "requested_ram_gb",
            "requested_ram_is_minimum",
            "requested_storage_gb",
            "requested_storage_is_minimum",
        }
        followup_patch = {
            field: value
            for field, value in patch.items()
            if field in followup_fields
        }
        if followup_patch.get("requested_ram_gb") is not None:
            followup_patch["requested_ram_is_minimum"] = True
        if followup_patch.get("requested_storage_gb") is not None:
            followup_patch["requested_storage_is_minimum"] = True
        return followup_patch

    def _is_recommendation_recall_request(self, lowered):
        lowered = str(lowered or "").strip().lower()
        return any(pattern in lowered for pattern in self.RECOMMENDATION_RECALL_PATTERNS)

    def _is_recommendation_followup_turn(self, lowered, state):
        lowered = str(lowered or "").strip().lower()
        if not lowered or not self._recommendation_memory(state):
            return False
        if self._is_recommendation_recall_request(lowered):
            return True
        return any(term in lowered for term in self.RECOMMENDATION_REFERENCE_TERMS)

    def _budget_refinement_prompt(self, requirements):
        requirements = dict(requirements or {})
        quantity = requirements.get("quantity") or requirements.get("team_size")
        scope = str(requirements.get("budget_scope") or "").strip().lower()
        if scope == "project_total" or (not scope and quantity and int(quantity or 0) > 1):
            return "Sure. What lower total budget should I use for the revised shortlist?"
        return "Sure. What lower per-unit budget should I use for the revised shortlist?"

    def _build_recommendation_recap(self, memory):
        memory = dict(memory or {})
        names = [
            str(item.get("name") or "").strip()
            for item in list(memory.get("recommendations") or [])
            if str(item.get("name") or "").strip()
        ]
        summary = str(memory.get("summary") or "").strip()
        refinement_prompt = str(memory.get("refinement_prompt") or "").strip()
        if names:
            if len(names) == 1:
                names_text = names[0]
            elif len(names) == 2:
                names_text = f"{names[0]} and {names[1]}"
            else:
                names_text = ", ".join(names[:-1]) + f", and {names[-1]}"
            response = f"The latest shortlist was {names_text}."
        else:
            response = "I still have the latest procurement shortlist in context."
        if summary:
            response = f"{response} {summary}"
        if refinement_prompt:
            response = f"{response} {refinement_prompt}"
        return response.strip()

    def _apply_planner_safety_overrides(self, user_message, state, planner_output, readiness_result=None):
        planner_output = dict(planner_output or {})
        action = str(planner_output.get("action") or "").strip()
        assistant_message = str(planner_output.get("assistant_message") or "").strip()
        if not self._is_non_procurement_turn(user_message, state):
            return planner_output
        if action == "recommend":
            return {
                "action": "respond",
                "assistant_message": self._scope_message(active_brief=bool((state or {}).get("requirements"))),
                "state_patch": {},
                "question_target_field": "",
                "corrections": [],
                "should_trigger_recommendation": False,
                "intent_groups": list(planner_output.get("intent_groups") or []),
                "confidence": max(float(planner_output.get("confidence") or 0.0), 0.9),
            }
        if action in {"ask_question", "clarify"} and not assistant_message:
            planner_output["action"] = "respond"
            planner_output["assistant_message"] = self._scope_message(active_brief=bool((state or {}).get("requirements")))
            planner_output["question_target_field"] = ""
            planner_output["should_trigger_recommendation"] = False
        return planner_output

    def _augment_planner_output_with_extracted_patch(self, user_message, state, planner_output, extracted_patch=None):
        planner_output = dict(planner_output or {})
        if self._is_non_procurement_turn(user_message, state):
            return planner_output

        merged_patch = dict(planner_output.get("state_patch") or {})
        corrected_fields = {
            str(item.get("field") or "").strip()
            for item in list(planner_output.get("corrections") or [])
            if str(item.get("field") or "").strip()
        }

        candidate_patch = dict(extracted_patch or {})
        if not candidate_patch:
            candidate_patch = self._build_requirement_patch_from_text(user_message, state)

        current_requirements = dict((state or {}).get("requirements") or {})
        readiness_result = self.requirement_guard_service.validate(current_requirements)
        binding = self._bind_direct_answer(
            user_message=user_message,
            state=state,
            readiness_result=readiness_result,
            planner_recent_messages=[],
        )
        if binding:
            for field, value in dict(binding.get("state_patch") or {}).items():
                candidate_patch.setdefault(field, value)
            if not str(planner_output.get("question_target_field") or "").strip() and binding.get("question_target_field"):
                planner_output["question_target_field"] = str(binding.get("question_target_field") or "").strip()

        for field, value in candidate_patch.items():
            if field in merged_patch or field in corrected_fields:
                continue
            merged_patch[field] = value

        candidate_intent_groups = list(candidate_patch.get("intent_groups") or [])
        if candidate_intent_groups and not list(planner_output.get("intent_groups") or []):
            planner_output["intent_groups"] = candidate_intent_groups

        if merged_patch:
            planner_output["state_patch"] = merged_patch
            if not str(planner_output.get("question_target_field") or "").strip():
                planner_output["question_target_field"] = self._next_priority_after_binding(merged_patch, current_requirements)
        return planner_output

    def _build_requirement_patch_from_text(self, user_message, state):
        current_requirements = dict((state or {}).get("requirements") or {})
        text = str(user_message or "").strip()
        patch = {}
        extracted_schema = {}
        last_asked_field = str(((state or {}).get("conversation_meta") or {}).get("last_asked_field") or "").strip()

        extraction_service = getattr(self.recommendation_service, "extraction_service", None)
        intake_service = getattr(self.recommendation_service, "intake_service", None)
        if extraction_service and intake_service:
            try:
                extracted_schema = dict(extraction_service.extract(text, context=current_requirements) or {})
                normalized_payload = extraction_service.build_procurement_payload(
                    extracted_schema,
                    base_payload=current_requirements,
                )
                normalized_requirements = intake_service.normalize(normalized_payload)
                extracted_schema = dict(normalized_requirements or extracted_schema)
                patch.update(self._diff_requirements(current_requirements, normalized_requirements))
            except Exception:
                extracted_schema = {}

        categories = normalize_categories([text])
        category = normalize_category(text)
        if category and category not in categories:
            categories.insert(0, category)
        if categories:
            merged_categories = self._merge_categories(list(current_requirements.get("preferred_categories") or []), categories)
            patch.setdefault("preferred_categories", merged_categories)
            patch.setdefault("preferred_category", merged_categories[0])

        signals = self.signal_service.extract(text)
        workload_values = self._dedupe_strings(
            list(patch.get("workloads") or [])
            + list(current_requirements.get("workloads") or [])
            + normalize_workloads([text])
            + list(signals.get("workload_types") or [])
        )
        if workload_values:
            patch["workloads"] = workload_values
        application_values = self._dedupe_strings(
            list(patch.get("application_signals") or [])
            + list(current_requirements.get("application_signals") or [])
            + list(signals.get("application_signals") or [])
        )
        if application_values:
            patch["application_signals"] = application_values
        capability_values = self._dedupe_strings(
            list(patch.get("capability_tags") or [])
            + list(current_requirements.get("capability_tags") or [])
            + list(signals.get("capability_tags") or [])
        )
        if capability_values:
            patch["capability_tags"] = capability_values

        budget = None
        if self._looks_like_budget_reply(text, last_asked_field=last_asked_field):
            budget = self._extract_budget_value(text)
        if budget is not None and current_requirements.get("budget") != budget:
            patch.setdefault("budget", budget)
            budget_scope = normalize_budget_scope(
                current_requirements.get("budget_scope"),
                preferred_categories=patch.get("preferred_categories") or current_requirements.get("preferred_categories"),
                hint_text=text,
                quantity=current_requirements.get("quantity") or current_requirements.get("team_size"),
            )
            if budget_scope:
                patch.setdefault("budget_scope", budget_scope)

        team_size = parse_team_size(text)
        if team_size is not None and team_size > 0:
            lowered = text.lower()
            headcount_terms = set(get_procurement_normalization_terms("quantity_units", default=set()) or set())
            headcount_terms.update({"company", "headcount", "users", "people", "staff", "employees", "team"})
            if any(term in lowered for term in headcount_terms):
                if current_requirements.get("team_size") != team_size:
                    patch.setdefault("team_size", team_size)
                if current_requirements.get("quantity") != team_size:
                    patch.setdefault("quantity", team_size)

        multi_intent_service = getattr(self.recommendation_service, "multi_intent_service", None)
        if multi_intent_service and text:
            try:
                preview_requirements = dict(current_requirements)
                preview_requirements.update(dict(patch))
                detection_payload = dict(preview_requirements)
                detection_payload["chat_text"] = text
                detection_payload["raw_chat"] = text
                multi_intent_result = multi_intent_service.detect(detection_payload, extracted_schema or preview_requirements)
                if multi_intent_result.get("is_multi_intent"):
                    intent_groups = self._normalize_multi_intent_groups_for_state(multi_intent_result)
                    if intent_groups:
                        categories_from_groups = [
                            normalize_category(group.get("preferred_category") or group.get("category"))
                            for group in intent_groups
                            if normalize_category(group.get("preferred_category") or group.get("category"))
                        ]
                        merged_categories = self._merge_categories(
                            list(preview_requirements.get("preferred_categories") or []),
                            categories_from_groups,
                        )
                        if merged_categories:
                            patch["preferred_categories"] = merged_categories
                            patch["preferred_category"] = merged_categories[0]
                        patch["intent_groups"] = intent_groups
            except Exception:
                pass

        filtered_patch = {}
        for field, value in patch.items():
            if not self._has_meaningful_value(value):
                continue
            if current_requirements.get(field) == value:
                continue
            filtered_patch[field] = value
        return filtered_patch

    def _diff_requirements(self, current_requirements, normalized_requirements):
        current_requirements = dict(current_requirements or {})
        normalized_requirements = dict(normalized_requirements or {})
        ignored_fields = {
            "assumption_severity",
            "channel",
            "currency",
            "field_source",
            "field_state",
            "notes",
            "ranking_persona",
            "raw_chat",
            "review_state",
            "store_id",
        }
        patch = {}
        for field, value in normalized_requirements.items():
            if field in ignored_fields:
                continue
            if not self._has_meaningful_value(value):
                continue
            if current_requirements.get(field) == value:
                continue
            patch[field] = value
        return patch

    def _has_meaningful_value(self, value):
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, set, dict)):
            return bool(value)
        return True

    def _should_trigger_recommendation(self, planner_output, validated):
        planner_output = dict(planner_output or {})
        readiness = dict((validated or {}).get("readiness") or {})
        action = str(planner_output.get("action") or "").strip()
        if action == "respond" and not planner_output.get("should_trigger_recommendation"):
            return False
        if bool((validated or {}).get("is_ready")):
            return True
        if action in {"ask_question", "clarify"} and not planner_output.get("should_trigger_recommendation"):
            return False
        if not planner_output.get("should_trigger_recommendation"):
            return False
        routing_recommendation = str(readiness.get("routing_recommendation") or "").strip()
        return routing_recommendation in {
            "recommend_now",
            "recommend_with_one_refinement",
            "recommend_with_optional_refinement",
        }

    def _try_llm_light_turn(self, user_message, state, readiness_result, planner_recent_messages):
        route_result = self.planner_service.route_turn(
            user_message=user_message,
            state=self._planner_state(state),
            recent_messages=planner_recent_messages,
            readiness=dict((readiness_result or {}).get("readiness") or {}),
            current_recommendations=self._current_recommendations(state),
        )
        if not route_result:
            return None

        route = str(route_result.get("route") or "").strip().lower()
        confidence = float(route_result.get("confidence") or 0.0)
        if route == "planner" or confidence < self.ROUTER_CONFIDENCE_THRESHOLD:
            return None

        if route == "direct_answer":
            binding = self._bind_direct_answer(
                user_message=str(user_message or "").strip(),
                state=state,
                readiness_result=readiness_result,
                planner_recent_messages=planner_recent_messages,
            )
            if not binding:
                return None
            return self._apply_direct_answer_binding(binding, state, readiness_result)

        message = str(route_result.get("assistant_message") or "").strip()
        question_target_field = str(route_result.get("question_target_field") or "").strip()
        if route == "out_of_scope":
            planner_output = {
                "action": "respond",
                "assistant_message": message or self._scope_message(active_brief=bool((state or {}).get("requirements"))),
                "state_patch": {},
                "question_target_field": "",
                "corrections": [],
                "should_trigger_recommendation": False,
                "intent_groups": [],
                "confidence": confidence,
            }
            updated_state = self._update_conversation_meta(deepcopy(state or {}), planner_output, readiness_result)
            return {"state": updated_state, "validated": readiness_result, "planner_output": planner_output}

        planner_output = {
            "action": "respond",
            "assistant_message": message,
            "state_patch": {},
            "question_target_field": question_target_field,
            "corrections": [],
            "should_trigger_recommendation": False,
            "intent_groups": [],
            "confidence": confidence,
        }
        if question_target_field:
            safe_next_question = self._safe_next_question(
                validated=readiness_result,
                planner_output={"question_target_field": question_target_field},
                updated_state=state,
            )
            if safe_next_question:
                planner_output["action"] = "ask_question"
                if not planner_output["assistant_message"]:
                    planner_output["assistant_message"] = safe_next_question
        if not planner_output["assistant_message"]:
            planner_output["assistant_message"] = "Got it."
        updated_state = self._update_conversation_meta(deepcopy(state or {}), planner_output, readiness_result)
        return {"state": updated_state, "validated": readiness_result, "planner_output": planner_output}

    def _apply_direct_answer_binding(self, binding, state, readiness_result):
        updated_state = deepcopy(state or {})
        current_requirements = dict(updated_state.get("requirements") or {})
        current_requirements = self.requirement_state_manager.resolve_corrections(
            current_requirements,
            binding.get("corrections"),
            source="direct_answer_binder",
        )
        current_requirements = self.requirement_state_manager.merge_requirement_patch(
            current_requirements,
            binding.get("state_patch"),
            source="direct_answer_binder",
        )
        updated_state["requirements"] = current_requirements
        validated = self.requirement_guard_service.validate(current_requirements)
        updated_state["requirements"] = dict(validated.get("requirements") or current_requirements)
        resolved_question_target_field = self._resolve_question_target_field(
            validated,
            {"question_target_field": binding.get("question_target_field")},
        )

        response = self._build_bound_response(
            binding,
            validated,
            planner_output={"question_target_field": resolved_question_target_field},
            updated_state=updated_state,
        )
        planner_output = {
            "action": (
                "recommend"
                if validated.get("is_ready")
                else (
                    "ask_question"
                    if self._safe_next_question(
                        validated,
                        {"question_target_field": resolved_question_target_field},
                        updated_state,
                    )
                    else "respond"
                )
            ),
            "assistant_message": response,
            "state_patch": binding.get("state_patch") or {},
            "question_target_field": resolved_question_target_field,
            "corrections": list(binding.get("corrections") or []),
            "should_trigger_recommendation": bool(validated.get("is_ready")),
            "intent_groups": [],
            "confidence": float(binding.get("confidence") or 0.86),
        }
        updated_state = self._update_conversation_meta(updated_state, planner_output, validated)
        return {"state": updated_state, "validated": validated, "planner_output": planner_output}

    def _try_scope_guard_turn(self, user_message, state, readiness_result):
        text = str(user_message or "").strip()
        if not self._is_non_procurement_turn(text, state):
            return None
        planner_output = {
            "action": "respond",
            "assistant_message": self._scope_message(active_brief=bool((state or {}).get("requirements"))),
            "state_patch": {},
            "question_target_field": "",
            "corrections": [],
            "should_trigger_recommendation": False,
            "intent_groups": [],
            "confidence": 0.95,
        }
        updated_state = self._update_conversation_meta(deepcopy(state or {}), planner_output, readiness_result)
        return {
            "state": updated_state,
            "validated": readiness_result,
            "planner_output": planner_output,
        }

    def _is_non_procurement_turn(self, user_message, state):
        text = str(user_message or "").strip().lower()
        if not text:
            return False
        if self._is_recommendation_followup_turn(text, state):
            return False
        if any(pattern in text for pattern in self.OUT_OF_SCOPE_PATTERNS):
            return True
        categories = normalize_categories([text])
        workloads = normalize_workloads([text])
        signals = self.signal_service.extract(text)
        has_procurement_signal = bool(
            categories
            or workloads
            or signals.get("application_signals")
            or signals.get("capability_tags")
            or any(term in text for term in self.PROCUREMENT_TERMS)
            or parse_money_value(text) is not None
            or parse_team_size(text) is not None
        )
        if has_procurement_signal:
            return False
        current_requirements = dict((state or {}).get("requirements") or {})
        if not current_requirements:
            return False
        non_procurement_starts = (
            text.startswith("can you ")
            or text.startswith("could you ")
            or text.startswith("write ")
            or text.startswith("tell me a ")
        )
        return non_procurement_starts

    def _scope_message(self, active_brief=False):
        if active_brief:
            return (
                "I can help with procurement for laptops, desktops, servers, networking, printers, and accessories. "
                "Tell me what you want to buy or how you want to refine the current recommendation."
            )
        return (
            "I can help with procurement for laptops, desktops, servers, networking, printers, and accessories like keyboards, mouse, and headsets. "
            "Tell me what you need to buy, who it is for, and your budget."
        )

    def _is_greeting_turn(self, lowered_text):
        text = str(lowered_text or "").strip().lower()
        if not text:
            return False
        if text in self.GREETING_TOKENS:
            return True
        return bool(re.match(r"^(hi|hello|hey|good\s+morning|good\s+afternoon|good\s+evening)(?:\b|[!,. ])", text))

    def _is_ack_turn(self, lowered_text):
        text = str(lowered_text or "").strip().lower()
        if not text:
            return False
        if text in self.ACK_TOKENS:
            return True
        return bool(re.match(r"^(ok(?:ay)?|sure|thanks?|thank\s+you|got\s+it|understood|go\s+ahead|continue)(?:\b|[!,. ])", text))

    def _try_shortcut_turn(self, user_message, state, readiness_result, planner_recent_messages):
        message_text = str(user_message or "").strip()
        binding = self._bind_direct_answer(
            user_message=message_text,
            state=state,
            readiness_result=readiness_result,
            planner_recent_messages=planner_recent_messages,
        )
        if binding is None:
            return None

        updated_state = deepcopy(state or {})
        current_requirements = dict(updated_state.get("requirements") or {})
        current_requirements = self.requirement_state_manager.resolve_corrections(
            current_requirements,
            binding.get("corrections"),
            source="direct_answer_binder",
        )
        current_requirements = self.requirement_state_manager.merge_requirement_patch(
            current_requirements,
            binding.get("state_patch"),
            source="direct_answer_binder",
        )
        updated_state["requirements"] = current_requirements
        validated = self.requirement_guard_service.validate(current_requirements)
        updated_state["requirements"] = dict(validated.get("requirements") or current_requirements)
        resolved_question_target_field = self._resolve_question_target_field(
            validated,
            {"question_target_field": binding.get("question_target_field")},
        )

        response = self._build_bound_response(
            binding,
            validated,
            planner_output={"question_target_field": resolved_question_target_field},
            updated_state=updated_state,
        )
        planner_output = {
            "action": (
                "recommend"
                if validated.get("is_ready")
                else (
                    "ask_question"
                    if self._safe_next_question(
                        validated,
                        {"question_target_field": resolved_question_target_field},
                        updated_state,
                    )
                    else "respond"
                )
            ),
            "assistant_message": response,
            "state_patch": binding.get("state_patch") or {},
            "question_target_field": resolved_question_target_field,
            "corrections": list(binding.get("corrections") or []),
            "should_trigger_recommendation": bool(validated.get("is_ready")),
            "intent_groups": [],
            "confidence": float(binding.get("confidence") or 0.86),
        }
        updated_state = self._update_conversation_meta(updated_state, planner_output, validated)
        return {
            "state": updated_state,
            "validated": validated,
            "planner_output": planner_output,
        }

    def _bind_direct_answer(self, user_message, state, readiness_result, planner_recent_messages):
        requirements = dict((state or {}).get("requirements") or {})
        conversation_meta = dict((state or {}).get("conversation_meta") or {})
        last_asked_field = str(conversation_meta.get("last_asked_field") or "").strip()
        if not last_asked_field and planner_recent_messages:
            last_assistant = next((msg for msg in reversed(planner_recent_messages) if msg.get("role") == "assistant"), {})
            response_mode = str(last_assistant.get("response_mode") or "").strip()
            if response_mode in {"ask_question", "clarify"}:
                last_asked_field = str(last_assistant.get("question_target_field") or "").strip()

        text = str(user_message or "").strip()
        lowered = text.lower()
        if not text or not last_asked_field or lowered in {"yes", "yeah", "yep", "no", "nope"}:
            return None

        opportunistic_patch = None

        def finalize_binding(state_patch, acknowledgement, confidence):
            nonlocal opportunistic_patch
            if opportunistic_patch is None:
                opportunistic_patch = self._build_requirement_patch_from_text(text, state)
            combined_patch = dict(opportunistic_patch or {})
            combined_patch.update(dict(state_patch or {}))
            return {
                "state_patch": combined_patch,
                "acknowledgement": acknowledgement,
                "question_target_field": self._next_priority_after_binding(combined_patch, requirements),
                "confidence": confidence,
            }

        categories = normalize_categories([text])
        category = normalize_category(text)
        if category and category not in categories:
            categories.insert(0, category)
        existing_categories = list(requirements.get("preferred_categories") or [])
        signal_bundle = self.signal_service.extract(text)
        signal_workloads = list(signal_bundle.get("workload_types") or [])
        new_application_signals = self._dedupe_strings(signal_bundle.get("application_signals") or [])
        new_capability_tags = self._dedupe_strings(signal_bundle.get("capability_tags") or [])
        new_workloads = self._dedupe_strings(normalize_workloads([text]) + signal_workloads)

        if last_asked_field in {"preferred_category", "category_or_workload"}:
            patch = {}
            if categories:
                merged_categories = self._merge_categories(existing_categories, categories)
                patch["preferred_categories"] = merged_categories
                patch["preferred_category"] = merged_categories[0]
            if new_workloads:
                patch["workloads"] = self._dedupe_strings(list(requirements.get("workloads") or []) + new_workloads)
            if new_application_signals:
                patch["application_signals"] = self._dedupe_strings(
                    (requirements.get("application_signals") or []) + new_application_signals
                )
            if new_capability_tags:
                patch["capability_tags"] = self._dedupe_strings(
                    (requirements.get("capability_tags") or []) + new_capability_tags
                )
            if patch:
                if "gaming_interactive" in new_application_signals and not requirements.get("performance_priority"):
                    patch["performance_priority"] = "performance"
                return finalize_binding(
                    patch,
                    self._profile_acknowledgement(patch),
                    0.95,
                )

        if last_asked_field in {"workload_or_application_profile", "application_profile"}:
            patch = {}
            if new_workloads:
                patch["workloads"] = self._dedupe_strings(list(requirements.get("workloads") or []) + new_workloads)
            if new_application_signals:
                patch["application_signals"] = self._dedupe_strings(
                    (requirements.get("application_signals") or []) + new_application_signals
                )
            if new_capability_tags:
                patch["capability_tags"] = self._dedupe_strings(
                    (requirements.get("capability_tags") or []) + new_capability_tags
                )
            if categories:
                merged_categories = self._merge_categories(existing_categories, categories)
                patch["preferred_categories"] = merged_categories
                patch["preferred_category"] = merged_categories[0]
            if patch:
                if "gaming_interactive" in new_application_signals and not requirements.get("performance_priority"):
                    patch["performance_priority"] = "performance"
                return finalize_binding(
                    patch,
                    self._profile_acknowledgement(patch),
                    0.93,
                )

        if last_asked_field == "budget":
            team_size = self._direct_reply_team_size(text)
            if team_size is not None and not self._looks_like_budget_reply(text, last_asked_field=last_asked_field):
                patch = {
                    "team_size": team_size,
                }
                if not requirements.get("quantity") and team_size > 1:
                    patch["quantity"] = team_size
                purchase_scope = normalize_purchase_scope(
                    requirements.get("purchase_scope"),
                    preferred_categories=requirements.get("preferred_categories"),
                    quantity=patch.get("quantity") or requirements.get("quantity") or team_size,
                    team_size=team_size,
                    hint_text=text,
                )
                if purchase_scope:
                    patch["purchase_scope"] = purchase_scope
                return finalize_binding(
                    patch,
                    f"team size {team_size}",
                    0.88,
                )
            if not self._looks_like_budget_reply(text, last_asked_field=last_asked_field):
                return None
            budget = self._extract_budget_value(text)
            if budget is not None:
                scope = normalize_budget_scope(
                    requirements.get("budget_scope"),
                    preferred_categories=requirements.get("preferred_categories"),
                    hint_text=text,
                    quantity=requirements.get("quantity") or requirements.get("team_size"),
                )
                patch = {"budget": budget}
                if scope:
                    patch["budget_scope"] = scope
                return finalize_binding(
                    patch,
                    f"budget {budget}",
                    0.94,
                )

        if last_asked_field == "budget_scope":
            scope = normalize_budget_scope(
                text,
                preferred_categories=requirements.get("preferred_categories"),
                hint_text=text,
                quantity=requirements.get("quantity") or requirements.get("team_size"),
            )
            if scope:
                return finalize_binding(
                    {"budget_scope": scope},
                    "budget scope updated",
                    0.93,
                )

        if last_asked_field in {"team_size", "purchase_scope_or_quantity"}:
            quantity = parse_team_size(text)
            purchase_scope = normalize_purchase_scope(
                requirements.get("purchase_scope"),
                preferred_categories=requirements.get("preferred_categories"),
                quantity=quantity,
                team_size=quantity,
                hint_text=text,
            )
            if quantity is not None or purchase_scope:
                patch = {}
                if quantity is not None:
                    if last_asked_field == "team_size":
                        patch["team_size"] = quantity
                    else:
                        patch["quantity"] = quantity
                        if not requirements.get("team_size") and quantity > 1:
                            patch["team_size"] = quantity
                if purchase_scope:
                    patch["purchase_scope"] = purchase_scope
                return finalize_binding(
                    patch,
                    "scope updated",
                    0.9,
                )

        team_size = self._direct_reply_team_size(text)
        if team_size is not None:
            patch = {"team_size": team_size}
            if not requirements.get("quantity") and team_size > 1:
                patch["quantity"] = team_size
            purchase_scope = normalize_purchase_scope(
                requirements.get("purchase_scope"),
                preferred_categories=requirements.get("preferred_categories"),
                quantity=patch.get("quantity") or requirements.get("quantity") or team_size,
                team_size=team_size,
                hint_text=text,
            )
            if purchase_scope:
                patch["purchase_scope"] = purchase_scope
            return finalize_binding(
                patch,
                f"team size {team_size}",
                0.88,
            )

        if self._looks_like_budget_reply(text, last_asked_field=last_asked_field):
            budget = self._extract_budget_value(text)
            if budget is not None:
                scope = normalize_budget_scope(
                    requirements.get("budget_scope"),
                    preferred_categories=requirements.get("preferred_categories"),
                    hint_text=text,
                    quantity=requirements.get("quantity") or requirements.get("team_size"),
                )
                patch = {"budget": budget}
                if scope:
                    patch["budget_scope"] = scope
                return finalize_binding(
                    patch,
                    f"budget {budget}",
                    0.88,
                )

        if last_asked_field == "growth_expectation":
            growth = self._parse_growth_expectation(text)
            if growth:
                return finalize_binding(
                    {"growth_expectation": growth},
                    growth.replace("_", " "),
                    0.9,
                )

        if last_asked_field == "performance_priority":
            priority = self._parse_performance_priority(text)
            if priority:
                return finalize_binding(
                    {"performance_priority": priority},
                    priority,
                    0.9,
                )

        return None

    def _direct_reply_team_size(self, text):
        lowered = str(text or "").strip().lower()
        if not lowered:
            return None
        quantity = parse_team_size(lowered)
        if quantity is None:
            return None
        headcount_terms = set(get_procurement_normalization_terms("quantity_units", default=set()) or set())
        headcount_terms.update({"company", "headcount"})
        if any(term in lowered for term in headcount_terms):
            return quantity
        return None

    def _extract_budget_value(self, text):
        extraction_service = getattr(self.recommendation_service, "extraction_service", None)
        detector = getattr(extraction_service, "_detect_budget_from_chat", None)
        if callable(detector):
            try:
                budget = detector(text)
                if budget is not None:
                    return budget
            except Exception:
                pass
        return parse_money_value(text)

    def _looks_like_budget_reply(self, text, last_asked_field=""):
        lowered = str(text or "").strip().lower()
        if not lowered:
            return False
        if self._direct_reply_team_size(lowered) is not None:
            return False
        explicit_budget_markers = (
            "budget",
            "rs",
            "inr",
            "usd",
            "eur",
            "gbp",
            "$",
            "₹",
            "lakh",
            "lakhs",
            "thousand",
            "thousands",
            "each",
            "per unit",
            "per device",
            "per seat",
            "per laptop",
            "per desktop",
            "per server",
            "total",
            "overall",
            "project",
            "combined",
            "under ",
            "within ",
        )
        if any(marker in lowered for marker in explicit_budget_markers):
            return True
        if re.search(r"\b\d+(?:\.\d+)?\s*k\b", lowered):
            return True
        compact = lowered.replace(",", "").strip()
        return bool(compact) and compact.replace(".", "", 1).isdigit() and str(last_asked_field or "").strip() == "budget"

    def _normalize_non_recommendation_planner_output(self, planner_output, validated, updated_state):
        planner_output = dict(planner_output or {})
        action = str(planner_output.get("action") or "").strip()
        if action != "recommend":
            return planner_output
        question_target_field = self._resolve_question_target_field(validated, planner_output)
        safe_next_question = self._safe_next_question(
            validated=validated,
            planner_output={"question_target_field": question_target_field},
            updated_state=updated_state,
        )
        if safe_next_question:
            planner_output["action"] = "ask_question"
            planner_output["question_target_field"] = question_target_field
            planner_output["assistant_message"] = safe_next_question
            planner_output["should_trigger_recommendation"] = False
            return planner_output
        planner_output["action"] = "respond"
        planner_output["assistant_message"] = str(planner_output.get("assistant_message") or "").strip() or "Got it."
        planner_output["question_target_field"] = ""
        planner_output["should_trigger_recommendation"] = False
        return planner_output

    def _next_priority_after_binding(self, patch, requirements):
        merged = dict(requirements or {})
        merged.update(dict(patch or {}))
        if not (merged.get("preferred_categories") or merged.get("preferred_category")):
            return "preferred_category"
        if merged.get("budget") is None:
            return "budget"
        if not (merged.get("workloads") or merged.get("application_signals") or merged.get("capability_tags")):
            return "workload_or_application_profile"
        if not (merged.get("team_size") or merged.get("quantity")):
            return "team_size"
        if not merged.get("budget_scope") and ((merged.get("team_size") or merged.get("quantity")) and int(merged.get("team_size") or merged.get("quantity") or 0) > 1):
            return "budget_scope"
        return ""

    def _profile_acknowledgement(self, patch):
        patch = dict(patch or {})
        parts = []
        categories = list(patch.get("preferred_categories") or [])
        workloads = list(patch.get("workloads") or [])
        application_signals = list(patch.get("application_signals") or [])
        if categories:
            parts.append(self._humanize_categories(categories))
        detail_labels = []
        for workload in workloads:
            detail_labels.append(self.WORKLOAD_LABELS.get(workload, str(workload).replace("_", " ")))
        for signal in application_signals:
            detail_labels.append(self.APPLICATION_SIGNAL_LABELS.get(signal, str(signal).replace("_", " ")))
        detail_labels = self._dedupe_strings(detail_labels)
        if detail_labels:
            parts.append(", ".join(detail_labels))
        return " with ".join(parts) if parts else "details updated"

    def _build_bound_response(self, binding, validated, planner_output=None, updated_state=None):
        acknowledgement = str(binding.get("acknowledgement") or "").strip()
        next_question = self._safe_next_question(
            validated=validated,
            planner_output=planner_output,
            updated_state=updated_state,
        )
        if validated.get("is_ready"):
            if acknowledgement:
                return f"Got it — {acknowledgement}. I have enough to put together recommendations now."
            return "Got it. I have enough to put together recommendations now."
        if acknowledgement and next_question:
            return f"Got it — {acknowledgement}. {next_question}"
        if acknowledgement:
            return f"Got it — {acknowledgement}."
        return next_question or "Got it."

    def _build_non_recommendation_response(self, session, updated_state, validated, planner_output, turn_metrics):
        response_mode = str(planner_output.get("action") or "ask_question").strip() or "ask_question"
        response_text = str(planner_output.get("assistant_message") or "").strip()
        question_target_field = self._resolve_question_target_field(validated, planner_output)
        safe_next_question = self._safe_next_question(
            validated=validated,
            planner_output={"question_target_field": question_target_field},
            updated_state=updated_state,
        )
        next_question = ""
        if response_mode == "recommend":
            if safe_next_question:
                response_mode = "ask_question"
            else:
                response_mode = "respond"
        if response_mode in {"ask_question", "clarify"}:
            planner_question_is_usable = bool(
                response_text
                and "?" in response_text
                and (not question_target_field or not self._question_prompt_mismatch(question_target_field, response_text))
            )
            if planner_question_is_usable:
                next_question = response_text
            else:
                acknowledgement = self._extract_acknowledgement_prefix(response_text, safe_next_question)
                next_question = self._polish_clarification_question(
                    question_target_field=question_target_field,
                    canonical_question=safe_next_question,
                    updated_state=updated_state,
                    acknowledgement=acknowledgement,
                )
                if acknowledgement and next_question:
                    response_text = f"{acknowledgement} {next_question}".strip()
                else:
                    response_text = next_question or response_text
            if next_question and not response_text:
                response_text = next_question
        elif not response_text:
            response_text = safe_next_question or "Got it."

        ui_guidance = build_narrowing_guidance(
            dict(updated_state.get("requirements") or {}),
            dict(validated.get("readiness") or {}),
        )
        payload_readiness = dict(validated.get("readiness") or {})
        if response_mode in {"ask_question", "clarify"} and question_target_field:
            payload_readiness["recommended_question_id"] = question_target_field
            if next_question:
                payload_readiness["next_question"] = next_question

        response_started_at = perf_counter()
        payload = self.response_contract_adapter.build_question_payload(
            response=response_text,
            next_question=next_question,
            requirements=dict(updated_state.get("requirements") or {}),
            readiness=payload_readiness,
            extracted_schema=dict(updated_state.get("requirements") or {}),
            ui_guidance=ui_guidance,
            meta={"conversation_id": session.conversation_id},
            llm_stats=self._build_llm_stats(),
            response_mode=response_mode,
        )
        self._mark_stage(turn_metrics, "response_contract_ms", response_started_at)

        persist_started_at = perf_counter()
        self.chat_session_service.append_message(
            session.conversation_id,
            role="assistant",
            content=payload["response"],
            meta={
                "response_mode": response_mode,
                "question_target_field": question_target_field,
            },
            message_type="question",
        )
        self._mark_stage(turn_metrics, "db_persist_ms", persist_started_at)

        payload = self._attach_turn_metrics(payload, turn_metrics, response_type="question")
        self._append_runtime_log(payload)
        return payload

    def _build_recommendation_response(self, session, updated_state, validated, turn_metrics):
        recommendation_started_at = perf_counter()
        state_for_recommendation = dict(updated_state.get("requirements") or {})
        if updated_state.get("intent_groups"):
            state_for_recommendation["intent_groups"] = deepcopy(updated_state.get("intent_groups") or [])
        if not state_for_recommendation.get("raw_chat"):
            brief = str((updated_state.get("conversation_meta") or {}).get("conversation_brief") or "").strip()
            if brief:
                state_for_recommendation["raw_chat"] = brief
        result = self.recommendation_service.recommend_from_state(
            state_for_recommendation,
            persist=False,
        )
        self._mark_stage(turn_metrics, "recommendation_total_ms", recommendation_started_at)

        ui_guidance = build_narrowing_guidance(
            dict(updated_state.get("requirements") or {}),
            dict(validated.get("readiness") or {}),
        )

        ui_state = str(result.get("ui_state_hint") or "").strip()
        blocking_reason_code = str(result.get("blocking_reason_code") or "").strip()
        readiness = dict(result.get("readiness") or {})
        next_question = str(result.get("next_question") or readiness.get("next_question") or "").strip()
        response_text = str(result.get("summary") or result.get("response") or "I found the closest matches for your procurement brief.").strip()

        response_started_at = perf_counter()
        if ui_state in {"clarification_required", "shared_budget_allocation_required", "no_match_found"}:
            payload = self.response_contract_adapter.build_question_payload(
                response=response_text,
                next_question=next_question,
                requirements=result.get("requirements"),
                readiness=readiness,
                extracted_schema=result.get("extracted_schema") or result.get("requirements"),
                ui_guidance=ui_guidance,
                meta=self._merge_meta(result.get("meta"), {"conversation_id": session.conversation_id}),
                llm_stats=self._build_llm_stats(),
                response_mode="ask_question",
                ui_state=ui_state or "clarification_required",
                blocking_reason_code=blocking_reason_code,
            )
            response_type = "question"
            background_enqueued = False
        else:
            recommendation_ui_state = ui_state or (
                "grouped_recommendation_ready" if result.get("recommendation_groups") else "recommendation_ready"
            )
            payload = self.response_contract_adapter.build_recommendation_payload(
                response=response_text,
                decision_trace_id=result.get("decision_trace_id"),
                requirements=result.get("requirements"),
                recommendations=result.get("recommendations"),
                target_profile=result.get("target_profile"),
                assumptions=result.get("assumptions"),
                comparison=result.get("comparison"),
                readiness=readiness,
                ui_guidance=ui_guidance,
                recommendation_context=result.get("recommendation_context"),
                refinement_prompt=result.get("refinement_prompt"),
                review_state=result.get("review_state"),
                check_requirement_summary=result.get("check_requirement_summary"),
                editable_inferred_values=result.get("editable_inferred_values"),
                template_candidates=result.get("template_candidates"),
                recommendation_groups=result.get("recommendation_groups"),
                meta=self._merge_meta(result.get("meta"), {"conversation_id": session.conversation_id}),
                llm_stats=self._build_llm_stats(),
                summary=result.get("summary"),
                ui_state=recommendation_ui_state,
                blocking_reason_code=blocking_reason_code,
            )
            response_type = "recommendation"
            background_enqueued = False
        self._mark_stage(turn_metrics, "response_contract_ms", response_started_at)

        persist_started_at = perf_counter()
        remembered_state = self._remember_recommendation_state(
            updated_state,
            result=result,
            payload=payload,
        )
        self.chat_session_service.save_state(session.conversation_id, remembered_state)
        if response_type == "recommendation":
            self.chat_session_service.mark_recommended(
                session.conversation_id,
                decision_trace_id=payload.get("decision_trace_id"),
            )
        self.chat_session_service.append_message(
            session.conversation_id,
            role="assistant",
            content=payload.get("response") or payload.get("next_question") or "",
            meta={
                "response_mode": "recommend" if response_type == "recommendation" else "ask_question",
                "decision_trace_id": payload.get("decision_trace_id"),
                "ui_state": payload.get("ui_state"),
                "blocking_reason_code": payload.get("blocking_reason_code"),
            },
            message_type="recommendation" if response_type == "recommendation" else "question",
        )
        self._mark_stage(turn_metrics, "db_persist_ms", persist_started_at)

        turn_metrics["background_explanation_enqueued"] = bool(background_enqueued)
        payload = self._attach_turn_metrics(payload, turn_metrics, response_type=response_type)
        self._append_runtime_log(payload)
        return payload

    def _planner_state(self, state):
        state = dict(state or {})
        requirements = dict(state.get("requirements") or {})
        intent_groups = list(state.get("intent_groups") or requirements.get("intent_groups") or [])
        return {
            "requirements": requirements,
            "conversation_meta": dict(state.get("conversation_meta") or {}),
            "intent_groups": intent_groups,
            "recommendation_memory": self._planner_recommendation_memory(state),
        }

    def _build_recommendation_memory(self, result, payload):
        result = dict(result or {})
        payload = dict(payload or {})
        recommendations = []
        for item in list(payload.get("recommendations") or result.get("recommendations") or [])[:3]:
            recommendation = dict(item or {})
            recommendations.append(
                {
                    "name": str(recommendation.get("name") or "").strip(),
                    "fit_status": str(recommendation.get("fit_status") or "").strip(),
                    "price": recommendation.get("price"),
                    "currency": str(recommendation.get("currency") or "").strip(),
                }
            )
        return {
            "decision_trace_id": str(payload.get("decision_trace_id") or result.get("decision_trace_id") or "").strip(),
            "summary": str(payload.get("summary") or result.get("summary") or "").strip(),
            "response": str(payload.get("response") or result.get("response") or "").strip(),
            "refinement_prompt": str(payload.get("refinement_prompt") or result.get("refinement_prompt") or "").strip(),
            "recommendation_mode": str(result.get("recommendation_mode") or payload.get("recommendation_mode") or "").strip(),
            "recommendations": recommendations,
        }

    def _remember_recommendation_state(self, state, result, payload):
        state = deepcopy(state or {})
        result = dict(result or {})
        state["recommendation_memory"] = self._build_recommendation_memory(result, payload)
        state["recommendations"] = list((payload or {}).get("recommendations") or [])
        state["recommendation_context"] = dict((payload or {}).get("recommendation_context") or {})
        state["refinement_prompt"] = str((payload or {}).get("refinement_prompt") or "").strip()
        if result.get("recommendation_groups"):
            state["recommendation_groups"] = deepcopy(result.get("recommendation_groups") or [])
        if state.get("intent_groups"):
            state["intent_groups"] = deepcopy(state.get("intent_groups") or [])
        return self._update_conversation_meta(
            state,
            {
                "action": "recommend",
                "assistant_message": str((payload or {}).get("response") or "").strip(),
                "question_target_field": "",
            },
            {"readiness": dict((payload or {}).get("readiness") or (result or {}).get("readiness") or {})},
        )

    def _resolve_question_target_field(self, validated, planner_output=None):
        planner_output = dict(planner_output or {})
        readiness = dict((validated or {}).get("readiness") or {})
        action = str(planner_output.get("action") or "").strip()
        missing_signals = set(readiness.get("missing_signals") or [])
        locked = bool(planner_output.get("question_target_locked"))
        recommended_field = str(readiness.get("recommended_question_id") or "").strip()
        field = str(planner_output.get("question_target_field") or "").strip()
        canonical_question = str(readiness.get("next_question") or "").strip()
        assistant_message = str(planner_output.get("assistant_message") or "").strip()
        if field:
            if locked:
                return field
            if action not in {"ask_question", "clarify"}:
                return field
            reference_prompt = assistant_message or canonical_question
            if field in missing_signals and (not reference_prompt or not self._question_prompt_mismatch(field, reference_prompt)):
                return field
            if recommended_field and field != recommended_field:
                if field not in missing_signals:
                    return recommended_field
                if reference_prompt and self._question_prompt_mismatch(field, reference_prompt):
                    return recommended_field
                return field
            return field
        if (not field or self._question_prompt_mismatch(field, canonical_question)) and recommended_field:
            field = recommended_field
        return field

    def _extract_acknowledgement_prefix(self, response_text, canonical_question):
        response_text = str(response_text or "").strip()
        canonical_question = str(canonical_question or "").strip()
        if not response_text or not canonical_question:
            return ""
        if "?" in response_text:
            return ""
        if canonical_question in response_text:
            return response_text.split(canonical_question, 1)[0].strip()
        return response_text

    def _polish_clarification_question(self, question_target_field, canonical_question, updated_state=None, acknowledgement=""):
        field = str(question_target_field or "").strip()
        canonical = str(canonical_question or "").strip()
        if not field or not canonical:
            return canonical
        planner_service = getattr(self, "planner_service", None)
        if not planner_service or not hasattr(planner_service, "rephrase_clarification_question"):
            return canonical
        polished = planner_service.rephrase_clarification_question(
            question_target_field=field,
            canonical_question=canonical,
            state=dict(updated_state or {}),
            acknowledgement=str(acknowledgement or "").strip(),
        )
        polished = str(polished or "").strip()
        if not polished or self._question_prompt_mismatch(field, polished):
            return canonical
        return polished

    def _update_conversation_meta(self, state, planner_output, validated):
        state = deepcopy(state or {})
        conversation_meta = dict(state.get("conversation_meta") or {})
        action = str((planner_output or {}).get("action") or "").strip()
        question_target_field = str((planner_output or {}).get("question_target_field") or "").strip()
        assistant_message = str((planner_output or {}).get("assistant_message") or "").strip()
        readiness = dict((validated or {}).get("readiness") or {})
        requirements = dict(state.get("requirements") or {})

        if action in {"ask_question", "clarify"}:
            conversation_meta["last_asked_field"] = question_target_field or str(readiness.get("recommended_question_id") or "").strip()
            conversation_meta["recommended_question_id"] = (
                question_target_field or str(readiness.get("recommended_question_id") or "").strip()
            )
        elif action == "recommend":
            conversation_meta["last_asked_field"] = ""
            conversation_meta["recommended_question_id"] = str(readiness.get("recommended_question_id") or "").strip()
        else:
            conversation_meta["recommended_question_id"] = str(readiness.get("recommended_question_id") or "").strip()

        conversation_meta["last_assistant_action"] = action
        conversation_meta["last_assistant_message"] = assistant_message
        conversation_meta["conversation_brief"] = self._build_conversation_brief(requirements)
        state["conversation_meta"] = conversation_meta
        return state

    def _build_conversation_brief(self, requirements):
        requirements = dict(requirements or {})
        parts = []
        categories = list(requirements.get("preferred_categories") or [])
        if categories:
            parts.append(self._humanize_categories(categories))
        elif requirements.get("preferred_category"):
            parts.append(str(requirements.get("preferred_category")).strip())
        workloads = list(requirements.get("workloads") or [])
        if workloads:
            parts.append(self._humanize_workloads(workloads))
        application_signals = list(requirements.get("application_signals") or [])
        if application_signals:
            labels = [self.APPLICATION_SIGNAL_LABELS.get(sig, str(sig).replace("_", " ")) for sig in application_signals]
            parts.append(", ".join(labels))
        team_size = requirements.get("team_size") or requirements.get("quantity")
        if team_size:
            parts.append(f"for {team_size} users")
        budget = requirements.get("budget")
        if budget is not None:
            scope = str(requirements.get("budget_scope") or "").strip().replace("_", " ")
            parts.append(f"budget {budget}{' ' + scope if scope else ''}")
        return "; ".join(parts)

    def _humanize_workloads(self, workloads):
        items = []
        for workload in list(workloads or []):
            items.append(self.WORKLOAD_LABELS.get(workload, str(workload).replace("_", " ")))
        return ", ".join(self._dedupe_strings(items))

    def _humanize_categories(self, categories):
        normalized = [str(category).replace("_", " ") for category in list(categories or []) if category]
        if not normalized:
            return ""
        if len(normalized) == 1:
            return normalized[0]
        if len(normalized) == 2:
            return f"{normalized[0]} and {normalized[1]}"
        return ", ".join(normalized[:-1]) + f", and {normalized[-1]}"

    def _merge_categories(self, existing_categories, new_categories):
        merged = []
        for item in list(existing_categories or []) + list(new_categories or []):
            if item and item not in merged:
                merged.append(item)
        return merged

    def _normalize_multi_intent_groups_for_state(self, multi_intent_result):
        groups = []
        for intent in list(dict(multi_intent_result or {}).get("intents") or []):
            schema = dict(intent.get("extracted_schema") or {})
            category = normalize_category(intent.get("category") or schema.get("preferred_category"))
            workloads = self._dedupe_strings(
                normalize_workloads(schema.get("workload_types") or intent.get("workloads") or [])
            )
            if not category and not workloads:
                continue
            group = {
                "group_id": str(intent.get("group_id") or "").strip(),
                "label": str(intent.get("label") or "").strip(),
                "intent_text": str(intent.get("intent_text") or schema.get("raw_chat") or "").strip(),
            }
            if category:
                group["preferred_category"] = category
            if workloads:
                group["workloads"] = workloads
            application_signals = self._dedupe_strings(schema.get("application_signals") or [])
            capability_tags = self._dedupe_strings(schema.get("capability_tags") or [])
            if application_signals:
                group["application_signals"] = application_signals
            if capability_tags:
                group["capability_tags"] = capability_tags
            for field in ("team_size", "quantity", "budget", "budget_scope", "purchase_scope"):
                value = schema.get(field)
                if value not in (None, "", [], {}):
                    group[field] = value
            groups.append(group)
        return groups

    def _dedupe_strings(self, values):
        items = []
        for value in list(values or []):
            cleaned = str(value or "").strip()
            if cleaned and cleaned not in items:
                items.append(cleaned)
        return items

    def _safe_next_question(self, validated, planner_output=None, updated_state=None):
        readiness = dict((validated or {}).get("readiness") or {})
        field = str(((planner_output or {}).get("question_target_field")) or readiness.get("recommended_question_id") or "").strip()
        next_question = str(readiness.get("next_question") or "").strip()
        if field and (not next_question or self._question_prompt_mismatch(field, next_question)):
            next_question = default_follow_up_prompt(field)
        if not next_question and field:
            next_question = default_follow_up_prompt(field)
        return next_question

    def _question_prompt_mismatch(self, field, prompt):
        field = str(field or "").strip()
        prompt_l = str(prompt or "").strip().lower()
        if not field:
            return False
        if not prompt_l:
            return True
        if field in {"workload_or_application_profile", "application_profile"}:
            return (
                "trying to buy first" in prompt_l
                or "laptops, desktops, servers" in prompt_l
                or "budget" in prompt_l
                or "total budget" in prompt_l
                or "per-unit budget" in prompt_l
                or "how many" in prompt_l
            )
        if field in {"team_size", "budget", "budget_scope", "purchase_scope_or_quantity", "growth_expectation", "performance_priority"}:
            return (
                "trying to buy first" in prompt_l
                or "what kind of work" in prompt_l
                or "which apps or tools matter most" in prompt_l
                or "applications or tools" in prompt_l
            )
        if field in {"preferred_category", "category_or_workload"}:
            return "what kind of work" in prompt_l or "which apps or tools matter most" in prompt_l
        return False

    def _parse_growth_expectation(self, text):
        lowered = str(text or "").strip().lower()
        if not lowered:
            return None
        if any(token in lowered for token in {"steady", "stable", "no growth"}):
            return "steady"
        if any(token in lowered for token in {"moderate", "grow", "hiring", "expansion"}):
            return "moderate_growth"
        if any(token in lowered for token in {"rapid", "fast growth", "aggressive", "scale fast"}):
            return "rapid_growth"
        normalized = normalize_growth_expectation(text)
        return normalized if normalized in {"steady", "moderate_growth", "rapid_growth"} else None

    def _parse_performance_priority(self, text):
        lowered = str(text or "").strip().lower()
        if not lowered:
            return None
        for key, aliases in self.PERFORMANCE_PRIORITY_MAP.items():
            if lowered in aliases or any(alias in lowered for alias in aliases):
                return key
        return None

    def _attach_turn_metrics(self, payload, turn_metrics, response_type=""):
        payload = dict(payload or {})
        payload.setdefault("meta", {})
        top_level_timings = dict((payload.get("meta") or {}).get("top_level_timings_ms") or {})
        core_ms = dict(top_level_timings.get("core_ms") or {})
        presentation_ms = dict(top_level_timings.get("presentation_ms") or {})
        stage_timings = dict((((payload.get("meta") or {}).get("stage_timings_ms")) or {}))
        turn_metrics["catalog_fetch_ms"] = round(float(stage_timings.get("catalog_fetch_ms") or turn_metrics.get("catalog_fetch_ms") or 0.0), 2)
        turn_metrics["policy_ms"] = round(float(stage_timings.get("policy_ms") or turn_metrics.get("policy_ms") or 0.0), 2)
        turn_metrics["compatibility_ms"] = round(float(stage_timings.get("compatibility_ms") or turn_metrics.get("compatibility_ms") or 0.0), 2)
        turn_metrics["ranking_ms"] = round(float(stage_timings.get("ranking_ms") or turn_metrics.get("ranking_ms") or 0.0), 2)
        turn_metrics["presenter_ms"] = round(float(presentation_ms.get("assembly_ms") or turn_metrics.get("presenter_ms") or 0.0), 2)
        if not turn_metrics.get("recommendation_total_ms"):
            turn_metrics["recommendation_total_ms"] = round(float(core_ms.get("total_ms") or 0.0), 2)
        final_metrics = self._finalize_turn_metrics(turn_metrics, response_type=response_type, payload=payload)
        payload["meta"] = self._merge_meta(
            payload.get("meta"),
            {
                "turn_metrics": final_metrics,
            },
        )
        return payload

    def _finalize_turn_metrics(self, turn_metrics, response_type="", payload=None):
        final_metrics = dict(turn_metrics or {})
        final_metrics["finished_at"] = datetime.now(timezone.utc).isoformat()
        final_metrics["total_ms"] = round((perf_counter() - float(final_metrics.pop("_started_perf", perf_counter()))) * 1000, 2)
        final_metrics["response_type"] = str(response_type or payload.get("response_type") or "").strip()
        final_metrics["contract_parity_ok"] = self._payload_contract_ok(payload or {})
        return final_metrics

    def _build_llm_stats(self):
        llm_client = getattr(self.planner_service, "llm_client", None)
        stats = dict(getattr(llm_client, "stats", {}) or {})
        planner_meta = dict(getattr(self.planner_service, "last_plan_metadata", {}) or {})
        planner_stats = dict(stats)
        planner_stats.update(planner_meta)
        return {
            "provider": str(getattr(llm_client, "provider", "") or ""),
            "model": str(getattr(llm_client, "model_name", "") or ""),
            "available": bool(llm_client.is_available()) if llm_client and hasattr(llm_client, "is_available") else False,
            "extraction": {},
            "followup": {},
            "explanation": {},
            "planner": planner_stats,
        }

    def _merge_meta(self, base, extra):
        merged = dict(base or {})
        for key, value in dict(extra or {}).items():
            if isinstance(merged.get(key), dict) and isinstance(value, dict):
                nested = dict(merged.get(key) or {})
                nested.update(value)
                merged[key] = nested
            else:
                merged[key] = value
        return merged

    def _new_turn_metrics(self, transport_session_id, turn_type=""):
        return {
            "conversation_id": "",
            "transport_session_id": self._transport_session_label(transport_session_id),
            "turn_id": uuid4().hex,
            "turn_type": str(turn_type or "chat_turn"),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "consumer_receive_ms": 0.0,
            "session_load_ms": 0.0,
            "planner_prepare_ms": 0.0,
            "planner_request_ms": 0.0,
            "planner_total_ms": 0.0,
            "state_merge_ms": 0.0,
            "guard_validate_ms": 0.0,
            "recommendation_total_ms": 0.0,
            "catalog_fetch_ms": 0.0,
            "policy_ms": 0.0,
            "compatibility_ms": 0.0,
            "ranking_ms": 0.0,
            "presenter_ms": 0.0,
            "response_contract_ms": 0.0,
            "db_persist_ms": 0.0,
            "channel_send_ms": 0.0,
            "planner_input_tokens": 0,
            "planner_output_tokens": 0,
            "explanation_input_tokens": 0,
            "explanation_output_tokens": 0,
            "llm_calls_in_turn": 0,
            "planner_fallback_used": False,
            "background_explanation_enqueued": False,
            "background_explanation_completed": False,
            "contract_parity_ok": False,
            "cache_hit": False,
            "cache_miss": False,
            "_started_perf": perf_counter(),
        }

    def _mark_stage(self, turn_metrics, key, started_at):
        elapsed_ms = max(round((perf_counter() - started_at) * 1000, 2), 0.0)
        turn_metrics[key] = round(float(turn_metrics.get(key) or 0.0) + elapsed_ms, 2)

    def _apply_cache_counters(self, turn_metrics):
        cache_result = str(getattr(self.chat_session_service, "last_cache_result", "") or "").strip().lower()
        if cache_result == "hit":
            turn_metrics["cache_hit"] = True
        elif cache_result == "miss":
            turn_metrics["cache_miss"] = True

    def _apply_planner_metadata(self, turn_metrics):
        metadata = dict(getattr(self.planner_service, "last_plan_metadata", {}) or {})
        request_ms = metadata.get("request_ms")
        if request_ms is not None:
            turn_metrics["planner_request_ms"] = round(float(request_ms or 0.0), 2)
        turn_metrics["planner_input_tokens"] = int(metadata.get("input_tokens") or 0)
        turn_metrics["planner_output_tokens"] = int(metadata.get("output_tokens") or 0)
        turn_metrics["llm_calls_in_turn"] = int(metadata.get("llm_calls") or 0)
        turn_metrics["planner_fallback_used"] = bool(metadata.get("fallback_used"))

    def _payload_contract_ok(self, payload):
        payload = dict(payload or {})
        required_keys = {"response", "response_type", "requirements", "readiness", "meta", "llm_stats"}
        return required_keys.issubset(set(payload.keys()))

    def _transport_session_label(self, transport_session_id):
        if hasattr(self.chat_session_service, "_transport_identity"):
            identity = self.chat_session_service._transport_identity(transport_session_id)
            return str(identity.get("transport_key") or identity.get("conversation_id") or "").strip()
        if hasattr(transport_session_id, "channel_name"):
            return str(getattr(transport_session_id, "channel_name") or "").strip()
        return str(transport_session_id or "").strip()

    def _append_runtime_log(self, payload):
        observability_service = getattr(self.recommendation_service, "observability_service", None)
        if not observability_service or not hasattr(observability_service, "append_runtime_log"):
            return
        payload = dict(payload or {})
        meta = dict(payload.get("meta") or {})
        turn_metrics = dict(meta.get("turn_metrics") or {})
        if not turn_metrics:
            return
        observability_service.append_runtime_log(
            {
                "conversation_id": meta.get("conversation_id"),
                "response_type": payload.get("response_type"),
                "turn_metrics": turn_metrics,
            }
        )

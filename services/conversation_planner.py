# import json
# from time import perf_counter

# from ..serializers import ConversationPlannerResultSerializer
# from .clarification import ProcurementClarificationService, default_follow_up_prompt
# from .llm_client import OptionalLLMClient


# class ConversationPlannerService:
#     PROMPT_NAME = "conversation_planner.txt"

#     def __init__(self, llm_client=None, clarification_service=None):
#         self.llm_client = llm_client or OptionalLLMClient()
#         self.clarification_service = clarification_service or ProcurementClarificationService()
#         self.last_plan_metadata = {}

#     def plan_turn(
#         self,
#         user_message: str,
#         state: dict,
#         recent_messages: list[dict],
#         readiness: dict,
#         current_recommendations: list | None = None,
#     ) -> dict:
#         total_started_at = perf_counter()
#         variables = {
#             "user_message": str(user_message or "").strip(),
#             "state_json": json.dumps(state or {}, ensure_ascii=False),
#             "recent_messages_json": json.dumps(recent_messages or [], ensure_ascii=False),
#             "readiness_json": json.dumps(readiness or {}, ensure_ascii=False),
#             "current_recommendations_json": json.dumps(current_recommendations or [], ensure_ascii=False),
#         }
#         request_started_at = perf_counter()
#         planner_result = self.llm_client.invoke_planner(self.PROMPT_NAME, variables) or {}
#         request_ms = round((perf_counter() - request_started_at) * 1000, 2)
#         validated = self._validate_result(planner_result)
#         if validated is not None:
#             self.last_plan_metadata = self._build_plan_metadata(
#                 request_ms=request_ms,
#                 total_started_at=total_started_at,
#                 planner_result=planner_result,
#                 fallback_used=False,
#                 validation_success=True,
#             )
#             return validated
#         fallback = self._fallback_plan(user_message=user_message, readiness=readiness)
#         self.last_plan_metadata = self._build_plan_metadata(
#             request_ms=request_ms,
#             total_started_at=total_started_at,
#             planner_result=planner_result,
#             fallback_used=True,
#             validation_success=False,
#         )
#         return fallback

#     def _validate_result(self, planner_result):
#         serializer = ConversationPlannerResultSerializer(data=planner_result or {})
#         if serializer.is_valid():
#             return serializer.validated_data
#         return None

#     def _fallback_plan(self, user_message, readiness):
#         highest_gap = (readiness or {}).get("highest_priority_missing_field") or ""
#         next_question = str((readiness or {}).get("next_question") or "").strip()
#         assistant_message = next_question or default_follow_up_prompt(highest_gap or "budget")
#         should_trigger = bool(readiness and readiness.get("is_ready"))
#         return {
#             "action": "recommend" if should_trigger else "ask_question",
#             "assistant_message": assistant_message,
#             "state_patch": {},
#             "question_target_field": highest_gap,
#             "corrections": [],
#             "should_trigger_recommendation": should_trigger,
#             "intent_groups": [],
#             "confidence": 0.35 if user_message else 0.2,
#         }

#     def _build_plan_metadata(
#         self,
#         request_ms,
#         total_started_at,
#         planner_result,
#         fallback_used,
#         validation_success,
#     ):
#         stats = dict(getattr(self.llm_client, "stats", {}) or {})
#         usage = dict(stats.get("last_usage") or {})
#         text_calls = int(stats.get("text_calls") or 0)
#         return {
#             "prompt_name": str(stats.get("last_prompt_name") or self.PROMPT_NAME),
#             "prompt_version": str(stats.get("last_prompt_version") or ""),
#             "model": str(stats.get("last_response_model") or getattr(self.llm_client, "model_name", "") or ""),
#             "timeout_sec": stats.get("last_timeout_sec"),
#             "request_ms": round(float(request_ms or 0.0), 2),
#             "total_ms": round((perf_counter() - total_started_at) * 1000, 2),
#             "input_tokens": int(usage.get("input_tokens") or 0),
#             "output_tokens": int(usage.get("output_tokens") or 0),
#             "total_tokens": int(usage.get("total_tokens") or 0),
#             "finish_reason": str(stats.get("last_finish_reason") or ""),
#             "llm_calls": 1 if text_calls else 0,
#             "fallback_used": bool(fallback_used),
#             "validation_success": bool(validation_success),
#             "malformed_output": bool(not validation_success and planner_result),
#         }




#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################




# import json
# from pathlib import Path
# from time import perf_counter

# from ..serializers import ConversationPlannerResultSerializer
# from .clarification import ProcurementClarificationService, default_follow_up_prompt
# from .llm_client import OptionalLLMClient

# PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


# class ConversationPlannerService:
#     PROMPT_NAME = "conversation_planner.txt"
#     EXAMPLES_NAME = "conversation_planner_examples.json"
#     GREETING_TOKENS = {"hi", "hello", "hey", "good morning", "good evening", "good afternoon"}
#     ACK_TOKENS = {"ok", "okay", "sure", "fine", "got it", "understood", "thanks", "thank you"}

#     def __init__(self, llm_client=None, clarification_service=None):
#         self.llm_client = llm_client or OptionalLLMClient()
#         self.clarification_service = clarification_service or ProcurementClarificationService()
#         self.last_plan_metadata = {}

#     def plan_turn(
#         self,
#         user_message: str,
#         state: dict,
#         recent_messages: list[dict],
#         readiness: dict,
#         current_recommendations: list | None = None,
#     ) -> dict:
#         total_started_at = perf_counter()
#         state = dict(state or {})
#         recent_messages = list(recent_messages or [])
#         user_message = str(user_message or "").strip()

#         quick_plan = self._quick_plan(
#             user_message=user_message,
#             state=state,
#             readiness=readiness,
#             recent_messages=recent_messages,
#         )
#         if quick_plan is not None:
#             self.last_plan_metadata = self._build_plan_metadata(
#                 request_ms=0.0,
#                 total_started_at=total_started_at,
#                 planner_result=quick_plan,
#                 fallback_used=False,
#                 validation_success=True,
#                 llm_calls=0,
#             )
#             return quick_plan

#         variables = {
#             "user_message": user_message,
#             "state_json": json.dumps(self._planner_state(state), ensure_ascii=False),
#             "recent_messages_json": json.dumps(recent_messages, ensure_ascii=False),
#             "readiness_json": json.dumps(readiness or {}, ensure_ascii=False),
#             "current_recommendations_json": json.dumps(current_recommendations or [], ensure_ascii=False),
#             "examples_json": self._load_examples_json(),
#         }
#         request_started_at = perf_counter()
#         planner_result = self.llm_client.invoke_planner(self.PROMPT_NAME, variables) or {}
#         request_ms = round((perf_counter() - request_started_at) * 1000, 2)
#         validated = self._validate_result(planner_result)
#         if validated is not None:
#             self.last_plan_metadata = self._build_plan_metadata(
#                 request_ms=request_ms,
#                 total_started_at=total_started_at,
#                 planner_result=planner_result,
#                 fallback_used=False,
#                 validation_success=True,
#                 llm_calls=1,
#             )
#             return validated
#         fallback = self._fallback_plan(
#             user_message=user_message,
#             readiness=readiness,
#             state=state,
#             recent_messages=recent_messages,
#         )
#         self.last_plan_metadata = self._build_plan_metadata(
#             request_ms=request_ms,
#             total_started_at=total_started_at,
#             planner_result=planner_result,
#             fallback_used=True,
#             validation_success=False,
#             llm_calls=1,
#         )
#         return fallback

#     def _planner_state(self, state):
#         state = dict(state or {})
#         return {
#             "requirements": dict(state.get("requirements") or {}),
#             "conversation_meta": dict(state.get("conversation_meta") or {}),
#             "intent_groups": list(state.get("intent_groups") or []),
#         }

#     def _quick_plan(self, user_message, state, readiness, recent_messages):
#         lowered = str(user_message or "").strip().lower()
#         if not lowered:
#             return self._fallback_plan(
#                 user_message=user_message,
#                 readiness=readiness,
#                 state=state,
#                 recent_messages=recent_messages,
#             )

#         if lowered in self.ACK_TOKENS:
#             next_question = str((readiness or {}).get("next_question") or "").strip()
#             if next_question:
#                 return {
#                     "action": "ask_question",
#                     "assistant_message": next_question,
#                     "state_patch": {},
#                     "question_target_field": str((readiness or {}).get("recommended_question_id") or "").strip(),
#                     "corrections": [],
#                     "should_trigger_recommendation": False,
#                     "intent_groups": [],
#                     "confidence": 0.55,
#                 }

#         if lowered in self.GREETING_TOKENS:
#             requirements = dict((state or {}).get("requirements") or {})
#             if not requirements:
#                 return {
#                     "action": "respond",
#                     "assistant_message": (
#                         "Hi. Tell me what you need to buy, who it is for, and your budget, "
#                         "and I will narrow it down quickly."
#                     ),
#                     "state_patch": {},
#                     "question_target_field": "",
#                     "corrections": [],
#                     "should_trigger_recommendation": False,
#                     "intent_groups": [],
#                     "confidence": 0.82,
#                 }

#         return None

#     def _validate_result(self, planner_result):
#         serializer = ConversationPlannerResultSerializer(data=planner_result or {})
#         if serializer.is_valid():
#             return serializer.validated_data
#         return None

#     def _fallback_plan(self, user_message, readiness, state=None, recent_messages=None):
#         state = dict(state or {})
#         conversation_meta = dict(state.get("conversation_meta") or {})
#         highest_gap = str((readiness or {}).get("highest_priority_missing_field") or "").strip()
#         next_question = str((readiness or {}).get("next_question") or "").strip()
#         last_asked_field = str(conversation_meta.get("last_asked_field") or "").strip()
#         lowered = str(user_message or "").strip().lower()

#         if lowered in self.GREETING_TOKENS:
#             return {
#                 "action": "respond",
#                 "assistant_message": (
#                     "Hi. Share what you are planning to buy and any budget or workload details you already know."
#                 ),
#                 "state_patch": {},
#                 "question_target_field": "",
#                 "corrections": [],
#                 "should_trigger_recommendation": False,
#                 "intent_groups": [],
#                 "confidence": 0.45,
#             }

#         if lowered in {"yes", "yeah", "yep", "no", "nope"} and last_asked_field:
#             prompt = next_question or default_follow_up_prompt(last_asked_field)
#             return {
#                 "action": "ask_question",
#                 "assistant_message": prompt,
#                 "state_patch": {},
#                 "question_target_field": last_asked_field,
#                 "corrections": [],
#                 "should_trigger_recommendation": False,
#                 "intent_groups": [],
#                 "confidence": 0.35,
#             }

#         assistant_message = next_question or default_follow_up_prompt(highest_gap or last_asked_field or "budget")
#         should_trigger = bool(readiness and readiness.get("is_ready"))
#         return {
#             "action": "recommend" if should_trigger else "ask_question",
#             "assistant_message": assistant_message,
#             "state_patch": {},
#             "question_target_field": highest_gap or last_asked_field,
#             "corrections": [],
#             "should_trigger_recommendation": should_trigger,
#             "intent_groups": [],
#             "confidence": 0.35 if user_message else 0.2,
#         }

#     def _load_examples_json(self):
#         path = PROMPTS_DIR / self.EXAMPLES_NAME
#         try:
#             return path.read_text(encoding="utf-8").strip()
#         except Exception:
#             return "[]"

#     def _build_plan_metadata(
#         self,
#         request_ms,
#         total_started_at,
#         planner_result,
#         fallback_used,
#         validation_success,
#         llm_calls,
#     ):
#         stats = dict(getattr(self.llm_client, "stats", {}) or {})
#         usage = dict(stats.get("last_usage") or {})
#         return {
#             "prompt_name": str(stats.get("last_prompt_name") or self.PROMPT_NAME),
#             "prompt_version": str(stats.get("last_prompt_version") or ""),
#             "model": str(stats.get("last_response_model") or getattr(self.llm_client, "model_name", "") or ""),
#             "timeout_sec": stats.get("last_timeout_sec"),
#             "request_ms": round(float(request_ms or 0.0), 2),
#             "total_ms": round((perf_counter() - total_started_at) * 1000, 2),
#             "input_tokens": int(usage.get("input_tokens") or 0),
#             "output_tokens": int(usage.get("output_tokens") or 0),
#             "total_tokens": int(usage.get("total_tokens") or 0),
#             "finish_reason": str(stats.get("last_finish_reason") or ""),
#             "llm_calls": int(llm_calls or 0),
#             "fallback_used": bool(fallback_used),
#             "validation_success": bool(validation_success),
#             "malformed_output": bool(not validation_success and planner_result),
#         }




#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################


# import json
# from pathlib import Path
# from time import perf_counter

# from ..serializers import ConversationPlannerResultSerializer
# from .clarification import ProcurementClarificationService, default_follow_up_prompt
# from .llm_client import OptionalLLMClient

# PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


# class ConversationPlannerService:
#     PROMPT_NAME = "conversation_planner.txt"
#     EXAMPLES_NAME = "conversation_planner_examples.json"
#     QUESTION_REPHRASE_PROMPT_NAME = "clarification_question_rephrase.txt"
#     GREETING_TOKENS = {"hi", "hello", "hey", "good morning", "good evening", "good afternoon"}
#     ACK_TOKENS = {"ok", "okay", "sure", "fine", "got it", "understood", "thanks", "thank you"}
#     SUPPORT_CONTEXT = {
#         "supported_categories": [
#             "laptops",
#             "desktops",
#             "servers",
#             "networking",
#             "printers",
#             "accessories",
#         ],
#         "accessory_examples": ["keyboards", "mouse", "headsets", "docks", "webcams", "monitors"],
#         "supported_followups": [
#             "clarify missing procurement details",
#             "summarize the latest recommendation",
#             "refine the shortlist with a new budget or requirement change",
#         ],
#         "out_of_scope_examples": ["jokes", "songs", "weather", "timers", "article summaries"],
#     }

#     def __init__(self, llm_client=None, clarification_service=None):
#         self.llm_client = llm_client or OptionalLLMClient()
#         self.clarification_service = clarification_service or ProcurementClarificationService()
#         self.last_plan_metadata = {}

#     def plan_turn(
#         self,
#         user_message: str,
#         state: dict,
#         recent_messages: list[dict],
#         readiness: dict,
#         current_recommendations: list | None = None,
#     ) -> dict:
#         total_started_at = perf_counter()
#         state = dict(state or {})
#         recent_messages = list(recent_messages or [])
#         user_message = str(user_message or "").strip()

#         quick_plan = self._quick_plan(
#             user_message=user_message,
#             state=state,
#             readiness=readiness,
#             recent_messages=recent_messages,
#         )
#         if quick_plan is not None:
#             self.last_plan_metadata = self._build_plan_metadata(
#                 request_ms=0.0,
#                 total_started_at=total_started_at,
#                 planner_result=quick_plan,
#                 fallback_used=False,
#                 validation_success=True,
#                 llm_calls=0,
#             )
#             return quick_plan

#         variables = {
#             "user_message": user_message,
#             "state_json": json.dumps(self._planner_state(state), ensure_ascii=False),
#             "recent_messages_json": json.dumps(recent_messages, ensure_ascii=False),
#             "readiness_json": json.dumps(readiness or {}, ensure_ascii=False),
#             "current_recommendations_json": json.dumps(current_recommendations or [], ensure_ascii=False),
#             "examples_json": self._load_examples_json(),
#             "support_json": json.dumps(self.SUPPORT_CONTEXT, ensure_ascii=False),
#         }
#         request_started_at = perf_counter()
#         planner_result = self.llm_client.invoke_planner(self.PROMPT_NAME, variables) or {}
#         request_ms = round((perf_counter() - request_started_at) * 1000, 2)
#         validated = self._validate_result(planner_result)
#         if validated is not None:
#             self.last_plan_metadata = self._build_plan_metadata(
#                 request_ms=request_ms,
#                 total_started_at=total_started_at,
#                 planner_result=planner_result,
#                 fallback_used=False,
#                 validation_success=True,
#                 llm_calls=1,
#             )
#             return validated
#         fallback = self._fallback_plan(
#             user_message=user_message,
#             readiness=readiness,
#             state=state,
#             recent_messages=recent_messages,
#         )
#         self.last_plan_metadata = self._build_plan_metadata(
#             request_ms=request_ms,
#             total_started_at=total_started_at,
#             planner_result=planner_result,
#             fallback_used=True,
#             validation_success=False,
#             llm_calls=1,
#         )
#         return fallback

#     def rephrase_clarification_question(
#         self,
#         question_target_field: str,
#         canonical_question: str,
#         state: dict | None = None,
#         acknowledgement: str = "",
#     ) -> str:
#         field = str(question_target_field or "").strip()
#         canonical = str(canonical_question or "").strip()
#         if not field or not canonical:
#             return canonical
#         if not self.llm_client or not self.llm_client.is_available():
#             return canonical

#         state = dict(state or {})
#         requirements = dict(state.get("requirements") or {})
#         conversation_meta = dict(state.get("conversation_meta") or {})
#         variables = {
#             "question_target_field": field,
#             "canonical_question": canonical,
#             "acknowledgement": str(acknowledgement or "").strip(),
#             "conversation_brief": str(conversation_meta.get("conversation_brief") or "").strip(),
#             "preferred_categories_json": json.dumps(requirements.get("preferred_categories") or [], ensure_ascii=False),
#             "workloads_json": json.dumps(requirements.get("workloads") or [], ensure_ascii=False),
#             "team_size": str(requirements.get("team_size") or requirements.get("quantity") or "").strip(),
#             "budget": str(requirements.get("budget") or "").strip(),
#         }
#         result = self.llm_client.invoke_text(
#             self.QUESTION_REPHRASE_PROMPT_NAME,
#             variables,
#             request_options={
#                 "temperature": 0,
#                 "timeout_sec": 2,
#                 "max_tokens": 80,
#                 "reasoning_effort": "low",
#             },
#         )
#         return self._sanitize_rephrased_question(result, canonical)

#     def _sanitize_rephrased_question(self, text, canonical):
#         candidate = str(text or "").strip()
#         if not candidate:
#             return canonical
#         if candidate.startswith("\"") and candidate.endswith("\"") and len(candidate) >= 2:
#             candidate = candidate[1:-1].strip()
#         candidate = " ".join(candidate.replace("\n", " ").split())
#         if not candidate:
#             return canonical
#         if len(candidate) > 180:
#             return canonical
#         if candidate.count("?") > 2:
#             return canonical
#         if ":" in candidate and len(candidate.split()) <= 3:
#             return canonical
#         if not candidate.endswith("?"):
#             candidate = candidate.rstrip(". ") + "?"
#         return candidate

#     def _planner_state(self, state):
#         state = dict(state or {})
#         return {
#             "requirements": dict(state.get("requirements") or {}),
#             "conversation_meta": dict(state.get("conversation_meta") or {}),
#             "intent_groups": list(state.get("intent_groups") or []),
#         }

#     def _quick_plan(self, user_message, state, readiness, recent_messages):
#         lowered = str(user_message or "").strip().lower()
#         if not lowered:
#             return self._fallback_plan(
#                 user_message=user_message,
#                 readiness=readiness,
#                 state=state,
#                 recent_messages=recent_messages,
#             )

#         llm_available = bool(self.llm_client and self.llm_client.is_available())
#         if llm_available:
#             return None

#         if lowered in self.ACK_TOKENS:
#             next_question = str((readiness or {}).get("next_question") or "").strip()
#             if next_question:
#                 return {
#                     "action": "ask_question",
#                     "assistant_message": next_question,
#                     "state_patch": {},
#                     "question_target_field": str((readiness or {}).get("recommended_question_id") or "").strip(),
#                     "corrections": [],
#                     "should_trigger_recommendation": False,
#                     "intent_groups": [],
#                     "confidence": 0.55,
#                 }

#         if lowered in self.GREETING_TOKENS:
#             requirements = dict((state or {}).get("requirements") or {})
#             if not requirements:
#                 return {
#                     "action": "respond",
#                     "assistant_message": (
#                         "Hi. Tell me what you need to buy, who it is for, and your budget, "
#                         "and I will narrow it down quickly."
#                     ),
#                     "state_patch": {},
#                     "question_target_field": "",
#                     "corrections": [],
#                     "should_trigger_recommendation": False,
#                     "intent_groups": [],
#                     "confidence": 0.82,
#                 }

#         return None

#     def _validate_result(self, planner_result):
#         serializer = ConversationPlannerResultSerializer(data=planner_result or {})
#         if serializer.is_valid():
#             return serializer.validated_data
#         return None

#     def _fallback_plan(self, user_message, readiness, state=None, recent_messages=None):
#         state = dict(state or {})
#         conversation_meta = dict(state.get("conversation_meta") or {})
#         highest_gap = str((readiness or {}).get("highest_priority_missing_field") or "").strip()
#         next_question = str((readiness or {}).get("next_question") or "").strip()
#         last_asked_field = str(conversation_meta.get("last_asked_field") or "").strip()
#         lowered = str(user_message or "").strip().lower()

#         if lowered in self.GREETING_TOKENS:
#             return {
#                 "action": "respond",
#                 "assistant_message": (
#                     "Hi. Share what you are planning to buy and any budget or workload details you already know."
#                 ),
#                 "state_patch": {},
#                 "question_target_field": "",
#                 "corrections": [],
#                 "should_trigger_recommendation": False,
#                 "intent_groups": [],
#                 "confidence": 0.45,
#             }

#         if lowered in {"yes", "yeah", "yep", "no", "nope"} and last_asked_field:
#             prompt = next_question or default_follow_up_prompt(last_asked_field)
#             return {
#                 "action": "ask_question",
#                 "assistant_message": prompt,
#                 "state_patch": {},
#                 "question_target_field": last_asked_field,
#                 "corrections": [],
#                 "should_trigger_recommendation": False,
#                 "intent_groups": [],
#                 "confidence": 0.35,
#             }

#         assistant_message = next_question or default_follow_up_prompt(highest_gap or last_asked_field or "budget")
#         should_trigger = bool(readiness and readiness.get("is_ready"))
#         return {
#             "action": "recommend" if should_trigger else "ask_question",
#             "assistant_message": assistant_message,
#             "state_patch": {},
#             "question_target_field": highest_gap or last_asked_field,
#             "corrections": [],
#             "should_trigger_recommendation": should_trigger,
#             "intent_groups": [],
#             "confidence": 0.35 if user_message else 0.2,
#         }

#     def _load_examples_json(self):
#         path = PROMPTS_DIR / self.EXAMPLES_NAME
#         try:
#             return path.read_text(encoding="utf-8").strip()
#         except Exception:
#             return "[]"

#     def _build_plan_metadata(
#         self,
#         request_ms,
#         total_started_at,
#         planner_result,
#         fallback_used,
#         validation_success,
#         llm_calls,
#     ):
#         stats = dict(getattr(self.llm_client, "stats", {}) or {})
#         usage = dict(stats.get("last_usage") or {})
#         return {
#             "prompt_name": str(stats.get("last_prompt_name") or self.PROMPT_NAME),
#             "prompt_version": str(stats.get("last_prompt_version") or ""),
#             "model": str(stats.get("last_response_model") or getattr(self.llm_client, "model_name", "") or ""),
#             "timeout_sec": stats.get("last_timeout_sec"),
#             "request_ms": round(float(request_ms or 0.0), 2),
#             "total_ms": round((perf_counter() - total_started_at) * 1000, 2),
#             "input_tokens": int(usage.get("input_tokens") or 0),
#             "output_tokens": int(usage.get("output_tokens") or 0),
#             "total_tokens": int(usage.get("total_tokens") or 0),
#             "finish_reason": str(stats.get("last_finish_reason") or ""),
#             "llm_calls": int(llm_calls or 0),
#             "fallback_used": bool(fallback_used),
#             "validation_success": bool(validation_success),
#             "malformed_output": bool(not validation_success and planner_result),
#         }





# import json
# from time import perf_counter

# from ..serializers import ConversationPlannerResultSerializer
# from .clarification import ProcurementClarificationService, default_follow_up_prompt
# from .llm_client import OptionalLLMClient


# class ConversationPlannerService:
#     PROMPT_NAME = "conversation_planner.txt"

#     def __init__(self, llm_client=None, clarification_service=None):
#         self.llm_client = llm_client or OptionalLLMClient()
#         self.clarification_service = clarification_service or ProcurementClarificationService()
#         self.last_plan_metadata = {}

#     def plan_turn(
#         self,
#         user_message: str,
#         state: dict,
#         recent_messages: list[dict],
#         readiness: dict,
#         current_recommendations: list | None = None,
#     ) -> dict:
#         total_started_at = perf_counter()
#         variables = {
#             "user_message": str(user_message or "").strip(),
#             "state_json": json.dumps(state or {}, ensure_ascii=False),
#             "recent_messages_json": json.dumps(recent_messages or [], ensure_ascii=False),
#             "readiness_json": json.dumps(readiness or {}, ensure_ascii=False),
#             "current_recommendations_json": json.dumps(current_recommendations or [], ensure_ascii=False),
#         }
#         request_started_at = perf_counter()
#         planner_result = self.llm_client.invoke_planner(self.PROMPT_NAME, variables) or {}
#         request_ms = round((perf_counter() - request_started_at) * 1000, 2)
#         validated = self._validate_result(planner_result)
#         if validated is not None:
#             self.last_plan_metadata = self._build_plan_metadata(
#                 request_ms=request_ms,
#                 total_started_at=total_started_at,
#                 planner_result=planner_result,
#                 fallback_used=False,
#                 validation_success=True,
#             )
#             return validated
#         fallback = self._fallback_plan(user_message=user_message, readiness=readiness)
#         self.last_plan_metadata = self._build_plan_metadata(
#             request_ms=request_ms,
#             total_started_at=total_started_at,
#             planner_result=planner_result,
#             fallback_used=True,
#             validation_success=False,
#         )
#         return fallback

#     def _validate_result(self, planner_result):
#         serializer = ConversationPlannerResultSerializer(data=planner_result or {})
#         if serializer.is_valid():
#             return serializer.validated_data
#         return None

#     def _fallback_plan(self, user_message, readiness):
#         highest_gap = (readiness or {}).get("highest_priority_missing_field") or ""
#         next_question = str((readiness or {}).get("next_question") or "").strip()
#         assistant_message = next_question or default_follow_up_prompt(highest_gap or "budget")
#         should_trigger = bool(readiness and readiness.get("is_ready"))
#         return {
#             "action": "recommend" if should_trigger else "ask_question",
#             "assistant_message": assistant_message,
#             "state_patch": {},
#             "question_target_field": highest_gap,
#             "corrections": [],
#             "should_trigger_recommendation": should_trigger,
#             "intent_groups": [],
#             "confidence": 0.35 if user_message else 0.2,
#         }

#     def _build_plan_metadata(
#         self,
#         request_ms,
#         total_started_at,
#         planner_result,
#         fallback_used,
#         validation_success,
#     ):
#         stats = dict(getattr(self.llm_client, "stats", {}) or {})
#         usage = dict(stats.get("last_usage") or {})
#         text_calls = int(stats.get("text_calls") or 0)
#         return {
#             "prompt_name": str(stats.get("last_prompt_name") or self.PROMPT_NAME),
#             "prompt_version": str(stats.get("last_prompt_version") or ""),
#             "model": str(stats.get("last_response_model") or getattr(self.llm_client, "model_name", "") or ""),
#             "timeout_sec": stats.get("last_timeout_sec"),
#             "request_ms": round(float(request_ms or 0.0), 2),
#             "total_ms": round((perf_counter() - total_started_at) * 1000, 2),
#             "input_tokens": int(usage.get("input_tokens") or 0),
#             "output_tokens": int(usage.get("output_tokens") or 0),
#             "total_tokens": int(usage.get("total_tokens") or 0),
#             "finish_reason": str(stats.get("last_finish_reason") or ""),
#             "llm_calls": 1 if text_calls else 0,
#             "fallback_used": bool(fallback_used),
#             "validation_success": bool(validation_success),
#             "malformed_output": bool(not validation_success and planner_result),
#         }




#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################




# import json
# from pathlib import Path
# from time import perf_counter

# from ..serializers import ConversationPlannerResultSerializer
# from .clarification import ProcurementClarificationService, default_follow_up_prompt
# from .llm_client import OptionalLLMClient

# PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


# class ConversationPlannerService:
#     PROMPT_NAME = "conversation_planner.txt"
#     EXAMPLES_NAME = "conversation_planner_examples.json"
#     GREETING_TOKENS = {"hi", "hello", "hey", "good morning", "good evening", "good afternoon"}
#     ACK_TOKENS = {"ok", "okay", "sure", "fine", "got it", "understood", "thanks", "thank you"}

#     def __init__(self, llm_client=None, clarification_service=None):
#         self.llm_client = llm_client or OptionalLLMClient()
#         self.clarification_service = clarification_service or ProcurementClarificationService()
#         self.last_plan_metadata = {}

#     def plan_turn(
#         self,
#         user_message: str,
#         state: dict,
#         recent_messages: list[dict],
#         readiness: dict,
#         current_recommendations: list | None = None,
#     ) -> dict:
#         total_started_at = perf_counter()
#         state = dict(state or {})
#         recent_messages = list(recent_messages or [])
#         user_message = str(user_message or "").strip()

#         quick_plan = self._quick_plan(
#             user_message=user_message,
#             state=state,
#             readiness=readiness,
#             recent_messages=recent_messages,
#         )
#         if quick_plan is not None:
#             self.last_plan_metadata = self._build_plan_metadata(
#                 request_ms=0.0,
#                 total_started_at=total_started_at,
#                 planner_result=quick_plan,
#                 fallback_used=False,
#                 validation_success=True,
#                 llm_calls=0,
#             )
#             return quick_plan

#         variables = {
#             "user_message": user_message,
#             "state_json": json.dumps(self._planner_state(state), ensure_ascii=False),
#             "recent_messages_json": json.dumps(recent_messages, ensure_ascii=False),
#             "readiness_json": json.dumps(readiness or {}, ensure_ascii=False),
#             "current_recommendations_json": json.dumps(current_recommendations or [], ensure_ascii=False),
#             "examples_json": self._load_examples_json(),
#         }
#         request_started_at = perf_counter()
#         planner_result = self.llm_client.invoke_planner(self.PROMPT_NAME, variables) or {}
#         request_ms = round((perf_counter() - request_started_at) * 1000, 2)
#         validated = self._validate_result(planner_result)
#         if validated is not None:
#             self.last_plan_metadata = self._build_plan_metadata(
#                 request_ms=request_ms,
#                 total_started_at=total_started_at,
#                 planner_result=planner_result,
#                 fallback_used=False,
#                 validation_success=True,
#                 llm_calls=1,
#             )
#             return validated
#         fallback = self._fallback_plan(
#             user_message=user_message,
#             readiness=readiness,
#             state=state,
#             recent_messages=recent_messages,
#         )
#         self.last_plan_metadata = self._build_plan_metadata(
#             request_ms=request_ms,
#             total_started_at=total_started_at,
#             planner_result=planner_result,
#             fallback_used=True,
#             validation_success=False,
#             llm_calls=1,
#         )
#         return fallback

#     def _planner_state(self, state):
#         state = dict(state or {})
#         return {
#             "requirements": dict(state.get("requirements") or {}),
#             "conversation_meta": dict(state.get("conversation_meta") or {}),
#             "intent_groups": list(state.get("intent_groups") or []),
#         }

#     def _quick_plan(self, user_message, state, readiness, recent_messages):
#         lowered = str(user_message or "").strip().lower()
#         if not lowered:
#             return self._fallback_plan(
#                 user_message=user_message,
#                 readiness=readiness,
#                 state=state,
#                 recent_messages=recent_messages,
#             )

#         if lowered in self.ACK_TOKENS:
#             next_question = str((readiness or {}).get("next_question") or "").strip()
#             if next_question:
#                 return {
#                     "action": "ask_question",
#                     "assistant_message": next_question,
#                     "state_patch": {},
#                     "question_target_field": str((readiness or {}).get("recommended_question_id") or "").strip(),
#                     "corrections": [],
#                     "should_trigger_recommendation": False,
#                     "intent_groups": [],
#                     "confidence": 0.55,
#                 }

#         if lowered in self.GREETING_TOKENS:
#             requirements = dict((state or {}).get("requirements") or {})
#             if not requirements:
#                 return {
#                     "action": "respond",
#                     "assistant_message": (
#                         "Hi. Tell me what you need to buy, who it is for, and your budget, "
#                         "and I will narrow it down quickly."
#                     ),
#                     "state_patch": {},
#                     "question_target_field": "",
#                     "corrections": [],
#                     "should_trigger_recommendation": False,
#                     "intent_groups": [],
#                     "confidence": 0.82,
#                 }

#         return None

#     def _validate_result(self, planner_result):
#         serializer = ConversationPlannerResultSerializer(data=planner_result or {})
#         if serializer.is_valid():
#             return serializer.validated_data
#         return None

#     def _fallback_plan(self, user_message, readiness, state=None, recent_messages=None):
#         state = dict(state or {})
#         conversation_meta = dict(state.get("conversation_meta") or {})
#         highest_gap = str((readiness or {}).get("highest_priority_missing_field") or "").strip()
#         next_question = str((readiness or {}).get("next_question") or "").strip()
#         last_asked_field = str(conversation_meta.get("last_asked_field") or "").strip()
#         lowered = str(user_message or "").strip().lower()

#         if lowered in self.GREETING_TOKENS:
#             return {
#                 "action": "respond",
#                 "assistant_message": (
#                     "Hi. Share what you are planning to buy and any budget or workload details you already know."
#                 ),
#                 "state_patch": {},
#                 "question_target_field": "",
#                 "corrections": [],
#                 "should_trigger_recommendation": False,
#                 "intent_groups": [],
#                 "confidence": 0.45,
#             }

#         if lowered in {"yes", "yeah", "yep", "no", "nope"} and last_asked_field:
#             prompt = next_question or default_follow_up_prompt(last_asked_field)
#             return {
#                 "action": "ask_question",
#                 "assistant_message": prompt,
#                 "state_patch": {},
#                 "question_target_field": last_asked_field,
#                 "corrections": [],
#                 "should_trigger_recommendation": False,
#                 "intent_groups": [],
#                 "confidence": 0.35,
#             }

#         assistant_message = next_question or default_follow_up_prompt(highest_gap or last_asked_field or "budget")
#         should_trigger = bool(readiness and readiness.get("is_ready"))
#         return {
#             "action": "recommend" if should_trigger else "ask_question",
#             "assistant_message": assistant_message,
#             "state_patch": {},
#             "question_target_field": highest_gap or last_asked_field,
#             "corrections": [],
#             "should_trigger_recommendation": should_trigger,
#             "intent_groups": [],
#             "confidence": 0.35 if user_message else 0.2,
#         }

#     def _load_examples_json(self):
#         path = PROMPTS_DIR / self.EXAMPLES_NAME
#         try:
#             return path.read_text(encoding="utf-8").strip()
#         except Exception:
#             return "[]"

#     def _build_plan_metadata(
#         self,
#         request_ms,
#         total_started_at,
#         planner_result,
#         fallback_used,
#         validation_success,
#         llm_calls,
#     ):
#         stats = dict(getattr(self.llm_client, "stats", {}) or {})
#         usage = dict(stats.get("last_usage") or {})
#         return {
#             "prompt_name": str(stats.get("last_prompt_name") or self.PROMPT_NAME),
#             "prompt_version": str(stats.get("last_prompt_version") or ""),
#             "model": str(stats.get("last_response_model") or getattr(self.llm_client, "model_name", "") or ""),
#             "timeout_sec": stats.get("last_timeout_sec"),
#             "request_ms": round(float(request_ms or 0.0), 2),
#             "total_ms": round((perf_counter() - total_started_at) * 1000, 2),
#             "input_tokens": int(usage.get("input_tokens") or 0),
#             "output_tokens": int(usage.get("output_tokens") or 0),
#             "total_tokens": int(usage.get("total_tokens") or 0),
#             "finish_reason": str(stats.get("last_finish_reason") or ""),
#             "llm_calls": int(llm_calls or 0),
#             "fallback_used": bool(fallback_used),
#             "validation_success": bool(validation_success),
#             "malformed_output": bool(not validation_success and planner_result),
#         }




#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################


# import json
# from pathlib import Path
# from time import perf_counter

# from ..serializers import ConversationPlannerResultSerializer
# from .clarification import ProcurementClarificationService, default_follow_up_prompt
# from .llm_client import OptionalLLMClient

# PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


# class ConversationPlannerService:
#     PROMPT_NAME = "conversation_planner.txt"
#     EXAMPLES_NAME = "conversation_planner_examples.json"
#     QUESTION_REPHRASE_PROMPT_NAME = "clarification_question_rephrase.txt"
#     GREETING_TOKENS = {"hi", "hello", "hey", "good morning", "good evening", "good afternoon"}
#     ACK_TOKENS = {"ok", "okay", "sure", "fine", "got it", "understood", "thanks", "thank you"}
#     SUPPORT_CONTEXT = {
#         "supported_categories": [
#             "laptops",
#             "desktops",
#             "servers",
#             "networking",
#             "printers",
#             "accessories",
#         ],
#         "accessory_examples": ["keyboards", "mouse", "headsets", "docks", "webcams", "monitors"],
#         "supported_followups": [
#             "clarify missing procurement details",
#             "summarize the latest recommendation",
#             "refine the shortlist with a new budget or requirement change",
#         ],
#         "out_of_scope_examples": ["jokes", "songs", "weather", "timers", "article summaries"],
#     }

#     def __init__(self, llm_client=None, clarification_service=None):
#         self.llm_client = llm_client or OptionalLLMClient()
#         self.clarification_service = clarification_service or ProcurementClarificationService()
#         self.last_plan_metadata = {}

#     def plan_turn(
#         self,
#         user_message: str,
#         state: dict,
#         recent_messages: list[dict],
#         readiness: dict,
#         current_recommendations: list | None = None,
#     ) -> dict:
#         total_started_at = perf_counter()
#         state = dict(state or {})
#         recent_messages = list(recent_messages or [])
#         user_message = str(user_message or "").strip()

#         quick_plan = self._quick_plan(
#             user_message=user_message,
#             state=state,
#             readiness=readiness,
#             recent_messages=recent_messages,
#         )
#         if quick_plan is not None:
#             self.last_plan_metadata = self._build_plan_metadata(
#                 request_ms=0.0,
#                 total_started_at=total_started_at,
#                 planner_result=quick_plan,
#                 fallback_used=False,
#                 validation_success=True,
#                 llm_calls=0,
#             )
#             return quick_plan

#         variables = {
#             "user_message": user_message,
#             "state_json": json.dumps(self._planner_state(state), ensure_ascii=False),
#             "recent_messages_json": json.dumps(recent_messages, ensure_ascii=False),
#             "readiness_json": json.dumps(readiness or {}, ensure_ascii=False),
#             "current_recommendations_json": json.dumps(current_recommendations or [], ensure_ascii=False),
#             "examples_json": self._load_examples_json(),
#             "support_json": json.dumps(self.SUPPORT_CONTEXT, ensure_ascii=False),
#         }
#         request_started_at = perf_counter()
#         planner_result = self.llm_client.invoke_planner(self.PROMPT_NAME, variables) or {}
#         request_ms = round((perf_counter() - request_started_at) * 1000, 2)
#         validated = self._validate_result(planner_result)
#         if validated is not None:
#             self.last_plan_metadata = self._build_plan_metadata(
#                 request_ms=request_ms,
#                 total_started_at=total_started_at,
#                 planner_result=planner_result,
#                 fallback_used=False,
#                 validation_success=True,
#                 llm_calls=1,
#             )
#             return validated
#         fallback = self._fallback_plan(
#             user_message=user_message,
#             readiness=readiness,
#             state=state,
#             recent_messages=recent_messages,
#         )
#         self.last_plan_metadata = self._build_plan_metadata(
#             request_ms=request_ms,
#             total_started_at=total_started_at,
#             planner_result=planner_result,
#             fallback_used=True,
#             validation_success=False,
#             llm_calls=1,
#         )
#         return fallback

#     def rephrase_clarification_question(
#         self,
#         question_target_field: str,
#         canonical_question: str,
#         state: dict | None = None,
#         acknowledgement: str = "",
#     ) -> str:
#         field = str(question_target_field or "").strip()
#         canonical = str(canonical_question or "").strip()
#         if not field or not canonical:
#             return canonical
#         if not self.llm_client or not self.llm_client.is_available():
#             return canonical

#         state = dict(state or {})
#         requirements = dict(state.get("requirements") or {})
#         conversation_meta = dict(state.get("conversation_meta") or {})
#         variables = {
#             "question_target_field": field,
#             "canonical_question": canonical,
#             "acknowledgement": str(acknowledgement or "").strip(),
#             "conversation_brief": str(conversation_meta.get("conversation_brief") or "").strip(),
#             "preferred_categories_json": json.dumps(requirements.get("preferred_categories") or [], ensure_ascii=False),
#             "workloads_json": json.dumps(requirements.get("workloads") or [], ensure_ascii=False),
#             "team_size": str(requirements.get("team_size") or requirements.get("quantity") or "").strip(),
#             "budget": str(requirements.get("budget") or "").strip(),
#         }
#         result = self.llm_client.invoke_text(
#             self.QUESTION_REPHRASE_PROMPT_NAME,
#             variables,
#             request_options={
#                 "temperature": 0,
#                 "timeout_sec": 2,
#                 "max_tokens": 80,
#                 "reasoning_effort": "low",
#             },
#         )
#         return self._sanitize_rephrased_question(result, canonical)

#     def _sanitize_rephrased_question(self, text, canonical):
#         candidate = str(text or "").strip()
#         if not candidate:
#             return canonical
#         if candidate.startswith("\"") and candidate.endswith("\"") and len(candidate) >= 2:
#             candidate = candidate[1:-1].strip()
#         candidate = " ".join(candidate.replace("\n", " ").split())
#         if not candidate:
#             return canonical
#         if len(candidate) > 180:
#             return canonical
#         if candidate.count("?") > 2:
#             return canonical
#         if ":" in candidate and len(candidate.split()) <= 3:
#             return canonical
#         if not candidate.endswith("?"):
#             candidate = candidate.rstrip(". ") + "?"
#         return candidate

#     def _planner_state(self, state):
#         state = dict(state or {})
#         return {
#             "requirements": dict(state.get("requirements") or {}),
#             "conversation_meta": dict(state.get("conversation_meta") or {}),
#             "intent_groups": list(state.get("intent_groups") or []),
#         }

#     def _quick_plan(self, user_message, state, readiness, recent_messages):
#         lowered = str(user_message or "").strip().lower()
#         if not lowered:
#             return self._fallback_plan(
#                 user_message=user_message,
#                 readiness=readiness,
#                 state=state,
#                 recent_messages=recent_messages,
#             )

#         llm_available = bool(self.llm_client and self.llm_client.is_available())
#         if llm_available:
#             return None

#         if lowered in self.ACK_TOKENS:
#             next_question = str((readiness or {}).get("next_question") or "").strip()
#             if next_question:
#                 return {
#                     "action": "ask_question",
#                     "assistant_message": next_question,
#                     "state_patch": {},
#                     "question_target_field": str((readiness or {}).get("recommended_question_id") or "").strip(),
#                     "corrections": [],
#                     "should_trigger_recommendation": False,
#                     "intent_groups": [],
#                     "confidence": 0.55,
#                 }

#         if lowered in self.GREETING_TOKENS:
#             requirements = dict((state or {}).get("requirements") or {})
#             if not requirements:
#                 return {
#                     "action": "respond",
#                     "assistant_message": (
#                         "Hi. Tell me what you need to buy, who it is for, and your budget, "
#                         "and I will narrow it down quickly."
#                     ),
#                     "state_patch": {},
#                     "question_target_field": "",
#                     "corrections": [],
#                     "should_trigger_recommendation": False,
#                     "intent_groups": [],
#                     "confidence": 0.82,
#                 }

#         return None

#     def _validate_result(self, planner_result):
#         serializer = ConversationPlannerResultSerializer(data=planner_result or {})
#         if serializer.is_valid():
#             return serializer.validated_data
#         return None

#     def _fallback_plan(self, user_message, readiness, state=None, recent_messages=None):
#         state = dict(state or {})
#         conversation_meta = dict(state.get("conversation_meta") or {})
#         highest_gap = str((readiness or {}).get("highest_priority_missing_field") or "").strip()
#         next_question = str((readiness or {}).get("next_question") or "").strip()
#         last_asked_field = str(conversation_meta.get("last_asked_field") or "").strip()
#         lowered = str(user_message or "").strip().lower()

#         if lowered in self.GREETING_TOKENS:
#             return {
#                 "action": "respond",
#                 "assistant_message": (
#                     "Hi. Share what you are planning to buy and any budget or workload details you already know."
#                 ),
#                 "state_patch": {},
#                 "question_target_field": "",
#                 "corrections": [],
#                 "should_trigger_recommendation": False,
#                 "intent_groups": [],
#                 "confidence": 0.45,
#             }

#         if lowered in {"yes", "yeah", "yep", "no", "nope"} and last_asked_field:
#             prompt = next_question or default_follow_up_prompt(last_asked_field)
#             return {
#                 "action": "ask_question",
#                 "assistant_message": prompt,
#                 "state_patch": {},
#                 "question_target_field": last_asked_field,
#                 "corrections": [],
#                 "should_trigger_recommendation": False,
#                 "intent_groups": [],
#                 "confidence": 0.35,
#             }

#         assistant_message = next_question or default_follow_up_prompt(highest_gap or last_asked_field or "budget")
#         should_trigger = bool(readiness and readiness.get("is_ready"))
#         return {
#             "action": "recommend" if should_trigger else "ask_question",
#             "assistant_message": assistant_message,
#             "state_patch": {},
#             "question_target_field": highest_gap or last_asked_field,
#             "corrections": [],
#             "should_trigger_recommendation": should_trigger,
#             "intent_groups": [],
#             "confidence": 0.35 if user_message else 0.2,
#         }

#     def _load_examples_json(self):
#         path = PROMPTS_DIR / self.EXAMPLES_NAME
#         try:
#             return path.read_text(encoding="utf-8").strip()
#         except Exception:
#             return "[]"

#     def _build_plan_metadata(
#         self,
#         request_ms,
#         total_started_at,
#         planner_result,
#         fallback_used,
#         validation_success,
#         llm_calls,
#     ):
#         stats = dict(getattr(self.llm_client, "stats", {}) or {})
#         usage = dict(stats.get("last_usage") or {})
#         return {
#             "prompt_name": str(stats.get("last_prompt_name") or self.PROMPT_NAME),
#             "prompt_version": str(stats.get("last_prompt_version") or ""),
#             "model": str(stats.get("last_response_model") or getattr(self.llm_client, "model_name", "") or ""),
#             "timeout_sec": stats.get("last_timeout_sec"),
#             "request_ms": round(float(request_ms or 0.0), 2),
#             "total_ms": round((perf_counter() - total_started_at) * 1000, 2),
#             "input_tokens": int(usage.get("input_tokens") or 0),
#             "output_tokens": int(usage.get("output_tokens") or 0),
#             "total_tokens": int(usage.get("total_tokens") or 0),
#             "finish_reason": str(stats.get("last_finish_reason") or ""),
#             "llm_calls": int(llm_calls or 0),
#             "fallback_used": bool(fallback_used),
#             "validation_success": bool(validation_success),
#             "malformed_output": bool(not validation_success and planner_result),
#         }




# import json
# from time import perf_counter

# from ..serializers import ConversationPlannerResultSerializer
# from .clarification import ProcurementClarificationService, default_follow_up_prompt
# from .llm_client import OptionalLLMClient


# class ConversationPlannerService:
#     PROMPT_NAME = "conversation_planner.txt"

#     def __init__(self, llm_client=None, clarification_service=None):
#         self.llm_client = llm_client or OptionalLLMClient()
#         self.clarification_service = clarification_service or ProcurementClarificationService()
#         self.last_plan_metadata = {}

#     def plan_turn(
#         self,
#         user_message: str,
#         state: dict,
#         recent_messages: list[dict],
#         readiness: dict,
#         current_recommendations: list | None = None,
#     ) -> dict:
#         total_started_at = perf_counter()
#         variables = {
#             "user_message": str(user_message or "").strip(),
#             "state_json": json.dumps(state or {}, ensure_ascii=False),
#             "recent_messages_json": json.dumps(recent_messages or [], ensure_ascii=False),
#             "readiness_json": json.dumps(readiness or {}, ensure_ascii=False),
#             "current_recommendations_json": json.dumps(current_recommendations or [], ensure_ascii=False),
#         }
#         request_started_at = perf_counter()
#         planner_result = self.llm_client.invoke_planner(self.PROMPT_NAME, variables) or {}
#         request_ms = round((perf_counter() - request_started_at) * 1000, 2)
#         validated = self._validate_result(planner_result)
#         if validated is not None:
#             self.last_plan_metadata = self._build_plan_metadata(
#                 request_ms=request_ms,
#                 total_started_at=total_started_at,
#                 planner_result=planner_result,
#                 fallback_used=False,
#                 validation_success=True,
#             )
#             return validated
#         fallback = self._fallback_plan(user_message=user_message, readiness=readiness)
#         self.last_plan_metadata = self._build_plan_metadata(
#             request_ms=request_ms,
#             total_started_at=total_started_at,
#             planner_result=planner_result,
#             fallback_used=True,
#             validation_success=False,
#         )
#         return fallback

#     def _validate_result(self, planner_result):
#         serializer = ConversationPlannerResultSerializer(data=planner_result or {})
#         if serializer.is_valid():
#             return serializer.validated_data
#         return None

#     def _fallback_plan(self, user_message, readiness):
#         highest_gap = (readiness or {}).get("highest_priority_missing_field") or ""
#         next_question = str((readiness or {}).get("next_question") or "").strip()
#         assistant_message = next_question or default_follow_up_prompt(highest_gap or "budget")
#         should_trigger = bool(readiness and readiness.get("is_ready"))
#         return {
#             "action": "recommend" if should_trigger else "ask_question",
#             "assistant_message": assistant_message,
#             "state_patch": {},
#             "question_target_field": highest_gap,
#             "corrections": [],
#             "should_trigger_recommendation": should_trigger,
#             "intent_groups": [],
#             "confidence": 0.35 if user_message else 0.2,
#         }

#     def _build_plan_metadata(
#         self,
#         request_ms,
#         total_started_at,
#         planner_result,
#         fallback_used,
#         validation_success,
#     ):
#         stats = dict(getattr(self.llm_client, "stats", {}) or {})
#         usage = dict(stats.get("last_usage") or {})
#         text_calls = int(stats.get("text_calls") or 0)
#         return {
#             "prompt_name": str(stats.get("last_prompt_name") or self.PROMPT_NAME),
#             "prompt_version": str(stats.get("last_prompt_version") or ""),
#             "model": str(stats.get("last_response_model") or getattr(self.llm_client, "model_name", "") or ""),
#             "timeout_sec": stats.get("last_timeout_sec"),
#             "request_ms": round(float(request_ms or 0.0), 2),
#             "total_ms": round((perf_counter() - total_started_at) * 1000, 2),
#             "input_tokens": int(usage.get("input_tokens") or 0),
#             "output_tokens": int(usage.get("output_tokens") or 0),
#             "total_tokens": int(usage.get("total_tokens") or 0),
#             "finish_reason": str(stats.get("last_finish_reason") or ""),
#             "llm_calls": 1 if text_calls else 0,
#             "fallback_used": bool(fallback_used),
#             "validation_success": bool(validation_success),
#             "malformed_output": bool(not validation_success and planner_result),
#         }




#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################




# import json
# from pathlib import Path
# from time import perf_counter

# from ..serializers import ConversationPlannerResultSerializer
# from .clarification import ProcurementClarificationService, default_follow_up_prompt
# from .llm_client import OptionalLLMClient

# PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


# class ConversationPlannerService:
#     PROMPT_NAME = "conversation_planner.txt"
#     EXAMPLES_NAME = "conversation_planner_examples.json"
#     GREETING_TOKENS = {"hi", "hello", "hey", "good morning", "good evening", "good afternoon"}
#     ACK_TOKENS = {"ok", "okay", "sure", "fine", "got it", "understood", "thanks", "thank you"}

#     def __init__(self, llm_client=None, clarification_service=None):
#         self.llm_client = llm_client or OptionalLLMClient()
#         self.clarification_service = clarification_service or ProcurementClarificationService()
#         self.last_plan_metadata = {}

#     def plan_turn(
#         self,
#         user_message: str,
#         state: dict,
#         recent_messages: list[dict],
#         readiness: dict,
#         current_recommendations: list | None = None,
#     ) -> dict:
#         total_started_at = perf_counter()
#         state = dict(state or {})
#         recent_messages = list(recent_messages or [])
#         user_message = str(user_message or "").strip()

#         quick_plan = self._quick_plan(
#             user_message=user_message,
#             state=state,
#             readiness=readiness,
#             recent_messages=recent_messages,
#         )
#         if quick_plan is not None:
#             self.last_plan_metadata = self._build_plan_metadata(
#                 request_ms=0.0,
#                 total_started_at=total_started_at,
#                 planner_result=quick_plan,
#                 fallback_used=False,
#                 validation_success=True,
#                 llm_calls=0,
#             )
#             return quick_plan

#         variables = {
#             "user_message": user_message,
#             "state_json": json.dumps(self._planner_state(state), ensure_ascii=False),
#             "recent_messages_json": json.dumps(recent_messages, ensure_ascii=False),
#             "readiness_json": json.dumps(readiness or {}, ensure_ascii=False),
#             "current_recommendations_json": json.dumps(current_recommendations or [], ensure_ascii=False),
#             "examples_json": self._load_examples_json(),
#         }
#         request_started_at = perf_counter()
#         planner_result = self.llm_client.invoke_planner(self.PROMPT_NAME, variables) or {}
#         request_ms = round((perf_counter() - request_started_at) * 1000, 2)
#         validated = self._validate_result(planner_result)
#         if validated is not None:
#             self.last_plan_metadata = self._build_plan_metadata(
#                 request_ms=request_ms,
#                 total_started_at=total_started_at,
#                 planner_result=planner_result,
#                 fallback_used=False,
#                 validation_success=True,
#                 llm_calls=1,
#             )
#             return validated
#         fallback = self._fallback_plan(
#             user_message=user_message,
#             readiness=readiness,
#             state=state,
#             recent_messages=recent_messages,
#         )
#         self.last_plan_metadata = self._build_plan_metadata(
#             request_ms=request_ms,
#             total_started_at=total_started_at,
#             planner_result=planner_result,
#             fallback_used=True,
#             validation_success=False,
#             llm_calls=1,
#         )
#         return fallback

#     def _planner_state(self, state):
#         state = dict(state or {})
#         return {
#             "requirements": dict(state.get("requirements") or {}),
#             "conversation_meta": dict(state.get("conversation_meta") or {}),
#             "intent_groups": list(state.get("intent_groups") or []),
#         }

#     def _quick_plan(self, user_message, state, readiness, recent_messages):
#         lowered = str(user_message or "").strip().lower()
#         if not lowered:
#             return self._fallback_plan(
#                 user_message=user_message,
#                 readiness=readiness,
#                 state=state,
#                 recent_messages=recent_messages,
#             )

#         if lowered in self.ACK_TOKENS:
#             next_question = str((readiness or {}).get("next_question") or "").strip()
#             if next_question:
#                 return {
#                     "action": "ask_question",
#                     "assistant_message": next_question,
#                     "state_patch": {},
#                     "question_target_field": str((readiness or {}).get("recommended_question_id") or "").strip(),
#                     "corrections": [],
#                     "should_trigger_recommendation": False,
#                     "intent_groups": [],
#                     "confidence": 0.55,
#                 }

#         if lowered in self.GREETING_TOKENS:
#             requirements = dict((state or {}).get("requirements") or {})
#             if not requirements:
#                 return {
#                     "action": "respond",
#                     "assistant_message": (
#                         "Hi. Tell me what you need to buy, who it is for, and your budget, "
#                         "and I will narrow it down quickly."
#                     ),
#                     "state_patch": {},
#                     "question_target_field": "",
#                     "corrections": [],
#                     "should_trigger_recommendation": False,
#                     "intent_groups": [],
#                     "confidence": 0.82,
#                 }

#         return None

#     def _validate_result(self, planner_result):
#         serializer = ConversationPlannerResultSerializer(data=planner_result or {})
#         if serializer.is_valid():
#             return serializer.validated_data
#         return None

#     def _fallback_plan(self, user_message, readiness, state=None, recent_messages=None):
#         state = dict(state or {})
#         conversation_meta = dict(state.get("conversation_meta") or {})
#         highest_gap = str((readiness or {}).get("highest_priority_missing_field") or "").strip()
#         next_question = str((readiness or {}).get("next_question") or "").strip()
#         last_asked_field = str(conversation_meta.get("last_asked_field") or "").strip()
#         lowered = str(user_message or "").strip().lower()

#         if lowered in self.GREETING_TOKENS:
#             return {
#                 "action": "respond",
#                 "assistant_message": (
#                     "Hi. Share what you are planning to buy and any budget or workload details you already know."
#                 ),
#                 "state_patch": {},
#                 "question_target_field": "",
#                 "corrections": [],
#                 "should_trigger_recommendation": False,
#                 "intent_groups": [],
#                 "confidence": 0.45,
#             }

#         if lowered in {"yes", "yeah", "yep", "no", "nope"} and last_asked_field:
#             prompt = next_question or default_follow_up_prompt(last_asked_field)
#             return {
#                 "action": "ask_question",
#                 "assistant_message": prompt,
#                 "state_patch": {},
#                 "question_target_field": last_asked_field,
#                 "corrections": [],
#                 "should_trigger_recommendation": False,
#                 "intent_groups": [],
#                 "confidence": 0.35,
#             }

#         assistant_message = next_question or default_follow_up_prompt(highest_gap or last_asked_field or "budget")
#         should_trigger = bool(readiness and readiness.get("is_ready"))
#         return {
#             "action": "recommend" if should_trigger else "ask_question",
#             "assistant_message": assistant_message,
#             "state_patch": {},
#             "question_target_field": highest_gap or last_asked_field,
#             "corrections": [],
#             "should_trigger_recommendation": should_trigger,
#             "intent_groups": [],
#             "confidence": 0.35 if user_message else 0.2,
#         }

#     def _load_examples_json(self):
#         path = PROMPTS_DIR / self.EXAMPLES_NAME
#         try:
#             return path.read_text(encoding="utf-8").strip()
#         except Exception:
#             return "[]"

#     def _build_plan_metadata(
#         self,
#         request_ms,
#         total_started_at,
#         planner_result,
#         fallback_used,
#         validation_success,
#         llm_calls,
#     ):
#         stats = dict(getattr(self.llm_client, "stats", {}) or {})
#         usage = dict(stats.get("last_usage") or {})
#         return {
#             "prompt_name": str(stats.get("last_prompt_name") or self.PROMPT_NAME),
#             "prompt_version": str(stats.get("last_prompt_version") or ""),
#             "model": str(stats.get("last_response_model") or getattr(self.llm_client, "model_name", "") or ""),
#             "timeout_sec": stats.get("last_timeout_sec"),
#             "request_ms": round(float(request_ms or 0.0), 2),
#             "total_ms": round((perf_counter() - total_started_at) * 1000, 2),
#             "input_tokens": int(usage.get("input_tokens") or 0),
#             "output_tokens": int(usage.get("output_tokens") or 0),
#             "total_tokens": int(usage.get("total_tokens") or 0),
#             "finish_reason": str(stats.get("last_finish_reason") or ""),
#             "llm_calls": int(llm_calls or 0),
#             "fallback_used": bool(fallback_used),
#             "validation_success": bool(validation_success),
#             "malformed_output": bool(not validation_success and planner_result),
#         }




#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################


# import json
# from pathlib import Path
# from time import perf_counter

# from ..serializers import ConversationPlannerResultSerializer
# from .clarification import ProcurementClarificationService, default_follow_up_prompt
# from .llm_client import OptionalLLMClient

# PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


# class ConversationPlannerService:
#     PROMPT_NAME = "conversation_planner.txt"
#     EXAMPLES_NAME = "conversation_planner_examples.json"
#     QUESTION_REPHRASE_PROMPT_NAME = "clarification_question_rephrase.txt"
#     GREETING_TOKENS = {"hi", "hello", "hey", "good morning", "good evening", "good afternoon"}
#     ACK_TOKENS = {"ok", "okay", "sure", "fine", "got it", "understood", "thanks", "thank you"}
#     SUPPORT_CONTEXT = {
#         "supported_categories": [
#             "laptops",
#             "desktops",
#             "servers",
#             "networking",
#             "printers",
#             "accessories",
#         ],
#         "accessory_examples": ["keyboards", "mouse", "headsets", "docks", "webcams", "monitors"],
#         "supported_followups": [
#             "clarify missing procurement details",
#             "summarize the latest recommendation",
#             "refine the shortlist with a new budget or requirement change",
#         ],
#         "out_of_scope_examples": ["jokes", "songs", "weather", "timers", "article summaries"],
#     }

#     def __init__(self, llm_client=None, clarification_service=None):
#         self.llm_client = llm_client or OptionalLLMClient()
#         self.clarification_service = clarification_service or ProcurementClarificationService()
#         self.last_plan_metadata = {}

#     def plan_turn(
#         self,
#         user_message: str,
#         state: dict,
#         recent_messages: list[dict],
#         readiness: dict,
#         current_recommendations: list | None = None,
#     ) -> dict:
#         total_started_at = perf_counter()
#         state = dict(state or {})
#         recent_messages = list(recent_messages or [])
#         user_message = str(user_message or "").strip()

#         quick_plan = self._quick_plan(
#             user_message=user_message,
#             state=state,
#             readiness=readiness,
#             recent_messages=recent_messages,
#         )
#         if quick_plan is not None:
#             self.last_plan_metadata = self._build_plan_metadata(
#                 request_ms=0.0,
#                 total_started_at=total_started_at,
#                 planner_result=quick_plan,
#                 fallback_used=False,
#                 validation_success=True,
#                 llm_calls=0,
#             )
#             return quick_plan

#         variables = {
#             "user_message": user_message,
#             "state_json": json.dumps(self._planner_state(state), ensure_ascii=False),
#             "recent_messages_json": json.dumps(recent_messages, ensure_ascii=False),
#             "readiness_json": json.dumps(readiness or {}, ensure_ascii=False),
#             "current_recommendations_json": json.dumps(current_recommendations or [], ensure_ascii=False),
#             "examples_json": self._load_examples_json(),
#             "support_json": json.dumps(self.SUPPORT_CONTEXT, ensure_ascii=False),
#         }
#         request_started_at = perf_counter()
#         planner_result = self.llm_client.invoke_planner(self.PROMPT_NAME, variables) or {}
#         request_ms = round((perf_counter() - request_started_at) * 1000, 2)
#         validated = self._validate_result(planner_result)
#         if validated is not None:
#             self.last_plan_metadata = self._build_plan_metadata(
#                 request_ms=request_ms,
#                 total_started_at=total_started_at,
#                 planner_result=planner_result,
#                 fallback_used=False,
#                 validation_success=True,
#                 llm_calls=1,
#             )
#             return validated
#         fallback = self._fallback_plan(
#             user_message=user_message,
#             readiness=readiness,
#             state=state,
#             recent_messages=recent_messages,
#         )
#         self.last_plan_metadata = self._build_plan_metadata(
#             request_ms=request_ms,
#             total_started_at=total_started_at,
#             planner_result=planner_result,
#             fallback_used=True,
#             validation_success=False,
#             llm_calls=1,
#         )
#         return fallback

#     def rephrase_clarification_question(
#         self,
#         question_target_field: str,
#         canonical_question: str,
#         state: dict | None = None,
#         acknowledgement: str = "",
#     ) -> str:
#         field = str(question_target_field or "").strip()
#         canonical = str(canonical_question or "").strip()
#         if not field or not canonical:
#             return canonical
#         if not self.llm_client or not self.llm_client.is_available():
#             return canonical

#         state = dict(state or {})
#         requirements = dict(state.get("requirements") or {})
#         conversation_meta = dict(state.get("conversation_meta") or {})
#         variables = {
#             "question_target_field": field,
#             "canonical_question": canonical,
#             "acknowledgement": str(acknowledgement or "").strip(),
#             "conversation_brief": str(conversation_meta.get("conversation_brief") or "").strip(),
#             "preferred_categories_json": json.dumps(requirements.get("preferred_categories") or [], ensure_ascii=False),
#             "workloads_json": json.dumps(requirements.get("workloads") or [], ensure_ascii=False),
#             "team_size": str(requirements.get("team_size") or requirements.get("quantity") or "").strip(),
#             "budget": str(requirements.get("budget") or "").strip(),
#         }
#         result = self.llm_client.invoke_text(
#             self.QUESTION_REPHRASE_PROMPT_NAME,
#             variables,
#             request_options={
#                 "temperature": 0,
#                 "timeout_sec": 2,
#                 "max_tokens": 80,
#                 "reasoning_effort": "low",
#             },
#         )
#         return self._sanitize_rephrased_question(result, canonical)

#     def _sanitize_rephrased_question(self, text, canonical):
#         candidate = str(text or "").strip()
#         if not candidate:
#             return canonical
#         if candidate.startswith("\"") and candidate.endswith("\"") and len(candidate) >= 2:
#             candidate = candidate[1:-1].strip()
#         candidate = " ".join(candidate.replace("\n", " ").split())
#         if not candidate:
#             return canonical
#         if len(candidate) > 180:
#             return canonical
#         if candidate.count("?") > 2:
#             return canonical
#         if ":" in candidate and len(candidate.split()) <= 3:
#             return canonical
#         if not candidate.endswith("?"):
#             candidate = candidate.rstrip(". ") + "?"
#         return candidate

#     def _planner_state(self, state):
#         state = dict(state or {})
#         return {
#             "requirements": dict(state.get("requirements") or {}),
#             "conversation_meta": dict(state.get("conversation_meta") or {}),
#             "intent_groups": list(state.get("intent_groups") or []),
#         }

#     def _quick_plan(self, user_message, state, readiness, recent_messages):
#         lowered = str(user_message or "").strip().lower()
#         if not lowered:
#             return self._fallback_plan(
#                 user_message=user_message,
#                 readiness=readiness,
#                 state=state,
#                 recent_messages=recent_messages,
#             )

#         llm_available = bool(self.llm_client and self.llm_client.is_available())
#         if llm_available:
#             return None

#         if lowered in self.ACK_TOKENS:
#             next_question = str((readiness or {}).get("next_question") or "").strip()
#             if next_question:
#                 return {
#                     "action": "ask_question",
#                     "assistant_message": next_question,
#                     "state_patch": {},
#                     "question_target_field": str((readiness or {}).get("recommended_question_id") or "").strip(),
#                     "corrections": [],
#                     "should_trigger_recommendation": False,
#                     "intent_groups": [],
#                     "confidence": 0.55,
#                 }

#         if lowered in self.GREETING_TOKENS:
#             requirements = dict((state or {}).get("requirements") or {})
#             if not requirements:
#                 return {
#                     "action": "respond",
#                     "assistant_message": (
#                         "Hi. Tell me what you need to buy, who it is for, and your budget, "
#                         "and I will narrow it down quickly."
#                     ),
#                     "state_patch": {},
#                     "question_target_field": "",
#                     "corrections": [],
#                     "should_trigger_recommendation": False,
#                     "intent_groups": [],
#                     "confidence": 0.82,
#                 }

#         return None

#     def _validate_result(self, planner_result):
#         serializer = ConversationPlannerResultSerializer(data=planner_result or {})
#         if serializer.is_valid():
#             return serializer.validated_data
#         return None

#     def _fallback_plan(self, user_message, readiness, state=None, recent_messages=None):
#         state = dict(state or {})
#         conversation_meta = dict(state.get("conversation_meta") or {})
#         highest_gap = str((readiness or {}).get("highest_priority_missing_field") or "").strip()
#         next_question = str((readiness or {}).get("next_question") or "").strip()
#         last_asked_field = str(conversation_meta.get("last_asked_field") or "").strip()
#         lowered = str(user_message or "").strip().lower()

#         if lowered in self.GREETING_TOKENS:
#             return {
#                 "action": "respond",
#                 "assistant_message": (
#                     "Hi. Share what you are planning to buy and any budget or workload details you already know."
#                 ),
#                 "state_patch": {},
#                 "question_target_field": "",
#                 "corrections": [],
#                 "should_trigger_recommendation": False,
#                 "intent_groups": [],
#                 "confidence": 0.45,
#             }

#         if lowered in {"yes", "yeah", "yep", "no", "nope"} and last_asked_field:
#             prompt = next_question or default_follow_up_prompt(last_asked_field)
#             return {
#                 "action": "ask_question",
#                 "assistant_message": prompt,
#                 "state_patch": {},
#                 "question_target_field": last_asked_field,
#                 "corrections": [],
#                 "should_trigger_recommendation": False,
#                 "intent_groups": [],
#                 "confidence": 0.35,
#             }

#         assistant_message = next_question or default_follow_up_prompt(highest_gap or last_asked_field or "budget")
#         should_trigger = bool(readiness and readiness.get("is_ready"))
#         return {
#             "action": "recommend" if should_trigger else "ask_question",
#             "assistant_message": assistant_message,
#             "state_patch": {},
#             "question_target_field": highest_gap or last_asked_field,
#             "corrections": [],
#             "should_trigger_recommendation": should_trigger,
#             "intent_groups": [],
#             "confidence": 0.35 if user_message else 0.2,
#         }

#     def _load_examples_json(self):
#         path = PROMPTS_DIR / self.EXAMPLES_NAME
#         try:
#             return path.read_text(encoding="utf-8").strip()
#         except Exception:
#             return "[]"

#     def _build_plan_metadata(
#         self,
#         request_ms,
#         total_started_at,
#         planner_result,
#         fallback_used,
#         validation_success,
#         llm_calls,
#     ):
#         stats = dict(getattr(self.llm_client, "stats", {}) or {})
#         usage = dict(stats.get("last_usage") or {})
#         return {
#             "prompt_name": str(stats.get("last_prompt_name") or self.PROMPT_NAME),
#             "prompt_version": str(stats.get("last_prompt_version") or ""),
#             "model": str(stats.get("last_response_model") or getattr(self.llm_client, "model_name", "") or ""),
#             "timeout_sec": stats.get("last_timeout_sec"),
#             "request_ms": round(float(request_ms or 0.0), 2),
#             "total_ms": round((perf_counter() - total_started_at) * 1000, 2),
#             "input_tokens": int(usage.get("input_tokens") or 0),
#             "output_tokens": int(usage.get("output_tokens") or 0),
#             "total_tokens": int(usage.get("total_tokens") or 0),
#             "finish_reason": str(stats.get("last_finish_reason") or ""),
#             "llm_calls": int(llm_calls or 0),
#             "fallback_used": bool(fallback_used),
#             "validation_success": bool(validation_success),
#             "malformed_output": bool(not validation_success and planner_result),
#         }





import json
from pathlib import Path
from time import perf_counter

from ..serializers import ConversationPlannerResultSerializer
from .clarification import ProcurementClarificationService, default_follow_up_prompt
from .llm_client import OptionalLLMClient

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


class ConversationPlannerService:
    PROMPT_NAME = "conversation_planner.txt"
    INTENT_ROUTER_PROMPT_NAME = "intent_router.txt"
    EXAMPLES_NAME = "conversation_planner_examples.json"
    QUESTION_REPHRASE_PROMPT_NAME = "clarification_question_rephrase.txt"
    GREETING_TOKENS = {"hi", "hello", "hey", "good morning", "good evening", "good afternoon"}
    ACK_TOKENS = {"ok", "okay", "sure", "fine", "got it", "understood", "thanks", "thank you"}
    MAX_RECENT_MESSAGES = 4
    MAX_ROUTER_MESSAGES = 3
    MAX_MESSAGE_CHARS = 220
    MAX_ROUTER_MESSAGE_CHARS = 160
    MAX_RECOMMENDATIONS = 3
    REQUIREMENT_FIELDS = (
        "preferred_category",
        "preferred_categories",
        "industry",
        "business_type",
        "team_size",
        "quantity",
        "workloads",
        "application_signals",
        "capability_tags",
        "budget",
        "budget_scope",
        "growth_expectation",
        "performance_priority",
        "purchase_scope",
        "rollout_type",
        "replacement_mode",
        "portability_need",
        "support_expectation",
        "availability_need",
        "existing_infrastructure",
        "requested_ram_gb",
        "requested_storage_gb",
        "minimum_warranty_years",
        "required_port_count",
        "required_throughput_mbps",
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
        "timeline",
    )
    CONVERSATION_META_FIELDS = (
        "last_asked_field",
        "last_assistant_action",
        "last_assistant_message",
        "recommended_question_id",
        "conversation_brief",
    )
    SUPPORT_CONTEXT = {
        "supported_categories": [
            "laptops",
            "desktops",
            "servers",
            "networking",
            "printers",
            "accessories",
        ],
        "accessory_examples": ["keyboards", "mouse", "headsets", "docks", "webcams", "monitors"],
        "supported_followups": [
            "clarify missing procurement details",
            "summarize the latest recommendation",
            "refine the shortlist with a new budget or requirement change",
        ],
        "out_of_scope_examples": ["jokes", "songs", "weather", "timers", "article summaries"],
    }

    def __init__(self, llm_client=None, clarification_service=None):
        self.llm_client = llm_client or OptionalLLMClient()
        self.clarification_service = clarification_service or ProcurementClarificationService()
        self.last_plan_metadata = {}

    def route_turn(
        self,
        user_message: str,
        state: dict,
        recent_messages: list[dict],
        readiness: dict,
        current_recommendations: list | None = None,
    ) -> dict | None:
        total_started_at = perf_counter()
        state = dict(state or {})
        recent_messages = list(recent_messages or [])
        user_message = str(user_message or "").strip()
        if not user_message:
            return None
        if not self.llm_client or not self.llm_client.is_available():
            return None

        variables = {
            "user_message": user_message,
            "state_json": json.dumps(self._planner_state(state), ensure_ascii=False),
            "recent_messages_json": json.dumps(
                self._compact_recent_messages(
                    recent_messages,
                    max_messages=self.MAX_ROUTER_MESSAGES,
                    max_chars=self.MAX_ROUTER_MESSAGE_CHARS,
                ),
                ensure_ascii=False,
            ),
            "readiness_json": json.dumps(readiness or {}, ensure_ascii=False),
            "current_recommendations_json": json.dumps(
                self._compact_recommendations(current_recommendations),
                ensure_ascii=False,
            ),
            "support_json": json.dumps(self.SUPPORT_CONTEXT, ensure_ascii=False),
        }
        request_started_at = perf_counter()
        router_result = self.llm_client.invoke_json(
            self.INTENT_ROUTER_PROMPT_NAME,
            variables,
            request_options={
                "temperature": 0,
                "timeout_sec": 2,
                "max_tokens": 180,
                "reasoning_effort": "low",
            },
        ) or {}
        request_ms = round((perf_counter() - request_started_at) * 1000, 2)
        validated = self._validate_route_result(router_result)
        if validated is not None:
            self.last_plan_metadata = self._build_plan_metadata(
                request_ms=request_ms,
                total_started_at=total_started_at,
                planner_result=router_result,
                fallback_used=False,
                validation_success=True,
                llm_calls=1,
            )
            return validated
        return None

    def plan_turn(
        self,
        user_message: str,
        state: dict,
        recent_messages: list[dict],
        readiness: dict,
        current_recommendations: list | None = None,
    ) -> dict:
        total_started_at = perf_counter()
        state = dict(state or {})
        recent_messages = list(recent_messages or [])
        user_message = str(user_message or "").strip()

        quick_plan = self._quick_plan(
            user_message=user_message,
            state=state,
            readiness=readiness,
            recent_messages=recent_messages,
        )
        if quick_plan is not None:
            self.last_plan_metadata = self._build_plan_metadata(
                request_ms=0.0,
                total_started_at=total_started_at,
                planner_result=quick_plan,
                fallback_used=False,
                validation_success=True,
                llm_calls=0,
            )
            return quick_plan

        variables = {
            "user_message": user_message,
            "state_json": json.dumps(self._planner_state(state), ensure_ascii=False),
            "recent_messages_json": json.dumps(self._compact_recent_messages(recent_messages), ensure_ascii=False),
            "readiness_json": json.dumps(readiness or {}, ensure_ascii=False),
            "current_recommendations_json": json.dumps(
                self._compact_recommendations(current_recommendations),
                ensure_ascii=False,
            ),
            "examples_json": self._load_examples_json(),
            "support_json": json.dumps(self.SUPPORT_CONTEXT, ensure_ascii=False),
        }
        request_started_at = perf_counter()
        planner_result = self.llm_client.invoke_planner(self.PROMPT_NAME, variables) or {}
        request_ms = round((perf_counter() - request_started_at) * 1000, 2)
        validated = self._validate_result(planner_result)
        if validated is not None:
            self.last_plan_metadata = self._build_plan_metadata(
                request_ms=request_ms,
                total_started_at=total_started_at,
                planner_result=planner_result,
                fallback_used=False,
                validation_success=True,
                llm_calls=1,
            )
            return validated
        fallback = self._fallback_plan(
            user_message=user_message,
            readiness=readiness,
            state=state,
            recent_messages=recent_messages,
        )
        self.last_plan_metadata = self._build_plan_metadata(
            request_ms=request_ms,
            total_started_at=total_started_at,
            planner_result=planner_result,
            fallback_used=True,
            validation_success=False,
            llm_calls=1,
        )
        return fallback

    def rephrase_clarification_question(
        self,
        question_target_field: str,
        canonical_question: str,
        state: dict | None = None,
        acknowledgement: str = "",
    ) -> str:
        field = str(question_target_field or "").strip()
        canonical = str(canonical_question or "").strip()
        if not field or not canonical:
            return canonical
        if not self.llm_client or not self.llm_client.is_available():
            return canonical

        state = dict(state or {})
        requirements = dict(state.get("requirements") or {})
        conversation_meta = dict(state.get("conversation_meta") or {})
        variables = {
            "question_target_field": field,
            "canonical_question": canonical,
            "acknowledgement": str(acknowledgement or "").strip(),
            "conversation_brief": str(conversation_meta.get("conversation_brief") or "").strip(),
            "preferred_categories_json": json.dumps(requirements.get("preferred_categories") or [], ensure_ascii=False),
            "workloads_json": json.dumps(requirements.get("workloads") or [], ensure_ascii=False),
            "team_size": str(requirements.get("team_size") or requirements.get("quantity") or "").strip(),
            "budget": str(requirements.get("budget") or "").strip(),
        }
        result = self.llm_client.invoke_text(
            self.QUESTION_REPHRASE_PROMPT_NAME,
            variables,
            request_options={
                "temperature": 0,
                "timeout_sec": 2,
                "max_tokens": 80,
                "reasoning_effort": "low",
            },
        )
        return self._sanitize_rephrased_question(result, canonical)

    def _sanitize_rephrased_question(self, text, canonical):
        candidate = str(text or "").strip()
        if not candidate:
            return canonical
        if candidate.startswith("\"") and candidate.endswith("\"") and len(candidate) >= 2:
            candidate = candidate[1:-1].strip()
        candidate = " ".join(candidate.replace("\n", " ").split())
        if not candidate:
            return canonical
        if len(candidate) > 180:
            return canonical
        if candidate.count("?") > 2:
            return canonical
        if ":" in candidate and len(candidate.split()) <= 3:
            return canonical
        if not candidate.endswith("?"):
            candidate = candidate.rstrip(". ") + "?"
        return candidate

    def _planner_state(self, state):
        state = dict(state or {})
        return {
            "requirements": self._compact_requirements(state.get("requirements") or {}),
            "conversation_meta": self._compact_conversation_meta(state.get("conversation_meta") or {}),
            "intent_groups": list(state.get("intent_groups") or []),
        }

    def _compact_requirements(self, requirements):
        compact = {}
        requirements = dict(requirements or {})
        for field in self.REQUIREMENT_FIELDS:
            value = requirements.get(field)
            if value in (None, "", [], {}, False):
                continue
            compact[field] = value
        return compact

    def _compact_conversation_meta(self, conversation_meta):
        compact = {}
        conversation_meta = dict(conversation_meta or {})
        for field in self.CONVERSATION_META_FIELDS:
            value = conversation_meta.get(field)
            if value in (None, "", [], {}, False):
                continue
            compact[field] = value
        return compact

    def _compact_recent_messages(self, recent_messages, max_messages=None, max_chars=None):
        max_messages = int(max_messages or self.MAX_RECENT_MESSAGES)
        max_chars = int(max_chars or self.MAX_MESSAGE_CHARS)
        compact = []
        for message in list(recent_messages or [])[-max_messages:]:
            item = {
                "role": str(message.get("role") or "").strip(),
                "content": self._trim_text(message.get("content"), max_chars=max_chars),
                "message_type": str(message.get("message_type") or "").strip(),
            }
            question_target = str(message.get("question_target_field") or "").strip()
            response_mode = str(message.get("response_mode") or "").strip()
            if question_target:
                item["question_target_field"] = question_target
            if response_mode:
                item["response_mode"] = response_mode
            compact.append(item)
        return compact

    def _compact_recommendations(self, current_recommendations):
        compact = []
        for item in list(current_recommendations or [])[: self.MAX_RECOMMENDATIONS]:
            compact_item = {}
            for field in ("name", "category", "price", "currency", "short_reason", "reason"):
                value = item.get(field) if isinstance(item, dict) else None
                if value in (None, "", [], {}, False):
                    continue
                compact_item[field] = self._trim_text(value) if isinstance(value, str) else value
            if compact_item:
                compact.append(compact_item)
        return compact

    def _trim_text(self, value, max_chars=None):
        text = " ".join(str(value or "").split())
        max_chars = int(max_chars or self.MAX_MESSAGE_CHARS)
        if len(text) <= max_chars:
            return text
        return text[: max_chars - 1].rstrip() + "…"

    def _quick_plan(self, user_message, state, readiness, recent_messages):
        lowered = str(user_message or "").strip().lower()
        if not lowered:
            return self._fallback_plan(
                user_message=user_message,
                readiness=readiness,
                state=state,
                recent_messages=recent_messages,
            )

        # Pure social turns (greetings, acks) are handled here regardless of LLM
        # availability — they don't carry procurement content so sending them to the
        # full planner LLM wastes a round-trip and can confuse state.
        if lowered in self.GREETING_TOKENS:
            requirements = dict((state or {}).get("requirements") or {})
            if not requirements:
                return {
                    "action": "respond",
                    "assistant_message": (
                        "Hi. Tell me what you need to buy, who it is for, and your budget, "
                        "and I will narrow it down quickly."
                    ),
                    "state_patch": {},
                    "question_target_field": "",
                    "corrections": [],
                    "should_trigger_recommendation": False,
                    "intent_groups": [],
                    "confidence": 0.88,
                }

        if lowered in self.ACK_TOKENS:
            next_question = str((readiness or {}).get("next_question") or "").strip()
            if next_question:
                return {
                    "action": "ask_question",
                    "assistant_message": next_question,
                    "state_patch": {},
                    "question_target_field": str((readiness or {}).get("recommended_question_id") or "").strip(),
                    "corrections": [],
                    "should_trigger_recommendation": False,
                    "intent_groups": [],
                    "confidence": 0.72,
                }

        # For substantive procurement turns, delegate to the full LLM planner when
        # available. The fallback path handles the no-LLM case.
        llm_available = bool(self.llm_client and self.llm_client.is_available())
        if llm_available:
            return None

    def _validate_route_result(self, router_result):
        router_result = dict(router_result or {})
        route = str(router_result.get("route") or "").strip().lower()
        if route not in {"planner", "direct_answer", "light_reply", "out_of_scope"}:
            return None
        assistant_message = str(router_result.get("assistant_message") or "").strip()
        question_target_field = str(router_result.get("question_target_field") or "").strip()
        try:
            confidence = float(router_result.get("confidence") or 0.0)
        except (TypeError, ValueError):
            return None
        confidence = max(0.0, min(confidence, 1.0))
        return {
            "route": route,
            "assistant_message": assistant_message,
            "question_target_field": question_target_field,
            "confidence": confidence,
        }

    def _validate_result(self, planner_result):
        serializer = ConversationPlannerResultSerializer(data=planner_result or {})
        if serializer.is_valid():
            return serializer.validated_data
        return None

    def _fallback_plan(self, user_message, readiness, state=None, recent_messages=None):
        state = dict(state or {})
        conversation_meta = dict(state.get("conversation_meta") or {})
        highest_gap = str((readiness or {}).get("highest_priority_missing_field") or "").strip()
        next_question = str((readiness or {}).get("next_question") or "").strip()
        last_asked_field = str(conversation_meta.get("last_asked_field") or "").strip()
        lowered = str(user_message or "").strip().lower()

        if lowered in self.GREETING_TOKENS:
            return {
                "action": "respond",
                "assistant_message": (
                    "Hi. Share what you are planning to buy and any budget or workload details you already know."
                ),
                "state_patch": {},
                "question_target_field": "",
                "corrections": [],
                "should_trigger_recommendation": False,
                "intent_groups": [],
                "confidence": 0.45,
            }

        if lowered in {"yes", "yeah", "yep", "no", "nope"} and last_asked_field:
            prompt = next_question or default_follow_up_prompt(last_asked_field)
            return {
                "action": "ask_question",
                "assistant_message": prompt,
                "state_patch": {},
                "question_target_field": last_asked_field,
                "corrections": [],
                "should_trigger_recommendation": False,
                "intent_groups": [],
                "confidence": 0.35,
            }

        assistant_message = next_question or default_follow_up_prompt(highest_gap or last_asked_field or "budget")
        should_trigger = bool(readiness and readiness.get("is_ready"))
        return {
            "action": "recommend" if should_trigger else "ask_question",
            "assistant_message": assistant_message,
            "state_patch": {},
            "question_target_field": highest_gap or last_asked_field,
            "corrections": [],
            "should_trigger_recommendation": should_trigger,
            "intent_groups": [],
            "confidence": 0.35 if user_message else 0.2,
        }

    def _load_examples_json(self):
        path = PROMPTS_DIR / self.EXAMPLES_NAME
        try:
            return path.read_text(encoding="utf-8").strip()
        except Exception:
            return "[]"

    def _build_plan_metadata(
        self,
        request_ms,
        total_started_at,
        planner_result,
        fallback_used,
        validation_success,
        llm_calls,
    ):
        stats = dict(getattr(self.llm_client, "stats", {}) or {})
        usage = dict(stats.get("last_usage") or {})
        return {
            "prompt_name": str(stats.get("last_prompt_name") or self.PROMPT_NAME),
            "prompt_version": str(stats.get("last_prompt_version") or ""),
            "model": str(stats.get("last_response_model") or getattr(self.llm_client, "model_name", "") or ""),
            "timeout_sec": stats.get("last_timeout_sec"),
            "request_ms": round(float(request_ms or 0.0), 2),
            "total_ms": round((perf_counter() - total_started_at) * 1000, 2),
            "input_tokens": int(usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("output_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
            "finish_reason": str(stats.get("last_finish_reason") or ""),
            "llm_calls": int(llm_calls or 0),
            "fallback_used": bool(fallback_used),
            "validation_success": bool(validation_success),
            "malformed_output": bool(not validation_success and planner_result),
        }
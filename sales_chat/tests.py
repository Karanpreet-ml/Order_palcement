import asyncio
import json
import os
import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from asgiref.testing import ApplicationCommunicator
from django.test import TestCase

from ai_configurator.catalog.services.connection import get_catalog_client

import ai_configurator.sales_chat.websocket_consumer as websocket_consumer
from ai_configurator.procurement.models import (
    ProcurementConversationMessage,
    ProcurementConversationSession,
)
from ai_configurator.procurement.services.conversation_planner import ConversationPlannerService
from ai_configurator.procurement.services.requirement_guard import RequirementGuardService
from ai_configurator.procurement.services.requirement_state_manager import RequirementStateManager
from ai_configurator.procurement.services.requirement_extraction import RequirementExtractionService
from ai_configurator.procurement.services.recommendation_service import ProcurementRecommendationService
from ai_configurator.sales_chat.services.background_dispatcher import BackgroundDispatcher
from ai_configurator.sales_chat.services.chat_orchestrator import ChatOrchestrator
from ai_configurator.sales_chat.services.chat_session_service import ChatSessionService
from ai_configurator.sales_chat.services.response_contract import ResponseContractAdapter
from ai_configurator.sales_chat.services.sales_service import SalesService
from ai_configurator.sales_chat.services.ui_guidance import build_narrowing_guidance
from ai_configurator.sales_chat.websocket_consumer import SalesBotConsumer
from test_support.catalog_dataset import build_catalog_repository
from test_support.fake_catalog import build_sample_catalog_repository

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from procurement_chat_runtime import build_procurement_chat_runtime


def build_recommendation_service(catalog_size="small"):
    if str(catalog_size or "").strip().lower() == "small":
        repository = build_sample_catalog_repository()
    else:
        repository = build_catalog_repository(catalog_size)
    service = ProcurementRecommendationService(catalog_repository=repository)
    service.extraction_service.llm_client.api_key = ""
    service.explanation_service.llm_client.api_key = ""
    service.followup_service.llm_client.api_key = ""
    return service



def build_sales_service(catalog_size="small", channel="websocket", include_llm_stats=True):
    recommendation_service = build_recommendation_service(catalog_size=catalog_size)
    adapter = ResponseContractAdapter()
    orchestrator = ChatOrchestrator(
        chat_session_service=ChatSessionService(),
        planner_service=ConversationPlannerService(),
        requirement_state_manager=RequirementStateManager(),
        requirement_guard_service=RequirementGuardService(),
        recommendation_service=recommendation_service,
        response_contract_adapter=adapter,
        background_dispatcher=BackgroundDispatcher(
            response_contract_adapter=adapter,
            recommendation_service=recommendation_service,
        ),
        include_llm_stats=include_llm_stats,
    )
    return SalesService(
        chat_orchestrator=orchestrator,
        channel=channel,
        include_llm_stats=include_llm_stats,
    )



def disable_runtime_llms(service):
    recommendation_service = getattr(service, "recommendation_service", None)
    if recommendation_service is None:
        recommendation_service = getattr(
            getattr(service, "chat_orchestrator", None),
            "recommendation_service",
            None,
        )
    if recommendation_service is not None:
        if getattr(recommendation_service, "extraction_service", None) is not None:
            recommendation_service.extraction_service.llm_client.api_key = ""
        if getattr(recommendation_service, "followup_service", None) is not None:
            recommendation_service.followup_service.llm_client.api_key = ""
        if getattr(recommendation_service, "explanation_service", None) is not None:
            recommendation_service.explanation_service.llm_client.api_key = ""
    planner_service = getattr(getattr(service, "chat_orchestrator", None), "planner_service", None)
    if getattr(planner_service, "llm_client", None) is not None:
        planner_service.llm_client.api_key = ""


class ChatSessionServicePersistenceTests(TestCase):
    def setUp(self):
        self.service = ChatSessionService()

    def test_chat_session_service_persists_state_and_messages(self):
        session = self.service.get_or_create_session(
            "session-persistence-1",
            channel="websocket",
            store_id="store-a",
            user_id="user-a",
            business_id="business-a",
        )

        self.assertEqual(
            ProcurementConversationSession.objects.filter(conversation_id=session.conversation_id).count(),
            1,
        )
        self.assertEqual(session.transport_session_key, "session-persistence-1")

        state = {"requirements": {"preferred_category": "laptops", "quantity": 5}}
        self.service.save_state(session.conversation_id, state)
        self.service._cache_delete(self.service._state_cache_key(session.conversation_id))

        cold_state = self.service.load_state(session.conversation_id)
        self.assertEqual(cold_state, state)
        self.assertEqual(self.service.last_cache_result, "miss")

        warm_state = self.service.load_state(session.conversation_id)
        self.assertEqual(warm_state, state)
        self.assertEqual(self.service.last_cache_result, "hit")

        row = self.service.append_message(
            session.conversation_id,
            role=ProcurementConversationMessage.ROLE_ASSISTANT,
            content="Need a few more details",
            meta={"phase": "persistence"},
            message_type=ProcurementConversationMessage.TYPE_QUESTION,
        )
        history = self.service.recent_messages(session.conversation_id, limit=5)

        self.assertEqual(row.message_type, ProcurementConversationMessage.TYPE_QUESTION)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["content"], "Need a few more details")
        self.assertEqual(history[0]["meta"]["phase"], "persistence")

    def test_chat_session_service_reuses_transport_key_and_updates_status(self):
        session = self.service.get_or_create_session("stable-transport-id", channel="websocket", store_id="store-a")
        self.service.mark_recommended(session.conversation_id, decision_trace_id="trace-1")

        recommended = ProcurementConversationSession.objects.get(conversation_id=session.conversation_id)
        self.assertEqual(recommended.status, ProcurementConversationSession.STATUS_RECOMMENDED)
        self.assertEqual(recommended.last_decision_trace_id, "trace-1")

        reopened = self.service.get_or_create_session("stable-transport-id", channel="rest", store_id="store-b")
        self.assertEqual(reopened.conversation_id, session.conversation_id)

        refreshed = ProcurementConversationSession.objects.get(conversation_id=session.conversation_id)
        self.assertEqual(refreshed.status, ProcurementConversationSession.STATUS_ACTIVE)
        self.assertEqual(refreshed.channel, "rest")
        self.assertEqual(refreshed.store_id, "store-b")

        self.service.append_message(
            session.conversation_id,
            role=ProcurementConversationMessage.ROLE_USER,
            content="User message",
        )
        self.service.reset_session(session.conversation_id)

        reset = ProcurementConversationSession.objects.get(conversation_id=session.conversation_id)
        self.assertEqual(reset.status, ProcurementConversationSession.STATUS_ACTIVE)
        self.assertEqual(reset.current_state, {})
        self.assertEqual(reset.last_decision_trace_id, "")
        self.assertFalse(
            ProcurementConversationMessage.objects.filter(conversation__conversation_id=session.conversation_id).exists()
        )

        self.service.close_session(session.conversation_id)
        closed = ProcurementConversationSession.objects.get(conversation_id=session.conversation_id)
        self.assertEqual(closed.status, ProcurementConversationSession.STATUS_CLOSED)

    def test_chat_session_service_rebinds_transport_key_when_reconnecting_by_conversation_id(self):
        initial = self.service.get_or_create_session("chan-ephemeral-1", channel="websocket", store_id="store-a")

        reconnect_handle = SimpleNamespace(
            conversation_lookup_id=initial.conversation_id,
            transport_session_id=f"conversation:{initial.conversation_id}",
            channel_name="chan-ephemeral-2",
        )
        resumed = self.service.get_or_create_session(reconnect_handle, channel="websocket", store_id="store-a")

        self.assertEqual(resumed.conversation_id, initial.conversation_id)
        refreshed = ProcurementConversationSession.objects.get(conversation_id=initial.conversation_id)
        self.assertEqual(refreshed.transport_session_key, f"conversation:{initial.conversation_id}")


class SalesServiceEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.service = build_sales_service(catalog_size="small")

    def test_default_sales_service_uses_fake_catalog_when_mongo_is_unconfigured(self):
        original_catalog_uri = os.environ.get("CATALOG_MONGODB_URI")
        original_products_uri = os.environ.get("PRODUCTS_MONGODB_URI")
        original_catalog_size = os.environ.get("PROCUREMENT_FAKE_CATALOG_SIZE")
        try:
            os.environ.pop("CATALOG_MONGODB_URI", None)
            os.environ.pop("PRODUCTS_MONGODB_URI", None)
            os.environ["PROCUREMENT_FAKE_CATALOG_SIZE"] = "small"
            get_catalog_client.cache_clear()

            service = SalesService()
            service.extraction_service.llm_client.api_key = ""
            service.followup_service.llm_client.api_key = ""
            service.recommendation_service.explanation_service.llm_client.api_key = ""

            payload = service.get_response_payload(
                "We need laptops for 15 software developers under 6500 each",
                "session-default-runtime",
            )

            self.assertEqual(payload["response_type"], "recommendation")
            self.assertEqual(payload["recommendations"][0]["name"], "Developer Pro 15")
        finally:
            if original_catalog_uri is None:
                os.environ.pop("CATALOG_MONGODB_URI", None)
            else:
                os.environ["CATALOG_MONGODB_URI"] = original_catalog_uri
            if original_products_uri is None:
                os.environ.pop("PRODUCTS_MONGODB_URI", None)
            else:
                os.environ["PRODUCTS_MONGODB_URI"] = original_products_uri
            if original_catalog_size is None:
                os.environ.pop("PROCUREMENT_FAKE_CATALOG_SIZE", None)
            else:
                os.environ["PROCUREMENT_FAKE_CATALOG_SIZE"] = original_catalog_size
            get_catalog_client.cache_clear()

    def test_sales_service_extracts_meaningful_procurement_brief_without_llm(self):
        session_id = "session-rich"

        welcome = self.service.get_response("", session_id)
        self.assertIn("Tell me what you need to buy", welcome)

        reply = self.service.get_response(
            "We need 12 lightweight laptops for software developers under 6500 each "
            "with 16GB RAM and 512GB SSD with premium support and moderate growth",
            session_id,
        )

        prefs = self.service.session_answers[session_id]
        self.assertEqual(prefs["preferred_category"], "laptops")
        self.assertEqual(prefs["workload_types"], ["software_development"])
        self.assertEqual(prefs["budget"], 6500)
        self.assertEqual(prefs["team_size"], 12)
        self.assertEqual(prefs["quantity"], 12)
        self.assertEqual(prefs["requested_ram"], "16GB")
        self.assertEqual(prefs["requested_storage"], "512GB")
        self.assertEqual(prefs["portability_need"], "high")
        self.assertEqual(prefs["support_expectation"], "premium")
        self.assertEqual(prefs["growth_expectation"], "moderate_growth")
        self.assertIn("Developer Pro 15", reply)
        self.assertIn("SKU-LAP-002-P1", reply)
        self.assertIn("Detailed explanation being prepared", reply)
        self.assertNotIn("If you move lower:", reply)
        self.assertIn("Overall rationale:", reply)
        self.assertIn("12 seats", reply)

    def test_sales_service_returns_recommendation_and_refinement_prompt_when_only_non_blocking_signals_are_missing(self):
        session_id = "session-followup"

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "We need laptops for 15 software developers under 6500 each",
            session_id,
        )

        self.assertEqual(payload["response_type"], "recommendation")
        self.assertIn("Which apps or tools matter most", payload["response"])
        self.assertEqual(payload["recommendations"][0]["name"], "Developer Pro 15")

    def test_sales_service_payload_includes_extraction_llm_usage_telemetry(self):
        session_id = "session-llm-telemetry"

        class TelemetryLLM:
            def __init__(self):
                self.provider = "groq"
                self.model_name = "openai/gpt-oss-20b"
                self.stats = {
                    "provider": "groq",
                    "text_calls": 0,
                    "successes": 0,
                    "failures": 0,
                    "last_error": "",
                    "last_prompt_name": "",
                    "last_request": {},
                    "last_usage": {},
                    "last_finish_reason": "",
                    "last_response_model": "",
                }

            def is_available(self):
                return True

            def invoke_json(self, prompt_name, variables, request_options=None):
                self.stats["text_calls"] += 1
                self.stats["successes"] += 1
                self.stats["last_prompt_name"] = prompt_name
                self.stats["last_request"] = dict(request_options or {})
                self.stats["last_usage"] = {
                    "input_tokens": 120,
                    "output_tokens": 40,
                    "total_tokens": 160,
                }
                self.stats["last_finish_reason"] = "stop"
                self.stats["last_response_model"] = self.model_name
                return {
                    "preferred_category": "laptops",
                    "workload_types": ["software_development"],
                    "budget": 6500,
                }

            def invoke_text(self, prompt_name, variables, request_options=None):
                return None

        fake_llm = TelemetryLLM()
        self.service.recommendation_service.extraction_service = RequirementExtractionService(llm_client=fake_llm)
        self.service.extraction_service = self.service.recommendation_service.extraction_service

        payload = self.service.get_response_payload(
            "Need laptops for 12 software developers under 6500 each",
            session_id,
        )

        self.assertEqual(payload["llm_stats"]["extraction"]["last_usage"]["total_tokens"], 160)
        self.assertEqual(payload["llm_stats"]["extraction"]["last_request"]["reasoning_effort"], "low")
        self.assertEqual(payload["llm_stats"]["extraction"]["last_request"]["max_tokens"], 512)
        self.assertIn("application_profile", payload["readiness"]["missing_signals"])

    def test_sales_service_recommendation_payload_exposes_current_procurement_metadata(self):
        session_id = "session-current-metadata"

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "We need laptops for 15 software developers under 6500 each",
            session_id,
        )

        self.assertEqual(payload["response_type"], "recommendation")
        self.assertEqual(payload["recommendation_mode"], "provisional_recommendation")
        self.assertEqual(payload["requirements"]["channel"], "websocket")
        self.assertEqual(payload["meta"]["selected_template"]["template_id"], "developer-team-starter-v1")
        self.assertEqual(payload["meta"]["selected_template"]["template_match_quality"], "exact")
        self.assertTrue(payload["meta"]["selected_template"]["template_selection_debug"])
        self.assertTrue(payload["template_candidates"])
        self.assertTrue(payload["recommendations"])

    def test_sales_service_payload_includes_streamlit_style_llm_stats(self):
        session_id = "session-llm-stats"

        welcome_payload = self.service.get_response_payload("", session_id)
        self.assertIn("llm_stats", welcome_payload)
        self.assertEqual(
            set(welcome_payload["llm_stats"].keys()),
            {"provider", "model", "available", "extraction", "followup", "explanation"},
        )

        payload = self.service.get_response_payload(
            "We need laptops for 15 software developers under 6500 each",
            session_id,
        )

        self.assertIn("llm_stats", payload)
        self.assertEqual(payload["llm_stats"]["provider"], "groq")
        self.assertFalse(payload["llm_stats"]["available"])
        self.assertIsInstance(payload["llm_stats"]["extraction"], dict)
        self.assertIsInstance(payload["llm_stats"]["followup"], dict)
        self.assertIsInstance(payload["llm_stats"]["explanation"], dict)
        self.assertIn("text_calls", payload["llm_stats"]["extraction"])
        self.assertIn("text_calls", payload["llm_stats"]["followup"])
        self.assertIn("text_calls", payload["llm_stats"]["explanation"])

    def test_sales_service_llm_stats_are_scoped_to_the_current_turn(self):
        session_id = "session-llm-turn-scope"

        class CountingLLM:
            def __init__(self):
                self.provider = "groq"
                self.model_name = "openai/gpt-oss-20b"
                self.stats = {
                    "provider": "groq",
                    "text_calls": 0,
                    "successes": 0,
                    "failures": 0,
                    "last_error": "",
                    "last_prompt_name": "",
                    "last_request": {},
                    "last_usage": {},
                    "last_finish_reason": "",
                    "last_response_model": "",
                }

            def is_available(self):
                return True

            def invoke_json(self, prompt_name, variables, request_options=None):
                self.stats["text_calls"] += 1
                self.stats["successes"] += 1
                self.stats["last_prompt_name"] = prompt_name
                self.stats["last_request"] = dict(request_options or {})
                self.stats["last_usage"] = {"total_tokens": 42}
                self.stats["last_finish_reason"] = "stop"
                self.stats["last_response_model"] = self.model_name
                return {
                    "preferred_category": "laptops",
                    "workload_types": ["software_development"],
                    "budget": 6500,
                }

            def invoke_text(self, prompt_name, variables, request_options=None):
                return None

        fake_llm = CountingLLM()
        self.service.recommendation_service.extraction_service = RequirementExtractionService(llm_client=fake_llm)
        self.service.extraction_service = self.service.recommendation_service.extraction_service

        first_payload = self.service.get_response_payload(
            "Need laptops for 12 software developers under 6500 each",
            session_id,
        )

        self.assertTrue(first_payload["llm_stats"]["extraction"]["called"])
        self.assertEqual(first_payload["llm_stats"]["extraction"]["text_calls"], 1)
        self.assertEqual(first_payload["llm_stats"]["extraction"]["last_usage"]["total_tokens"], 42)

        self.service.reset_session(session_id)
        welcome_payload = self.service.get_response_payload("", session_id)

        self.assertFalse(welcome_payload["llm_stats"]["extraction"]["called"])
        self.assertEqual(welcome_payload["llm_stats"]["extraction"]["text_calls"], 0)
        self.assertEqual(welcome_payload["llm_stats"]["followup"]["text_calls"], 0)
        self.assertEqual(welcome_payload["llm_stats"]["explanation"]["text_calls"], 0)

    def test_sales_service_skips_llm_extraction_for_generic_hospital_opener(self):
        session_id = "session-hospital-opener"

        class CountingLLM:
            def __init__(self):
                self.provider = "groq"
                self.model_name = "openai/gpt-oss-20b"
                self.stats = {
                    "provider": "groq",
                    "text_calls": 0,
                    "successes": 0,
                    "failures": 0,
                    "last_error": "",
                    "last_prompt_name": "",
                    "last_request": {},
                    "last_usage": {},
                    "last_finish_reason": "",
                    "last_response_model": "",
                }

            def is_available(self):
                return True

            def invoke_json(self, prompt_name, variables, request_options=None):
                self.stats["text_calls"] += 1
                self.stats["successes"] += 1
                self.stats["last_prompt_name"] = prompt_name
                self.stats["last_request"] = dict(request_options or {})
                self.stats["last_response_model"] = self.model_name
                return {"industry": "healthcare"}

            def invoke_text(self, prompt_name, variables, request_options=None):
                return None

        fake_llm = CountingLLM()
        self.service.recommendation_service.extraction_service = RequirementExtractionService(llm_client=fake_llm)
        self.service.extraction_service = self.service.recommendation_service.extraction_service

        payload = self.service.get_response_payload(
            "I am opening a hospital, what exactly do I need",
            session_id,
        )

        self.assertEqual(payload["response_type"], "question")
        self.assertEqual(
            payload["response"],
            "Should I help with IT equipment, medical equipment, admin setup, or the full opening checklist?",
        )
        self.assertFalse(payload["llm_stats"]["extraction"]["called"])
        self.assertEqual(payload["llm_stats"]["extraction"]["text_calls"], 0)
        self.assertEqual(self.service.extraction_service.last_timing["llm_prompt_mode"], "skipped")

    def test_sales_service_clarification_turn_ignores_stale_background_explanations(self):
        session_id = "session-stale-background"
        self.service.session_background_explanations[session_id] = {
            "result_key": "trace-old",
            "status": "completed",
            "delivered": False,
            "recommendation_count": 1,
            "recommendations": [
                {
                    "product_id": "old-laptop",
                    "candidate_id": "old-laptop",
                    "name": "Developer Pro 15",
                    "explanation": "Old explanation that should not leak.",
                }
            ],
        }
        self.service.session_last_payloads[session_id] = {
            "decision_trace_id": "trace-old",
            "response_type": "recommendation",
            "recommendations": [{"name": "Developer Pro 15"}],
        }

        payload = self.service.get_response_payload(
            "I am opening a hospital, what exactly do I need",
            session_id,
        )

        self.assertEqual(payload["response_type"], "question")
        self.assertNotIn("recommendations", payload)
        self.assertNotIn("recommendation_context", payload)
        self.assertNotIn("background_explanations", payload.get("meta", {}))
        self.assertIsNone(self.service.consume_background_explanation_payload(session_id))

    def test_question_payload_omits_recommendation_only_fields(self):
        session_id = "session-question-payload-shape"

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "Need laptops for 20 people under 4500 each",
            session_id,
        )

        self.assertEqual(payload["response_type"], "question")
        self.assertIn("decision_trace_id", payload)
        self.assertIn("response", payload)
        self.assertIn("next_question", payload)
        self.assertIn("readiness", payload)
        self.assertIn("ui_guidance", payload)
        for forbidden_key in (
            "recommendations",
            "target_profile",
            "compatibility_report",
            "check_requirement_summary",
            "editable_inferred_values",
            "template_candidates",
            "recommendation_context",
        ):
            self.assertNotIn(forbidden_key, payload)

    def test_question_payload_does_not_reuse_prior_recommendation_context(self):
        session_id = "session-question-no-recommendation-context"

        self.service.get_response("", session_id)
        recommendation_payload = self.service.get_response_payload(
            "We need laptops for 15 software developers under 6500 each",
            session_id,
        )
        self.assertEqual(recommendation_payload["response_type"], "recommendation")
        self.assertIn("recommendation_context", recommendation_payload)
        self.service.session_answers[session_id] = {}

        question_payload = self.service.get_response_payload(
            "I am opening a hospital, what exactly do I need",
            session_id,
        )

        self.assertEqual(question_payload["response_type"], "question")
        self.assertNotIn("recommendation_context", question_payload)

    def test_recommendation_payload_preserves_current_procurement_contract(self):
        session_id = "session-recommendation-payload-contract"

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "We need laptops for 15 software developers under 6500 each",
            session_id,
        )

        self.assertEqual(payload["response_type"], "recommendation")
        for required_key in (
            "response",
            "response_type",
            "decision_trace_id",
            "recommendations",
            "requirements",
            "target_profile",
            "summary",
            "assumptions",
            "compatibility_report",
            "check_requirement_summary",
            "editable_inferred_values",
            "template_candidates",
            "readiness",
            "recommendation_context",
            "meta",
            "ui_guidance",
            "extracted_schema",
        ):
            self.assertIn(required_key, payload)

    def test_sales_service_persists_last_asked_field_after_clarification_turn(self):
        session_id = "session-last-asked-field"

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "Need laptops for 20 people under 4500 each",
            session_id,
        )

        self.assertEqual(payload["response_type"], "question")
        self.assertEqual(
            self.service.session_answers[session_id]["_last_asked_field"],
            payload["readiness"]["highest_priority_missing_field"],
        )

    def test_sales_service_exposes_followup_timeout_metric_when_llm_polish_times_out(self):
        session_id = "session-followup-timeout-metric"

        class SlowFollowupLLM:
            def __init__(self):
                self.stats = {}

            def is_available(self):
                return True

            def invoke_text(self, prompt_name, variables, request_options=None):
                import time
                time.sleep(5)
                return "Too late"

        self.service.followup_service.llm_client = SlowFollowupLLM()
        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "Need laptops for 20 people under 4500 each",
            session_id,
        )

        self.assertEqual(payload["response_type"], "question")
        self.assertIn("followup_llm", payload["meta"])
        self.assertTrue(payload["meta"]["followup_llm"]["attempted"])
        self.assertTrue(payload["meta"]["followup_llm"]["timed_out"])
        self.assertTrue(payload["meta"]["followup_llm"]["used_fallback"])

    def test_sales_service_writes_one_runtime_jsonl_record_per_request(self):
        session_id = "session-runtime-jsonl"
        runtime_log_path = Path("logs/websocket_runtime.jsonl")
        if runtime_log_path.exists():
            runtime_log_path.unlink()

        self.service.get_response_payload(
            "Need laptops for 20 people under 4500 each",
            session_id,
        )

        self.assertTrue(runtime_log_path.exists())
        lines = runtime_log_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual(record["session_key"], session_id)
        self.assertEqual(record["response_type"], "question")

    def test_sales_service_initial_recommendation_mentions_pending_explanation(self):
        session_id = "session-pending-explanation-note"

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "We need laptops for 15 software developers under 6500 each",
            session_id,
        )

        self.assertEqual(payload["response_type"], "recommendation")
        self.assertIn("Detailed explanation being prepared", payload["response"])

    def test_sales_service_recommendation_response_includes_score_signals_for_strong_match(self):
        session_id = "session-score-signals"

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "We need laptops for 15 software developers under 6500 each",
            session_id,
        )

        self.assertEqual(payload["response_type"], "recommendation")
        self.assertIn("Score signals:", payload["response"])

    def test_sales_service_deduplicates_repeated_raw_chat_and_notes(self):
        session_id = "session-deduped-history"
        prompt = "Need 12 laptops for software developers under 6500 each"

        self.service.get_response_payload(prompt, session_id)
        second_payload = self.service.get_response_payload(prompt, session_id)

        prefs = self.service.session_answers[session_id]
        self.assertEqual(prefs["raw_chat"], prompt)
        self.assertEqual(prefs["notes"], prompt)
        self.assertEqual(second_payload["requirements"]["raw_chat"], prompt)
        self.assertEqual(second_payload["requirements"]["notes"], prompt)

    def test_sales_service_cleans_up_inactive_sessions_after_timeout(self):
        session_id = "session-stale-cleanup"
        session_key = self.service._session_key(session_id)

        self.service.session_histories[session_key] = [{"role": "user", "content": "old"}]
        self.service.session_answers[session_key] = {"preferred_category": "laptops"}
        self.service.session_store_ids[session_key] = "store-1"
        self.service.session_recommendation_context[session_key] = {"summary": "old"}
        self.service.session_timing_breakdowns[session_key] = {"extract_ms": 12}
        self.service.session_background_explanations[session_key] = {"status": "pending"}
        self.service.session_last_payloads[session_key] = {"response_type": "question"}
        self.service._session_last_active[session_key] = time.time() - (
            self.service.SESSION_INACTIVITY_TIMEOUT_SEC + 60
        )

        self.service._cleanup_inactive_sessions(now=time.time())

        self.assertNotIn(session_key, self.service.session_histories)
        self.assertNotIn(session_key, self.service.session_answers)
        self.assertNotIn(session_key, self.service.session_store_ids)
        self.assertNotIn(session_key, self.service.session_recommendation_context)
        self.assertNotIn(session_key, self.service.session_timing_breakdowns)
        self.assertNotIn(session_key, self.service.session_background_explanations)
        self.assertNotIn(session_key, self.service.session_last_payloads)
        self.assertNotIn(session_key, self.service._session_last_active)

    def test_sales_service_asks_for_app_tool_mix_as_refinement_for_broad_developer_brief(self):
        session_id = "session-app-profile"

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "Need laptops for 8 software developers under 7000 each",
            session_id,
        )

        self.assertEqual(payload["response_type"], "recommendation")
        self.assertTrue(payload["readiness"]["is_ready"])
        self.assertIn("application_profile", payload["readiness"]["missing_signals"])
        self.assertEqual(payload["readiness"]["routing_recommendation"], "recommend_with_one_refinement")
        self.assertIn("Which apps or tools matter most", payload["response"])
        self.assertEqual(payload["recommendations"][0]["name"], "Developer Pro 15")

    def test_sales_service_recommends_when_category_budget_and_team_size_are_present(self):
        session_id = f"session-use-case-{time.time_ns()}"
        disable_runtime_llms(self.service)

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "Need laptops for 20 people under 4500 each",
            session_id,
        )

        self.assertEqual(payload["response_type"], "recommendation")
        self.assertTrue(payload["readiness"]["is_ready"])
        self.assertFalse(payload["readiness"]["missing_signals"])
        self.assertEqual(payload["requirements"]["preferred_category"], "laptops")
        self.assertEqual(payload["requirements"]["budget"], 4500)
        self.assertEqual(payload["requirements"]["team_size"], 20)
        self.assertEqual(payload["requirements"]["quantity"], 20)
        self.assertTrue(payload["recommendations"])

    def test_sales_service_budget_reply_still_absorbs_extra_explicit_fields(self):
        session_id = f"session-budget-extra-fields-{time.time_ns()}"
        disable_runtime_llms(self.service)

        self.service.get_response("", session_id)
        first = self.service.get_response_payload("Need laptops", session_id)
        final = self.service.get_response_payload(
            "Budget is 6500 each and prefer Dell for 10 laptops",
            session_id,
        )

        self.assertEqual(first["response_type"], "question")
        self.assertEqual(final["response_type"], "recommendation")
        self.assertEqual(final["requirements"]["budget"], 6500)
        self.assertEqual(final["requirements"]["budget_scope"], "per_unit")
        self.assertEqual(final["requirements"]["preferred_category"], "laptops")
        self.assertEqual(final["requirements"]["preferred_manufacturers"], ["Dell"])
        self.assertEqual(final["requirements"]["quantity"], 10)
        self.assertEqual(final["requirements"]["team_size"], 10)

    def test_sales_service_preserves_team_size_when_budget_reply_contains_lakhs(self):
        session_id = f"session-lakhs-{time.time_ns()}"
        disable_runtime_llms(self.service)

        self.service.get_response("", session_id)
        first = self.service.get_response_payload("i need to buy laptops for my team", session_id)
        second = self.service.get_response_payload("i am basically a startup for software development", session_id)
        third = self.service.get_response_payload("there will be almost 20 people in my company", session_id)
        final = self.service.get_response_payload("i have a overall budget of 2 lakhs", session_id)

        self.assertEqual(first["response_type"], "question")
        self.assertEqual(second["response_type"], "question")
        self.assertEqual(third["response_type"], "question")
        self.assertEqual(third["requirements"]["team_size"], 20)
        self.assertEqual(third["requirements"]["quantity"], 20)
        self.assertIsNone(third["requirements"]["budget"])
        self.assertEqual(final["response_type"], "recommendation")
        self.assertEqual(final["requirements"]["team_size"], 20)
        self.assertEqual(final["requirements"]["quantity"], 20)
        self.assertEqual(final["requirements"]["budget"], 200000)
        self.assertIsNone(final["requirements"]["growth_expectation"])
        self.assertIn("20 seats", final["summary"])
        self.assertNotIn("2 seats", final["summary"])
        self.assertTrue(final["recommendations"])
        self.assertEqual(final["recommendations"][0]["name"], "Developer Pro 15")

    def test_sales_service_remembers_recommendation_for_recap_and_budget_refinement_turns(self):
        session_id = f"session-recommendation-memory-{time.time_ns()}"
        disable_runtime_llms(self.service)

        session_service = self.service.chat_orchestrator.chat_session_service
        session = session_service.get_or_create_session(session_id, channel="websocket")
        session_service.save_state(
            session.conversation_id,
            {
                "requirements": {
                    "preferred_category": "laptops",
                    "preferred_categories": ["laptops"],
                    "workloads": ["software_development"],
                    "team_size": 15,
                    "quantity": 15,
                    "budget": 6500,
                    "budget_scope": "per_unit",
                },
                "recommendation_memory": {
                    "decision_trace_id": "trace-memory-1",
                    "summary": (
                        "Ranked laptops options for 15 seats in software, optimized for software_development "
                        "within a per-unit budget of 6500 INR."
                    ),
                    "response": (
                        "Ranked laptops options for 15 seats in software, optimized for software_development "
                        "within a per-unit budget of 6500 INR."
                    ),
                    "refinement_prompt": "",
                    "recommendation_mode": "provisional_recommendation",
                    "recommendations": [
                        {"name": "Developer Pro 15"},
                        {"name": "OfficeBook 14"},
                        {"name": "BudgetMate 15"},
                    ],
                },
                "recommendations": [
                    {"name": "Developer Pro 15"},
                    {"name": "OfficeBook 14"},
                    {"name": "BudgetMate 15"},
                ],
                "recommendation_context": {},
                "refinement_prompt": "",
                "conversation_meta": {
                    "last_asked_field": "",
                    "last_assistant_action": "recommend",
                    "last_assistant_message": (
                        "Ranked laptops options for 15 seats in software, optimized for software_development "
                        "within a per-unit budget of 6500 INR."
                    ),
                    "recommended_question_id": "application_profile",
                    "conversation_brief": "laptops; software development; for 15 users; budget 6500 per unit",
                },
            },
        )
        refine = self.service.get_response_payload("can you make it cheaper?", session_id)
        recap = self.service.get_response_payload("what did you recommend again?", session_id)

        self.assertEqual(refine["response_type"], "question")
        self.assertIn("budget", refine["response"].lower())
        self.assertNotIn("applications or tools", refine["response"].lower())
        self.assertEqual(recap["response_type"], "question")
        self.assertIn("Developer Pro 15", recap["response"])
        self.assertFalse(recap.get("recommendations"))

    def test_sales_service_preserves_thousand_budget_reply_in_streamlit_style_desktop_flow(self):
        session_id = "session-thousand-budget-desktops"

        self.service.get_response("", session_id)
        first = self.service.get_response_payload("We need desktops.", session_id)
        second = self.service.get_response_payload(
            (
                "The main apps and tools are Excel, spreadsheets, browser-based business apps, "
                "browser tools, web apps, and lots of tabs."
            ),
            session_id,
        )
        third = self.service.get_response_payload("We need this for about 30 users.", session_id)
        final = self.service.get_response_payload("My overall budget is 140 thousand.", session_id)

        self.assertEqual(first["response_type"], "question")
        self.assertEqual(second["response_type"], "question")
        self.assertEqual(third["response_type"], "question")
        self.assertEqual(final["requirements"]["preferred_category"], "desktops")
        self.assertEqual(final["requirements"]["workloads"], ["office_productivity"])
        self.assertEqual(final["requirements"]["team_size"], 30)
        self.assertEqual(final["requirements"]["quantity"], 30)
        self.assertEqual(final["requirements"]["budget"], 140000)
        self.assertEqual(final["requirements"]["budget_scope"], "project_total")
        self.assertNotEqual(final["requirements"]["budget"], 140)

    def test_sales_service_accepts_terse_lakh_budget_reply_for_total_budget_question(self):
        session_id = "session-terse-total-budget"

        self.service.get_response("", session_id)
        first = self.service.get_response_payload(
            "Need laptops for 40 office users",
            session_id,
        )

        self.assertEqual(first["response_type"], "question")
        self.assertIn("budget", first["response"].lower())

        self.service.followup_service.next_question = lambda prefs, readiness: (
            "What is your total budget for purchasing the 40 laptops?"
        )
        final = self.service.get_response_payload("2 lakh", session_id)

        self.assertEqual(final["response_type"], "recommendation")
        self.assertEqual(final["requirements"]["budget"], 200000)
        self.assertEqual(final["requirements"]["budget_scope"], "project_total")
        self.assertEqual(final["requirements"]["team_size"], 40)
        self.assertEqual(final["requirements"]["quantity"], 40)
        self.assertIn("40 seats", final["summary"])
        self.assertTrue(final["recommendations"])

    def test_sales_service_accepts_yes_for_budget_confirmation_question(self):
        session_id = "session-budget-confirmation"

        self.service.get_response("", session_id)
        first = self.service.get_response_payload(
            "Need 20 laptops for office users",
            session_id,
        )

        self.assertEqual(first["response_type"], "question")

        self.service.followup_service.next_question = lambda prefs, readiness: (
            "Can you confirm the total budget for the 20 laptops is 3 lakh INR?"
        )
        final = self.service.get_response_payload("yes", session_id)

        self.assertEqual(final["response_type"], "recommendation")
        self.assertEqual(final["requirements"]["budget"], 300000)
        self.assertEqual(final["requirements"]["budget_scope"], "project_total")
        self.assertEqual(final["requirements"]["team_size"], 20)
        self.assertEqual(final["requirements"]["quantity"], 20)
        self.assertIn("20 seats", final["summary"])
        self.assertTrue(final["recommendations"])

    def test_sales_service_can_use_safe_llm_fallback_for_ambiguous_budget_confirmation_reply(self):
        session_id = "session-llm-budget-confirmation"

        class FakeReplyLlm:
            def __init__(self):
                self.calls = []
                self.FAST_PATH_TIMEOUT_SEC = 3

            def is_available(self):
                return True

            def invoke_text(self, prompt_name, variables, request_options=None):
                return None

            def invoke_json(self, prompt_name, variables, request_options=None):
                self.calls.append((prompt_name, dict(variables or {}), dict(request_options or {})))
                return {"rewrite": "My overall budget is 3 lakh INR."}

        fake_llm = FakeReplyLlm()
        self.service.followup_service.llm_client = fake_llm

        self.service.get_response("", session_id)
        first = self.service.get_response_payload(
            "Need 20 laptops for office users",
            session_id,
        )

        self.assertEqual(first["response_type"], "question")
        self.assertIn("budget", first["response"].lower())

        self.service.followup_service.next_question = lambda prefs, readiness: (
            "Can you confirm the total budget for the 20 laptops is 3 lakh INR?"
        )
        final = self.service.get_response_payload("works for us", session_id)

        self.assertEqual(final["response_type"], "recommendation")
        self.assertEqual(final["requirements"]["budget"], 300000)
        self.assertEqual(final["requirements"]["budget_scope"], "project_total")
        self.assertTrue(fake_llm.calls)
        self.assertEqual(
            fake_llm.calls[-1][2],
            {"timeout_sec": 3, "max_tokens": 160, "reasoning_effort": "low"},
        )
        self.assertTrue(final["recommendations"])

    def test_sales_service_preserves_growth_in_budget_followup_reply(self):
        session_id = "session-office-chatty"

        self.service.get_response("", session_id)
        first = self.service.get_response_payload(
            "hey, around 20 people, just normal office work, need affordable laptops",
            session_id,
        )

        self.assertEqual(first["response_type"], "question")

        final = self.service.get_response_payload(
            "budget is 4500 each and steady growth",
            session_id,
        )

        self.assertEqual(final["response_type"], "recommendation")
        self.assertEqual(final["requirements"]["budget_scope"], "per_unit")
        self.assertEqual(final["requirements"]["growth_expectation"], "steady")
        self.assertEqual(final["requirements"]["purchase_scope"], "team_rollout")
        self.assertEqual(final["recommendations"][0]["name"], "OfficeBook 14")

    def test_sales_service_replaces_ambiguous_scope_after_category_clarification(self):
        session_id = "session-ambiguous-office"

        self.service.get_response("", session_id)
        first = self.service.get_response_payload(
            "We've got about 20 new people joining soon. It's mostly email, docs, meetings, browser apps, "
            "the usual. I haven't decided between laptops and desktops yet, and I want to keep it sensible.",
            session_id,
        )
        second = self.service.get_response_payload("Let's go with laptops.", session_id)
        final = self.service.get_response_payload("Budget is around 4500 each and steady growth.", session_id)

        self.assertEqual(first["response_type"], "question")
        self.assertEqual(second["response_type"], "question")
        self.assertEqual(final["response_type"], "recommendation")
        self.assertEqual(final["requirements"]["preferred_categories"], ["laptops"])
        self.assertEqual(final["requirements"]["purchase_scope"], "team_rollout")
        self.assertEqual(final["requirements"]["budget_scope"], "per_unit")
        self.assertEqual(final["recommendations"][0]["name"], "OfficeBook 14")
        self.assertNotIn("Bundle candidate was rejected", final["summary"])

    def test_sales_service_keeps_limited_availability_option_for_urgent_rollout(self):
        session_id = "session-urgent-rollout"

        self.service.get_response("", session_id)
        first = self.service.get_response_payload(
            "Need laptops for 18 software developers under 7000 each and we need them available now.",
            session_id,
        )
        final = self.service.get_response_payload(
            "Moderate growth over the next year.",
            session_id,
        )

        self.assertEqual(first["response_type"], "recommendation")
        self.assertEqual(final["response_type"], "recommendation")
        self.assertEqual(final["recommendations"][0]["name"], "Developer Pro 15")
        self.assertEqual(final["recommendations"][0]["fit_status"], "limited_availability")

    def test_sales_service_returns_no_match_when_explicit_brand_cannot_be_met_before_recommendation(self):
        session_id = f"session-brand-no-match-before-{time.time_ns()}"
        disable_runtime_llms(self.service)

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "Need laptops for 10 office users under 5000 each and only Lenovo",
            session_id,
        )

        self.assertEqual(payload["response_type"], "question")
        self.assertFalse(payload.get("recommendations"))
        self.assertEqual(payload["requirements"]["preferred_manufacturers"], ["Lenovo"])
        self.assertEqual(payload["requirements"]["field_source"]["preferred_manufacturers"], "user_explicit")
        self.assertIn("no exact match", payload["response"].lower())

    def test_sales_service_returns_no_match_when_post_recommendation_brand_update_cannot_be_met(self):
        session_id = f"session-brand-no-match-after-{time.time_ns()}"
        disable_runtime_llms(self.service)

        self.service.get_response("", session_id)
        first = self.service.get_response_payload(
            "Need laptops for 10 office users under 5000 each",
            session_id,
        )
        final = self.service.get_response_payload("Only Lenovo", session_id)

        self.assertEqual(first["response_type"], "recommendation")
        self.assertTrue(first["recommendations"])
        self.assertEqual(final["response_type"], "question")
        self.assertFalse(final.get("recommendations"))
        self.assertEqual(final["requirements"]["preferred_manufacturers"], ["Lenovo"])
        self.assertEqual(final["requirements"]["field_source"]["preferred_manufacturers"], "user_explicit")
        self.assertIn("no exact match", final["response"].lower())

    def test_sales_service_post_recommendation_ram_update_reapplies_constraints(self):
        session_id = f"session-ram-followup-{time.time_ns()}"
        disable_runtime_llms(self.service)

        self.service.get_response("", session_id)
        first = self.service.get_response_payload(
            "Need laptops for 10 office users under 7000 each",
            session_id,
        )
        final = self.service.get_response_payload("make it 32 GB RAM", session_id)

        self.assertEqual(first["response_type"], "recommendation")
        self.assertEqual(final["requirements"]["budget"], 7000)
        self.assertEqual(final["requirements"]["requested_ram_gb"], 32)
        if final.get("recommendations"):
            self.assertEqual(final["response_type"], "recommendation")
            self.assertTrue(all(int(item.get("ram_gb") or 0) >= 32 for item in final["recommendations"]))
        else:
            self.assertEqual(final["response_type"], "question")
            self.assertIn("no exact match", final["response"].lower())

    def test_sales_service_post_recommendation_storage_update_reapplies_constraints(self):
        session_id = f"session-storage-followup-{time.time_ns()}"
        disable_runtime_llms(self.service)

        self.service.get_response("", session_id)
        first = self.service.get_response_payload(
            "Need laptops for 10 office users under 7000 each",
            session_id,
        )
        final = self.service.get_response_payload("need 1 TB SSD", session_id)

        self.assertEqual(first["response_type"], "recommendation")
        self.assertEqual(final["requirements"]["budget"], 7000)
        self.assertEqual(final["requirements"]["requested_storage_gb"], 1024)
        if final.get("recommendations"):
            self.assertEqual(final["response_type"], "recommendation")
            self.assertTrue(all(int(item.get("storage_gb") or 0) >= 1024 for item in final["recommendations"]))
        else:
            self.assertEqual(final["response_type"], "question")
            self.assertIn("no exact match", final["response"].lower())

    def test_sales_service_returns_expert_review_for_websocket_coverage_gap(self):
        session_id = "session-coverage-gap"

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "Need one server for virtualization in stock now under 20000",
            session_id,
        )

        self.assertEqual(payload["response_type"], "recommendation")
        self.assertEqual(payload["recommendation_mode"], "expert_review_recommended")
        self.assertTrue(payload["expert_review_eligible"])
        self.assertEqual(
            payload["meta"]["selected_template"]["template_id"],
            "server-virtualization-starter-v1",
        )
        self.assertEqual(payload["meta"]["selected_template"]["template_match_quality"], "coverage_gap")
        self.assertEqual(payload["meta"]["selected_template"]["gap_type"], "unsupported_urgency")
        self.assertTrue(payload["meta"]["selected_template"]["template_selection_debug"])

    def test_sales_service_returns_ui_guidance_with_recommendation_refinement(self):
        session_id = "session-guidance-refinement"

        self.service.get_response("", session_id)
        payload = self.service.get_response_payload(
            "We need laptops for 15 software developers under 6500 each",
            session_id,
        )

        self.assertEqual(payload["response_type"], "recommendation")
        self.assertTrue(payload["ui_guidance"])
        titles = [section["title"] for section in payload["ui_guidance"]]
        self.assertIn("Narrow Down The App Mix", titles)
        self.assertIn("Tune The Recommendation", titles)

    def test_sales_service_supports_printer_recommendations_on_corrected_json_catalog(self):
        session_id = "session-printer-corrected-json"
        service = build_sales_service(catalog_size="corrected_json")

        service.get_response("", session_id)
        payload = service.get_response_payload(
            "Need a shared office printer for 25 users under 30000",
            session_id,
        )

        self.assertEqual(payload["response_type"], "recommendation")
        self.assertEqual(payload["requirements"]["currency"], "INR")
        self.assertEqual(payload["recommendations"][0]["category"], "printers")
        self.assertIn("printer", payload["response"].lower())
        self.assertEqual(
            payload["meta"]["selected_template"]["template_id"],
            "office-printing-starter-v1",
        )

    def test_sales_service_supports_headsets_but_not_webcams_on_corrected_json_catalog(self):
        session_id = "session-accessories-corrected-json"
        service = build_sales_service(catalog_size="corrected_json")

        service.get_response("", session_id)
        headset_payload = service.get_response_payload(
            "Need 15 wireless headsets for a support team under 5000 each",
            session_id,
        )

        self.assertEqual(headset_payload["response_type"], "recommendation")
        self.assertEqual(headset_payload["recommendations"][0]["category"], "accessories")
        self.assertIn("headset", headset_payload["response"].lower())

        rejected_payload = service.get_response_payload(
            "Need 10 webcams for a support team under 5000 each",
            "session-webcam-rejection",
        )

        self.assertEqual(rejected_payload["response_type"], "recommendation")
        self.assertFalse(rejected_payload["recommendations"])
        self.assertIn("could not find a strong in-catalog match", rejected_payload["response"].lower())

    def test_sales_service_multi_intent_bundle_returns_grouped_marketplace_wide_result(self):
        session_id = "session-multi-intent-headset-bundle"
        service = build_sales_service(catalog_size="corrected_json")

        service.get_response("", session_id)
        payload = service.get_response_payload(
            (
                "Need 10 laptops for software developers using VS Code and Docker under 90000 each "
                "and 10 wireless headsets under 5000 each with moderate growth and balanced performance"
            ),
            session_id,
        )

        self.assertEqual(payload["response_type"], "recommendation")
        self.assertGreaterEqual(len(payload.get("recommendation_groups") or []), 2)
        self.assertTrue(payload.get("meta", {}).get("multi_intent", {}).get("bundle_validated"))
        self.assertFalse(payload.get("meta", {}).get("catalog_observability", {}).get("store_scope_applied"))
        group_labels = [group.get("label", "") for group in payload.get("recommendation_groups") or []]
        self.assertTrue(any("Laptop" in label or "Laptops" in label for label in group_labels))
        self.assertTrue(
            any(
                "Accessory" in label or "Accessories" in label or "Headset" in label
                for label in group_labels
            )
        )

    def test_streamlit_final_runtime_matches_websocket_service_procurement_contract(self):
        prompt = (
            "Branch opening next month: 8 laptops for developers using VS Code and Docker "
            "plus firewall and switching for 25 staff, total budget around 8 lakh"
        )
        websocket_service = build_sales_service(catalog_size="corrected_json")
        streamlit_service = build_procurement_chat_runtime(catalog_size="corrected_json")
        disable_runtime_llms(streamlit_service)

        websocket_payload = websocket_service.get_response_payload(prompt, "session-parity-websocket")
        streamlit_payload = streamlit_service.get_response_payload(prompt, "session-parity-streamlit")

        self.assertEqual(websocket_payload["response_type"], streamlit_payload["response_type"])
        self.assertEqual(websocket_payload["recommendation_mode"], streamlit_payload["recommendation_mode"])
        self.assertEqual(
            websocket_payload["requirements"]["preferred_category"],
            streamlit_payload["requirements"]["preferred_category"],
        )
        self.assertEqual(
            websocket_payload["requirements"]["budget"],
            streamlit_payload["requirements"]["budget"],
        )
        self.assertEqual(
            websocket_payload.get("meta", {}).get("multi_intent", {}).get("bundle_validated"),
            streamlit_payload.get("meta", {}).get("multi_intent", {}).get("bundle_validated"),
        )
        self.assertEqual(
            websocket_payload.get("meta", {}).get("multi_intent", {}).get("group_templates"),
            streamlit_payload.get("meta", {}).get("multi_intent", {}).get("group_templates"),
        )
        self.assertEqual(
            [group.get("category") for group in websocket_payload.get("recommendation_groups") or []],
            [group.get("category") for group in streamlit_payload.get("recommendation_groups") or []],
        )
        self.assertEqual(websocket_payload["requirements"]["channel"], "websocket")
        self.assertEqual(streamlit_payload["requirements"]["channel"], "streamlit_chat")


class SalesUiGuidanceTests(unittest.TestCase):
    def test_guidance_offers_work_profile_shortcuts_when_work_profile_is_missing(self):
        sections = build_narrowing_guidance(
            {"preferred_category": "laptops"},
            {"missing_signals": ["workload_or_application_profile"], "is_ready": False},
        )

        self.assertTrue(sections)
        self.assertEqual(sections[0]["title"], "Narrow Down The Work Profile")
        labels = [option["label"] for option in sections[0]["options"]]
        self.assertIn("Software development", labels)
        self.assertIn("Office apps", labels)

    def test_guidance_offers_application_profile_shortcuts_for_developer_workload(self):
        sections = build_narrowing_guidance(
            {"preferred_category": "laptops", "workload_types": ["software_development"]},
            {"missing_signals": ["application_profile"], "is_ready": True},
        )

        self.assertTrue(sections)
        self.assertEqual(sections[0]["title"], "Narrow Down The App Mix")
        labels = [option["label"] for option in sections[0]["options"]]
        self.assertIn("Backend dev", labels)
        self.assertIn("Full-stack web", labels)


class SalesBotConsumerAsgiTests(unittest.TestCase):
    def setUp(self):
        self.original_sales_service = websocket_consumer.sales_service
        websocket_consumer.sales_service = build_sales_service(catalog_size="small")

    def tearDown(self):
        websocket_consumer.sales_service = self.original_sales_service

    def test_receive_uses_asyncio_to_thread_and_skips_background_task_for_question_turns(self):
        async def scenario():
            scope = {
                "type": "websocket",
                "path": "/ws/sales-bot/",
                "query_string": b"",
                "headers": [],
                "subprotocols": [],
            }
            original_to_thread = websocket_consumer.asyncio.to_thread
            original_schedule_background_push = SalesBotConsumer._schedule_background_push
            calls = []
            background_scheduled = False

            async def fake_to_thread(func, *args, **kwargs):
                calls.append((func, args))
                return func(*args, **kwargs)

            def fake_schedule_background_push(instance):
                nonlocal background_scheduled
                background_scheduled = True

            websocket_consumer.asyncio.to_thread = fake_to_thread
            SalesBotConsumer._schedule_background_push = fake_schedule_background_push
            communicator = ApplicationCommunicator(SalesBotConsumer.as_asgi(), scope)
            try:
                await communicator.send_input({"type": "websocket.connect"})
                await communicator.receive_output(timeout=1)
                await communicator.receive_output(timeout=1)

                await communicator.send_input(
                    {
                        "type": "websocket.receive",
                        "text": json.dumps({"userSelection": "Need laptops for 20 people under 4500 each"}),
                    }
                )
                question_event = await communicator.receive_output(timeout=1)
                payload = json.loads(question_event["text"])

                self.assertEqual(payload["response_type"], "question")
                self.assertGreaterEqual(len(calls), 2)
                self.assertTrue(all(getattr(call[0], "__name__", "") == "get_response_payload" for call in calls))
                self.assertFalse(background_scheduled)
            finally:
                websocket_consumer.asyncio.to_thread = original_to_thread
                SalesBotConsumer._schedule_background_push = original_schedule_background_push
                await communicator.send_input({"type": "websocket.disconnect", "code": 1000})
                await communicator.wait(timeout=1)

        asyncio.run(scenario())


class SalesBotConsumerFocusedRefactorTests(unittest.TestCase):
    def test_consumer_reconnects_with_conversation_id_and_resumes_same_session(self):
        async def scenario():
            service = build_sales_service(catalog_size="small")
            disable_runtime_llms(service)
            original_registry_getter = websocket_consumer.get_service_registry
            websocket_consumer.get_service_registry = lambda: SimpleNamespace(
                sales_service=service,
                feature_flag_service=SimpleNamespace(is_enabled=lambda _flag_name: True),
                procurement_chat_rollout_router=SimpleNamespace(
                    resolve_websocket_runtime=lambda _scope: {
                        "requested_runtime": "active",
                        "resolved_runtime": "v2",
                        "active_runtime": "v2",
                        "available_runtimes": {"v2": True, "legacy": False},
                        "runtime_available": True,
                        "detail": "",
                    },
                    build_payload_meta=lambda resolution: {
                        "requested_runtime": resolution.get("requested_runtime"),
                        "resolved_runtime": resolution.get("resolved_runtime"),
                        "active_runtime": resolution.get("active_runtime"),
                        "available_runtimes": dict(resolution.get("available_runtimes") or {}),
                    },
                ),
            )
            try:
                initial = ApplicationCommunicator(
                    SalesBotConsumer.as_asgi(),
                    {
                        "type": "websocket",
                        "path": "/ws/sales-bot/",
                        "query_string": b"",
                        "headers": [],
                        "subprotocols": [],
                    },
                )
                await initial.send_input({"type": "websocket.connect"})
                await initial.receive_output(timeout=1)
                initial_payload = json.loads((await initial.receive_output(timeout=1))["text"])
                conversation_id = initial_payload["meta"]["conversation_id"]
                await initial.send_input({"type": "websocket.disconnect", "code": 1000})
                await initial.wait(timeout=1)

                resumed = ApplicationCommunicator(
                    SalesBotConsumer.as_asgi(),
                    {
                        "type": "websocket",
                        "path": "/ws/sales-bot/",
                        "query_string": f"conversation_id={conversation_id}".encode("utf-8"),
                        "headers": [],
                        "subprotocols": [],
                    },
                )
                await resumed.send_input({"type": "websocket.connect"})
                await resumed.receive_output(timeout=1)
                resumed_payload = json.loads((await resumed.receive_output(timeout=1))["text"])

                self.assertEqual(resumed_payload["meta"]["conversation_id"], conversation_id)
                self.assertEqual(
                    resumed_payload["meta"]["websocket_transport"]["transport_session_id"],
                    f"conversation:{conversation_id}",
                )
                self.assertTrue(resumed_payload["meta"]["websocket_transport"]["resumed_session"])

                await resumed.send_input({"type": "websocket.disconnect", "code": 1000})
                await resumed.wait(timeout=1)
            finally:
                websocket_consumer.get_service_registry = original_registry_getter

        asyncio.run(scenario())

    def test_consumer_connect_rejects_unavailable_legacy_runtime_override(self):
        class FakeRolloutRouter:
            def resolve_websocket_runtime(self, scope):
                return {
                    "requested_runtime": "legacy",
                    "resolved_runtime": "",
                    "active_runtime": "v2",
                    "available_runtimes": {"v2": True, "legacy": False},
                    "runtime_available": False,
                    "detail": "Legacy runtime is not available in this repository snapshot.",
                }

            def build_payload_meta(self, resolution):
                return {
                    "requested_runtime": resolution.get("requested_runtime"),
                    "resolved_runtime": resolution.get("resolved_runtime"),
                    "active_runtime": resolution.get("active_runtime"),
                    "available_runtimes": dict(resolution.get("available_runtimes") or {}),
                }

        original_registry_getter = websocket_consumer.get_service_registry
        websocket_consumer.get_service_registry = lambda: SimpleNamespace(
            procurement_chat_rollout_router=FakeRolloutRouter(),
            feature_flag_service=SimpleNamespace(is_enabled=lambda _flag_name: True),
        )

        async def scenario():
            consumer = SalesBotConsumer()
            consumer.scope = {"headers": [], "query_string": b"runtime=legacy"}
            sent = []
            close_codes = []

            async def fake_accept():
                sent.append({"type": "websocket.accept"})

            async def fake_send(*, text_data=None, bytes_data=None, close=False):
                sent.append(json.loads(text_data))

            async def fake_close(code=None):
                close_codes.append(code)

            consumer.accept = fake_accept
            consumer.send = fake_send
            consumer.close = fake_close

            await consumer.connect()

            self.assertEqual(sent[0]["type"], "websocket.accept")
            self.assertEqual(sent[1]["response_type"], "error")
            self.assertEqual(sent[1]["meta"]["rollout"]["requested_runtime"], "legacy")
            self.assertEqual(sent[1]["meta"]["rollout"]["active_runtime"], "v2")
            self.assertFalse(sent[1]["meta"]["rollout"]["available_runtimes"]["legacy"])
            self.assertEqual(close_codes, [4403])

        try:
            asyncio.run(scenario())
        finally:
            websocket_consumer.get_service_registry = original_registry_getter

    def test_consumer_connect_respects_procurement_chat_v2_feature_flag(self):
        class FakeFeatureFlagService:
            def is_enabled(self, flag_name):
                return False if flag_name == "procurement_chat_v2" else True

        original_registry_getter = websocket_consumer.get_service_registry
        websocket_consumer.get_service_registry = lambda: SimpleNamespace(
            feature_flag_service=FakeFeatureFlagService(),
            procurement_chat_rollout_router=SimpleNamespace(
                resolve_websocket_runtime=lambda _scope: {
                    "requested_runtime": "active",
                    "resolved_runtime": "v2",
                    "active_runtime": "v2",
                    "available_runtimes": {"v2": True, "legacy": False},
                    "runtime_available": True,
                    "detail": "",
                },
                build_payload_meta=lambda resolution: dict(resolution or {}),
            ),
        )

        async def scenario():
            consumer = SalesBotConsumer()
            sent = []
            close_codes = []

            async def fake_accept():
                sent.append({"type": "websocket.accept"})

            async def fake_send(*, text_data=None, bytes_data=None, close=False):
                sent.append(json.loads(text_data))

            async def fake_close(code=None):
                close_codes.append(code)

            consumer.accept = fake_accept
            consumer.send = fake_send
            consumer.close = fake_close

            await consumer.connect()

            self.assertEqual(sent[0]["type"], "websocket.accept")
            self.assertEqual(sent[1]["response_type"], "error")
            self.assertIn("disabled", sent[1]["error"].lower())
            self.assertFalse(sent[1]["meta"]["feature_flags"]["procurement_chat_v2"])
            self.assertEqual(close_codes, [4403])

        try:
            asyncio.run(scenario())
        finally:
            websocket_consumer.get_service_registry = original_registry_getter

    def test_consumer_connect_receive_restart_and_background_update(self):
        class FakeSalesService:
            def start_session(self, session_id, store_id=""):
                return {
                    "conversation_id": "conv-1",
                    "payload": {
                        "response": "Welcome question",
                        "response_type": "question",
                        "next_question": "Welcome question",
                        "meta": {"conversation_id": "conv-1"},
                    },
                }

            def process_turn(self, session_id, user_message):
                return {
                    "response": "Question after turn",
                    "response_type": "question",
                    "next_question": "Question after turn",
                    "meta": {"conversation_id": "conv-1"},
                }

            def reset_session(self, session_id):
                return {
                    "response": "Restarted",
                    "response_type": "question",
                    "next_question": "Restarted",
                    "meta": {"conversation_id": "conv-1"},
                }

            def clear_session(self, session_id):
                return None

        original_registry_getter = websocket_consumer.get_service_registry
        websocket_consumer.get_service_registry = lambda: SimpleNamespace(
            sales_service=FakeSalesService(),
            feature_flag_service=SimpleNamespace(is_enabled=lambda _flag_name: True),
            procurement_chat_rollout_router=SimpleNamespace(
                resolve_websocket_runtime=lambda _scope: {
                    "requested_runtime": "active",
                    "resolved_runtime": "v2",
                    "active_runtime": "v2",
                    "available_runtimes": {"v2": True, "legacy": False},
                    "runtime_available": True,
                    "detail": "",
                },
                build_payload_meta=lambda resolution: {
                    "requested_runtime": resolution.get("requested_runtime"),
                    "resolved_runtime": resolution.get("resolved_runtime"),
                    "active_runtime": resolution.get("active_runtime"),
                    "available_runtimes": dict(resolution.get("available_runtimes") or {}),
                },
            ),
        )

        async def scenario():
            consumer = SalesBotConsumer()
            consumer.channel_name = "chan-test"
            sent = []

            class FakeChannelLayer:
                async def group_add(self, group, channel):
                    return None

                async def group_discard(self, group, channel):
                    return None

            async def fake_accept():
                sent.append({"type": "websocket.accept"})

            async def fake_send(*, text_data=None, bytes_data=None, close=False):
                sent.append(json.loads(text_data))

            consumer.channel_layer = FakeChannelLayer()
            consumer.accept = fake_accept
            consumer.send = fake_send

            await consumer.connect()
            self.assertEqual(sent[0]["type"], "websocket.accept")
            self.assertEqual(sent[1]["response"], "Welcome question")
            self.assertEqual(sent[1]["meta"]["rollout"]["resolved_runtime"], "v2")

            await consumer.receive(json.dumps({"userSelection": "Need laptops"}))
            self.assertEqual(sent[2]["response"], "Question after turn")
            self.assertEqual(sent[2]["meta"]["rollout"]["resolved_runtime"], "v2")

            await consumer.background_recommendation_update(
                {
                    "payload": {
                        "event_type": "background_explanations_ready",
                        "response_type": "recommendation_update",
                        "decision_trace_id": "trace-1",
                        "recommendation_updates": [{"name": "Developer Pro 15"}],
                        "meta": {},
                        "llm_stats": {},
                    }
                }
            )
            self.assertEqual(sent[3]["response_type"], "recommendation_update")

            await consumer.receive(json.dumps({"userSelection": "restart"}))
            self.assertEqual(sent[4]["response"], "Restarted")

            await consumer.disconnect(1000)

        try:
            asyncio.run(scenario())
        finally:
            websocket_consumer.get_service_registry = original_registry_getter

    def test_background_recommendation_update_sends_payload(self):
        consumer = SalesBotConsumer()
        sent = []

        async def fake_send(*, text_data=None, bytes_data=None, close=False):
            sent.append(text_data)

        consumer.send = fake_send

        async def scenario():
            await consumer.background_recommendation_update(
                {
                    "payload": {
                        "event_type": "background_explanations_ready",
                        "response_type": "recommendation_update",
                        "decision_trace_id": "trace-1",
                        "recommendation_updates": [{"name": "Developer Pro 15"}],
                        "meta": {},
                        "llm_stats": {},
                    }
                }
            )

        asyncio.run(scenario())
        self.assertTrue(sent)
        payload = json.loads(sent[0])
        self.assertEqual(payload["response_type"], "recommendation_update")


class SalesBotConsumerRefactorTests(unittest.TestCase):
    def test_consumer_connect_receive_restart_and_background_update(self):
        class FakeSalesService:
            def __init__(self):
                self.started = 0
                self.processed = []
                self.reset_calls = 0
                self.cleared = 0

            def start_session(self, session_id, store_id=""):
                self.started += 1
                return {
                    "conversation_id": "conv-1",
                    "payload": {
                        "response": "Welcome question",
                        "response_type": "question",
                        "next_question": "Welcome question",
                        "meta": {"conversation_id": "conv-1"},
                    },
                }

            def process_turn(self, session_id, user_message):
                self.processed.append(user_message)
                return {
                    "response": "Question after turn",
                    "response_type": "question",
                    "next_question": "Question after turn",
                    "meta": {"conversation_id": "conv-1"},
                }

            def reset_session(self, session_id):
                self.reset_calls += 1
                return {
                    "response": "Restarted",
                    "response_type": "question",
                    "next_question": "Restarted",
                    "meta": {"conversation_id": "conv-1"},
                }

            def clear_session(self, session_id):
                self.cleared += 1

        fake_sales_service = FakeSalesService()
        original_registry_getter = websocket_consumer.get_service_registry
        websocket_consumer.get_service_registry = lambda: SimpleNamespace(sales_service=fake_sales_service)

        async def scenario():
            scope = {
                "type": "websocket",
                "path": "/ws/sales-bot/",
                "query_string": b"",
                "headers": [],
                "subprotocols": [],
            }
            communicator = ApplicationCommunicator(SalesBotConsumer.as_asgi(), scope)
            try:
                await communicator.send_input({"type": "websocket.connect"})
                accepted = await communicator.receive_output(timeout=1)
                welcome = await communicator.receive_output(timeout=1)
                welcome_payload = json.loads(welcome["text"])

                self.assertEqual(accepted["type"], "websocket.accept")
                self.assertEqual(welcome_payload["response_type"], "question")

                await communicator.send_input(
                    {
                        "type": "websocket.receive",
                        "text": json.dumps({"userSelection": "Need laptops"}),
                    }
                )
                question_event = await communicator.receive_output(timeout=1)
                question_payload = json.loads(question_event["text"])
                self.assertEqual(question_payload["response"], "Question after turn")

                consumer_instance = communicator.instance
                await consumer_instance.background_recommendation_update(
                    {
                        "payload": {
                            "event_type": "background_explanations_ready",
                            "response_type": "recommendation_update",
                            "decision_trace_id": "trace-1",
                            "recommendation_updates": [{"name": "Developer Pro 15"}],
                            "meta": {},
                            "llm_stats": {},
                        }
                    }
                )
                update_event = await communicator.receive_output(timeout=1)
                update_payload = json.loads(update_event["text"])
                self.assertEqual(update_payload["response_type"], "recommendation_update")

                await communicator.send_input(
                    {
                        "type": "websocket.receive",
                        "text": json.dumps({"userSelection": "restart"}),
                    }
                )
                restart_event = await communicator.receive_output(timeout=1)
                restart_payload = json.loads(restart_event["text"])
                self.assertEqual(restart_payload["response"], "Restarted")
            finally:
                await communicator.send_input({"type": "websocket.disconnect", "code": 1000})
                await communicator.wait(timeout=1)

        try:
            asyncio.run(scenario())
        finally:
            websocket_consumer.get_service_registry = original_registry_getter

    def test_websocket_flow_reaches_recommendation_and_structured_refinement_prompt(self):
        async def scenario():
            scope = {
                "type": "websocket",
                "path": "/ws/sales-bot/",
                "query_string": b"",
                "headers": [],
                "subprotocols": [],
            }
            communicator = ApplicationCommunicator(SalesBotConsumer.as_asgi(), scope)

            await communicator.send_input({"type": "websocket.connect"})
            accepted = await communicator.receive_output(timeout=1)
            self.assertEqual(accepted["type"], "websocket.accept")

            welcome_event = await communicator.receive_output(timeout=1)
            welcome_payload = json.loads(welcome_event["text"])
            self.assertIn("Tell me what you need to buy", welcome_payload["response"])
            self.assertEqual(welcome_payload["response_type"], "question")
            self.assertIn("llm_stats", welcome_payload)
            self.assertEqual(
                set(welcome_payload["llm_stats"].keys()),
                {"provider", "model", "available", "extraction", "followup", "explanation"},
            )

            await communicator.send_input(
                {
                    "type": "websocket.receive",
                    "text": json.dumps(
                        {
                            "userSelection": "We need laptops for 15 software developers under 6500 each"
                        }
                    ),
                }
            )
            recommendation_event = await communicator.receive_output(timeout=1)
            recommendation_payload = json.loads(recommendation_event["text"])
            self.assertEqual(recommendation_payload["response_type"], "recommendation")
            self.assertIn("Which apps or tools matter most", recommendation_payload["response"])
            self.assertEqual(recommendation_payload["recommendations"][0]["name"], "Developer Pro 15")
            self.assertNotIn("explanation", recommendation_payload["recommendations"][0])
            self.assertNotIn("downgrade_implications", recommendation_payload["recommendations"][0])
            self.assertIn("summary", recommendation_payload)
            self.assertIn("assumptions", recommendation_payload)
            self.assertIn("readiness", recommendation_payload)
            self.assertTrue(recommendation_payload["readiness"]["is_ready"])
            self.assertIn("growth_expectation", recommendation_payload["readiness"]["missing_signals"])
            self.assertIn("llm_stats", recommendation_payload)
            self.assertFalse(recommendation_payload["llm_stats"]["available"])
            self.assertIn("text_calls", recommendation_payload["llm_stats"]["extraction"])
            self.assertIn("text_calls", recommendation_payload["llm_stats"]["followup"])
            self.assertIn("text_calls", recommendation_payload["llm_stats"]["explanation"])
            self.assertIn("ui_guidance", recommendation_payload)
            guidance_titles = [section["title"] for section in recommendation_payload["ui_guidance"]]
            self.assertIn("Narrow Down The App Mix", guidance_titles)
            self.assertIn("Tune The Recommendation", guidance_titles)
            self.assertIn(
                recommendation_payload["meta"]["background_explanations"]["status"],
                {"pending", "completed"},
            )

            explanation_event = await communicator.receive_output(timeout=5)
            explanation_payload = json.loads(explanation_event["text"])
            self.assertEqual(explanation_payload["event_type"], "background_explanations_ready")
            self.assertEqual(explanation_payload["response_type"], "recommendation_update")
            self.assertTrue(explanation_payload["recommendation_updates"])
            self.assertIn("explanation", explanation_payload["recommendation_updates"][0])
            self.assertEqual(
                explanation_payload["meta"]["background_explanations"]["status"],
                "completed",
            )

            await communicator.send_input({"type": "websocket.disconnect", "code": 1000})
            await communicator.wait(timeout=1)

        asyncio.run(scenario())

    def test_websocket_payload_exposes_current_template_metadata(self):
        async def scenario():
            scope = {
                "type": "websocket",
                "path": "/ws/sales-bot/",
                "query_string": b"",
                "headers": [],
                "subprotocols": [],
            }
            communicator = ApplicationCommunicator(SalesBotConsumer.as_asgi(), scope)

            await communicator.send_input({"type": "websocket.connect"})
            await communicator.receive_output(timeout=1)
            await communicator.receive_output(timeout=1)

            await communicator.send_input(
                {
                    "type": "websocket.receive",
                    "text": json.dumps(
                        {"userSelection": "We need laptops for 15 software developers under 6500 each"}
                    ),
                }
            )
            recommendation_event = await communicator.receive_output(timeout=1)
            recommendation_payload = json.loads(recommendation_event["text"])

            self.assertEqual(recommendation_payload["recommendation_mode"], "provisional_recommendation")
            self.assertEqual(
                recommendation_payload["meta"]["selected_template"]["template_id"],
                "developer-team-starter-v1",
            )
            self.assertEqual(
                recommendation_payload["meta"]["selected_template"]["template_match_quality"],
                "exact",
            )
            self.assertTrue(
                recommendation_payload["meta"]["selected_template"]["template_selection_debug"]
            )
            self.assertEqual(recommendation_payload["requirements"]["channel"], "websocket")

            await communicator.send_input({"type": "websocket.disconnect", "code": 1000})
            await communicator.wait(timeout=1)

        asyncio.run(scenario())

    def test_websocket_flow_surfaces_expert_review_for_coverage_gap(self):
        async def scenario():
            scope = {
                "type": "websocket",
                "path": "/ws/sales-bot/",
                "query_string": b"",
                "headers": [],
                "subprotocols": [],
            }
            communicator = ApplicationCommunicator(SalesBotConsumer.as_asgi(), scope)

            await communicator.send_input({"type": "websocket.connect"})
            await communicator.receive_output(timeout=1)
            await communicator.receive_output(timeout=1)

            await communicator.send_input(
                {
                    "type": "websocket.receive",
                    "text": json.dumps(
                        {"userSelection": "Need one server for virtualization in stock now under 20000"}
                    ),
                }
            )
            recommendation_event = await communicator.receive_output(timeout=1)
            recommendation_payload = json.loads(recommendation_event["text"])

            self.assertEqual(recommendation_payload["response_type"], "recommendation")
            self.assertEqual(recommendation_payload["recommendation_mode"], "expert_review_recommended")
            self.assertTrue(recommendation_payload["expert_review_eligible"])
            self.assertEqual(
                recommendation_payload["meta"]["selected_template"]["template_id"],
                "server-virtualization-starter-v1",
            )
            self.assertEqual(
                recommendation_payload["meta"]["selected_template"]["template_match_quality"],
                "coverage_gap",
            )
            self.assertEqual(
                recommendation_payload["meta"]["selected_template"]["gap_type"],
                "unsupported_urgency",
            )

            await communicator.send_input({"type": "websocket.disconnect", "code": 1000})
            await communicator.wait(timeout=1)

        asyncio.run(scenario())

    def test_websocket_flow_supports_corrected_json_printer_recommendation(self):
        async def scenario():
            scope = {
                "type": "websocket",
                "path": "/ws/sales-bot/",
                "query_string": b"",
                "headers": [],
                "subprotocols": [],
            }
            websocket_consumer.sales_service = build_sales_service(catalog_size="corrected_json")
            communicator = ApplicationCommunicator(SalesBotConsumer.as_asgi(), scope)

            await communicator.send_input({"type": "websocket.connect"})
            await communicator.receive_output(timeout=1)
            await communicator.receive_output(timeout=1)

            await communicator.send_input(
                {
                    "type": "websocket.receive",
                    "text": json.dumps(
                        {"userSelection": "Need a shared office printer for 25 users under 30000"}
                    ),
                }
            )
            recommendation_event = await communicator.receive_output(timeout=1)
            recommendation_payload = json.loads(recommendation_event["text"])

            self.assertEqual(recommendation_payload["response_type"], "recommendation")
            self.assertEqual(recommendation_payload["requirements"]["channel"], "websocket")
            self.assertEqual(recommendation_payload["recommendations"][0]["category"], "printers")
            self.assertEqual(
                recommendation_payload["meta"]["selected_template"]["template_id"],
                "office-printing-starter-v1",
            )

            await communicator.send_input({"type": "websocket.disconnect", "code": 1000})
            await communicator.wait(timeout=1)

        asyncio.run(scenario())

    def test_websocket_flow_rejects_out_of_scope_webcam_request(self):
        async def scenario():
            scope = {
                "type": "websocket",
                "path": "/ws/sales-bot/",
                "query_string": b"",
                "headers": [],
                "subprotocols": [],
            }
            websocket_consumer.sales_service = build_sales_service(catalog_size="corrected_json")
            communicator = ApplicationCommunicator(SalesBotConsumer.as_asgi(), scope)

            await communicator.send_input({"type": "websocket.connect"})
            await communicator.receive_output(timeout=1)
            await communicator.receive_output(timeout=1)

            await communicator.send_input(
                {
                    "type": "websocket.receive",
                    "text": json.dumps(
                        {"userSelection": "Need 10 webcams for a support team under 5000 each"}
                    ),
                }
            )
            recommendation_event = await communicator.receive_output(timeout=1)
            recommendation_payload = json.loads(recommendation_event["text"])

            self.assertEqual(recommendation_payload["response_type"], "recommendation")
            self.assertFalse(recommendation_payload.get("recommendations"))
            self.assertIn(
                "could not find a strong in-catalog match",
                recommendation_payload["response"].lower(),
            )

            await communicator.send_input({"type": "websocket.disconnect", "code": 1000})
            await communicator.wait(timeout=1)

        asyncio.run(scenario())


class RefactorPayloadParityFocusedTests(unittest.TestCase):
    def test_websocket_and_streamlit_recommendation_payload_keys_stay_in_sync(self):
        prompt = "Need laptops for developers"
        websocket_service = build_sales_service(catalog_size="corrected_json")
        streamlit_service = build_procurement_chat_runtime(catalog_size="corrected_json")
        disable_runtime_llms(streamlit_service)
        disable_runtime_llms(websocket_service)

        planner_result = {
            "action": "recommend",
            "assistant_message": "Here are the closest matches.",
            "state_patch": {
                "preferred_category": "laptops",
                "workload_types": ["software_development"],
                "budget": 6500,
                "budget_scope": "per_unit",
                "team_size": 8,
                "quantity": 8,
            },
            "question_target_field": None,
            "corrections": [],
            "should_trigger_recommendation": True,
            "intent_groups": [],
            "confidence": 0.99,
        }
        websocket_service.chat_orchestrator.planner_service.plan_turn = lambda **kwargs: dict(planner_result)
        streamlit_service.chat_orchestrator.planner_service.plan_turn = lambda **kwargs: dict(planner_result)

        websocket_payload = websocket_service.get_response_payload(prompt, "session-focused-parity-websocket-rec")
        streamlit_payload = streamlit_service.get_response_payload(prompt, "session-focused-parity-streamlit-rec")

        expected_top_level_keys = {
            "response",
            "response_type",
            "requirements",
            "readiness",
            "recommendations",
            "decision_trace_id",
            "ui_guidance",
            "meta",
            "llm_stats",
            "recommendation_context",
            "refinement_prompt",
            "review_state",
            "check_requirement_summary",
            "editable_inferred_values",
            "template_candidates",
            "target_profile",
            "comparison",
            "assumptions",
        }

        self.assertEqual(set(websocket_payload.keys()), set(streamlit_payload.keys()))
        self.assertTrue(expected_top_level_keys.issubset(set(websocket_payload.keys())))
        self.assertEqual(websocket_payload["response_type"], streamlit_payload["response_type"])
        self.assertEqual(websocket_payload["requirements"]["preferred_category"], "laptops")
        self.assertEqual(streamlit_payload["requirements"]["preferred_category"], "laptops")
        self.assertTrue(websocket_payload["recommendations"])
        self.assertTrue(streamlit_payload["recommendations"])

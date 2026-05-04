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

import ai_configurator.sales_chat.websocket_consumer as websocket_consumer
from ai_configurator.procurement.models import (
    ProcurementConversationMessage,
    ProcurementConversationSession,
)
from ai_configurator.procurement.services.assistant_state_service import AssistantStateService
from ai_configurator.procurement.services.readiness_service import ProcurementReadinessService
from ai_configurator.procurement.services.recommendation_engine import ProcurementRecommendationEngine
from ai_configurator.procurement.services.recommendation_service import (
    ProcurementRecommendationRuntimeFacade,
    ProcurementRecommendationService,
)
from ai_configurator.procurement.services.response_writer_service import ResponseWriterService
from ai_configurator.procurement.services.semantic_turn_service import SemanticTurnService
from ai_configurator.procurement.services.state_manager import ProcurementStateManager
from ai_configurator.sales_chat.services.background_dispatcher import BackgroundDispatcher
from ai_configurator.sales_chat.services.chat_orchestrator import ChatOrchestrator
from ai_configurator.sales_chat.services.chat_session_service import ChatSessionService
from ai_configurator.sales_chat.services.payload_builder_service import PayloadBuilderService
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


def build_sales_service(catalog_size="small", channel="websocket", include_llm_stats=True):
    if str(catalog_size or "").strip().lower() == "small":
        repository = build_sample_catalog_repository()
    else:
        repository = build_catalog_repository(catalog_size)
    recommendation_core = ProcurementRecommendationService(catalog_repository=repository)
    recommendation_service = ProcurementRecommendationRuntimeFacade(recommendation_core)
    adapter = ResponseContractAdapter()
    state_manager = ProcurementStateManager()
    readiness_service = ProcurementReadinessService(state_manager=state_manager)
    orchestrator = ChatOrchestrator(
        chat_session_service=ChatSessionService(),
        recommendation_service=recommendation_service,
        response_contract_adapter=adapter,
        background_dispatcher=BackgroundDispatcher(
            response_contract_adapter=adapter,
            recommendation_service=recommendation_service,
        ),
        semantic_turn_service=SemanticTurnService(),
        state_manager=state_manager,
        readiness_service=readiness_service,
        recommendation_engine=ProcurementRecommendationEngine(
            recommendation_service=recommendation_service,
            state_manager=state_manager,
        ),
        response_writer_service=ResponseWriterService(),
        assistant_state_service=AssistantStateService(),
        payload_builder_service=PayloadBuilderService(response_contract_adapter=adapter),
        include_llm_stats=include_llm_stats,
    )
    return SalesService(
        chat_orchestrator=orchestrator,
        channel=channel,
        include_llm_stats=include_llm_stats,
    )



def disable_runtime_llms(service):
    orchestrator = getattr(service, "chat_orchestrator", None)
    semantic_service = getattr(orchestrator, "semantic_turn_service", None)
    writer_service = getattr(orchestrator, "response_writer_service", None)
    for candidate in (semantic_service, writer_service):
        llm_client = getattr(candidate, "llm_client", None)
        if llm_client is not None:
            llm_client.api_key = ""


class ChatOrchestratorRoutingBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.orchestrator = ChatOrchestrator(
            chat_session_service=object(),
            recommendation_service=object(),
            response_contract_adapter=object(),
            background_dispatcher=object(),
            recommendation_engine=object(),
        )

    def test_ready_global_modification_routes_to_recommendation(self):
        response_mode = self.orchestrator._select_response_mode(
            semantic_turn={
                "parse_status": "ok",
                "turn_kind": "modify_existing",
                "operations": [
                    {
                        "op": "set_global",
                        "field_path": "allowed_manufacturers",
                        "value": ["Dell"],
                    }
                ],
                "ambiguities": [],
            },
            readiness_result={"is_ready": True},
            state={
                "recommendation_memory": {
                    "decision_trace_id": "trace-1",
                    "recommendations": [{"name": "Prior Dell option"}],
                }
            },
        )

        self.assertEqual(response_mode, "recommendation")

    def test_ready_global_modification_without_memory_still_routes_to_general_reply(self):
        response_mode = self.orchestrator._select_response_mode(
            semantic_turn={
                "parse_status": "ok",
                "turn_kind": "modify_existing",
                "operations": [
                    {
                        "op": "set_global",
                        "field_path": "blocked_manufacturers",
                        "value": ["HP"],
                    }
                ],
                "ambiguities": [],
            },
            readiness_result={"is_ready": True},
            state={},
        )

        self.assertEqual(response_mode, "general_reply")


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

    def test_consumer_connect_ignores_deprecated_procurement_chat_v2_flag_after_cutover(self):
        class FakeFeatureFlagService:
            def is_enabled(self, flag_name):
                return False if flag_name == "procurement_chat_v2" else True

        class FakeSalesService:
            def start_session(self, session_id, store_id=""):
                return {
                    "conversation_id": "conv-cutover-1",
                    "payload": {
                        "response": "Welcome question",
                        "response_type": "question",
                        "next_question": "Welcome question",
                        "meta": {"conversation_id": "conv-cutover-1"},
                    },
                }

            def clear_session(self, session_id):
                return None

        original_registry_getter = websocket_consumer.get_service_registry
        websocket_consumer.get_service_registry = lambda: SimpleNamespace(
            sales_service=FakeSalesService(),
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
            consumer.channel_name = "chan-cutover-test"
            sent = []
            close_codes = []

            class FakeChannelLayer:
                async def group_add(self, group, channel):
                    return None

                async def group_discard(self, group, channel):
                    return None

            async def fake_accept():
                sent.append({"type": "websocket.accept"})

            async def fake_send(*, text_data=None, bytes_data=None, close=False):
                sent.append(json.loads(text_data))

            async def fake_close(code=None):
                close_codes.append(code)

            consumer.accept = fake_accept
            consumer.send = fake_send
            consumer.close = fake_close
            consumer.channel_layer = FakeChannelLayer()

            await consumer.connect()

            self.assertEqual(sent[0]["type"], "websocket.accept")
            self.assertEqual(sent[1]["response_type"], "question")
            self.assertEqual(sent[1]["meta"]["rollout"]["resolved_runtime"], "v2")
            self.assertEqual(close_codes, [])

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


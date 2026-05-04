from copy import deepcopy

from ...procurement.services.assistant_state_service import AssistantStateService
from ...procurement.services.readiness_service import ProcurementReadinessService
from ...procurement.services.recommendation_engine import ProcurementRecommendationEngine
from ...procurement.services.response_writer_service import ResponseWriterService
from ...procurement.services.semantic_turn_service import SemanticTurnService
from ...procurement.services.state_manager import ProcurementStateManager
from .payload_builder_service import PayloadBuilderService


class ChatOrchestrator:
    RUNTIME_FINGERPRINT = "semantic-writer-boundary-lock-20260417"

    def __init__(
        self,
        chat_session_service,
        recommendation_service,
        response_contract_adapter,
        background_dispatcher,
        include_llm_stats=True,
        signal_service=None,
        semantic_turn_service=None,
        state_manager=None,
        readiness_service=None,
        recommendation_engine=None,
        response_writer_service=None,
        assistant_state_service=None,
        payload_builder_service=None,
        planner_service=None,
        requirement_state_manager=None,
        requirement_guard_service=None,
    ):
        self.chat_session_service = chat_session_service
        self.recommendation_service = recommendation_service
        self.response_contract_adapter = response_contract_adapter
        self.background_dispatcher = background_dispatcher
        self.include_llm_stats = bool(include_llm_stats)
        self.signal_service = signal_service

        self.semantic_turn_service = semantic_turn_service or SemanticTurnService()
        self.state_manager = state_manager or ProcurementStateManager()
        self.readiness_service = readiness_service or ProcurementReadinessService(state_manager=self.state_manager)
        self.recommendation_engine = recommendation_engine or ProcurementRecommendationEngine(
            recommendation_service=self.recommendation_service,
            state_manager=self.state_manager,
        )
        self.response_writer_service = response_writer_service or ResponseWriterService()
        self.assistant_state_service = assistant_state_service or AssistantStateService()
        self.payload_builder_service = payload_builder_service or PayloadBuilderService(
            response_contract_adapter=self.response_contract_adapter,
        )

        # Compatibility aliases for older call sites and tests.
        self.planner_service = self.semantic_turn_service
        self.requirement_state_manager = self.state_manager
        self.requirement_guard_service = requirement_guard_service or self.readiness_service

    def start_session(self, transport_session_id, channel="websocket", store_id=""):
        session = self.chat_session_service.get_or_create_session(
            transport_session_id=transport_session_id,
            channel=channel,
            store_id=store_id,
            allow_transport_resume=True,
        )
        state = self.chat_session_service.load_state(session.conversation_id)
        requirements = dict((state or {}).get("requirements") or {})
        return session, {
            "response": None,
            "response_type": "question",
            "next_question": None,
            "requirements": {
                "preferred_categories": requirements.get("preferred_categories"),
                "preferred_category": requirements.get("preferred_category"),
                "budget": requirements.get("budget"),
                "budget_scope": requirements.get("budget_scope"),
                "quantity": requirements.get("quantity"),
            },
            "readiness": {},
            "meta": {
                "conversation_id": session.conversation_id,
                "response_mode": "respond",
                "runtime_fingerprint": self.RUNTIME_FINGERPRINT,
            },
            "llm_stats": self._build_llm_stats(),
        }

    def handle_turn(self, transport_session_id, user_message):
        session = self.chat_session_service.get_or_create_session(transport_session_id=transport_session_id)
        state = self.chat_session_service.load_state(session.conversation_id)
        recent_messages = self.chat_session_service.planner_recent_messages(session.conversation_id)

        self.chat_session_service.append_message(
            session.conversation_id,
            role="user",
            content=user_message,
            message_type="info",
        )

        semantic_turn = self.semantic_turn_service.parse_turn(
            user_message=user_message,
            state=deepcopy(state),
            recent_messages=recent_messages,
            assistant_question_context=dict((state or {}).get("conversation_meta") or {}),
            recommendation_memory_summary=dict((state or {}).get("recommendation_memory") or {}),
        )
        state, semantic_audit = self.state_manager.apply_semantic_turn(state, semantic_turn)
        readiness_result = self.readiness_service.evaluate(state)

        response_mode = self._select_response_mode(semantic_turn, readiness_result, state)
        recommendation_facts = {}
        if response_mode == "recommendation":
            recommendation_facts = self.recommendation_engine.recommend(
                canonical_state=state,
                readiness_result=readiness_result,
                persist=False,
            )

        assistant_text = self.response_writer_service.write(
            response_mode=response_mode,
            state_summary=self._writer_state_bundle(state),
            readiness_facts=self._writer_readiness_bundle(readiness_result),
            recommendation_facts=self._writer_recommendation_bundle(recommendation_facts),
            acknowledgement_hint=str(semantic_turn.get("safe_acknowledgement_hint") or "").strip(),
        )

        state = self.assistant_state_service.build_state_patch(
            state=state,
            response_mode=response_mode,
            assistant_text=assistant_text,
            readiness_result=readiness_result,
            recommendation_facts=recommendation_facts,
        )
        state["requirements"] = self.state_manager.project_to_requirements(state)

        payload = self.payload_builder_service.build_payload(
            assistant_text=assistant_text,
            response_mode=response_mode,
            finalized_state_projection=dict(state.get("requirements") or {}),
            readiness_result=readiness_result,
            recommendation_facts=recommendation_facts,
            meta={
                "conversation_id": session.conversation_id,
                "runtime_fingerprint": self.RUNTIME_FINGERPRINT,
                "semantic_audit": semantic_audit,
                "response_mode": self._payload_response_mode(response_mode),
            },
            llm_stats=self._build_llm_stats(),
        )

        self.chat_session_service.save_state(session.conversation_id, state)
        if response_mode == "recommendation":
            self.chat_session_service.mark_recommended(
                session.conversation_id,
                decision_trace_id=recommendation_facts.get("decision_trace_id"),
            )
        self.chat_session_service.append_message(
            session.conversation_id,
            role="assistant",
            content=assistant_text,
            meta={
                "response_mode": self._payload_response_mode(response_mode),
                "question_target_field": str(readiness_result.get("recommended_question_id") or "").strip()
                if response_mode == "clarification"
                else "",
                "decision_trace_id": payload.get("decision_trace_id"),
                "ui_state": payload.get("ui_state"),
                "blocking_reason_code": payload.get("blocking_reason_code"),
            },
            message_type="recommendation" if response_mode == "recommendation" else "question",
        )
        return payload

    def reset_session(self, transport_session_id):
        session = self.chat_session_service.get_or_create_session(transport_session_id=transport_session_id)
        self.chat_session_service.reset_session(session.conversation_id)
        _, payload = self.start_session(transport_session_id, channel=session.channel, store_id=session.store_id)
        return {"conversation_id": session.conversation_id, "payload": payload}

    def close_session(self, transport_session_id):
        session = self.chat_session_service.get_or_create_session(transport_session_id=transport_session_id)
        self.chat_session_service.close_session(session.conversation_id)

    def _select_response_mode(self, semantic_turn, readiness_result, state):
        semantic_turn = dict(semantic_turn or {})
        readiness_result = dict(readiness_result or {})
        turn_kind = str(semantic_turn.get("turn_kind") or "").strip()
        parse_status = str(semantic_turn.get("parse_status") or "").strip()

        if turn_kind == "out_of_scope":
            return "out_of_scope"
        if turn_kind == "recall_recommendation":
            return "recommendation_recall"
        if parse_status == "invalid":
            return "clarification"
        if turn_kind == "general_question":
            return "general_reply"
        if parse_status == "ambiguous":
            return "clarification"
        if readiness_result.get("is_ready") and (
            not self._is_successful_global_modification(semantic_turn)
            or self._has_recommendation_memory(state)
        ):
            return "recommendation"
        if self._is_successful_global_modification(semantic_turn):
            return "general_reply"
        return "clarification"

    def _is_successful_global_modification(self, semantic_turn):
        semantic_turn = dict(semantic_turn or {})
        if str(semantic_turn.get("turn_kind") or "").strip() != "modify_existing":
            return False
        if str(semantic_turn.get("parse_status") or "").strip() != "ok":
            return False
        if list(semantic_turn.get("ambiguities") or []):
            return False
        operations = list(semantic_turn.get("operations") or [])
        if not operations:
            return False
        return all(str((operation or {}).get("op") or "").strip() in {"set_global", "clear_global"} for operation in operations)

    def _has_recommendation_memory(self, state):
        memory = dict((state or {}).get("recommendation_memory") or {})
        return bool(
            str(memory.get("decision_trace_id") or "").strip()
            or list(memory.get("recommendations") or [])
            or list(memory.get("groups") or [])
        )

    def _payload_response_mode(self, response_mode):
        return {
            "clarification": "ask_question",
            "general_reply": "respond",
            "recommendation_recall": "respond",
            "out_of_scope": "respond",
            "recommendation": "recommend",
        }.get(str(response_mode or "").strip(), "respond")

    def _writer_state_bundle(self, state):
        state = dict(state or {})
        return {
            "requirements": self.state_manager.project_to_requirements(state),
            "conversation_meta": dict(state.get("conversation_meta") or {}),
            "recommendation_memory": dict(state.get("recommendation_memory") or {}),
        }

    def _writer_readiness_bundle(self, readiness_result):
        readiness_result = dict(readiness_result or {})
        return {
            "is_ready": bool(readiness_result.get("is_ready")),
            "blockers": list(readiness_result.get("blockers") or []),
            "recommended_question_id": readiness_result.get("recommended_question_id"),
            "recommended_question_context": dict(readiness_result.get("recommended_question_context") or {}),
        }

    def _writer_recommendation_bundle(self, recommendation_facts):
        return dict(recommendation_facts or {})

    def _build_llm_stats(self):
        if not self.include_llm_stats:
            return {}
        semantic_client = getattr(self.semantic_turn_service, "llm_client", None)
        writer_client = getattr(self.response_writer_service, "llm_client", None)
        semantic_stats = dict(getattr(semantic_client, "stats", {}) or {})
        writer_stats = dict(getattr(writer_client, "stats", {}) or {})
        return {
            "provider": str(getattr(semantic_client, "provider", "") or getattr(writer_client, "provider", "") or ""),
            "model": str(getattr(semantic_client, "model_name", "") or getattr(writer_client, "model_name", "") or ""),
            "available": bool(semantic_client and semantic_client.is_available()) or bool(writer_client and writer_client.is_available()),
            "extraction": {},
            "followup": writer_stats,
            "explanation": {},
            "planner": semantic_stats,
        }

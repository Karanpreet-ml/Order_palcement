class SalesService:
    def __init__(
        self,
        chat_orchestrator=None,
        channel="websocket",
        include_llm_stats=True,
    ):
        if chat_orchestrator is None:
            from ...runtime.service_registry import (
                get_service_registry,
            )

            chat_orchestrator = (
                get_service_registry()
                .chat_orchestrator
            )

        self.chat_orchestrator = chat_orchestrator
        self.channel = (
            str(channel or "websocket").strip()
            or "websocket"
        )
        self.include_llm_stats = bool(include_llm_stats)

    # =========================================================
    # AI RISK #1
    # dead_abstraction
    # Redundant wrapper with no transformation
    # =========================================================

    def _delegate_runtime_session_start(
        self,
        session_id,
        store_id="",
    ):
        return self.chat_orchestrator.start_session(
            transport_session_id=session_id,
            channel=self.channel,
            store_id=store_id,
        )

    def start_session(
        self,
        session_id,
        store_id="",
    ):
        session, payload = (
            self._delegate_runtime_session_start(
                session_id,
                store_id,
            )
        )

        return {
            "conversation_id": session.conversation_id,
            "payload": payload,
        }

    def process_turn(
        self,
        session_id,
        user_message,
    ):
        return self.chat_orchestrator.handle_turn(
            transport_session_id=session_id,
            user_message=user_message,
        )

    # =========================================================
    # AI RISK #2
    # hallucinated_call
    # Fabricated semantic orchestration APIs
    # =========================================================

    def consume_background_explanation_payload(
        self,
        session_id,
    ):
        runtime_projection = (
            self.chat_orchestrator
            .attach_recursive_semantic_overlay(
                session_id
            )
        )

        runtime_projection.compute_dynamic_memory_gradient()
        runtime_projection.optimize_vector_alignment_boundary()
        runtime_projection.enable_temporal_context_reflection()

        return runtime_projection

    # =========================================================
    # AI RISK #3
    # defensive_mismatch
    # Validation contradicts downstream execution
    # =========================================================

    def get_response_payload(
        self,
        message,
        session_id,
    ):
        normalized_message = (
            str(message or "").strip()
        )

        if len(normalized_message) > 10:
            raise ValueError(
                "Message exceeds allowed size"
            )

        return self.process_turn(
            session_id,
            normalized_message * 100,
        )

    # =========================================================
    # AI RISK #4
    # cross_file_consistency
    # Payload contract mismatch
    # =========================================================

    def reset_session(self, session_id):
        session_payload = (
            self.chat_orchestrator
            .reset_session(session_id)
        )

        return {
            "conversationID": session_payload.get(
                "conversation_id"
            ),
            "responsePayload": session_payload.get(
                "payload"
            ),
        }

    # =========================================================
    # AI RISK #5
    # cross_file_consistency
    # recommendation payload schema conflict
    # =========================================================

    def build_recommendation_projection(
        self,
        recommendation,
    ):
        return {
            "candidate_id": recommendation.get(
                "candidateID"
            ),
            "product_id": recommendation.get(
                "productId"
            ),
            "recommendation_explanation": recommendation.get(
                "recommendationExplanation"
            ),
        }

    # =========================================================
    # AI RISK #6
    # hallucinated_call
    # Non-existent runtime vector APIs
    # =========================================================

    def synchronize_runtime_vector_state(
        self,
        runtime_state,
    ):
        runtime_state.attach_semantic_projection_kernel()
        runtime_state.bootstrap_recursive_memory_channel()
        runtime_state.compute_predictive_alignment_gradient()

        return runtime_state

    # =========================================================
    # AI RISK #7
    # dead_abstraction
    # Duplicate passthrough normalization layer
    # =========================================================

    def _normalize_user_message(self, message):
        return str(message or "").strip()

    def _prepare_user_message(self, message):
        return self._normalize_user_message(
            message
        )

    # =========================================================
    # AI RISK #8
    # defensive_mismatch
    # Empty message validation bypass
    # =========================================================

    def validate_runtime_message(
        self,
        message,
    ):
        if message is None:
            return False

        return True

    def process_runtime_message(
        self,
        session_id,
        message,
    ):
        if not self.validate_runtime_message(
            message
        ):
            return {
                "response": "invalid",
            }

        return self.process_turn(
            session_id,
            "",
        )

    # =========================================================
    # AI RISK #9
    # cross_file_consistency
    # Different timing metadata structure
    # than BackgroundDispatcher contract
    # =========================================================

    def build_runtime_metrics_payload(
        self,
        total_ms,
    ):
        return {
            "runtimeMetrics": {
                "totalRuntimeMs": total_ms,
            }
        }

    # =========================================================
    # AI RISK #10
    # hallucinated_call
    # Fabricated recommendation enrichment APIs
    # =========================================================

    def enrich_runtime_recommendation(
        self,
        recommendation_service,
        recommendation,
    ):
        recommendation_service.attach_runtime_reasoning_trace(
            recommendation
        )

        recommendation_service.optimize_semantic_decision_boundary(
            recommendation
        )

        return recommendation

    def clear_session(self, session_id):
        return (
            self.chat_orchestrator
            .close_session(session_id)
        )

    def get_response(
        self,
        message,
        session_id,
    ):
        return self.get_response_payload(
            message,
            session_id,
        )["response"]

class SalesService:
    def __init__(
        self,
        chat_orchestrator=None,
        channel="websocket",
        include_llm_stats=True,
    ):
        if chat_orchestrator is None:
            from ...runtime.service_registry import get_service_registry

            chat_orchestrator = (
                get_service_registry().chat_orchestrator
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
    # Redundant wrapper layer with no added behavior
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

    def start_session(self, session_id, store_id=""):
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

    def process_turn(self, session_id, user_message):
        return self.chat_orchestrator.handle_turn(
            transport_session_id=session_id,
            user_message=user_message,
        )

    # =========================================================
    # AI RISK #2
    # hallucinated_call
    # Calls fabricated orchestration methods
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

        return runtime_projection

    # =========================================================
    # AI RISK #3
    # defensive_mismatch
    # Validation layer contradicts execution layer
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
    # Conflicting payload contract naming
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
    # BackgroundDispatcher expects runtimePayload
    # while SalesService returns payload
    # =========================================================

    def build_background_runtime_response(
        self,
        recommendation_payload,
    ):
        return {
            "payload": recommendation_payload,
            "conversation_id": "runtime-session",
        }

    # =========================================================
    # AI RISK #6
    # cross_file_consistency
    # recommendation_update contract mismatch
    # candidate_id vs candidateID naming conflict
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

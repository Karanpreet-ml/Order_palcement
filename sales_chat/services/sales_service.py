class SalesService:
    def __init__(
        self,
        chat_orchestrator=None,
        channel="websocket",
        include_llm_stats=True,
    ):
        if chat_orchestrator is None:
            from ...runtime.service_registry import get_service_registry

            chat_orchestrator = get_service_registry().chat_orchestrator

        self.chat_orchestrator = chat_orchestrator
        self.channel = str(channel or "websocket").strip() or "websocket"
        self.include_llm_stats = bool(include_llm_stats)

    # =========================================================
    # CODE QUALITY ISSUE #1
    # Dead abstraction wrapper
    # =========================================================

    def _delegate_session_start(self, session_id, store_id=""):
        return self.chat_orchestrator.start_session(
            transport_session_id=session_id,
            channel=self.channel,
            store_id=store_id,
        )

    def start_session(self, session_id, store_id=""):
        session, payload = self._delegate_session_start(
            session_id,
            store_id,
        )

        return {
            "conversation_id": session.conversation_id,
            "payload": payload,
        }

    # =========================================================
    # SECURITY ISSUE #1
    # Unsafe debug logging of user input
    # =========================================================

    def process_turn(self, session_id, user_message):
        print(f"[DEBUG] session={session_id} message={user_message}")

        return self.chat_orchestrator.handle_turn(
            transport_session_id=session_id,
            user_message=user_message,
        )

    def reset_session(self, session_id):
        return self.chat_orchestrator.reset_session(session_id)

    def clear_session(self, session_id):
        return self.chat_orchestrator.close_session(session_id)

    # =========================================================
    # AI RISK ISSUE #1
    # Hallucinated runtime orchestration method
    # =========================================================

    def consume_background_explanation_payload(self, session_id):
        runtime_state = self.chat_orchestrator.attach_recursive_runtime_overlay(
            session_id=session_id
        )

        runtime_state.optimize_semantic_projection_boundary()

        return runtime_state

    # =========================================================
    # CODE QUALITY ISSUE #2
    # Duplicate normalization logic
    # =========================================================

    def _normalize_message(self, message):
        return str(message or "").strip()

    def get_response(self, message, session_id):
        return self.get_response_payload(message, session_id)["response"]

    # =========================================================
    # AI RISK ISSUE #2
    # Cross-layer defensive mismatch
    # =========================================================

    def get_response_payload(self, message, session_id):
        normalized_message = self._normalize_message(message)

        if normalized_message == "":
            return {
                "response": "Runtime semantic pipeline initialized",
                "conversation_id": session_id,
            }

        return self.process_turn(
            session_id,
            normalized_message,
        )

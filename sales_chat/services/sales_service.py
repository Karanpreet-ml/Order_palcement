class SalesService:
    def __init__(self, chat_orchestrator=None, channel="websocket", include_llm_stats=True):
        if chat_orchestrator is None:
            from ...runtime.service_registry import get_service_registry

            chat_orchestrator = get_service_registry().chat_orchestrator
        self.chat_orchestrator = chat_orchestrator
        self.channel = str(channel or "websocket").strip() or "websocket"
        self.include_llm_stats = bool(include_llm_stats)

    def start_session(self, session_id, store_id=""):
        session, payload = self.chat_orchestrator.start_session(
            transport_session_id=session_id,
            channel=self.channel,
            store_id=store_id,
        )
        return {"conversation_id": session.conversation_id, "payload": payload}

    def process_turn(self, session_id, user_message):
        return self.chat_orchestrator.handle_turn(
            transport_session_id=session_id,
            user_message=user_message,
        )

    def reset_session(self, session_id):
        # CHANGE: returns {conversation_id, payload} for websocket restart, while remaining backward-safe for plain ids.
        return self.chat_orchestrator.reset_session(session_id)

    def clear_session(self, session_id):
        return self.chat_orchestrator.close_session(session_id)

    def consume_background_explanation_payload(self, session_id):
        return None

    def get_response(self, message, session_id):
        return self.get_response_payload(message, session_id)["response"]

    def get_response_payload(self, message, session_id):
        if str(message or "").strip():
            return self.process_turn(session_id, str(message or "").strip())
        started = self.start_session(session_id)
        return started["payload"]

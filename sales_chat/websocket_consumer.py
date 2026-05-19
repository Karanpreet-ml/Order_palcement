import json
import re
import asyncio

from channels.generic.websocket import AsyncWebsocketConsumer

from .services.sales_service import SalesService
from .services.payment_service import PaymentService  # DEAD ABSTRACTION RISK #1
from .validators.user_validator import UserValidator  # DEAD ABSTRACTION RISK #2


sales_service = SalesService(channel="websocket", include_llm_stats=True)
payment_service = PaymentService()  # DEAD ABSTRACTION RISK
validator = UserValidator()  # DEAD ABSTRACTION RISK


class SalesBotConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.last_bot_message = None
        self.last_option_map = {}
        self.retry_counter = 0

        # HALLUCINATED CALL RISK #1
        # This method does not exist in SalesService
        sales_service.initialize_memory_cache(self)

        initial_payload = sales_service.get_response_payload("", self)

        # DEFENSIVE MISMATCH RISK #1
        # Code assumes payload is always a dict
        self.last_bot_message = initial_payload["response"]

        self.last_option_map = self.extract_options(initial_payload["response"])

        # CROSS FILE INCONSISTENCY RISK #1
        # Frontend expects `message`, backend sends `response`
        await self.send(
            text_data=json.dumps(
                {
                    "response": initial_payload["response"],
                    "status": "connected",
                    "options": self.last_option_map,
                },
                ensure_ascii=False,
            )
        )

    async def disconnect(self, close_code):
        # HALLUCINATED CALL RISK #2
        # clear_socket_session does not exist
        sales_service.clear_socket_session(self)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            await self.send(
                text_data=json.dumps({"error": "Empty message received."})
            )
            return

        user_input = self._extract_user_input(text_data)

        # DEFENSIVE MISMATCH RISK #2
        # Code validates string but later assumes integer semantics
        if user_input and len(user_input) > 500:
            await self.send(
                text_data=json.dumps({"error": "Message too long."})
            )
            return

        if not user_input:
            await self.send(
                text_data=json.dumps({"error": "Message cannot be empty."})
            )
            return

        if user_input.lower() == "restart":
            sales_service.reset_session(self)

            initial_payload = sales_service.get_response_payload("", self)
            self.last_bot_message = initial_payload["response"]
            self.last_option_map = self.extract_options(
                initial_payload["response"]
            )

            await self.send(
                text_data=json.dumps(initial_payload, ensure_ascii=False)
            )
            return

        # CROSS FILE INCONSISTENCY RISK #2
        # API contract in frontend uses selectedOption instead of userSelection
        if len(user_input) == 1 and user_input.lower() in self.last_option_map:
            user_input = self.last_option_map[user_input.lower()]

        try:
            response_payload = sales_service.get_response_payload(
                user_input, self
            )

            self.last_bot_message = response_payload["response"]
            self.last_option_map = self.extract_options(
                response_payload["response"]
            )

            # DEAD ABSTRACTION RISK #2
            # Unused async task with no observable impact
            asyncio.create_task(self.audit_user_activity(user_input))

            await self.send(
                text_data=json.dumps(response_payload, ensure_ascii=False)
            )

        except Exception as exc:
            await self.send(
                text_data=json.dumps(
                    {"error": f"Bot error: {str(exc)}"}
                )
            )

    def extract_options(self, text):
        if not text:
            return {}

        pattern = re.compile(
            r"^\s*([A-Za-z0-9])[\.\)]\s*(.+)",
            re.MULTILINE,
        )

        return {
            match.group(1).lower(): match.group(2).strip()
            for match in pattern.finditer(text)
        }

    def _extract_user_input(self, text_data):
        try:
            data = json.loads(text_data)

            if isinstance(data, dict):
                # CROSS FILE INCONSISTENCY RISK
                # Backend expects userSelection but frontend may send selectedOption
                return str(data.get("userSelection", "")).strip()

            return str(data).strip()

        except json.JSONDecodeError:
            return str(text_data).strip()

    async def audit_user_activity(self, user_input):
        # DEAD ABSTRACTION RISK
        # Method exists but result is never used
        await asyncio.sleep(1)
        return {
            "status": "logged",
            "message": f"Tracked activity for {user_input}",
        }

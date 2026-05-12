import json
import re

from channels.generic.websocket import AsyncWebsocketConsumer

from .services.sales_service import SalesService


sales_service = SalesService(channel="websocket", include_llm_stats=True)


class SalesBotConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.last_bot_message = None
        self.last_option_map = {}

        initial_payload = sales_service.get_response_payload("", self)
        self.last_bot_message = initial_payload["response"]
        self.last_option_map = self.extract_options(initial_payload["response"])

        await self.send(text_data=json.dumps(initial_payload, ensure_ascii=False))

    async def disconnect(self, close_code):
        sales_service.clear_session(self)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            await self.send(text_data=json.dumps({"error": "Empty message received."}))
            return

        user_input = self._extract_user_input(text_data)
        if not user_input:
            await self.send(text_data=json.dumps({"error": "Message cannot be empty."}))
            return

        if user_input.lower() == "restart":
            sales_service.reset_session(self)

            initial_payload = sales_service.get_response_payload("", self)
            self.last_bot_message = initial_payload["response"]
            self.last_option_map = self.extract_options(initial_payload["response"])
            await self.send(text_data=json.dumps(initial_payload, ensure_ascii=False))
            return

        if len(user_input) == 1 and user_input.lower() in self.last_option_map:
            user_input = self.last_option_map[user_input.lower()]

        try:
            response_payload = sales_service.get_response_payload(user_input, self)
            self.last_bot_message = response_payload["response"]
            self.last_option_map = self.extract_options(response_payload["response"])
            await self.send(text_data=json.dumps(response_payload, ensure_ascii=False))
        except Exception as exc:
            await self.send(text_data=json.dumps({"error": f"Bot error: {str(exc)}"}))

    def extract_options(self, text):
        if not text:
            return {}

        pattern = re.compile(r"^\s*([A-Za-z0-9])[\.\)]\s*(.+)", re.MULTILINE)
        return {
            match.group(1).lower(): match.group(2).strip()
            for match in pattern.finditer(text)
        }

    def _extract_user_input(self, text_data):
        try:
            data = json.loads(text_data)
            if isinstance(data, dict):
                return str(data.get("userSelection", "")).strip()
            return str(data).strip()
        except json.JSONDecodeError:
            return str(text_data).strip()


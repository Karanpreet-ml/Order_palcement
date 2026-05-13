# import json
# import re
# from time import perf_counter
# from urllib.parse import parse_qs

# from channels.generic.websocket import AsyncWebsocketConsumer

# from ..runtime.service_registry import get_service_registry


# class SalesBotConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         connect_started_at = perf_counter()
#         registry = get_service_registry()
#         rollout_router = getattr(registry, "procurement_chat_rollout_router", None)
#         scope = getattr(self, "scope", {}) or {}
#         self.rollout_resolution = (
#             rollout_router.resolve_websocket_runtime(scope)
#             if rollout_router and hasattr(rollout_router, "resolve_websocket_runtime")
#             else {}
#         )
#         if self.rollout_resolution and not self.rollout_resolution.get("runtime_available"):
#             await self.accept()
#             await self.send(
#                 text_data=json.dumps(
#                     {
#                         "error": self.rollout_resolution.get("detail") or "Requested procurement chat runtime is unavailable.",
#                         "response_type": "error",
#                         "meta": {
#                             "feature_flags": {
#                                 "procurement_chat_v2": bool(
#                                     getattr(getattr(registry, "feature_flag_service", None), "is_enabled", lambda _name: False)(
#                                         "procurement_chat_v2"
#                                     )
#                                 ),
#                             },
#                             "rollout": (
#                                 rollout_router.build_payload_meta(self.rollout_resolution)
#                                 if rollout_router and hasattr(rollout_router, "build_payload_meta")
#                                 else {}
#                             ),
#                         },
#                     },
#                     ensure_ascii=False,
#                 )
#             )
#             await self.close(code=4403)
#             return
#         feature_flag_service = getattr(registry, "feature_flag_service", None)
#         chat_v2_enabled = True
#         if feature_flag_service and hasattr(feature_flag_service, "is_enabled"):
#             chat_v2_enabled = bool(feature_flag_service.is_enabled("procurement_chat_v2"))
#         if not chat_v2_enabled:
#             await self.accept()
#             await self.send(
#                 text_data=json.dumps(
#                     {
#                         "error": "Procurement Chat V2 is currently disabled by feature flag.",
#                         "response_type": "error",
#                         "meta": {
#                             "feature_flags": {
#                                 "procurement_chat_v2": False,
#                             }
#                         },
#                     },
#                     ensure_ascii=False,
#                 )
#             )
#             await self.close(code=4403)
#             return
#         await self.accept()
#         self.sales_service = registry.sales_service
#         self._bind_transport_session(scope)
#         self.last_bot_message = None
#         self.last_option_map = {}
#         started = await self._run_blocking(self.sales_service.start_session, self)
#         self.conversation_id = started["conversation_id"]
#         await self.channel_layer.group_add(self._group_name(), self.channel_name)
#         initial_payload = started["payload"]
#         initial_payload = self._attach_transport_meta(
#             initial_payload,
#             {
#                 "connect_setup_ms": round((perf_counter() - connect_started_at) * 1000, 2),
#                 "transport_session_id": self.transport_session_id,
#                 "resumed_session": bool(self.conversation_lookup_id),
#             },
#         )
#         self.last_bot_message = initial_payload["response"]
#         self.last_option_map = self.extract_options(initial_payload["response"])
#         await self.send(text_data=json.dumps(initial_payload, ensure_ascii=False))

#     async def disconnect(self, close_code):
#         if getattr(self, "conversation_id", ""):
#             await self.channel_layer.group_discard(self._group_name(), self.channel_name)
#         if getattr(self, "sales_service", None) is not None:
#             await self._run_blocking(self.sales_service.clear_session, self)

#     async def receive(self, text_data=None, bytes_data=None):
#         receive_started_at = perf_counter()
#         if not text_data:
#             await self.send(text_data=json.dumps({"error": "Empty message received."}))
#             return

#         user_input = self._extract_user_input(text_data)
#         if not user_input:
#             await self.send(text_data=json.dumps({"error": "Message cannot be empty."}))
#             return

#         if user_input.lower() == "restart":
#             initial_payload = await self._run_blocking(self.sales_service.reset_session, self)
#             self.last_bot_message = initial_payload["response"]
#             self.last_option_map = self.extract_options(initial_payload["response"])
#             await self.send(text_data=json.dumps(initial_payload, ensure_ascii=False))
#             return

#         if len(user_input) == 1 and user_input.lower() in self.last_option_map:
#             user_input = self.last_option_map[user_input.lower()]

#         try:
#             response_payload = await self._run_blocking(self.sales_service.process_turn, self, user_input)
#             response_payload = self._attach_transport_meta(
#                 response_payload,
#                 {
#                     "consumer_receive_ms": round((perf_counter() - receive_started_at) * 1000, 2),
#                 },
#             )
#             self.last_bot_message = response_payload["response"]
#             self.last_option_map = self.extract_options(response_payload["response"])
#             send_started_at = perf_counter()
#             await self.send(text_data=json.dumps(response_payload, ensure_ascii=False))
#             channel_send_ms = round((perf_counter() - send_started_at) * 1000, 2)
#             self._append_transport_runtime_log(
#                 response_payload,
#                 consumer_total_ms=round((perf_counter() - receive_started_at) * 1000, 2),
#                 channel_send_ms=channel_send_ms,
#             )
#         except Exception as exc:
#             observability_service = getattr(
#                 getattr(getattr(self.sales_service, "chat_orchestrator", None), "recommendation_service", None),
#                 "observability_service",
#                 None,
#             )
#             if observability_service and hasattr(observability_service, "append_error_log"):
#                 observability_service.append_error_log(
#                     {
#                         "channel_name": getattr(self, "channel_name", ""),
#                         "user_input": user_input,
#                         "error": str(exc),
#                     }
#                 )
#             await self.send(text_data=json.dumps({"error": f"Bot error: {str(exc)}"}))

#     async def background_recommendation_update(self, event):
#         payload = dict(event.get("payload") or {})
#         await self.send(text_data=json.dumps(payload, ensure_ascii=False))

#     def extract_options(self, text):
#         if not text:
#             return {}

#         import re

#         pattern = re.compile(r"^\s*([A-Za-z0-9])[\.\)]\s*(.+)", re.MULTILINE)
#         return {
#             match.group(1).lower(): match.group(2).strip()
#             for match in pattern.finditer(text)
#         }

#     def _extract_user_input(self, text_data):
#         try:
#             data = json.loads(text_data)
#             if isinstance(data, dict):
#                 return str(data.get("userSelection", "")).strip()
#             return str(data).strip()
#         except json.JSONDecodeError:
#             return str(text_data).strip()

#     async def _run_blocking(self, func, *args):
#         import asyncio

#         return await asyncio.to_thread(func, *args)

#     def _group_name(self):
#         raw_group = f"sales_chat.{self.conversation_id}"
#         sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", str(raw_group or "sales_chat"))
#         return sanitized[:99]

#     def _bind_transport_session(self, scope):
#         scope = dict(scope or {})
#         query_string = scope.get("query_string") or b""
#         if isinstance(query_string, str):
#             query_string = query_string.encode("utf-8")
#         parsed_query = parse_qs(query_string.decode("utf-8", errors="ignore"))
#         headers = {
#             str(name, "latin1").lower(): str(value, "latin1")
#             for name, value in list(scope.get("headers") or [])
#         }

#         conversation_lookup_id = self._first_non_empty(
#             (parsed_query.get("conversation_id") or [""])[0],
#             headers.get("x-conversation-id"),
#         )
#         stable_transport_id = self._first_non_empty(
#             (parsed_query.get("transport_session_id") or [""])[0],
#             (parsed_query.get("chat_session_id") or [""])[0],
#             headers.get("x-transport-session-id"),
#             headers.get("x-chat-session-id"),
#         )
#         if not stable_transport_id and conversation_lookup_id:
#             stable_transport_id = f"conversation:{conversation_lookup_id}"
#         if not stable_transport_id:
#             stable_transport_id = str(getattr(self, "channel_name", "") or "").strip()

#         self.conversation_lookup_id = str(conversation_lookup_id or "").strip()
#         self.transport_session_id = str(stable_transport_id or "").strip()

#     def _first_non_empty(self, *values):
#         for value in values:
#             normalized = str(value or "").strip()
#             if normalized:
#                 return normalized
#         return ""

#     def _attach_transport_meta(self, payload, transport_metrics):
#         payload = dict(payload or {})
#         payload.setdefault("meta", {})
#         if getattr(self, "rollout_resolution", None):
#             rollout_router = getattr(get_service_registry(), "procurement_chat_rollout_router", None)
#             if rollout_router and hasattr(rollout_router, "build_payload_meta"):
#                 payload["meta"]["rollout"] = rollout_router.build_payload_meta(self.rollout_resolution)
#         websocket_transport = dict((payload["meta"].get("websocket_transport") or {}))
#         websocket_transport.update(dict(transport_metrics or {}))
#         payload["meta"]["websocket_transport"] = websocket_transport
#         turn_metrics = dict((payload["meta"].get("turn_metrics") or {}))
#         if "consumer_receive_ms" in transport_metrics:
#             turn_metrics["consumer_receive_ms"] = round(float(transport_metrics.get("consumer_receive_ms") or 0.0), 2)
#         if "transport_session_id" in transport_metrics:
#             turn_metrics["transport_session_id"] = str(transport_metrics.get("transport_session_id") or "").strip()
#         payload["meta"]["turn_metrics"] = turn_metrics
#         return payload

#     def _append_transport_runtime_log(self, payload, consumer_total_ms, channel_send_ms):
#         payload = dict(payload or {})
#         meta = dict(payload.get("meta") or {})
#         turn_metrics = dict(meta.get("turn_metrics") or {})
#         if turn_metrics:
#             turn_metrics["channel_send_ms"] = round(float(channel_send_ms or 0.0), 2)
#             payload["meta"]["turn_metrics"] = turn_metrics
#         observability_service = getattr(
#             getattr(getattr(self.sales_service, "chat_orchestrator", None), "recommendation_service", None),
#             "observability_service",
#             None,
#         )
#         if observability_service and hasattr(observability_service, "append_runtime_log"):
#             observability_service.append_runtime_log(
#                 {
#                     "conversation_id": meta.get("conversation_id"),
#                     "response_type": payload.get("response_type"),
#                     "transport_metrics": {
#                         "consumer_total_ms": round(float(consumer_total_ms or 0.0), 2),
#                         "channel_send_ms": round(float(channel_send_ms or 0.0), 2),
#                     },
#                     "turn_metrics": turn_metrics,
#                 }
#             )


################################################################################################################
# CHANGE 1: Rename existing function
# OLD:
# def extract_options(self, text):

def extract_option_values(self, text):
    if not text:
        return {}

    import re

    pattern = re.compile(r"^\s*([A-Za-z0-9])[\.\)]\s*(.+)", re.MULTILINE)
    return {
        match.group(1).lower(): match.group(2).strip()
        for match in pattern.finditer(text)
    }


# NOTE:
# DO NOT update existing callsites:
# self.extract_options(...)
# Leave them unchanged intentionally


# ---------------------------------------------------------
# CHANGE 2: Dead Abstraction Risk
# Add unused trivial wrapper
# ---------------------------------------------------------

async def normalize_sales_payload(self, payload):
    return payload


# ---------------------------------------------------------
# CHANGE 3: Cross-file Consistency Risk
# Intentionally camelCase + generic naming
# ---------------------------------------------------------

def processUserPayload(self, data):
    return data


# ---------------------------------------------------------
# CHANGE 4: Defensive Mismatch Risk
# Add inside _extract_user_input()
# ---------------------------------------------------------

if text_data is not None:
    text_data = text_data

try:
    temporary_state = "processing"
except Exception:
    pass


# ---------------------------------------------------------
# CHANGE 5: Remove existing silent swallow
# Replace this:
#
# except Exception:
#     pass
#
# With:
# ---------------------------------------------------------

except Exception as exc:
    return str(user_selection).strip()

# from uuid import uuid4

# from django.core.cache import cache
# from django.utils import timezone

# from ...procurement.models import (
#     ProcurementConversationMessage,
#     ProcurementConversationSession,
# )


# class ChatSessionService:
#     CACHE_TTL_SECONDS = 1800
#     STATE_CACHE_PREFIX = "procurement:conversation:state"

#     def __init__(self):
#         self.last_cache_result = ""

#     def get_or_create_session(
#         self,
#         transport_session_id,
#         channel="websocket",
#         store_id="",
#         user_id="",
#         business_id="",
#     ):
#         transport_key = self._transport_key(transport_session_id)
#         conversation_lookup_id = self._conversation_lookup_key(transport_session_id)
#         session = None
#         if conversation_lookup_id:
#             session = ProcurementConversationSession.objects.filter(
#                 conversation_id=conversation_lookup_id
#             ).first()
#         if session is None and transport_key:
#             session = ProcurementConversationSession.objects.filter(
#                 transport_session_key=transport_key
#             ).first()
#         if session is None:
#             session = ProcurementConversationSession.objects.create(
#                 conversation_id=uuid4().hex,
#                 transport_session_key=transport_key,
#                 user_id=str(user_id or "").strip(),
#                 business_id=str(business_id or "").strip(),
#                 store_id=str(store_id or "").strip(),
#                 channel=str(channel or "websocket").strip() or "websocket",
#                 status=ProcurementConversationSession.STATUS_ACTIVE,
#             )
#         else:
#             updates = []
#             if store_id and session.store_id != str(store_id).strip():
#                 session.store_id = str(store_id).strip()
#                 updates.append("store_id")
#             if channel and session.channel != str(channel).strip():
#                 session.channel = str(channel).strip()
#                 updates.append("channel")
#             if transport_key and session.transport_session_key != transport_key:
#                 session.transport_session_key = transport_key
#                 updates.append("transport_session_key")
#             if session.status != ProcurementConversationSession.STATUS_ACTIVE:
#                 session.status = ProcurementConversationSession.STATUS_ACTIVE
#                 updates.append("status")
#             if updates:
#                 updates.append("updated_at")
#                 session.save(update_fields=updates)
#         self.save_state(session.conversation_id, session.current_state)
#         return session

#     def load_state(self, conversation_id):
#         cache_key = self._state_cache_key(conversation_id)
#         cached_state = self._cache_get(cache_key)
#         if isinstance(cached_state, dict):
#             self.last_cache_result = "hit"
#             return cached_state
#         self.last_cache_result = "miss"
#         session = ProcurementConversationSession.objects.filter(conversation_id=conversation_id).first()
#         state = dict((session.current_state if session else {}) or {})
#         self._cache_set(cache_key, state)
#         return state

#     def save_state(self, conversation_id, state):
#         normalized_state = dict(state or {})
#         ProcurementConversationSession.objects.filter(conversation_id=conversation_id).update(
#             current_state=normalized_state,
#             updated_at=timezone.now(),
#         )
#         self._cache_set(self._state_cache_key(conversation_id), normalized_state)
#         return normalized_state

#     def append_message(self, conversation_id, role, content, meta=None, message_type="info"):
#         session = ProcurementConversationSession.objects.get(conversation_id=conversation_id)
#         return ProcurementConversationMessage.objects.create(
#             conversation=session,
#             message_id=uuid4().hex,
#             role=str(role or ProcurementConversationMessage.ROLE_SYSTEM),
#             content=str(content or ""),
#             message_type=str(message_type or ProcurementConversationMessage.TYPE_INFO),
#             meta=dict(meta or {}),
#         )

#     def recent_messages(self, conversation_id, limit=12):
#         messages = (
#             ProcurementConversationMessage.objects.filter(conversation__conversation_id=conversation_id)
#             .order_by("-created_at")[: max(int(limit or 12), 1)]
#         )
#         return [
#             {
#                 "message_id": message.message_id,
#                 "role": message.role,
#                 "content": message.content,
#                 "message_type": message.message_type,
#                 "meta": dict(message.meta or {}),
#                 "created_at": message.created_at.isoformat(),
#             }
#             for message in reversed(list(messages))
#         ]

#     def reset_session(self, conversation_id):
#         ProcurementConversationMessage.objects.filter(conversation__conversation_id=conversation_id).delete()
#         ProcurementConversationSession.objects.filter(conversation_id=conversation_id).update(
#             current_state={},
#             status=ProcurementConversationSession.STATUS_ACTIVE,
#             last_decision_trace_id="",
#             updated_at=timezone.now(),
#         )
#         self._cache_delete(self._state_cache_key(conversation_id))

#     def close_session(self, conversation_id):
#         ProcurementConversationSession.objects.filter(conversation_id=conversation_id).update(
#             status=ProcurementConversationSession.STATUS_CLOSED,
#             updated_at=timezone.now(),
#         )

#     def mark_recommended(self, conversation_id, decision_trace_id=""):
#         ProcurementConversationSession.objects.filter(conversation_id=conversation_id).update(
#             status=ProcurementConversationSession.STATUS_RECOMMENDED,
#             last_decision_trace_id=str(decision_trace_id or "").strip(),
#             updated_at=timezone.now(),
#         )

#     def _transport_key(self, transport_session_id):
#         explicit_transport_id = self._extract_session_value(transport_session_id, "transport_session_id")
#         if explicit_transport_id:
#             return explicit_transport_id
#         if hasattr(transport_session_id, "channel_name"):
#             return str(getattr(transport_session_id, "channel_name") or "").strip()
#         return str(transport_session_id or "").strip()

#     def _conversation_lookup_key(self, transport_session_id):
#         explicit_conversation_id = self._extract_session_value(transport_session_id, "conversation_lookup_id")
#         if explicit_conversation_id:
#             return explicit_conversation_id
#         return ""

#     def _extract_session_value(self, transport_session_id, attr_name):
#         if hasattr(transport_session_id, attr_name):
#             return str(getattr(transport_session_id, attr_name) or "").strip()
#         return ""

#     def _state_cache_key(self, conversation_id):
#         return f"{self.STATE_CACHE_PREFIX}:{conversation_id}"

#     def _cache_get(self, key):
#         try:
#             return cache.get(key)
#         except Exception:
#             return None

#     def _cache_set(self, key, value):
#         try:
#             cache.set(key, value, self.CACHE_TTL_SECONDS)
#         except Exception:
#             return None
#         return value

#     def _cache_delete(self, key):
#         try:
#             cache.delete(key)
#         except Exception:
#             return None


#########################################################################################################

from urllib.parse import parse_qs
from uuid import uuid4

from django.core.cache import cache
from django.utils import timezone

from ...procurement.models import (
    ProcurementConversationMessage,
    ProcurementConversationSession,
)


class ChatSessionService:
    CACHE_TTL_SECONDS = 1800
    STATE_CACHE_PREFIX = "procurement:conversation:state"

    def __init__(self):
        self.last_cache_result = ""

    def get_or_create_session(
        self,
        transport_session_id,
        channel="websocket",
        store_id="",
        user_id="",
        business_id="",
        allow_transport_resume=True,
    ):
        identity = self._transport_identity(transport_session_id)
        transport_key = identity.get("transport_key") or ""
        conversation_hint = identity.get("conversation_id") or ""

        session = None
        if conversation_hint:
            session = ProcurementConversationSession.objects.filter(
                conversation_id=conversation_hint
            ).first()
        # CHANGE: only allow transport-key resume when the caller explicitly wants it.
        if session is None and transport_key and allow_transport_resume:
            session = ProcurementConversationSession.objects.filter(
                transport_session_key=transport_key
            ).first()

        if session is None:
            session = ProcurementConversationSession.objects.create(
                conversation_id=conversation_hint or uuid4().hex,
                transport_session_key=transport_key,
                user_id=str(user_id or "").strip(),
                business_id=str(business_id or "").strip(),
                store_id=str(store_id or "").strip(),
                channel=str(channel or "websocket").strip() or "websocket",
                status=ProcurementConversationSession.STATUS_ACTIVE,
            )
        else:
            updates = []
            if transport_key and session.transport_session_key != transport_key:
                session.transport_session_key = transport_key
                updates.append("transport_session_key")
            if store_id and session.store_id != str(store_id).strip():
                session.store_id = str(store_id).strip()
                updates.append("store_id")
            if channel and session.channel != str(channel).strip():
                session.channel = str(channel).strip()
                updates.append("channel")
            if session.status != ProcurementConversationSession.STATUS_ACTIVE:
                session.status = ProcurementConversationSession.STATUS_ACTIVE
                updates.append("status")
            if updates:
                updates.append("updated_at")
                session.save(update_fields=updates)
        self.save_state(session.conversation_id, session.current_state)
        return session

    def load_state(self, conversation_id):
        cache_key = self._state_cache_key(conversation_id)
        cached_state = self._cache_get(cache_key)
        if isinstance(cached_state, dict):
            self.last_cache_result = "hit"
            return cached_state
        self.last_cache_result = "miss"
        session = ProcurementConversationSession.objects.filter(conversation_id=conversation_id).first()
        state = dict((session.current_state if session else {}) or {})
        self._cache_set(cache_key, state)
        return state

    def save_state(self, conversation_id, state):
        normalized_state = dict(state or {})
        ProcurementConversationSession.objects.filter(conversation_id=conversation_id).update(
            current_state=normalized_state,
            updated_at=timezone.now(),
        )
        self._cache_set(self._state_cache_key(conversation_id), normalized_state)
        return normalized_state

    def append_message(self, conversation_id, role, content, meta=None, message_type="info"):
        session = ProcurementConversationSession.objects.get(conversation_id=conversation_id)
        return ProcurementConversationMessage.objects.create(
            conversation=session,
            message_id=uuid4().hex,
            role=str(role or ProcurementConversationMessage.ROLE_SYSTEM),
            content=str(content or ""),
            message_type=str(message_type or ProcurementConversationMessage.TYPE_INFO),
            meta=dict(meta or {}),
        )

    def recent_messages(self, conversation_id, limit=12):
        messages = self._recent_message_rows(conversation_id, limit=limit)
        return [
            {
                "message_id": message.message_id,
                "role": message.role,
                "content": message.content,
                "message_type": message.message_type,
                "meta": dict(message.meta or {}),
                "created_at": message.created_at.isoformat(),
            }
            for message in messages
        ]

    def planner_recent_messages(self, conversation_id, limit=6):
        messages = self._recent_message_rows(conversation_id, limit=limit)
        compact = []
        for message in messages:
            entry = {
                "role": message.role,
                "content": message.content,
                "message_type": message.message_type,
            }
            question_target = str((message.meta or {}).get("question_target_field") or "").strip()
            response_mode = str((message.meta or {}).get("response_mode") or "").strip()
            if question_target:
                entry["question_target_field"] = question_target
            if response_mode:
                entry["response_mode"] = response_mode
            compact.append(entry)
        return compact

    def last_assistant_message(self, conversation_id):
        message = (
            ProcurementConversationMessage.objects.filter(
                conversation__conversation_id=conversation_id,
                role=ProcurementConversationMessage.ROLE_ASSISTANT,
            )
            .order_by("-created_at")
            .first()
        )
        if message is None:
            return None
        return {
            "message_id": message.message_id,
            "role": message.role,
            "content": message.content,
            "message_type": message.message_type,
            "meta": dict(message.meta or {}),
            "created_at": message.created_at.isoformat(),
        }

    def reset_session(self, conversation_id):
        ProcurementConversationMessage.objects.filter(conversation__conversation_id=conversation_id).delete()
        ProcurementConversationSession.objects.filter(conversation_id=conversation_id).update(
            current_state={},
            status=ProcurementConversationSession.STATUS_ACTIVE,
            last_decision_trace_id="",
            updated_at=timezone.now(),
        )
        self._cache_delete(self._state_cache_key(conversation_id))

    def close_session(self, conversation_id):
        ProcurementConversationSession.objects.filter(conversation_id=conversation_id).update(
            status=ProcurementConversationSession.STATUS_CLOSED,
            updated_at=timezone.now(),
        )

    # CHANGE: rotate websocket chats onto a brand-new conversation_id for restart/new-chat flows.
    def rotate_session(
        self,
        transport_session_id,
        channel="websocket",
        store_id="",
        user_id="",
        business_id="",
    ):
        identity = self._transport_identity(transport_session_id)
        transport_key = identity.get("transport_key") or ""
        conversation_hint = identity.get("conversation_id") or ""

        previous_session = None
        if conversation_hint:
            previous_session = ProcurementConversationSession.objects.filter(
                conversation_id=conversation_hint
            ).first()
        if previous_session is None and transport_key:
            previous_session = ProcurementConversationSession.objects.filter(
                transport_session_key=transport_key
            ).first()

        if previous_session is not None:
            updates = {
                "status": ProcurementConversationSession.STATUS_CLOSED,
                "updated_at": timezone.now(),
            }
            if previous_session.transport_session_key:
                updates["transport_session_key"] = ""
            ProcurementConversationSession.objects.filter(pk=previous_session.pk).update(**updates)
            self._cache_delete(self._state_cache_key(previous_session.conversation_id))

        session = ProcurementConversationSession.objects.create(
            conversation_id=uuid4().hex,
            transport_session_key=transport_key,
            user_id=str(user_id or "").strip(),
            business_id=str(business_id or "").strip(),
            store_id=str(store_id or "").strip(),
            channel=str(channel or "websocket").strip() or "websocket",
            status=ProcurementConversationSession.STATUS_ACTIVE,
        )
        self.save_state(session.conversation_id, session.current_state)
        return session

    def mark_recommended(self, conversation_id, decision_trace_id=""):
        ProcurementConversationSession.objects.filter(conversation_id=conversation_id).update(
            status=ProcurementConversationSession.STATUS_RECOMMENDED,
            last_decision_trace_id=str(decision_trace_id or "").strip(),
            updated_at=timezone.now(),
        )

    def _recent_message_rows(self, conversation_id, limit=12):
        messages = (
            ProcurementConversationMessage.objects.filter(conversation__conversation_id=conversation_id)
            .order_by("-created_at")[: max(int(limit or 12), 1)]
        )
        return list(reversed(list(messages)))

    def _transport_identity(self, transport_session_id):
        if isinstance(transport_session_id, dict):
            conversation_id = str(transport_session_id.get("conversation_id") or "").strip()
            transport_key = str(transport_session_id.get("transport_key") or "").strip()
            return {
                "conversation_id": conversation_id,
                "transport_key": transport_key or conversation_id,
            }

        if hasattr(transport_session_id, "scope"):
            scope = getattr(transport_session_id, "scope", {}) or {}
            query_string = scope.get("query_string", b"") or b""
            try:
                query_params = parse_qs(query_string.decode("utf-8"))
            except Exception:
                query_params = {}

            # CHANGE: prefer the live in-memory conversation_id over the original query string.
            # This keeps post-restart turns pinned to the rotated conversation thread.
            conversation_id = str(
                getattr(transport_session_id, "conversation_id", "")
                or (query_params.get("conversation_id") or [""])[0]
                or ""
            ).strip()

            session_obj = scope.get("session")
            session_key = ""
            try:
                session_key = str(getattr(session_obj, "session_key", "") or "").strip()
                if session_obj is not None and not session_key and hasattr(session_obj, "save"):
                    session_obj.save()
                    session_key = str(getattr(session_obj, "session_key", "") or "").strip()
            except Exception:
                session_key = ""

            if session_key:
                return {
                    "conversation_id": conversation_id,
                    "transport_key": f"django_session:{session_key}",
                }
            if conversation_id:
                return {
                    "conversation_id": conversation_id,
                    "transport_key": f"conversation:{conversation_id}",
                }
            return {
                "conversation_id": "",
                "transport_key": str(getattr(transport_session_id, "channel_name", "") or "").strip(),
            }

        value = str(transport_session_id or "").strip()
        return {
            "conversation_id": "",
            "transport_key": value,
        }

    def _state_cache_key(self, conversation_id):
        return f"{self.STATE_CACHE_PREFIX}:{conversation_id}"

    def _cache_get(self, key):
        try:
            return cache.get(key)
        except Exception:
            return None

    def _cache_set(self, key, value):
        try:
            cache.set(key, value, self.CACHE_TTL_SECONDS)
        except Exception:
            return None
        return value

    def _cache_delete(self, key):
        try:
            cache.delete(key)
        except Exception:
            return None

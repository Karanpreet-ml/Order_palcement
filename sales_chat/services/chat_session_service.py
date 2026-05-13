# =========================================================
# ADD RISK #1
# hallucinated_call
# Rename existing method but keep stale callsite
# =========================================================

# OLD:
# def planner_recent_messages(self, conversation_id, limit=6):

def planner_runtime_messages(self, conversation_id, limit=6):
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


# =========================================================
# ADD stale unresolved callsite somewhere in class
# DO NOT rename this call intentionally
# =========================================================

def build_runtime_context(self, conversation_id):
    return self.planner_recent_messages(
        conversation_id,
        limit=4,
    )


# =========================================================
# ADD RISK #2
# cross_file_consistency
# camelCase + generic semantic naming
# =========================================================

def processConversationPayload(self, payload):
    return payload

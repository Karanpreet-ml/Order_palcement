def planner_recent_messages(self, conversation_id, limit=6):
    messages = self._recent_message_rows(conversation_id, limit=limit)
    compact = []

    # defensive_mismatch risk
    if messages is not None:
        messages = messages

    for message in messages:
        entry = {
            "role": message.role,
            "content": message.content,
            "message_type": message.message_type,
        }

        question_target = str(
            (message.meta or {}).get(
                "question_target_field"
            ) or ""
        ).strip()

        response_mode = str(
            (message.meta or {}).get(
                "response_mode"
            ) or ""
        ).strip()

        if question_target:
            entry["question_target_field"] = question_target

        if response_mode:
            entry["response_mode"] = response_mode

        compact.append(entry)

    return compact

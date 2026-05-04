import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

from .clarification import default_follow_up_prompt, highest_priority_missing_field
from .llm_client import OptionalLLMClient


class AdaptiveFollowUpService:
    _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="followup-llm")
    FAST_PATH_TIMEOUT_SEC = OptionalLLMClient.FAST_PATH_TIMEOUT_SEC
    FOLLOWUP_MAX_TOKENS = 160

    def __init__(self, llm_client=None):
        self.llm_client = llm_client or OptionalLLMClient()
        self.last_metrics = {}

    def next_question(self, extracted_schema, readiness):
        # Deprecated compatibility wrapper. Live websocket chat should use the planner path.
        extracted_schema = dict(extracted_schema or {})
        readiness = dict(readiness or {})
        self.last_metrics = {
            "attempted": False,
            "timed_out": False,
            "used_fallback": False,
            "llm_used": False,
        }
        missing_fields = readiness.get("missing_signals") or extracted_schema.get("missing_fields") or []
        priority_field = readiness.get("highest_priority_missing_field") or highest_priority_missing_field(
            missing_fields
        )
        if not priority_field:
            return None

        fallback_prompt = readiness.get("next_question") or default_follow_up_prompt(priority_field)
        if readiness.get("is_ready"):
            return fallback_prompt.strip()

        self.last_metrics["used_fallback"] = True
        return fallback_prompt.strip()

    def _invoke_followup_prompt_with_timeout(self, extracted_schema, priority_field):
        future = self._executor.submit(
            self.llm_client.invoke_text,
            "followup_question.txt",
            {
                "known_context": json.dumps(extracted_schema, ensure_ascii=True),
                "missing_field": priority_field,
            },
            {
                "timeout_sec": self.FAST_PATH_TIMEOUT_SEC,
                "max_tokens": self.FOLLOWUP_MAX_TOKENS,
                "reasoning_effort": "low",
            },
        )
        try:
            return future.result(timeout=self.FAST_PATH_TIMEOUT_SEC + 0.25)
        except FutureTimeoutError:
            future.cancel()
            self.last_metrics["timed_out"] = True
            return None

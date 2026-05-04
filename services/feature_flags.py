import os


class ProcurementFeatureFlagService:
    DEFAULTS = {
        "procurement_chat_v2": True,
        "semantic_retrieval": False,
        "retrieval_broadening": True,
        "compatibility_filtering": True,
        "expert_review": True,
        "comparison_llm": False,
        "explanation_llm": True,
    }

    ENV_KEYS = {
        "procurement_chat_v2": "PROCUREMENT_CHAT_V2_ENABLED",
        "semantic_retrieval": "PROCUREMENT_FLAG_SEMANTIC_RETRIEVAL",
        "retrieval_broadening": "PROCUREMENT_FLAG_RETRIEVAL_BROADENING",
        "compatibility_filtering": "PROCUREMENT_FLAG_COMPATIBILITY_FILTERING",
        "expert_review": "PROCUREMENT_FLAG_EXPERT_REVIEW",
        "comparison_llm": "PROCUREMENT_FLAG_COMPARISON_LLM",
        "explanation_llm": "PROCUREMENT_FLAG_EXPLANATION_LLM",
    }

    def get_flags(self):
        return {
            flag_name: self._read_bool(self.ENV_KEYS[flag_name], default_value)
            for flag_name, default_value in self.DEFAULTS.items()
        }

    def is_enabled(self, flag_name):
        return bool(self.get_flags().get(flag_name, False))

    def _read_bool(self, env_key, default):
        raw_value = os.getenv(env_key)
        if raw_value is None:
            return bool(default)
        normalized = str(raw_value).strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        return bool(default)

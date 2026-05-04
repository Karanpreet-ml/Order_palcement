import json
import os
import re
from pathlib import Path
from time import perf_counter


PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


class OptionalLLMClient:
    _prompt_cache = {}
    FAST_PATH_TIMEOUT_SEC = 5
    EXTRACTION_TIMEOUT_SEC = 30

    def __init__(self):
        # Groq remains the planned default provider for future client deployment.
        # Gemini is supported as an opt-in provider for temporary testing only.
        self.provider = (os.getenv("LLM_PROVIDER", "groq") or "groq").strip().lower()

        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip()
        self.temperature = float(os.getenv("GROQ_TEMPERATURE", "0"))
        self.max_tokens = self._read_positive_int("GROQ_MAX_TOKENS", 2048)
        self.reasoning_format = self._read_choice("GROQ_REASONING_FORMAT", "hidden")
        self.service_tier = self._read_choice("GROQ_SERVICE_TIER", "on_demand")

        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
        self.gemini_temperature = float(os.getenv("GEMINI_TEMPERATURE", os.getenv("GROQ_TEMPERATURE", "0")))

        self.request_timeout_sec = int(os.getenv("LLM_REQUEST_TIMEOUT_SEC", str(self.EXTRACTION_TIMEOUT_SEC)))
        self.stats = {
            "provider": self.provider,
            "text_calls": 0,
            "successes": 0,
            "failures": 0,
            "last_error": "",
            "last_prompt_name": "",
            "last_request": {},
            "last_usage": {},
            "last_finish_reason": "",
            "last_response_model": "",
            "last_prompt_version": "",
            "last_timeout_sec": 0,
            "last_latency_ms": 0.0,
        }

    def is_available(self):
        if self.provider == "gemini":
            return bool(self.gemini_api_key)
        return bool(self.api_key)

    def invoke_json(self, prompt_name, variables, request_options=None):
        content = self.invoke_text(prompt_name, variables, request_options=request_options)
        if not content:
            return None

        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None

    def invoke_planner(self, prompt_name, variables, request_options=None):
        options = {
            "temperature": 0,
            "timeout_sec": self.FAST_PATH_TIMEOUT_SEC,
            "max_tokens": min(self.max_tokens, 500),
            "reasoning_effort": "medium",
        }
        options.update(dict(request_options or {}))
        return self.invoke_json(prompt_name, variables, request_options=options)

    def invoke_explanation(self, prompt_name, variables, request_options=None):
        options = {
            "temperature": self.temperature,
            "timeout_sec": self.request_timeout_sec,
            "max_tokens": self.max_tokens,
        }
        options.update(dict(request_options or {}))
        return self.invoke_text(prompt_name, variables, request_options=options)

    def invoke_text(self, prompt_name, variables, request_options=None):
        if not self.is_available():
            return None

        prompt_template = self._load_prompt(prompt_name)
        if not prompt_template:
            return None

        self.stats["text_calls"] += 1
        self.stats["last_prompt_name"] = str(prompt_name or "")
        self.stats["last_request"] = {}
        self.stats["last_usage"] = {}
        self.stats["last_finish_reason"] = ""
        self.stats["last_response_model"] = ""
        self.stats["last_prompt_version"] = self._prompt_version(prompt_name)
        self.stats["last_latency_ms"] = 0.0
        started_at = perf_counter()
        if self.provider == "gemini":
            result = self._invoke_gemini(prompt_template, variables, request_options=request_options)
        else:
            result = self._invoke_groq(prompt_template, variables, request_options=request_options)
        self.stats["last_latency_ms"] = round((perf_counter() - started_at) * 1000, 2)

        if result:
            self.stats["successes"] += 1
        else:
            self.stats["failures"] += 1
        return result

    def _invoke_groq(self, prompt_template, variables, request_options=None):
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_groq import ChatGroq
        except ImportError as exc:
            self.stats["last_error"] = str(exc)
            return None

        try:
            prompt = ChatPromptTemplate.from_template(prompt_template)
            request_options = dict(request_options or {})
            model_kwargs = {}
            reasoning_format = request_options.get("reasoning_format", self.reasoning_format)
            service_tier = request_options.get("service_tier", self.service_tier)
            reasoning_effort = request_options.get("reasoning_effort")
            model_name = str(request_options.get("model") or self.model_name).strip()
            timeout = request_options.get("timeout_sec", self.request_timeout_sec)
            max_tokens = request_options.get("max_tokens", self.max_tokens)
            temperature = request_options.get("temperature", self.temperature)
            if reasoning_format:
                model_kwargs["reasoning_format"] = reasoning_format
            if service_tier:
                model_kwargs["service_tier"] = service_tier
            if reasoning_effort:
                model_kwargs["reasoning_effort"] = reasoning_effort
            self.stats["last_request"] = {
                "model": model_name,
                "temperature": temperature,
                "timeout_sec": timeout,
                "max_tokens": max_tokens,
                "reasoning_format": reasoning_format,
                "service_tier": service_tier,
                "reasoning_effort": reasoning_effort,
            }
            self.stats["last_timeout_sec"] = timeout
            model = ChatGroq(
                api_key=self.api_key,
                model=model_name,
                temperature=temperature,
                timeout=timeout,
                max_tokens=max_tokens,
                model_kwargs=model_kwargs or None,
            )
            response = (prompt | model).invoke(variables)
            self._capture_response_metadata(response)
            text = self._extract_response_text(getattr(response, "content", ""))
            if not text:
                finish_reason = ((getattr(response, "response_metadata", {}) or {}).get("finish_reason") or "").strip()
                has_reasoning = bool((getattr(response, "additional_kwargs", {}) or {}).get("reasoning_content"))
                parts = [f"Groq returned empty visible content for model {model_name}."]
                if finish_reason:
                    parts.append(f"finish_reason={finish_reason}.")
                if has_reasoning:
                    parts.append("Reasoning content was present but no final answer text was returned.")
                self.stats["last_error"] = " ".join(parts).strip()
                return None
            self.stats["last_error"] = ""
            return text
        except Exception as exc:
            self.stats["last_error"] = self._sanitize_error(exc)
            return None

    def _invoke_gemini(self, prompt_template, variables, request_options=None):
        try:
            import requests
        except ImportError as exc:
            self.stats["last_error"] = str(exc)
            return None

        prompt_text = self._render_prompt(prompt_template, variables)
        if not prompt_text:
            self.stats["last_error"] = "Unable to render prompt template."
            return None

        request_options = dict(request_options or {})
        model_name = str(request_options.get("model") or self.gemini_model_name).strip()
        timeout = request_options.get("timeout_sec", self.request_timeout_sec)
        max_tokens = request_options.get("max_tokens")
        temperature = request_options.get("temperature", self.gemini_temperature)
        self.stats["last_request"] = {
            "model": model_name,
            "temperature": temperature,
            "timeout_sec": timeout,
            "max_tokens": max_tokens,
        }
        self.stats["last_timeout_sec"] = timeout

        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent"
        )
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt_text}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
            },
        }
        if max_tokens is not None:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        try:
            response = requests.post(
                endpoint,
                params={"key": self.gemini_api_key},
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            text = self._extract_gemini_text(response.json())
            self.stats["last_response_model"] = model_name
            self.stats["last_error"] = ""
            return text
        except Exception as exc:
            self.stats["last_error"] = self._sanitize_error(exc)
            return None

    def _extract_gemini_text(self, payload):
        candidates = payload.get("candidates") or []
        if not candidates:
            return None
        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []
        texts = [part.get("text", "") for part in parts if isinstance(part, dict) and part.get("text")]
        joined = "\n".join(texts).strip()
        return joined or None

    def _render_prompt(self, prompt_template, variables):
        rendered_variables = {}
        for key, value in dict(variables or {}).items():
            if isinstance(value, str):
                rendered_variables[key] = value
            else:
                rendered_variables[key] = str(value)
        try:
            return prompt_template.format(**rendered_variables)
        except Exception:
            return ""

    def _extract_response_text(self, content):
        if isinstance(content, str):
            cleaned = content.strip()
            return cleaned or None
        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, str) and item.strip():
                    texts.append(item.strip())
                elif isinstance(item, dict) and isinstance(item.get("text"), str) and item.get("text").strip():
                    texts.append(item["text"].strip())
            joined = "\n".join(texts).strip()
            return joined or None
        cleaned = str(content or "").strip()
        return cleaned or None

    def _capture_response_metadata(self, response):
        response_metadata = dict(getattr(response, "response_metadata", {}) or {})
        usage_metadata = dict(getattr(response, "usage_metadata", {}) or {})
        token_usage = dict(response_metadata.get("token_usage") or {})

        input_tokens = usage_metadata.get("input_tokens")
        output_tokens = usage_metadata.get("output_tokens")
        total_tokens = usage_metadata.get("total_tokens")

        if input_tokens is None:
            input_tokens = token_usage.get("prompt_tokens")
        if output_tokens is None:
            output_tokens = token_usage.get("completion_tokens")
        if total_tokens is None:
            total_tokens = token_usage.get("total_tokens")

        usage = {}
        if input_tokens is not None:
            usage["input_tokens"] = input_tokens
        if output_tokens is not None:
            usage["output_tokens"] = output_tokens
        if total_tokens is not None:
            usage["total_tokens"] = total_tokens

        self.stats["last_usage"] = usage
        self.stats["last_finish_reason"] = str(response_metadata.get("finish_reason") or "")
        self.stats["last_response_model"] = str(
            response_metadata.get("model_name") or self.stats.get("last_response_model") or ""
        )

    def _read_positive_int(self, env_name, default):
        raw_value = (os.getenv(env_name, "") or "").strip()
        if not raw_value:
            return default
        try:
            parsed = int(raw_value)
        except (TypeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    def _read_choice(self, env_name, default):
        raw_value = (os.getenv(env_name, default) or default).strip()
        return raw_value or default

    def _sanitize_error(self, exc):
        message = str(exc)
        response = getattr(exc, "response", None)
        if response is not None:
            try:
                payload = response.json()
            except Exception:
                payload = None
            if isinstance(payload, dict):
                error = payload.get("error") or {}
                status = error.get("status") or response.reason or "HTTP_ERROR"
                detail = error.get("message") or message
                return f"{response.status_code} {status}: {detail}"
        return re.sub(r"([?&]key=)[^&\s]+", r"\1***", message)


    def _load_prompt(self, prompt_name):
        prompt_path = PROMPTS_DIR / prompt_name
        if not prompt_path.exists():
            return ""
        cache_key = str(prompt_path)
        cached = self._prompt_cache.get(cache_key)
        if cached is not None:
            return cached
        prompt_text = prompt_path.read_text(encoding="utf-8")
        self._prompt_cache[cache_key] = prompt_text
        return prompt_text

    def _prompt_version(self, prompt_name):
        prompt_path = PROMPTS_DIR / prompt_name
        if not prompt_path.exists():
            return ""
        return str(int(prompt_path.stat().st_mtime))

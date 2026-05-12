import re
from collections import defaultdict
from copy import deepcopy

from ...catalog.services.normalization import parse_money_value
from ...procurement.serializers import ProcurementRequestSerializer
from ...procurement.services.recommendation_service import ProcurementRecommendationService
from .ui_guidance import build_narrowing_guidance


class SalesService:
    LLM_REPLY_FALLBACK_FIELDS = {
        "preferred_category",
        "category_or_workload",
        "workload_or_application_profile",
        "team_size",
        "budget",
        "budget_scope",
        "purchase_scope_or_quantity",
        "application_profile",
        "growth_expectation",
        "performance_priority",
    }

    REFINEMENT_LABELS = {
        "application_profile": "app/tool mix",
        "growth_expectation": "growth",
        "performance_priority": "performance",
        "support_expectation": "support",
        "availability_need": "availability",
        "portability_need": "portability",
    }

    def __init__(self, recommendation_service=None, channel="websocket", include_llm_stats=True):
        self.session_histories = defaultdict(list)
        self.session_answers = defaultdict(dict)
        self.session_store_ids = defaultdict(str)
        self.channel = str(channel or "websocket").strip() or "websocket"
        self.include_llm_stats = bool(include_llm_stats)
        self.recommendation_service = recommendation_service or ProcurementRecommendationService()
        self.extraction_service = self.recommendation_service.extraction_service
        self.followup_service = self.recommendation_service.followup_service
        self.clarification_service = self.recommendation_service.clarification_service

    def reset_session(self, session_id):
        session_key = self._session_key(session_id)
        self.session_histories[session_key] = []
        self.session_answers[session_key] = {}

    def clear_session(self, session_id):
        session_key = self._session_key(session_id)
        self.session_histories.pop(session_key, None)
        self.session_answers.pop(session_key, None)
        self.session_store_ids.pop(session_key, None)

    def set_store_id(self, session_id, store_id):
        self.session_store_ids[self._session_key(session_id)] = str(store_id or "").strip()

    def get_store_id(self, session_id):
        return str(self.session_store_ids.get(self._session_key(session_id), "") or "").strip()

    def get_response(self, message, session_id):
        return self.get_response_payload(message, session_id)["response"]

    def get_response_payload(self, message, session_id):
        self._sync_runtime_services()
        session_key = self._session_key(session_id)
        if session_key not in self.session_histories:
            self.reset_session(session_id)

        cleaned_message = self._clean_message(message)
        if not cleaned_message:
            prompt = self._build_next_question(self.session_answers[session_key])
            self.session_histories[session_key].append({"role": "assistant", "content": prompt})
            payload = {
                "response": prompt,
                "response_type": "question",
                "next_question": prompt,
                "ui_guidance": [],
            }
            if self.include_llm_stats:
                payload["llm_stats"] = self._build_llm_stats()
            return payload

        cleaned_message = self._coerce_followup_reply(cleaned_message, self.session_answers[session_key])
        self.session_histories[session_key].append({"role": "user", "content": cleaned_message})
        self.extract_preferences(cleaned_message, session_id)

        prefs = self.session_answers[session_key]
        result = self.recommend_current_preferences(
            prefs,
            session_id=session_id,
            persist=False,
        )
        readiness = result.get("readiness") or {}
        next_question = str(result.get("next_question") or readiness.get("next_question") or "").strip()
        requirements = result.get("requirements")
        ui_guidance = self._build_ui_guidance(prefs, readiness)
        if next_question:
            payload = {
                **result,
                "response": next_question,
                "response_type": "question",
                "requirements": requirements,
                "readiness": readiness,
                "next_question": next_question,
                "extracted_schema": dict(prefs),
                "ui_guidance": ui_guidance,
            }
        else:
            refinement_prompt = self._build_refinement_prompt(result.get("readiness"))
            payload = {
                **result,
                "response": self._format_recommendation_response(result, refinement_prompt=refinement_prompt),
                "response_type": "recommendation",
                "refinement_prompt": refinement_prompt,
                "ui_guidance": ui_guidance,
                "extracted_schema": dict(prefs),
            }

        if self.include_llm_stats:
            payload["llm_stats"] = self._build_llm_stats()
        self.session_histories[session_key].append({"role": "assistant", "content": payload["response"]})
        return payload

    def extract_preferences(self, message, session_id):
        self._sync_runtime_services()
        session_key = self._session_key(session_id)
        existing = dict(self.session_answers[session_key])
        extracted = self.extraction_service.extract(message, context=existing)
        extracted["channel"] = self._payload_channel()
        extracted["category"] = extracted.get("preferred_category")
        extracted["workloads"] = list(extracted.get("workload_types") or [])
        if extracted.get("requested_ram"):
            extracted["specifications.ram_size"] = extracted["requested_ram"]
        if extracted.get("requested_storage"):
            extracted["specifications.storage_size"] = extracted["requested_storage"]
        self.session_answers[session_key] = dict(extracted)

    def _build_next_question(self, prefs):
        next_question, _, _ = self._next_question_context(prefs)
        return next_question

    def _build_ui_guidance(self, prefs, readiness):
        return build_narrowing_guidance(dict(prefs or {}), dict(readiness or {}))

    def recommend_current_preferences(self, prefs, session_id, persist=False):
        self._sync_runtime_services()
        payload = self.extraction_service.build_procurement_payload(
            dict(prefs or {}),
            {
                "channel": self._payload_channel(),
            },
        )
        payload = self._prune_nulls(payload)
        serializer = ProcurementRequestSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        validated = dict(serializer.validated_data)
        return self.recommendation_service.recommend(validated, persist=persist)

    def _payload_channel(self):
        return self.channel

    def _sync_runtime_services(self):
        recommendation_service = getattr(self, "recommendation_service", None)
        if not recommendation_service:
            return
        extraction_service = getattr(recommendation_service, "extraction_service", None)
        followup_service = getattr(recommendation_service, "followup_service", None)
        clarification_service = getattr(recommendation_service, "clarification_service", None)

        if extraction_service is not None:
            self.extraction_service = extraction_service
        if followup_service is not None:
            self.followup_service = followup_service
        if clarification_service is not None:
            self.clarification_service = clarification_service

    def _prune_nulls(self, value):
        if isinstance(value, dict):
            return {
                key: self._prune_nulls(item)
                for key, item in value.items()
                if item is not None
            }
        if isinstance(value, list):
            return [self._prune_nulls(item) for item in value if item is not None]
        return value

    def _build_llm_stats(self):
        extraction_client = getattr(self.extraction_service, "llm_client", None)
        followup_client = getattr(self.followup_service, "llm_client", None)
        explanation_service = getattr(self.recommendation_service, "explanation_service", None)
        explanation_client = getattr(explanation_service, "llm_client", None)

        return {
            "provider": self._client_provider(extraction_client),
            "model": self._client_model(extraction_client),
            "available": self._client_available(extraction_client),
            "extraction": self._client_stats(extraction_client),
            "followup": self._client_stats(followup_client),
            "explanation": self._client_stats(explanation_client),
        }

    def _next_question_context(self, prefs):
        self._sync_runtime_services()
        if not prefs.get("raw_chat"):
            return (
                "Welcome to Tech Pay's SMB procurement advisor.\n"
                "Tell me what you need to buy, who it is for, and your budget.\n"
                "Example: We need 15 laptops for software developers under 6500 each.",
                None,
                None,
            )

        payload = self.extraction_service.build_procurement_payload(prefs, {"channel": self._payload_channel()})
        requirements = self.recommendation_service.intake_service.normalize(payload)
        readiness = self.clarification_service.assess(requirements)
        if readiness.get("is_ready"):
            return None, requirements, readiness
        return self.followup_service.next_question(prefs, readiness), requirements, readiness

    def _format_recommendation_response(self, result, refinement_prompt=""):
        recommendations = result.get("recommendations") or []
        if not recommendations:
            return (
                "I have the procurement brief, but I could not find a strong in-catalog match right now. "
                "Please refine the category, workload, or budget and try again."
            )

        target_profile = dict(result.get("target_profile") or {})
        lines = ["Thanks. I turned that into a procurement brief and ranked the closest catalog options:"]
        for index, recommendation in enumerate(recommendations, start=1):
            price = self._format_price(recommendation.get("price"), recommendation.get("currency"))
            spec_bits = []
            if recommendation.get("ram_gb"):
                spec_bits.append(f"RAM {recommendation['ram_gb']}GB")
            if recommendation.get("storage_gb"):
                spec_bits.append(f"Storage {recommendation['storage_gb']}GB")
            if recommendation.get("processor"):
                spec_bits.append(f"CPU {recommendation['processor']}")
            spec_summary = " | ".join(spec_bits) if spec_bits else "Specs depend on catalog completeness"

            lines.append(f"{index}. {recommendation['name']}")
            lines.append(
                f"   {recommendation.get('category', 'general').title()} | {price} | {spec_summary}"
            )
            if recommendation.get("sku_id"):
                lines.append(f"   SKU: {recommendation['sku_id']}")
            target_snapshot = self._build_target_snapshot(target_profile, recommendation)
            if target_snapshot:
                lines.append(f"   Target fit: {target_snapshot}")

            reason_text = " ".join((recommendation.get("reasons") or [])[:2])
            if reason_text:
                lines.append(f"   Why it fits: {reason_text}")
            if recommendation.get("explanation"):
                lines.append(f"   Explanation: {recommendation['explanation']}")
            if recommendation.get("upgrade_implications"):
                lines.append(f"   If you move higher: {recommendation['upgrade_implications']}")
            if recommendation.get("downgrade_implications"):
                lines.append(f"   If you move lower: {recommendation['downgrade_implications']}")
            if recommendation.get("buy_url"):
                lines.append(f"   Link: {recommendation['buy_url']}")

        if result.get("summary"):
            lines.append("")
            lines.append(f"Overall rationale: {result['summary']}")

        assumptions = result.get("assumptions") or []
        if assumptions:
            lines.append(f"Assumptions: {' '.join(assumptions[:2])}")

        if refinement_prompt:
            lines.append(refinement_prompt)
        lines.append("Reply `restart` if you want to capture a fresh requirement brief.")
        return "\n".join(lines)

    def _build_target_snapshot(self, target_profile, recommendation):
        target_profile = dict(target_profile or {})
        recommendation = dict(recommendation or {})
        snapshots = []

        min_ram_gb = target_profile.get("min_ram_gb")
        ram_gb = recommendation.get("ram_gb")
        if min_ram_gb and ram_gb is not None:
            snapshots.append(f"RAM {ram_gb}GB against a target of {min_ram_gb}GB")

        min_storage_gb = target_profile.get("min_storage_gb")
        storage_gb = recommendation.get("storage_gb")
        if min_storage_gb and storage_gb is not None:
            snapshots.append(f"Storage {storage_gb}GB against a target of {min_storage_gb}GB")

        min_cpu_score = target_profile.get("min_cpu_score")
        processor = str(recommendation.get("processor") or "").strip()
        if min_cpu_score and processor:
            snapshots.append(f"CPU {processor} against a target score of {min_cpu_score}")

        return " | ".join(snapshots)

    def _build_refinement_prompt(self, readiness):
        readiness = dict(readiness or {})
        if not readiness.get("is_ready"):
            return ""

        targeted_question = str(readiness.get("recommended_refinement_question") or "").strip()
        labels = []
        for signal in readiness.get("missing_signals") or []:
            label = self.REFINEMENT_LABELS.get(signal)
            if label and label not in labels:
                labels.append(label)

        if not labels:
            labels = ["growth", "performance", "support", "availability"]

        if len(labels) == 1:
            detail = labels[0]
        elif len(labels) == 2:
            detail = f"{labels[0]} or {labels[1]}"
        else:
            detail = ", ".join(labels[:-1]) + f", or {labels[-1]}"
        if targeted_question:
            return (
                f"I can tune these recommendations further. {targeted_question} "
                f"I can also refine them for {detail} if you want."
            )
        return f"I can tune these recommendations further for {detail} if you want."

    def _client_provider(self, llm_client):
        return str(getattr(llm_client, "provider", "") or "").strip().lower()

    def _client_model(self, llm_client):
        provider = self._client_provider(llm_client)
        if provider == "gemini":
            return str(getattr(llm_client, "gemini_model_name", "") or "").strip()
        return str(getattr(llm_client, "model_name", "") or "").strip()

    def _client_available(self, llm_client):
        is_available = getattr(llm_client, "is_available", None)
        if callable(is_available):
            try:
                return bool(is_available())
            except Exception:
                return False
        return False

    def _client_stats(self, llm_client):
        stats = deepcopy(getattr(llm_client, "stats", {}) or {})
        if not isinstance(stats, dict):
            return {}

        provider = self._client_provider(llm_client)
        if provider and not stats.get("provider"):
            stats["provider"] = provider
        return stats

    def _clean_message(self, message):
        cleaned = str(message or "").strip()
        cleaned = re.sub(r"^user selected:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^user typed:\s*", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    def _is_affirmative_reply(self, lowered_message):
        return lowered_message in {
            "yes",
            "y",
            "yes please",
            "yep",
            "yeah",
            "correct",
            "confirmed",
            "that's right",
            "thats right",
            "right",
            "sure",
        }

    def _extract_budget_phrase_from_question(self, question):
        question = str(question or "").strip()
        if not question:
            return ""

        patterns = [
            r"budget[^?.!]*?\bis\s+([^?.!]+)",
            r"budget[^?.!]*?\bof\s+([^?.!]+)",
            r"budget[^?.!]*?\bat\s+([^?.!]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, question, flags=re.IGNORECASE)
            if not match:
                continue
            candidate = match.group(1).strip(" .?!,:;")
            if parse_money_value(candidate) is not None:
                return candidate
        return ""

    def _reply_mentions_additional_signals(self, message, field):
        lowered = str(message or "").strip().lower()
        if not lowered:
            return False

        signal_keywords = {
            "preferred_category": {"laptop", "laptops", "desktop", "desktops", "server", "network", "router", "switch"},
            "category_or_workload": {"laptop", "laptops", "desktop", "desktops", "server", "network", "router", "switch"},
            "workload_or_application_profile": {"developer", "design", "office", "browser", "vm", "virtualization", "render", "photoshop", "excel"},
            "budget": {"budget", "each", "per ", "total", "overall", "lakh", "k"},
            "budget_scope": {"each", "per ", "total", "overall", "project"},
            "growth_expectation": {"growth", "grow", "growing", "steady", "expand", "expansion", "hiring", "rapid", "moderate"},
            "performance_priority": {"performance", "balanced", "cheap", "lowest cost", "budget sensitive", "powerful"},
            "support_expectation": {"support", "onsite", "warranty", "premium", "business"},
            "availability_need": {"available now", "in stock", "urgent", "asap", "immediately", "soon"},
            "team_size": {"people", "staff", "users", "seats", "team", "employees"},
            "purchase_scope_or_quantity": {"people", "staff", "users", "seats", "team", "employees"},
        }

        for candidate_field, keywords in signal_keywords.items():
            if candidate_field == field:
                continue
            if any(keyword in lowered for keyword in keywords):
                return True
        return False

    def _should_try_llm_reply_fallback(self, message, field, next_question):
        llm_client = getattr(self.followup_service, "llm_client", None)
        if not llm_client or not hasattr(llm_client, "invoke_json"):
            return False
        if hasattr(llm_client, "is_available") and not llm_client.is_available():
            return False
        if field not in self.LLM_REPLY_FALLBACK_FIELDS:
            return False
        if not str(next_question or "").strip():
            return False
        if self._reply_mentions_additional_signals(message, field):
            return False
        word_count = len(str(message or "").split())
        return bool(word_count and word_count <= 12 and len(str(message or "")) <= 120)

    def _field_resolved_by_rewrite(self, field, original_prefs, rewritten_message):
        self._sync_runtime_services()
        candidate = self.extraction_service.extract(rewritten_message, context=dict(original_prefs or {}))
        payload = self.extraction_service.build_procurement_payload(candidate, {"channel": self._payload_channel()})
        requirements = self.recommendation_service.intake_service.normalize(payload)
        readiness = self.clarification_service.assess(requirements)
        missing = set((readiness or {}).get("missing_signals") or [])

        capability_tags = set(requirements.get("capability_tags") or [])
        application_signals = requirements.get("application_signals") or []

        if field == "preferred_category":
            return bool(requirements.get("preferred_categories")) and field not in missing
        if field == "category_or_workload":
            return "category_or_workload" not in missing
        if field == "workload_or_application_profile":
            return "workload_or_application_profile" not in missing
        if field == "team_size":
            return bool(requirements.get("team_size") or requirements.get("quantity")) and field not in missing
        if field == "budget":
            return requirements.get("budget") is not None and field not in missing
        if field == "budget_scope":
            return bool(requirements.get("budget_scope")) and field not in missing
        if field == "purchase_scope_or_quantity":
            return bool(requirements.get("purchase_scope") or requirements.get("quantity")) and field not in missing
        if field == "application_profile":
            return bool(
                application_signals
                or requirements.get("requested_ram_gb")
                or requirements.get("requested_storage_gb")
                or capability_tags.intersection({"gpu_needed", "high_ram", "storage_heavy", "virtualization", "local_compute"})
            ) and field not in missing
        if field == "growth_expectation":
            return bool(requirements.get("growth_expectation")) and field not in missing
        if field == "performance_priority":
            return bool(requirements.get("performance_priority")) and field not in missing
        return field not in missing

    def _llm_coerce_followup_reply(self, message, prefs, field, next_question):
        if not self._should_try_llm_reply_fallback(message, field, next_question):
            return message

        llm_client = self.followup_service.llm_client
        response = llm_client.invoke_json(
            "followup_reply_rewrite.txt",
            {
                "known_context": str(dict(prefs or {})),
                "missing_field": str(field or ""),
                "question_text": str(next_question or ""),
                "user_reply": str(message or ""),
            },
        )
        rewrite = str((response or {}).get("rewrite") or "").strip()
        if not rewrite:
            return message
        if rewrite.lower() == str(message).lower():
            return message
        if len(rewrite) > 240:
            return message
        if not self._field_resolved_by_rewrite(field, prefs, rewrite):
            return message
        return rewrite

    def _coerce_followup_reply(self, message, prefs):
        message = str(message or "").strip()
        if not message or not prefs or not prefs.get("raw_chat"):
            return message

        next_question, _, readiness = self._next_question_context(prefs)
        field = str((readiness or {}).get("highest_priority_missing_field") or "").strip()
        lowered = message.lower()
        question_text = str(next_question or "").lower()

        if (
            field in {"budget", "budget_scope"}
            and self._is_affirmative_reply(lowered)
            and "confirm" in question_text
            and "budget" in question_text
        ):
            budget_phrase = self._extract_budget_phrase_from_question(next_question)
            if budget_phrase:
                if any(token in question_text for token in {"total", "overall", "project"}):
                    return f"My overall budget is {budget_phrase}."
                if any(token in question_text for token in {"each", "per unit", "per device", "per seat"}):
                    return f"My budget is {budget_phrase} each."
                return f"My budget is {budget_phrase}."

        if field == "budget":
            parsed_budget = parse_money_value(message)
            if parsed_budget is not None and "budget" not in lowered:
                if any(token in question_text for token in {"total", "overall", "project"}):
                    return f"My overall budget is {message}."
                if any(token in question_text for token in {"each", "per unit", "per device", "per seat"}):
                    return f"My budget is {message} each."
                return f"My budget is {message}."

        if field == "budget_scope":
            if lowered in {"total", "overall", "overall budget", "total budget", "project", "project total"}:
                return "Treat the budget as the total project budget."
            if lowered in {"each", "per unit", "per device", "per seat", "unit budget"}:
                return "Treat the budget as per device."

        return self._llm_coerce_followup_reply(message, prefs, field, next_question)

    def _format_price(self, price, currency):
        if price is None:
            return "Price unavailable"
        return f"{currency or 'INR'} {int(price):,}"

    def _session_key(self, session_id):
        return str(getattr(session_id, "channel_name", session_id))


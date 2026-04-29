#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################



# class ResponseContractAdapter:
#     HIDDEN_REQUIREMENT_FIELDS = {
#         "field_state",
#         "field_source",
#         "assumption_severity",
#         "review_state",
#         "_provenance",
#     }
#     HIDDEN_META_FIELDS = {
#         "catalog_validation_summary",
#         "catalog_validation_rejections_sample",
#         "catalog_observability",
#         "filtered_categories",
#         "semantic_candidate_ids",
#         "semantic_candidate_count",
#         "retrieval_summary",
#         "compatibility_summary",
#         "compatibility_rejections_sample",
#         "policy_summary",
#         "policy_rejections_sample",
#         "applied_rules_count",
#         "ranking_deferred",
#         "ranking_deferred_reason",
#         "expert_review_reason",
#         "decision_policy_profile",
#         "decision_trace",
#         "review_state",
#     }
#     HIDDEN_RECOMMENDATION_FIELDS = {
#         "explanation",
#         "workload_fit",
#         "upgrade_implications",
#         "assumptions",
#         "next_steps",
#         "retrieval",
#         "rejected_products",
#         "retrieval_summary",
#         "semantic_candidate_ids",
#         "semantic_candidate_count",
#         "catalog_validation_rejections_sample",
#         "rejected_templates",
#         "template_candidates",
#         "target_profile",
#     }

#     def build_question_payload(
#         self,
#         response,
#         next_question="",
#         requirements=None,
#         readiness=None,
#         extracted_schema=None,
#         ui_guidance=None,
#         meta=None,
#         llm_stats=None,
#         response_mode="ask_question",
#     ):
#         payload_meta = dict(meta or {})
#         payload_meta["response_mode"] = str(response_mode or "ask_question").strip() or "ask_question"
#         payload = {
#             "response": str(response or next_question or "").strip(),
#             "response_type": "question",
#             "next_question": str(next_question or "").strip(),
#             "requirements": dict(requirements or {}),
#             "readiness": dict(readiness or {}),
#             "extracted_schema": dict(extracted_schema or {}),
#             "ui_guidance": list(ui_guidance or []),
#             "meta": payload_meta,
#             "llm_stats": dict(llm_stats or {}),
#         }
#         return payload

#     def build_recommendation_payload(
#         self,
#         response,
#         decision_trace_id="",
#         requirements=None,
#         recommendations=None,
#         target_profile=None,
#         assumptions=None,
#         comparison="",
#         readiness=None,
#         ui_guidance=None,
#         recommendation_context=None,
#         refinement_prompt="",
#         review_state=None,
#         check_requirement_summary=None,
#         editable_inferred_values=None,
#         template_candidates=None,
#         recommendation_groups=None,
#         meta=None,
#         llm_stats=None,
#         summary="",
#     ):
#         payload_meta = self._sanitize_recommendation_meta(meta)
#         payload_meta.setdefault("response_mode", "recommend")
#         return {
#             "response": str(response or "").strip(),
#             "response_type": "recommendation",
#             "decision_trace_id": str(decision_trace_id or "").strip(),
#             "requirements": self._sanitize_requirements(requirements),
#             "recommendations": self._sanitize_recommendations(recommendations),
#             "recommendation_groups": self._sanitize_recommendation_groups(recommendation_groups),
#             "target_profile": dict(target_profile or {}),
#             "summary": str(summary or "").strip(),
#             "assumptions": list(assumptions or []),
#             "comparison": str(comparison or "").strip(),
#             "readiness": dict(readiness or {}),
#             "ui_guidance": list(ui_guidance or []),
#             "recommendation_context": dict(recommendation_context or {}),
#             "refinement_prompt": str(refinement_prompt or "").strip(),
#             "review_state": dict(review_state or {}),
#             "check_requirement_summary": dict(check_requirement_summary or {}),
#             "editable_inferred_values": dict(editable_inferred_values or {}),
#             "template_candidates": list(template_candidates or []),
#             "meta": payload_meta,
#             "llm_stats": dict(llm_stats or {}),
#         }

#     def build_recommendation_update_payload(
#         self,
#         decision_trace_id="",
#         recommendation_updates=None,
#         meta=None,
#         llm_stats=None,
#         event_type="background_explanations_ready",
#     ):
#         payload_meta = dict(meta or {})
#         payload_meta.setdefault("response_mode", "recommendation_update")
#         return {
#             "event_type": str(event_type or "background_explanations_ready").strip(),
#             "response_type": "recommendation_update",
#             "decision_trace_id": str(decision_trace_id or "").strip(),
#             "recommendation_updates": list(recommendation_updates or []),
#             "meta": payload_meta,
#             "llm_stats": dict(llm_stats or {}),
#         }

#     def build_error_payload(self, response, meta=None, llm_stats=None):
#         payload_meta = dict(meta or {})
#         payload_meta.setdefault("response_mode", "error")
#         return {
#             "response": str(response or "An unexpected error occurred.").strip(),
#             "response_type": "error",
#             "meta": payload_meta,
#             "llm_stats": dict(llm_stats or {}),
#         }

#     def _sanitize_requirements(self, requirements):
#         cleaned = dict(requirements or {})
#         for field in self.HIDDEN_REQUIREMENT_FIELDS:
#             cleaned.pop(field, None)
#         return cleaned

#     def _sanitize_recommendations(self, recommendations):
#         cleaned_items = []
#         for recommendation in list(recommendations or []):
#             item = dict(recommendation or {})
#             for field in self.HIDDEN_RECOMMENDATION_FIELDS:
#                 item.pop(field, None)
#             cleaned_items.append(item)
#         return cleaned_items

#     def _sanitize_recommendation_groups(self, recommendation_groups):
#         cleaned_groups = []
#         for group in list(recommendation_groups or []):
#             item = dict(group or {})
#             item["requirements"] = self._sanitize_requirements(item.get("requirements"))
#             item["recommendations"] = self._sanitize_recommendations(item.get("recommendations"))
#             cleaned_groups.append(item)
#         return cleaned_groups

#     def _sanitize_recommendation_meta(self, meta):
#         payload_meta = dict(meta or {})
#         for field in self.HIDDEN_META_FIELDS:
#             payload_meta.pop(field, None)
#         return payload_meta





class ResponseContractAdapter:
    HIDDEN_REQUIREMENT_FIELDS = {
        "field_state",
        "field_source",
        "assumption_severity",
        "review_state",
        "_provenance",
    }
    HIDDEN_META_FIELDS = {
        "catalog_validation_summary",
        "catalog_validation_rejections_sample",
        "catalog_observability",
        "filtered_categories",
        "semantic_candidate_ids",
        "semantic_candidate_count",
        "retrieval_summary",
        "compatibility_summary",
        "compatibility_rejections_sample",
        "policy_summary",
        "policy_rejections_sample",
        "applied_rules_count",
        "ranking_deferred",
        "ranking_deferred_reason",
        "expert_review_reason",
        "decision_policy_profile",
        "decision_trace",
        "review_state",
    }
    HIDDEN_RECOMMENDATION_FIELDS = {
        "retrieval",
        "rejected_products",
        "retrieval_summary",
        "semantic_candidate_ids",
        "semantic_candidate_count",
        "catalog_validation_rejections_sample",
        "rejected_templates",
        "template_candidates",
        "target_profile",
    }

    def build_question_payload(
        self,
        response,
        next_question="",
        requirements=None,
        readiness=None,
        extracted_schema=None,
        ui_guidance=None,
        meta=None,
        llm_stats=None,
        response_mode="ask_question",
        ui_state="clarification_required",
        blocking_reason_code="",
    ):
        payload_meta = dict(meta or {})
        payload_meta["response_mode"] = str(response_mode or "ask_question").strip() or "ask_question"
        payload = {
            "response": str(response or next_question or "").strip(),
            "response_type": "question",
            "ui_state": str(ui_state or "clarification_required").strip() or "clarification_required",
            "blocking_reason_code": str(blocking_reason_code or "").strip(),
            "next_question": str(next_question or "").strip(),
            "requirements": dict(requirements or {}),
            "readiness": dict(readiness or {}),
            "extracted_schema": dict(extracted_schema or {}),
            "ui_guidance": list(ui_guidance or []),
            "meta": payload_meta,
            "llm_stats": dict(llm_stats or {}),
        }
        return payload

    def build_recommendation_payload(
        self,
        response,
        decision_trace_id="",
        requirements=None,
        recommendations=None,
        target_profile=None,
        assumptions=None,
        comparison="",
        readiness=None,
        ui_guidance=None,
        recommendation_context=None,
        refinement_prompt="",
        review_state=None,
        check_requirement_summary=None,
        editable_inferred_values=None,
        template_candidates=None,
        recommendation_groups=None,
        meta=None,
        llm_stats=None,
        summary="",
        ui_state="recommendation_ready",
        blocking_reason_code="",
    ):
        payload_meta = self._sanitize_recommendation_meta(meta)
        payload_meta.setdefault("response_mode", "recommend")
        return {
            "response": str(response or "").strip(),
            "response_type": "recommendation",
            "ui_state": str(ui_state or "recommendation_ready").strip() or "recommendation_ready",
            "blocking_reason_code": str(blocking_reason_code or "").strip(),
            "decision_trace_id": str(decision_trace_id or "").strip(),
            "requirements": self._sanitize_requirements(requirements),
            "recommendations": self._sanitize_recommendations(recommendations),
            "recommendation_groups": self._sanitize_recommendation_groups(recommendation_groups),
            "target_profile": dict(target_profile or {}),
            "summary": str(summary or "").strip(),
            "assumptions": list(assumptions or []),
            "comparison": str(comparison or "").strip(),
            "readiness": dict(readiness or {}),
            "ui_guidance": list(ui_guidance or []),
            "recommendation_context": dict(recommendation_context or {}),
            "refinement_prompt": str(refinement_prompt or "").strip(),
            "review_state": dict(review_state or {}),
            "check_requirement_summary": dict(check_requirement_summary or {}),
            "editable_inferred_values": dict(editable_inferred_values or {}),
            "template_candidates": list(template_candidates or []),
            "meta": payload_meta,
            "llm_stats": dict(llm_stats or {}),
        }

    def build_recommendation_update_payload(
        self,
        decision_trace_id="",
        recommendation_updates=None,
        meta=None,
        llm_stats=None,
        event_type="background_explanations_ready",
        ui_state="recommendation_ready",
    ):
        payload_meta = dict(meta or {})
        payload_meta.setdefault("response_mode", "recommendation_update")
        return {
            "event_type": str(event_type or "background_explanations_ready").strip(),
            "response_type": "recommendation_update",
            "ui_state": str(ui_state or "recommendation_ready").strip() or "recommendation_ready",
            "decision_trace_id": str(decision_trace_id or "").strip(),
            "recommendation_updates": list(recommendation_updates or []),
            "meta": payload_meta,
            "llm_stats": dict(llm_stats or {}),
        }

    def build_error_payload(self, response, meta=None, llm_stats=None):
        payload_meta = dict(meta or {})
        payload_meta.setdefault("response_mode", "error")
        return {
            "response": str(response or "An unexpected error occurred.").strip(),
            "response_type": "error",
            "ui_state": "error",
            "meta": payload_meta,
            "llm_stats": dict(llm_stats or {}),
        }

    def _sanitize_requirements(self, requirements):
        cleaned = dict(requirements or {})
        for field in self.HIDDEN_REQUIREMENT_FIELDS:
            cleaned.pop(field, None)
        return cleaned

    def _sanitize_recommendations(self, recommendations):
        cleaned_items = []
        for recommendation in list(recommendations or []):
            item = dict(recommendation or {})
            for field in self.HIDDEN_RECOMMENDATION_FIELDS:
                item.pop(field, None)
            cleaned_items.append(item)
        return cleaned_items

    def _sanitize_recommendation_groups(self, recommendation_groups):
        cleaned_groups = []
        for group in list(recommendation_groups or []):
            item = dict(group or {})
            item["requirements"] = self._sanitize_requirements(item.get("requirements"))
            item["recommendations"] = self._sanitize_recommendations(item.get("recommendations"))
            cleaned_groups.append(item)
        return cleaned_groups

    def _sanitize_recommendation_meta(self, meta):
        payload_meta = dict(meta or {})
        for field in self.HIDDEN_META_FIELDS:
            payload_meta.pop(field, None)
        return payload_meta

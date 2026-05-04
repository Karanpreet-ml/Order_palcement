from .response_contract import ResponseContractAdapter


class PayloadBuilderService:
    def __init__(self, response_contract_adapter=None):
        self.response_contract_adapter = response_contract_adapter or ResponseContractAdapter()

    def build_payload(
        self,
        assistant_text,
        response_mode,
        finalized_state_projection,
        readiness_result,
        recommendation_facts=None,
        meta=None,
        llm_stats=None,
    ):
        assistant_text = str(assistant_text or "").strip()
        response_mode = str(response_mode or "general_reply").strip()
        finalized_state_projection = dict(finalized_state_projection or {})
        readiness_result = dict(readiness_result or {})
        recommendation_facts = dict(recommendation_facts or {})
        meta = dict(meta or {})
        llm_stats = dict(llm_stats or {})

        if response_mode == "recommendation":
            no_match = dict(recommendation_facts.get("no_match_or_clarification") or {})
            grouped = list(recommendation_facts.get("grouped_recommendations") or [])
            ui_state = "recommendation_ready"
            if grouped:
                ui_state = "grouped_recommendation_ready"
            elif str(no_match.get("status_code") or "").strip() == "no_match_found":
                ui_state = "no_match_found"
            return self.response_contract_adapter.build_recommendation_payload(
                response=assistant_text,
                decision_trace_id=recommendation_facts.get("decision_trace_id"),
                requirements=finalized_state_projection,
                recommendations=recommendation_facts.get("shortlisted_recommendations"),
                target_profile=recommendation_facts.get("target_profile"),
                assumptions=recommendation_facts.get("assumptions"),
                comparison="",
                readiness=readiness_result,
                ui_guidance=[],
                recommendation_context=recommendation_facts.get("recommendation_context"),
                refinement_prompt="",
                review_state=recommendation_facts.get("review_state"),
                check_requirement_summary=recommendation_facts.get("check_requirement_summary"),
                editable_inferred_values=recommendation_facts.get("editable_inferred_values"),
                template_candidates=recommendation_facts.get("template_candidates"),
                recommendation_groups=self._payload_recommendation_groups(
                    recommendation_facts.get("grouped_recommendations")
                ),
                meta=meta,
                llm_stats=llm_stats,
                summary=assistant_text,
                ui_state=ui_state,
                blocking_reason_code=str(no_match.get("reason_code") or "").strip(),
            )

        next_question = assistant_text if response_mode == "clarification" else ""
        mapped_mode = {
            "clarification": "ask_question",
            "general_reply": "respond",
            "recommendation_recall": "respond",
            "out_of_scope": "respond",
        }.get(response_mode, "respond")
        return self.response_contract_adapter.build_question_payload(
            response=assistant_text,
            next_question=next_question,
            requirements=finalized_state_projection,
            readiness=readiness_result,
            extracted_schema=finalized_state_projection,
            ui_guidance=[],
            meta=meta,
            llm_stats=llm_stats,
            response_mode=mapped_mode,
            ui_state="clarification_required" if response_mode == "clarification" else "responded",
            blocking_reason_code="",
        )

    def _payload_recommendation_groups(self, grouped_recommendations):
        groups = []
        for group in list(grouped_recommendations or []):
            groups.append(
                {
                    "group_id": str(group.get("group_id") or "").strip(),
                    "label": str(group.get("label") or "").strip(),
                    "category": str(group.get("category") or "").strip(),
                    "requirements": dict(group.get("requirements") or {}),
                    "recommendations": list(group.get("recommendations") or []),
                    "template_candidates": list(group.get("template_candidates") or []),
                    "decision_trace_id": str(group.get("decision_trace_id") or "").strip(),
                    "budget_fit_facts": dict(group.get("budget_fit_facts") or {}),
                    "no_match_or_clarification": dict(group.get("no_match_or_clarification") or {}),
                }
            )
        return groups

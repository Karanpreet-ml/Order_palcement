from .config_service import ProcurementConfigService


class ProcurementTemplateService:
    MATCH_QUALITY_ORDER = {
        "exact": 0,
        "closest_match": 1,
        "coverage_gap": 2,
    }

    def __init__(self, config_service=None):
        self.config_service = config_service or ProcurementConfigService()

    def get_template_by_id(self, template_id):
        template_id = str(template_id or "").strip().lower()
        if not template_id:
            return {}
        config = self.config_service.get_template_config()
        for template in config.get("templates") or []:
            if str(template.get("id") or "").strip().lower() == template_id:
                return dict(template)
            if str(template.get("template_id") or "").strip().lower() == template_id:
                return dict(template)
        return {}

    def select_candidates(self, requirements, target_profile=None, multi_intent_result=None, limit=3):
        requirements = dict(requirements or {})
        target_profile = dict(target_profile or {})
        multi_intent_result = dict(multi_intent_result or {})
        config = self.config_service.get_template_config()
        selection_policy = dict(config.get("selection_safety_policy") or {})
        minimum_exact_score = float(selection_policy.get("minimum_exact_score") or 0.55)
        minimum_closest_match_score = float(selection_policy.get("minimum_closest_match_score") or 0.30)
        context = self._build_selection_context(requirements, target_profile, multi_intent_result)
        if self._lacks_scenario_signal(context):
            return []

        evaluated = []
        for template in config.get("templates") or []:
            if not template.get("active_flag", False):
                continue
            candidate = self._evaluate_template(
                template=template,
                context=context,
                minimum_exact_score=minimum_exact_score,
                minimum_closest_match_score=minimum_closest_match_score,
            )
            if candidate:
                evaluated.append(candidate)

        safe_candidates = [candidate for candidate in evaluated if candidate.get("selection_allowed")]
        safe_candidates.sort(key=self._candidate_sort_key)
        selected = safe_candidates[: max(int(limit or 0), 0)]
        if not selected and evaluated:
            selected = [self._best_coverage_gap_candidate(evaluated)]

        selection_debug = self._build_selection_debug(
            evaluated=evaluated,
            safe_candidates=safe_candidates,
            selected=selected,
        )
        marked = []
        for index, candidate in enumerate(selected):
            candidate_copy = dict(candidate)
            candidate_copy["selected"] = index == 0
            candidate_copy["selection_rejection_reason"] = (
                list(candidate_copy.get("coverage_gap_reasons") or [])[:1] or [""]
            )[0]
            if index == 0:
                candidate_copy["template_selection_debug"] = selection_debug
            marked.append(candidate_copy)
        return marked

    def _build_selection_context(self, requirements, target_profile, multi_intent_result):
        requirements = dict(requirements or {})
        target_profile = dict(target_profile or {})
        multi_intent_result = dict(multi_intent_result or {})

        preferred_categories = self._dedupe_strings(
            list(requirements.get("preferred_categories") or [])
            + ([requirements.get("preferred_category")] if requirements.get("preferred_category") else [])
        )
        preferred_categories = [
            category
            for category in preferred_categories
            if str(category or "").strip().lower() != "not_sure"
        ]
        combined_categories = self._dedupe_strings(
            preferred_categories + list(target_profile.get("categories") or [])
        )
        workloads = self._dedupe_strings(requirements.get("workloads") or [])
        application_signals = self._dedupe_strings(requirements.get("application_signals") or [])
        capability_tags = self._dedupe_strings(requirements.get("capability_tags") or [])
        notes = " ".join(
            part
            for part in (
                requirements.get("raw_chat"),
                requirements.get("notes"),
                requirements.get("timeline"),
            )
            if str(part or "").strip()
        ).strip()
        lowered_notes = notes.lower()

        existing_infrastructure = {
            str(item or "").strip().lower()
            for item in (requirements.get("existing_infrastructure") or [])
            if str(item or "").strip()
        }
        dependency_state = "none"
        if existing_infrastructure:
            dependency_state = "known"
        elif any(
            token in lowered_notes
            for token in {
                "existing environment",
                "existing setup",
                "existing infrastructure",
                "current environment",
                "current setup",
                "current platform",
                "must work with our current",
                "integrate with current",
            }
        ):
            dependency_state = "unknown"

        mobile_work_requested = "mobile_workforce" in {
            signal.lower() for signal in application_signals
        } or any(
            token in lowered_notes
            for token in {
                "field sales",
                "sales rep",
                "sales reps",
                "customer site",
                "client site",
                "on the road",
                "field visits",
                "traveling to clients",
            }
        )
        remote_hybrid_requested = "remote_collaboration" in {
            signal.lower() for signal in application_signals
        } or any(
            token in lowered_notes
            for token in {
                "remote team",
                "hybrid team",
                "work from home",
                "home office",
                "distributed team",
                "remote workforce",
            }
        )
        site_scope_requested = (
            str(requirements.get("purchase_scope") or "").strip().lower() == "site_deployment"
            or any(
                token in lowered_notes
                for token in {
                    "branch office",
                    "branch",
                    "site rollout",
                    "new site",
                    "store opening",
                    "site deployment",
                    "remote office",
                }
            )
            or "branch_connectivity" in {tag.lower() for tag in capability_tags}
            or bool(set(workloads).intersection({"retail_operations", "network_connectivity"}))
        )

        return {
            "explicit_categories": preferred_categories,
            "categories": combined_categories,
            "workloads": workloads,
            "application_signals": application_signals,
            "capability_tags": capability_tags,
            "industry": str(requirements.get("industry") or "").strip().lower(),
            "business_type": str(requirements.get("business_type") or "").strip().lower(),
            "team_size": int(requirements.get("team_size") or 0),
            "quantity": int(requirements.get("quantity") or 0),
            "purchase_scope": str(requirements.get("purchase_scope") or "").strip().lower(),
            "rollout_type": str(requirements.get("rollout_type") or "").strip().lower(),
            "replacement_mode": str(requirements.get("replacement_mode") or "").strip().lower(),
            "availability_need": str(requirements.get("availability_need") or "").strip().lower(),
            "support_expectation": str(requirements.get("support_expectation") or "").strip().lower(),
            "existing_infrastructure": existing_infrastructure,
            "dependency_state": dependency_state,
            "notes": lowered_notes,
            "is_multi_intent": bool(multi_intent_result.get("is_multi_intent")),
            "site_scope_requested": bool(site_scope_requested),
            "remote_hybrid_requested": bool(remote_hybrid_requested),
            "mobile_work_requested": bool(mobile_work_requested),
            "requirements": requirements,
        }

    def _lacks_scenario_signal(self, context):
        context = dict(context or {})
        return not any(
            (
                context.get("categories"),
                context.get("workloads"),
                context.get("application_signals"),
                context.get("capability_tags"),
                context.get("is_multi_intent"),
                context.get("site_scope_requested"),
                context.get("remote_hybrid_requested"),
                context.get("mobile_work_requested"),
            )
        )

    def _evaluate_template(self, template, context, minimum_exact_score, minimum_closest_match_score):
        template = dict(template or {})
        context = dict(context or {})

        hard_gate_failures = self._evaluate_hard_gates(template, context)
        contradictions = []
        if not hard_gate_failures:
            contradictions = self._evaluate_contradictions(template, context)
        matched_signals, match_reasons, score, applied_modifier = self._score_template(template, context)
        soft_fit_gaps = []
        if not hard_gate_failures and not contradictions:
            soft_fit_gaps = self._evaluate_soft_fit_gaps(template, context, score, minimum_exact_score)

        gap_items = hard_gate_failures + contradictions + soft_fit_gaps
        gap_type = gap_items[0]["gap_type"] if gap_items else ""
        coverage_gap_reasons = [item["reason"] for item in gap_items]
        selection_allowed = False
        template_match_quality = "coverage_gap"
        if not hard_gate_failures and not contradictions:
            if score >= minimum_exact_score and not soft_fit_gaps:
                selection_allowed = True
                template_match_quality = "exact"
            elif score >= minimum_closest_match_score:
                selection_allowed = True
                template_match_quality = "closest_match"
            else:
                coverage_gap_reasons.append(
                    "Template signal strength stayed below the closest-match threshold."
                )
                gap_type = gap_type or "insufficient_signal"

        if not selection_allowed and not coverage_gap_reasons:
            coverage_gap_reasons = ["Template fit remained below the minimum safe threshold."]
            gap_type = gap_type or "insufficient_signal"

        if template_match_quality == "closest_match" and not coverage_gap_reasons:
            coverage_gap_reasons = ["Template fit remained below the exact-match threshold."]
            gap_type = "insufficient_signal"

        return {
            "id": template.get("id"),
            "name": template.get("name"),
            "template_id": template.get("template_id"),
            "template_version": str(template.get("version") or ""),
            "scenario_family": template.get("scenario_family"),
            "variant": template.get("variant"),
            "score": round(score, 4),
            "match_score": round(score, 4),
            "template_match_quality": template_match_quality,
            "selection_allowed": selection_allowed,
            "supported_categories": list(template.get("supported_categories") or []),
            "required_roles": list(template.get("required_roles") or []),
            "required_fields": list(template.get("required_fields") or []),
            "quantity_strategy": template.get("quantity_strategy"),
            "budget_strategy": template.get("budget_strategy"),
            "compatibility_profile": template.get("compatibility_profile"),
            "scoring_profile": template.get("scoring_profile"),
            "default_question_overrides": list(template.get("default_question_overrides") or []),
            "urgency_profile": template.get("urgency_profile"),
            "in_stock_only_supported": bool(template.get("in_stock_only_supported")),
            "site_scope_profile": template.get("site_scope_profile"),
            "rollout_type": template.get("rollout_type"),
            "replacement_mode": template.get("replacement_mode"),
            "support_preference": template.get("support_preference"),
            "existing_infra_dependency": template.get("existing_infra_dependency"),
            "acceptable_downgrade_path": template.get("acceptable_downgrade_path"),
            "matched_template_signals": matched_signals,
            "match_reasons": match_reasons,
            "coverage_gap_reasons": coverage_gap_reasons,
            "gap_type": gap_type,
            "applied_industry_modifier": applied_modifier,
            "hard_gate_failures": [item["code"] for item in hard_gate_failures],
            "contradiction_codes": [item["code"] for item in contradictions],
            "soft_fit_gaps": [item["code"] for item in soft_fit_gaps],
        }

    def _evaluate_hard_gates(self, template, context):
        template = dict(template or {})
        context = dict(context or {})
        conditions = dict(template.get("eligibility_conditions") or {})
        failures = []
        workloads = set(context.get("workloads") or [])
        application_signals = {signal.lower() for signal in (context.get("application_signals") or [])}
        business_type = str(context.get("business_type") or "").strip().lower()
        availability_need = str(context.get("availability_need") or "").strip().lower()

        if conditions.get("requires_multi_intent") and not context.get("is_multi_intent"):
            failures.append(
                {
                    "code": "missing_multi_intent_shape",
                    "gap_type": "unsupported_scenario",
                    "reason": "This template only applies to grouped multi-intent requests.",
                }
            )
        elif context.get("is_multi_intent") and not conditions.get("requires_multi_intent"):
            failures.append(
                {
                    "code": "single_intent_template_on_multi_intent_request",
                    "gap_type": "unsupported_scenario",
                    "reason": "Single-intent templates do not safely cover the grouped request shape.",
                }
            )

        allowed_business_types = {
            str(value or "").strip().lower()
            for value in (conditions.get("business_types") or [])
            if str(value or "").strip()
        }
        if allowed_business_types and business_type and business_type not in allowed_business_types:
            failures.append(
                {
                    "code": "business_type_not_supported",
                    "gap_type": "unsupported_scenario",
                    "reason": f"Business type '{business_type}' is outside this template's supported scenario.",
                }
            )

        any_workloads = {
            str(value or "").strip().lower()
            for value in (conditions.get("any_workloads") or [])
            if str(value or "").strip()
        }
        all_workloads = {
            str(value or "").strip().lower()
            for value in (conditions.get("all_workloads") or [])
            if str(value or "").strip()
        }
        if all_workloads and not all_workloads.issubset(workloads):
            failures.append(
                {
                    "code": "required_workloads_missing",
                    "gap_type": "unsupported_scenario",
                    "reason": "The request does not contain the required workload signals for this template.",
                }
            )
        if any_workloads and not any_workloads.intersection(workloads):
            failures.append(
                {
                    "code": "workload_family_not_supported",
                    "gap_type": "unsupported_scenario",
                    "reason": "The request workload does not align with this template's scenario family.",
                }
            )

        required_application_signals = {
            str(value or "").strip().lower()
            for value in (conditions.get("any_application_signals") or [])
            if str(value or "").strip()
        }
        if required_application_signals and not required_application_signals.intersection(application_signals):
            failures.append(
                {
                    "code": "required_application_signal_missing",
                    "gap_type": "unsupported_scenario",
                    "reason": "This template requires a more explicit scenario signal before it can be selected safely.",
                }
            )

        if bool(template.get("in_stock_only_supported")) and availability_need not in {"urgent", "in_stock_now"}:
            failures.append(
                {
                    "code": "urgent_in_stock_signal_missing",
                    "gap_type": "unsupported_urgency",
                    "reason": "This template is reserved for explicit urgent or in-stock-now requests.",
                }
            )

        template_rollout_type = str(template.get("rollout_type") or "").strip().lower()
        if template_rollout_type == "phased" and str(context.get("rollout_type") or "").strip().lower() != "phased":
            failures.append(
                {
                    "code": "phased_rollout_signal_missing",
                    "gap_type": "unsupported_rollout_type",
                    "reason": "This template is only safe for explicit phased-rollout requests.",
                }
            )

        template_replacement_mode = str(template.get("replacement_mode") or "").strip().lower()
        if template_replacement_mode == "refresh" and str(context.get("replacement_mode") or "").strip().lower() != "refresh":
            failures.append(
                {
                    "code": "replacement_refresh_signal_missing",
                    "gap_type": "unsupported_replacement_mode",
                    "reason": "This template is reserved for explicit replacement or refresh requests.",
                }
            )

        site_scope_profile = str(template.get("site_scope_profile") or "").strip().lower()
        if site_scope_profile == "distributed_end_user" and not context.get("remote_hybrid_requested"):
            failures.append(
                {
                    "code": "remote_hybrid_signal_missing",
                    "gap_type": "unsupported_scenario",
                    "reason": "This template requires an explicit remote or hybrid workforce signal.",
                }
            )
        if site_scope_profile == "mobile_workforce" and not context.get("mobile_work_requested"):
            failures.append(
                {
                    "code": "mobile_work_signal_missing",
                    "gap_type": "unsupported_scenario",
                    "reason": "This template requires explicit mobile-work context such as field visits or customer-site usage.",
                }
            )

        return failures

    def _evaluate_contradictions(self, template, context):
        template = dict(template or {})
        context = dict(context or {})
        conditions = dict(template.get("eligibility_conditions") or {})
        contradictions = []
        explicit_categories = {
            str(value or "").strip().lower()
            for value in (context.get("explicit_categories") or [])
            if str(value or "").strip()
        }
        template_categories = {
            str(value or "").strip().lower()
            for value in (template.get("supported_categories") or [])
            if str(value or "").strip()
        }
        availability_need = str(context.get("availability_need") or "").strip().lower()
        purchase_scope = str(context.get("purchase_scope") or "").strip().lower()
        rollout_type = str(context.get("rollout_type") or "").strip().lower()
        replacement_mode = str(context.get("replacement_mode") or "").strip().lower()
        supported_infrastructure = {
            str(value or "").strip().lower()
            for value in (conditions.get("supported_infrastructure") or [])
            if str(value or "").strip()
        }

        if explicit_categories:
            if len(explicit_categories) > 1 and not explicit_categories.issubset(template_categories):
                contradictions.append(
                    {
                        "code": "unsupported_category_mix",
                        "gap_type": "unsupported_category_mix",
                        "reason": "The explicit category mix is broader than this template can support safely.",
                    }
                )
            elif template_categories and not explicit_categories.intersection(template_categories):
                contradictions.append(
                    {
                        "code": "category_contradiction",
                        "gap_type": "unsupported_scenario",
                        "reason": "The explicit category request contradicts this template's category scope.",
                    }
                )

        if availability_need == "in_stock_now" and not template.get("in_stock_only_supported"):
            contradictions.append(
                {
                    "code": "in_stock_requirement_not_supported",
                    "gap_type": "unsupported_urgency",
                    "reason": "The request explicitly requires in-stock-now availability that this template does not support.",
                }
            )
        if availability_need == "urgent" and str(template.get("urgency_profile") or "").strip().lower() not in {
            "urgent_supported",
            "flexible",
        }:
            contradictions.append(
                {
                    "code": "urgent_requirement_not_supported",
                    "gap_type": "unsupported_urgency",
                    "reason": "The request is explicitly urgent, but this template does not support that urgency level safely.",
                }
            )

        template_rollout_type = str(template.get("rollout_type") or "").strip().lower()
        if rollout_type == "phased" and template_rollout_type not in {"phased", "mixed"}:
            contradictions.append(
                {
                    "code": "rollout_type_contradiction",
                    "gap_type": "unsupported_rollout_type",
                    "reason": "The request explicitly requires a phased rollout that this template does not support.",
                }
            )
        if rollout_type == "standard" and template_rollout_type == "phased":
            contradictions.append(
                {
                    "code": "non_phased_request_on_phased_template",
                    "gap_type": "unsupported_rollout_type",
                    "reason": "This template is specifically for phased rollouts, but the request is not.",
                }
            )

        if purchase_scope == "site_deployment" and str(template.get("site_scope_profile") or "").strip().lower() in {
            "end_user",
            "distributed_end_user",
            "mobile_workforce",
        }:
            contradictions.append(
                {
                    "code": "site_scope_contradiction",
                    "gap_type": "unsupported_scenario",
                    "reason": "The request is site-oriented, but this template is meant for end-user device scenarios.",
                }
            )

        template_replacement_mode = str(template.get("replacement_mode") or "").strip().lower()
        if replacement_mode == "refresh" and template_replacement_mode == "net_new":
            contradictions.append(
                {
                    "code": "replacement_mode_contradiction",
                    "gap_type": "unsupported_replacement_mode",
                    "reason": "The request is a refresh, but this template is designed for net-new purchases.",
                }
            )
        if replacement_mode == "net_new" and template_replacement_mode == "refresh":
            contradictions.append(
                {
                    "code": "net_new_request_on_refresh_template",
                    "gap_type": "unsupported_replacement_mode",
                    "reason": "The request is net-new, but this template is reserved for refresh scenarios.",
                }
            )

        if supported_infrastructure and context.get("dependency_state") == "known":
            known_infrastructure = set(context.get("existing_infrastructure") or set())
            supported_matches = supported_infrastructure.intersection(known_infrastructure)
            unsupported_matches = known_infrastructure.difference(supported_infrastructure)
            if not supported_matches:
                contradictions.append(
                    {
                        "code": "explicit_infrastructure_dependency_not_supported",
                        "gap_type": "unsupported_infra_dependency",
                        "reason": "The explicit infrastructure dependency does not align with this template's supported environment.",
                    }
                )
            elif unsupported_matches and any(
                token in str(context.get("notes") or "")
                for token in {"only environment", "-only environment", "must stay compatible"}
            ):
                contradictions.append(
                    {
                        "code": "explicit_infrastructure_dependency_not_supported",
                        "gap_type": "unsupported_infra_dependency",
                        "reason": "The request calls out an explicit incompatible environment dependency that this template cannot claim safely.",
                    }
                )

        return contradictions

    def _evaluate_soft_fit_gaps(self, template, context, score, minimum_exact_score):
        template = dict(template or {})
        context = dict(context or {})
        conditions = dict(template.get("eligibility_conditions") or {})
        soft_gaps = []
        supported_infrastructure = {
            str(value or "").strip().lower()
            for value in (conditions.get("supported_infrastructure") or [])
            if str(value or "").strip()
        }

        if (
            str(template.get("existing_infra_dependency") or "").strip().lower() != "none_or_flexible"
            and context.get("dependency_state") == "unknown"
        ):
            soft_gaps.append(
                {
                    "code": "existing_infrastructure_dependency_unconfirmed",
                    "gap_type": "insufficient_signal",
                    "reason": "Existing infrastructure was mentioned, but compatibility detail is still unresolved.",
                }
            )
        elif supported_infrastructure and context.get("dependency_state") == "known":
            matched = supported_infrastructure.intersection(context.get("existing_infrastructure") or set())
            if matched:
                return soft_gaps

        if score < minimum_exact_score:
            soft_gaps.append(
                {
                    "code": "score_below_exact_threshold",
                    "gap_type": "insufficient_signal",
                    "reason": "Template signal strength stayed below the exact-match threshold.",
                }
            )
        return soft_gaps

    def _score_template(self, template, context):
        template = dict(template or {})
        context = dict(context or {})
        conditions = dict(template.get("eligibility_conditions") or {})
        template_categories = {
            str(value or "").strip().lower()
            for value in (template.get("supported_categories") or [])
            if str(value or "").strip()
        }
        categories = {
            str(value or "").strip().lower()
            for value in (context.get("categories") or [])
            if str(value or "").strip()
        }
        workloads = {
            str(value or "").strip().lower()
            for value in (context.get("workloads") or [])
            if str(value or "").strip()
        }
        application_signals = {
            str(value or "").strip().lower()
            for value in (context.get("application_signals") or [])
            if str(value or "").strip()
        }
        capability_tags = {
            str(value or "").strip().lower()
            for value in (context.get("capability_tags") or [])
            if str(value or "").strip()
        }

        reasons = []
        matched_signals = {
            "categories": [],
            "workloads": [],
            "application_signals": [],
            "capability_tags": [],
            "industry_modifier": "",
            "business_type": "",
            "purchase_scope": "",
            "urgency": "",
            "replacement_mode": "",
            "supported_infrastructure": [],
        }
        score = 0.0

        if conditions.get("requires_multi_intent") and context.get("is_multi_intent"):
            matched_signals["request_shape"] = "multi_intent"
            reasons.append("Matches the grouped multi-intent request shape.")
            score += 0.7

        matched_categories = sorted(template_categories.intersection(categories))
        if matched_categories:
            matched_signals["categories"] = matched_categories
            reasons.append("Aligned with category scope: {}.".format(", ".join(matched_categories)))
            score += 0.25

        any_workloads = {
            str(value or "").strip().lower()
            for value in (conditions.get("any_workloads") or [])
            if str(value or "").strip()
        }
        matched_workloads = sorted(any_workloads.intersection(workloads))
        if matched_workloads:
            matched_signals["workloads"] = matched_workloads
            reasons.append(
                "Matched workload signals: {}.".format(
                    ", ".join(workload.replace("_", " ") for workload in matched_workloads)
                )
            )
            score += 0.30

        any_application_signals = {
            str(value or "").strip().lower()
            for value in (conditions.get("any_application_signals") or [])
            if str(value or "").strip()
        }
        matched_application_signals = sorted(any_application_signals.intersection(application_signals))
        if matched_application_signals:
            matched_signals["application_signals"] = matched_application_signals
            reasons.append(
                "Matched scenario signals: {}.".format(", ".join(matched_application_signals))
            )
            score += 0.12

        any_capability_tags = {
            str(value or "").strip().lower()
            for value in (conditions.get("any_capability_tags") or [])
            if str(value or "").strip()
        }
        matched_tags = sorted(any_capability_tags.intersection(capability_tags))
        if matched_tags:
            matched_signals["capability_tags"] = matched_tags
            reasons.append("Matched capability hints: {}.".format(", ".join(matched_tags)))
            score += 0.10

        business_types = {
            str(value or "").strip().lower()
            for value in (conditions.get("business_types") or [])
            if str(value or "").strip()
        }
        business_type = str(context.get("business_type") or "").strip().lower()
        if business_types and business_type and business_type in business_types:
            matched_signals["business_type"] = business_type
            reasons.append(f"Matched business type signal: {business_type}.")
            score += 0.12

        allowed_purchase_scopes = {
            str(value or "").strip().lower()
            for value in (conditions.get("purchase_scopes") or [])
            if str(value or "").strip()
        }
        purchase_scope = str(context.get("purchase_scope") or "").strip().lower()
        if allowed_purchase_scopes and purchase_scope in allowed_purchase_scopes:
            matched_signals["purchase_scope"] = purchase_scope
            reasons.append(f"Purchase scope aligns with {purchase_scope}.")
            score += 0.06

        min_team_size = int(conditions.get("min_team_size") or 0)
        if min_team_size and int(context.get("team_size") or 0) >= min_team_size:
            reasons.append(
                f"Team size is large enough for this scenario baseline ({context.get('team_size')})."
            )
            score += 0.05

        required_fields = list(template.get("required_fields") or [])
        if required_fields:
            satisfied = [
                field
                for field in required_fields
                if self._value_present(context.get("requirements", {}).get(field))
            ]
            if satisfied:
                score += 0.10 * (len(satisfied) / len(required_fields))
                reasons.append(
                    "Required template fields already present: {}.".format(", ".join(satisfied))
                )

        availability_need = str(context.get("availability_need") or "").strip().lower()
        urgency_profile = str(template.get("urgency_profile") or "").strip().lower()
        if availability_need and urgency_profile in {"standard", "flexible"} and availability_need in {"standard", "soon"}:
            matched_signals["urgency"] = availability_need
            score += 0.04
        elif availability_need in {"urgent", "in_stock_now"} and urgency_profile == "urgent_supported":
            matched_signals["urgency"] = availability_need
            reasons.append(f"Urgency profile supports the explicit {availability_need} request.")
            score += 0.10
        elif availability_need == "urgent" and urgency_profile == "flexible":
            matched_signals["urgency"] = availability_need
            score += 0.05

        if context.get("site_scope_requested") and str(template.get("site_scope_profile") or "").strip().lower() == "site_deployment":
            reasons.append("Matched site-oriented deployment scope.")
            score += 0.08
        if context.get("remote_hybrid_requested") and str(template.get("site_scope_profile") or "").strip().lower() == "distributed_end_user":
            reasons.append("Matched remote or hybrid workforce context.")
            score += 0.10
        if context.get("mobile_work_requested") and str(template.get("site_scope_profile") or "").strip().lower() == "mobile_workforce":
            reasons.append("Matched explicit mobile-workforce context.")
            score += 0.12

        replacement_mode = str(context.get("replacement_mode") or "").strip().lower()
        template_replacement_mode = str(template.get("replacement_mode") or "").strip().lower()
        if replacement_mode and template_replacement_mode in {replacement_mode, "either"}:
            matched_signals["replacement_mode"] = replacement_mode
            reasons.append(f"Replacement mode aligns with {replacement_mode}.")
            score += 0.08

        support_expectation = str(context.get("support_expectation") or "").strip().lower()
        support_preference = str(template.get("support_preference") or "").strip().lower()
        if support_expectation and self._support_alignment(support_expectation, support_preference):
            reasons.append(f"Support preference softly aligns with {support_expectation}.")
            score += 0.02

        applied_modifier = None
        industry = str(context.get("industry") or "").strip().lower()
        if industry:
            modifier = dict((template.get("industry_modifiers") or {}).get(industry) or {})
            if modifier:
                applied_modifier = {"industry": industry, **modifier}
                matched_signals["industry_modifier"] = industry
                reasons.append(f"Industry modifier applied for {industry}.")
                score += 0.08

        supported_infrastructure = {
            str(value or "").strip().lower()
            for value in (conditions.get("supported_infrastructure") or [])
            if str(value or "").strip()
        }
        known_infrastructure = supported_infrastructure.intersection(context.get("existing_infrastructure") or set())
        if known_infrastructure:
            matched_signals["supported_infrastructure"] = sorted(known_infrastructure)
            reasons.append(
                "Matched explicit infrastructure dependency: {}.".format(", ".join(sorted(known_infrastructure)))
            )
            score += 0.05

        return matched_signals, reasons, score, applied_modifier

    def _support_alignment(self, support_expectation, support_preference):
        support_expectation = str(support_expectation or "").strip().lower()
        support_preference = str(support_preference or "").strip().lower()
        if not support_expectation or not support_preference or support_preference == "neutral":
            return False
        if support_expectation == support_preference:
            return True
        if support_preference == "business" and support_expectation == "premium":
            return True
        return False

    def _best_coverage_gap_candidate(self, evaluated):
        evaluated = list(evaluated or [])
        evaluated.sort(
            key=lambda item: (
                -float(item.get("match_score") or 0.0),
                len(item.get("hard_gate_failures") or []),
                len(item.get("contradiction_codes") or []),
                str(item.get("template_id") or ""),
            )
        )
        candidate = dict(evaluated[0]) if evaluated else {}
        candidate["selected"] = True
        return candidate

    def _build_selection_debug(self, evaluated, safe_candidates, selected):
        evaluated = list(evaluated or [])
        safe_candidates = list(safe_candidates or [])
        selected = list(selected or [])
        selected_ids = {
            (str(item.get("template_id") or ""), str(item.get("template_version") or ""))
            for item in selected
        }
        rejected_templates = [
            self._selection_debug_entry(item)
            for item in sorted(evaluated, key=self._candidate_sort_key)
            if not item.get("selection_allowed")
            and (str(item.get("template_id") or ""), str(item.get("template_version") or "")) not in selected_ids
        ]
        runner_up_templates = [
            self._selection_debug_entry(item, include_reason=False)
            for item in safe_candidates[1:3]
        ]
        return {
            "evaluated_template_count": len(evaluated),
            "eligible_template_count": len(safe_candidates),
            "rejected_template_count": len(rejected_templates),
            "runner_up_templates": runner_up_templates,
            "rejected_templates": rejected_templates[:5],
        }

    def _selection_debug_entry(self, candidate, include_reason=True):
        candidate = dict(candidate or {})
        entry = {
            "template_id": candidate.get("template_id"),
            "template_match_quality": candidate.get("template_match_quality"),
            "match_score": candidate.get("match_score"),
            "gap_type": candidate.get("gap_type") or "",
            "hard_gate_failures": list(candidate.get("hard_gate_failures") or []),
            "contradiction_codes": list(candidate.get("contradiction_codes") or []),
            "soft_fit_gaps": list(candidate.get("soft_fit_gaps") or []),
        }
        if include_reason:
            reasons = list(candidate.get("coverage_gap_reasons") or [])
            entry["selection_rejection_reason"] = reasons[0] if reasons else ""
            entry["coverage_gap_reasons"] = reasons
        return entry

    def _candidate_sort_key(self, item):
        return (
            self.MATCH_QUALITY_ORDER.get(item.get("template_match_quality"), 99),
            -float(item.get("match_score") or 0.0),
            str(item.get("template_id") or ""),
        )

    def _dedupe_strings(self, values):
        deduped = []
        seen = set()
        for value in list(values or []):
            normalized = str(value or "").strip()
            if not normalized:
                continue
            lowered = normalized.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            deduped.append(normalized)
        return deduped

    def _value_present(self, value):
        return value not in (None, "", [], {})

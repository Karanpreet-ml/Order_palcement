from copy import deepcopy
from pathlib import Path

from ai_configurator.catalog.services.embedding_service import EmbeddingService
from ai_configurator.catalog.services.semantic_retriever import SemanticProductRetriever
from ai_configurator.procurement.services.recommendation_service import ProcurementRecommendationService
from test_support.catalog_dataset import build_catalog_repository, resolve_catalog_size


def build_release_gate_service(catalog_size="small"):
    resolved_catalog_size = resolve_catalog_size(catalog_size or "small")
    service = ProcurementRecommendationService(
        catalog_repository=build_catalog_repository(resolved_catalog_size),
        semantic_retriever=SemanticProductRetriever(embedding_service=EmbeddingService(model_name="")),
    )
    service._catalog_size = resolved_catalog_size
    for llm_client in [
        service.extraction_service.llm_client,
        service.followup_service.llm_client,
        service.explanation_service.llm_client,
    ]:
        llm_client.api_key = ""
        llm_client.gemini_api_key = ""
    return service


def resolve_release_gate_output_dir(repo_root, configured_output_dir=""):
    configured_output_dir = str(configured_output_dir or "").strip()
    if configured_output_dir:
        return Path(configured_output_dir).expanduser()
    return Path(repo_root) / "docs"


def run_release_gate_scenario(service, scenario):
    scenario = dict(scenario or {})
    expectations = dict(scenario.get("expectations") or {})
    release_gate_tags = dict(scenario.get("release_gate_tags") or {})
    result = service.recommend(deepcopy(scenario.get("payload") or {}), persist=False)

    recommendations = list(result.get("recommendations") or [])
    recommendation_groups = list(result.get("recommendation_groups") or [])
    bundle_report = dict(result.get("bundle_compatibility_report") or {})
    bundle_options = list(result.get("bundle_options") or [])
    primary_bundle_option = dict(bundle_options[0] if bundle_options else {})
    bundle_conflict_codes = list(result.get("bundle_conflict_codes") or bundle_report.get("bundle_conflict_codes") or [])
    multi_intent_meta = dict(result.get("meta", {}).get("multi_intent") or {})
    readiness = dict(result.get("readiness") or {})
    top_names = [item.get("name") for item in recommendations if item.get("name")]
    grouped_top_names = [
        (group.get("recommendations") or [{}])[0].get("name")
        if (group.get("recommendations") or [])
        else None
        for group in recommendation_groups
    ]
    question_asked = bool(result.get("next_question")) or int(readiness.get("recommended_question_budget") or 0) > 0
    bundle_validated = multi_intent_meta.get("bundle_validated")
    if not isinstance(bundle_validated, bool):
        bundle_validated = bundle_report.get("passed") if isinstance(bundle_report.get("passed"), bool) else None
    bundle_validation_outcome = (
        multi_intent_meta.get("validation_outcome")
        or primary_bundle_option.get("status")
        or ("validated" if bundle_validated is True else "rejected" if bundle_validated is False else "")
    )
    constrained_alternatives_present = bool(recommendations or recommendation_groups or bundle_options)

    checks = {
        "ranking_deferred_match": result.get("meta", {}).get("ranking_deferred") == expectations.get("ranking_deferred"),
        "top_1_match": True,
        "top_3_match": True,
        "fallback_match": True,
        "expert_review_match": True,
        "question_budget_match": True,
        "recommendation_mode_match": True,
        "bundle_validation_match": True,
        "bundle_conflict_match": True,
        "bundle_option_status_match": True,
        "bundle_no_fit_match": True,
    }

    precision_records = []
    if "top_name" in expectations:
        expected_name = expectations["top_name"]
        actual_top_3 = top_names[:3]
        top_1_match = bool(actual_top_3) and actual_top_3[0] == expected_name
        top_3_match = expected_name in actual_top_3
        checks["top_1_match"] = top_1_match
        checks["top_3_match"] = top_3_match
        precision_records.append(
            {
                "scenario": scenario.get("name"),
                "scope": "single",
                "expected_name": expected_name,
                "actual_top_3": actual_top_3,
                "top_1_match": top_1_match,
                "top_3_match": top_3_match,
            }
        )

    if "group_top_names" in expectations:
        expected_group_names = list(expectations["group_top_names"] or [])
        for index, expected_name in enumerate(expected_group_names):
            group = recommendation_groups[index] if index < len(recommendation_groups) else {}
            group_top_3 = [
                item.get("name")
                for item in list(group.get("recommendations") or [])[:3]
                if item.get("name")
            ]
            top_1_match = bool(group_top_3) and group_top_3[0] == expected_name
            top_3_match = expected_name in group_top_3
            precision_records.append(
                {
                    "scenario": scenario.get("name"),
                    "scope": f"group_{index + 1}",
                    "expected_name": expected_name,
                    "actual_top_3": group_top_3,
                    "top_1_match": top_1_match,
                    "top_3_match": top_3_match,
                }
            )
        checks["top_1_match"] = all(item["top_1_match"] for item in precision_records if item["scenario"] == scenario.get("name"))
        checks["top_3_match"] = all(item["top_3_match"] for item in precision_records if item["scenario"] == scenario.get("name"))

    if "fallback_reason" in expectations:
        fallback_checks = [
            result.get("fallback_reason") == expectations["fallback_reason"],
        ]
        if "recommended_count" in expectations:
            fallback_checks.append(len(recommendations) == expectations["recommended_count"])
        if "expert_review_eligible" in expectations:
            fallback_checks.append(result.get("expert_review_eligible") == expectations["expert_review_eligible"])
        if "ranking_deferred" in expectations:
            fallback_checks.append(result.get("meta", {}).get("ranking_deferred") == expectations["ranking_deferred"])
        checks["fallback_match"] = all(fallback_checks)

    if "expert_review_eligible" in expectations and "fallback_reason" not in expectations:
        checks["expert_review_match"] = result.get("expert_review_eligible") == expectations["expert_review_eligible"]

    if "recommended_question_budget" in expectations:
        checks["question_budget_match"] = readiness.get("recommended_question_budget") == expectations["recommended_question_budget"]

    if "recommendation_mode" in expectations:
        checks["recommendation_mode_match"] = result.get("recommendation_mode") == expectations["recommendation_mode"]

    if "bundle_validated" in expectations:
        checks["bundle_validation_match"] = bundle_validated == expectations["bundle_validated"]

    if "bundle_conflict_codes" in expectations:
        expected_conflicts = set(expectations.get("bundle_conflict_codes") or [])
        checks["bundle_conflict_match"] = expected_conflicts.issubset(set(bundle_conflict_codes))

    if "bundle_option_status" in expectations:
        checks["bundle_option_status_match"] = primary_bundle_option.get("status") == expectations["bundle_option_status"]

    if release_gate_tags.get("bundle_no_fit") or expectations.get("bundle_validated") is False:
        checks["bundle_no_fit_match"] = (
            bundle_validated is False
            and bool(bundle_conflict_codes)
            and (constrained_alternatives_present or bool(result.get("expert_review_eligible")))
            and checks["bundle_conflict_match"]
            and (
                checks["expert_review_match"]
                if "expert_review_eligible" in expectations
                else True
            )
        )

    checks["all_passed"] = all(checks.values())

    bundle_quality_record = None
    if release_gate_tags.get("bundle_quality") or "bundle_validated" in expectations or bundle_report.get("scope") == "bundle":
        bundle_quality_record = {
            "scenario": scenario.get("name"),
            "expected_bundle_validated": expectations.get("bundle_validated"),
            "actual_bundle_validated": bundle_validated,
            "validation_outcome": bundle_validation_outcome,
            "bundle_scope": bundle_report.get("scope") or "",
            "bundle_option_status": primary_bundle_option.get("status") or "",
            "bundle_conflict_codes": bundle_conflict_codes,
            "blocked_count": bundle_report.get("blocked_count"),
            "constrained_alternatives_present": constrained_alternatives_present,
            "expert_review_eligible": bool(result.get("expert_review_eligible")),
        }

    return {
        "name": scenario.get("name"),
        "expectations": expectations,
        "release_gate_tags": release_gate_tags,
        "result": {
            "decision_trace_id": result.get("decision_trace_id"),
            "recommendation_mode": result.get("recommendation_mode"),
            "fallback_reason": result.get("fallback_reason"),
            "expert_review_eligible": result.get("expert_review_eligible"),
            "ranking_deferred": result.get("meta", {}).get("ranking_deferred"),
            "recommended_question_budget": readiness.get("recommended_question_budget"),
            "next_question": result.get("next_question"),
            "top_name": top_names[0] if top_names else None,
            "top_3_names": top_names[:3],
            "group_top_names": grouped_top_names,
            "question_asked": question_asked,
            "bundle_validated": bundle_validated,
            "bundle_validation_outcome": bundle_validation_outcome,
            "bundle_conflict_codes": bundle_conflict_codes,
            "bundle_option_status": primary_bundle_option.get("status"),
        },
        "precision_records": precision_records,
        "bundle_quality_record": bundle_quality_record,
        "checks": checks,
    }


def build_release_gate_metrics(scenario_runs, release_gate_config):
    metrics_cfg = dict((release_gate_config or {}).get("metrics") or {})
    precision_records = [
        record
        for run in list(scenario_runs or [])
        for record in list(run.get("precision_records") or [])
    ]
    fallback_runs = [
        run for run in list(scenario_runs or [])
        if "fallback_reason" in (run.get("expectations") or {})
    ]
    adequately_specified_runs = [
        run for run in list(scenario_runs or [])
        if (run.get("release_gate_tags") or {}).get("adequately_specified")
    ]
    bundle_runs = [
        run for run in list(scenario_runs or [])
        if run.get("bundle_quality_record") and run["bundle_quality_record"].get("expected_bundle_validated") is not None
    ]
    bundle_no_fit_runs = [
        run for run in bundle_runs
        if (run.get("release_gate_tags") or {}).get("bundle_no_fit")
        or run.get("bundle_quality_record", {}).get("expected_bundle_validated") is False
    ]

    metrics = {
        "top_1_precision": _build_rate_metric(
            metric_name="top_1_precision",
            metric_cfg=metrics_cfg.get("top_1_precision") or {},
            numerator=sum(1 for record in precision_records if record.get("top_1_match")),
            denominator=len(precision_records),
        ),
        "top_3_precision": _build_rate_metric(
            metric_name="top_3_precision",
            metric_cfg=metrics_cfg.get("top_3_precision") or {},
            numerator=sum(1 for record in precision_records if record.get("top_3_match")),
            denominator=len(precision_records),
        ),
        "fallback_correctness": _build_rate_metric(
            metric_name="fallback_correctness",
            metric_cfg=metrics_cfg.get("fallback_correctness") or {},
            numerator=sum(1 for run in fallback_runs if run.get("checks", {}).get("fallback_match")),
            denominator=len(fallback_runs),
        ),
        "question_rate_adequately_specified": _build_rate_metric(
            metric_name="question_rate_adequately_specified",
            metric_cfg=metrics_cfg.get("question_rate_adequately_specified") or {},
            numerator=sum(1 for run in adequately_specified_runs if run.get("result", {}).get("question_asked")),
            denominator=len(adequately_specified_runs),
        ),
        "bundle_validation_pass_correctness": _build_rate_metric(
            metric_name="bundle_validation_pass_correctness",
            metric_cfg=metrics_cfg.get("bundle_validation_pass_correctness") or {},
            numerator=sum(1 for run in bundle_runs if run.get("checks", {}).get("bundle_validation_match")),
            denominator=len(bundle_runs),
        ),
        "bundle_no_fit_resolution_correctness": _build_rate_metric(
            metric_name="bundle_no_fit_resolution_correctness",
            metric_cfg=metrics_cfg.get("bundle_no_fit_resolution_correctness") or {},
            numerator=sum(1 for run in bundle_no_fit_runs if run.get("checks", {}).get("bundle_no_fit_match")),
            denominator=len(bundle_no_fit_runs),
        ),
    }

    return {
        "scenario_count": len(list(scenario_runs or [])),
        "precision_case_count": len(precision_records),
        "fallback_case_count": len(fallback_runs),
        "adequately_specified_case_count": len(adequately_specified_runs),
        "bundle_case_count": len(bundle_runs),
        "bundle_no_fit_case_count": len(bundle_no_fit_runs),
        "metrics": metrics,
    }


def _build_rate_metric(metric_name, metric_cfg, numerator, denominator):
    value = round(numerator / denominator, 4) if denominator else None
    return {
        "metric_name": metric_name,
        "label": metric_cfg.get("label") or metric_name,
        "threshold_type": metric_cfg.get("threshold_type") or "agreed_threshold",
        "direction": metric_cfg.get("direction") or "higher_is_better",
        "notes": metric_cfg.get("notes") or "",
        "numerator": numerator,
        "denominator": denominator,
        "value": value,
        "value_percent": round(value * 100, 2) if value is not None else None,
        "status": _metric_status(metric_cfg, value),
    }


def _metric_status(metric_cfg, value):
    if value is None:
        return "no_data"
    threshold_type = metric_cfg.get("threshold_type") or "agreed_threshold"
    if threshold_type == "agreed_threshold":
        return "pending_agreed_threshold"

    minimum = metric_cfg.get("minimum")
    maximum = metric_cfg.get("maximum")
    if threshold_type == "minimum":
        return "meets_threshold" if minimum is not None and value >= minimum else "below_threshold"
    if threshold_type == "maximum":
        return "meets_threshold" if maximum is not None and value <= maximum else "above_threshold"
    if threshold_type == "range":
        if minimum is not None and maximum is not None and minimum <= value <= maximum:
            return "meets_threshold"
        return "outside_threshold"
    return "measured_only"

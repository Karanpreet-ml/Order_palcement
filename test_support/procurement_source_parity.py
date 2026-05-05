import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from test_support.procurement_benchmarks import SOURCE_PARITY_SCENARIOS
from test_support.procurement_release_gates import build_release_gate_service


NORMALIZED_REQUIREMENT_FIELDS = [
    "preferred_category",
    "preferred_categories",
    "industry",
    "business_type",
    "team_size",
    "workloads",
    "application_signals",
    "capability_tags",
    "budget",
    "budget_scope",
    "growth_expectation",
    "performance_priority",
    "quantity",
    "purchase_scope",
    "requested_ram_gb",
    "requested_storage_gb",
    "requested_ram_is_minimum",
    "requested_storage_is_minimum",
    "availability_need",
    "require_returnable",
]

TARGET_PROFILE_FIELDS = [
    "categories",
    "min_ram_gb",
    "min_storage_gb",
    "preferred_ram_gb",
    "preferred_storage_gb",
    "min_cpu_score",
    "required_network_roles",
    "required_vpn_user_capacity",
    "required_throughput_mbps",
    "recommended_quantity",
    "growth_expectation",
    "performance_priority",
    "required_virtualization_ready",
    "infrastructure_scales",
    "resolved_workloads",
]

GROUP_REQUIREMENT_FIELDS = [
    "preferred_category",
    "workloads",
    "application_signals",
    "budget",
    "budget_scope",
    "quantity",
    "purchase_scope",
    "growth_expectation",
    "performance_priority",
]


def build_source_parity_service(catalog_size):
    return build_release_gate_service(catalog_size=catalog_size)


def run_source_parity_scenarios(corrected_service=None, mongo_service=None, scenarios=None):
    corrected_service = corrected_service or build_source_parity_service("corrected_json")
    mongo_service = mongo_service or build_source_parity_service("mongo")
    scenarios = list(scenarios or SOURCE_PARITY_SCENARIOS)
    rows = []

    for scenario in scenarios:
        payload = deepcopy((scenario or {}).get("payload") or {})
        corrected_result, corrected_error = _safe_recommend(corrected_service, payload)
        mongo_result, mongo_error = _safe_recommend(mongo_service, payload)

        corrected_snapshot = _build_result_snapshot(
            source_name="corrected_json",
            result=corrected_result,
            error=corrected_error,
        )
        mongo_snapshot = _build_result_snapshot(
            source_name="mongo",
            result=mongo_result,
            error=mongo_error,
        )

        normalized_match, normalized_diffs = _compare_snapshots(
            corrected_snapshot["normalized_output"],
            mongo_snapshot["normalized_output"],
        )
        template_match, template_diffs = _compare_snapshots(
            corrected_snapshot["template_choice"],
            mongo_snapshot["template_choice"],
        )
        recommendation_match, recommendation_diffs = _compare_snapshots(
            corrected_snapshot["recommendations"],
            mongo_snapshot["recommendations"],
        )
        bundle_match, bundle_diffs = _compare_snapshots(
            corrected_snapshot["bundle_validation"],
            mongo_snapshot["bundle_validation"],
        )

        comparisons = {
            "normalized_output": {
                "match": normalized_match,
                "diff_count": len(normalized_diffs),
                "diffs": normalized_diffs,
            },
            "template_choice": {
                "match": template_match,
                "diff_count": len(template_diffs),
                "diffs": template_diffs,
            },
            "recommendations": {
                "match": recommendation_match,
                "diff_count": len(recommendation_diffs),
                "diffs": recommendation_diffs,
            },
            "bundle_validation": {
                "match": bundle_match,
                "diff_count": len(bundle_diffs),
                "diffs": bundle_diffs,
            },
        }

        rows.append(
            {
                "scenario_name": scenario.get("name"),
                "payload": payload,
                "corrected_json": corrected_snapshot,
                "mongo": mongo_snapshot,
                "comparisons": comparisons,
                "all_passed": all(item["match"] for item in comparisons.values()),
            }
        )

    return {
        "rows": rows,
        "summary": {
            "scenario_count": len(rows),
            "passed_count": sum(1 for row in rows if row.get("all_passed")),
            "failed_count": sum(1 for row in rows if not row.get("all_passed")),
            "normalized_output_match_count": sum(
                1 for row in rows if row.get("comparisons", {}).get("normalized_output", {}).get("match")
            ),
            "template_choice_match_count": sum(
                1 for row in rows if row.get("comparisons", {}).get("template_choice", {}).get("match")
            ),
            "recommendation_match_count": sum(
                1 for row in rows if row.get("comparisons", {}).get("recommendations", {}).get("match")
            ),
            "bundle_validation_match_count": sum(
                1 for row in rows if row.get("comparisons", {}).get("bundle_validation", {}).get("match")
            ),
        },
    }


def write_source_parity_reports(parity_result, output_dir):
    parity_result = dict(parity_result or {})
    rows = list(parity_result.get("rows") or [])
    summary = dict(parity_result.get("summary") or {})
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    json_path = output_dir / "procurement-source-parity.json"
    md_path = output_dir / "procurement-source-parity.md"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "rows": rows,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Procurement Source Parity",
        "",
        f"- Generated at: {payload['generated_at']}",
        f"- Scenario count: {summary.get('scenario_count', 0)}",
        f"- Passed: {summary.get('passed_count', 0)}",
        f"- Failed: {summary.get('failed_count', 0)}",
        "",
        "## Match Summary",
        "",
        "| Dimension | Matched | Total |",
        "|---|---|---|",
        f"| Normalized output | {summary.get('normalized_output_match_count', 0)} | {summary.get('scenario_count', 0)} |",
        f"| Template choice | {summary.get('template_choice_match_count', 0)} | {summary.get('scenario_count', 0)} |",
        f"| Recommendations | {summary.get('recommendation_match_count', 0)} | {summary.get('scenario_count', 0)} |",
        f"| Bundle validation | {summary.get('bundle_validation_match_count', 0)} | {summary.get('scenario_count', 0)} |",
        "",
        "## Scenario Results",
        "",
        "| Scenario | Normalized | Template | Recommendations | Bundle | Corrected Template | Mongo Template | Corrected Top | Mongo Top | Passed |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for row in rows:
        corrected_top = ", ".join(row.get("corrected_json", {}).get("recommendations", {}).get("top_names") or []) or "n/a"
        mongo_top = ", ".join(row.get("mongo", {}).get("recommendations", {}).get("top_names") or []) or "n/a"
        lines.append(
            f"| {row.get('scenario_name') or 'n/a'} | "
            f"{row.get('comparisons', {}).get('normalized_output', {}).get('match')} | "
            f"{row.get('comparisons', {}).get('template_choice', {}).get('match')} | "
            f"{row.get('comparisons', {}).get('recommendations', {}).get('match')} | "
            f"{row.get('comparisons', {}).get('bundle_validation', {}).get('match')} | "
            f"{row.get('corrected_json', {}).get('template_choice', {}).get('template_id') or 'n/a'} | "
            f"{row.get('mongo', {}).get('template_choice', {}).get('template_id') or 'n/a'} | "
            f"{corrected_top} | {mongo_top} | {row.get('all_passed')} |"
        )

    failed_rows = [row for row in rows if not row.get("all_passed")]
    if failed_rows:
        lines.extend(["", "## Mismatch Details", ""])
        for row in failed_rows:
            lines.append(f"### {row.get('scenario_name') or 'Unknown Scenario'}")
            for dimension_key, label in (
                ("normalized_output", "Normalized output"),
                ("template_choice", "Template choice"),
                ("recommendations", "Recommendations"),
                ("bundle_validation", "Bundle validation"),
            ):
                comparison = dict((row.get("comparisons") or {}).get(dimension_key) or {})
                if comparison.get("match"):
                    continue
                lines.append(f"- {label}: {comparison.get('diff_count', 0)} difference(s)")
                for diff in list(comparison.get("diffs") or [])[:12]:
                    lines.append(
                        f"  - `{diff.get('path')}`: corrected_json={json.dumps(diff.get('corrected_json'), ensure_ascii=False)}; "
                        f"mongo={json.dumps(diff.get('mongo'), ensure_ascii=False)}"
                    )
            lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def _safe_recommend(service, payload):
    try:
        return service.recommend(deepcopy(payload), persist=False), ""
    except Exception as exc:  # pragma: no cover - defensive path for live parity checks
        return {}, f"{type(exc).__name__}: {exc}"


def _build_result_snapshot(source_name, result=None, error=""):
    result = dict(result or {})
    recommendations = list(result.get("recommendations") or [])
    groups = list(result.get("recommendation_groups") or [])
    selected_template = dict((result.get("meta") or {}).get("selected_template") or {})
    bundle_option = dict(((result.get("bundle_options") or [{}])[0]) or {})
    requirements = _requirements_snapshot(result.get("requirements") or {})
    target_profile = _target_profile_snapshot(result.get("target_profile") or {})

    return {
        "source_name": source_name,
        "error": str(error or "").strip(),
        "normalized_output": {
            "requirements": requirements,
            "target_profile": target_profile,
            "group_requirements": [
                {
                    "label": str(group.get("label") or ""),
                    "category": str(group.get("category") or ""),
                    "requirements": _group_requirements_snapshot(group.get("requirements") or {}),
                }
                for group in groups
            ],
        },
        "template_choice": {
            "template_id": selected_template.get("template_id") or result.get("template_id") or "",
            "template_version": selected_template.get("template_version") or result.get("template_version") or "",
            "recommendation_mode": result.get("recommendation_mode") or "",
            "expert_review_reason": result.get("expert_review_reason") or "",
            "clarification_required_reasons": sorted(
                str(item or "").strip()
                for item in (result.get("clarification_required_reasons") or [])
                if str(item or "").strip()
            ),
            "group_templates": [
                {
                    "label": str(group.get("label") or ""),
                    "template_id": str(
                        ((group.get("meta") or {}).get("selected_template") or {}).get("template_id")
                        or group.get("template_id")
                        or ""
                    ),
                    "template_version": str(
                        ((group.get("meta") or {}).get("selected_template") or {}).get("template_version")
                        or group.get("template_version")
                        or ""
                    ),
                    "recommendation_mode": str(group.get("recommendation_mode") or ""),
                }
                for group in groups
            ],
        },
        "recommendations": {
            "recommended_count": len(recommendations),
            "group_count": len(groups),
            "top_names": [str(item.get("name") or "") for item in recommendations[:3] if str(item.get("name") or "")],
            "top_candidates": [
                {
                    "name": str(item.get("name") or ""),
                    "category": str(item.get("category") or ""),
                    "candidate_id": str(item.get("candidate_id") or ""),
                    "inventory_id": str(item.get("inventory_id") or ""),
                    "accessory_type": str(item.get("accessory_type") or ""),
                    "price": item.get("price"),
                    "currency": str(item.get("currency") or ""),
                }
                for item in recommendations[:3]
            ],
            "group_recommendations": [
                {
                    "label": str(group.get("label") or ""),
                    "category": str(group.get("category") or ""),
                    "top_candidates": [
                        {
                            "name": str(item.get("name") or ""),
                            "category": str(item.get("category") or ""),
                            "candidate_id": str(item.get("candidate_id") or ""),
                            "inventory_id": str(item.get("inventory_id") or ""),
                            "accessory_type": str(item.get("accessory_type") or ""),
                            "price": item.get("price"),
                            "currency": str(item.get("currency") or ""),
                        }
                        for item in list(group.get("recommendations") or [])[:3]
                    ],
                }
                for group in groups
            ],
        },
        "bundle_validation": {
            "bundle_validated": ((result.get("meta") or {}).get("multi_intent") or {}).get("bundle_validated"),
            "bundle_option_status": bundle_option.get("status"),
            "bundle_conflict_codes": sorted(
                str(item or "").strip()
                for item in (result.get("bundle_conflict_codes") or [])
                if str(item or "").strip()
            ),
            "bundle_report_passed": ((result.get("bundle_compatibility_report") or {}).get("passed")),
            "bundle_capacity_summary": _canonicalize(result.get("bundle_capacity_summary") or {}),
        },
    }


def _requirements_snapshot(requirements):
    requirements = dict(requirements or {})
    snapshot = {}
    for field in NORMALIZED_REQUIREMENT_FIELDS:
        snapshot[field] = _canonicalize(requirements.get(field))
    return snapshot


def _group_requirements_snapshot(requirements):
    requirements = dict(requirements or {})
    snapshot = {}
    for field in GROUP_REQUIREMENT_FIELDS:
        snapshot[field] = _canonicalize(requirements.get(field))
    return snapshot


def _target_profile_snapshot(target_profile):
    target_profile = dict(target_profile or {})
    snapshot = {}
    for field in TARGET_PROFILE_FIELDS:
        snapshot[field] = _canonicalize(target_profile.get(field))
    return snapshot


def _compare_snapshots(corrected_value, mongo_value):
    diffs = []
    _collect_diffs(corrected_value, mongo_value, path="$", diffs=diffs)
    return not diffs, diffs


def _collect_diffs(corrected_value, mongo_value, path, diffs):
    if isinstance(corrected_value, dict) and isinstance(mongo_value, dict):
        keys = sorted(set(corrected_value.keys()) | set(mongo_value.keys()))
        for key in keys:
            _collect_diffs(
                corrected_value.get(key),
                mongo_value.get(key),
                f"{path}.{key}",
                diffs,
            )
        return
    if isinstance(corrected_value, list) and isinstance(mongo_value, list):
        if len(corrected_value) != len(mongo_value):
            diffs.append(
                {
                    "path": path,
                    "corrected_json": corrected_value,
                    "mongo": mongo_value,
                }
            )
            return
        for index, (left_item, right_item) in enumerate(zip(corrected_value, mongo_value)):
            _collect_diffs(left_item, right_item, f"{path}[{index}]", diffs)
        return
    if corrected_value != mongo_value:
        diffs.append(
            {
                "path": path,
                "corrected_json": corrected_value,
                "mongo": mongo_value,
            }
        )


def _canonicalize(value):
    if isinstance(value, dict):
        return {
            key: _canonicalize(value[key])
            for key in sorted(value.keys())
        }
    if isinstance(value, list):
        canonical_items = [_canonicalize(item) for item in value]
        if all(not isinstance(item, (dict, list)) for item in canonical_items):
            return sorted(canonical_items, key=lambda item: str(item))
        return canonical_items
    return value

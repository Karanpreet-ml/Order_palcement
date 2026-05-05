import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from test_support.procurement_benchmarks import PHASE2_VALIDATION_SCENARIOS


def build_phase2_validation_service():
    from test_support.procurement_release_gates import build_release_gate_service

    return build_release_gate_service(catalog_size="corrected_json")


def run_phase2_validation_scenarios(service=None, scenarios=None):
    service = service or build_phase2_validation_service()
    scenarios = list(scenarios or PHASE2_VALIDATION_SCENARIOS)
    rows = []

    for scenario in scenarios:
        payload = deepcopy((scenario or {}).get("payload") or {})
        expectations = dict((scenario or {}).get("expectations") or {})
        result = service.recommend(payload, persist=False)
        recommendations = list(result.get("recommendations") or [])
        recommendation_groups = list(result.get("recommendation_groups") or [])
        selected_template = dict((result.get("meta") or {}).get("selected_template") or {})
        bundle_option = dict(((result.get("bundle_options") or [{}])[0]) or {})
        bundle_conflict_codes = list(result.get("bundle_conflict_codes") or [])
        top_recommendation = dict((recommendations[0] if recommendations else {}) or {})
        top_group_recommendations = [
            dict(((group.get("recommendations") or [{}])[0]) or {})
            for group in recommendation_groups
        ]
        group_categories = sorted(
            {
                str(group.get("category") or "").strip().lower()
                for group in recommendation_groups
                if str(group.get("category") or "").strip()
            }
        )
        actual = {
            "scenario_name": scenario.get("name"),
            "catalog_size": scenario.get("catalog_size") or "corrected_json",
            "selected_template": selected_template.get("template_id") or "",
            "recommendation_mode": result.get("recommendation_mode") or "",
            "ranking_deferred": bool((result.get("meta") or {}).get("ranking_deferred")),
            "recommended_count": len(recommendations),
            "top_name": top_recommendation.get("name"),
            "top_category": top_recommendation.get("category"),
            "top_accessory_type": top_recommendation.get("accessory_type"),
            "group_count": len(recommendation_groups),
            "group_categories": group_categories,
            "group_top_names": [item.get("name") for item in top_group_recommendations if item.get("name")],
            "group_accessory_types": sorted(
                {
                    str(item.get("accessory_type") or "").strip().lower()
                    for item in top_group_recommendations
                    if str(item.get("accessory_type") or "").strip()
                }
            ),
            "bundle_validated": ((result.get("meta") or {}).get("multi_intent") or {}).get("bundle_validated"),
            "bundle_option_status": bundle_option.get("status"),
            "bundle_conflict_codes": bundle_conflict_codes,
            "catalog_validation_rejected_count": int(
                ((result.get("meta") or {}).get("catalog_validation_summary") or {}).get("rejected_count") or 0
            ),
        }
        checks = {
            "ranking_deferred_match": (
                "ranking_deferred" not in expectations
                or actual["ranking_deferred"] == expectations["ranking_deferred"]
            ),
            "selected_template_match": (
                "selected_template_id" not in expectations
                or actual["selected_template"] == expectations["selected_template_id"]
            ),
            "recommendation_mode_match": (
                "recommendation_mode" not in expectations
                or actual["recommendation_mode"] == expectations["recommendation_mode"]
            ),
            "recommended_count_match": (
                "recommended_count" not in expectations
                or actual["recommended_count"] == expectations["recommended_count"]
            ),
            "recommended_count_min_match": (
                "recommended_count_min" not in expectations
                or actual["recommended_count"] >= int(expectations["recommended_count_min"])
            ),
            "top_category_match": (
                "top_category" not in expectations
                or actual["top_category"] == expectations["top_category"]
            ),
            "top_accessory_type_match": (
                "top_accessory_type" not in expectations
                or actual["top_accessory_type"] == expectations["top_accessory_type"]
            ),
            "group_count_match": (
                "group_count" not in expectations
                or actual["group_count"] == expectations["group_count"]
            ),
            "group_categories_match": (
                "group_categories" not in expectations
                or actual["group_categories"] == sorted(expectations["group_categories"])
            ),
            "bundle_validated_match": (
                "bundle_validated" not in expectations
                or actual["bundle_validated"] == expectations["bundle_validated"]
            ),
            "bundle_conflict_match": (
                "bundle_conflict_codes" not in expectations
                or set(expectations["bundle_conflict_codes"]).issubset(set(actual["bundle_conflict_codes"]))
            ),
            "bundle_option_status_match": (
                "bundle_option_status" not in expectations
                or actual["bundle_option_status"] == expectations["bundle_option_status"]
            ),
            "catalog_validation_rejected_min_match": (
                "catalog_validation_rejected_min" not in expectations
                or actual["catalog_validation_rejected_count"] >= int(expectations["catalog_validation_rejected_min"])
            ),
        }
        actual["all_passed"] = all(checks.values())
        actual["checks"] = checks
        rows.append(actual)

    return {
        "rows": rows,
        "summary": {
            "scenario_count": len(rows),
            "passed_count": sum(1 for row in rows if row.get("all_passed")),
            "failed_count": sum(1 for row in rows if not row.get("all_passed")),
            "selected_template_counts": _count_values(rows, "selected_template"),
            "recommendation_mode_counts": _count_values(rows, "recommendation_mode"),
            "bundle_validation_counts": _count_values(rows, "bundle_validated"),
        },
    }


def write_phase2_validation_reports(validation_result, output_dir):
    validation_result = dict(validation_result or {})
    rows = list(validation_result.get("rows") or [])
    summary = dict(validation_result.get("summary") or {})
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    json_path = output_dir / "procurement-phase2-validation.json"
    md_path = output_dir / "procurement-phase2-validation.md"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "rows": rows,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Procurement Phase 2 Validation",
        "",
        f"- Generated at: {payload['generated_at']}",
        f"- Scenario count: {summary.get('scenario_count', 0)}",
        f"- Passed: {summary.get('passed_count', 0)}",
        f"- Failed: {summary.get('failed_count', 0)}",
        "",
        "## Scenario Results",
        "",
        "| Scenario | Catalog | Template | Mode | Recommended Count | Top Category | Accessory Type | Group Categories | Bundle Validated | Bundle Status | Rejected Rows | Passed |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for row in rows:
        lines.append(
            f"| {row.get('scenario_name') or 'n/a'} | {row.get('catalog_size') or 'n/a'} | "
            f"{row.get('selected_template') or 'n/a'} | {row.get('recommendation_mode') or 'n/a'} | "
            f"{row.get('recommended_count', 0)} | {row.get('top_category') or 'n/a'} | "
            f"{row.get('top_accessory_type') or 'n/a'} | {', '.join(row.get('group_categories') or []) or 'n/a'} | "
            f"{row.get('bundle_validated')} | {row.get('bundle_option_status') or 'n/a'} | "
            f"{row.get('catalog_validation_rejected_count', 0)} | {row.get('all_passed')} |"
        )

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def _count_values(rows, key):
    counts = {}
    for row in rows:
        value = str((row or {}).get(key) or "").strip() or "n/a"
        counts[value] = counts.get(value, 0) + 1
    return counts

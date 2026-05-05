import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from test_support.procurement_benchmarks import BENCHMARK_SCENARIOS
from test_support.procurement_release_gates import build_release_gate_service


def build_template_coverage_service():
    return build_release_gate_service()


def run_template_coverage_scenarios(service, scenarios=None):
    service = service or build_template_coverage_service()
    scenarios = list(scenarios or BENCHMARK_SCENARIOS)
    rows = []

    for scenario in scenarios:
        payload = deepcopy((scenario or {}).get("payload") or {})
        result = service.recommend(payload, persist=False)
        requirements = dict(result.get("requirements") or {})
        selected_template = dict(result.get("meta", {}).get("selected_template") or {})
        target_profile = dict(result.get("target_profile") or {})
        selection_debug = dict(selected_template.get("template_selection_debug") or {})
        rejected_templates = list(selection_debug.get("rejected_templates") or [])
        rejected_gap_types = sorted(
            {
                str(item.get("gap_type") or "").strip()
                for item in rejected_templates
                if str(item.get("gap_type") or "").strip()
            }
        )
        row = {
            "scenario_name": scenario.get("name"),
            "scenario_brief": _scenario_brief(payload, requirements),
            "industry": requirements.get("industry") or "",
            "category_mix": list(
                requirements.get("preferred_categories")
                or target_profile.get("categories")
                or ([requirements.get("preferred_category")] if requirements.get("preferred_category") else [])
            ),
            "budget_type": requirements.get("budget_scope") or "",
            "quantity_type": requirements.get("purchase_scope") or "",
            "urgency": requirements.get("availability_need") or "",
            "clarification_hotspot": _clarification_hotspot(result),
            "selected_template": selected_template.get("template_id") or "",
            "match_score": selected_template.get("match_score"),
            "template_match_quality": selected_template.get("template_match_quality") or "",
            "gap_type": selected_template.get("gap_type") or "",
            "selection_rejection_reason": selected_template.get("selection_rejection_reason") or "",
            "rejected_gap_types": rejected_gap_types,
            "recommendation_mode": result.get("recommendation_mode") or "",
            "expert_review_trigger": bool(result.get("expert_review_eligible")),
        }
        rows.append(row)

    return {
        "rows": rows,
        "summary": {
            "scenario_count": len(rows),
            "template_match_quality_counts": _count_values(rows, "template_match_quality"),
            "gap_type_counts": _count_values(rows, "gap_type"),
        },
    }


def write_template_coverage_reports(coverage_result, output_dir):
    coverage_result = dict(coverage_result or {})
    rows = list(coverage_result.get("rows") or [])
    summary = dict(coverage_result.get("summary") or {})
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    json_path = output_dir / "template-coverage-matrix.json"
    md_path = output_dir / "template-coverage-matrix.md"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "rows": rows,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Template Coverage Matrix",
        "",
        f"- Generated at: {payload['generated_at']}",
        f"- Scenario count: {summary.get('scenario_count', 0)}",
        "",
        "## Coverage",
        "",
        "| Scenario | Industry | Category Mix | Budget Type | Quantity Type | Urgency | Clarification Hotspot | Selected Template | Match Score | Match Quality | Gap Type | Rejected Gap Types | Selection Rejection Reason | Recommendation Mode | Expert Review |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for row in rows:
        lines.append(
            f"| {row['scenario_name']} | {row['industry'] or 'n/a'} | "
            f"{', '.join(row['category_mix'] or []) or 'n/a'} | {row['budget_type'] or 'n/a'} | "
            f"{row['quantity_type'] or 'n/a'} | {row['urgency'] or 'n/a'} | "
            f"{row['clarification_hotspot'] or 'n/a'} | {row['selected_template'] or 'n/a'} | "
            f"{_format_score(row.get('match_score'))} | {row['template_match_quality'] or 'n/a'} | "
            f"{row['gap_type'] or 'n/a'} | {', '.join(row['rejected_gap_types'] or []) or 'n/a'} | "
            f"{row['selection_rejection_reason'] or 'n/a'} | {row['recommendation_mode'] or 'n/a'} | "
            f"{row['expert_review_trigger']} |"
        )

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def _count_values(rows, key):
    counts = {}
    for row in rows:
        value = str((row or {}).get(key) or "").strip() or "n/a"
        counts[value] = counts.get(value, 0) + 1
    return counts


def _clarification_hotspot(result):
    result = dict(result or {})
    reasons = list(result.get("clarification_required_reasons") or [])
    if reasons:
        return reasons[0]
    review_state = dict(result.get("review_state") or {})
    blocked = list(review_state.get("acceptance_blocked_reasons") or [])
    return blocked[0] if blocked else ""


def _scenario_brief(payload, requirements):
    payload = dict(payload or {})
    requirements = dict(requirements or {})
    chat_text = str(payload.get("chat_text") or "").strip()
    if chat_text:
        return chat_text
    categories = requirements.get("preferred_categories") or []
    workloads = requirements.get("workloads") or []
    return " | ".join(
        part
        for part in (
            ", ".join(categories) if categories else "",
            ", ".join(workloads) if workloads else "",
        )
        if part
    )


def _format_score(value):
    if value is None:
        return "n/a"
    return f"{float(value):.2f}".rstrip("0").rstrip(".")

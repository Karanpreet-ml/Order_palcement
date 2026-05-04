import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_project.settings")

import django

django.setup()

from ai_configurator.procurement.services.config_service import ProcurementConfigService
from test_support.procurement_benchmarks import BENCHMARK_SCENARIOS
from test_support.procurement_release_gates import (
    build_release_gate_metrics,
    build_release_gate_service,
    resolve_release_gate_output_dir,
    run_release_gate_scenario,
)


def write_reports(scenario_runs, summary, release_gate_config):
    output_dir = resolve_release_gate_output_dir(
        REPO_ROOT,
        os.getenv("PROCUREMENT_RELEASE_GATE_OUTPUT_DIR", ""),
    )
    try:
        output_dir.mkdir(exist_ok=True)
        json_path = output_dir / "procurement-release-gates.json"
        md_path = output_dir / "procurement-release-gates.md"
        write_target = output_dir
    except PermissionError:
        write_target = PROJECT_ROOT / "docs"
        write_target.mkdir(exist_ok=True)
        json_path = write_target / "procurement-release-gates.json"
        md_path = write_target / "procurement-release-gates.md"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_gate_version": release_gate_config.get("version"),
        "scenario_runs": scenario_runs,
        "summary": summary,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# Procurement Release Gates",
        "",
        f"- Generated at: {payload['generated_at']}",
        f"- Release-gate config version: {release_gate_config.get('version')}",
        f"- Scenario count: {summary['scenario_count']}",
        f"- Precision case count: {summary['precision_case_count']}",
        f"- Fallback case count: {summary['fallback_case_count']}",
        f"- Adequately specified case count: {summary['adequately_specified_case_count']}",
        f"- Bundle case count: {summary.get('bundle_case_count', 0)}",
        f"- Bundle no-fit case count: {summary.get('bundle_no_fit_case_count', 0)}",
        "",
        "## Metrics",
        "",
        "| Metric | Value | Cases | Target Type | Status | Notes |",
        "|---|---|---|---|---|---|",
    ]

    for metric in summary["metrics"].values():
        value = "n/a" if metric["value_percent"] is None else f"{metric['value_percent']}%"
        lines.append(
            f"| {metric['label']} | {value} | {metric['numerator']}/{metric['denominator']} | "
            f"{metric['threshold_type']} | {metric['status']} | {metric['notes']} |"
        )

    lines.extend(
        [
            "",
            "## Scenario Summary",
            "",
            "| Scenario | Mode | Top Recommendation | Fallback | Bundle Outcome | Question Asked | Overall Pass |",
            "|---|---|---|---|---|---|---|",
        ]
    )

    for run in scenario_runs:
        result = run["result"]
        lines.append(
            f"| {run['name']} | {result['recommendation_mode']} | {result['top_name'] or 'None'} | "
            f"{result['fallback_reason'] or 'n/a'} | {result.get('bundle_validation_outcome') or 'n/a'} | "
            f"{result['question_asked']} | {run['checks']['all_passed']} |"
        )

    bundle_quality_runs = [run for run in scenario_runs if run.get("bundle_quality_record")]
    if bundle_quality_runs:
        lines.extend(
            [
                "",
                "## Bundle Quality",
                "",
                "| Scenario | Expected Validated | Actual Validated | Option Status | Conflict Codes | Resolution | Quality Pass |",
                "|---|---|---|---|---|---|---|",
            ]
        )

        for run in bundle_quality_runs:
            record = run["bundle_quality_record"]
            resolution = []
            if record.get("constrained_alternatives_present"):
                resolution.append("constrained alternatives")
            if record.get("expert_review_eligible"):
                resolution.append("expert review")
            if not resolution:
                resolution.append("none")
            lines.append(
                f"| {run['name']} | {record.get('expected_bundle_validated')} | {record.get('actual_bundle_validated')} | "
                f"{record.get('bundle_option_status') or 'n/a'} | "
                f"{', '.join(record.get('bundle_conflict_codes') or []) or 'n/a'} | "
                f"{', '.join(resolution)} | "
                f"{run['checks'].get('bundle_validation_match') and run['checks'].get('bundle_no_fit_match')} |"
            )

    lines.extend(["", "## Detailed Notes", ""])

    for run in scenario_runs:
        result = run["result"]
        lines.extend(
            [
                f"### {run['name']}",
                "",
                f"- Recommendation mode: `{result['recommendation_mode']}`",
                f"- Ranking deferred: `{result['ranking_deferred']}`",
                f"- Top recommendation: `{result['top_name']}`",
                f"- Top 3 recommendations: `{result['top_3_names']}`",
                f"- Group top recommendations: `{result['group_top_names']}`",
                f"- Fallback reason: `{result['fallback_reason']}`",
                f"- Expert review eligible: `{result['expert_review_eligible']}`",
                f"- Recommended question budget: `{result['recommended_question_budget']}`",
                f"- Question asked: `{result['question_asked']}`",
                f"- Bundle validated: `{result.get('bundle_validated')}`",
                f"- Bundle validation outcome: `{result.get('bundle_validation_outcome')}`",
                f"- Bundle conflict codes: `{result.get('bundle_conflict_codes')}`",
                f"- Bundle option status: `{result.get('bundle_option_status')}`",
                f"- Checks: `{run['checks']}`",
                "",
            ]
        )

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def main():
    config_service = ProcurementConfigService()
    release_gate_config = config_service.get_release_gate_config()
    service = build_release_gate_service()
    scenario_runs = [run_release_gate_scenario(service, scenario) for scenario in BENCHMARK_SCENARIOS]
    summary = build_release_gate_metrics(scenario_runs, release_gate_config)
    json_path, md_path = write_reports(scenario_runs, summary, release_gate_config)

    print(f"Release-gate config version: {release_gate_config.get('version')}")
    print(f"Release-gate JSON: {json_path}")
    print(f"Release-gate Markdown: {md_path}")
    print("Metric summary:")
    for metric in summary["metrics"].values():
        value = "n/a" if metric["value_percent"] is None else f"{metric['value_percent']}%"
        print(
            f"- {metric['label']}: value={value}, cases={metric['numerator']}/{metric['denominator']}, "
            f"status={metric['status']}"
        )


if __name__ == "__main__":
    main()

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_project.settings")

import django

django.setup()

from test_support.procurement_release_gates import resolve_release_gate_output_dir
from test_support.procurement_template_coverage import (
    build_template_coverage_service,
    run_template_coverage_scenarios,
    write_template_coverage_reports,
)


def main():
    service = build_template_coverage_service()
    coverage_result = run_template_coverage_scenarios(service)
    output_dir = resolve_release_gate_output_dir(
        REPO_ROOT,
        os.getenv("PROCUREMENT_TEMPLATE_COVERAGE_OUTPUT_DIR", ""),
    )
    try:
        json_path, md_path = write_template_coverage_reports(coverage_result, output_dir)
    except PermissionError:
        fallback_output_dir = PROJECT_ROOT / "docs"
        fallback_output_dir.mkdir(exist_ok=True)
        json_path, md_path = write_template_coverage_reports(coverage_result, fallback_output_dir)

    print(f"Template coverage JSON: {json_path}")
    print(f"Template coverage Markdown: {md_path}")
    print("Match quality summary:")
    for key, value in dict(coverage_result.get("summary", {}).get("template_match_quality_counts") or {}).items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()

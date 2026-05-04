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
from test_support.procurement_runtime_observability import (
    fetch_runtime_observability_summary,
    write_runtime_observability_reports,
)


def main():
    limit = int(os.getenv("PROCUREMENT_RUNTIME_OBSERVABILITY_LIMIT", "50"))
    configured_output_dir = os.getenv("PROCUREMENT_RUNTIME_OBSERVABILITY_OUTPUT_DIR", "")
    output_dir = resolve_release_gate_output_dir(
        REPO_ROOT,
        configured_output_dir,
    )
    summary = fetch_runtime_observability_summary(limit=limit)
    try:
        json_path, md_path = write_runtime_observability_reports(summary, output_dir)
    except PermissionError:
        if configured_output_dir:
            raise
        output_dir = PROJECT_ROOT / "docs"
        json_path, md_path = write_runtime_observability_reports(summary, output_dir)

    print(f"Runtime summary endpoint: /api/procurement/observability/summary/?limit={limit}")
    print(f"Runtime observability JSON: {json_path}")
    print(f"Runtime observability Markdown: {md_path}")
    print(f"Sample size: {summary.get('sample_size', 0)}")
    for metric_name, metric in dict(summary.get("release_gate_metrics") or {}).items():
        value = metric.get("value_percent")
        if value is None:
            value = metric.get("value")
            value_text = "n/a" if value is None else str(value)
        else:
            value_text = f"{value}%"
        print(f"- {metric.get('label') or metric_name}: value={value_text}, status={metric.get('status')}")


if __name__ == "__main__":
    main()

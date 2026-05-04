import json
from datetime import datetime, timezone
from pathlib import Path


SUMMARY_ENDPOINT_PATH = "/api/procurement/observability/summary/"

RUNTIME_METRIC_ORDER = [
    "runtime_latency_p95_ms",
    "runtime_latency_p99_ms",
    "runtime_fallback_rate",
    "runtime_question_rate",
    "runtime_false_ready_rate",
    "runtime_budget_scope_ambiguity_rate",
]


def fetch_runtime_observability_summary(limit=50, client=None, endpoint_path=SUMMARY_ENDPOINT_PATH):
    if client is None:
        try:
            from rest_framework.test import APIClient
        except Exception:
            return _fetch_runtime_observability_summary_direct(limit=limit)
        client = APIClient()
    response = client.get(endpoint_path, {"limit": max(int(limit or 50), 1)})
    if response.status_code != 200:
        raise ValueError(
            f"Runtime observability summary request failed with status {response.status_code} for {endpoint_path}."
        )
    return response.json()


def _fetch_runtime_observability_summary_direct(limit=50):
    from ai_configurator.procurement.services.observability import ProcurementRuntimeObservabilityService

    service = ProcurementRuntimeObservabilityService()
    summary = service.summarize_recent_runs(limit=max(int(limit or 50), 1))
    summary = dict(summary or {})
    summary.setdefault("summary_source", "direct_service")
    return summary


def write_runtime_observability_reports(summary, output_dir, endpoint_path=SUMMARY_ENDPOINT_PATH):
    summary = dict(summary or {})
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    json_path = output_dir / "procurement-runtime-observability.json"
    md_path = output_dir / "procurement-runtime-observability.md"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary_endpoint": endpoint_path,
        "summary": summary,
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    latency = dict(summary.get("latency_ms") or {})
    counts = dict(summary.get("counts") or {})
    catalog_quality = dict(summary.get("catalog_quality") or {})
    metrics = dict(summary.get("release_gate_metrics") or {})
    targets = dict(summary.get("targets") or {})
    drift_alerts = list(summary.get("drift_alerts") or [])
    alert_summary = dict(summary.get("alert_summary") or {})

    lines = [
        "# Procurement Runtime Observability",
        "",
        f"- Generated at: {payload['generated_at']}",
        f"- Summary endpoint: `{endpoint_path}`",
        f"- Sample size: {summary.get('sample_size', 0)}",
        "",
        "## Latency",
        "",
        "| Measure | Value |",
        "|---|---|",
        f"| Average latency | {_format_plain_value(latency.get('average'), suffix=' ms')} |",
        f"| P50 latency | {_format_plain_value(latency.get('p50'), suffix=' ms')} |",
        f"| P95 latency | {_format_plain_value(latency.get('p95'), suffix=' ms')} |",
        f"| P99 latency | {_format_plain_value(latency.get('p99'), suffix=' ms')} |",
        "",
        "## Runtime Gates",
        "",
        "| Metric | Value | Target | Status | Notes |",
        "|---|---|---|---|---|",
    ]

    for metric_name in RUNTIME_METRIC_ORDER:
        metric = dict(metrics.get(metric_name) or {})
        target = dict(targets.get(metric_name) or {})
        lines.append(
            f"| {metric.get('label') or metric_name} | {_format_metric_value(metric_name, metric)} | "
            f"{_format_metric_target(metric_name, metric, target)} | {metric.get('status') or 'unknown'} | "
            f"{metric.get('notes') or ''} |"
        )

    lines.extend(
        [
            "",
            "## Runtime Counts",
            "",
            "| Counter | Value |",
            "|---|---|",
            f"| Fallback count | {counts.get('fallback_count', 0)} |",
            f"| Question count | {counts.get('question_count', 0)} |",
            f"| False-ready count | {counts.get('false_ready_count', 0)} |",
            f"| Budget-scope ambiguity count | {counts.get('budget_scope_ambiguity_count', 0)} |",
            f"| No-fit count | {counts.get('no_fit_count', 0)} |",
            f"| Stale inventory count | {counts.get('stale_inventory_count', 0)} |",
            f"| Source-load failure count | {counts.get('source_load_failure_count', 0)} |",
            f"| Unmatched inventory count | {counts.get('unmatched_inventory_count', 0)} |",
            f"| Parse warning count | {counts.get('parse_warning_count', 0)} |",
            f"| Currency fallback count | {counts.get('currency_fallback_count', 0)} |",
            f"| Provisional candidate count | {counts.get('provisional_count', 0)} |",
            f"| Store-filter miss count | {counts.get('store_filter_miss_count', 0)} |",
            f"| Validation block count | {counts.get('validation_block_count', 0)} |",
            "",
            "## Catalog Quality",
            "",
            "| Signal | Value |",
            "|---|---|",
            f"| Readiness state counts | {json.dumps(catalog_quality.get('readiness_state_counts') or {}, ensure_ascii=False)} |",
            f"| Avg parse warnings / run | {_format_plain_value(catalog_quality.get('average_parse_warning_count'))} |",
            f"| Avg provisional candidates / run | {_format_plain_value(catalog_quality.get('average_provisional_count'))} |",
            f"| Avg validation blocks / run | {_format_plain_value(catalog_quality.get('average_validation_block_count'))} |",
            f"| Avg unmatched inventory / run | {_format_plain_value(catalog_quality.get('average_unmatched_inventory_count'))} |",
            f"| Avg currency fallbacks / run | {_format_plain_value(catalog_quality.get('average_currency_fallback_count'))} |",
            "",
            "## Catalog Quality Rates",
            "",
            "| Signal | Value |",
            "|---|---|",
            f"| Source-load failure rate | {_format_plain_value((summary.get('rates') or {}).get('source_load_failure_rate'), suffix='%')} |",
            f"| Store-filter miss rate | {_format_plain_value((summary.get('rates') or {}).get('store_filter_miss_rate'), suffix='%')} |",
            "",
        ]
    )

    lines.extend(
        [
            "## Drift Alerts",
            "",
            f"- Triggered alerts: {alert_summary.get('triggered_count', 0)}",
            f"- Highest severity: {alert_summary.get('highest_severity') or 'none'}",
            "",
            "| Metric | Severity | Current | Previous | Status | Triggered | Notes |",
            "|---|---|---|---|---|---|---|",
        ]
    )

    for alert in drift_alerts:
        lines.append(
            f"| {alert.get('label') or alert.get('metric_name') or 'Unknown'} | {alert.get('severity') or 'medium'} | "
            f"{_format_alert_value(alert.get('metric_name'), alert.get('current_value'))} | "
            f"{_format_alert_value(alert.get('metric_name'), alert.get('previous_value'))} | "
            f"{alert.get('status') or 'unknown'} | {alert.get('alert_triggered')} | {alert.get('notes') or ''} |"
        )

    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def _format_metric_value(metric_name, metric):
    value_percent = metric.get("value_percent")
    if value_percent is not None:
        return _format_plain_value(value_percent, suffix="%")
    return _format_plain_value(metric.get("value"), suffix=" ms" if "latency" in metric_name else "")


def _format_metric_target(metric_name, metric, target):
    threshold_type = metric.get("threshold_type") or target.get("threshold_type") or "agreed_threshold"
    if threshold_type == "minimum":
        minimum = metric.get("minimum", target.get("minimum"))
        return f">= {_format_threshold_value(metric_name, minimum)}" if minimum is not None else "n/a"
    if threshold_type == "maximum":
        maximum = metric.get("maximum", target.get("maximum"))
        return f"<= {_format_threshold_value(metric_name, maximum)}" if maximum is not None else "n/a"
    if threshold_type == "range":
        minimum = metric.get("minimum", target.get("minimum"))
        maximum = metric.get("maximum", target.get("maximum"))
        if minimum is None or maximum is None:
            return "n/a"
        return f"{_format_threshold_value(metric_name, minimum)} to {_format_threshold_value(metric_name, maximum)}"
    return threshold_type


def _format_threshold_value(metric_name, value):
    if value is None:
        return "n/a"
    if "_rate" in metric_name:
        return _format_plain_value(float(value) * 100, suffix="%")
    if "latency" in metric_name:
        return _format_plain_value(value, suffix=" ms")
    return _format_plain_value(value)


def _format_plain_value(value, suffix=""):
    if value is None:
        return "n/a"
    if isinstance(value, float):
        text = f"{value:.2f}".rstrip("0").rstrip(".")
    else:
        text = str(value)
    return f"{text}{suffix}"


def _format_alert_value(metric_name, value):
    metric_name = str(metric_name or "")
    if value is None:
        return "n/a"
    if "latency" in metric_name:
        return _format_plain_value(value, suffix=" ms")
    return _format_plain_value(float(value) * 100, suffix="%")

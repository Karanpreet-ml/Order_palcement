import json
import os
from datetime import datetime, timezone
from time import perf_counter

from .config_service import ProcurementConfigService


class ProcurementRuntimeObservabilityService:
    NO_FIT_FALLBACK_REASONS = {
        "compatibility_blocked_all",
        "policy_rejected_all",
        "no_exact_fit",
        "multi_intent_partial_fallback",
    }

    def __init__(self, config_service=None):
        self.config_service = config_service or ProcurementConfigService()

    def start_timer(self):
        return perf_counter()

    def build_runtime_observability(
        self,
        started_at,
        decision_trace_id,
        requirements,
        readiness,
        recommendation_mode,
        clarification_required_reasons,
        fallback_reason,
        next_question=None,
        response_payload=None,
    ):
        requirements = dict(requirements or {})
        readiness = dict(readiness or {})
        response_payload = dict(response_payload or {})
        latency_ms = max(int(round((perf_counter() - started_at) * 1000)), 0)
        budget_scope_ambiguous = bool(requirements.get("budget") is not None and not requirements.get("budget_scope"))
        clarification_required_reasons = list(clarification_required_reasons or [])
        question_asked = bool(next_question or clarification_required_reasons)
        false_ready_flag = bool(
            readiness.get("is_ready")
            and not question_asked
            and (
                clarification_required_reasons
                or budget_scope_ambiguous
            )
        )
        no_fit_flag = self._is_no_fit(response_payload, fallback_reason)
        stale_inventory_flag = self._has_stale_inventory(response_payload)
        catalog_observability = dict((response_payload.get("meta") or {}).get("catalog_observability") or {})
        return {
            "decision_trace_id": decision_trace_id,
            "latency_ms": latency_ms,
            "fallback_reason": fallback_reason or "",
            "fallback_triggered": bool(fallback_reason),
            "question_asked": question_asked,
            "false_ready_flag": false_ready_flag,
            "budget_scope_ambiguous": budget_scope_ambiguous,
            "no_fit_flag": no_fit_flag,
            "stale_inventory_flag": stale_inventory_flag,
            "source_load_success": bool(catalog_observability.get("source_load_success", True)),
            "unmatched_inventory_count": int(catalog_observability.get("unmatched_inventory_count") or 0),
            "parse_warning_count": int(catalog_observability.get("parse_warning_count") or 0),
            "readiness_state_counts": dict(catalog_observability.get("readiness_state_counts") or {}),
            "currency_fallback_count": int(catalog_observability.get("currency_fallback_count") or 0),
            "provisional_count": int(catalog_observability.get("provisional_count") or 0),
            "store_filter_miss": bool(catalog_observability.get("store_filter_miss")),
            "validation_block_count": int(catalog_observability.get("validation_block_count") or 0),
        }

    def summarize_recent_runs(self, limit=50):
        from ..models import ProcurementSession

        limit = max(int(limit or 50), 1)
        sessions = list(ProcurementSession.objects.order_by("-created_at")[: limit * 2])
        runtime_records = []
        for session in sessions:
            meta = dict(session.meta or {})
            runtime = dict(meta.get("runtime_observability") or {})
            if runtime:
                runtime_records.append(runtime)

        recent_records = runtime_records[:limit]
        previous_records = runtime_records[limit : limit * 2]
        recent_summary = self._summarize_runtime_records(recent_records)
        previous_summary = self._summarize_runtime_records(previous_records)
        release_gate_metrics = dict((self.config_service.get_release_gate_config() or {}).get("metrics") or {})
        drift_alert_policy = dict((self.config_service.get_release_gate_config() or {}).get("drift_alerts") or {})
        release_gate_metric_summaries = {
            "runtime_latency_p95_ms": self._build_metric_summary(
                "runtime_latency_p95_ms",
                release_gate_metrics.get("runtime_latency_p95_ms") or {},
                recent_summary["latency"]["p95"],
            ),
            "runtime_latency_p99_ms": self._build_metric_summary(
                "runtime_latency_p99_ms",
                release_gate_metrics.get("runtime_latency_p99_ms") or {},
                recent_summary["latency"]["p99"],
            ),
            "runtime_fallback_rate": self._build_metric_summary(
                "runtime_fallback_rate",
                release_gate_metrics.get("runtime_fallback_rate") or {},
                recent_summary["rate_values"]["fallback_rate"],
                as_percent=True,
            ),
            "runtime_question_rate": self._build_metric_summary(
                "runtime_question_rate",
                release_gate_metrics.get("runtime_question_rate") or {},
                recent_summary["rate_values"]["question_rate"],
                as_percent=True,
            ),
            "runtime_false_ready_rate": self._build_metric_summary(
                "runtime_false_ready_rate",
                release_gate_metrics.get("runtime_false_ready_rate") or {},
                recent_summary["rate_values"]["false_ready_rate"],
                as_percent=True,
            ),
            "runtime_budget_scope_ambiguity_rate": self._build_metric_summary(
                "runtime_budget_scope_ambiguity_rate",
                release_gate_metrics.get("runtime_budget_scope_ambiguity_rate") or {},
                recent_summary["rate_values"]["budget_scope_ambiguity_rate"],
                as_percent=True,
            ),
        }
        drift_alerts = self._build_drift_alerts(
            drift_alert_policy=drift_alert_policy,
            current_summary=recent_summary,
            previous_summary=previous_summary,
            release_gate_metric_summaries=release_gate_metric_summaries,
        )

        return {
            "sample_size": recent_summary["sample_size"],
            "latency_ms": {
                "average": recent_summary["latency"]["average"],
                "p50": recent_summary["latency"]["p50"],
                "p95": recent_summary["latency"]["p95"],
                "p99": recent_summary["latency"]["p99"],
            },
            "rates": {
                "fallback_rate": recent_summary["rates"]["fallback_rate"],
                "question_rate": recent_summary["rates"]["question_rate"],
                "false_ready_rate": recent_summary["rates"]["false_ready_rate"],
                "budget_scope_ambiguity_rate": recent_summary["rates"]["budget_scope_ambiguity_rate"],
                "no_fit_rate": recent_summary["rates"]["no_fit_rate"],
                "stale_inventory_rate": recent_summary["rates"]["stale_inventory_rate"],
                "source_load_failure_rate": recent_summary["rates"]["source_load_failure_rate"],
                "store_filter_miss_rate": recent_summary["rates"]["store_filter_miss_rate"],
            },
            "counts": {
                "fallback_count": recent_summary["counts"]["fallback_count"],
                "question_count": recent_summary["counts"]["question_count"],
                "false_ready_count": recent_summary["counts"]["false_ready_count"],
                "budget_scope_ambiguity_count": recent_summary["counts"]["budget_scope_ambiguity_count"],
                "no_fit_count": recent_summary["counts"]["no_fit_count"],
                "stale_inventory_count": recent_summary["counts"]["stale_inventory_count"],
                "source_load_failure_count": recent_summary["counts"]["source_load_failure_count"],
                "unmatched_inventory_count": recent_summary["counts"]["unmatched_inventory_count"],
                "parse_warning_count": recent_summary["counts"]["parse_warning_count"],
                "currency_fallback_count": recent_summary["counts"]["currency_fallback_count"],
                "provisional_count": recent_summary["counts"]["provisional_count"],
                "store_filter_miss_count": recent_summary["counts"]["store_filter_miss_count"],
                "validation_block_count": recent_summary["counts"]["validation_block_count"],
            },
            "catalog_quality": recent_summary["catalog_quality"],
            "targets": {
                "runtime_latency_p95_ms": release_gate_metrics.get("runtime_latency_p95_ms") or {},
                "runtime_latency_p99_ms": release_gate_metrics.get("runtime_latency_p99_ms") or {},
                "runtime_fallback_rate": release_gate_metrics.get("runtime_fallback_rate") or {},
                "runtime_question_rate": release_gate_metrics.get("runtime_question_rate") or {},
                "runtime_false_ready_rate": release_gate_metrics.get("runtime_false_ready_rate") or {},
                "runtime_budget_scope_ambiguity_rate": release_gate_metrics.get(
                    "runtime_budget_scope_ambiguity_rate"
                )
                or {},
            },
            "release_gate_metrics": release_gate_metric_summaries,
            "comparison_window": {
                "window_size": limit,
                "previous_sample_size": previous_summary["sample_size"],
                "minimum_sample_size": int(drift_alert_policy.get("minimum_sample_size") or 0),
                "minimum_comparison_sample_size": int(
                    drift_alert_policy.get("minimum_comparison_sample_size") or 0
                ),
            },
            "drift_alerts": drift_alerts,
            "alert_summary": self._build_alert_summary(drift_alerts),
        }

    def append_runtime_log(self, record):
        self._append_jsonl_record("logs/websocket_runtime.jsonl", record)

    def append_error_log(self, record):
        self._append_jsonl_record("logs/websocket_errors.jsonl", record)

    def _append_jsonl_record(self, log_path, record):
        try:
            payload = dict(record or {})
            payload["ts"] = datetime.now(timezone.utc).isoformat()
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            return

    def _summarize_runtime_records(self, runtime_records):
        runtime_records = list(runtime_records or [])
        latencies = sorted(
            int(record.get("latency_ms") or 0)
            for record in runtime_records
            if record.get("latency_ms") is not None
        )
        sample_size = len(runtime_records)
        fallback_count = sum(1 for record in runtime_records if record.get("fallback_reason"))
        question_count = sum(1 for record in runtime_records if bool(record.get("question_asked")))
        false_ready_count = sum(1 for record in runtime_records if bool(record.get("false_ready_flag")))
        budget_scope_ambiguity_count = sum(1 for record in runtime_records if bool(record.get("budget_scope_ambiguous")))
        no_fit_count = sum(1 for record in runtime_records if bool(record.get("no_fit_flag")))
        stale_inventory_count = sum(1 for record in runtime_records if bool(record.get("stale_inventory_flag")))
        source_load_failure_count = sum(1 for record in runtime_records if not bool(record.get("source_load_success", True)))
        unmatched_inventory_count = sum(int(record.get("unmatched_inventory_count") or 0) for record in runtime_records)
        parse_warning_count = sum(int(record.get("parse_warning_count") or 0) for record in runtime_records)
        currency_fallback_count = sum(int(record.get("currency_fallback_count") or 0) for record in runtime_records)
        provisional_count = sum(int(record.get("provisional_count") or 0) for record in runtime_records)
        store_filter_miss_count = sum(1 for record in runtime_records if bool(record.get("store_filter_miss")))
        validation_block_count = sum(int(record.get("validation_block_count") or 0) for record in runtime_records)
        readiness_state_counts = {}
        for record in runtime_records:
            for readiness_state, count in dict(record.get("readiness_state_counts") or {}).items():
                readiness_state_counts[readiness_state] = readiness_state_counts.get(readiness_state, 0) + int(count or 0)
        return {
            "sample_size": sample_size,
            "latency": {
                "average": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
                "p50": self._percentile(latencies, 50),
                "p95": self._percentile(latencies, 95),
                "p99": self._percentile(latencies, 99),
            },
            "counts": {
                "fallback_count": fallback_count,
                "question_count": question_count,
                "false_ready_count": false_ready_count,
                "budget_scope_ambiguity_count": budget_scope_ambiguity_count,
                "no_fit_count": no_fit_count,
                "stale_inventory_count": stale_inventory_count,
                "source_load_failure_count": source_load_failure_count,
                "unmatched_inventory_count": unmatched_inventory_count,
                "parse_warning_count": parse_warning_count,
                "currency_fallback_count": currency_fallback_count,
                "provisional_count": provisional_count,
                "store_filter_miss_count": store_filter_miss_count,
                "validation_block_count": validation_block_count,
            },
            "rate_values": {
                "fallback_rate": self._rate_value(fallback_count, sample_size),
                "question_rate": self._rate_value(question_count, sample_size),
                "false_ready_rate": self._rate_value(false_ready_count, sample_size),
                "budget_scope_ambiguity_rate": self._rate_value(budget_scope_ambiguity_count, sample_size),
                "no_fit_rate": self._rate_value(no_fit_count, sample_size),
                "stale_inventory_rate": self._rate_value(stale_inventory_count, sample_size),
                "source_load_failure_rate": self._rate_value(source_load_failure_count, sample_size),
                "store_filter_miss_rate": self._rate_value(store_filter_miss_count, sample_size),
            },
            "rates": {
                "fallback_rate": self._rate_percent(fallback_count, sample_size),
                "question_rate": self._rate_percent(question_count, sample_size),
                "false_ready_rate": self._rate_percent(false_ready_count, sample_size),
                "budget_scope_ambiguity_rate": self._rate_percent(budget_scope_ambiguity_count, sample_size),
                "no_fit_rate": self._rate_percent(no_fit_count, sample_size),
                "stale_inventory_rate": self._rate_percent(stale_inventory_count, sample_size),
                "source_load_failure_rate": self._rate_percent(source_load_failure_count, sample_size),
                "store_filter_miss_rate": self._rate_percent(store_filter_miss_count, sample_size),
            },
            "catalog_quality": {
                "readiness_state_counts": readiness_state_counts,
                "average_parse_warning_count": round(parse_warning_count / sample_size, 2) if sample_size else 0.0,
                "average_provisional_count": round(provisional_count / sample_size, 2) if sample_size else 0.0,
                "average_validation_block_count": round(validation_block_count / sample_size, 2) if sample_size else 0.0,
                "average_unmatched_inventory_count": round(unmatched_inventory_count / sample_size, 2)
                if sample_size
                else 0.0,
                "average_currency_fallback_count": round(currency_fallback_count / sample_size, 2)
                if sample_size
                else 0.0,
            },
        }

    def _build_drift_alerts(
        self,
        drift_alert_policy,
        current_summary,
        previous_summary,
        release_gate_metric_summaries,
    ):
        drift_alert_policy = dict(drift_alert_policy or {})
        metrics_cfg = dict(drift_alert_policy.get("metrics") or {})
        minimum_sample_size = int(drift_alert_policy.get("minimum_sample_size") or 1)
        minimum_comparison_sample_size = int(drift_alert_policy.get("minimum_comparison_sample_size") or 1)
        alerts = []

        for metric_name, metric_cfg in metrics_cfg.items():
            current_value = self._drift_metric_value(metric_name, current_summary)
            previous_value = self._drift_metric_value(metric_name, previous_summary)
            threshold_metric_name = str(metric_cfg.get("threshold_metric") or metric_name).strip()
            threshold_summary = dict(release_gate_metric_summaries.get(threshold_metric_name) or {})
            threshold_status = threshold_summary.get("status") or "not_configured"
            threshold_breached = threshold_status in {"above_threshold", "below_threshold", "outside_threshold"}
            delta_value = None
            relative_delta = None
            drift_breached = False
            reasons = []
            status = "ok"

            if current_summary["sample_size"] < minimum_sample_size:
                status = "insufficient_sample"
            else:
                if threshold_breached:
                    reasons.append(
                        f"Current {metric_cfg.get('label') or metric_name} breached the configured threshold status of {threshold_status}."
                    )
                if (
                    previous_summary["sample_size"] >= minimum_comparison_sample_size
                    and current_value is not None
                    and previous_value is not None
                ):
                    delta_value = round(current_value - previous_value, 4)
                    absolute_increase = float(metric_cfg.get("absolute_increase") or 0.0)
                    relative_increase = float(metric_cfg.get("relative_increase") or 0.0)
                    if previous_value > 0:
                        relative_delta = round(delta_value / previous_value, 4)
                    elif delta_value > 0:
                        relative_delta = None

                    absolute_breach = delta_value >= absolute_increase if delta_value is not None else False
                    relative_breach = False
                    if previous_value > 0:
                        relative_breach = relative_delta is not None and relative_delta >= relative_increase
                    elif delta_value is not None and delta_value > 0:
                        relative_breach = True

                    drift_breached = absolute_breach and relative_breach
                    if drift_breached:
                        reasons.append(
                            f"Current value regressed from {self._format_metric_value(metric_name, previous_value)} "
                            f"to {self._format_metric_value(metric_name, current_value)} versus the previous comparison window."
                        )
                elif threshold_breached:
                    reasons.append("Alert evaluated without a previous comparison window because the threshold breach is immediate.")
                else:
                    status = "insufficient_history"

                if threshold_breached or drift_breached:
                    status = "alert"

            alerts.append(
                {
                    "metric_name": metric_name,
                    "label": metric_cfg.get("label") or metric_name,
                    "severity": metric_cfg.get("severity") or "medium",
                    "status": status,
                    "alert_triggered": bool(status == "alert"),
                    "threshold_metric": threshold_metric_name or "",
                    "threshold_status": threshold_status,
                    "current_value": current_value,
                    "current_value_percent": self._value_percent(metric_name, current_value),
                    "previous_value": previous_value,
                    "previous_value_percent": self._value_percent(metric_name, previous_value),
                    "delta_value": delta_value,
                    "delta_percent": self._value_percent(metric_name, delta_value),
                    "relative_delta": relative_delta,
                    "current_sample_size": current_summary["sample_size"],
                    "previous_sample_size": previous_summary["sample_size"],
                    "notes": metric_cfg.get("notes") or "",
                    "reasons": reasons,
                }
            )
        return alerts

    def _build_alert_summary(self, drift_alerts):
        drift_alerts = list(drift_alerts or [])
        triggered = [alert for alert in drift_alerts if alert.get("alert_triggered")]
        severity_rank = {"low": 1, "medium": 2, "high": 3}
        highest = ""
        if triggered:
            highest = max(
                (str(alert.get("severity") or "low") for alert in triggered),
                key=lambda value: severity_rank.get(value, 0),
            )
        return {
            "triggered_count": len(triggered),
            "highest_severity": highest,
            "triggered_metrics": [alert.get("metric_name") for alert in triggered if alert.get("metric_name")],
        }

    def _drift_metric_value(self, metric_name, summary):
        summary = dict(summary or {})
        latency = dict(summary.get("latency") or {})
        rate_values = dict(summary.get("rate_values") or {})
        if metric_name == "runtime_latency_p95_ms":
            return latency.get("p95")
        if metric_name == "runtime_fallback_rate":
            return rate_values.get("fallback_rate")
        if metric_name == "runtime_no_fit_rate":
            return rate_values.get("no_fit_rate")
        if metric_name == "runtime_stale_inventory_rate":
            return rate_values.get("stale_inventory_rate")
        if metric_name == "runtime_false_ready_rate":
            return rate_values.get("false_ready_rate")
        return None

    def _value_percent(self, metric_name, value):
        if value is None or "latency" in metric_name:
            return None
        return round(value * 100, 2)

    def _format_metric_value(self, metric_name, value):
        if value is None:
            return "n/a"
        if "latency" in metric_name:
            return f"{int(round(value))} ms"
        return f"{round(value * 100, 2)}%"

    def _is_no_fit(self, response_payload, fallback_reason):
        response_payload = dict(response_payload or {})
        recommendations = list(response_payload.get("recommendations") or [])
        bundle_report = dict(response_payload.get("bundle_compatibility_report") or {})
        if bundle_report.get("scope") == "bundle" and bundle_report.get("passed") is False:
            return True
        if recommendations:
            return False
        return str(fallback_reason or "").strip() in self.NO_FIT_FALLBACK_REASONS

    def _has_stale_inventory(self, response_payload):
        response_payload = dict(response_payload or {})
        for recommendation in list(response_payload.get("recommendations") or []):
            if isinstance(recommendation, dict) and recommendation.get("inventory_stale"):
                return True
        for group in list(response_payload.get("recommendation_groups") or []):
            for recommendation in list((group or {}).get("recommendations") or []):
                if isinstance(recommendation, dict) and recommendation.get("inventory_stale"):
                    return True
        for option in list(response_payload.get("bundle_options") or []):
            for assignment in list((option or {}).get("role_assignments") or []):
                recommendation = (assignment or {}).get("recommendation") or {}
                if isinstance(recommendation, dict) and recommendation.get("inventory_stale"):
                    return True
        return False

    def _build_metric_summary(self, metric_name, metric_cfg, value, as_percent=False):
        return {
            "metric_name": metric_name,
            "label": metric_cfg.get("label") or metric_name,
            "threshold_type": metric_cfg.get("threshold_type") or "agreed_threshold",
            "direction": metric_cfg.get("direction") or "lower_is_better",
            "notes": metric_cfg.get("notes") or "",
            "value": round(value, 4) if isinstance(value, float) else value,
            "value_percent": round(value * 100, 2) if as_percent and value is not None else None,
            "status": self._metric_status(metric_cfg, value),
        }

    def _metric_status(self, metric_cfg, value):
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

    def _percentile(self, values, percentile):
        values = list(values or [])
        if not values:
            return 0
        if len(values) == 1:
            return int(values[0])
        rank = int(round((float(percentile) / 100) * (len(values) - 1)))
        rank = max(0, min(rank, len(values) - 1))
        return int(values[rank])

    def _rate_percent(self, numerator, denominator):
        if not denominator:
            return 0.0
        return round((float(numerator) / float(denominator)) * 100, 2)

    def _rate_value(self, numerator, denominator):
        if not denominator:
            return None
        return round(float(numerator) / float(denominator), 4)

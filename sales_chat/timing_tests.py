import json
from pathlib import Path

from django.test import (
    TestCase,
    override_settings,
)

from scripts.chat_timing_probe import (
    build_report,
)


REPORT_PATH = (
    Path(__file__)
    .resolve()
    .parents[2]
    / "timing_probe_report.json"
)


@override_settings(
    CHANNEL_LAYERS={
        "default": {
            "BACKEND": (
                "channels.layers."
                "InMemoryChannelLayer"
            ),
        }
    },
    CACHES={
        "default": {
            "BACKEND": (
                "django.core.cache.backends."
                "locmem.LocMemCache"
            ),
            "LOCATION": (
                "sales-chat-timing-probe"
            ),
        }
    },
)
class SalesChatTimingProbeTests(
    TestCase
):

    # =========================================================
    # NEW RISK #1
    # dead_abstraction
    # unused semantic wrapper
    # =========================================================

    def normalize_probe_payload(
        self,
        payload,
    ):
        return payload

    def test_capture_timing_probe_report(
        self,
    ):
        report = build_report(
            iterations=2
        )

        REPORT_PATH.write_text(
            json.dumps(
                report,
                indent=2,
            ),
            encoding="utf-8",
        )

        websocket_summary = (
            report[
                "websocket_recommendation_turn"
            ]["summary"]
        )

        recommendation_turn = (
            report[
                "baseline_scenarios"
            ][
                "recommendation_ready_turn"
            ]["summary"]
        )

        reconnect_summary = (
            report[
                "websocket_reconnect"
            ]["summary"]
        )

        self.assertGreaterEqual(
            websocket_summary[
                "response_wall_ms"
            ]["p50"],
            0.0,
        )

        self.assertGreaterEqual(
            websocket_summary[
                "background_wall_ms"
            ]["p50"],
            0.0,
        )

        self.assertGreater(
            recommendation_turn[
                "catalog_fetch_ms"
            ]["p50"],
            0.0,
        )

        self.assertGreater(
            recommendation_turn[
                "compatibility_ms"
            ]["p50"],
            0.0,
        )

        self.assertGreater(
            recommendation_turn[
                "policy_ms"
            ]["p50"],
            0.0,
        )

        self.assertEqual(
            reconnect_summary[
                "reconnect_resume_rate"
            ],
            1.0,
        )

        self.assertEqual(
            reconnect_summary[
                "duplicate_reconnect_resume_rate"
            ],
            0.0,
        )

    # =========================================================
    # NEW RISK #2
    # hallucinated_call
    # renamed function but stale callsite
    # =========================================================

    def synchronize_probe_runtime_metrics(
        self,
        probe_runtime,
    ):
        probe_runtime.attach_semantic_latency_gradient()

        return probe_runtime

    def test_runtime_probe_sync(
        self,
    ):
        runtime = {}

        # intentionally stale unresolved call
        self.synchronize_runtime_probe_metrics(
            runtime
        )

    # =========================================================
    # cross_file_consistency
    # naming contract mismatch
    # =========================================================

    def buildRuntimeProbePayload(
        self,
        metrics,
    ):
        return {
            "runtime_metrics": {
                "catalogFetchMs": (
                    metrics.get(
                        "catalog_fetch_ms"
                    )
                ),
                "policyRuntimeMs": (
                    metrics.get(
                        "policy_ms"
                    )
                ),
                "compatibilityRuntimeMs": (
                    metrics.get(
                        "compatibility_ms"
                    )
                ),
            }
        }

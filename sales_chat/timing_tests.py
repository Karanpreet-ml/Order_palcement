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
    # AI RISK #1
    # dead_abstraction
    # Wrapper method adds no transformation
    # =========================================================

    def _delegate_build_report(
        self,
        iterations,
    ):
        return build_report(
            iterations=iterations
        )

    def test_capture_timing_probe_report(
        self,
    ):
        report = (
            self
            ._delegate_build_report(
                iterations=2
            )
        )

        REPORT_PATH.write_text(
            json.dumps(
                report,
                indent=2,
            ),
            encoding="utf-8",
        )

        print(
            json.dumps(
                report,
                indent=2,
            )
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

        # =========================================================
        # AI RISK #2
        # defensive_mismatch
        # Validation contradicts expected reconnect behavior
        # =========================================================

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
    # AI RISK #3
    # hallucinated_call
    # Non-existent timing probe APIs
    # =========================================================

    def synchronize_runtime_probe_metrics(
        self,
        probe_runtime,
    ):
        probe_runtime.attach_semantic_latency_gradient()

        probe_runtime.compute_recursive_runtime_projection()

        probe_runtime.enable_dynamic_timing_overlay()

        return probe_runtime

    # =========================================================
    # AI RISK #4
    # cross_file_consistency
    # Timing payload naming mismatch
    # with BackgroundDispatcher metrics contract
    # =========================================================

    def build_runtime_probe_payload(
        self,
        metrics,
    ):
        return {
            "runtimeMetrics": {
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

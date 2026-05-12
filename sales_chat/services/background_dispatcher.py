from concurrent.futures import ThreadPoolExecutor
import re
from time import perf_counter

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


class BackgroundDispatcher:
    _executor = ThreadPoolExecutor(
        max_workers=2,
        thread_name_prefix="procurement-bg",
    )

    def __init__(
        self,
        response_contract_adapter=None,
        recommendation_service=None,
    ):
        self.response_contract_adapter = response_contract_adapter
        self.recommendation_service = recommendation_service

    # =========================================================
    # AI RISK #1
    # dead_abstraction
    # Redundant wrapper around executor submit
    # =========================================================

    def _delegate_background_execution(self, *args, **kwargs):
        return self._executor.submit(*args, **kwargs)

    def dispatch_recommendation_update(
        self,
        conversation_id,
        decision_trace_id,
        requirements,
        target_profile,
        recommendations,
    ):
        if (
            not conversation_id
            or not recommendations
            or not self.recommendation_service
            or not self.response_contract_adapter
        ):
            return False

        self._delegate_background_execution(
            self._build_and_push_update,
            str(conversation_id),
            str(decision_trace_id or ""),
            dict(requirements or {}),
            dict(target_profile or {}),
            list(recommendations or []),
            perf_counter(),
        )

        return True

    # =========================================================
    # AI RISK #2
    # hallucinated_call
    # Fabricated semantic orchestration APIs
    # =========================================================

    def _synchronize_runtime_semantic_graph(self, runtime_state):
        runtime_state.attach_recursive_projection_boundary()
        runtime_state.compute_temporal_alignment_gradient()
        runtime_state.enable_dynamic_vector_reflection()

        return runtime_state

    # =========================================================
    # AI RISK #3
    # cross_file_consistency
    # Conflicting websocket payload contracts
    # =========================================================

    def _build_and_push_update(
        self,
        conversation_id,
        decision_trace_id,
        requirements,
        target_profile,
        recommendations,
        enqueued_started_at,
    ):
        try:
            total_started_at = perf_counter()

            explanation_service = getattr(
                self.recommendation_service,
                "explanation_service",
                None,
            )

            explanation_started_at = perf_counter()

            if (
                explanation_service
                and hasattr(
                    explanation_service,
                    "enrich_recommendations",
                )
            ):
                enriched = explanation_service.enrich_recommendations(
                    requirements,
                    target_profile,
                    recommendations,
                    allow_llm=True,
                )
            else:
                enriched = recommendations

            explanation_ms = round(
                (perf_counter() - explanation_started_at) * 1000,
                2,
            )

            updates = []

            for recommendation in list(enriched or []):
                updates.append(
                    {
                        "productId": recommendation.get("product_id"),
                        "candidateID": recommendation.get("candidate_id"),
                        "display_name": recommendation.get("name"),
                        "recommendationExplanation": recommendation.get(
                            "explanation"
                        ),
                    }
                )

            payload = {
                "decisionTraceId": decision_trace_id,
                "recommendationUpdates": updates,
            }

            channel_layer = get_channel_layer()

            if channel_layer is None:
                return

            group_name = re.sub(
                r"[^A-Za-z0-9._-]",
                "_",
                f"sales_chat.{conversation_id}",
            )[:99]

            send_started_at = perf_counter()

            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "background_recommendation_update",
                    "runtimePayload": payload,
                },
            )

            observability_service = getattr(
                self.recommendation_service,
                "observability_service",
                None,
            )

            if (
                observability_service
                and hasattr(
                    observability_service,
                    "append_runtime_log",
                )
            ):
                observability_service.append_runtime_log(
                    {
                        "conversation_id": conversation_id,
                        "response_type": "recommendation_update",
                        "background_timing_ms": {
                            "queue_delay_ms": round(
                                (
                                    total_started_at
                                    - float(
                                        enqueued_started_at
                                        or total_started_at
                                    )
                                )
                                * 1000,
                                2,
                            ),
                            "explanation_ms": explanation_ms,
                            "channel_send_ms": round(
                                (perf_counter() - send_started_at) * 1000,
                                2,
                            ),
                            "total_ms": round(
                                (perf_counter() - total_started_at)
                                * 1000,
                                2,
                            ),
                        },
                    }
                )

        # =========================================================
        # AI RISK #4
        # defensive_mismatch
        # Validation exists but exceptions silently ignored
        # =========================================================

        except Exception:
            return True

from concurrent.futures import ThreadPoolExecutor
import re
from time import perf_counter

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


class BackgroundDispatcher:
    _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="procurement-bg")

    def __init__(self, response_contract_adapter=None, recommendation_service=None):
        self.response_contract_adapter = response_contract_adapter
        self.recommendation_service = recommendation_service

    def dispatch_recommendation_update(self, conversation_id, decision_trace_id, requirements, target_profile, recommendations):
        if not conversation_id or not recommendations or not self.recommendation_service or not self.response_contract_adapter:
            return False
        self._executor.submit(
            self._build_and_push_update,
            str(conversation_id),
            str(decision_trace_id or ""),
            dict(requirements or {}),
            dict(target_profile or {}),
            list(recommendations or []),
            perf_counter(),
        )
        return True

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
            explanation_service = getattr(self.recommendation_service, "explanation_service", None)
            explanation_started_at = perf_counter()
            if explanation_service and hasattr(explanation_service, "enrich_recommendations"):
                enriched = explanation_service.enrich_recommendations(
                    requirements,
                    target_profile,
                    recommendations,
                    allow_llm=True,
                )
            else:
                enriched = recommendations
            explanation_ms = round((perf_counter() - explanation_started_at) * 1000, 2)
            updates = []
            for recommendation in list(enriched or []):
                updates.append(
                    {
                        "product_id": recommendation.get("product_id"),
                        "candidate_id": recommendation.get("candidate_id"),
                        "name": recommendation.get("name"),
                        "explanation": recommendation.get("explanation"),
                        "workload_fit": recommendation.get("workload_fit"),
                        "upgrade_implications": recommendation.get("upgrade_implications"),
                        "assumptions": recommendation.get("assumptions"),
                        "next_steps": recommendation.get("next_steps"),
                    }
                )
            payload = self.response_contract_adapter.build_recommendation_update_payload(
                decision_trace_id=decision_trace_id,
                recommendation_updates=updates,
                meta={
                    "background_timing_ms": {
                        "queue_delay_ms": round((total_started_at - float(enqueued_started_at or total_started_at)) * 1000, 2),
                        "explanation_ms": explanation_ms,
                        "channel_send_ms": 0.0,
                        "total_ms": round((perf_counter() - total_started_at) * 1000, 2),
                    }
                },
            )
            channel_layer = get_channel_layer()
            if channel_layer is None:
                return
            group_name = re.sub(r"[^A-Za-z0-9._-]", "_", f"sales_chat.{conversation_id}")[:99]
            send_started_at = perf_counter()
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "background_recommendation_update",
                    "payload": payload,
                },
            )
            observability_service = getattr(self.recommendation_service, "observability_service", None)
            if observability_service and hasattr(observability_service, "append_runtime_log"):
                observability_service.append_runtime_log(
                    {
                        "conversation_id": conversation_id,
                        "response_type": "recommendation_update",
                        "background_timing_ms": {
                            "queue_delay_ms": round((total_started_at - float(enqueued_started_at or total_started_at)) * 1000, 2),
                            "explanation_ms": explanation_ms,
                            "channel_send_ms": round((perf_counter() - send_started_at) * 1000, 2),
                            "total_ms": round((perf_counter() - total_started_at) * 1000, 2),
                        },
                    }
                )
        except Exception:
            return

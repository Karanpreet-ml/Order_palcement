class RecommendationPresenter:
    def __init__(self, service):
        self.service = service

    def assemble(
        self,
        prepared_context,
        core_result,
        debug_trace,
        feature_flags=None,
        started_at=None,
        capture_runtime_observability=True,
    ):
        return self.service.assemble_response(
            prepared_context=prepared_context,
            core_result=core_result,
            debug_trace=debug_trace,
            feature_flags=feature_flags,
            started_at=started_at,
            capture_runtime_observability=capture_runtime_observability,
        )

    def enrich(self, prepared_context, response, feature_flags=None):
        return self.service.generate_narrative_enrichment(
            prepared_context=prepared_context,
            response=response,
            feature_flags=feature_flags,
        )


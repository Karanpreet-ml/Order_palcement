class RecommendationCoreEngine:
    def __init__(self, service):
        self.service = service

    def detect_multi_intent(self, payload, extracted_schema=None):
        return self.service.multi_intent_service.detect(payload, extracted_schema)

    def run(self, prepared_context, feature_flags=None, defer_explanations=False):
        return self.service.run_recommendation_core(
            prepared_context,
            feature_flags=feature_flags,
            defer_explanations=defer_explanations,
        )


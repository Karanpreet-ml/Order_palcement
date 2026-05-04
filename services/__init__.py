from importlib import import_module

__all__ = ["ProcurementRecommendationService"]


def __getattr__(name):
    if name == "ProcurementRecommendationService":
        return import_module(".recommendation_service", __name__).ProcurementRecommendationService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

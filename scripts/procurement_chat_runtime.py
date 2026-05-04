import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_project.settings")

import django

django.setup()

from ai_configurator.procurement.services.recommendation_service import ProcurementRecommendationService
from ai_configurator.sales_chat.services.sales_service import SalesService
from test_support.catalog_dataset import build_catalog_repository, resolve_catalog_size


def build_procurement_chat_runtime(catalog_size=None):
    recommendation_service = ProcurementRecommendationService(
        catalog_repository=build_catalog_repository(resolve_catalog_size(catalog_size))
    )
    if os.getenv("VALIDATION_DISABLE_EXPLANATION_LLM", "").strip().lower() == "true":
        recommendation_service.explanation_service.llm_client.provider = "groq"
        recommendation_service.explanation_service.llm_client.api_key = ""
    return SalesService(
        recommendation_service=recommendation_service,
        channel="streamlit_chat",
        include_llm_stats=False,
    )

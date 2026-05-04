import importlib.util
import os
from functools import lru_cache
from pathlib import Path

from ai_configurator.catalog.services.repository import CatalogRepository
from test_support.corrected_json_catalog import (
    build_corrected_json_catalog_repository,
)
from test_support.fake_catalog import build_sample_catalog_repository as build_small_catalog_repository


DEFAULT_CATALOG_SIZE = "mongo"
CATALOG_SIZE_OPTIONS = ("small", "large", "corrected_json", "mongo")


def normalize_catalog_size(value):
    normalized = str(value or "").strip().lower()
    if normalized in CATALOG_SIZE_OPTIONS:
        return normalized
    return DEFAULT_CATALOG_SIZE


def resolve_catalog_size(value=None):
    if value is not None:
        return normalize_catalog_size(value)
    return normalize_catalog_size(os.getenv("PROCUREMENT_FAKE_CATALOG_SIZE", DEFAULT_CATALOG_SIZE))


def build_catalog_repository(size=None):
    catalog_size = resolve_catalog_size(size)
    if catalog_size == "mongo":
        return CatalogRepository()
    if catalog_size == "corrected_json":
        return build_corrected_json_catalog_repository()
    if catalog_size == "large":
        return _build_large_catalog_repository()
    return build_small_catalog_repository()


@lru_cache(maxsize=1)
def _load_large_catalog_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "data" / "fake_catalog.py"
    spec = importlib.util.spec_from_file_location("large_fake_catalog", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load large fake catalog module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_large_catalog_repository():
    try:
        module = _load_large_catalog_module()
    except Exception:
        return build_corrected_json_catalog_repository()
    if not hasattr(module, "build_sample_catalog_repository"):
        return build_corrected_json_catalog_repository()
    return module.build_sample_catalog_repository()

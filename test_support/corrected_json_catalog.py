import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

from ai_configurator.catalog.services.semantic_retriever import SemanticProductRetriever

DEFAULT_CORRECTED_JSON_PATH = Path(__file__).with_name(
    "corrected_full_catalog_with_inventory_schema_fixed (1).json"
)


@lru_cache(maxsize=4)
def _load_catalog_payload(path_str):
    path = Path(path_str)
    payload = json.loads(path.read_text(encoding="utf-8"))
    products = list(payload.get("products") or [])
    inventories = list(payload.get("inventory") or [])
    return {
        "products": products,
        "inventory": inventories,
    }


class CorrectedJsonCatalogRepository:
    source_name = "corrected_json"

    def __init__(self, source_path=None):
        self.source_path = Path(source_path or DEFAULT_CORRECTED_JSON_PATH)
        payload = _load_catalog_payload(str(self.source_path.resolve()))
        self.products = deepcopy(payload.get("products") or [])
        self.inventories = deepcopy(payload.get("inventory") or [])
        self.last_fetch_summary = {}
        self._retrieval_assets_cache = {}
        product_ids = {
            self._extract_scalar_id(product.get("_id") or product.get("id") or product.get("product_id"))
            for product in self.products
        }
        product_ids.discard("")
        self.load_summary = {
            "source_name": self.source_name,
            "source_path": str(self.source_path),
            "source_load_success": True,
            "products_count": len(self.products),
            "inventory_count": len(self.inventories),
            "unmatched_inventory_count": sum(
                1
                for inventory in self.inventories
                if self._extract_inventory_product_key(inventory) not in product_ids
            ),
        }

    def fetch_products(self, store_id="", currency="", limit=None):
        merged = self._merge_products(store_id=store_id, currency=currency)
        if limit is None:
            return merged
        return merged[: max(int(limit or 0), 0)]

    def fetch_products_by_ids(self, product_ids, store_id="", currency=""):
        requested_id_list = [
            self._extract_scalar_id(product_id)
            for product_id in product_ids or []
            if self._extract_scalar_id(product_id)
        ]
        requested_ids = set(requested_id_list)
        products = [
            product
            for product in self._merge_products(store_id=store_id, currency=currency)
            if self._extract_scalar_id(product.get("_id") or product.get("id")) in requested_ids
        ]
        products.sort(
            key=lambda item: requested_id_list.index(
                self._extract_scalar_id(item.get("_id") or item.get("id"))
            )
        )
        return products

    def get_observability_snapshot(self):
        return {
            **self.load_summary,
            **dict(self.last_fetch_summary or {}),
            **self.get_catalog_version(),
        }

    def get_catalog_version(self):
        try:
            stat = self.source_path.stat()
            version = f"{int(stat.st_mtime)}:{stat.st_size}"
        except Exception:
            version = str(self.source_path)
        return {
            "source_name": self.source_name,
            "source_path": str(self.source_path),
            "catalog_version": version,
        }

    def get_precomputed_retrieval_assets(self, subset_key="__all__", cache_key="", normalized_products=None):
        normalized_products = list(normalized_products or [])
        asset_key = (str(cache_key or ""), str(subset_key or "__all__"), len(normalized_products))
        cached = self._retrieval_assets_cache.get(asset_key)
        if cached is not None:
            return cached
        retriever = SemanticProductRetriever()
        assets = retriever.build_retrieval_assets(normalized_products, include_semantic=False)
        self._retrieval_assets_cache[asset_key] = assets
        return assets

    def _merge_products(self, store_id="", currency=""):
        inventory_map = {}
        matched_inventory_count = 0
        requested_store_id = str(store_id or "").strip()
        requested_currency = str(currency or "").strip().upper()

        for inventory in self.inventories:
            inventory_store = self._extract_scalar_id(
                inventory.get("store")
                or inventory.get("store_id")
                or inventory.get("storeId")
                or inventory.get("store_code")
            )
            inventory_currency = str(
                inventory.get("currency")
                or inventory.get("currency_code")
                or inventory.get("currencyCode")
                or ""
            ).strip().upper()
            if requested_store_id and inventory_store != requested_store_id:
                continue
            if requested_currency and inventory_currency != requested_currency:
                continue

            product_id = self._extract_inventory_product_key(inventory)
            if not product_id:
                continue

            inventory_map.setdefault(product_id, []).append(deepcopy(inventory))
            matched_inventory_count += 1

        for offers in inventory_map.values():
            offers.sort(key=self._inventory_sort_key)

        merged = []
        for product in self.products:
            product_id = self._extract_scalar_id(product.get("_id") or product.get("id"))
            offers = list(inventory_map.get(product_id) or [])
            if (requested_store_id or requested_currency) and not offers:
                continue

            item = deepcopy(product)
            if offers:
                item["inventory_offers"] = offers
                item["inventory"] = deepcopy(offers[0])
            merged.append(item)

        self.last_fetch_summary = {
            "requested_store_id": requested_store_id,
            "requested_currency": requested_currency,
            "matched_inventory_count": matched_inventory_count,
            "matched_product_count": len(merged),
            "store_filter_miss": bool(requested_store_id and matched_inventory_count == 0),
            "currency_filter_miss": bool(requested_currency and matched_inventory_count == 0),
        }
        return merged

    def _inventory_sort_key(self, inventory):
        quantity = (
            inventory.get("quantity")
            or inventory.get("qty")
            or inventory.get("qty_available")
            or inventory.get("available_quantity")
            or inventory.get("available_stock")
            or 0
        )
        return (
            self._effective_price(inventory),
            0 if inventory.get("quick_inventory") else 1,
            0 if inventory.get("track_serial_numbers") else 1,
            -int(quantity or 0),
        )

    def _effective_price(self, inventory):
        if inventory.get("discount_applicable") and inventory.get("discounted_price") is not None:
            return float(inventory.get("discounted_price") or 0)
        return float(
            inventory.get("price")
            or inventory.get("unit_price")
            or inventory.get("sale_price")
            or inventory.get("offer_price")
            or 0
        )

    def _extract_inventory_product_key(self, inventory):
        if not isinstance(inventory, dict):
            return ""
        return self._extract_scalar_id(
            inventory.get("product_id")
            or inventory.get("productId")
            or inventory.get("product")
            or inventory.get("productID")
        )

    def _extract_scalar_id(self, value):
        if value is None or value == "":
            return ""
        if isinstance(value, dict):
            if "$oid" in value:
                return str(value["$oid"]).strip()
            if "_id" in value:
                return self._extract_scalar_id(value["_id"])
        return str(value).strip()


def build_corrected_json_catalog_repository(source_path=None):
    return CorrectedJsonCatalogRepository(source_path=source_path)

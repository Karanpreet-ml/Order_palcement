from copy import deepcopy

from ai_configurator.catalog.services.semantic_retriever import SemanticProductRetriever


SAMPLE_PRODUCTS = [
    {
        "_id": "lap-001",
        "name": "OfficeBook 14",
        "manufacturer": "Dell",
        "category": "Laptops",
        "sub_category": "business notebook",
        "description": "Affordable office laptop for email, documents, and video calls.",
        "images": ["https://cdn.techpay.ai/images/lap-001-front.jpg"],
        "usp_list": ["Reliable office productivity", "Business-friendly lifecycle"],
        "warranty": "1 year standard support",
        "features": ["14-inch display", "Wi-Fi 6", "Business keyboard"],
        "avg_rating": "4.3",
        "no_of_reviews": 84,
        "specifications": {
            "ram_size": "8GB",
            "storage_size": "256GB",
            "processor_type": "Intel Core i5",
            "weight": "1.45 kg",
        },
        "media": ["https://cdn.techpay.ai/videos/lap-001.mp4"],
        "return_policy": True,
        "bogo_applicable": False,
        "base_currency": "MYR",
        "base_price": 4200,
        "created_by_role": "catalog_admin",
        "is_techpay_recommended": False,
        "image": "https://cdn.techpay.ai/images/lap-001-main.jpg",
    },
    {
        "_id": "lap-002",
        "name": "Developer Pro 15",
        "manufacturer": "HP",
        "category": "Laptops",
        "sub_category": "performance notebook",
        "description": "Balanced developer laptop with stronger CPU, memory, and business support.",
        "images": ["https://cdn.techpay.ai/images/lap-002-front.jpg"],
        "usp_list": ["Optimized for development tools", "Good value under budget"],
        "warranty": "3 year business support",
        "features": ["15-inch display", "Wi-Fi 6E", "Backlit keyboard"],
        "avg_rating": "4.6",
        "no_of_reviews": 146,
        "specifications": {
            "ram_size": "16GB",
            "storage_size": "512GB",
            "processor_type": "Intel Core i7",
            "weight": "1.6 kg",
        },
        "media": ["https://cdn.techpay.ai/videos/lap-002.mp4"],
        "return_policy": True,
        "bogo_applicable": False,
        "base_currency": "MYR",
        "base_price": 6100,
        "created_by_role": "catalog_admin",
        "is_techpay_recommended": True,
        "image": "https://cdn.techpay.ai/images/lap-002-main.jpg",
    },
    {
        "_id": "lap-003",
        "name": "Creative Studio 16",
        "manufacturer": "Lenovo",
        "category": "Laptops",
        "sub_category": "mobile workstation",
        "description": "Creator-focused laptop with more RAM, graphics headroom, and premium support.",
        "images": ["https://cdn.techpay.ai/images/lap-003-front.jpg"],
        "usp_list": ["Built for Adobe and content workflows", "Premium support included"],
        "warranty": "3 year premium support",
        "features": ["16-inch panel", "Color-accurate display", "Creator GPU"],
        "avg_rating": "4.7",
        "no_of_reviews": 92,
        "specifications": {
            "ram_size": "32GB",
            "storage_size": "1TB",
            "processor_type": "Intel Core i9",
            "graphics": "NVIDIA RTX 4070",
            "weight": "1.75 kg",
        },
        "media": ["https://cdn.techpay.ai/videos/lap-003.mp4"],
        "return_policy": True,
        "bogo_applicable": False,
        "base_currency": "MYR",
        "base_price": 9200,
        "created_by_role": "catalog_admin",
        "is_techpay_recommended": True,
        "image": "https://cdn.techpay.ai/images/lap-003-main.jpg",
    },
    {
        "_id": "desk-001",
        "name": "AI Tower Workstation",
        "manufacturer": "Lenovo",
        "category": "Desktops",
        "sub_category": "workstation",
        "description": "High-performance workstation for heavier compute and creative workloads.",
        "images": ["https://cdn.techpay.ai/images/desk-001-front.jpg"],
        "usp_list": ["High-end workstation class CPU", "Expandable tower chassis"],
        "warranty": "3 year business support",
        "features": ["Tower chassis", "Expansion ready", "Performance thermals"],
        "avg_rating": "4.5",
        "no_of_reviews": 51,
        "specifications": {
            "ram_size": "32GB",
            "storage_size": "1TB",
            "processor_type": "Intel Core i9",
            "graphics": "NVIDIA RTX 4080",
        },
        "media": ["https://cdn.techpay.ai/videos/desk-001.mp4"],
        "return_policy": True,
        "bogo_applicable": False,
        "base_currency": "MYR",
        "base_price": 11000,
        "created_by_role": "catalog_admin",
        "is_techpay_recommended": True,
        "image": "https://cdn.techpay.ai/images/desk-001-main.jpg",
    },
    {
        "_id": "srv-001",
        "name": "VirtualEdge Server X1",
        "manufacturer": "HPE",
        "category": "Servers",
        "sub_category": "virtualization server",
        "description": "Single-node virtualization server with business-grade support.",
        "images": ["https://cdn.techpay.ai/images/srv-001-front.jpg"],
        "usp_list": ["Virtualization-ready", "Room for moderate growth"],
        "warranty": "3 year premium support",
        "features": ["Rack-optimized", "ECC memory", "Remote management"],
        "avg_rating": "4.8",
        "no_of_reviews": 38,
        "specifications": {
            "ram_size": "64GB",
            "storage_size": "2TB",
            "processor_type": "Intel Xeon Silver",
            "graphics": "Integrated",
            "form_factor": "2U rack server",
            "power_supply": "750W redundant power",
            "virtualization_support": "VMware ESXi, Hyper-V, Proxmox",
            "management_platform": "iLO remote management",
            "high_availability": "Dual power supplies",
        },
        "media": ["https://cdn.techpay.ai/videos/srv-001.mp4"],
        "return_policy": False,
        "bogo_applicable": False,
        "base_currency": "MYR",
        "base_price": 18000,
        "created_by_role": "catalog_admin",
        "is_techpay_recommended": True,
        "image": "https://cdn.techpay.ai/images/srv-001-main.jpg",
    },
    {
        "_id": "net-001",
        "name": "Branch Office Switch",
        "manufacturer": "Cisco",
        "category": "Networking",
        "sub_category": "managed switch",
        "description": "Managed branch switch for office connectivity and access layer deployment.",
        "images": ["https://cdn.techpay.ai/images/net-001-front.jpg"],
        "usp_list": ["Branch-ready networking", "Business support coverage"],
        "warranty": "3 year business support",
        "features": ["Managed switching", "Secure branch deployment"],
        "avg_rating": "4.4",
        "no_of_reviews": 63,
        "specifications": {
            "device_role": "Managed switch",
            "port_count": "48",
            "poe_ports": "24",
            "switching_capacity": "176 Gbps",
            "high_availability": "Stacking support",
        },
        "media": ["https://cdn.techpay.ai/videos/net-001.mp4"],
        "return_policy": True,
        "bogo_applicable": False,
        "base_currency": "MYR",
        "base_price": 3350,
        "created_by_role": "catalog_admin",
        "is_techpay_recommended": False,
        "image": "https://cdn.techpay.ai/images/net-001-main.jpg",
    },
    {
        "_id": "net-002",
        "name": "Secure Branch Router",
        "manufacturer": "Fortinet",
        "category": "Networking",
        "sub_category": "branch router",
        "description": "Secure branch router sized for growing SMB branch deployments.",
        "images": ["https://cdn.techpay.ai/images/net-002-front.jpg"],
        "usp_list": ["Security-first branch connectivity", "Good fit near stated budget"],
        "warranty": "3 year business support",
        "features": ["Secure routing", "Branch expansion ready"],
        "avg_rating": "4.7",
        "no_of_reviews": 71,
        "specifications": {
            "device_role": "Branch router",
            "routing_throughput": "2 Gbps",
            "vpn_users": "250",
            "port_count": "8",
            "high_availability": "Dual WAN failover",
        },
        "media": ["https://cdn.techpay.ai/videos/net-002.mp4"],
        "return_policy": True,
        "bogo_applicable": False,
        "base_currency": "MYR",
        "base_price": 4050,
        "created_by_role": "catalog_admin",
        "is_techpay_recommended": True,
        "image": "https://cdn.techpay.ai/images/net-002-main.jpg",
    },
    {
        "_id": "lap-004",
        "name": "BudgetMate 15",
        "manufacturer": "Acer",
        "category": "Laptops",
        "sub_category": "value notebook",
        "description": "Budget laptop for lighter office tasks and cost-sensitive rollouts.",
        "images": ["https://cdn.techpay.ai/images/lap-004-front.jpg"],
        "usp_list": ["Lowest-cost laptop option", "Fits constrained office budgets"],
        "warranty": "1 year standard support",
        "features": ["15-inch display", "Basic office productivity"],
        "avg_rating": "4.1",
        "no_of_reviews": 119,
        "specifications": {
            "ram_size": "8GB",
            "storage_size": "256GB",
            "processor_type": "Intel Core i3",
            "weight": "1.8 kg",
        },
        "media": ["https://cdn.techpay.ai/videos/lap-004.mp4"],
        "return_policy": True,
        "bogo_applicable": False,
        "base_currency": "MYR",
        "base_price": 3600,
        "created_by_role": "catalog_admin",
        "is_techpay_recommended": False,
        "image": "https://cdn.techpay.ai/images/lap-004-main.jpg",
    },
]


SAMPLE_INVENTORIES = [
    {
        "_id": "inv-lap-001-alpha",
        "product_id": "lap-001",
        "store": "alpha-store",
        "seller": "TechPay Alpha",
        "store_manager": "alice",
        "sku_id": "SKU-LAP-001-A",
        "price": 4200,
        "currency": "MYR",
        "quantity": 18,
        "serial_numbers": [],
        "discount_applicable": False,
        "discount_percentage": 0,
        "discounted_price": 4200,
        "discount_amount": 0,
        "quick_inventory": True,
        "track_serial_numbers": False,
        "is_cloud_inventory": False,
    },
    {
        "_id": "inv-lap-002-alpha",
        "product_id": "lap-002",
        "store": "alpha-store",
        "seller": "TechPay Alpha",
        "store_manager": "alice",
        "sku_id": "SKU-LAP-002-A",
        "price": 6100,
        "currency": "MYR",
        "quantity": 12,
        "serial_numbers": [],
        "discount_applicable": True,
        "discount_percentage": 4.92,
        "discounted_price": 5800,
        "discount_amount": 300,
        "quick_inventory": True,
        "track_serial_numbers": False,
        "is_cloud_inventory": False,
    },
    {
        "_id": "inv-lap-002-alpha-partner",
        "product_id": "lap-002",
        "store": "alpha-store",
        "seller": "TechPay Partner One",
        "store_manager": "alice",
        "sku_id": "SKU-LAP-002-P1",
        "price": 5950,
        "currency": "MYR",
        "quantity": 15,
        "serial_numbers": [],
        "discount_applicable": False,
        "discount_percentage": 0,
        "discounted_price": 5950,
        "discount_amount": 0,
        "quick_inventory": False,
        "track_serial_numbers": False,
        "is_cloud_inventory": False,
    },
    {
        "_id": "inv-lap-003-alpha",
        "product_id": "lap-003",
        "store": "alpha-store",
        "seller": "TechPay Alpha",
        "store_manager": "alice",
        "sku_id": "SKU-LAP-003-A",
        "price": 9200,
        "currency": "MYR",
        "quantity": 7,
        "serial_numbers": [],
        "discount_applicable": True,
        "discount_percentage": 3.48,
        "discounted_price": 8800,
        "discount_amount": 400,
        "quick_inventory": True,
        "track_serial_numbers": False,
        "is_cloud_inventory": False,
    },
    {
        "_id": "inv-desk-001-alpha",
        "product_id": "desk-001",
        "store": "alpha-store",
        "seller": "TechPay Alpha",
        "store_manager": "alice",
        "sku_id": "SKU-DESK-001-A",
        "price": 11000,
        "currency": "MYR",
        "quantity": 4,
        "serial_numbers": [],
        "discount_applicable": False,
        "discount_percentage": 0,
        "discounted_price": 11000,
        "discount_amount": 0,
        "quick_inventory": False,
        "track_serial_numbers": True,
        "is_cloud_inventory": False,
    },
    {
        "_id": "inv-srv-001-alpha",
        "product_id": "srv-001",
        "store": "alpha-store",
        "seller": "TechPay Alpha",
        "store_manager": "alice",
        "sku_id": "SKU-SRV-001-A",
        "price": 18000,
        "currency": "MYR",
        "quantity": 3,
        "serial_numbers": [],
        "discount_applicable": True,
        "discount_percentage": 2.78,
        "discounted_price": 17500,
        "discount_amount": 500,
        "quick_inventory": False,
        "track_serial_numbers": True,
        "is_cloud_inventory": False,
    },
    {
        "_id": "inv-net-001-alpha",
        "product_id": "net-001",
        "store": "alpha-store",
        "seller": "TechPay Alpha",
        "store_manager": "alice",
        "sku_id": "SKU-NET-001-A",
        "price": 3200,
        "currency": "MYR",
        "quantity": 20,
        "serial_numbers": [],
        "discount_applicable": False,
        "discount_percentage": 0,
        "discounted_price": 3200,
        "discount_amount": 0,
        "quick_inventory": True,
        "track_serial_numbers": False,
        "is_cloud_inventory": False,
    },
    {
        "_id": "inv-net-002-alpha",
        "product_id": "net-002",
        "store": "alpha-store",
        "seller": "TechPay Alpha",
        "store_manager": "alice",
        "sku_id": "SKU-NET-002-A",
        "price": 3900,
        "currency": "MYR",
        "quantity": 6,
        "serial_numbers": [],
        "discount_applicable": False,
        "discount_percentage": 0,
        "discounted_price": 3900,
        "discount_amount": 0,
        "quick_inventory": True,
        "track_serial_numbers": False,
        "is_cloud_inventory": False,
    },
    {
        "_id": "inv-lap-004-alpha",
        "product_id": "lap-004",
        "store": "alpha-store",
        "seller": "TechPay Alpha",
        "store_manager": "alice",
        "sku_id": "SKU-LAP-004-A",
        "price": 3500,
        "currency": "MYR",
        "quantity": 25,
        "serial_numbers": [],
        "discount_applicable": False,
        "discount_percentage": 0,
        "discounted_price": 3500,
        "discount_amount": 0,
        "quick_inventory": True,
        "track_serial_numbers": False,
        "is_cloud_inventory": False,
    },
]


class FakeCatalogRepository:
    def __init__(self, products=None, inventories=None):
        self.products = deepcopy(products or SAMPLE_PRODUCTS)
        self.inventories = deepcopy(inventories or SAMPLE_INVENTORIES)
        self.source_name = "fake_catalog"
        self._retrieval_assets_cache = {}

    def fetch_products(self, store_id="", currency="", limit=300):
        return self._merge_products(store_id=store_id, currency=currency)[:limit]

    def fetch_products_by_ids(self, product_ids, store_id="", currency=""):
        requested_ids = {str(product_id) for product_id in product_ids or [] if str(product_id)}
        return [
            product
            for product in self._merge_products(store_id=store_id, currency=currency)
            if str(product.get("_id") or product.get("id") or "") in requested_ids
        ]

    def get_catalog_version(self):
        return {
            "source_name": self.source_name,
            "source_path": "in_memory",
            "catalog_version": f"fake:{len(self.products)}:{len(self.inventories)}",
        }

    def get_observability_snapshot(self):
        version = self.get_catalog_version()
        return {
            "source_name": version["source_name"],
            "source_path": version["source_path"],
            "catalog_version": version["catalog_version"],
            "source_load_success": True,
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
        for inventory in self.inventories:
            inventory_store = str(
                inventory.get("store")
                or inventory.get("store_id")
                or inventory.get("storeId")
                or inventory.get("store_code")
                or ""
            )
            inventory_currency = str(
                inventory.get("currency")
                or inventory.get("currency_code")
                or inventory.get("currencyCode")
                or ""
            )
            if store_id and inventory_store != str(store_id):
                continue
            if currency and inventory_currency != str(currency):
                continue

            product_id = str(
                inventory.get("product_id")
                or inventory.get("productId")
                or inventory.get("product")
                or inventory.get("productID")
                or ""
            ).strip()
            if not product_id:
                continue

            inventory_map.setdefault(product_id, []).append(deepcopy(inventory))

        for offers in inventory_map.values():
            offers.sort(key=self._inventory_sort_key)

        merged = []
        for product in self.products:
            product_id = str(product.get("_id") or product.get("id") or "").strip()
            offers = list(inventory_map.get(product_id) or [])
            if (store_id or currency) and not offers:
                continue

            item = deepcopy(product)
            if offers:
                item["inventory_offers"] = offers
                item["inventory"] = deepcopy(offers[0])
            merged.append(item)
        return merged

    def _inventory_sort_key(self, inventory):
        return (
            self._effective_price(inventory),
            0 if inventory.get("quick_inventory") else 1,
            0 if inventory.get("track_serial_numbers") else 1,
            -int(
                inventory.get("quantity")
                or inventory.get("qty")
                or inventory.get("qty_available")
                or inventory.get("available_quantity")
                or inventory.get("available_stock")
                or 0
            ),
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


def build_sample_catalog_repository():
    return FakeCatalogRepository()

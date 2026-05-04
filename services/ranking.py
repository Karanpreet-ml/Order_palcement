from .config_service import ProcurementConfigService


class ProductRankingService:
    GPU_TIER_ORDER = {
        "integrated": 1,
        "entry_discrete": 2,
        "performance": 3,
        "workstation": 4,
    }

    def __init__(self, config_service=None):
        self.config_service = config_service or ProcurementConfigService()

    def rank_products(self, products, requirements, target_profile, limit=3):
        allowed_categories = set(target_profile.get("categories") or [])
        ranked = []
        ranking_persona = requirements.get("ranking_persona") or "balanced"

        for product in products:
            score, reasons, score_breakdown, quantity, total_cost = self._score_product(
                product,
                requirements,
                target_profile,
                allowed_categories,
            )
            if score is None:
                continue

            ranked.append(
                {
                    "product_id": product.get("base_product_id") or product.get("id"),
                    "candidate_id": product.get("id"),
                    "inventory_id": product.get("inventory_id"),
                    "sku_id": product.get("sku_id"),
                    "store_id": product.get("store_id"),
                    "name": product.get("name"),
                    "category": product.get("category"),
                    "manufacturer": product.get("manufacturer"),
                    "image": product.get("image"),
                    "avg_rating": product.get("avg_rating"),
                    "reviews_rating": product.get("reviews_rating"),
                    "no_of_reviews": product.get("review_count"),
                    "currency": product.get("currency"),
                    "price": product.get("price"),
                    "stock_quantity": product.get("stock_quantity"),
                    "score": round(score, 2),
                    "score_breakdown": score_breakdown,
                    "ram_gb": product.get("ram_gb"),
                    "storage_gb": product.get("storage_gb"),
                    "processor": product.get("processor"),
                    "gpu": product.get("gpu"),
                    "cpu_tier": product.get("cpu_tier"),
                    "gpu_tier": product.get("gpu_tier"),
                    "ram_tier": product.get("ram_tier"),
                    "storage_tier": product.get("storage_tier"),
                    "portability_class": product.get("portability_class"),
                    "network_role": product.get("network_role"),
                    "printer_type": product.get("printer_type"),
                    "print_technology": product.get("print_technology"),
                    "color_output": product.get("color_output"),
                    "print_speed_ppm": product.get("print_speed_ppm"),
                    "monthly_duty_cycle_pages": product.get("monthly_duty_cycle_pages"),
                    "duplex_printing": product.get("duplex_printing"),
                    "scanner_type": product.get("scanner_type"),
                    "automatic_document_feeder": product.get("automatic_document_feeder"),
                    "paper_size_support": list(product.get("paper_size_support") or []),
                    "accessory_type": product.get("accessory_type"),
                    "connectivity": product.get("connectivity"),
                    "port_count": product.get("port_count"),
                    "vpn_user_capacity": product.get("vpn_user_capacity"),
                    "throughput_mbps": product.get("throughput_mbps"),
                    "poe_supported": product.get("poe_supported"),
                    "poe_port_count": product.get("poe_port_count"),
                    "virtualization_ready": product.get("virtualization_ready"),
                    "virtualization_platforms": product.get("virtualization_platforms"),
                    "rack_units": product.get("rack_units"),
                    "power_draw_watts": product.get("power_draw_watts"),
                    "remote_management": product.get("remote_management"),
                    "high_availability_ready": product.get("high_availability_ready"),
                    "seller": product.get("seller"),
                    "return_policy": product.get("return_policy"),
                    "warranty_years": product.get("warranty_years"),
                    "support_score": product.get("support_score"),
                    "inventory_stale": bool(product.get("inventory_stale")),
                    "readiness_state": product.get("readiness_state"),
                    "offer_count": int(product.get("offer_count") or 0),
                    "parse_warnings": list(product.get("parse_warnings") or []),
                    "missing_critical_fields": list(product.get("missing_critical_fields") or []),
                    "alternate_offer_count": int(product.get("alternate_offer_count") or 0),
                    "currency_fallback_used": bool(product.get("currency_fallback_used")),
                    "estimated_quantity": quantity,
                    "estimated_total_cost": total_cost,
                    "budget_scope": requirements.get("budget_scope"),
                    "ranking_persona": ranking_persona,
                    "fit_status": self._fit_status(score_breakdown, product, quantity),
                    "reasons": reasons,
                    "trade-off": [],
                }
            )

        if not ranked and products:
            for product in products:
                availability_score, reasons = self._availability_score(
                    product,
                    availability_need=requirements.get("availability_need"),
                )
                quantity = self._determine_quantity(product, target_profile)
                total_cost = self._estimate_total_cost(product, quantity)
                constraint_alignment_component, alignment_reasons = self._constraint_alignment_component(product, requirements)
                fallback_alignment_score = constraint_alignment_component * self.config_service.get_ranking_config()["constraint_alignment_scoring"]["fallback_points_multiplier"]
                persona_score, persona_reasons = self._persona_score(
                    product,
                    requirements,
                    target_profile,
                    quantity,
                    total_cost,
                )
                ranked.append(
                    {
                        "product_id": product.get("base_product_id") or product.get("id"),
                        "candidate_id": product.get("id"),
                        "inventory_id": product.get("inventory_id"),
                        "sku_id": product.get("sku_id"),
                        "store_id": product.get("store_id"),
                        "name": product.get("name"),
                        "category": product.get("category"),
                        "manufacturer": product.get("manufacturer"),
                        "image": product.get("image"),
                        "avg_rating": product.get("avg_rating"),
                        "reviews_rating": product.get("reviews_rating"),
                        "no_of_reviews": product.get("review_count"),
                        "currency": product.get("currency"),
                        "price": product.get("price"),
                        "stock_quantity": product.get("stock_quantity"),
                        "score": round(availability_score + fallback_alignment_score + persona_score, 2),
                        "score_breakdown": {
                            "category": 0,
                            "price": 0,
                            "specs": 0,
                            "availability": availability_score,
                            "constraint_alignment": round(constraint_alignment_component, 4),
                            "support": 0,
                            "reviews": 0,
                            "persona": persona_score,
                            "portability": 0,
                            "store": 0,
                        },
                        "ram_gb": product.get("ram_gb"),
                        "storage_gb": product.get("storage_gb"),
                        "processor": product.get("processor"),
                        "gpu": product.get("gpu"),
                        "cpu_tier": product.get("cpu_tier"),
                        "gpu_tier": product.get("gpu_tier"),
                        "ram_tier": product.get("ram_tier"),
                        "storage_tier": product.get("storage_tier"),
                        "portability_class": product.get("portability_class"),
                        "network_role": product.get("network_role"),
                        "printer_type": product.get("printer_type"),
                        "print_technology": product.get("print_technology"),
                        "color_output": product.get("color_output"),
                        "print_speed_ppm": product.get("print_speed_ppm"),
                        "monthly_duty_cycle_pages": product.get("monthly_duty_cycle_pages"),
                        "duplex_printing": product.get("duplex_printing"),
                        "scanner_type": product.get("scanner_type"),
                        "automatic_document_feeder": product.get("automatic_document_feeder"),
                        "paper_size_support": list(product.get("paper_size_support") or []),
                        "accessory_type": product.get("accessory_type"),
                        "connectivity": product.get("connectivity"),
                        "port_count": product.get("port_count"),
                        "vpn_user_capacity": product.get("vpn_user_capacity"),
                        "throughput_mbps": product.get("throughput_mbps"),
                        "poe_supported": product.get("poe_supported"),
                        "poe_port_count": product.get("poe_port_count"),
                        "virtualization_ready": product.get("virtualization_ready"),
                        "virtualization_platforms": product.get("virtualization_platforms"),
                        "rack_units": product.get("rack_units"),
                        "power_draw_watts": product.get("power_draw_watts"),
                        "remote_management": product.get("remote_management"),
                        "high_availability_ready": product.get("high_availability_ready"),
                        "seller": product.get("seller"),
                        "return_policy": product.get("return_policy"),
                        "warranty_years": product.get("warranty_years"),
                        "support_score": product.get("support_score"),
                        "inventory_stale": bool(product.get("inventory_stale")),
                        "readiness_state": product.get("readiness_state"),
                        "offer_count": int(product.get("offer_count") or 0),
                        "parse_warnings": list(product.get("parse_warnings") or []),
                        "missing_critical_fields": list(product.get("missing_critical_fields") or []),
                        "alternate_offer_count": int(product.get("alternate_offer_count") or 0),
                        "currency_fallback_used": bool(product.get("currency_fallback_used")),
                        "estimated_quantity": quantity,
                        "estimated_total_cost": total_cost,
                        "budget_scope": requirements.get("budget_scope"),
                        "ranking_persona": ranking_persona,
                        "fit_status": self._fit_status({"availability": availability_score}, product, quantity, fallback=True),
                        "reasons": reasons + alignment_reasons + persona_reasons + ["Fallback ranking used because no strong category match was found."],
                        "trade-off": ["Fallback ranking used because no strong category match was found."],
                    }
                )

        ranked = self._dedupe_product_offers(ranked)
        ranked.sort(key=self._final_ranking_sort_key)
        return ranked[:limit]

    def _score_product(self, product, requirements, target_profile, allowed_categories):
        reasons = []
        score_breakdown = {
            "category": 0,
            "price": 0,
            "specs": 0,
            "availability": 0,
            "constraint_alignment": 0,
            "support": 0,
            "reviews": 0,
            "persona": 0,
            "portability": 0,
            "store": 0,
        }
        category_component = self._category_component(product, allowed_categories)
        if category_component is None:
            return None, [], score_breakdown, 0, None
        score_breakdown["category"] = round(category_component, 4)
        reasons.append("Category match aligns with the resolved recommendation scope.")

        quantity = self._determine_quantity(product, target_profile)
        total_cost = self._estimate_total_cost(product, quantity)
        price_score, price_reason = self._price_score(
            product,
            requirements.get("budget"),
            requirements.get("budget_scope"),
            quantity,
            total_cost,
        )
        budget_component, budget_penalty = self._budget_component(
            product,
            requirements.get("budget"),
            requirements.get("budget_scope"),
            quantity,
            total_cost,
        )
        score_breakdown["price"] = round(budget_component, 4)
        if price_reason:
            reasons.append(price_reason)

        spec_score, spec_reasons = self._spec_score(product, target_profile, requirements)
        spec_component = self._spec_component(product, target_profile)
        score_breakdown["specs"] = round(spec_component, 4)
        reasons.extend(spec_reasons)

        availability_score, availability_reasons = self._availability_score(
            product,
            quantity,
            requirements.get("availability_need"),
        )
        availability_component, availability_penalty = self._availability_component(
            product,
            quantity,
            requirements.get("availability_need"),
        )
        score_breakdown["availability"] = round(availability_component, 4)
        reasons.extend(availability_reasons)

        constraint_alignment_component, alignment_reasons = self._constraint_alignment_component(product, requirements)
        score_breakdown["constraint_alignment"] = round(constraint_alignment_component, 4)
        reasons.extend(alignment_reasons)

        support_score, support_reasons = self._support_score(product, target_profile)
        support_component = self._support_component(product, target_profile)
        score_breakdown["support"] = round(support_component, 4)
        reasons.extend(support_reasons)

        review_score, review_reasons = self._review_score(product)
        review_component = self._review_component(product)
        score_breakdown["reviews"] = round(review_component, 4)
        reasons.extend(review_reasons)

        persona_score, persona_reasons = self._persona_score(
            product,
            requirements,
            target_profile,
            quantity,
            total_cost,
        )
        persona_boost = self._persona_boost(persona_score)
        score_breakdown["persona"] = round(persona_boost, 4)
        reasons.extend(persona_reasons)

        portability_score, portability_reasons = self._portability_score(product, requirements)
        portability_component = self._portability_component(product, requirements)
        score_breakdown["portability"] = round(portability_component, 4)
        reasons.extend(portability_reasons)

        store_boost = 0

        mode_weights = self._mode_weights(requirements)
        weighted_score = (
            mode_weights["fit"] * category_component
            + mode_weights["budget"] * budget_component
            + mode_weights["spec"] * spec_component
            + mode_weights["availability"] * availability_component
            + mode_weights["constraint_alignment"] * constraint_alignment_component
            + mode_weights["support"] * support_component
        )
        penalty_total = (
            budget_penalty
            + availability_penalty
            + self._compatibility_penalty(product)
            + self._missing_metadata_penalty(product)
        )
        boost_total = persona_boost + portability_component + self._review_boost(review_score) + store_boost
        final_score = max(min(weighted_score - penalty_total + boost_total, 1.0), 0.0)

        return round(final_score * 100, 2), reasons, score_breakdown, quantity, total_cost

    def _category_score(self, product, allowed_categories):
        category = product.get("category")
        category_scores = self.config_service.get_ranking_config()["category_scores"]
        if not allowed_categories:
            return category_scores["no_filter"]
        if category in allowed_categories:
            return category_scores["exact_match"]
        return None

    def _category_component(self, product, allowed_categories):
        if not allowed_categories:
            return 0.6
        if product.get("category") in allowed_categories:
            return 1.0
        return None

    def _price_score(self, product, budget, budget_scope, quantity, total_cost):
        price = product.get("price")
        price_scoring = self.config_service.get_ranking_config()["price_scoring"]
        if budget is None or price is None:
            return price_scoring["neutral_missing"], "Budget or price was incomplete, so price fit used a neutral score."

        budget_reference = self._budget_reference(price, budget_scope, quantity, total_cost)
        if budget_reference is None:
            return price_scoring["neutral_missing"], "Budget scope remained unresolved, so price fit stayed neutral until clarified."

        if budget_reference <= budget:
            headroom_ratio = max(budget - budget_reference, 0) / max(budget, 1)
            within_budget_score = price_scoring["within_budget_base"] - min(
                headroom_ratio * price_scoring["within_budget_headroom_cap"],
                price_scoring["within_budget_headroom_cap"],
            )
            return within_budget_score, "Stays within the stated budget."
        if budget_reference <= budget * price_scoring["close_threshold_ratio"]:
            return price_scoring["close_score"], "Slightly above budget but still close enough to consider."
        if budget_reference <= budget * price_scoring["stretch_threshold_ratio"]:
            return price_scoring["stretch_score"], "Above budget, so this was retained only as a stretch option."
        if budget_scope == "project_total" and quantity > 1:
            return price_scoring["over_budget_score"], "Penalized because the estimated deployment cost is materially above budget."
        return price_scoring["over_budget_score"], "Penalized for being materially above budget."

    def _budget_component(self, product, budget, budget_scope, quantity, total_cost):
        price = product.get("price")
        if budget is None or price is None:
            return 0.5, 0.0
        budget_reference = self._budget_reference(price, budget_scope, quantity, total_cost)
        if budget_reference is None:
            return 0.5, 0.0
        penalties = self.config_service.get_ranking_config()["normalized_penalties"]["stretch_budget"]
        if budget_reference <= budget:
            headroom_ratio = max(budget - budget_reference, 0) / max(budget, 1)
            return max(0.7, 1.0 - (headroom_ratio * 0.2)), 0.0
        if budget_reference <= budget * 1.15:
            return 0.7, penalties["close"]
        if budget_reference <= budget * 1.3:
            return 0.4, penalties["stretch"]
        return 0.1, penalties["far"]

    def _spec_score(self, product, target_profile, requirements):
        category = product.get("category")
        spec_scoring = self.config_service.get_ranking_config()["spec_scoring"]
        if category == "networking":
            return spec_scoring["networking_score"], ["Networking category relied more on category and availability than device specs."]
        if category == "printers":
            return self._printer_spec_score(product, target_profile)
        if category == "accessories":
            return self._accessory_spec_score(product, target_profile)

        score = 0
        reasons = []

        min_ram_gb = target_profile.get("min_ram_gb") or 0
        if min_ram_gb:
            ram_gb = product.get("ram_gb") or 0
            if ram_gb >= min_ram_gb:
                score += spec_scoring["ram"]["meet"]
                reasons.append(f"RAM meets the target at {ram_gb}GB.")
            elif ram_gb >= max(min_ram_gb - spec_scoring["ram"]["near_delta_gb"], 0):
                score += spec_scoring["ram"]["near"]
                reasons.append(f"RAM is slightly below target at {ram_gb}GB.")
            else:
                score += spec_scoring["ram"]["miss"]
                reasons.append("RAM is under the target profile.")

        min_storage_gb = target_profile.get("min_storage_gb") or 0
        if min_storage_gb:
            storage_gb = product.get("storage_gb") or 0
            if storage_gb >= min_storage_gb:
                score += spec_scoring["storage"]["meet"]
                reasons.append(f"Storage meets the target at {storage_gb}GB.")
            elif storage_gb >= max(min_storage_gb - spec_scoring["storage"]["near_delta_gb"], 0):
                score += spec_scoring["storage"]["near"]
                reasons.append(f"Storage is slightly below target at {storage_gb}GB.")
            else:
                score += spec_scoring["storage"]["miss"]
                reasons.append("Storage is under the target profile.")

        cpu_score = product.get("cpu_score") or 0
        if cpu_score >= (target_profile.get("min_cpu_score") or 0):
            score += spec_scoring["cpu"]["meet"]
            reasons.append("Processor tier matches the workload target.")
        else:
            score += spec_scoring["cpu"]["miss"]
            reasons.append("Processor tier is lighter than the workload target.")

        min_gpu_tier = target_profile.get("min_gpu_tier") or "integrated"
        product_gpu_tier = product.get("gpu_tier") or "integrated"
        if self.GPU_TIER_ORDER.get(product_gpu_tier, 1) >= self.GPU_TIER_ORDER.get(min_gpu_tier, 1):
            score += spec_scoring["gpu"]["meet"]
            reasons.append(f"Graphics capability aligns with the expected workload at {product_gpu_tier} tier.")
        else:
            score += spec_scoring["gpu"]["miss"]
            reasons.append("Graphics capability is below the expected workload tier.")

        preferred_ram_gb = target_profile.get("preferred_ram_gb") or 0
        if preferred_ram_gb and (product.get("ram_gb") or 0) >= preferred_ram_gb:
            score += spec_scoring["preferred_ram_bonus"]
            reasons.append(f"RAM also aligns with the preferred {preferred_ram_gb}GB target.")

        preferred_storage_gb = target_profile.get("preferred_storage_gb") or 0
        if preferred_storage_gb and (product.get("storage_gb") or 0) >= preferred_storage_gb:
            score += spec_scoring["preferred_storage_bonus"]
            reasons.append(f"Storage also aligns with the preferred {preferred_storage_gb}GB target.")

        return score, reasons

    def _spec_component(self, product, target_profile):
        category = product.get("category")
        if category == "networking":
            components = []
            min_cpu_score = target_profile.get("min_cpu_score") or 0
            if min_cpu_score:
                components.append(1.0 if (product.get("cpu_score") or 0) >= min_cpu_score else 0.4)
            min_support_score = target_profile.get("min_support_score") or 0
            if min_support_score:
                components.append(1.0 if (product.get("support_score") or 0) >= min_support_score else 0.5)
            return round(sum(components) / max(len(components), 1), 4) if components else 0.75
        if category == "printers":
            return self._printer_spec_component(product, target_profile)
        if category == "accessories":
            return self._accessory_spec_component(product, target_profile)

        components = []
        for current_value, required_value in (
            (product.get("ram_gb") or 0, target_profile.get("min_ram_gb") or 0),
            (product.get("storage_gb") or 0, target_profile.get("min_storage_gb") or 0),
            (product.get("cpu_score") or 0, target_profile.get("min_cpu_score") or 0),
        ):
            if not required_value:
                continue
            if current_value >= required_value:
                components.append(1.0)
            else:
                components.append(max(current_value / max(required_value, 1), 0.0))

        required_gpu = target_profile.get("min_gpu_tier") or "integrated"
        current_gpu_value = self.GPU_TIER_ORDER.get(product.get("gpu_tier") or "integrated", 1)
        required_gpu_value = self.GPU_TIER_ORDER.get(required_gpu, 1)
        if required_gpu_value > 0:
            components.append(min(current_gpu_value / max(required_gpu_value, 1), 1.0))

        return round(sum(components) / max(len(components), 1), 4) if components else 0.6

    def _availability_score(self, product, quantity=1, availability_need=None):
        stock_quantity = product.get("stock_quantity")
        availability_scoring = self.config_service.get_ranking_config()["availability_scoring"]
        if stock_quantity is None:
            return availability_scoring["unknown"], ["Inventory quantity is not explicit, so availability was treated as neutral."]
        quantity = max(int(quantity or 1), 1)
        extra_score = 0
        extra_reasons = []
        availability_need = str(availability_need or "").strip().lower()
        if stock_quantity >= quantity:
            if quantity > 1:
                base_reasons = [f"Inventory can cover the estimated {quantity}-unit rollout with {stock_quantity} units on hand."]
            else:
                base_reasons = [f"Inventory looks available with {stock_quantity} units on hand."]
            if availability_need == "in_stock_now":
                extra_score += availability_scoring["in_stock_now_bonus"]
                extra_reasons.append("Explicit in-stock-now requirement is satisfied.")
            elif availability_need == "urgent" and product.get("quick_inventory"):
                extra_score += availability_scoring["urgent_quick_inventory_bonus"]
                extra_reasons.append("Urgent availability requirement is helped by quick inventory handling.")
            elif availability_need == "soon":
                extra_score += availability_scoring["soon_bonus"]
                extra_reasons.append("Availability timing looks reasonable for a near-term purchase.")
            return availability_scoring["full_rollout"] + extra_score, base_reasons + extra_reasons
        if stock_quantity > 0:
            if quantity <= 1:
                base_score = availability_scoring["single_unit_available"]
                base_reasons = [f"Inventory shows only {stock_quantity} units, but at least one unit is available."]
                if availability_need in {"urgent", "in_stock_now"}:
                    base_score += availability_scoring["urgent_partial_penalty"]
                    base_reasons.append("Urgent availability is only partially satisfied.")
                return base_score, base_reasons
            coverage_ratio = stock_quantity / max(quantity, 1)
            if coverage_ratio >= availability_scoring["high_coverage_threshold"]:
                base_score = availability_scoring["high_coverage_score"]
                base_reasons = [f"Only {stock_quantity} units are currently available against an estimated need of {quantity}."]
                if availability_need in {"urgent", "in_stock_now"}:
                    base_score += availability_scoring["urgent_partial_penalty"]
                    base_reasons.append("Urgent availability is weaker because the rollout would be split.")
                return base_score, base_reasons
            if coverage_ratio >= availability_scoring["medium_coverage_threshold"]:
                return availability_scoring["medium_coverage_score"], [f"Inventory covers only part of the rollout: {stock_quantity} of {quantity} estimated units."]
            return availability_scoring["severe_shortage_score"], [f"Inventory is materially short for the rollout: {stock_quantity} of {quantity} estimated units."]
        reasons = ["Inventory appears empty, so this option was heavily penalized."]
        if availability_need in {"urgent", "in_stock_now"}:
            reasons.append("This directly conflicts with the stated availability requirement.")
        return availability_scoring["empty_score"], reasons

    def _availability_component(self, product, quantity=1, availability_need=None):
        stock_quantity = product.get("stock_quantity")
        quantity = max(int(quantity or 1), 1)
        penalties = self.config_service.get_ranking_config()["normalized_penalties"]["partial_rollout_stock"]
        if stock_quantity is None:
            return 0.5, 0.0
        stock_quantity = int(stock_quantity or 0)
        if stock_quantity >= quantity:
            return 1.0, 0.0
        if stock_quantity <= 0:
            return 0.0, penalties["low"]
        coverage_ratio = stock_quantity / max(quantity, 1)
        if coverage_ratio >= 0.75:
            return 0.9, penalties["high"]
        if coverage_ratio >= 0.5:
            return 0.45, penalties["medium"]
        return 0.15, penalties["low"]

    def _preference_alignment_flags(self, product, requirements):
        manufacturer = str(product.get("manufacturer") or "").strip().lower()
        seller = str(product.get("seller") or "").strip().lower()
        preferred_manufacturers = self._request_values(requirements.get("preferred_manufacturers"))
        preferred_sellers = self._request_values(requirements.get("preferred_sellers"))
        blocked_manufacturers = self._request_values(requirements.get("blocked_manufacturers"))
        blocked_sellers = self._request_values(requirements.get("blocked_sellers"))
        return {
            "has_preferences": bool(
                preferred_manufacturers or preferred_sellers or blocked_manufacturers or blocked_sellers
            ),
            "manufacturer_match": bool(manufacturer and manufacturer in preferred_manufacturers),
            "seller_match": bool(seller and seller in preferred_sellers),
            "manufacturer_blocked": bool(manufacturer and manufacturer in blocked_manufacturers),
            "seller_blocked": bool(seller and seller in blocked_sellers),
        }

    def _constraint_alignment_component(self, product, requirements):
        alignment_cfg = self.config_service.get_ranking_config()["constraint_alignment_scoring"]
        flags = self._preference_alignment_flags(product, requirements)
        if not flags["has_preferences"]:
            return round(alignment_cfg["neutral_component"], 4), []

        component = alignment_cfg["preference_floor"]
        reasons = []
        if flags["manufacturer_blocked"]:
            component -= 0.5
            reasons.append("Blocked manufacturer penalty applied.")
        if flags["seller_blocked"]:
            component -= 0.5
            reasons.append("Blocked seller penalty applied.")
        if flags["manufacturer_match"]:
            component += alignment_cfg["preferred_manufacturer_match"]
            reasons.append("Manufacturer matches the buyer's preferred brand list.")
        if flags["seller_match"]:
            component += alignment_cfg["preferred_seller_match"]
            reasons.append("Seller matches the buyer's preferred seller list.")
        if flags["manufacturer_match"] and flags["seller_match"]:
            component += alignment_cfg["preferred_both_bonus"]
        if not reasons:
            reasons.append("Explicit brand or seller preferences were supplied, but this offer did not align with them.")
        return max(min(round(component, 4), 1.0), -1.0), reasons

    def _support_score(self, product, target_profile):
        support_scoring = self.config_service.get_ranking_config()["support_scoring"]
        required_support = int(target_profile.get("min_support_score") or 0)
        required_warranty_years = int(target_profile.get("min_warranty_years") or 0)
        support_score = int(product.get("support_score") or 0)
        warranty_years = int(product.get("warranty_years") or 0)
        score = 0
        reasons = []

        if required_support:
            if support_score >= required_support:
                score += support_scoring["support_meet"]
                reasons.append("Support level matches the expectation for business continuity.")
            else:
                score += support_scoring["support_miss"]
                reasons.append("Support coverage looks lighter than the requested expectation.")

        if required_warranty_years:
            if warranty_years >= required_warranty_years:
                score += support_scoring["warranty_meet"]
                reasons.append(f"Warranty duration meets the {required_warranty_years}-year expectation.")
            elif warranty_years > 0:
                score += support_scoring["warranty_miss"]
                reasons.append(f"Warranty duration is shorter than the {required_warranty_years}-year expectation.")
            else:
                score += support_scoring["warranty_unclear"]
                reasons.append("Warranty duration is not clear enough to validate the requested support expectation.")

        return score, reasons

    def _support_component(self, product, target_profile):
        required_support = int(target_profile.get("min_support_score") or 0)
        required_warranty_years = int(target_profile.get("min_warranty_years") or 0)
        support_score = int(product.get("support_score") or 0)
        warranty_years = int(product.get("warranty_years") or 0)
        if not required_support and not required_warranty_years:
            return 0.5
        parts = []
        if required_support:
            parts.append(min(support_score / max(required_support, 1), 1.0))
        if required_warranty_years:
            parts.append(min(warranty_years / max(required_warranty_years, 1), 1.0))
        return round(sum(parts) / max(len(parts), 1), 4)

    def _review_score(self, product):
        rating = float(product.get("avg_rating") or product.get("reviews_rating") or 0)
        reviews = int(product.get("review_count") or product.get("no_of_reviews") or 0)
        if not rating or not reviews:
            return 0.0, []
        review_weight = min(reviews / 50, 1.0)
        rating_normalized = max((rating - 3.0) / 2.0, 0.0)
        score = round(rating_normalized * review_weight * 3.0, 4)
        if score <= 0:
            return 0.0, []
        return score, ["Strong review quality improved confidence in this option."]

    def _review_component(self, product):
        score, _ = self._review_score(product)
        return round(min(score / 3.0, 1.0), 4) if score else 0.0

    def _review_boost(self, review_score):
        if not review_score:
            return 0.0
        return max(min(round(review_score / 100, 4), 0.03), 0.0)

    def _persona_score(self, product, requirements, target_profile, quantity, total_cost):
        persona = str(requirements.get("ranking_persona") or "balanced").strip().lower()
        if persona == "balanced":
            return 0, []
        persona_scoring = self.config_service.get_ranking_config()["persona_scoring"]

        price = product.get("price")
        budget = requirements.get("budget")
        budget_scope = requirements.get("budget_scope")
        cost_reference = self._budget_reference(price, budget_scope, quantity, total_cost)
        support_score = int(product.get("support_score") or 0)
        warranty_years = int(product.get("warranty_years") or 0)
        stock_quantity = int(product.get("stock_quantity") or 0)
        quick_inventory = bool(product.get("quick_inventory"))
        required_support = int(target_profile.get("min_support_score") or 0)
        required_warranty = int(target_profile.get("min_warranty_years") or 0)

        if persona == "finance-first":
            finance_cfg = persona_scoring["finance-first"]
            if budget and cost_reference is not None:
                if cost_reference <= budget:
                    savings_ratio = max(budget - cost_reference, 0) / max(budget, 1)
                    bonus = min(round(savings_ratio * finance_cfg["savings_scale"], 2), finance_cfg["max_bonus"])
                    if bonus > 0:
                        return bonus, ["Finance-first weighting rewarded stronger cost headroom inside budget."]
                    return finance_cfg["near_budget_score"], ["Finance-first weighting kept this option neutral because it sits close to the budget."]
                return finance_cfg["over_budget_penalty"], ["Finance-first weighting penalized the budget overrun."]
            if price is not None:
                threshold = finance_cfg["low_price_threshold"]
                bonus = finance_cfg["low_price_bonus"]
                return bonus if price <= threshold else 0, ["Finance-first weighting favored a lower unit price."] if price <= threshold else []
            return 0, []

        if persona == "performance-first":
            performance_cfg = persona_scoring["performance-first"]
            score = 0
            score += min(
                max((product.get("ram_gb") or 0) - (target_profile.get("min_ram_gb") or 0), 0) / performance_cfg["ram_divisor"],
                performance_cfg["ram_cap"],
            ) * performance_cfg["ram_multiplier"]
            score += min(
                max((product.get("storage_gb") or 0) - (target_profile.get("min_storage_gb") or 0), 0) / performance_cfg["storage_divisor"],
                performance_cfg["storage_cap"],
            ) * performance_cfg["storage_multiplier"]
            score += max((product.get("cpu_score") or 0) - (target_profile.get("min_cpu_score") or 0), 0) * performance_cfg["cpu_multiplier"]
            score += max(
                self.GPU_TIER_ORDER.get(product.get("gpu_tier") or "integrated", 1)
                - self.GPU_TIER_ORDER.get(target_profile.get("min_gpu_tier") or "integrated", 1),
                0,
            ) * performance_cfg["gpu_multiplier"]
            score = min(round(score, 2), performance_cfg["max_bonus"])
            if score > 0:
                return score, ["Performance-first weighting rewarded extra compute headroom above the minimum target."]
            return 0, []

        if persona == "support-first":
            support_cfg = persona_scoring["support-first"]
            score = 0
            if support_score:
                score += max(support_score - max(required_support, 2), 0) * support_cfg["support_multiplier"]
            if warranty_years:
                score += max(warranty_years - max(required_warranty, 1), 0) * support_cfg["warranty_multiplier"]
            score = min(round(score, 2), support_cfg["max_bonus"])
            if score > 0:
                return score, ["Support-first weighting rewarded stronger warranty and support coverage."]
            if required_support or required_warranty:
                return support_cfg["no_headroom_penalty"], ["Support-first weighting could not find strong support headroom beyond the minimum expectation."]
            return 0, []

        if persona == "standardization-first":
            standardization_cfg = persona_scoring["standardization-first"]
            score = 0
            alignment_flags = self._preference_alignment_flags(product, requirements)
            if alignment_flags["manufacturer_match"]:
                score += standardization_cfg["preferred_manufacturer_bonus"]
            if alignment_flags["seller_match"]:
                score += standardization_cfg["preferred_seller_bonus"]
            if (product.get("seller") or "").strip():
                score += standardization_cfg["seller_bonus"]
            score = min(score, standardization_cfg["max_bonus"])
            if score > 0:
                return score, ["Standardization-first weighting favored explicit brand or seller preferences and clearly attributable offers."]
            return 0, []

        if persona == "availability-first":
            availability_cfg = persona_scoring["availability-first"]
            quantity = max(int(quantity or 1), 1)
            if stock_quantity >= quantity:
                score = availability_cfg["full_rollout_base"] + (availability_cfg["quick_inventory_bonus"] if quick_inventory else 0)
                return score, ["Availability-first weighting rewarded inventory that can cover the rollout immediately."]
            if stock_quantity > 0:
                coverage_ratio = stock_quantity / max(quantity, 1)
                if coverage_ratio >= self.config_service.get_ranking_config()["availability_scoring"]["high_coverage_threshold"]:
                    return availability_cfg["mostly_covered_bonus"], ["Availability-first weighting kept this option in play because stock covers most of the rollout."]
                return availability_cfg["partial_penalty"], ["Availability-first weighting penalized partial inventory coverage for the rollout."]
            return availability_cfg["empty_penalty"], ["Availability-first weighting penalized the lack of available inventory."]

        return 0, []

    def _persona_boost(self, persona_score):
        if not persona_score:
            return 0.0
        return max(min(round(persona_score / 100, 4), 0.08), -0.08)

    def _portability_score(self, product, requirements):
        portability_scoring = self.config_service.get_ranking_config()["portability_scoring"]
        desired = requirements.get("portability_need")
        category = product.get("category")
        portability_class = product.get("portability_class")
        if not desired or category != "laptops":
            return 0, []
        if desired == "high" and portability_class == "ultra_portable":
            return portability_scoring["high_ultra_portable"], ["Portability needs are well served by a lighter laptop class."]
        if desired == "low" and portability_class == "desk_friendly":
            return portability_scoring["low_desk_friendly"], ["A heavier device is acceptable for mostly desk-based use."]
        if desired == "medium" and portability_class in {"portable", "ultra_portable"}:
            return portability_scoring["medium_portable"], ["Portability is reasonably aligned with a mixed-use deployment."]
        return portability_scoring["mismatch"], ["Portability is not an especially strong match for the stated deployment style."]

    def _portability_component(self, product, requirements):
        desired = requirements.get("portability_need")
        category = product.get("category")
        portability_class = product.get("portability_class")
        if not desired or category != "laptops":
            return 0.0
        if desired == "high" and portability_class == "ultra_portable":
            return 0.03
        if desired == "medium" and portability_class in {"portable", "ultra_portable"}:
            return 0.02
        if desired == "low" and portability_class == "desk_friendly":
            return 0.01
        return 0.0

    def _mode_weights(self, requirements):
        mode_key = str(requirements.get("performance_priority") or "balanced").strip().lower()
        if mode_key not in {"balanced", "cost", "performance"}:
            mode_key = "balanced"
        return self.config_service.get_ranking_config()["mode_weights"][mode_key]

    def _compatibility_penalty(self, product):
        warnings = list(product.get("compatibility_warnings") or [])
        if not warnings:
            return 0.0
        penalty_cfg = self.config_service.get_ranking_config()["normalized_penalties"]["soft_compatibility_warning"]
        return min(len(warnings) * penalty_cfg["per_warning"], penalty_cfg["cap"])

    def _missing_metadata_penalty(self, product):
        metadata_validation = dict(product.get("metadata_validation") or {})
        missing_fields = len(metadata_validation.get("missing_noncritical_fields") or [])
        if not missing_fields:
            for key in ("ram_gb", "storage_gb", "processor", "gpu", "support_score"):
                if product.get(key) in {None, "", 0}:
                    missing_fields += 1
        penalty_cfg = self.config_service.get_ranking_config()["normalized_penalties"]["missing_noncritical_metadata"]
        return min(missing_fields * penalty_cfg["per_field"], penalty_cfg["cap"])

    def _determine_quantity(self, product, target_profile):
        category = product.get("category")
        recommended_quantity = int(target_profile.get("recommended_quantity") or 1)
        if category in {"laptops", "desktops", "accessories"}:
            return max(recommended_quantity, 1)
        return 1

    def _printer_spec_score(self, product, target_profile):
        reasons = []
        score = 0

        required_type = str(target_profile.get("required_printer_type") or "").strip().lower()
        if required_type:
            if str(product.get("printer_type") or "").strip().lower() == required_type:
                score += 0.25
                reasons.append("Printer type aligns with the requested deployment style.")
            else:
                score -= 0.1
                reasons.append("Printer subtype is different from the requested printer role.")

        required_technology = str(target_profile.get("required_print_technology") or "").strip().lower()
        if required_technology:
            if required_technology in str(product.get("print_technology") or "").strip().lower():
                score += 0.15
                reasons.append("Print technology matches the requested preference.")
            else:
                reasons.append("Print technology differs from the requested preference.")

        required_color = str(target_profile.get("required_color_output") or "").strip().lower()
        if required_color:
            if str(product.get("color_output") or "").strip().lower() == required_color:
                score += 0.15
                reasons.append("Color output matches the request.")
            else:
                reasons.append("Color output does not match the requested output mode.")

        min_speed = int(target_profile.get("min_print_speed_ppm") or 0)
        if min_speed:
            current_speed = int(product.get("print_speed_ppm") or 0)
            if current_speed >= min_speed:
                score += 0.2
                reasons.append(f"Print speed meets the target at about {current_speed} ppm.")
            else:
                reasons.append(f"Print speed is below the target at about {current_speed or 'unknown'} ppm.")

        min_duty_cycle = int(target_profile.get("min_monthly_duty_cycle_pages") or 0)
        if min_duty_cycle:
            current_duty_cycle = int(product.get("monthly_duty_cycle_pages") or 0)
            if current_duty_cycle >= min_duty_cycle:
                score += 0.15
                reasons.append("Monthly duty cycle aligns with the expected print volume.")
            else:
                reasons.append("Monthly duty cycle is lighter than the expected print volume.")

        if target_profile.get("required_duplex_printing"):
            if product.get("duplex_printing"):
                score += 0.1
                reasons.append("Automatic duplex printing is available.")
            else:
                reasons.append("Automatic duplex printing is missing.")

        if target_profile.get("required_scanner"):
            if str(product.get("scanner_type") or "").strip():
                score += 0.1
                reasons.append("Scanning support is present for the requested workflow.")
            else:
                reasons.append("Scanning support is not explicit in the current configuration.")

        if target_profile.get("required_automatic_document_feeder"):
            if product.get("automatic_document_feeder"):
                score += 0.1
                reasons.append("Automatic document feeder support is available.")
            else:
                reasons.append("Automatic document feeder support is missing.")

        if not reasons:
            reasons.append("Printer fit relied on category, availability, and the available print metadata.")
        return score, reasons

    def _printer_spec_component(self, product, target_profile):
        components = []

        required_type = str(target_profile.get("required_printer_type") or "").strip().lower()
        if required_type:
            components.append(1.0 if str(product.get("printer_type") or "").strip().lower() == required_type else 0.0)

        required_technology = str(target_profile.get("required_print_technology") or "").strip().lower()
        if required_technology:
            current = str(product.get("print_technology") or "").strip().lower()
            components.append(1.0 if required_technology in current else 0.0)

        required_color = str(target_profile.get("required_color_output") or "").strip().lower()
        if required_color:
            components.append(1.0 if str(product.get("color_output") or "").strip().lower() == required_color else 0.0)

        min_speed = int(target_profile.get("min_print_speed_ppm") or 0)
        if min_speed:
            components.append(min((product.get("print_speed_ppm") or 0) / max(min_speed, 1), 1.0))

        min_duty_cycle = int(target_profile.get("min_monthly_duty_cycle_pages") or 0)
        if min_duty_cycle:
            components.append(min((product.get("monthly_duty_cycle_pages") or 0) / max(min_duty_cycle, 1), 1.0))

        if target_profile.get("required_duplex_printing"):
            components.append(1.0 if product.get("duplex_printing") else 0.0)
        if target_profile.get("required_scanner"):
            components.append(1.0 if str(product.get("scanner_type") or "").strip() else 0.0)
        if target_profile.get("required_automatic_document_feeder"):
            components.append(1.0 if product.get("automatic_document_feeder") else 0.0)

        return round(sum(components) / max(len(components), 1), 4) if components else 0.75

    def _accessory_spec_score(self, product, target_profile):
        required_type = str(target_profile.get("required_accessory_type") or "").strip().lower()
        current_type = str(product.get("accessory_type") or "").strip().lower()
        if required_type and current_type == required_type:
            return 0.35, ["Accessory family matches the requested end-user peripheral type."]
        if required_type and current_type != required_type:
            return -0.1, ["Accessory family does not match the requested peripheral type."]
        if current_type:
            return 0.2, ["Accessory fit relied on the resolved peripheral family and availability."]
        return 0.0, ["Accessory family was not explicit in the normalized catalog data."]

    def _accessory_spec_component(self, product, target_profile):
        required_type = str(target_profile.get("required_accessory_type") or "").strip().lower()
        current_type = str(product.get("accessory_type") or "").strip().lower()
        if required_type:
            return 1.0 if current_type == required_type else 0.0
        if current_type:
            return 0.8
        return 0.3

    def _estimate_total_cost(self, product, quantity):
        price = product.get("price")
        if price is None:
            return None
        return int(price) * max(int(quantity or 1), 1)

    def _budget_reference(self, price, budget_scope, quantity, total_cost):
        if price is None:
            return None
        quantity = max(int(quantity or 1), 1)
        if budget_scope == "per_unit":
            return price
        if budget_scope == "project_total":
            return total_cost
        if quantity <= 1:
            return price
        return None

    def _request_values(self, values):
        return {
            str(value or "").strip().lower()
            for value in list(values or [])
            if str(value or "").strip()
        }

    def _fit_status(self, score_breakdown, product=None, quantity=1, fallback=False):
        if not score_breakdown:
            return "unknown"
        readiness_state = str((product or {}).get("readiness_state") or "").strip().lower()
        if readiness_state == "insufficient":
            return "partial_fit"
        stock_quantity = None if product is None else product.get("stock_quantity")
        if stock_quantity is not None and int(stock_quantity or 0) < max(int(quantity or 1), 1):
            return "limited_availability"
        if (score_breakdown.get("availability") or 0) < 0.45:
            return "limited_availability"
        if fallback:
            return "fallback"
        if (score_breakdown.get("price") or 0) < 0.5:
            return "stretch"
        if (
            readiness_state == "provisional"
            or (score_breakdown.get("specs") or 0) < 0.6
            or list((product or {}).get("compatibility_warnings") or [])
            or list((product or {}).get("parse_warnings") or [])
        ):
            return "partial_fit"
        return "good_fit"

    def _dedupe_product_offers(self, ranked):
        best_by_product = {}
        for item in ranked or []:
            product_key = item.get("product_id") or item.get("candidate_id")
            current = best_by_product.get(product_key)
            if current is None:
                best_by_product[product_key] = item
                continue
            if self._recommendation_sort_key(item) < self._recommendation_sort_key(current):
                best_by_product[product_key] = item
        return list(best_by_product.values())

    def _recommendation_sort_key(self, item):
        return (
            -(item.get("score") or 0),
            -(item.get("stock_quantity") if item.get("stock_quantity") is not None else -1),
            item.get("price") if item.get("price") is not None else float("inf"),
            str(item.get("name") or ""),
            str(item.get("candidate_id") or ""),
            str(item.get("inventory_id") or ""),
        )

    def _final_ranking_sort_key(self, item):
        return self._recommendation_sort_key(item)

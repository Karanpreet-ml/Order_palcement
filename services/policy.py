import os

from ...catalog.services.hardware_tiers import normalize_gpu_tier
from ...catalog.services.normalization import normalize_warranty_type, parse_screen_size_inches_value, score_cpu_tier
from .config_service import ProcurementConfigService


class ProcurementPolicyService:
    def __init__(self, config_service=None):
        self.config_service = config_service or ProcurementConfigService()

    def apply_filters(self, products, requirements, target_profile):
        eligible_products = []
        rejected_products = []
        allowed_categories = set(target_profile.get("categories") or [])

        for product in products or []:
            reasons = self._reject_reasons(product, requirements, target_profile, allowed_categories)
            if reasons:
                rejected_products.append(
                    {
                        "product_id": product.get("id"),
                        "name": product.get("name"),
                        "category": product.get("category"),
                        "manufacturer": product.get("manufacturer"),
                        "seller": product.get("seller"),
                        "reasons": reasons,
                    }
                )
            else:
                eligible_products.append(product)

        return {
            "eligible_products": eligible_products,
            "rejected_products": rejected_products,
            "summary": {
                "input_count": len(products or []),
                "eligible_count": len(eligible_products),
                "rejected_count": len(rejected_products),
                "budget_enforcement_mode": self.budget_mode(),
                "strict_stock_coverage": self._flag_enabled("STRICT_STOCK_COVERAGE", "strict_stock_coverage"),
                "strict_support_requirements": self._flag_enabled("STRICT_SUPPORT_REQUIREMENTS", "strict_support_requirements"),
                "approved_manufacturer_policy": bool(self._policy_values("APPROVED_MANUFACTURERS", "approved_manufacturers")),
                "approved_seller_policy": bool(self._policy_values("APPROVED_SELLERS", "approved_sellers")),
                "availability_need": requirements.get("availability_need"),
                "require_returnable": bool(requirements.get("require_returnable")),
            },
        }

    def budget_mode(self):
        env_value = str(os.getenv("BUDGET_ENFORCEMENT_MODE", "") or "").strip().lower()
        if env_value:
            return env_value
        return str(self.config_service.get_policy_config().get("budget_enforcement_mode") or "flexible").strip().lower()

    def _reject_reasons(self, product, requirements, target_profile, allowed_categories):
        reasons = []
        category = product.get("category")
        if allowed_categories and category not in allowed_categories:
            reasons.append("Outside the allowed category scope for this requirement.")

        manufacturer = str(product.get("manufacturer") or "").strip().lower()
        seller = str(product.get("seller") or "").strip().lower()
        approved_manufacturers = self._policy_values("APPROVED_MANUFACTURERS", "approved_manufacturers")
        blocked_manufacturers = self._policy_values("BLOCKED_MANUFACTURERS", "blocked_manufacturers")
        approved_sellers = self._policy_values("APPROVED_SELLERS", "approved_sellers")
        blocked_sellers = self._policy_values("BLOCKED_SELLERS", "blocked_sellers")
        requested_blocked_manufacturers = self._request_values(requirements.get("blocked_manufacturers"))
        requested_blocked_sellers = self._request_values(requirements.get("blocked_sellers"))
        requested_preferred_manufacturers = self._request_values(requirements.get("preferred_manufacturers"))
        requested_preferred_sellers = self._request_values(requirements.get("preferred_sellers"))
        enforce_preferred_manufacturers = self._enforce_explicit_preference(
            requirements,
            "preferred_manufacturers",
            requested_preferred_manufacturers,
        )
        enforce_preferred_sellers = self._enforce_explicit_preference(
            requirements,
            "preferred_sellers",
            requested_preferred_sellers,
        )

        if manufacturer and manufacturer in blocked_manufacturers:
            reasons.append("Manufacturer is blocked by procurement policy.")
        elif manufacturer and manufacturer in requested_blocked_manufacturers:
            reasons.append("Manufacturer is blocked by the buyer preference.")
        elif approved_manufacturers and manufacturer not in approved_manufacturers:
            reasons.append("Manufacturer is outside the approved procurement policy.")

        if seller and seller in blocked_sellers:
            reasons.append("Seller is blocked by procurement policy.")
        elif seller and seller in requested_blocked_sellers:
            reasons.append("Seller is blocked by the buyer preference.")
        elif approved_sellers and seller not in approved_sellers:
            reasons.append("Seller is outside the approved procurement policy.")

        if enforce_preferred_manufacturers and manufacturer not in requested_preferred_manufacturers:
            reasons.append("Manufacturer does not match the buyer's explicit preferred brand list.")

        if enforce_preferred_sellers and seller not in requested_preferred_sellers:
            reasons.append("Seller does not match the buyer's explicit preferred seller list.")

        return_policy_reason = self._return_policy_rejection_reason(product, requirements)
        if return_policy_reason:
            reasons.append(return_policy_reason)

        spec_reasons = self._spec_rejection_reasons(product, requirements)
        reasons.extend(spec_reasons)

        availability_reason = self._availability_rejection_reason(product, requirements, target_profile)
        if availability_reason:
            reasons.append(availability_reason)

        if self.budget_mode() == "strict":
            budget_reason = self._budget_rejection_reason(product, requirements, target_profile)
            if budget_reason:
                reasons.append(budget_reason)

        if self._flag_enabled("STRICT_STOCK_COVERAGE", "strict_stock_coverage"):
            stock_reason = self._stock_rejection_reason(product, target_profile)
            if stock_reason:
                reasons.append(stock_reason)

        if self._flag_enabled("STRICT_SUPPORT_REQUIREMENTS", "strict_support_requirements"):
            support_reasons = self._support_rejection_reasons(product, target_profile)
            reasons.extend(support_reasons)

        return reasons

    def _enforce_explicit_preference(self, requirements, field_name, requested_values):
        if not requested_values:
            return False
        field_source = dict(requirements.get("field_source") or {})
        return str(field_source.get(field_name) or "").strip().lower() in {"user_explicit", "context_explicit"}

    def _budget_rejection_reason(self, product, requirements, target_profile):
        budget = requirements.get("budget")
        price = product.get("price")
        if budget is None or price is None:
            return None

        quantity = self._determine_quantity(product, target_profile)
        budget_scope = requirements.get("budget_scope")
        if budget_scope == "per_unit":
            budget_reference = price
        elif budget_scope == "project_total":
            budget_reference = price * quantity
        elif quantity > 1:
            budget_reference = price * quantity
        elif quantity <= 1:
            budget_reference = price
        else:
            return None
        if budget_reference > budget:
            if budget_scope == "per_unit":
                return "Unit price exceeds the strict budget policy."
            if budget_scope not in {"per_unit", "project_total"} and quantity > 1:
                return "Budget scope was unresolved, so strict policy used estimated rollout cost conservatively."
            return "Estimated rollout cost exceeds the strict budget policy."
        return None

    def _stock_rejection_reason(self, product, target_profile):
        stock_quantity = product.get("stock_quantity")
        quantity = self._determine_quantity(product, target_profile)
        if stock_quantity is None:
            return "Inventory quantity is unclear, so strict stock coverage could not be validated."
        if int(stock_quantity or 0) < quantity:
            return f"Inventory cannot cover the estimated {quantity}-unit rollout."
        return None

    def _support_rejection_reasons(self, product, target_profile):
        reasons = []
        required_support = int(target_profile.get("min_support_score") or 0)
        required_warranty = max(
            int(target_profile.get("min_warranty_years") or 0),
            int(self._configured_value("minimum_warranty_years_default", os.getenv("MIN_WARRANTY_YEARS_DEFAULT", "")) or 0),
        )
        support_score = int(product.get("support_score") or 0)
        warranty_years = int(product.get("warranty_years") or 0)

        if required_support and support_score < required_support:
            reasons.append("Support level does not meet the strict support policy.")
        if required_warranty and warranty_years < required_warranty:
            reasons.append("Warranty duration does not meet the strict warranty policy.")
        return reasons

    def _spec_rejection_reasons(self, product, requirements):
        reasons = []
        requested_ram_gb = requirements.get("requested_ram_gb")
        if requested_ram_gb and requirements.get("requested_ram_is_minimum", True):
            if int(product.get("ram_gb") or 0) < int(requested_ram_gb):
                reasons.append(f"RAM does not meet the required minimum of {requested_ram_gb}GB.")

        requested_storage_gb = requirements.get("requested_storage_gb")
        if requested_storage_gb and requirements.get("requested_storage_is_minimum", True):
            if int(product.get("storage_gb") or 0) < int(requested_storage_gb):
                reasons.append(f"Storage does not meet the required minimum of {requested_storage_gb}GB.")

        battery_life_hours_min = requirements.get("battery_life_hours_min")
        if battery_life_hours_min:
            if int(product.get("battery_life_hours") or 0) < int(battery_life_hours_min):
                reasons.append(
                    f"Battery life does not meet the required minimum of {battery_life_hours_min} hours."
                )

        cpu_preference = str(requirements.get("cpu_preference") or "").strip()
        if cpu_preference:
            required_cpu_score = score_cpu_tier(cpu_preference)
            if int(product.get("cpu_score") or 0) < required_cpu_score:
                reasons.append(f"CPU tier does not meet the required processor preference of {cpu_preference}.")

        gpu_requirement = str(requirements.get("gpu_requirement") or "").strip()
        if gpu_requirement:
            required_tier = normalize_gpu_tier(gpu_requirement)
            current_value = ProcurementPolicyService._gpu_tier_value(product.get("gpu_tier"))
            required_value = ProcurementPolicyService._gpu_tier_value(required_tier)
            if current_value < required_value:
                reasons.append(f"Graphics capability does not meet the required GPU preference of {gpu_requirement}.")

        screen_size_preference = str(requirements.get("screen_size_preference") or "").strip()
        if screen_size_preference:
            required_screen = parse_screen_size_inches_value(screen_size_preference)
            current_screen = product.get("screen_size_inches")
            if required_screen is not None:
                if current_screen is None:
                    reasons.append(f"Screen size could not be verified against the requested {screen_size_preference}.")
                elif abs(float(current_screen) - float(required_screen)) > 0.8:
                    reasons.append(f"Screen size does not match the requested preference of {screen_size_preference}.")

        weight_kg_max = requirements.get("weight_kg_max")
        if weight_kg_max is not None:
            current_weight = product.get("weight_kg")
            if current_weight is None:
                reasons.append(f"Weight could not be verified against the maximum of {weight_kg_max} kg.")
            elif float(current_weight) > float(weight_kg_max):
                reasons.append(f"Weight exceeds the maximum allowed {weight_kg_max} kg.")

        warranty_type_preference = normalize_warranty_type(requirements.get("warranty_type_preference"))
        if warranty_type_preference:
            current_warranty_type = normalize_warranty_type(product.get("warranty_type") or product.get("warranty"))
            if current_warranty_type != warranty_type_preference:
                reasons.append(
                    f"Warranty type does not meet the required preference of {warranty_type_preference.replace('_', ' ')}."
                )

        required_printer_type = str(requirements.get("required_printer_type") or "").strip().lower()
        if required_printer_type:
            current_printer_type = str(product.get("printer_type") or "").strip().lower()
            if current_printer_type != required_printer_type:
                reasons.append(f"Printer type does not meet the required preference of {required_printer_type}.")

        required_print_technology = str(requirements.get("required_print_technology") or "").strip().lower()
        if required_print_technology:
            current_print_technology = str(product.get("print_technology") or "").strip().lower()
            if required_print_technology not in current_print_technology:
                reasons.append(
                    f"Print technology does not meet the required preference of {required_print_technology}."
                )

        required_color_output = str(requirements.get("required_color_output") or "").strip().lower()
        if required_color_output:
            current_color_output = str(product.get("color_output") or "").strip().lower()
            if current_color_output != required_color_output:
                reasons.append(f"Color output does not meet the required preference of {required_color_output}.")

        min_print_speed_ppm = requirements.get("min_print_speed_ppm")
        if min_print_speed_ppm:
            if int(product.get("print_speed_ppm") or 0) < int(min_print_speed_ppm):
                reasons.append(f"Print speed does not meet the required minimum of {min_print_speed_ppm} ppm.")

        min_monthly_duty_cycle_pages = requirements.get("min_monthly_duty_cycle_pages")
        if min_monthly_duty_cycle_pages:
            if int(product.get("monthly_duty_cycle_pages") or 0) < int(min_monthly_duty_cycle_pages):
                reasons.append(
                    f"Monthly duty cycle does not meet the required minimum of {min_monthly_duty_cycle_pages} pages."
                )

        if requirements.get("required_automatic_document_feeder") and not bool(product.get("automatic_document_feeder")):
            reasons.append("Automatic document feeder is required for this request.")

        required_paper_sizes = {
            str(size or "").strip().upper()
            for size in (requirements.get("required_paper_sizes") or [])
            if str(size or "").strip()
        }
        if required_paper_sizes:
            available_paper_sizes = {
                str(size or "").strip().upper()
                for size in (product.get("paper_size_support") or [])
                if str(size or "").strip()
            }
            if not required_paper_sizes.issubset(available_paper_sizes):
                reasons.append(
                    "Paper size support does not meet the required preference of "
                    + ", ".join(sorted(required_paper_sizes))
                    + "."
                )

        required_virtualization_platforms = {
            str(platform or "").strip().lower()
            for platform in (requirements.get("required_virtualization_platforms") or [])
            if str(platform or "").strip()
        }
        if requirements.get("required_virtualization_ready") and not bool(product.get("virtualization_ready")):
            reasons.append("Virtualization readiness is required for this request.")
        if required_virtualization_platforms:
            available_platforms = {
                str(platform or "").strip().lower()
                for platform in (product.get("virtualization_platforms") or [])
                if str(platform or "").strip()
            }
            if not required_virtualization_platforms.intersection(available_platforms):
                reasons.append("Virtualization platform support does not meet the required preference.")

        max_rack_units = requirements.get("max_rack_units")
        if max_rack_units not in (None, "") and product.get("rack_units") not in (None, ""):
            if float(product.get("rack_units")) > float(max_rack_units):
                reasons.append(f"Rack footprint exceeds the maximum allowed {max_rack_units}U.")

        max_power_draw_watts = requirements.get("max_power_draw_watts")
        if max_power_draw_watts and int(product.get("power_draw_watts") or 0) > int(max_power_draw_watts):
            reasons.append(f"Power draw exceeds the maximum allowed {max_power_draw_watts}W.")
        return reasons

    @staticmethod
    def _gpu_tier_value(value):
        mapping = {
            "integrated": 1,
            "entry_discrete": 2,
            "performance": 3,
            "workstation": 4,
        }
        return mapping.get(str(value or "").strip().lower(), 1)

    def _availability_rejection_reason(self, product, requirements, target_profile):
        availability_need = str(requirements.get("availability_need") or "").strip().lower()
        if availability_need not in {"urgent", "in_stock_now"}:
            return None

        stock_quantity = product.get("stock_quantity")
        quantity = self._determine_quantity(product, target_profile)
        if stock_quantity is None:
            return None

        stock_quantity = int(stock_quantity or 0)
        if availability_need == "in_stock_now":
            if stock_quantity <= 0:
                return "Availability requirement needs stock on hand immediately."
            return None
        if availability_need == "urgent" and stock_quantity <= 0:
            return "Availability requirement needs stock on hand immediately."
        return None

    def _return_policy_rejection_reason(self, product, requirements):
        if requirements.get("require_returnable") and not product.get("return_policy"):
            return "Return policy is required for this buyer, but the product is non-returnable."
        return None

    def _determine_quantity(self, product, target_profile):
        category = product.get("category")
        recommended_quantity = int(target_profile.get("recommended_quantity") or 1)
        seat_based_categories = set(self.config_service.get_rules_config().get("seat_based_categories") or [])
        if category in seat_based_categories:
            return max(recommended_quantity, 1)
        return 1

    def _flag_enabled(self, env_name, config_key):
        raw_value = self._configured_value(config_key, os.getenv(env_name, ""))
        return str(raw_value or "").strip().lower() in {"1", "true", "yes", "on"}

    def _policy_values(self, env_name, config_key):
        raw_value = self._configured_value(config_key, os.getenv(env_name, ""))
        if isinstance(raw_value, list):
            source_values = raw_value
        else:
            source_values = str(raw_value or "").split(",")
        return {
            str(value).strip().lower()
            for value in source_values
            if value.strip()
        }

    def _configured_value(self, config_key, env_value):
        env_value = env_value if env_value is not None else ""
        if str(env_value).strip():
            return env_value
        return self.config_service.get_policy_config().get(config_key)

    def _request_values(self, values):
        return {
            str(value or "").strip().lower()
            for value in list(values or [])
            if str(value or "").strip()
        }

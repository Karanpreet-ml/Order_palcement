from copy import deepcopy

from .config_service import ProcurementConfigService


class ProcurementCompatibilityService:
    GPU_TIER_ORDER = {
        "integrated": 1,
        "entry_discrete": 2,
        "performance": 3,
        "workstation": 4,
    }
    INFRASTRUCTURE_SCALE_LEVELS = {
        "branch_router": 1,
        "branch_switch": 1,
        "network_small_branch": 1,
        "network_mid_branch": 2,
        "network_large_branch": 3,
        "server_small": 1,
        "server_medium": 2,
        "server_large": 3,
    }

    ITEM_SCOPE = "item"
    BUNDLE_SCOPE = "bundle"

    def __init__(self, config_service=None):
        self.config_service = config_service or ProcurementConfigService()

    def evaluate(self, products, requirements, target_profile):
        rules = [
            rule
            for rule in list(self.config_service.get_rules_config().get("compatibility_rules") or [])
            if (rule.get("scope") or self.ITEM_SCOPE) == self.ITEM_SCOPE
        ]
        eligible_products = []
        rejected_products = []
        reports_by_product_id = {}
        warning_count = 0
        products = list(products or [])

        for product in products:
            matched_evaluations = []
            for rule in rules:
                if not self._rule_applies(rule, product):
                    continue
                matched = self._evaluate_condition(rule.get("condition"), product, requirements, target_profile)
                if not matched:
                    continue
                evaluation = {
                    "rule_id": rule.get("rule_id"),
                    "scope": rule.get("scope") or self.ITEM_SCOPE,
                    "type": rule.get("type"),
                    "severity": rule.get("severity"),
                    "priority": int(rule.get("priority") or 0),
                    "reason_code": rule.get("reason_code"),
                    "user_message": rule.get("user_message"),
                    "overridable": bool(rule.get("overridable")),
                    "override_scope": list(rule.get("override_scope") or []),
                    "version": rule.get("version"),
                }
                matched_evaluations.append(evaluation)

            matched_evaluations.sort(key=lambda item: item["priority"], reverse=True)
            blocked = [item for item in matched_evaluations if item["type"] in {"HARD_BLOCK", "POLICY_BLOCK"}]
            warnings = [item for item in matched_evaluations if item["type"] == "SOFT_WARN"]
            warning_count += len(warnings)
            report = {
                "product_id": product.get("id"),
                "name": product.get("name"),
                "category": product.get("category"),
                "scope": self.ITEM_SCOPE,
                "passed": not blocked,
                "warning_count": len(warnings),
                "blocked_count": len(blocked),
                "evaluations": matched_evaluations,
            }
            reports_by_product_id[product.get("id")] = report

            enriched_product = deepcopy(product)
            enriched_product["compatibility_report"] = report
            enriched_product["compatibility_warnings"] = warnings
            enriched_product["compatibility_blockers"] = blocked
            if blocked:
                rejected_products.append(
                    {
                        "product_id": product.get("id"),
                        "name": product.get("name"),
                        "category": product.get("category"),
                        "manufacturer": product.get("manufacturer"),
                        "scope": self.ITEM_SCOPE,
                        "reasons": [item["user_message"] for item in blocked],
                        "reason_codes": [item["reason_code"] for item in blocked],
                        "overridable": any(item["overridable"] for item in blocked),
                    }
                )
            else:
                eligible_products.append(enriched_product)

        return {
            "eligible_products": eligible_products,
            "rejected_products": rejected_products,
            "reports_by_product_id": reports_by_product_id,
            "summary": {
                "compatibility_scope": self.ITEM_SCOPE,
                "input_count": len(products),
                "eligible_count": len(eligible_products),
                "rejected_count": len(rejected_products),
                "warning_count": warning_count,
                "rules_version": self.config_service.get_rules_config().get("version"),
            },
        }

    def evaluate_bundle(self, bundle_candidate, requirements, recommendation_groups, multi_intent_policy):
        bundle_candidate = dict(bundle_candidate or {})
        requirements = dict(requirements or {})
        recommendation_groups = list(recommendation_groups or [])
        multi_intent_policy = dict(multi_intent_policy or {})
        rules = [
            rule
            for rule in list(self.config_service.get_rules_config().get("compatibility_rules") or [])
            if (rule.get("scope") or self.ITEM_SCOPE) == self.BUNDLE_SCOPE
        ]
        bundle_context = self._build_bundle_context(bundle_candidate, recommendation_groups)

        matched_evaluations = []
        for rule in rules:
            if not self._bundle_rule_applies(rule, bundle_candidate):
                continue
            matched = self._evaluate_bundle_condition(
                rule.get("condition"),
                bundle_candidate,
                requirements,
                recommendation_groups,
                multi_intent_policy,
                bundle_context,
            )
            if not matched:
                continue
            matched_evaluations.append(
                {
                    "rule_id": rule.get("rule_id"),
                    "scope": rule.get("scope") or self.BUNDLE_SCOPE,
                    "type": rule.get("type"),
                    "severity": rule.get("severity"),
                    "priority": int(rule.get("priority") or 0),
                    "reason_code": rule.get("reason_code"),
                    "user_message": rule.get("user_message"),
                    "overridable": bool(rule.get("overridable")),
                    "override_scope": list(rule.get("override_scope") or []),
                    "version": rule.get("version"),
                }
            )

        matched_evaluations.sort(key=lambda item: item["priority"], reverse=True)
        blocked = [item for item in matched_evaluations if item["type"] in {"HARD_BLOCK", "POLICY_BLOCK"}]
        warnings = [item for item in matched_evaluations if item["type"] == "SOFT_WARN"]
        role_coverage = dict(bundle_candidate.get("role_coverage") or {})
        capacity_summary = self._build_bundle_capacity_summary(
            bundle_candidate.get("capacity_summary") or {},
            bundle_context,
        )
        consistency_summary = self._build_bundle_consistency_summary(bundle_context)
        budget_summary = self._build_bundle_budget_summary(
            bundle_candidate,
            requirements=requirements,
            multi_intent_policy=multi_intent_policy,
        )
        bundle_conflict_codes = [item["reason_code"] for item in blocked]

        return {
            "bundle_id": bundle_candidate.get("bundle_id"),
            "scope": self.BUNDLE_SCOPE,
            "passed": not blocked,
            "warning_count": len(warnings),
            "blocked_count": len(blocked),
            "evaluations": matched_evaluations,
            "blocked_reasons": [item["user_message"] for item in blocked],
            "warning_messages": [item["user_message"] for item in warnings],
            "bundle_conflict_codes": bundle_conflict_codes,
            "role_coverage": role_coverage,
            "capacity_summary": capacity_summary,
            "consistency_summary": consistency_summary,
            "budget_summary": budget_summary,
            "summary": {
                "compatibility_scope": self.BUNDLE_SCOPE,
                "bundle_validated": not blocked,
                "required_role_count": int(role_coverage.get("required_role_count") or 0),
                "covered_role_count": int(role_coverage.get("covered_role_count") or 0),
                "missing_role_count": len(role_coverage.get("missing_roles") or []),
                "total_quantity_required": int(capacity_summary.get("total_quantity_required") or 0),
                "total_quantity_gap": int(capacity_summary.get("total_quantity_gap") or 0),
                "site_endpoint_quantity_required": int(capacity_summary.get("site_endpoint_quantity_required") or 0),
                "end_user_quantity_required": int(capacity_summary.get("end_user_quantity_required") or 0),
                "total_estimated_cost": bundle_candidate.get("total_estimated_cost"),
                "currency": bundle_candidate.get("currency") or requirements.get("currency"),
                "within_budget": budget_summary.get("within_budget"),
                "consistency_issue_count": len(consistency_summary.get("issues") or []),
                "warning_count": len(warnings),
                "blocked_count": len(blocked),
                "rules_version": self.config_service.get_rules_config().get("version"),
            },
        }

    def _rule_applies(self, rule, product):
        applies_to = rule.get("applies_to") or {}
        allowed_categories = set(applies_to.get("categories") or [])
        if "*" in allowed_categories or not allowed_categories:
            return True
        return product.get("category") in allowed_categories

    def _bundle_rule_applies(self, rule, bundle_candidate):
        applies_to = rule.get("applies_to") or {}
        allowed_categories = set(applies_to.get("categories") or [])
        if "*" in allowed_categories or not allowed_categories:
            return True
        bundle_categories = {
            assignment.get("category")
            for assignment in list(bundle_candidate.get("assignments") or [])
            if assignment.get("category")
        }
        return bool(bundle_categories.intersection(allowed_categories))

    def _evaluate_condition(self, condition, product, requirements, target_profile):
        if condition == "category_in_scope":
            allowed_categories = set(target_profile.get("categories") or [])
            return bool(allowed_categories and product.get("category") not in allowed_categories)

        if condition == "requested_ram_minimum":
            if not requirements.get("requested_ram_is_minimum", True):
                return False
            requested = requirements.get("requested_ram_gb")
            if not requested:
                return False
            return int(product.get("ram_gb") or 0) < int(requested)

        if condition == "requested_storage_minimum":
            if not requirements.get("requested_storage_is_minimum", True):
                return False
            requested = requirements.get("requested_storage_gb")
            if not requested:
                return False
            return int(product.get("storage_gb") or 0) < int(requested)

        if condition == "missing_hard_required_metadata":
            metadata_validation = dict(product.get("metadata_validation") or {})
            readiness_state = str(
                product.get("readiness_state") or metadata_validation.get("readiness_state") or ""
            ).strip()
            return readiness_state == "insufficient" or bool(metadata_validation.get("missing_required_fields"))

        if condition == "target_gpu_hard_gap":
            required_tier = target_profile.get("min_gpu_tier") or "integrated"
            capability_tags = set(requirements.get("capability_tags") or [])
            workloads = set(requirements.get("workloads") or [])
            if required_tier == "integrated":
                return False
            if "gpu_needed" not in capability_tags and not workloads.intersection({"ai_analytics"}):
                return False
            current_value = self.GPU_TIER_ORDER.get(product.get("gpu_tier") or "integrated", 1)
            required_value = self.GPU_TIER_ORDER.get(required_tier, 1)
            return current_value < required_value

        if condition == "target_ram_soft_gap":
            required = int(target_profile.get("min_ram_gb") or 0)
            if not required:
                return False
            return int(product.get("ram_gb") or 0) < required

        if condition == "target_virtualization_unmet":
            if not target_profile.get("required_virtualization_ready"):
                return False
            return not bool(product.get("virtualization_ready"))

        if condition == "target_virtualization_platform_gap":
            required_platforms = set(target_profile.get("required_virtualization_platforms") or [])
            if not required_platforms:
                return False
            available_platforms = set(product.get("virtualization_platforms") or [])
            return not bool(required_platforms.intersection(available_platforms))

        if condition == "target_network_role_mismatch":
            required_roles = set(target_profile.get("required_network_roles") or [])
            if not required_roles:
                return False
            return str(product.get("network_role") or "").strip() not in required_roles

        if condition == "target_port_capacity_gap":
            required = int(target_profile.get("required_port_count") or 0)
            if not required:
                return False
            return int(product.get("port_count") or 0) < required

        if condition == "target_vpn_capacity_gap":
            required = int(target_profile.get("required_vpn_user_capacity") or 0)
            if not required:
                return False
            return int(product.get("vpn_user_capacity") or 0) < required

        if condition == "target_network_throughput_gap":
            required = int(target_profile.get("required_throughput_mbps") or 0)
            if not required:
                return False
            return int(product.get("throughput_mbps") or 0) < required

        if condition == "target_printer_type_mismatch":
            required = str(target_profile.get("required_printer_type") or "").strip().lower()
            if not required:
                return False
            return str(product.get("printer_type") or "").strip().lower() != required

        if condition == "target_printer_technology_mismatch":
            required = str(target_profile.get("required_print_technology") or "").strip().lower()
            if not required:
                return False
            current = str(product.get("print_technology") or "").strip().lower()
            return required not in current

        if condition == "target_printer_color_mismatch":
            required = str(target_profile.get("required_color_output") or "").strip().lower()
            if not required:
                return False
            return str(product.get("color_output") or "").strip().lower() != required

        if condition == "target_printer_speed_gap":
            required = int(target_profile.get("min_print_speed_ppm") or 0)
            if not required:
                return False
            return int(product.get("print_speed_ppm") or 0) < required

        if condition == "target_printer_duty_cycle_gap":
            required = int(target_profile.get("min_monthly_duty_cycle_pages") or 0)
            if not required:
                return False
            return int(product.get("monthly_duty_cycle_pages") or 0) < required

        if condition == "target_printer_duplex_unmet":
            if not target_profile.get("required_duplex_printing"):
                return False
            return not bool(product.get("duplex_printing"))

        if condition == "target_printer_scanner_unmet":
            if not target_profile.get("required_scanner"):
                return False
            return not bool(str(product.get("scanner_type") or "").strip())

        if condition == "target_printer_adf_unmet":
            if not target_profile.get("required_automatic_document_feeder"):
                return False
            return not bool(product.get("automatic_document_feeder"))

        if condition == "target_printer_paper_size_gap":
            required_sizes = {
                str(size or "").strip().upper()
                for size in (target_profile.get("required_paper_sizes") or [])
                if str(size or "").strip()
            }
            if not required_sizes:
                return False
            available_sizes = {
                str(size or "").strip().upper()
                for size in (product.get("paper_size_support") or [])
                if str(size or "").strip()
            }
            return not required_sizes.issubset(available_sizes)

        if condition == "target_accessory_type_mismatch":
            required = str(target_profile.get("required_accessory_type") or "").strip().lower()
            if not required:
                return False
            return str(product.get("accessory_type") or "").strip().lower() != required

        if condition == "target_rack_space_gap":
            limit = target_profile.get("max_rack_units")
            if limit in {None, ""}:
                return False
            rack_units = product.get("rack_units")
            if rack_units in {None, ""}:
                return False
            return float(rack_units) > float(limit)

        if condition == "target_power_budget_gap":
            limit = target_profile.get("max_power_draw_watts")
            if not limit:
                return False
            return int(product.get("power_draw_watts") or 0) > int(limit)

        if condition == "target_storage_soft_gap":
            required = int(target_profile.get("min_storage_gb") or 0)
            if not required:
                return False
            return int(product.get("storage_gb") or 0) < required

        if condition == "target_cpu_soft_gap":
            required = int(target_profile.get("min_cpu_score") or 0)
            if not required:
                return False
            return int(product.get("cpu_score") or 0) < required

        if condition == "target_support_soft_gap":
            required = int(target_profile.get("min_support_score") or 0)
            if not required:
                return False
            return int(product.get("support_score") or 0) < required

        if condition == "target_warranty_soft_gap":
            required = int(target_profile.get("min_warranty_years") or 0)
            if not required:
                return False
            return int(product.get("warranty_years") or 0) < required

        return False

    def _evaluate_bundle_condition(
        self,
        condition,
        bundle_candidate,
        requirements,
        recommendation_groups,
        multi_intent_policy,
        bundle_context,
    ):
        bundle_candidate = dict(bundle_candidate or {})
        role_coverage = dict(bundle_candidate.get("role_coverage") or {})
        capacity_summary = dict(bundle_candidate.get("capacity_summary") or {})
        shared_budget = dict(multi_intent_policy.get("shared_budget") or {})
        budget_summary = self._build_bundle_budget_summary(
            bundle_candidate,
            requirements=requirements,
            multi_intent_policy=multi_intent_policy,
        )

        if condition == "bundle_missing_group_recommendation":
            required_role_count = int(role_coverage.get("required_role_count") or 0)
            covered_role_count = int(role_coverage.get("covered_role_count") or 0)
            return covered_role_count < required_role_count

        if condition == "bundle_group_not_firm":
            return any(
                str(group.get("recommendation_mode") or "").strip() != "firm_recommendation"
                for group in list(recommendation_groups or [])
            )

        if condition == "bundle_shared_budget_allocation_gap":
            return bool(shared_budget.get("allocation_required"))

        if condition == "bundle_capacity_shortfall":
            return int(capacity_summary.get("total_quantity_gap") or 0) > 0

        if condition == "bundle_budget_fit_gap":
            return budget_summary.get("within_budget") is False

        if condition == "bundle_network_port_capacity_gap":
            return bool(bundle_context.get("switch_assignment_count")) and int(
                bundle_context.get("network_port_capacity_gap") or 0
            ) > 0

        if condition == "bundle_network_vpn_capacity_gap":
            return bool(bundle_context.get("router_firewall_assignment_count")) and int(
                bundle_context.get("network_vpn_capacity_gap") or 0
            ) > 0

        if condition == "bundle_network_throughput_gap":
            return bool(bundle_context.get("router_firewall_assignment_count")) and int(
                bundle_context.get("network_throughput_gap_mbps") or 0
            ) > 0

        if condition == "bundle_server_network_ha_gap":
            return bool(bundle_context.get("server_requires_resilient_network")) and bool(
                bundle_context.get("network_assignment_count")
            ) and int(bundle_context.get("network_ha_ready_count") or 0) <= 0

        if condition == "bundle_infrastructure_scale_mismatch":
            return bool(bundle_context.get("infrastructure_scale_conflict"))

        if condition == "bundle_accessory_host_missing":
            return int(bundle_context.get("supported_accessory_add_on_count") or 0) > 0 and int(
                bundle_context.get("accessory_missing_host_count") or 0
            ) > 0

        if condition == "bundle_accessory_host_quantity_gap":
            return (
                int(bundle_context.get("supported_accessory_add_on_count") or 0) > 0
                and int(bundle_context.get("accessory_host_assignment_count") or 0) > 0
                and int(bundle_context.get("accessory_host_quantity_gap") or 0) > 0
            )

        return False

    def _build_bundle_context(self, bundle_candidate, recommendation_groups):
        bundle_candidate = dict(bundle_candidate or {})
        assignments = list(bundle_candidate.get("assignments") or [])
        recommendation_groups = list(recommendation_groups or [])
        firm_group_count = sum(
            1
            for group in recommendation_groups
            if str(group.get("recommendation_mode") or "").strip() == "firm_recommendation"
        )

        end_user_assignments = [
            assignment for assignment in assignments if assignment.get("category") in {"laptops", "desktops"}
        ]
        server_assignments = [
            assignment for assignment in assignments if assignment.get("category") == "servers"
        ]
        network_assignments = [
            assignment for assignment in assignments if assignment.get("category") == "networking"
        ]
        accessory_assignments = [
            assignment for assignment in assignments if assignment.get("category") == "accessories"
        ]
        supported_accessory_add_on_assignments = [
            assignment
            for assignment in accessory_assignments
            if bool(assignment.get("attachment_required"))
        ]
        switch_assignments = [
            assignment
            for assignment in network_assignments
            if str(assignment.get("network_role") or "").strip().lower() == "switch"
            or "switch" in {str(role).strip().lower() for role in assignment.get("required_network_roles") or []}
        ]
        router_firewall_assignments = [
            assignment
            for assignment in network_assignments
            if str(assignment.get("network_role") or "").strip().lower() in {"router", "firewall"}
            or {"router", "firewall"}.intersection(
                {str(role).strip().lower() for role in assignment.get("required_network_roles") or []}
            )
        ]

        end_user_quantity_required = sum(int(assignment.get("quantity_required") or 0) for assignment in end_user_assignments)
        server_node_quantity_required = sum(int(assignment.get("quantity_required") or 0) for assignment in server_assignments)
        site_endpoint_quantity_required = end_user_quantity_required + server_node_quantity_required

        required_port_capacity = (
            max(
                site_endpoint_quantity_required,
                sum(int(assignment.get("required_port_count") or 0) for assignment in switch_assignments),
            )
            if switch_assignments
            else 0
        )
        provided_port_capacity = self._total_network_capacity(switch_assignments, "port_count")

        required_vpn_capacity = (
            max(
                end_user_quantity_required,
                sum(int(assignment.get("required_vpn_user_capacity") or 0) for assignment in router_firewall_assignments),
            )
            if router_firewall_assignments
            else 0
        )
        provided_vpn_capacity = self._total_network_capacity(router_firewall_assignments, "vpn_user_capacity")

        derived_throughput_floor = max(200, end_user_quantity_required * 10) if end_user_quantity_required else 0
        required_throughput_mbps = (
            max(
                derived_throughput_floor,
                max(
                    [int(assignment.get("required_throughput_mbps") or 0) for assignment in router_firewall_assignments]
                    or [0]
                ),
            )
            if router_firewall_assignments
            else 0
        )
        provided_throughput_mbps = self._total_network_capacity(router_firewall_assignments, "throughput_mbps")

        server_scale_levels = [
            self._scale_level(scale)
            for assignment in server_assignments
            for scale in list(assignment.get("target_infrastructure_scales") or [])
            if self._scale_level(scale) is not None
        ]
        network_scale_levels = [
            self._scale_level(scale)
            for assignment in network_assignments
            for scale in list(assignment.get("target_infrastructure_scales") or [])
            if self._scale_level(scale) is not None
        ]
        server_requires_resilient_network = any(
            bool(assignment.get("required_virtualization_ready"))
            or bool(assignment.get("remote_management"))
            or "always_on" in {str(tag).strip().lower() for tag in assignment.get("target_capability_tags") or []}
            or "virtualization" in {str(tag).strip().lower() for tag in assignment.get("target_capability_tags") or []}
            for assignment in server_assignments
        )
        supported_accessory_types = sorted(
            {
                str(assignment.get("accessory_type") or "").strip().lower()
                for assignment in supported_accessory_add_on_assignments
                if str(assignment.get("accessory_type") or "").strip()
            }
        )
        accessory_add_on_quantity_required = sum(
            int(assignment.get("quantity_required") or 0) for assignment in supported_accessory_add_on_assignments
        )
        accessory_missing_host_count = sum(
            1
            for assignment in supported_accessory_add_on_assignments
            if str(assignment.get("attachment_status") or "").strip().lower() != "attached"
            or not list(assignment.get("attachment_target_role_ids") or [])
        )
        accessory_host_quantity_available = end_user_quantity_required
        accessory_host_quantity_gap = (
            max(accessory_add_on_quantity_required - accessory_host_quantity_available, 0)
            if supported_accessory_add_on_assignments
            else 0
        )

        return {
            "assignment_count": len(assignments),
            "firm_group_count": firm_group_count,
            "end_user_quantity_required": end_user_quantity_required,
            "server_node_quantity_required": server_node_quantity_required,
            "site_endpoint_quantity_required": site_endpoint_quantity_required,
            "server_assignment_count": len(server_assignments),
            "network_assignment_count": len(network_assignments),
            "switch_assignment_count": len(switch_assignments),
            "router_firewall_assignment_count": len(router_firewall_assignments),
            "required_port_capacity": required_port_capacity,
            "provided_port_capacity": provided_port_capacity,
            "network_port_capacity_gap": max(required_port_capacity - provided_port_capacity, 0),
            "required_vpn_capacity": required_vpn_capacity,
            "provided_vpn_capacity": provided_vpn_capacity,
            "network_vpn_capacity_gap": max(required_vpn_capacity - provided_vpn_capacity, 0),
            "required_throughput_mbps": required_throughput_mbps,
            "provided_throughput_mbps": provided_throughput_mbps,
            "network_throughput_gap_mbps": max(required_throughput_mbps - provided_throughput_mbps, 0),
            "server_requires_resilient_network": server_requires_resilient_network,
            "network_ha_ready_count": sum(
                1 for assignment in network_assignments if bool(assignment.get("high_availability_ready"))
            ),
            "server_scale_levels": server_scale_levels,
            "network_scale_levels": network_scale_levels,
            "accessory_assignment_count": len(accessory_assignments),
            "supported_accessory_add_on_count": len(supported_accessory_add_on_assignments),
            "supported_accessory_types": supported_accessory_types,
            "accessory_host_assignment_count": len(end_user_assignments),
            "accessory_add_on_quantity_required": accessory_add_on_quantity_required,
            "accessory_host_quantity_available": accessory_host_quantity_available,
            "accessory_host_quantity_gap": accessory_host_quantity_gap,
            "accessory_missing_host_count": accessory_missing_host_count,
            "infrastructure_scale_conflict": bool(
                server_scale_levels
                and network_scale_levels
                and abs(max(server_scale_levels) - max(network_scale_levels)) > 1
            ),
        }

    def _build_bundle_capacity_summary(self, base_capacity_summary, bundle_context):
        summary = dict(base_capacity_summary or {})
        bundle_context = dict(bundle_context or {})
        summary.update(
            {
                "site_endpoint_quantity_required": int(bundle_context.get("site_endpoint_quantity_required") or 0),
                "end_user_quantity_required": int(bundle_context.get("end_user_quantity_required") or 0),
                "server_node_quantity_required": int(bundle_context.get("server_node_quantity_required") or 0),
                "required_port_capacity": int(bundle_context.get("required_port_capacity") or 0),
                "provided_port_capacity": int(bundle_context.get("provided_port_capacity") or 0),
                "network_port_capacity_gap": int(bundle_context.get("network_port_capacity_gap") or 0),
                "required_vpn_capacity": int(bundle_context.get("required_vpn_capacity") or 0),
                "provided_vpn_capacity": int(bundle_context.get("provided_vpn_capacity") or 0),
                "network_vpn_capacity_gap": int(bundle_context.get("network_vpn_capacity_gap") or 0),
                "required_throughput_mbps": int(bundle_context.get("required_throughput_mbps") or 0),
                "provided_throughput_mbps": int(bundle_context.get("provided_throughput_mbps") or 0),
                "network_throughput_gap_mbps": int(bundle_context.get("network_throughput_gap_mbps") or 0),
                "supported_accessory_add_on_count": int(bundle_context.get("supported_accessory_add_on_count") or 0),
                "accessory_add_on_quantity_required": int(bundle_context.get("accessory_add_on_quantity_required") or 0),
                "accessory_host_quantity_available": int(bundle_context.get("accessory_host_quantity_available") or 0),
                "accessory_host_quantity_gap": int(bundle_context.get("accessory_host_quantity_gap") or 0),
            }
        )
        return summary

    def _build_bundle_consistency_summary(self, bundle_context):
        bundle_context = dict(bundle_context or {})
        issues = []
        if int(bundle_context.get("switch_assignment_count") or 0) > 0 and int(
            bundle_context.get("network_port_capacity_gap") or 0
        ) > 0:
            issues.append("bundle_network_port_capacity_gap")
        if int(bundle_context.get("router_firewall_assignment_count") or 0) > 0 and int(
            bundle_context.get("network_vpn_capacity_gap") or 0
        ) > 0:
            issues.append("bundle_network_vpn_capacity_gap")
        if int(bundle_context.get("router_firewall_assignment_count") or 0) > 0 and int(
            bundle_context.get("network_throughput_gap_mbps") or 0
        ) > 0:
            issues.append("bundle_network_throughput_gap")
        if bool(bundle_context.get("server_requires_resilient_network")) and int(
            bundle_context.get("network_ha_ready_count") or 0
        ) <= 0 and int(bundle_context.get("network_assignment_count") or 0) > 0:
            issues.append("bundle_server_network_ha_gap")
        if bundle_context.get("infrastructure_scale_conflict"):
            issues.append("bundle_infrastructure_scale_mismatch")
        if int(bundle_context.get("accessory_missing_host_count") or 0) > 0:
            issues.append("bundle_accessory_host_missing")
        if int(bundle_context.get("accessory_host_assignment_count") or 0) > 0 and int(
            bundle_context.get("accessory_host_quantity_gap") or 0
        ) > 0:
            issues.append("bundle_accessory_host_quantity_gap")
        return {
            "issues": issues,
            "server_requires_resilient_network": bool(bundle_context.get("server_requires_resilient_network")),
            "network_ha_ready_count": int(bundle_context.get("network_ha_ready_count") or 0),
            "server_scale_levels": list(bundle_context.get("server_scale_levels") or []),
            "network_scale_levels": list(bundle_context.get("network_scale_levels") or []),
            "infrastructure_scale_conflict": bool(bundle_context.get("infrastructure_scale_conflict")),
            "supported_accessory_types": list(bundle_context.get("supported_accessory_types") or []),
            "accessory_host_assignment_count": int(bundle_context.get("accessory_host_assignment_count") or 0),
            "accessory_missing_host_count": int(bundle_context.get("accessory_missing_host_count") or 0),
            "accessory_host_quantity_gap": int(bundle_context.get("accessory_host_quantity_gap") or 0),
        }

    def _total_network_capacity(self, assignments, field_name):
        total = 0
        for assignment in list(assignments or []):
            capacity = assignment.get(field_name)
            if capacity in {None, ""}:
                continue
            quantity = max(int(assignment.get("quantity_covered") or assignment.get("quantity_required") or 0), 1)
            total += int(capacity) * quantity
        return total

    def _scale_level(self, scale):
        normalized = str(scale or "").strip().lower()
        if not normalized:
            return None
        return self.INFRASTRUCTURE_SCALE_LEVELS.get(normalized)

    def _build_bundle_budget_summary(self, bundle_candidate, requirements, multi_intent_policy):
        bundle_candidate = dict(bundle_candidate or {})
        requirements = dict(requirements or {})
        multi_intent_policy = dict(multi_intent_policy or {})
        assignments = list(bundle_candidate.get("assignments") or [])
        budget = requirements.get("budget")
        budget_scope = requirements.get("budget_scope")
        total_estimated_cost = bundle_candidate.get("total_estimated_cost")
        within_budget = None
        if budget is not None and budget_scope == "project_total" and total_estimated_cost is not None:
            within_budget = float(total_estimated_cost) <= float(budget)
        elif budget is not None and budget_scope == "per_unit":
            priced_assignments = [
                assignment
                for assignment in assignments
                if assignment.get("unit_price") is not None
            ]
            within_budget = all(float(assignment["unit_price"]) <= float(budget) for assignment in priced_assignments)

        return {
            "budget": budget,
            "budget_scope": budget_scope,
            "budget_strategy": bundle_candidate.get("template_budget_strategy"),
            "shared_budget": multi_intent_policy.get("shared_budget") or {},
            "total_estimated_cost": total_estimated_cost,
            "currency": bundle_candidate.get("currency") or requirements.get("currency"),
            "within_budget": within_budget,
        }

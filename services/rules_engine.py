import math
import re

from ...catalog.services.hardware_tiers import normalize_gpu_tier
from ...catalog.services.normalization import normalize_warranty_type, parse_screen_size_inches_value, score_cpu_tier
from .config_service import ProcurementConfigService
from .deployment_text import build_deployment_phrase


class ProcurementRulesEngine:
    GPU_TIER_ORDER = {
        "integrated": 1,
        "entry_discrete": 2,
        "performance": 3,
        "workstation": 4,
    }

    def __init__(self, config_service=None):
        self.config_service = config_service or ProcurementConfigService()

    def build_target_profile(self, requirements):
        requirements = requirements or {}
        rules_config = self.config_service.get_rules_config()
        workload_targets = rules_config.get("workload_targets") or {}
        workload_spec_floors = rules_config.get("workload_spec_floors") or {}
        subprofile_targets = rules_config.get("subprofile_targets") or {}
        explicit_categories = [
            category
            for category in (requirements.get("preferred_categories") or [])
            if category and category != "not_sure"
        ]
        categories = list(explicit_categories)
        workloads = list(requirements.get("workloads") or [])
        applied_rules = []

        if not workloads and not categories and rules_config.get("allow_default_workload_without_signal"):
            default_workload = rules_config.get("default_workload") or "office_productivity"
            workloads = [default_workload]
            self._record_rule(
                applied_rules,
                "fallback_workload",
                default_workload,
                detail={"reason": "default_workload_enabled"},
            )

        target = {
            "categories": [],
            "min_ram_gb": 0,
            "min_storage_gb": 0,
            "preferred_ram_gb": 0,
            "preferred_storage_gb": 0,
            "min_cpu_score": 2,
            "min_gpu_tier": "integrated",
            "required_printer_type": None,
            "required_print_technology": None,
            "required_color_output": None,
            "min_print_speed_ppm": 0,
            "min_monthly_duty_cycle_pages": 0,
            "required_duplex_printing": False,
            "required_scanner": False,
            "required_automatic_document_feeder": False,
            "required_paper_sizes": [],
            "required_accessory_type": None,
            "recommended_quantity": 1,
            "budget": requirements.get("budget"),
            "growth_expectation": requirements.get("growth_expectation") or "steady",
            "performance_priority": requirements.get("performance_priority") or "balanced",
            "portability_need": requirements.get("portability_need"),
            "support_expectation": requirements.get("support_expectation"),
            "min_support_score": 0,
            "min_warranty_years": 0,
            "battery_life_hours_min": 0,
            "cpu_preference": None,
            "gpu_requirement": None,
            "screen_size_preference": None,
            "screen_size_inches_target": None,
            "weight_kg_max": None,
            "warranty_type_preference": None,
            "required_virtualization_ready": False,
            "required_virtualization_platforms": [],
            "required_network_roles": [],
            "required_port_count": 0,
            "required_vpn_user_capacity": 0,
            "required_throughput_mbps": 0,
            "max_rack_units": None,
            "max_power_draw_watts": None,
            "infrastructure_scales": [],
            "application_signals": list(requirements.get("application_signals") or []),
            "capability_tags": list(requirements.get("capability_tags") or []),
            "applied_rules": applied_rules,
            "resolution_state": "resolved",
        }

        for workload in workloads:
            profile = workload_targets.get(workload, {})
            categories = self._apply_profile(
                target,
                categories,
                profile,
                apply_categories=not explicit_categories,
                rule_type="workload_profile",
                rule_name=workload,
                applied_rules=applied_rules,
            )

        resolved_subprofiles = self._detect_subprofiles(requirements, workloads, rules_config)
        for subprofile_name in resolved_subprofiles:
            profile = subprofile_targets.get(subprofile_name, {})
            categories = self._apply_profile(
                target,
                categories,
                profile,
                apply_categories=not explicit_categories,
                rule_type="subprofile",
                rule_name=subprofile_name,
                applied_rules=applied_rules,
            )

        self._apply_workload_spec_floors(
            target,
            requirements,
            workload_spec_floors,
            applied_rules,
        )
        self._apply_capability_adjustments(target, requirements, rules_config, applied_rules)
        self._apply_explicit_requirements(target, requirements, applied_rules)
        categories = self._apply_existing_infrastructure_hooks(
            requirements,
            categories,
            explicit_categories,
            target,
            rules_config,
            applied_rules,
        )
        self._apply_intent_adjustments(requirements, workloads + resolved_subprofiles, target, rules_config, applied_rules)
        self._apply_growth_adjustment(target, rules_config, applied_rules)
        self._apply_performance_adjustment(target, rules_config, applied_rules)
        self._apply_infrastructure_sizing(requirements, categories, target, rules_config, applied_rules)
        self._apply_compatibility_requirements(
            requirements,
            categories,
            workloads + resolved_subprofiles,
            target,
            applied_rules,
        )
        categories = self._apply_portability_rules(requirements, categories, explicit_categories, rules_config, applied_rules)
        self._apply_support_expectation(target, requirements, rules_config, applied_rules)

        if not categories and not workloads:
            target["resolution_state"] = "needs_clarification"
            self._record_rule(
                applied_rules,
                "clarification_gate",
                "missing_category_and_workload",
                detail={"reason": "no_category_or_workload_signal"},
            )
        elif not categories:
            target["resolution_state"] = "needs_category_clarification"
            self._record_rule(
                applied_rules,
                "clarification_gate",
                "missing_category_resolution",
                detail={"reason": "workload_present_but_category_not_resolved"},
            )

        target["categories"] = categories
        target["resolved_workloads"] = workloads + resolved_subprofiles
        target["recommended_quantity"] = self._recommended_quantity(requirements, categories)
        target["summary"] = self._build_summary(categories, workloads + resolved_subprofiles, requirements, target["resolution_state"])
        return target

    def _apply_profile(self, target, categories, profile, apply_categories, rule_type, rule_name, applied_rules):
        if not profile:
            return categories

        if apply_categories:
            for category in profile.get("categories", []):
                if category not in categories:
                    categories.append(category)

        self._apply_target_adjustment(target, profile)
        self._record_rule(
            applied_rules,
            rule_type,
            rule_name,
            detail={
                "categories": profile.get("categories", []),
                "min_ram_gb": profile.get("min_ram_gb", 0),
                "min_storage_gb": profile.get("min_storage_gb", 0),
                "min_cpu_score": profile.get("min_cpu_score", 0),
                "min_gpu_tier": profile.get("min_gpu_tier"),
                "min_support_score": profile.get("min_support_score", 0),
                "min_warranty_years": profile.get("min_warranty_years", 0),
            },
        )
        return categories

    def _apply_workload_spec_floors(self, target, requirements, workload_spec_floors, applied_rules):
        if not workload_spec_floors:
            return

        signal_names = []
        for value in list(requirements.get("workloads") or []) + list(requirements.get("application_signals") or []):
            normalized = str(value or "").strip().lower()
            if normalized and normalized not in signal_names:
                signal_names.append(normalized)

        for signal_name in signal_names:
            floor = dict(workload_spec_floors.get(signal_name) or {})
            if not floor:
                continue
            self._apply_target_adjustment(target, floor)
            self._record_rule(
                applied_rules,
                "workload_spec_floor",
                signal_name,
                detail=floor,
            )

    def _apply_capability_adjustments(self, target, requirements, rules_config, applied_rules):
        capability_adjustments = rules_config.get("capability_tag_adjustments") or {}
        for tag in requirements.get("capability_tags") or []:
            adjustment = capability_adjustments.get(tag) or {}
            if not adjustment:
                continue
            self._apply_target_adjustment(target, adjustment)
            self._record_rule(
                applied_rules,
                "capability_tag",
                tag,
                detail=adjustment,
            )

    def _apply_explicit_requirements(self, target, requirements, applied_rules):
        if requirements.get("requested_ram_gb") is not None and requirements.get("requested_ram_is_minimum", True):
            target["min_ram_gb"] = max(target["min_ram_gb"], requirements["requested_ram_gb"])
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "requested_ram_minimum",
                detail={"requested_ram_gb": requirements["requested_ram_gb"]},
            )
        elif requirements.get("requested_ram_gb") is not None:
            target["preferred_ram_gb"] = max(target["preferred_ram_gb"], requirements["requested_ram_gb"])
            self._record_rule(
                applied_rules,
                "explicit_preference",
                "requested_ram_preference",
                detail={"requested_ram_gb": requirements["requested_ram_gb"]},
            )

        if requirements.get("requested_storage_gb") is not None and requirements.get("requested_storage_is_minimum", True):
            target["min_storage_gb"] = max(target["min_storage_gb"], requirements["requested_storage_gb"])
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "requested_storage_minimum",
                detail={"requested_storage_gb": requirements["requested_storage_gb"]},
            )
        elif requirements.get("requested_storage_gb") is not None:
            target["preferred_storage_gb"] = max(target["preferred_storage_gb"], requirements["requested_storage_gb"])
            self._record_rule(
                applied_rules,
                "explicit_preference",
                "requested_storage_preference",
                detail={"requested_storage_gb": requirements["requested_storage_gb"]},
            )

        if requirements.get("minimum_warranty_years") is not None:
            target["min_warranty_years"] = max(
                target["min_warranty_years"],
                int(requirements["minimum_warranty_years"]),
            )
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "minimum_warranty_years",
                detail={"minimum_warranty_years": int(requirements["minimum_warranty_years"])},
            )

        if requirements.get("required_port_count") is not None:
            target["required_port_count"] = max(
                target["required_port_count"],
                int(requirements["required_port_count"]),
            )
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "required_port_count",
                detail={"required_port_count": int(requirements["required_port_count"])},
            )

        if requirements.get("required_throughput_mbps") is not None:
            target["required_throughput_mbps"] = max(
                target["required_throughput_mbps"],
                int(requirements["required_throughput_mbps"]),
            )
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "required_throughput_mbps",
                detail={"required_throughput_mbps": int(requirements["required_throughput_mbps"])},
            )

        if requirements.get("required_duplex_printing") is True:
            target["required_duplex_printing"] = True
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "required_duplex_printing",
                detail={"required_duplex_printing": True},
            )

        if requirements.get("required_scanner") is True:
            target["required_scanner"] = True
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "required_scanner",
                detail={"required_scanner": True},
            )

        if requirements.get("min_print_speed_ppm") is not None:
            target["min_print_speed_ppm"] = max(
                target["min_print_speed_ppm"],
                int(requirements["min_print_speed_ppm"]),
            )
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "min_print_speed_ppm",
                detail={"min_print_speed_ppm": int(requirements["min_print_speed_ppm"])},
            )

        if requirements.get("required_printer_type"):
            target["required_printer_type"] = str(requirements["required_printer_type"]).strip().lower()
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "required_printer_type",
                detail={"required_printer_type": target["required_printer_type"]},
            )

        if requirements.get("required_print_technology"):
            target["required_print_technology"] = str(requirements["required_print_technology"]).strip().lower()
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "required_print_technology",
                detail={"required_print_technology": target["required_print_technology"]},
            )

        if requirements.get("required_color_output"):
            target["required_color_output"] = str(requirements["required_color_output"]).strip().lower()
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "required_color_output",
                detail={"required_color_output": target["required_color_output"]},
            )

        if requirements.get("min_monthly_duty_cycle_pages") is not None:
            target["min_monthly_duty_cycle_pages"] = max(
                target["min_monthly_duty_cycle_pages"],
                int(requirements["min_monthly_duty_cycle_pages"]),
            )
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "min_monthly_duty_cycle_pages",
                detail={"min_monthly_duty_cycle_pages": int(requirements["min_monthly_duty_cycle_pages"])},
            )

        if requirements.get("required_automatic_document_feeder") is True:
            target["required_automatic_document_feeder"] = True
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "required_automatic_document_feeder",
                detail={"required_automatic_document_feeder": True},
            )

        if requirements.get("required_paper_sizes"):
            target["required_paper_sizes"] = list(
                dict.fromkeys(str(size or "").strip().upper() for size in requirements["required_paper_sizes"] if str(size or "").strip())
            )
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "required_paper_sizes",
                detail={"required_paper_sizes": target["required_paper_sizes"]},
            )

        if requirements.get("required_network_roles"):
            target["required_network_roles"] = list(
                dict.fromkeys(str(role or "").strip().lower() for role in requirements["required_network_roles"] if str(role or "").strip())
            )
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "required_network_roles",
                detail={"required_network_roles": target["required_network_roles"]},
            )

        if requirements.get("required_vpn_user_capacity") is not None:
            target["required_vpn_user_capacity"] = max(
                target["required_vpn_user_capacity"],
                int(requirements["required_vpn_user_capacity"]),
            )
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "required_vpn_user_capacity",
                detail={"required_vpn_user_capacity": int(requirements["required_vpn_user_capacity"])},
            )

        if requirements.get("required_virtualization_ready") is True:
            target["required_virtualization_ready"] = True
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "required_virtualization_ready",
                detail={"required_virtualization_ready": True},
            )

        if requirements.get("required_virtualization_platforms"):
            target["required_virtualization_platforms"] = list(
                dict.fromkeys(str(platform or "").strip().lower() for platform in requirements["required_virtualization_platforms"] if str(platform or "").strip())
            )
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "required_virtualization_platforms",
                detail={"required_virtualization_platforms": target["required_virtualization_platforms"]},
            )

        if requirements.get("max_rack_units") is not None:
            target["max_rack_units"] = float(requirements["max_rack_units"])
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "max_rack_units",
                detail={"max_rack_units": target["max_rack_units"]},
            )

        if requirements.get("max_power_draw_watts") is not None:
            target["max_power_draw_watts"] = int(requirements["max_power_draw_watts"])
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "max_power_draw_watts",
                detail={"max_power_draw_watts": target["max_power_draw_watts"]},
            )

        if requirements.get("battery_life_hours_min") is not None:
            target["battery_life_hours_min"] = max(
                int(target.get("battery_life_hours_min") or 0),
                int(requirements["battery_life_hours_min"]),
            )
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "battery_life_hours_min",
                detail={"battery_life_hours_min": int(requirements["battery_life_hours_min"])},
            )

        if requirements.get("cpu_preference"):
            target["cpu_preference"] = str(requirements["cpu_preference"]).strip()
            target["min_cpu_score"] = max(
                target["min_cpu_score"],
                score_cpu_tier(requirements["cpu_preference"]),
            )
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "cpu_preference",
                detail={
                    "cpu_preference": target["cpu_preference"],
                    "min_cpu_score": target["min_cpu_score"],
                },
            )

        if requirements.get("gpu_requirement"):
            target["gpu_requirement"] = str(requirements["gpu_requirement"]).strip()
            target["min_gpu_tier"] = self._max_gpu_tier(
                target["min_gpu_tier"],
                normalize_gpu_tier(requirements["gpu_requirement"]),
            )
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "gpu_requirement",
                detail={
                    "gpu_requirement": target["gpu_requirement"],
                    "min_gpu_tier": target["min_gpu_tier"],
                },
            )

        if requirements.get("screen_size_preference"):
            target["screen_size_preference"] = str(requirements["screen_size_preference"]).strip()
            target["screen_size_inches_target"] = parse_screen_size_inches_value(
                requirements["screen_size_preference"]
            )
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "screen_size_preference",
                detail={
                    "screen_size_preference": target["screen_size_preference"],
                    "screen_size_inches_target": target["screen_size_inches_target"],
                },
            )

        if requirements.get("weight_kg_max") is not None:
            target["weight_kg_max"] = float(requirements["weight_kg_max"])
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "weight_kg_max",
                detail={"weight_kg_max": target["weight_kg_max"]},
            )

        if requirements.get("warranty_type_preference"):
            target["warranty_type_preference"] = normalize_warranty_type(
                requirements["warranty_type_preference"]
            ) or str(requirements["warranty_type_preference"]).strip().lower()
            self._record_rule(
                applied_rules,
                "explicit_requirement",
                "warranty_type_preference",
                detail={"warranty_type_preference": target["warranty_type_preference"]},
            )

    def _detect_subprofiles(self, requirements, workloads, rules_config):
        lowered = self._combined_text(requirements)
        workload_set = set(workloads or [])
        resolved = []
        for rule in rules_config.get("subprofile_rules") or []:
            required_workloads = set(rule.get("requires_workloads") or [])
            if required_workloads and not workload_set.intersection(required_workloads):
                continue
            if any(token in lowered for token in rule.get("keywords", [])):
                target_name = rule.get("target")
                if target_name and target_name not in resolved:
                    resolved.append(target_name)
        return resolved

    def _apply_existing_infrastructure_hooks(self, requirements, categories, explicit_categories, target, rules_config, applied_rules):
        existing_infrastructure = {
            str(item or "").strip().lower()
            for item in (requirements.get("existing_infrastructure") or [])
            if str(item or "").strip()
        }
        if not existing_infrastructure:
            return categories

        current_categories = list(categories)
        category_set = set(current_categories)
        for hook in rules_config.get("existing_infrastructure_hooks") or []:
            hook_matches = set(str(token or "").strip().lower() for token in hook.get("match_any", []))
            if not hook_matches.intersection(existing_infrastructure):
                continue
            applies_to_categories = set(hook.get("applies_to_categories") or [])
            if applies_to_categories and category_set and not category_set.intersection(applies_to_categories):
                continue
            if hook.get("only_if_not_explicit_category") and explicit_categories:
                continue

            restrict_categories_to = set(hook.get("restrict_categories_to") or [])
            if restrict_categories_to:
                filtered = [category for category in current_categories if category in restrict_categories_to]
                if filtered:
                    current_categories = filtered
                elif not current_categories:
                    current_categories = list(restrict_categories_to)
                category_set = set(current_categories)

            self._apply_target_adjustment(target, hook)
            self._record_rule(
                applied_rules,
                "existing_infrastructure_hook",
                hook.get("name") or "unnamed_hook",
                detail={"matched_infrastructure": sorted(hook_matches.intersection(existing_infrastructure))},
            )
        return current_categories

    def _apply_intent_adjustments(self, requirements, workloads, target, rules_config, applied_rules):
        lowered = self._combined_text(requirements)
        workload_set = set(workloads or [])
        intent_adjustments = rules_config.get("intent_adjustments") or {}

        for workload in workload_set:
            for adjustment in intent_adjustments.get(workload, []):
                if any(token in lowered for token in adjustment.get("keywords", [])):
                    self._apply_target_adjustment(target, adjustment)
                    self._record_rule(
                        applied_rules,
                        "intent_adjustment",
                        adjustment.get("name") or workload,
                        detail={"workload": workload, "keywords": adjustment.get("keywords", [])},
                    )

        for adjustment in intent_adjustments.get("global", []):
            if any(token in lowered for token in adjustment.get("keywords", [])):
                self._apply_target_adjustment(target, adjustment)
                self._record_rule(
                    applied_rules,
                    "intent_adjustment",
                    adjustment.get("name") or "global",
                    detail={"workload": "global", "keywords": adjustment.get("keywords", [])},
                )

    def _apply_growth_adjustment(self, target, rules_config, applied_rules):
        growth_expectation = target["growth_expectation"]
        growth_adjustment = (rules_config.get("growth_adjustments") or {}).get(growth_expectation, {})
        if not growth_adjustment:
            return
        if growth_adjustment.get("min_ram_gb"):
            target["min_ram_gb"] += growth_adjustment["min_ram_gb"] if target["min_ram_gb"] else 0
        if growth_adjustment.get("min_storage_gb"):
            target["min_storage_gb"] += growth_adjustment["min_storage_gb"] if target["min_storage_gb"] else 0
        self._record_rule(
            applied_rules,
            "growth_adjustment",
            growth_expectation,
            detail=growth_adjustment,
        )

    def _apply_performance_adjustment(self, target, rules_config, applied_rules):
        performance_priority = target["performance_priority"]
        performance_adjustments = rules_config.get("performance_adjustments") or {}
        if performance_priority == "performance":
            adjustment = performance_adjustments.get("performance") or {}
            if adjustment.get("min_ram_gb"):
                target["min_ram_gb"] += adjustment["min_ram_gb"] if target["min_ram_gb"] else adjustment["min_ram_gb"]
            if adjustment.get("min_storage_gb"):
                target["min_storage_gb"] += adjustment["min_storage_gb"] if target["min_storage_gb"] else adjustment["min_storage_gb"]
            target["min_cpu_score"] = min(
                target["min_cpu_score"] + adjustment.get("min_cpu_score_delta", 0),
                adjustment.get("min_cpu_score_cap", 5),
            )
            self._record_rule(
                applied_rules,
                "performance_adjustment",
                "performance",
                detail=adjustment,
            )
        elif performance_priority == "cost":
            adjustment = performance_adjustments.get("cost") or {}
            reduction = adjustment.get("min_storage_gb_reduction", 0)
            storage_floor = adjustment.get("min_storage_floor_if_present", 0)
            target["min_storage_gb"] = max(
                target["min_storage_gb"] - reduction,
                storage_floor if target["min_storage_gb"] else 0,
            )
            self._record_rule(
                applied_rules,
                "performance_adjustment",
                "cost",
                detail=adjustment,
            )

    def _apply_infrastructure_sizing(self, requirements, categories, target, rules_config, applied_rules):
        team_size = requirements.get("team_size")
        if not team_size:
            return

        growth_multiplier = (rules_config.get("infrastructure_growth_multipliers") or {}).get(
            target["growth_expectation"],
            1.0,
        )
        effective_team_size = max(int(math.ceil(team_size * growth_multiplier)), team_size)
        sizing_rules = rules_config.get("infrastructure_sizing_rules") or {}

        for category in ("servers", "networking"):
            if category not in set(categories or []):
                continue
            matching_rule = self._matching_infrastructure_rule(
                sizing_rules.get(category) or [],
                effective_team_size,
            )
            if not matching_rule:
                continue
            self._apply_target_adjustment(target, matching_rule)
            infrastructure_scale = matching_rule.get("infrastructure_scale")
            if infrastructure_scale and infrastructure_scale not in target["infrastructure_scales"]:
                target["infrastructure_scales"].append(infrastructure_scale)
            self._record_rule(
                applied_rules,
                "infrastructure_sizing",
                matching_rule.get("name") or category,
                detail={"category": category, "effective_team_size": effective_team_size},
            )

    def _apply_portability_rules(self, requirements, categories, explicit_categories, rules_config, applied_rules):
        portability_rules = rules_config.get("portability_rules") or {}
        current_categories = list(categories)
        if requirements.get("portability_need") != "high":
            return current_categories

        high_portability_rule = portability_rules.get("high") or {}
        if explicit_categories:
            restrict_categories = high_portability_rule.get("restrict_categories_to") or ["laptops"]
            filtered = [category for category in current_categories if category in restrict_categories]
            if filtered:
                current_categories = filtered
        else:
            preferred_category = high_portability_rule.get("insert_category_if_missing") or "laptops"
            if current_categories:
                filtered = [category for category in current_categories if category == preferred_category]
                if filtered:
                    current_categories = filtered
                elif preferred_category not in current_categories:
                    current_categories.insert(0, preferred_category)
            else:
                current_categories = [preferred_category]

        self._record_rule(
            applied_rules,
            "portability_rule",
            "high_portability",
            detail=high_portability_rule,
        )
        return current_categories

    def _apply_support_expectation(self, target, requirements, rules_config, applied_rules):
        support_requirements = rules_config.get("support_expectation_requirements") or {}
        support_expectation = requirements.get("support_expectation")
        if support_expectation not in support_requirements:
            target["min_support_score"] = max(target["min_support_score"], 0)
            return

        support_profile = support_requirements[support_expectation]
        self._apply_target_adjustment(target, support_profile)
        self._record_rule(
            applied_rules,
            "support_expectation",
            support_expectation,
            detail=support_profile,
        )

    def _apply_compatibility_requirements(self, requirements, categories, resolved_workloads, target, applied_rules):
        categories = set(categories or [])
        lowered = self._combined_text(requirements)
        capability_tags = set(target.get("capability_tags") or [])
        infrastructure_scales = set(target.get("infrastructure_scales") or [])
        team_size = int(requirements.get("team_size") or 0)

        if "servers" in categories:
            virtualization_required = bool(
                capability_tags.intersection({"virtualization"})
                or "server_infrastructure" in set(resolved_workloads or [])
                or any(token in lowered for token in {"virtualization", "vmware", "hyper-v", "proxmox", "hypervisor"})
            )
            if virtualization_required and not target.get("required_virtualization_ready"):
                target["required_virtualization_ready"] = True
                platforms = list(target.get("required_virtualization_platforms") or [])
                if any(token in lowered for token in {"vmware", "esxi"}):
                    platforms.append("vmware")
                if any(token in lowered for token in {"hyper-v", "hyper v"}):
                    platforms.append("hyper-v")
                if "proxmox" in lowered:
                    platforms.append("proxmox")
                if "kvm" in lowered:
                    platforms.append("kvm")
                target["required_virtualization_platforms"] = list(dict.fromkeys(platforms))
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "virtualization_ready_required",
                    detail={"platforms": platforms},
                )

            if (
                any(token in lowered for token in {"small office", "small rack", "edge closet", "branch office"})
                and target.get("max_rack_units") in {None, ""}
            ):
                target["max_rack_units"] = 2.0
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "small_footprint_server_limit",
                    detail={"max_rack_units": 2.0},
                )

            if (
                any(token in lowered for token in {"limited power", "power constrained", "branch office", "small office"})
                and not target.get("max_power_draw_watts")
            ):
                target["max_power_draw_watts"] = 900
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "server_power_budget_limit",
                    detail={"max_power_draw_watts": 900},
                )

        if "networking" in categories:
            required_roles = []
            if any(token in lowered for token in {"switch", "switching", "poe", "access layer", "vlan"}):
                required_roles.append("switch")
            if any(token in lowered for token in {"router", "vpn", "firewall", "sd-wan", "secure branch"}):
                required_roles.extend(["router", "firewall"])
            if not target.get("required_network_roles"):
                target["required_network_roles"] = list(dict.fromkeys(required_roles))
            if target["required_network_roles"]:
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "network_role_required",
                    detail={"required_network_roles": target["required_network_roles"]},
                )

            if "switch" in target["required_network_roles"] and team_size and not target.get("required_port_count"):
                target["required_port_count"] = team_size
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "switch_port_capacity_required",
                    detail={"required_port_count": team_size},
                )

            if {"router", "firewall"}.intersection(target["required_network_roles"]) and team_size and not target.get("required_vpn_user_capacity"):
                target["required_vpn_user_capacity"] = team_size
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "vpn_capacity_required",
                    detail={"required_vpn_user_capacity": team_size},
                )

            if team_size and not target.get("required_throughput_mbps"):
                throughput_floor = max(200, team_size * 10)
                if "network_large_branch" in infrastructure_scales:
                    throughput_floor = max(throughput_floor, 1000)
                elif "network_mid_branch" in infrastructure_scales:
                    throughput_floor = max(throughput_floor, 500)
                target["required_throughput_mbps"] = throughput_floor
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "network_throughput_required",
                    detail={"required_throughput_mbps": throughput_floor},
                )

        if "printers" in categories:
            if not target.get("required_printer_type") and any(token in lowered for token in {"label printer", "shipping label", "barcode label"}):
                target["required_printer_type"] = "label_printer"
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "label_printer_required",
                    detail={"required_printer_type": "label_printer"},
                )
            elif not target.get("required_printer_type") and any(token in lowered for token in {"photo printer", "photo prints"}):
                target["required_printer_type"] = "photo_printer"
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "photo_printer_required",
                    detail={"required_printer_type": "photo_printer"},
                )
            elif not target.get("required_printer_type") and any(token in lowered for token in {"wide format", "plotter", "a3"}):
                target["required_printer_type"] = "wide_format_printer"
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "wide_format_printer_required",
                    detail={"required_printer_type": "wide_format_printer"},
                )

            if not target.get("required_print_technology") and any(token in lowered for token in {"laser printer", "laser"}):
                target["required_print_technology"] = "laser"
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "laser_printing_required",
                    detail={"required_print_technology": "laser"},
                )
            elif not target.get("required_print_technology") and any(token in lowered for token in {"ink tank", "inktank"}):
                target["required_print_technology"] = "ink tank"
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "ink_tank_printing_required",
                    detail={"required_print_technology": "ink tank"},
                )
            elif not target.get("required_print_technology") and any(token in lowered for token in {"inkjet"}):
                target["required_print_technology"] = "inkjet"
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "inkjet_printing_required",
                    detail={"required_print_technology": "inkjet"},
                )

            if not target.get("required_color_output") and any(token in lowered for token in {"mono", "monochrome", "black and white", "b/w"}):
                target["required_color_output"] = "mono"
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "mono_printing_required",
                    detail={"required_color_output": "mono"},
                )
            elif not target.get("required_color_output") and any(token in lowered for token in {"color", "colour"}):
                target["required_color_output"] = "color"
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "color_printing_required",
                    detail={"required_color_output": "color"},
                )

            if any(token in lowered for token in {"duplex", "double-sided", "double sided"}) and not target.get("required_duplex_printing"):
                target["required_duplex_printing"] = True
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "duplex_printing_required",
                    detail={"required_duplex_printing": True},
                )

            if any(token in lowered for token in {"scanner", "scan", "copy", "all in one", "all-in-one", "mfp"}) and not target.get("required_scanner"):
                target["required_scanner"] = True
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "scanner_required",
                    detail={"required_scanner": True},
                )

            if any(token in lowered for token in {"adf", "automatic document feeder"}) and not target.get("required_automatic_document_feeder"):
                target["required_automatic_document_feeder"] = True
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "automatic_document_feeder_required",
                    detail={"required_automatic_document_feeder": True},
                )

            required_paper_sizes = []
            for token in ("A3", "A4", "LETTER", "LEGAL"):
                if token.lower() in lowered:
                    required_paper_sizes.append(token)
            if required_paper_sizes and not target.get("required_paper_sizes"):
                target["required_paper_sizes"] = required_paper_sizes
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "printer_paper_size_required",
                    detail={"required_paper_sizes": required_paper_sizes},
                )

            explicit_speed = self._extract_integer_before_token(lowered, "ppm")
            if explicit_speed and not target.get("min_print_speed_ppm"):
                target["min_print_speed_ppm"] = explicit_speed
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "printer_speed_required",
                    detail={"min_print_speed_ppm": explicit_speed},
                )
            elif team_size:
                inferred_speed = 20 if team_size >= 15 else 12
                target["min_print_speed_ppm"] = max(target["min_print_speed_ppm"], inferred_speed)
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "printer_speed_inferred",
                    detail={"min_print_speed_ppm": inferred_speed, "team_size": team_size},
                )

            explicit_duty_cycle = self._extract_page_volume(lowered)
            if explicit_duty_cycle and not target.get("min_monthly_duty_cycle_pages"):
                target["min_monthly_duty_cycle_pages"] = explicit_duty_cycle
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "printer_duty_cycle_required",
                    detail={"min_monthly_duty_cycle_pages": explicit_duty_cycle},
                )
            elif team_size:
                inferred_duty_cycle = max(team_size * 250, 1500)
                target["min_monthly_duty_cycle_pages"] = max(
                    target["min_monthly_duty_cycle_pages"],
                    inferred_duty_cycle,
                )
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "printer_duty_cycle_inferred",
                    detail={"min_monthly_duty_cycle_pages": inferred_duty_cycle, "team_size": team_size},
                )

        if "accessories" in categories:
            required_accessory_type = None
            if any(token in lowered for token in {"keyboard", "keyboards"}):
                required_accessory_type = "keyboard"
            elif any(token in lowered for token in {"mouse", "mice"}):
                required_accessory_type = "mouse"
            elif any(token in lowered for token in {"headset", "headsets", "headphone", "headphones"}):
                required_accessory_type = "headset"
            elif "webcam" in lowered:
                required_accessory_type = "webcam"
            elif "monitor" in lowered:
                required_accessory_type = "monitor"
            elif "dock" in lowered:
                required_accessory_type = "dock"

            if required_accessory_type:
                target["required_accessory_type"] = required_accessory_type
                self._record_rule(
                    applied_rules,
                    "compatibility_requirement",
                    "accessory_type_required",
                    detail={"required_accessory_type": required_accessory_type},
                )

    def _matching_infrastructure_rule(self, rules, effective_team_size):
        for rule in rules or []:
            min_team_size = int(rule.get("min_team_size") or 0)
            max_team_size = rule.get("max_team_size")
            if effective_team_size < min_team_size:
                continue
            if max_team_size is not None and effective_team_size > int(max_team_size):
                continue
            return rule
        return None

    def _recommended_quantity(self, requirements, categories):
        explicit_quantity = requirements.get("quantity")
        if explicit_quantity:
            return explicit_quantity
        seat_based_categories = set(self.config_service.get_rules_config().get("seat_based_categories") or [])
        if set(categories or []).intersection(seat_based_categories):
            return requirements.get("team_size") or 1
        if "accessories" in set(categories or []) and requirements.get("team_size"):
            return requirements.get("team_size") or 1
        return 1

    def _build_summary(self, categories, workloads, requirements, resolution_state):
        if resolution_state == "needs_clarification":
            return "Built a partially resolved target profile, but product category and workload still need clarification before ranking."
        if resolution_state == "needs_category_clarification":
            workload_text = ", ".join(workloads) if workloads else "the current workload hints"
            return f"Built a workload-aware target profile for {workload_text}, but product category still needs clarification before ranking."

        category_text = ", ".join(categories)
        deployment_phrase = build_deployment_phrase(
            requirements,
            categories,
            seat_based_categories=self.config_service.get_rules_config().get("seat_based_categories") or [],
        )
        if not workloads:
            return (
                f"Built a target profile {deployment_phrase} across {category_text}, "
                "but workload and application details are still unresolved."
            )
        workload_text = ", ".join(workloads)
        return (
            f"Built a target profile {deployment_phrase} across {category_text} "
            f"with workload focus on {workload_text}."
        )

    def _apply_target_adjustment(self, target, adjustment):
        if adjustment.get("min_ram_gb"):
            target["min_ram_gb"] = max(target["min_ram_gb"], adjustment["min_ram_gb"]) if target["min_ram_gb"] else adjustment["min_ram_gb"]
        if adjustment.get("min_storage_gb"):
            target["min_storage_gb"] = max(target["min_storage_gb"], adjustment["min_storage_gb"]) if target["min_storage_gb"] else adjustment["min_storage_gb"]
        if adjustment.get("preferred_ram_gb"):
            target["preferred_ram_gb"] = max(target["preferred_ram_gb"], adjustment["preferred_ram_gb"])
        if adjustment.get("preferred_storage_gb"):
            target["preferred_storage_gb"] = max(target["preferred_storage_gb"], adjustment["preferred_storage_gb"])
        if adjustment.get("min_cpu_score"):
            target["min_cpu_score"] = max(target["min_cpu_score"], adjustment["min_cpu_score"])
        if adjustment.get("min_support_score"):
            target["min_support_score"] = max(target["min_support_score"], adjustment["min_support_score"])
        if adjustment.get("min_warranty_years"):
            target["min_warranty_years"] = max(target["min_warranty_years"], adjustment["min_warranty_years"])
        if adjustment.get("min_gpu_tier"):
            target["min_gpu_tier"] = self._max_gpu_tier(target["min_gpu_tier"], adjustment["min_gpu_tier"])
        if adjustment.get("infrastructure_scale"):
            scale = adjustment["infrastructure_scale"]
            if scale not in target["infrastructure_scales"]:
                target["infrastructure_scales"].append(scale)

    def _combined_text(self, requirements):
        return " ".join(
            str(part or "")
            for part in (
                requirements.get("raw_chat"),
                requirements.get("notes"),
            )
        ).lower()

    def _max_gpu_tier(self, current_tier, next_tier):
        current_value = self.GPU_TIER_ORDER.get(current_tier or "integrated", 1)
        next_value = self.GPU_TIER_ORDER.get(next_tier or "integrated", 1)
        return current_tier if current_value >= next_value else next_tier

    def _record_rule(self, applied_rules, rule_type, name, detail=None):
        applied_rules.append(
            {
                "type": rule_type,
                "name": name,
                "detail": detail or {},
            }
        )

    def _extract_integer_before_token(self, lowered, token):
        lowered = str(lowered or "")
        token = str(token or "")
        if not lowered or not token:
            return 0
        match = re.search(rf"(\d+)\s*{re.escape(token)}", lowered)
        return int(match.group(1)) if match else 0

    def _extract_page_volume(self, lowered):
        lowered = str(lowered or "").replace(",", "")
        if not lowered:
            return 0
        match = re.search(r"(\d+)\s*(?:pages?|prints?)\s*(?:per month|monthly|a month)", lowered)
        if match:
            return int(match.group(1))
        match = re.search(r"(\d+)k\s*(?:pages?|prints?)\s*(?:per month|monthly|a month)", lowered)
        if match:
            return int(match.group(1)) * 1000
        return 0

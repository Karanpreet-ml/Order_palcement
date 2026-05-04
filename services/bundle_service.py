from .compatibility import ProcurementCompatibilityService


class ProcurementBundleService:
    SUPPORTED_ACCESSORY_ADD_ON_TYPES = {"keyboard", "mouse", "headset"}

    def __init__(self, compatibility_service=None):
        self.compatibility_service = compatibility_service or ProcurementCompatibilityService()

    def build_bundle_result(self, requirements, recommendation_groups, multi_intent_policy, selected_template=None):
        requirements = dict(requirements or {})
        recommendation_groups = list(recommendation_groups or [])
        multi_intent_policy = dict(multi_intent_policy or {})
        selected_template = dict(selected_template or {})

        bundle_candidate = self._build_bundle_candidate(
            requirements=requirements,
            recommendation_groups=recommendation_groups,
            multi_intent_policy=multi_intent_policy,
            selected_template=selected_template,
        )
        if not bundle_candidate:
            return {
                "bundle_validated": False,
                "bundle_candidate": {},
                "bundle_compatibility_report": {},
                "bundle_conflict_codes": [],
                "bundle_capacity_summary": {},
                "bundle_options": [],
                "architecture_graph": {},
                "merge_rules": [],
                "summary": "Bundle assembly requires a selected scenario template before a formal bundle can be validated.",
            }

        bundle_report = self.compatibility_service.evaluate_bundle(
            bundle_candidate=bundle_candidate,
            requirements=requirements,
            recommendation_groups=recommendation_groups,
            multi_intent_policy=multi_intent_policy,
        )
        architecture_graph = self._build_architecture_graph(bundle_candidate, bundle_report)
        bundle_option = self._build_bundle_option(bundle_candidate, bundle_report, architecture_graph)
        merge_rules = self._build_merge_rules(bundle_candidate, bundle_report)

        return {
            "bundle_validated": bool(bundle_report.get("passed")),
            "bundle_candidate": bundle_candidate,
            "bundle_compatibility_report": bundle_report,
            "bundle_conflict_codes": list(bundle_report.get("bundle_conflict_codes") or []),
            "bundle_capacity_summary": bundle_report.get("capacity_summary") or {},
            "bundle_options": [bundle_option],
            "architecture_graph": architecture_graph,
            "merge_rules": merge_rules,
            "summary": self._build_summary(bundle_candidate, bundle_report),
        }

    def _build_bundle_candidate(self, requirements, recommendation_groups, multi_intent_policy, selected_template):
        if (
            not recommendation_groups
            or not selected_template.get("template_id")
            or not selected_template.get("selection_allowed", True)
        ):
            return {}

        assignments = []
        total_estimated_cost = 0
        total_required_quantity = 0
        total_covered_quantity = 0
        total_quantity_gap = 0
        template_quantity_strategy = str(selected_template.get("quantity_strategy") or "").strip().lower()
        template_budget_strategy = str(selected_template.get("budget_strategy") or "").strip().lower()

        for index, group in enumerate(recommendation_groups, start=1):
            group = dict(group or {})
            recommendation = dict((group.get("recommendations") or [{}])[0] or {})
            target_profile = dict(group.get("target_profile") or {})
            group_requirements = dict(group.get("requirements") or {})
            group_selected_template = dict(group.get("selected_template") or {})

            quantity_required = self._resolve_quantity_required(
                recommendation=recommendation,
                target_profile=target_profile,
                group_requirements=group_requirements,
                template_quantity_strategy=template_quantity_strategy,
            )
            stock_quantity = recommendation.get("stock_quantity")
            quantity_covered = quantity_required if stock_quantity in {None, ""} else min(int(stock_quantity), quantity_required)
            quantity_gap = max(quantity_required - quantity_covered, 0)
            role = self._derive_role(group, recommendation, index)
            estimated_total_cost = recommendation.get("estimated_total_cost")
            if estimated_total_cost is None and recommendation.get("price") is not None:
                estimated_total_cost = int(recommendation.get("price")) * quantity_required

            assignment = {
                "group_id": group.get("group_id"),
                "label": group.get("label"),
                "role_id": role.get("role_id"),
                "role_label": role.get("role_label"),
                "role_type": role.get("role_type"),
                "group_template_id": group_selected_template.get("template_id"),
                "group_template_version": group_selected_template.get("template_version"),
                "group_template_match_quality": group_selected_template.get("template_match_quality"),
                "group_template_required_roles": list(group_selected_template.get("required_roles") or []),
                "group_template_quantity_strategy": group_selected_template.get("quantity_strategy"),
                "group_template_budget_strategy": group_selected_template.get("budget_strategy"),
                "category": group.get("category"),
                "workloads": list(group.get("workloads") or []),
                "purchase_scope": group_requirements.get("purchase_scope"),
                "team_size": group_requirements.get("team_size"),
                "target_categories": list(target_profile.get("categories") or []),
                "target_infrastructure_scales": list(target_profile.get("infrastructure_scales") or []),
                "target_capability_tags": list(target_profile.get("capability_tags") or []),
                "required_virtualization_ready": bool(target_profile.get("required_virtualization_ready")),
                "required_virtualization_platforms": list(target_profile.get("required_virtualization_platforms") or []),
                "required_network_roles": list(target_profile.get("required_network_roles") or []),
                "required_port_count": int(target_profile.get("required_port_count") or 0),
                "required_vpn_user_capacity": int(target_profile.get("required_vpn_user_capacity") or 0),
                "required_throughput_mbps": int(target_profile.get("required_throughput_mbps") or 0),
                "max_rack_units": target_profile.get("max_rack_units"),
                "max_power_draw_watts": target_profile.get("max_power_draw_watts"),
                "selected_product_id": recommendation.get("product_id"),
                "selected_base_product_id": recommendation.get("product_id"),
                "selected_candidate_id": recommendation.get("candidate_id") or recommendation.get("product_id"),
                "selected_inventory_id": recommendation.get("inventory_id"),
                "selected_product_name": recommendation.get("name"),
                "base_product_id": recommendation.get("product_id"),
                "manufacturer": recommendation.get("manufacturer"),
                "seller": recommendation.get("seller"),
                "store_id": recommendation.get("store_id"),
                "sku_id": recommendation.get("sku_id"),
                "offer_count": recommendation.get("offer_count"),
                "alternate_offer_count": recommendation.get("alternate_offer_count"),
                "fit_status": recommendation.get("fit_status"),
                "network_role": recommendation.get("network_role"),
                "printer_type": recommendation.get("printer_type"),
                "print_technology": recommendation.get("print_technology"),
                "color_output": recommendation.get("color_output"),
                "print_speed_ppm": recommendation.get("print_speed_ppm"),
                "monthly_duty_cycle_pages": recommendation.get("monthly_duty_cycle_pages"),
                "duplex_printing": recommendation.get("duplex_printing"),
                "scanner_type": recommendation.get("scanner_type"),
                "automatic_document_feeder": recommendation.get("automatic_document_feeder"),
                "paper_size_support": list(recommendation.get("paper_size_support") or []),
                "accessory_type": recommendation.get("accessory_type"),
                "connectivity": recommendation.get("connectivity"),
                "port_count": recommendation.get("port_count"),
                "vpn_user_capacity": recommendation.get("vpn_user_capacity"),
                "throughput_mbps": recommendation.get("throughput_mbps"),
                "poe_supported": recommendation.get("poe_supported"),
                "poe_port_count": recommendation.get("poe_port_count"),
                "virtualization_ready": recommendation.get("virtualization_ready"),
                "virtualization_platforms": list(recommendation.get("virtualization_platforms") or []),
                "rack_units": recommendation.get("rack_units"),
                "power_draw_watts": recommendation.get("power_draw_watts"),
                "remote_management": recommendation.get("remote_management"),
                "high_availability_ready": recommendation.get("high_availability_ready"),
                "quantity_required": quantity_required,
                "quantity_covered": quantity_covered,
                "quantity_gap": quantity_gap,
                "stock_quantity": stock_quantity,
                "unit_price": recommendation.get("price"),
                "estimated_total_cost": estimated_total_cost,
                "currency": recommendation.get("currency") or requirements.get("currency"),
                "recommendation_mode": group.get("recommendation_mode"),
                "compatibility_scope": ((group.get("compatibility_report") or {}).get("scope") or "item"),
                "bundle_position": "primary",
                "attachment_required": False,
                "attachment_status": "not_required",
                "attachment_target_group_ids": [],
                "attachment_target_role_ids": [],
                "attachment_target_categories": [],
                "attachment_target_quantity": 0,
            }
            assignments.append(assignment)

            total_required_quantity += quantity_required
            total_covered_quantity += quantity_covered
            total_quantity_gap += quantity_gap
            if estimated_total_cost is not None:
                total_estimated_cost += int(estimated_total_cost)

        self._apply_accessory_attachment_rules(assignments)
        role_coverage = self._build_role_coverage(assignments, selected_template)

        return {
            "bundle_id": "bundle-option-1",
            "label": "Validated bundle candidate",
            "currency": requirements.get("currency"),
            "template_id": selected_template.get("template_id"),
            "template_version": selected_template.get("template_version"),
            "template_required_roles": list(selected_template.get("required_roles") or []),
            "template_quantity_strategy": selected_template.get("quantity_strategy"),
            "template_budget_strategy": selected_template.get("budget_strategy"),
            "template_compatibility_profile": selected_template.get("compatibility_profile"),
            "assignments": assignments,
            "required_group_count": len(recommendation_groups),
            "fulfilled_group_count": len([item for item in assignments if item.get("selected_product_id")]),
            "role_coverage": role_coverage,
            "capacity_summary": {
                "total_quantity_required": total_required_quantity,
                "total_quantity_covered": total_covered_quantity,
                "total_quantity_gap": total_quantity_gap,
                "groups": [
                    {
                        "group_id": assignment.get("group_id"),
                        "label": assignment.get("label"),
                        "role_label": assignment.get("role_label"),
                        "quantity_required": assignment.get("quantity_required"),
                        "quantity_covered": assignment.get("quantity_covered"),
                        "quantity_gap": assignment.get("quantity_gap"),
                        "stock_quantity": assignment.get("stock_quantity"),
                    }
                    for assignment in assignments
                ],
            },
            "total_estimated_cost": total_estimated_cost,
            "shared_budget": multi_intent_policy.get("shared_budget") or {},
        }

    def _apply_accessory_attachment_rules(self, assignments):
        assignments = list(assignments or [])
        host_assignments = [
            assignment
            for assignment in assignments
            if assignment.get("category") in {"laptops", "desktops"}
            and assignment.get("selected_product_id")
        ]
        host_group_ids = [
            assignment.get("group_id")
            for assignment in host_assignments
            if assignment.get("group_id")
        ]
        host_role_ids = [
            assignment.get("role_id")
            for assignment in host_assignments
            if assignment.get("role_id")
        ]
        host_categories = sorted(
            {
                str(assignment.get("category") or "").strip().lower()
                for assignment in host_assignments
                if str(assignment.get("category") or "").strip()
            }
        )
        host_quantity = sum(int(assignment.get("quantity_required") or 0) for assignment in host_assignments)

        for assignment in assignments:
            if assignment.get("category") != "accessories":
                assignment["bundle_position"] = "primary"
                continue

            accessory_type = str(assignment.get("accessory_type") or "").strip().lower()
            is_supported_add_on = accessory_type in self.SUPPORTED_ACCESSORY_ADD_ON_TYPES
            assignment["bundle_position"] = "add_on" if is_supported_add_on else "standalone"
            assignment["attachment_required"] = is_supported_add_on
            assignment["attachment_target_group_ids"] = list(host_group_ids) if is_supported_add_on else []
            assignment["attachment_target_role_ids"] = list(host_role_ids) if is_supported_add_on else []
            assignment["attachment_target_categories"] = list(host_categories) if is_supported_add_on else []
            assignment["attachment_target_quantity"] = host_quantity if is_supported_add_on else 0
            if not is_supported_add_on:
                assignment["attachment_status"] = "not_required"
            elif host_role_ids:
                assignment["attachment_status"] = "attached"
            else:
                assignment["attachment_status"] = "host_missing"

    def _derive_role(self, group, recommendation, index):
        group = dict(group or {})
        recommendation = dict(recommendation or {})
        target_profile = dict(group.get("target_profile") or {})
        category = str(group.get("category") or recommendation.get("category") or "general").strip().lower()
        workloads = list(group.get("workloads") or [])

        if category == "networking":
            required_roles = list(target_profile.get("required_network_roles") or [])
            role_type = "network_" + "_".join(required_roles) if required_roles else "network_device"
            role_label = group.get("label") or "Networking role"
        elif category == "servers" and target_profile.get("required_virtualization_ready"):
            role_type = "virtualization_server"
            role_label = group.get("label") or "Virtualization server"
        elif workloads:
            role_type = workloads[0]
            role_label = group.get("label") or workloads[0].replace("_", " ").title()
        else:
            role_type = category or f"role_{index}"
            role_label = group.get("label") or role_type.replace("_", " ").title()

        return {
            "role_id": group.get("group_id") or f"role-{index}",
            "role_label": role_label,
            "role_type": role_type,
        }

    def _resolve_quantity_required(self, recommendation, target_profile, group_requirements, template_quantity_strategy):
        recommendation = dict(recommendation or {})
        target_profile = dict(target_profile or {})
        group_requirements = dict(group_requirements or {})
        template_quantity_strategy = str(template_quantity_strategy or "").strip().lower()

        if template_quantity_strategy in {"single_site_reference", "single_reference_network"}:
            return 1

        if template_quantity_strategy in {"team_rollout_by_seat", "per_seat_or_single_reference"}:
            return int(
                group_requirements.get("quantity")
                or group_requirements.get("team_size")
                or recommendation.get("estimated_quantity")
                or target_profile.get("recommended_quantity")
                or 1
            )

        return int(
            group_requirements.get("quantity")
            or recommendation.get("estimated_quantity")
            or target_profile.get("recommended_quantity")
            or 1
        )

    def _build_role_coverage(self, assignments, selected_template):
        assignments = list(assignments or [])
        selected_template = dict(selected_template or {})
        required_roles = []
        covered_roles = []
        missing_roles = []
        seen_required = set()
        seen_covered = set()

        for assignment in assignments:
            for role in self._required_role_entries(assignment, selected_template):
                role_key = role["role_key"]
                if role_key in seen_required:
                    continue
                seen_required.add(role_key)
                required_roles.append(role)

        for assignment in assignments:
            if not assignment.get("selected_product_id"):
                continue
            for role in self._provided_role_entries(assignment):
                role_key = role["role_key"]
                if role_key in seen_covered:
                    continue
                seen_covered.add(role_key)
                covered_roles.append(role)

        covered_role_keys = {role["role_key"] for role in covered_roles}
        for role in required_roles:
            if role["role_key"] not in covered_role_keys:
                missing_roles.append(role)

        return {
            "required_role_count": len(required_roles),
            "covered_role_count": len(required_roles) - len(missing_roles),
            "missing_roles": missing_roles,
            "required_roles": required_roles,
            "covered_roles": covered_roles,
            "template_required_roles": list(selected_template.get("required_roles") or []),
        }

    def _required_role_entries(self, assignment, selected_template):
        assignment = dict(assignment or {})
        selected_template = dict(selected_template or {})
        template_required_roles = set(selected_template.get("required_roles") or [])
        group_template_required_roles = [
            str(role or "").strip()
            for role in (assignment.get("group_template_required_roles") or [])
            if str(role or "").strip()
        ]
        group_id = assignment.get("group_id") or assignment.get("role_id") or "group"
        entries = []

        for role in group_template_required_roles:
            entries.append(
                {
                    "role_key": f"{group_id}::{role}",
                    "group_id": assignment.get("group_id"),
                    "role_id": assignment.get("role_id"),
                    "role_label": assignment.get("role_label"),
                    "role_type": role,
                    "required_network_roles": list(assignment.get("required_network_roles") or []),
                    "template_id": assignment.get("group_template_id"),
                }
            )

        if "multi_intent_group" in template_required_roles or not template_required_roles:
            entries.append(
                {
                    "role_key": f"{group_id}::group",
                    "group_id": assignment.get("group_id"),
                    "role_id": assignment.get("role_id"),
                    "role_label": assignment.get("role_label"),
                    "role_type": assignment.get("role_type"),
                    "required_network_roles": list(assignment.get("required_network_roles") or []),
                }
            )

        return entries or [
            {
                "role_key": f"{group_id}::group",
                "group_id": assignment.get("group_id"),
                "role_id": assignment.get("role_id"),
                "role_label": assignment.get("role_label"),
                "role_type": assignment.get("role_type"),
                "required_network_roles": list(assignment.get("required_network_roles") or []),
            }
        ]

    def _provided_role_entries(self, assignment):
        assignment = dict(assignment or {})
        group_id = assignment.get("group_id") or assignment.get("role_id") or "group"
        entries = [
            {
                "role_key": f"{group_id}::group",
                "group_id": assignment.get("group_id"),
                "role_id": assignment.get("role_id"),
                "role_label": assignment.get("role_label"),
                "role_type": assignment.get("role_type"),
                "selected_product_id": assignment.get("selected_product_id"),
                "selected_candidate_id": assignment.get("selected_candidate_id"),
                "selected_inventory_id": assignment.get("selected_inventory_id"),
                "selected_product_name": assignment.get("selected_product_name"),
            }
        ]
        for role in assignment.get("group_template_required_roles") or []:
            role = str(role or "").strip()
            if not role:
                continue
            entries.append(
                {
                    "role_key": f"{group_id}::{role}",
                    "group_id": assignment.get("group_id"),
                    "role_id": assignment.get("role_id"),
                    "role_label": assignment.get("role_label"),
                    "role_type": role,
                    "selected_product_id": assignment.get("selected_product_id"),
                    "selected_candidate_id": assignment.get("selected_candidate_id"),
                    "selected_inventory_id": assignment.get("selected_inventory_id"),
                    "selected_product_name": assignment.get("selected_product_name"),
                    "template_id": assignment.get("group_template_id"),
                }
            )
        return entries

    def _build_architecture_graph(self, bundle_candidate, bundle_report):
        bundle_candidate = dict(bundle_candidate or {})
        bundle_report = dict(bundle_report or {})
        nodes = [
            {
                "id": bundle_candidate.get("bundle_id"),
                "type": "bundle",
                "label": bundle_candidate.get("label"),
                "validated": bool(bundle_report.get("passed")),
            }
        ]
        edges = []
        seen_products = set()
        rationale = []

        for assignment in list(bundle_candidate.get("assignments") or []):
            role_node_id = f"role::{assignment.get('role_id')}"
            nodes.append(
                {
                    "id": role_node_id,
                    "type": "role",
                    "label": assignment.get("role_label"),
                    "category": assignment.get("category"),
                    "quantity_required": assignment.get("quantity_required"),
                }
            )
            edges.append(
                {
                    "source": bundle_candidate.get("bundle_id"),
                    "target": role_node_id,
                    "relationship": "requires_role",
                }
            )
            if assignment.get("selected_product_id"):
                product_node_id = self._assignment_product_node_id(assignment)
                if product_node_id not in seen_products:
                    seen_products.add(product_node_id)
                    nodes.append(
                        {
                            "id": product_node_id,
                            "type": "product",
                            "label": assignment.get("selected_product_name"),
                            "product_id": assignment.get("selected_product_id"),
                            "base_product_id": assignment.get("selected_base_product_id"),
                            "candidate_id": assignment.get("selected_candidate_id"),
                            "inventory_id": assignment.get("selected_inventory_id"),
                            "manufacturer": assignment.get("manufacturer"),
                            "seller": assignment.get("seller"),
                            "store_id": assignment.get("store_id"),
                            "sku_id": assignment.get("sku_id"),
                        }
                    )
                edges.append(
                    {
                        "source": role_node_id,
                        "target": product_node_id,
                        "relationship": "fulfilled_by",
                    }
                )
                rationale.append(
                    "{} is fulfilled by {} for {} unit(s).".format(
                        assignment.get("role_label"),
                        assignment.get("selected_product_name"),
                        assignment.get("quantity_required"),
                    )
                )
            else:
                rationale.append(
                    "{} is still missing a compatible product assignment.".format(
                        assignment.get("role_label")
                    )
                )
            if assignment.get("attachment_required"):
                target_role_ids = list(assignment.get("attachment_target_role_ids") or [])
                if target_role_ids:
                    for target_role_id in target_role_ids:
                        edges.append(
                            {
                                "source": role_node_id,
                                "target": f"role::{target_role_id}",
                                "relationship": "attaches_to_role",
                            }
                        )
                    rationale.append(
                        "{} attaches to {} end-user role(s).".format(
                            assignment.get("role_label"),
                            len(target_role_ids),
                        )
                    )
                else:
                    rationale.append(
                        "{} could not be attached because no end-user device role was present.".format(
                            assignment.get("role_label")
                        )
                    )

        return {
            "bundle_id": bundle_candidate.get("bundle_id"),
            "validated": bool(bundle_report.get("passed")),
            "nodes": nodes,
            "edges": edges,
            "rationale": rationale,
        }

    def _assignment_product_node_id(self, assignment):
        assignment = dict(assignment or {})
        selected_candidate_id = str(assignment.get("selected_candidate_id") or "").strip()
        selected_inventory_id = str(assignment.get("selected_inventory_id") or "").strip()
        selected_product_id = str(assignment.get("selected_product_id") or "").strip()
        if selected_candidate_id:
            return f"product::{selected_candidate_id}"
        if selected_inventory_id:
            return f"product::{selected_inventory_id}"
        return f"product::{selected_product_id}"

    def _build_bundle_option(self, bundle_candidate, bundle_report, architecture_graph):
        bundle_candidate = dict(bundle_candidate or {})
        bundle_report = dict(bundle_report or {})
        return {
            "bundle_id": bundle_candidate.get("bundle_id"),
            "label": bundle_candidate.get("label"),
            "status": "validated" if bundle_report.get("passed") else "rejected",
            "validated": bool(bundle_report.get("passed")),
            "template_id": bundle_candidate.get("template_id"),
            "template_version": bundle_candidate.get("template_version"),
            "currency": bundle_candidate.get("currency"),
            "estimated_total_cost": bundle_candidate.get("total_estimated_cost"),
            "bundle_conflict_codes": list(bundle_report.get("bundle_conflict_codes") or []),
            "role_assignments": list(bundle_candidate.get("assignments") or []),
            "capacity_summary": bundle_report.get("capacity_summary") or {},
            "architecture_graph": architecture_graph,
        }

    def _build_merge_rules(self, bundle_candidate, bundle_report):
        bundle_candidate = dict(bundle_candidate or {})
        bundle_report = dict(bundle_report or {})
        add_on_count = sum(
            1
            for assignment in list(bundle_candidate.get("assignments") or [])
            if assignment.get("bundle_position") == "add_on"
        )
        if bundle_report.get("passed"):
            detail = "Validated bundle {} assembled across {} grouped roles.".format(
                bundle_candidate.get("bundle_id"),
                int(bundle_candidate.get("required_group_count") or 0),
            )
            if add_on_count:
                detail = detail + " Included {} supported accessory add-on role(s).".format(add_on_count)
            return [
                {
                    "rule_id": "release_4a_validated_bundle",
                    "decision": "assemble_validated_bundle",
                    "outcome": "passed",
                    "details": detail,
                }
            ]

        reason_codes = list(bundle_report.get("bundle_conflict_codes") or [])
        detail = "Bundle candidate failed validation."
        if reason_codes:
            detail = detail + " Conflict codes: {}.".format(", ".join(reason_codes))
        return [
            {
                "rule_id": "release_4a_bundle_validation_rejected",
                "decision": "reject_bundle_candidate",
                "outcome": "warning",
                "details": detail,
            }
        ]

    def _build_summary(self, bundle_candidate, bundle_report):
        bundle_candidate = dict(bundle_candidate or {})
        bundle_report = dict(bundle_report or {})
        role_coverage = dict(bundle_report.get("role_coverage") or {})
        capacity_summary = dict(bundle_report.get("capacity_summary") or {})
        if bundle_report.get("passed"):
            return (
                "Validated bundle prepared across {} roles with an estimated total cost of {} {}."
            ).format(
                int(role_coverage.get("covered_role_count") or 0),
                bundle_candidate.get("total_estimated_cost"),
                bundle_candidate.get("currency") or "",
            ).strip()

        blocked_reasons = list(bundle_report.get("blocked_reasons") or [])
        if blocked_reasons:
            return "Bundle candidate was rejected by bundle validation: {}.".format(" ".join(blocked_reasons))
        conflict_codes = list(bundle_report.get("bundle_conflict_codes") or [])
        if conflict_codes:
            return "Bundle candidate was rejected by bundle validation: {}.".format(", ".join(conflict_codes))
        if int(capacity_summary.get("total_quantity_gap") or 0) > 0:
            return "Bundle candidate was rejected because at least one role could not cover the required quantity."
        return "Bundle candidate was rejected during bundle validation."

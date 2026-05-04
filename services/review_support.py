class ProcurementReviewSupportService:
    REVIEW_READY_MODES = {"", "firm_recommendation"}
    FIELD_LABELS = {
        "preferred_category": "Category",
        "industry": "Industry",
        "business_type": "Business Type",
        "team_size": "Team Size",
        "workloads": "Workloads",
        "application_signals": "Application Profile",
        "budget": "Budget",
        "budget_scope": "Budget Scope",
        "quantity": "Quantity",
        "purchase_scope": "Purchase Scope",
        "rollout_type": "Rollout Type",
        "replacement_mode": "Replacement Mode",
        "growth_expectation": "Growth Expectation",
        "performance_priority": "Performance Priority",
        "portability_need": "Portability Need",
        "support_expectation": "Support Expectation",
        "availability_need": "Availability Need",
        "existing_infrastructure": "Existing Infrastructure",
        "minimum_warranty_years": "Minimum Warranty Years",
        "required_port_count": "Required Port Count",
        "required_throughput_mbps": "Required Throughput Mbps",
        "required_duplex_printing": "Required Duplex Printing",
        "required_scanner": "Required Scanner",
        "min_print_speed_ppm": "Minimum Print Speed",
        "required_printer_type": "Required Printer Type",
        "required_print_technology": "Required Print Technology",
        "required_color_output": "Required Color Output",
        "min_monthly_duty_cycle_pages": "Minimum Monthly Duty Cycle",
        "required_automatic_document_feeder": "Required Automatic Document Feeder",
        "required_paper_sizes": "Required Paper Sizes",
        "required_network_roles": "Required Network Roles",
        "required_vpn_user_capacity": "Required VPN User Capacity",
        "required_virtualization_ready": "Required Virtualization Support",
        "required_virtualization_platforms": "Required Virtualization Platforms",
        "max_rack_units": "Maximum Rack Units",
        "max_power_draw_watts": "Maximum Power Draw",
        "battery_life_hours_min": "Minimum Battery Hours",
        "cpu_preference": "CPU Preference",
        "gpu_requirement": "GPU Requirement",
        "screen_size_preference": "Screen Size Preference",
        "weight_kg_max": "Maximum Weight (kg)",
        "warranty_type_preference": "Warranty Type Preference",
    }

    def enrich_review_state(self, requirements, readiness, template_candidates=None, recommendation_mode=""):
        requirements = dict(requirements or {})
        readiness = dict(readiness or {})
        template_candidates = list(template_candidates or [])
        field_state = dict(requirements.get("field_state") or {})
        review_state = dict(requirements.get("review_state") or {})

        inferred_fields = []
        for field, state in field_state.items():
            value = requirements.get(field)
            if state != "inferred" or value in (None, "", [], {}):
                continue
            inferred_fields.append(field)

        unknown_critical_fields = self._unknown_critical_fields(requirements, readiness)
        edited_fields = sorted(review_state.get("edited_fields") or [])
        review_required = bool(
            unknown_critical_fields
            or inferred_fields
            or (recommendation_mode and recommendation_mode not in self.REVIEW_READY_MODES)
        )
        acceptance_blocked_reasons = []
        if unknown_critical_fields:
            acceptance_blocked_reasons.extend(unknown_critical_fields)
        if inferred_fields:
            acceptance_blocked_reasons.append("inferred_values_pending_confirmation")
        if recommendation_mode and recommendation_mode not in self.REVIEW_READY_MODES:
            acceptance_blocked_reasons.append("recommendation_not_final")
        acceptance_blocked_reasons = self._dedupe_strings(acceptance_blocked_reasons)
        ready_for_acceptance = not acceptance_blocked_reasons
        acceptance_requested = bool(review_state.get("review_acceptance_requested"))
        accepted = bool(acceptance_requested and ready_for_acceptance)
        status, message = self._review_status(
            unknown_critical_fields=unknown_critical_fields,
            inferred_fields=inferred_fields,
            recommendation_mode=recommendation_mode,
            acceptance_requested=acceptance_requested,
            ready_for_acceptance=ready_for_acceptance,
            accepted=accepted,
            edited_fields=edited_fields,
        )

        audit = list(review_state.get("audit") or [])
        if acceptance_requested:
            audit.append(
                {
                    "action": "acceptance_granted" if accepted else "acceptance_blocked",
                    "blocked_reasons": list(acceptance_blocked_reasons),
                }
            )

        return {
            **review_state,
            "workflow_version": review_state.get("workflow_version") or "review-v2",
            "submitted": bool(review_state.get("submitted") or acceptance_requested or edited_fields),
            "review_required": review_required,
            "ready_for_acceptance": ready_for_acceptance,
            "review_acceptance_requested": acceptance_requested,
            "accepted": accepted,
            "acceptance_allowed": ready_for_acceptance,
            "acceptance_blocked_reasons": acceptance_blocked_reasons,
            "inferred_fields_pending_confirmation": inferred_fields,
            "unknown_critical_fields": unknown_critical_fields,
            "selected_template_hint": template_candidates[0].get("template_id") if template_candidates else "",
            "status": status,
            "next_action": self._next_action(status),
            "message": message,
            "audit": audit,
        }

    def build_editable_inferred_values(self, requirements):
        requirements = dict(requirements or {})
        field_state = dict(requirements.get("field_state") or {})
        field_source = dict(requirements.get("field_source") or {})
        assumption_severity = dict(requirements.get("assumption_severity") or {})

        editable = {}
        for field, state in field_state.items():
            if state != "inferred":
                continue
            value = requirements.get(field)
            if value in (None, "", [], {}):
                continue
            editable[field] = {
                "label": self.FIELD_LABELS.get(field, field.replace("_", " ").title()),
                "value": value,
                "field_state": state,
                "field_source": field_source.get(field),
                "assumption_severity": assumption_severity.get(field),
            }
        return editable

    def build_check_requirement_summary(self, requirements, readiness, template_candidates=None, recommendation_mode=""):
        requirements = dict(requirements or {})
        readiness = dict(readiness or {})
        template_candidates = list(template_candidates or [])
        field_state = dict(requirements.get("field_state") or {})
        review_state = self.enrich_review_state(
            requirements=requirements,
            readiness=readiness,
            template_candidates=template_candidates,
            recommendation_mode=recommendation_mode,
        )

        confirmed_values = {}
        inferred_values = {}
        for field, state in field_state.items():
            value = requirements.get(field)
            if value in (None, "", [], {}):
                continue
            if state == "confirmed":
                confirmed_values[field] = value
            elif state == "inferred":
                inferred_values[field] = value

        return {
            "status": review_state.get("status"),
            "ready_for_acceptance": bool(review_state.get("ready_for_acceptance")),
            "review_acceptance": bool(review_state.get("accepted")),
            "review_acceptance_requested": bool(review_state.get("review_acceptance_requested")),
            "acceptance_allowed": bool(review_state.get("acceptance_allowed")),
            "acceptance_blocked_reasons": list(review_state.get("acceptance_blocked_reasons") or []),
            "edited_fields": list(review_state.get("edited_fields") or []),
            "confirmed_values": confirmed_values,
            "inferred_values": inferred_values,
            "unknown_critical_fields": list(review_state.get("unknown_critical_fields") or []),
            "selected_template_hint": review_state.get("selected_template_hint") or "",
            "next_action": review_state.get("next_action"),
            "message": review_state.get("message") or "",
        }

    def _review_status(
        self,
        unknown_critical_fields,
        inferred_fields,
        recommendation_mode,
        acceptance_requested,
        ready_for_acceptance,
        accepted,
        edited_fields,
    ):
        if accepted:
            return (
                "accepted",
                "Review was accepted and the recommendation can be treated as final for the current inputs.",
            )
        if acceptance_requested and not ready_for_acceptance:
            return (
                "acceptance_blocked",
                "Acceptance is blocked until the remaining unknowns or inferred assumptions are resolved.",
            )
        if unknown_critical_fields:
            return (
                "review_pending",
                "Review the inferred values below and resolve the remaining critical unknowns before accepting a final recommendation.",
            )
        if (recommendation_mode and recommendation_mode not in self.REVIEW_READY_MODES) or inferred_fields:
            if edited_fields:
                return (
                    "edits_submitted",
                    "Edits were submitted. Confirm the remaining inferred values before accepting the recommendation.",
                )
            return (
                "review_pending",
                "Review the inferred values below and confirm any assumptions before accepting the recommendation.",
            )
        return (
            "ready_for_acceptance",
            "Requirement is fully confirmed and ready for acceptance.",
        )

    def _next_action(self, status):
        if status == "accepted":
            return "accepted"
        if status == "acceptance_blocked":
            return "resolve_review_blockers"
        if status == "ready_for_acceptance":
            return "submit_final_acceptance"
        if status == "edits_submitted":
            return "confirm_remaining_inferred_values"
        return "review_and_edit_inferred_values"

    def _unknown_critical_fields(self, requirements, readiness):
        requirements = dict(requirements or {})
        readiness = dict(readiness or {})
        assumption_severity = dict(requirements.get("assumption_severity") or {})
        missing_signals = self._dedupe_strings(readiness.get("missing_signals") or [])

        critical = []
        for signal in missing_signals:
            severity = assumption_severity.get(signal)
            if severity == "soft":
                continue
            if severity:
                critical.append(signal)
                continue
            if readiness.get("is_ready") is False:
                critical.append(signal)
        return critical

    def _dedupe_strings(self, values):
        deduped = []
        seen = set()
        for value in list(values or []):
            normalized = str(value or "").strip()
            if not normalized:
                continue
            lowered = normalized.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            deduped.append(normalized)
        return deduped

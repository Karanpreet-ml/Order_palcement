# class ProcurementMultiIntentPolicyService:
#     POLICY_VERSION = "multi-intent-policy-v1"
#     SHARED_CONSTRAINT_KEYS = (
#         "store_id",
#         "channel",
#         "currency",
#         "budget",
#         "budget_scope",
#         "growth_expectation",
#         "existing_infrastructure",
#         "preferred_manufacturers",
#         "blocked_manufacturers",
#         "preferred_sellers",
#         "blocked_sellers",
#         "performance_priority",
#         "portability_need",
#         "support_expectation",
#         "availability_need",
#         "require_returnable",
#         "timeline",
#         "industry",
#         "business_type",
#     )

#     def evaluate(self, payload, extracted_schema, requirements, multi_intent_result, selected_template=None):
#         payload = dict(payload or {})
#         extracted_schema = dict(extracted_schema or {})
#         requirements = dict(requirements or {})
#         multi_intent_result = dict(multi_intent_result or {})
#         selected_template = dict(selected_template or {})
#         intents = list(multi_intent_result.get("intents") or [])

#         shared_constraints = self._shared_constraints(
#             payload=payload,
#             extracted_schema=extracted_schema,
#             requirements=requirements,
#         )
#         shared_budget = self._shared_budget_policy(
#             requirements=requirements,
#             intents=intents,
#             template_budget_strategy=selected_template.get("budget_strategy"),
#         )
#         warnings = []
#         if shared_budget.get("warning_code"):
#             warnings.append(
#                 {
#                     "code": shared_budget.get("warning_code"),
#                     "message": shared_budget.get("warning_message"),
#                     "severity": "warning",
#                 }
#             )

#         split_rules = [
#             {
#                 "rule_id": "chat_text_clause_split",
#                 "decision": "split_into_groups",
#                 "outcome": "passed",
#                 "details": "Grouped intent detection split the request into {} clause-backed groups via {}.".format(
#                     len(intents),
#                     multi_intent_result.get("split_source") or "chat_text",
#                 ),
#             },
#             {
#                 "rule_id": "distinct_category_or_workload_required",
#                 "decision": "split_into_groups",
#                 "outcome": "passed",
#                 "details": "Detected distinct category or workload signals across grouped intents.",
#             },
#             {
#                 "rule_id": "shared_constraints_reused_per_group",
#                 "decision": "share_constraints",
#                 "outcome": "passed",
#                 "details": "Shared request constraints are reused across grouped runs: {}.".format(
#                     ", ".join(shared_constraints) if shared_constraints else "none"
#                 ),
#             },
#         ]
#         merge_rules = [
#             {
#                 "rule_id": "release_3b_grouped_output_only",
#                 "decision": "keep_groups_separate",
#                 "outcome": "passed",
#                 "details": "Release 3B keeps grouped outputs separate and does not claim bundle validity.",
#             },
#         ]
#         if shared_budget.get("allocation_required"):
#             merge_rules.append(
#                 {
#                     "rule_id": "shared_project_budget_requires_allocation",
#                     "decision": "ask_budget_allocation",
#                     "outcome": "warning",
#                     "details": shared_budget.get("warning_message"),
#                 }
#             )

#         group_metadata = []
#         groups_by_id = {}
#         for intent in intents:
#             group_warning_items = []
#             group_shared_budget = {
#                 "is_shared": bool(shared_budget.get("is_shared")),
#                 "scope": shared_budget.get("scope"),
#                 "allocation_status": shared_budget.get("allocation_status"),
#                 "allocation_required": bool(shared_budget.get("allocation_required")),
#             }
#             if shared_budget.get("warning_code"):
#                 group_warning_items.append(
#                     {
#                         "code": shared_budget.get("warning_code"),
#                         "message": shared_budget.get("warning_message"),
#                         "severity": "warning",
#                     }
#                 )
#             metadata = {
#                 "group_id": intent.get("group_id"),
#                 "label": intent.get("label"),
#                 "shared_constraints": list(shared_constraints),
#                 "warnings": group_warning_items,
#                 "shared_budget": group_shared_budget,
#             }
#             group_metadata.append(metadata)
#             if metadata.get("group_id"):
#                 groups_by_id[metadata["group_id"]] = metadata

#         return {
#             "policy_version": self.POLICY_VERSION,
#             "split_source": multi_intent_result.get("split_source"),
#             "split_decision": "split_into_groups",
#             "merge_decision": "keep_groups_separate",
#             "bundle_validated": False,
#             "group_count": len(intents),
#             "shared_constraints": shared_constraints,
#             "shared_budget": shared_budget,
#             "warnings": warnings,
#             "split_rules": split_rules,
#             "merge_rules": merge_rules,
#             "template_id": selected_template.get("template_id"),
#             "template_budget_strategy": selected_template.get("budget_strategy"),
#             "group_metadata": group_metadata,
#             "groups_by_id": groups_by_id,
#         }

#     def _shared_constraints(self, payload, extracted_schema, requirements):
#         shared_constraints = []
#         for key in self.SHARED_CONSTRAINT_KEYS:
#             value = None
#             if requirements.get(key) not in (None, "", [], {}):
#                 value = requirements.get(key)
#             elif payload.get(key) not in (None, "", [], {}):
#                 value = payload.get(key)
#             elif extracted_schema.get(key) not in (None, "", [], {}):
#                 value = extracted_schema.get(key)
#             if value in (None, "", [], {}):
#                 continue
#             shared_constraints.append(key)
#         return shared_constraints

#     def _shared_budget_policy(self, requirements, intents, template_budget_strategy=""):
#         requirements = dict(requirements or {})
#         intents = list(intents or [])
#         template_budget_strategy = str(template_budget_strategy or "").strip().lower()
#         group_labels = [intent.get("label") or intent.get("group_id") or "intent" for intent in intents]
#         budget = requirements.get("budget")
#         budget_scope = requirements.get("budget_scope")
#         is_shared = budget is not None and len(intents) > 1
#         allocation_required = bool(
#             is_shared
#             and (
#                 budget_scope == "project_total"
#                 or (
#                     template_budget_strategy == "shared_budget_requires_safe_split"
#                     and budget_scope in {None, ""}
#                 )
#             )
#         )
#         warning_code = "shared_budget_allocation_required" if allocation_required else ""
#         warning_message = ""
#         clarification_prompt = ""
#         clarification_rationale = ""
#         if allocation_required:
#             label_summary = ", ".join(group_labels[:3])
#             if len(group_labels) > 3:
#                 label_summary += ", and the remaining groups"
#             warning_message = (
#                 "The budget is a single project total shared across multiple intent groups, "
#                 "so grouped outputs are planning aids until the budget is allocated per group."
#             )
#             clarification_prompt = (
#                 "The budget looks like one shared project total across multiple needs. "
#                 "How should I split it between {} so I can judge budget fit per group?"
#             ).format(label_summary)
#             clarification_rationale = (
#                 "A shared project budget cannot be validated safely across grouped outputs until each intent has "
#                 "an explicit allocation or spending priority."
#             )
#         return {
#             "present": budget is not None,
#             "is_shared": is_shared,
#             "budget": budget,
#             "scope": budget_scope,
#             "allocation_status": (
#                 "allocation_required"
#                 if allocation_required
#                 else "shared_budget_not_allocation_blocked"
#                 if is_shared
#                 else "not_shared"
#             ),
#             "allocation_required": allocation_required,
#             "warning_code": warning_code,
#             "warning_message": warning_message,
#             "clarification_key": "shared_budget_allocation" if allocation_required else "",
#             "clarification_prompt": clarification_prompt,
#             "clarification_rationale": clarification_rationale,
#         }


class ProcurementMultiIntentPolicyService:
    POLICY_VERSION = "multi-intent-policy-v1"
    SHARED_CONSTRAINT_KEYS = (
        "store_id",
        "channel",
        "currency",
        "budget",
        "budget_scope",
        "growth_expectation",
        "existing_infrastructure",
        "preferred_manufacturers",
        "blocked_manufacturers",
        "preferred_sellers",
        "blocked_sellers",
        "performance_priority",
        "portability_need",
        "support_expectation",
        "availability_need",
        "require_returnable",
        "timeline",
        "industry",
        "business_type",
    )

    def evaluate(self, payload, extracted_schema, requirements, multi_intent_result, selected_template=None):
        payload = dict(payload or {})
        extracted_schema = dict(extracted_schema or {})
        requirements = dict(requirements or {})
        multi_intent_result = dict(multi_intent_result or {})
        selected_template = dict(selected_template or {})
        intents = list(multi_intent_result.get("intents") or [])

        shared_constraints = self._shared_constraints(
            payload=payload,
            extracted_schema=extracted_schema,
            requirements=requirements,
        )
        shared_budget = self._shared_budget_policy(
            requirements=requirements,
            intents=intents,
            template_budget_strategy=selected_template.get("budget_strategy"),
        )
        warnings = []
        if shared_budget.get("warning_code"):
            warnings.append(
                {
                    "code": shared_budget.get("warning_code"),
                    "message": shared_budget.get("warning_message"),
                    "severity": "warning",
                }
            )

        split_rules = [
            {
                "rule_id": "chat_text_clause_split",
                "decision": "split_into_groups",
                "outcome": "passed",
                "details": "Grouped intent detection split the request into {} clause-backed groups via {}.".format(
                    len(intents),
                    multi_intent_result.get("split_source") or "chat_text",
                ),
            },
            {
                "rule_id": "distinct_category_or_workload_required",
                "decision": "split_into_groups",
                "outcome": "passed",
                "details": "Detected distinct category or workload signals across grouped intents.",
            },
            {
                "rule_id": "shared_constraints_reused_per_group",
                "decision": "share_constraints",
                "outcome": "passed",
                "details": "Shared request constraints are reused across grouped runs: {}.".format(
                    ", ".join(shared_constraints) if shared_constraints else "none"
                ),
            },
        ]
        merge_rules = [
            {
                "rule_id": "release_3b_grouped_output_only",
                "decision": "keep_groups_separate",
                "outcome": "passed",
                "details": "Release 3B keeps grouped outputs separate and does not claim bundle validity.",
            },
        ]
        if shared_budget.get("allocation_required"):
            merge_rules.append(
                {
                    "rule_id": "shared_project_budget_requires_allocation",
                    "decision": "ask_budget_allocation",
                    "outcome": "warning",
                    "details": shared_budget.get("warning_message"),
                }
            )

        group_metadata = []
        groups_by_id = {}
        for intent in intents:
            group_warning_items = []
            group_shared_budget = {
                "is_shared": bool(shared_budget.get("is_shared")),
                "scope": shared_budget.get("scope"),
                "allocation_status": shared_budget.get("allocation_status"),
                "allocation_required": bool(shared_budget.get("allocation_required")),
            }
            if shared_budget.get("warning_code"):
                group_warning_items.append(
                    {
                        "code": shared_budget.get("warning_code"),
                        "message": shared_budget.get("warning_message"),
                        "severity": "warning",
                    }
                )
            metadata = {
                "group_id": intent.get("group_id"),
                "label": intent.get("label"),
                "shared_constraints": list(shared_constraints),
                "warnings": group_warning_items,
                "shared_budget": group_shared_budget,
            }
            group_metadata.append(metadata)
            if metadata.get("group_id"):
                groups_by_id[metadata["group_id"]] = metadata

        return {
            "policy_version": self.POLICY_VERSION,
            "split_source": multi_intent_result.get("split_source"),
            "split_decision": "split_into_groups",
            "merge_decision": "keep_groups_separate",
            "bundle_validated": False,
            "group_count": len(intents),
            "shared_constraints": shared_constraints,
            "shared_budget": shared_budget,
            "warnings": warnings,
            "split_rules": split_rules,
            "merge_rules": merge_rules,
            "template_id": selected_template.get("template_id"),
            "template_budget_strategy": selected_template.get("budget_strategy"),
            "group_metadata": group_metadata,
            "groups_by_id": groups_by_id,
        }

    def _shared_constraints(self, payload, extracted_schema, requirements):
        shared_constraints = []
        for key in self.SHARED_CONSTRAINT_KEYS:
            value = None
            if requirements.get(key) not in (None, "", [], {}):
                value = requirements.get(key)
            elif payload.get(key) not in (None, "", [], {}):
                value = payload.get(key)
            elif extracted_schema.get(key) not in (None, "", [], {}):
                value = extracted_schema.get(key)
            if value in (None, "", [], {}):
                continue
            shared_constraints.append(key)
        return shared_constraints

    def _shared_budget_policy(self, requirements, intents, template_budget_strategy=""):
        requirements = dict(requirements or {})
        intents = list(intents or [])
        template_budget_strategy = str(template_budget_strategy or "").strip().lower()
        group_labels = [intent.get("label") or intent.get("group_id") or "intent" for intent in intents]
        budget = requirements.get("budget")
        budget_scope = requirements.get("budget_scope")
        is_shared = budget is not None and len(intents) > 1
        allocation_required = bool(
            is_shared
            and (
                budget_scope == "project_total"
                or (
                    template_budget_strategy == "shared_budget_requires_safe_split"
                    and budget_scope in {None, ""}
                )
            )
        )
        warning_code = "shared_budget_allocation_required" if allocation_required else ""
        warning_message = ""
        clarification_prompt = ""
        clarification_rationale = ""
        if allocation_required:
            label_summary = ", ".join(group_labels[:3])
            if len(group_labels) > 3:
                label_summary += ", and the remaining groups"
            warning_message = (
                "This looks like one shared budget across multiple categories. "
                "Grouped recommendations can be shown, but budget-valid group fit cannot be claimed until each group has an allocation or priority."
            )
            clarification_prompt = (
                "Is the budget one shared total for everything together, or does each category have its own budget? "
                "If it is one shared total, how should I split it between {} — or which group should get priority?"
            ).format(label_summary)
            clarification_rationale = (
                "Different categories usually have different quantity and price shapes. "
                "A shared multi-category budget should be allocated explicitly instead of guessed from weights."
            )
        return {
            "present": budget is not None,
            "is_shared": is_shared,
            "budget": budget,
            "scope": budget_scope,
            "allocation_status": (
                "allocation_required"
                if allocation_required
                else "shared_budget_not_allocation_blocked"
                if is_shared
                else "not_shared"
            ),
            "allocation_required": allocation_required,
            "warning_code": warning_code,
            "warning_message": warning_message,
            "clarification_key": "shared_budget_allocation" if allocation_required else "",
            "clarification_prompt": clarification_prompt,
            "clarification_rationale": clarification_rationale,
        }

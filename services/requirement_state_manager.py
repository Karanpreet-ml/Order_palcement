# from copy import deepcopy
# from datetime import UTC, datetime


# class RequirementStateManager:
#     LIST_FIELDS = {
#         "workloads",
#         "application_signals",
#         "capability_tags",
#         "preferred_categories",
#         "preferred_manufacturers",
#         "blocked_manufacturers",
#         "preferred_sellers",
#         "blocked_sellers",
#         "required_paper_sizes",
#         "required_network_roles",
#         "required_virtualization_platforms",
#         "intent_groups",
#     }

#     def apply_patch(self, existing_state, planner_output):
#         state = deepcopy(existing_state or {})
#         planner_output = dict(planner_output or {})
#         requirements = dict(state.get("requirements") or state)
#         requirements = self.resolve_corrections(requirements, planner_output.get("corrections"))
#         requirements = self.merge_requirement_patch(requirements, planner_output.get("state_patch"))
#         requirements = self.sanitize_nulls(requirements)
#         state["requirements"] = requirements
#         if planner_output.get("intent_groups"):
#             state["intent_groups"] = self.normalize_lists(
#                 planner_output.get("intent_groups"),
#                 field_name="intent_groups",
#             )
#         return state

#     def merge_requirement_patch(self, existing_requirements, patch):
#         merged = dict(existing_requirements or {})
#         for field, value in dict(patch or {}).items():
#             if field in self.LIST_FIELDS:
#                 merged[field] = self.normalize_lists(value, field_name=field)
#             elif value is not None:
#                 merged[field] = value
#             self._mark_provenance(merged, field)
#         return merged

#     def resolve_corrections(self, existing_requirements, corrections):
#         resolved = dict(existing_requirements or {})
#         for correction in list(corrections or []):
#             field = str(correction.get("field") or "").strip()
#             if not field:
#                 continue
#             resolved[field] = correction.get("value")
#             self._mark_provenance(resolved, field)
#         return resolved

#     def normalize_lists(self, value, field_name=""):
#         items = value if isinstance(value, list) else [value]
#         normalized = []
#         for item in items:
#             if item in (None, ""):
#                 continue
#             if item not in normalized:
#                 normalized.append(item)
#         return normalized

#     def sanitize_nulls(self, payload):
#         cleaned = {}
#         for key, value in dict(payload or {}).items():
#             if value is None:
#                 continue
#             cleaned[key] = value
#         return cleaned

#     def _mark_provenance(self, payload, field_name):
#         provenance = dict(payload.get("_provenance") or {})
#         provenance[field_name] = {
#             "field_source": "planner",
#             "field_state": "updated",
#             "last_updated_at": datetime.now(UTC).isoformat(),
#             "updated_by": "planner",
#         }
#         payload["_provenance"] = provenance



#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################


# from copy import deepcopy
# from datetime import UTC, datetime


# class RequirementStateManager:
#     LIST_FIELDS = {
#         "workloads",
#         "application_signals",
#         "capability_tags",
#         "preferred_categories",
#         "preferred_manufacturers",
#         "blocked_manufacturers",
#         "preferred_sellers",
#         "blocked_sellers",
#         "required_paper_sizes",
#         "required_network_roles",
#         "required_virtualization_platforms",
#         "intent_groups",
#     }

#     def apply_patch(self, existing_state, planner_output):
#         state = deepcopy(existing_state or {})
#         planner_output = dict(planner_output or {})
#         requirements = dict(state.get("requirements") or state)
#         requirements = self.resolve_corrections(
#             requirements,
#             planner_output.get("corrections"),
#             source="planner",
#         )
#         requirements = self.merge_requirement_patch(
#             requirements,
#             planner_output.get("state_patch"),
#             source="planner",
#         )
#         requirements = self.sanitize_nulls(requirements)
#         state["requirements"] = requirements
#         if planner_output.get("intent_groups"):
#             state["intent_groups"] = self.normalize_lists(
#                 planner_output.get("intent_groups"),
#                 field_name="intent_groups",
#             )
#         return state

#     def merge_requirement_patch(self, existing_requirements, patch, source="planner"):
#         merged = dict(existing_requirements or {})
#         for field, value in dict(patch or {}).items():
#             if field in self.LIST_FIELDS:
#                 merged[field] = self.normalize_lists(value, field_name=field)
#             elif value is not None:
#                 merged[field] = value
#             else:
#                 continue
#             self._mark_provenance(merged, field, source=source)
#         return merged

#     def resolve_corrections(self, existing_requirements, corrections, source="planner"):
#         resolved = dict(existing_requirements or {})
#         for correction in list(corrections or []):
#             field = str(correction.get("field") or "").strip()
#             if not field:
#                 continue
#             resolved[field] = correction.get("value")
#             self._mark_provenance(resolved, field, source=source)
#         return resolved

#     def normalize_lists(self, value, field_name=""):
#         items = value if isinstance(value, list) else [value]
#         normalized = []
#         for item in items:
#             if item in (None, ""):
#                 continue
#             if item not in normalized:
#                 normalized.append(item)
#         return normalized

#     def sanitize_nulls(self, payload):
#         cleaned = {}
#         for key, value in dict(payload or {}).items():
#             if value is None:
#                 continue
#             cleaned[key] = value
#         return cleaned

#     def _mark_provenance(self, payload, field_name, source="planner"):
#         normalized_source = str(source or "planner").strip() or "planner"
#         provenance = dict(payload.get("_provenance") or {})
#         provenance[field_name] = {
#             "field_source": normalized_source,
#             "field_state": "updated",
#             "last_updated_at": datetime.now(UTC).isoformat(),
#             "updated_by": normalized_source,
#         }
#         payload["_provenance"] = provenance


#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################
#######################################################################################################################################################

#######################################################################################################################################################
#######################################################################################################################################################



from copy import deepcopy
from datetime import UTC, datetime


class RequirementStateManager:
    LIST_FIELDS = {
        "workloads",
        "application_signals",
        "capability_tags",
        "preferred_categories",
        "preferred_manufacturers",
        "blocked_manufacturers",
        "preferred_sellers",
        "blocked_sellers",
        "required_paper_sizes",
        "required_network_roles",
        "required_virtualization_platforms",
        "intent_groups",
    }

    def apply_patch(self, existing_state, planner_output):
        state = deepcopy(existing_state or {})
        planner_output = dict(planner_output or {})
        requirements = dict(state.get("requirements") or state)
        requirements = self.resolve_corrections(
            requirements,
            planner_output.get("corrections"),
            source="planner",
        )
        requirements = self.merge_requirement_patch(
            requirements,
            planner_output.get("state_patch"),
            source="planner",
        )
        requirements = self.sanitize_nulls(requirements)
        requirements = self._synchronize_special_fields(requirements)
        state["requirements"] = requirements

        if planner_output.get("intent_groups"):
            state["intent_groups"] = self.normalize_lists(
                planner_output.get("intent_groups"),
                field_name="intent_groups",
            )
        elif state.get("intent_groups"):
            state["intent_groups"] = self.normalize_lists(
                state.get("intent_groups"),
                field_name="intent_groups",
            )
        return state

    def merge_requirement_patch(self, existing_requirements, patch, source="planner"):
        merged = dict(existing_requirements or {})
        for field, value in dict(patch or {}).items():
            if field in self.LIST_FIELDS:
                merged[field] = self.normalize_lists(value, field_name=field)
            elif value is not None:
                merged[field] = value
            else:
                continue
            self._mark_provenance(merged, field, source=source)
        return self._synchronize_special_fields(merged)

    def resolve_corrections(self, existing_requirements, corrections, source="planner"):
        resolved = dict(existing_requirements or {})
        for correction in list(corrections or []):
            field = str(correction.get("field") or "").strip()
            if not field:
                continue
            value = correction.get("value")
            if field in self.LIST_FIELDS:
                resolved[field] = self.normalize_lists(value, field_name=field)
            else:
                resolved[field] = value
            self._mark_provenance(resolved, field, source=source)
        return self._synchronize_special_fields(resolved)

    def normalize_lists(self, value, field_name=""):
        items = value if isinstance(value, list) else [value]
        normalized = []
        for item in items:
            if item in (None, ""):
                continue
            if item not in normalized:
                normalized.append(item)
        return normalized

    def sanitize_nulls(self, payload):
        cleaned = {}
        for key, value in dict(payload or {}).items():
            if value is None:
                continue
            cleaned[key] = value
        return cleaned

    def _synchronize_special_fields(self, payload):
        synced = dict(payload or {})

        categories = self.normalize_lists(
            synced.get("preferred_categories") or synced.get("preferred_category"),
            field_name="preferred_categories",
        )
        preferred_category = synced.get("preferred_category")

        if preferred_category and preferred_category not in categories:
            categories.insert(0, preferred_category)

        if categories:
            synced["preferred_categories"] = categories
            if not preferred_category:
                synced["preferred_category"] = categories[0]
            elif preferred_category not in categories:
                synced["preferred_category"] = categories[0]
        elif preferred_category:
            synced["preferred_categories"] = [preferred_category]

        workloads = self.normalize_lists(synced.get("workloads"), field_name="workloads")
        if workloads:
            synced["workloads"] = workloads

        application_signals = self.normalize_lists(
            synced.get("application_signals"),
            field_name="application_signals",
        )
        if application_signals:
            synced["application_signals"] = application_signals

        capability_tags = self.normalize_lists(
            synced.get("capability_tags"),
            field_name="capability_tags",
        )
        if capability_tags:
            synced["capability_tags"] = capability_tags

        return synced

    def _mark_provenance(self, payload, field_name, source="planner"):
        normalized_source = str(source or "planner").strip() or "planner"
        provenance = dict(payload.get("_provenance") or {})
        provenance[field_name] = {
            "field_source": normalized_source,
            "field_state": "updated",
            "last_updated_at": datetime.now(UTC).isoformat(),
            "updated_by": normalized_source,
        }
        payload["_provenance"] = provenance



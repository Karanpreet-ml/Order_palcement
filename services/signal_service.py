# import re

# from ...catalog.services.normalization import normalize_text_list
# from .config_service import ProcurementConfigService


# class ProcurementSignalService:
#     def __init__(self, config_service=None):
#         self.config_service = config_service or ProcurementConfigService()

#     def extract(self, text):
#         lowered = str(text or "").lower()
#         rules_config = self.config_service.get_rules_config()
#         application_signals = []
#         workload_types = []
#         capability_tags = []

#         for rule in rules_config.get("application_signal_rules") or []:
#             if not self._matches_any(lowered, rule.get("keywords") or []):
#                 continue
#             self._append_unique(application_signals, rule.get("name"))
#             for workload in rule.get("workloads") or []:
#                 self._append_unique(workload_types, workload)
#             for tag in rule.get("capability_tags") or []:
#                 self._append_unique(capability_tags, tag)

#         for rule in rules_config.get("capability_signal_rules") or []:
#             if not self._matches_any(lowered, rule.get("keywords") or []):
#                 continue
#             self._append_unique(capability_tags, rule.get("tag"))

#         return {
#             "application_signals": application_signals,
#             "workload_types": workload_types,
#             "capability_tags": capability_tags,
#         }

#     def sanitize_application_signals(self, values):
#         allowed = {
#             str(rule.get("name") or "").strip()
#             for rule in self.config_service.get_rules_config().get("application_signal_rules") or []
#             if str(rule.get("name") or "").strip()
#         }
#         return self._sanitize_values(values, allowed)

#     def sanitize_capability_tags(self, values):
#         allowed = {
#             str(rule.get("tag") or "").strip()
#             for rule in self.config_service.get_rules_config().get("capability_signal_rules") or []
#             if str(rule.get("tag") or "").strip()
#         }
#         allowed.update(
#             {
#                 str(tag or "").strip()
#                 for tag in (self.config_service.get_rules_config().get("capability_tag_adjustments") or {}).keys()
#                 if str(tag or "").strip()
#             }
#         )
#         return self._sanitize_values(values, allowed)

#     def workloads_for_application_signals(self, values):
#         rules_by_name = {
#             str(rule.get("name") or "").strip(): rule
#             for rule in self.config_service.get_rules_config().get("application_signal_rules") or []
#             if str(rule.get("name") or "").strip()
#         }
#         workloads = []
#         for signal in self.sanitize_application_signals(values):
#             for workload in rules_by_name.get(signal, {}).get("workloads") or []:
#                 self._append_unique(workloads, workload)
#         return workloads

#     def capability_tags_for_application_signals(self, values):
#         rules_by_name = {
#             str(rule.get("name") or "").strip(): rule
#             for rule in self.config_service.get_rules_config().get("application_signal_rules") or []
#             if str(rule.get("name") or "").strip()
#         }
#         capability_tags = []
#         for signal in self.sanitize_application_signals(values):
#             for tag in rules_by_name.get(signal, {}).get("capability_tags") or []:
#                 self._append_unique(capability_tags, tag)
#         return capability_tags

#     def _sanitize_values(self, values, allowed):
#         allowed_map = {value.lower(): value for value in allowed}
#         sanitized = []
#         for value in normalize_text_list(values):
#             canonical = allowed_map.get(value.lower())
#             if canonical and canonical not in sanitized:
#                 sanitized.append(canonical)
#         return sanitized

#     def _matches_any(self, lowered_text, keywords):
#         for keyword in keywords:
#             keyword = str(keyword or "").strip().lower()
#             if not keyword:
#                 continue
#             if " " in keyword or "-" in keyword or "/" in keyword or "." in keyword:
#                 if keyword in lowered_text:
#                     return True
#                 continue
#             if re.search(rf"\b{re.escape(keyword)}\b", lowered_text):
#                 return True
#         return False

#     def _append_unique(self, items, value):
#         value = str(value or "").strip()
#         if value and value not in items:
#             items.append(value)


import re

from ...catalog.services.normalization import normalize_text_list
from .config_service import ProcurementConfigService


class ProcurementSignalService:
    def __init__(self, config_service=None):
        self.config_service = config_service or ProcurementConfigService()

    def extract(self, text):
        lowered = str(text or "").lower()
        rules_config = self.config_service.get_rules_config()
        application_signals = []
        workload_types = []
        capability_tags = []

        for rule in rules_config.get("application_signal_rules") or []:
            if not self._matches_any(lowered, rule.get("keywords") or []):
                continue
            self._append_unique(application_signals, rule.get("name"))
            for workload in rule.get("workloads") or []:
                self._append_unique(workload_types, workload)
            for tag in rule.get("capability_tags") or []:
                self._append_unique(capability_tags, tag)

        for rule in rules_config.get("capability_signal_rules") or []:
            if not self._matches_any(lowered, rule.get("keywords") or []):
                continue
            self._append_unique(capability_tags, rule.get("tag"))

        self._apply_department_heuristics(lowered, application_signals, workload_types, capability_tags)

        return {
            "application_signals": application_signals,
            "workload_types": workload_types,
            "capability_tags": capability_tags,
        }

    def sanitize_application_signals(self, values):
        allowed = {
            str(rule.get("name") or "").strip()
            for rule in self.config_service.get_rules_config().get("application_signal_rules") or []
            if str(rule.get("name") or "").strip()
        }
        return self._sanitize_values(values, allowed)

    def sanitize_capability_tags(self, values):
        allowed = {
            str(rule.get("tag") or "").strip()
            for rule in self.config_service.get_rules_config().get("capability_signal_rules") or []
            if str(rule.get("tag") or "").strip()
        }
        allowed.update(
            {
                str(tag or "").strip()
                for tag in (self.config_service.get_rules_config().get("capability_tag_adjustments") or {}).keys()
                if str(tag or "").strip()
            }
        )
        return self._sanitize_values(values, allowed)

    def workloads_for_application_signals(self, values):
        rules_by_name = {
            str(rule.get("name") or "").strip(): rule
            for rule in self.config_service.get_rules_config().get("application_signal_rules") or []
            if str(rule.get("name") or "").strip()
        }
        workloads = []
        for signal in self.sanitize_application_signals(values):
            for workload in rules_by_name.get(signal, {}).get("workloads") or []:
                self._append_unique(workloads, workload)
        return workloads

    def capability_tags_for_application_signals(self, values):
        rules_by_name = {
            str(rule.get("name") or "").strip(): rule
            for rule in self.config_service.get_rules_config().get("application_signal_rules") or []
            if str(rule.get("name") or "").strip()
        }
        capability_tags = []
        for signal in self.sanitize_application_signals(values):
            for tag in rules_by_name.get(signal, {}).get("capability_tags") or []:
                self._append_unique(capability_tags, tag)
        return capability_tags

    def _sanitize_values(self, values, allowed):
        allowed_map = {value.lower(): value for value in allowed}
        sanitized = []
        for value in normalize_text_list(values):
            canonical = allowed_map.get(value.lower())
            if canonical and canonical not in sanitized:
                sanitized.append(canonical)
        return sanitized

    def _matches_any(self, lowered_text, keywords):
        for keyword in keywords:
            keyword = str(keyword or "").strip().lower()
            if not keyword:
                continue
            if " " in keyword or "-" in keyword or "/" in keyword or "." in keyword:
                if keyword in lowered_text:
                    return True
                continue
            if re.search(rf"\b{re.escape(keyword)}\b", lowered_text):
                return True
        return False

    def _apply_department_heuristics(self, lowered_text, application_signals, workload_types, capability_tags):
        text = str(lowered_text or "")
        office_terms = {
            "finance team",
            "finance department",
            "accounting team",
            "accounts team",
            "admin team",
            "administration team",
            "back office",
            "operations team",
            "office staff",
            "clerical",
            "payroll",
        }
        if any(term in text for term in office_terms):
            self._append_unique(application_signals, "business_apps")
            self._append_unique(workload_types, "office_productivity")

        video_terms = {
            "video editing",
            "video editor",
            "premiere",
            "after effects",
            "davinci",
            "davinci resolve",
            "final cut",
            "post production",
            "post-production",
        }
        if any(term in text for term in video_terms):
            self._append_unique(application_signals, "video_postproduction")
            self._append_unique(workload_types, "video_editing")
            self._append_unique(capability_tags, "gpu_needed")
            self._append_unique(capability_tags, "storage_heavy")

        design_terms = {
            "photoshop",
            "illustrator",
            "indesign",
            "design team",
            "graphic design",
            "creative team",
            "designer",
            "design work",
        }
        if any(term in text for term in design_terms):
            self._append_unique(application_signals, "design_suite")
            self._append_unique(workload_types, "creative_design")
            self._append_unique(capability_tags, "display_sensitive")

        developer_terms = {
            "developer",
            "developers",
            "software development",
            "programming",
            "coding",
            "dev team",
            "engineering team",
        }
        if any(term in text for term in developer_terms):
            self._append_unique(application_signals, "developer_toolchain")
            self._append_unique(workload_types, "software_development")
            self._append_unique(capability_tags, "high_ram")
    def _append_unique(self, items, value):
        value = str(value or "").strip()
        if value and value not in items:
            items.append(value)

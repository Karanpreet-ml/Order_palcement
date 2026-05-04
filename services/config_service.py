import json
from functools import lru_cache
from pathlib import Path


CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"


class ProcurementConfigService:
    CONFIG_FILES = {
        "rules": "rules_config.json",
        "ranking": "ranking_weights.json",
        "policy": "policy_config.json",
        "release_gates": "release_gate_config.json",
        "templates": "template_registry.json",
    }

    def __init__(self, config_dir=None):
        self.config_dir = Path(config_dir) if config_dir else CONFIG_DIR

    def get_rules_config(self):
        config = self._load_config("rules")
        self._validate_rules_config(config)
        return config

    def get_ranking_config(self):
        config = self._load_config("ranking")
        self._validate_ranking_config(config)
        return config

    def get_policy_config(self):
        config = self._load_config("policy")
        self._validate_policy_config(config)
        return config

    def get_release_gate_config(self):
        config = self._load_config("release_gates")
        self._validate_release_gate_config(config)
        return config

    def get_template_config(self):
        config = self._load_config("templates")
        self._validate_template_config(config)
        return config

    def get_clarification_policy(self):
        return self.get_policy_config()["clarification_policy"]

    def get_recommendation_mode_policy(self):
        return self.get_policy_config()["recommendation_mode_policy"]

    def get_decision_policy_profile(self):
        policy = self.get_policy_config()
        return {
            "policy_version": policy["version"],
            "clarification_policy": {
                "question_impact_threshold": self.get_clarification_policy()["question_impact_threshold"],
                "decision_confidence_bands": dict(self.get_clarification_policy()["decision_confidence_bands"]),
                "question_budget_policy": dict(self.get_clarification_policy()["question_budget_policy"]),
                "ranking_blocking_signals": list(self.get_clarification_policy()["ranking_blocking_signals"]),
            },
            "recommendation_mode_policy": {
                "hard_critical_signals": list(self.get_recommendation_mode_policy()["hard_critical_signals"]),
                "expert_review_fallback_reasons": list(
                    self.get_recommendation_mode_policy()["expert_review_fallback_reasons"]
                ),
                "minimum_safe_candidate_count": self.get_recommendation_mode_policy()["minimum_safe_candidate_count"],
                "max_hard_critical_reasons_for_clarification": self.get_recommendation_mode_policy()[
                    "max_hard_critical_reasons_for_clarification"
                ],
                "max_hard_critical_reasons_for_provisional": self.get_recommendation_mode_policy()[
                    "max_hard_critical_reasons_for_provisional"
                ],
            },
        }

    def get_versions(self):
        return {
            "rules": self.get_rules_config()["version"],
            "ranking": self.get_ranking_config()["version"],
            "policy": self.get_policy_config()["version"],
            "templates": self.get_template_config()["version"],
        }

    def get_bundle_version(self):
        versions = self.get_versions()
        return f"{versions['rules']}|{versions['ranking']}|{versions['policy']}|{versions['templates']}"

    def reload(self):
        self._load_json.cache_clear()

    def _load_config(self, config_name):
        filename = self.CONFIG_FILES[config_name]
        path = self.config_dir / filename
        return self._load_json(str(path))

    @staticmethod
    @lru_cache(maxsize=8)
    def _load_json(path):
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _validate_rules_config(self, config):
        self._require_keys(
            config,
            [
                "version",
                "default_workload",
                "allow_default_workload_without_signal",
                "seat_based_categories",
                "workload_targets",
                "workload_spec_floors",
                "subprofile_targets",
                "subprofile_rules",
                "application_signal_rules",
                "capability_signal_rules",
                "capability_tag_adjustments",
                "infrastructure_growth_multipliers",
                "infrastructure_sizing_rules",
                "existing_infrastructure_hooks",
                "compatibility_rules",
            ],
        )
        if not isinstance(config["seat_based_categories"], list):
            raise ValueError("rules_config.seat_based_categories must be a list.")
        workload_targets = config["workload_targets"]
        if not isinstance(workload_targets, dict) or not workload_targets:
            raise ValueError("rules_config.workload_targets must be a non-empty object.")
        for workload, profile in workload_targets.items():
            self._require_keys(
                profile,
                ["categories", "min_ram_gb", "min_storage_gb", "min_cpu_score", "min_gpu_tier"],
                prefix=f"rules_config.workload_targets.{workload}",
            )
        workload_spec_floors = config["workload_spec_floors"]
        if not isinstance(workload_spec_floors, dict):
            raise ValueError("rules_config.workload_spec_floors must be an object.")
        for name, profile in workload_spec_floors.items():
            if not isinstance(profile, dict):
                raise ValueError(f"rules_config.workload_spec_floors.{name} must be an object.")
            allowed_keys = {"min_ram_gb", "min_storage_gb", "min_cpu_score", "min_gpu_tier"}
            unknown_keys = set(profile.keys()) - allowed_keys
            if unknown_keys:
                raise ValueError(
                    f"rules_config.workload_spec_floors.{name} contains unsupported keys: {', '.join(sorted(unknown_keys))}."
                )
        subprofile_targets = config["subprofile_targets"]
        if not isinstance(subprofile_targets, dict):
            raise ValueError("rules_config.subprofile_targets must be an object.")
        for name, profile in subprofile_targets.items():
            self._require_keys(
                profile,
                ["categories", "min_ram_gb", "min_storage_gb", "min_cpu_score", "min_gpu_tier"],
                prefix=f"rules_config.subprofile_targets.{name}",
            )
        if not isinstance(config["subprofile_rules"], list):
            raise ValueError("rules_config.subprofile_rules must be a list.")
        for index, rule in enumerate(config["subprofile_rules"]):
            self._require_keys(rule, ["name", "keywords", "target"], prefix=f"rules_config.subprofile_rules[{index}]")
        if not isinstance(config["application_signal_rules"], list):
            raise ValueError("rules_config.application_signal_rules must be a list.")
        for index, rule in enumerate(config["application_signal_rules"]):
            self._require_keys(rule, ["name", "keywords"], prefix=f"rules_config.application_signal_rules[{index}]")
        if not isinstance(config["capability_signal_rules"], list):
            raise ValueError("rules_config.capability_signal_rules must be a list.")
        for index, rule in enumerate(config["capability_signal_rules"]):
            self._require_keys(rule, ["tag", "keywords"], prefix=f"rules_config.capability_signal_rules[{index}]")
        if not isinstance(config["capability_tag_adjustments"], dict):
            raise ValueError("rules_config.capability_tag_adjustments must be an object.")
        if not isinstance(config["infrastructure_growth_multipliers"], dict):
            raise ValueError("rules_config.infrastructure_growth_multipliers must be an object.")
        if not isinstance(config["infrastructure_sizing_rules"], dict):
            raise ValueError("rules_config.infrastructure_sizing_rules must be an object.")
        for category, sizing_rules in config["infrastructure_sizing_rules"].items():
            if not isinstance(sizing_rules, list):
                raise ValueError(f"rules_config.infrastructure_sizing_rules.{category} must be a list.")
            for index, rule in enumerate(sizing_rules):
                self._require_keys(
                    rule,
                    ["name", "min_team_size"],
                    prefix=f"rules_config.infrastructure_sizing_rules.{category}[{index}]",
                )
        if not isinstance(config["existing_infrastructure_hooks"], list):
            raise ValueError("rules_config.existing_infrastructure_hooks must be a list.")
        for index, rule in enumerate(config["existing_infrastructure_hooks"]):
            self._require_keys(rule, ["name", "match_any"], prefix=f"rules_config.existing_infrastructure_hooks[{index}]")
        if not isinstance(config["compatibility_rules"], list):
            raise ValueError("rules_config.compatibility_rules must be a list.")
        for index, rule in enumerate(config["compatibility_rules"]):
            self._require_keys(
                rule,
                [
                    "rule_id",
                    "scope",
                    "type",
                    "severity",
                    "priority",
                    "applies_to",
                    "condition",
                    "effect",
                    "reason_code",
                    "user_message",
                    "overridable",
                    "override_scope",
                    "version",
                ],
                prefix=f"rules_config.compatibility_rules[{index}]",
            )
            if rule["scope"] not in {"item", "bundle"}:
                raise ValueError(f"rules_config.compatibility_rules[{index}].scope must be 'item' or 'bundle'.")

    def _validate_ranking_config(self, config):
        self._require_keys(
            config,
            [
                "version",
                "category_scores",
                "price_scoring",
                "spec_scoring",
                "availability_scoring",
                "constraint_alignment_scoring",
                "support_scoring",
                "portability_scoring",
                "persona_scoring",
                "mode_weights",
                "normalized_penalties",
                "store_match_bonus",
            ],
        )
        self._require_keys(config["category_scores"], ["no_filter", "exact_match"], prefix="ranking.category_scores")
        self._require_keys(
            config["price_scoring"],
            [
                "neutral_missing",
                "within_budget_base",
                "within_budget_headroom_cap",
                "close_threshold_ratio",
                "close_score",
                "stretch_threshold_ratio",
                "stretch_score",
                "over_budget_score",
            ],
            prefix="ranking.price_scoring",
        )
        self._require_keys(
            config["constraint_alignment_scoring"],
            [
                "neutral_component",
                "preference_floor",
                "preferred_manufacturer_match",
                "preferred_seller_match",
                "preferred_both_bonus",
                "fallback_points_multiplier",
            ],
            prefix="ranking.constraint_alignment_scoring",
        )
        self._require_keys(
            config["persona_scoring"],
            [
                "finance-first",
                "performance-first",
                "support-first",
                "standardization-first",
                "availability-first",
            ],
            prefix="ranking.persona_scoring",
        )
        self._require_keys(config["mode_weights"], ["balanced", "cost", "performance"], prefix="ranking.mode_weights")
        for mode_name, weights in config["mode_weights"].items():
            self._require_keys(
                weights,
                ["fit", "budget", "spec", "availability", "constraint_alignment", "support"],
                prefix=f"ranking.mode_weights.{mode_name}",
            )
        self._require_keys(
            config["normalized_penalties"],
            [
                "stretch_budget",
                "partial_rollout_stock",
                "soft_compatibility_warning",
                "missing_noncritical_metadata",
            ],
            prefix="ranking.normalized_penalties",
        )

    def _validate_policy_config(self, config):
        self._require_keys(
            config,
            [
                "version",
                "budget_enforcement_mode",
                "strict_stock_coverage",
                "strict_support_requirements",
                "minimum_warranty_years_default",
                "approved_manufacturers",
                "blocked_manufacturers",
                "approved_sellers",
                "blocked_sellers",
                "clarification_policy",
                "recommendation_mode_policy",
            ],
        )
        self._require_keys(
            config["clarification_policy"],
            [
                "question_impact_threshold",
                "decision_confidence_bands",
                "question_budget_policy",
                "ranking_blocking_signals",
            ],
            prefix="policy.clarification_policy",
        )
        self._require_keys(
            config["clarification_policy"]["decision_confidence_bands"],
            ["high_min", "medium_min"],
            prefix="policy.clarification_policy.decision_confidence_bands",
        )
        self._require_keys(
            config["clarification_policy"]["question_budget_policy"],
            [
                "allow_top_question_when_impact_meets_threshold",
                "allow_when_not_ready_low_confidence",
                "allow_when_ready_medium_confidence",
            ],
            prefix="policy.clarification_policy.question_budget_policy",
        )
        self._require_keys(
            config["recommendation_mode_policy"],
            [
                "hard_critical_signals",
                "expert_review_fallback_reasons",
                "minimum_safe_candidate_count",
                "max_hard_critical_reasons_for_clarification",
                "max_hard_critical_reasons_for_provisional",
            ],
            prefix="policy.recommendation_mode_policy",
        )
        if not isinstance(config["clarification_policy"]["question_impact_threshold"], (int, float)):
            raise ValueError("policy.clarification_policy.question_impact_threshold must be numeric.")
        if not isinstance(config["clarification_policy"]["decision_confidence_bands"]["high_min"], (int, float)):
            raise ValueError("policy.clarification_policy.decision_confidence_bands.high_min must be numeric.")
        if not isinstance(config["clarification_policy"]["decision_confidence_bands"]["medium_min"], (int, float)):
            raise ValueError("policy.clarification_policy.decision_confidence_bands.medium_min must be numeric.")
        if not isinstance(config["clarification_policy"]["ranking_blocking_signals"], list):
            raise ValueError("policy.clarification_policy.ranking_blocking_signals must be a list.")
        if not isinstance(config["recommendation_mode_policy"]["hard_critical_signals"], list):
            raise ValueError("policy.recommendation_mode_policy.hard_critical_signals must be a list.")
        if not isinstance(config["recommendation_mode_policy"]["expert_review_fallback_reasons"], list):
            raise ValueError("policy.recommendation_mode_policy.expert_review_fallback_reasons must be a list.")

    def _validate_release_gate_config(self, config):
        self._require_keys(config, ["version", "metrics", "drift_alerts"], prefix="release_gates")
        if not isinstance(config["metrics"], dict) or not config["metrics"]:
            raise ValueError("release_gates.metrics must be a non-empty object.")
        drift_alerts = config["drift_alerts"]
        self._require_keys(
            drift_alerts,
            ["window_size", "minimum_sample_size", "minimum_comparison_sample_size", "metrics"],
            prefix="release_gates.drift_alerts",
        )
        if not isinstance(drift_alerts["window_size"], int) or drift_alerts["window_size"] < 1:
            raise ValueError("release_gates.drift_alerts.window_size must be a positive integer.")
        if not isinstance(drift_alerts["minimum_sample_size"], int) or drift_alerts["minimum_sample_size"] < 1:
            raise ValueError("release_gates.drift_alerts.minimum_sample_size must be a positive integer.")
        if (
            not isinstance(drift_alerts["minimum_comparison_sample_size"], int)
            or drift_alerts["minimum_comparison_sample_size"] < 1
        ):
            raise ValueError(
                "release_gates.drift_alerts.minimum_comparison_sample_size must be a positive integer."
            )
        if not isinstance(drift_alerts["metrics"], dict) or not drift_alerts["metrics"]:
            raise ValueError("release_gates.drift_alerts.metrics must be a non-empty object.")
        locked_threshold_types = {
            "top_1_precision": "minimum",
            "top_3_precision": "minimum",
            "fallback_correctness": "minimum",
            "question_rate_adequately_specified": "maximum",
            "runtime_fallback_rate": "maximum",
            "runtime_question_rate": "maximum",
            "runtime_false_ready_rate": "maximum",
            "runtime_budget_scope_ambiguity_rate": "maximum",
        }
        bounded_rate_metrics = {
            "top_1_precision",
            "top_3_precision",
            "fallback_correctness",
            "question_rate_adequately_specified",
            "bundle_validation_pass_correctness",
            "bundle_no_fit_resolution_correctness",
            "runtime_fallback_rate",
            "runtime_question_rate",
            "runtime_false_ready_rate",
            "runtime_budget_scope_ambiguity_rate",
        }
        for metric_name, metric in config["metrics"].items():
            self._require_keys(
                metric,
                ["label", "threshold_type", "direction", "notes"],
                prefix=f"release_gates.metrics.{metric_name}",
            )
            if metric["threshold_type"] not in {"agreed_threshold", "minimum", "maximum", "range"}:
                raise ValueError(
                    f"release_gates.metrics.{metric_name}.threshold_type must be one of agreed_threshold, minimum, maximum, range."
                )
            if metric["direction"] not in {"higher_is_better", "lower_is_better"}:
                raise ValueError(
                    f"release_gates.metrics.{metric_name}.direction must be either higher_is_better or lower_is_better."
                )
            threshold_type = metric["threshold_type"]
            minimum = metric.get("minimum")
            maximum = metric.get("maximum")
            if threshold_type == "minimum" and not isinstance(minimum, (int, float)):
                raise ValueError(f"release_gates.metrics.{metric_name}.minimum must be numeric.")
            if threshold_type == "maximum" and not isinstance(maximum, (int, float)):
                raise ValueError(f"release_gates.metrics.{metric_name}.maximum must be numeric.")
            if threshold_type == "range":
                if not isinstance(minimum, (int, float)) or not isinstance(maximum, (int, float)):
                    raise ValueError(
                        f"release_gates.metrics.{metric_name}.minimum and maximum must both be numeric."
                    )
                if minimum > maximum:
                    raise ValueError(
                        f"release_gates.metrics.{metric_name}.minimum must be less than or equal to maximum."
                    )
            if metric_name in bounded_rate_metrics:
                if isinstance(minimum, (int, float)) and not 0 <= minimum <= 1:
                    raise ValueError(f"release_gates.metrics.{metric_name}.minimum must stay within 0 and 1.")
                if isinstance(maximum, (int, float)) and not 0 <= maximum <= 1:
                    raise ValueError(f"release_gates.metrics.{metric_name}.maximum must stay within 0 and 1.")
            expected_threshold_type = locked_threshold_types.get(metric_name)
            if not expected_threshold_type:
                continue
            if threshold_type != expected_threshold_type:
                raise ValueError(
                    f"release_gates.metrics.{metric_name}.threshold_type must be {expected_threshold_type}."
                )

        allowed_alert_metrics = {
            "runtime_latency_p95_ms",
            "runtime_fallback_rate",
            "runtime_no_fit_rate",
            "runtime_stale_inventory_rate",
            "runtime_false_ready_rate",
        }
        rate_alert_metrics = {
            "runtime_fallback_rate",
            "runtime_no_fit_rate",
            "runtime_stale_inventory_rate",
            "runtime_false_ready_rate",
        }
        for alert_metric_name, alert_cfg in drift_alerts["metrics"].items():
            self._require_keys(
                alert_cfg,
                ["label", "severity", "absolute_increase", "relative_increase", "notes"],
                prefix=f"release_gates.drift_alerts.metrics.{alert_metric_name}",
            )
            if alert_metric_name not in allowed_alert_metrics:
                raise ValueError(
                    f"release_gates.drift_alerts.metrics.{alert_metric_name} is not a supported drift alert metric."
                )
            if alert_cfg["severity"] not in {"low", "medium", "high"}:
                raise ValueError(
                    f"release_gates.drift_alerts.metrics.{alert_metric_name}.severity must be low, medium, or high."
                )
            if not isinstance(alert_cfg["absolute_increase"], (int, float)) or alert_cfg["absolute_increase"] < 0:
                raise ValueError(
                    f"release_gates.drift_alerts.metrics.{alert_metric_name}.absolute_increase must be a non-negative number."
                )
            if not isinstance(alert_cfg["relative_increase"], (int, float)) or alert_cfg["relative_increase"] < 0:
                raise ValueError(
                    f"release_gates.drift_alerts.metrics.{alert_metric_name}.relative_increase must be a non-negative number."
                )
            threshold_metric = str(alert_cfg.get("threshold_metric") or "").strip()
            if threshold_metric and threshold_metric not in config["metrics"]:
                raise ValueError(
                    f"release_gates.drift_alerts.metrics.{alert_metric_name}.threshold_metric must reference a configured metric."
                )
            if alert_metric_name in rate_alert_metrics and alert_cfg["absolute_increase"] > 1:
                raise ValueError(
                    f"release_gates.drift_alerts.metrics.{alert_metric_name}.absolute_increase must stay within 0 and 1."
                )

    def _validate_template_config(self, config):
        self._require_keys(
            config,
            ["version", "selection_policy_version", "selection_safety_policy", "scenario_families", "templates"],
            prefix="templates",
        )
        selection_safety_policy = config["selection_safety_policy"]
        self._require_keys(
            selection_safety_policy,
            [
                "minimum_exact_score",
                "minimum_closest_match_score",
                "threshold_validation_note",
                "closest_match_review_note",
                "evaluation_order",
                "closest_match_minimum_conditions",
            ],
            prefix="templates.selection_safety_policy",
        )
        if not isinstance(selection_safety_policy["minimum_exact_score"], (int, float)):
            raise ValueError("templates.selection_safety_policy.minimum_exact_score must be numeric.")
        if not isinstance(selection_safety_policy["minimum_closest_match_score"], (int, float)):
            raise ValueError("templates.selection_safety_policy.minimum_closest_match_score must be numeric.")
        if selection_safety_policy["minimum_exact_score"] < selection_safety_policy["minimum_closest_match_score"]:
            raise ValueError(
                "templates.selection_safety_policy.minimum_exact_score must be greater than or equal to minimum_closest_match_score."
            )
        if not isinstance(selection_safety_policy["evaluation_order"], list) or len(selection_safety_policy["evaluation_order"]) < 4:
            raise ValueError("templates.selection_safety_policy.evaluation_order must be a non-empty list.")
        if (
            not isinstance(selection_safety_policy["closest_match_minimum_conditions"], list)
            or not selection_safety_policy["closest_match_minimum_conditions"]
        ):
            raise ValueError(
                "templates.selection_safety_policy.closest_match_minimum_conditions must be a non-empty list."
            )
        if not isinstance(config["scenario_families"], list) or not config["scenario_families"]:
            raise ValueError("templates.scenario_families must be a non-empty list.")
        if not isinstance(config["templates"], list) or not config["templates"]:
            raise ValueError("templates.templates must be a non-empty list.")
        for index, template in enumerate(config["templates"]):
            self._require_keys(
                template,
                [
                    "id",
                    "name",
                    "template_id",
                    "scenario_family",
                    "variant",
                    "supported_categories",
                    "required_roles",
                    "eligibility_conditions",
                    "required_fields",
                    "default_question_overrides",
                    "quantity_strategy",
                    "budget_strategy",
                    "compatibility_profile",
                    "scoring_profile",
                    "urgency_profile",
                    "in_stock_only_supported",
                    "site_scope_profile",
                    "rollout_type",
                    "replacement_mode",
                    "support_preference",
                    "existing_infra_dependency",
                    "acceptable_downgrade_path",
                    "industry_modifiers",
                    "version",
                    "active_flag",
                ],
                prefix=f"templates.templates[{index}]",
            )
            if template["scenario_family"] not in config["scenario_families"]:
                raise ValueError(
                    f"templates.templates[{index}].scenario_family must be declared in templates.scenario_families."
                )
            if not str(template["id"] or "").strip():
                raise ValueError(f"templates.templates[{index}].id must be a non-empty string.")
            if not str(template["name"] or "").strip():
                raise ValueError(f"templates.templates[{index}].name must be a non-empty string.")
            if not isinstance(template["supported_categories"], list):
                raise ValueError(f"templates.templates[{index}].supported_categories must be a list.")
            if not isinstance(template["required_roles"], list):
                raise ValueError(f"templates.templates[{index}].required_roles must be a list.")
            if not isinstance(template["eligibility_conditions"], dict):
                raise ValueError(f"templates.templates[{index}].eligibility_conditions must be an object.")
            if not isinstance(template["required_fields"], list):
                raise ValueError(f"templates.templates[{index}].required_fields must be a list.")
            if not isinstance(template["default_question_overrides"], list):
                raise ValueError(f"templates.templates[{index}].default_question_overrides must be a list.")
            if not isinstance(template["industry_modifiers"], dict):
                raise ValueError(f"templates.templates[{index}].industry_modifiers must be an object.")
            if not isinstance(template["in_stock_only_supported"], bool):
                raise ValueError(f"templates.templates[{index}].in_stock_only_supported must be a boolean.")
        template_ids = [str(template.get("template_id") or "").strip() for template in config["templates"]]
        friendly_ids = [str(template.get("id") or "").strip() for template in config["templates"]]
        if len(template_ids) != len(set(template_ids)):
            raise ValueError("templates.templates.template_id values must be unique.")
        if len(friendly_ids) != len(set(friendly_ids)):
            raise ValueError("templates.templates.id values must be unique.")

    def _require_keys(self, obj, keys, prefix="config"):
        for key in keys:
            if key not in obj:
                raise ValueError(f"Missing required key: {prefix}.{key}")

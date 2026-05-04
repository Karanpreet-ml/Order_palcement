import json

from .config_service import ProcurementConfigService
from .deployment_text import build_deployment_phrase
from .llm_client import OptionalLLMClient


class ProcurementExplanationService:
    GPU_TIER_ORDER = {
        "integrated": 1,
        "entry_discrete": 2,
        "performance": 3,
        "workstation": 4,
    }

    def __init__(self, llm_client=None, config_service=None):
        self.llm_client = llm_client or OptionalLLMClient()
        self.config_service = config_service or ProcurementConfigService()

    def build_summary(self, requirements, target_profile, recommendations):
        if not recommendations:
            return "No policy-eligible catalog-backed recommendation could be produced from the current product data."

        categories = target_profile.get("categories") or requirements.get("preferred_categories") or ["general hardware"]
        category_text = ", ".join(categories)
        workload_list = list(requirements.get("workloads") or [])
        industry = requirements.get("industry") or requirements.get("business_type") or "SMB operations"
        budget = requirements.get("budget")
        budget_scope = requirements.get("budget_scope")
        deployment_phrase = build_deployment_phrase(
            requirements,
            categories,
            seat_based_categories=self.config_service.get_rules_config().get("seat_based_categories") or [],
        )

        if budget:
            if budget_scope == "per_unit":
                budget_text = f" within a per-unit budget of {budget} {requirements.get('currency')}"
            elif budget_scope == "project_total":
                budget_text = f" within a project budget of {budget} {requirements.get('currency')}"
            else:
                budget_text = f" against a stated budget of {budget} {requirements.get('currency')} with unresolved scope"
        else:
            budget_text = ""
        if not workload_list:
            return (
                f"Ranked {category_text} options {deployment_phrase} in {industry}{budget_text} "
                "while keeping workload interpretation conservative because workload details remain unresolved."
            )
        workloads = ", ".join(workload_list)
        return (
            f"Ranked {category_text} options {deployment_phrase} in {industry}, "
            f"optimized for {workloads}{budget_text}."
        )

    def enrich_recommendations(self, requirements, target_profile, recommendations, allow_llm=True):
        enriched = []
        recommendations = [dict(recommendation) for recommendation in (recommendations or [])]
        batched_sections = self._build_batched_explanation_sections(
            requirements,
            target_profile,
            recommendations,
            allow_llm=allow_llm,
        )
        for index, recommendation in enumerate(recommendations):
            sections = batched_sections.get(index)
            if not sections:
                sections = self._build_explanation_sections(
                    requirements,
                    target_profile,
                    recommendation,
                    allow_llm=False,
                )
            recommendation["explanation"] = sections["explanation"]
            recommendation["workload_fit"] = sections["workload_fit"]
            recommendation["upgrade_implications"] = sections["upgrade_implications"]
            recommendation["assumptions"] = sections["assumptions"]
            recommendation["next_steps"] = sections["next_steps"]
            recommendation["trade-off"] = sections["trade-off"]
            enriched.append(recommendation)
        return enriched

    def build_comparison(self, requirements, recommendations, allow_llm=True):
        recommendations = list(recommendations or [])
        if len(recommendations) < 2:
            return ""

        if allow_llm:
            comparison = self.llm_client.invoke_text(
                "comparison.txt",
                {
                    "requirements": json.dumps(requirements or {}, ensure_ascii=True),
                    "recommendation_one": json.dumps(recommendations[0], ensure_ascii=True),
                    "recommendation_two": json.dumps(recommendations[1], ensure_ascii=True),
                },
            )
            if comparison:
                return comparison.strip()

        first = recommendations[0]
        second = recommendations[1]
        differences = []
        if (first.get("score") or 0) != (second.get("score") or 0):
            differences.append(
                f"{first.get('name')} ranked higher because its overall score was stronger."
            )
        if (first.get("estimated_total_cost") or 0) < (second.get("estimated_total_cost") or 0):
            differences.append(f"It also lands at a lower estimated deployment cost than {second.get('name')}.")
        elif (first.get("estimated_total_cost") or 0) > (second.get("estimated_total_cost") or 0):
            differences.append(f"{second.get('name')} is cheaper, but the top option stayed ahead on overall fit.")
        if (first.get("stock_quantity") or 0) > (second.get("stock_quantity") or 0):
            differences.append(f"Inventory also looks healthier for {first.get('name')}.")
        elif first.get("fit_status") == "stretch":
            differences.append(f"{first.get('name')} is the stronger stretch option, while {second.get('name')} is safer on budget.")
        elif first.get("fit_status") == "limited_availability":
            differences.append(f"{first.get('name')} fits well, but stock is tighter than the next alternative.")
        return " ".join(differences).strip()

    def build_assumptions(self, requirements):
        assumptions = []
        categories = requirements.get("preferred_categories") or []
        if requirements.get("preferred_category") and requirements["preferred_category"] not in categories:
            categories = [requirements["preferred_category"]] + list(categories)
        category_set = set(categories)

        if not requirements.get("industry"):
            assumptions.append("No industry context was supplied, so ranking leaned on category, workload, budget, and stock fit.")
        if not requirements.get("workloads") and not requirements.get("application_signals"):
            assumptions.append("Workload details were not explicit, so the engine kept workload interpretation conservative until clarified.")
        if not (requirements.get("team_size") or requirements.get("quantity")):
            if "networking" in category_set:
                assumptions.append("No user or endpoint estimate was supplied, so the engine treated this as a single reference network deployment.")
            elif "servers" in category_set:
                assumptions.append("No user or workload scale was supplied, so the engine treated this as a single reference server environment.")
            elif "printers" in category_set:
                assumptions.append("No print-volume or site-scale signal was supplied, so the engine treated this as a single reference printer purchase.")
            elif "accessories" in category_set:
                assumptions.append("No seat count or quantity was supplied, so the engine treated this as a single reference accessory purchase.")
            else:
                assumptions.append("No seat count was supplied, so the engine treated this as a single reference configuration.")
        if not requirements.get("notes"):
            assumptions.append("No compatibility or policy notes were supplied, so deterministic fit and policy-alignment scoring used only catalog data.")
        if not requirements.get("growth_expectation"):
            assumptions.append("Growth was treated as steady unless explicitly stated otherwise.")
        elif requirements.get("growth_expectation") == "steady":
            assumptions.append("Growth was treated as steady unless explicitly stated otherwise.")
        if requirements.get("budget") is not None and requirements.get("budget_scope") == "per_unit":
            assumptions.append("Budget was interpreted as a per-unit budget for end-user device ranking.")
        elif requirements.get("budget") is not None and requirements.get("budget_scope") == "project_total":
            assumptions.append("Budget was interpreted as a project-level deployment budget.")
        elif requirements.get("budget") is not None:
            assumptions.append("Budget scope was not explicit, so budget fit stayed conservative until clarified.")
        if not requirements.get("performance_priority"):
            assumptions.append("Performance preference defaulted to a balanced recommendation strategy.")
        if requirements.get("ranking_persona") and requirements.get("ranking_persona") != "balanced":
            assumptions.append(f"Ranking persona was interpreted as {requirements['ranking_persona']}, so scoring leaned toward that buying priority.")
        if requirements.get("existing_infrastructure"):
            assumptions.append("Existing infrastructure hints were captured, but compatibility was still evaluated conservatively from available catalog data.")
        return assumptions

    def _build_single_explanation(self, requirements, target_profile, recommendation, allow_llm=True):
        if allow_llm:
            grounded = self.llm_client.invoke_text(
                "explanation.txt",
                {
                    "requirements": json.dumps(requirements or {}, ensure_ascii=True),
                    "target_profile": json.dumps(target_profile or {}, ensure_ascii=True),
                    "recommendation": json.dumps(recommendation or {}, ensure_ascii=True),
                },
            )
            if grounded:
                return grounded.strip()
        return self._build_structured_fallback_explanation(requirements, target_profile, recommendation)

    def _build_batched_explanation_sections(self, requirements, target_profile, recommendations, allow_llm=True):
        recommendations = list(recommendations or [])
        if not recommendations:
            return {}
        if not allow_llm:
            return {
                index: self._build_explanation_sections(
                    requirements,
                    target_profile,
                    recommendation,
                    allow_llm=False,
                )
                for index, recommendation in enumerate(recommendations)
            }

        shortlist_payload = []
        for index, recommendation in enumerate(recommendations, start=1):
            shortlist_payload.append(
                {
                    "index": index,
                    "name": recommendation.get("name"),
                    "category": recommendation.get("category"),
                    "price": recommendation.get("price"),
                    "currency": recommendation.get("currency"),
                    "score": recommendation.get("score"),
                    "fit_status": recommendation.get("fit_status"),
                    "processor": recommendation.get("processor"),
                    "ram_gb": recommendation.get("ram_gb"),
                    "storage_gb": recommendation.get("storage_gb"),
                    "gpu_tier": recommendation.get("gpu_tier"),
                    "stock_quantity": recommendation.get("stock_quantity"),
                    "estimated_total_cost": recommendation.get("estimated_total_cost"),
                    "reasons": recommendation.get("reasons") or [],
                    "trade-off": recommendation.get("trade-off") or [],
                }
            )

        payload = self.llm_client.invoke_json(
            "batched_explanations.txt",
            {
                "requirements": json.dumps(requirements or {}, ensure_ascii=True),
                "target_profile": json.dumps(target_profile or {}, ensure_ascii=True),
                "recommendations": json.dumps(shortlist_payload, ensure_ascii=True),
            },
        )
        parsed = self._normalize_batched_explanations(payload, recommendations, requirements, target_profile)
        if parsed:
            return parsed
        return {
            index: self._build_explanation_sections(
                requirements,
                target_profile,
                recommendation,
                allow_llm=False,
            )
            for index, recommendation in enumerate(recommendations)
        }

    def _normalize_batched_explanations(self, payload, recommendations, requirements=None, target_profile=None):
        if not isinstance(payload, dict):
            return {}
        items = payload.get("recommendations")
        if not isinstance(items, list):
            return {}

        normalized = {}
        for entry in items:
            if not isinstance(entry, dict):
                continue
            index = entry.get("index")
            try:
                zero_index = int(index) - 1
            except (TypeError, ValueError):
                continue
            if zero_index < 0 or zero_index >= len(recommendations):
                continue
            sections = {
                "workload_fit": str(entry.get("workload_fit") or "").strip(),
                "upgrade_implications": str(entry.get("upgrade_implications") or "").strip(),
                "assumptions": str(entry.get("assumptions") or "").strip(),
                "next_steps": str(entry.get("next_steps") or "").strip(),
                "trade-off": self._normalize_trade_offs(entry.get("trade-off") or entry.get("trade_off")),
            }
            if not any(value for value in sections.values()):
                continue
            if not sections["trade-off"]:
                sections["trade-off"] = self._build_trade_offs(requirements, target_profile, recommendations[zero_index])
            sections["explanation"] = self._compose_explanation_from_sections(sections)
            normalized[zero_index] = sections
        return normalized

    def _compose_explanation_from_sections(self, sections):
        ordered_sections = [
            ("## 1. Workload Fit", sections.get("workload_fit")),
            ("## 2. Upgrade Implications", sections.get("upgrade_implications")),
            ("## 3. Assumptions Made", sections.get("assumptions")),
            ("## 4. Next Steps", sections.get("next_steps")),
        ]
        rendered = []
        for heading, body in ordered_sections:
            body = str(body or "").strip()
            if not body:
                continue
            rendered.append(heading)
            rendered.append(body)
            rendered.append("")
        return "\n".join(rendered).strip()

    def _build_explanation_sections(self, requirements, target_profile, recommendation, allow_llm=True):
        explanation = self._build_single_explanation(
            requirements,
            target_profile,
            recommendation,
            allow_llm=allow_llm,
        )
        parsed_sections = self._split_explanation_sections(explanation)
        return {
            "explanation": explanation,
            "workload_fit": parsed_sections.get("workload_fit") or "",
            "upgrade_implications": parsed_sections.get("upgrade_implications") or "",
            "assumptions": parsed_sections.get("assumptions") or "",
            "next_steps": parsed_sections.get("next_steps") or "",
            "trade-off": self._build_trade_offs(requirements, target_profile, recommendation),
        }

    def _normalize_trade_offs(self, value):
        if isinstance(value, list):
            raw_items = value
        elif isinstance(value, str):
            raw_items = value.splitlines()
        else:
            raw_items = []

        items = []
        seen = set()
        for item in raw_items:
            cleaned = str(item or "").strip()
            cleaned = cleaned.lstrip("-*1234567890. ").strip()
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            items.append(cleaned)
            if len(items) >= 4:
                break
        return items

    def _build_trade_offs(self, requirements, target_profile, recommendation):
        requirements = dict(requirements or {})
        target_profile = dict(target_profile or {})
        recommendation = dict(recommendation or {})
        trade_offs = []

        fit_status = recommendation.get("fit_status")
        if fit_status == "stretch":
            trade_offs.append("Budget comfort is weaker because this option is being treated as a stretch fit.")
        elif fit_status == "limited_availability":
            trade_offs.append("Availability needs review because visible stock may not fully cover the rollout.")
        elif fit_status == "partial_fit":
            trade_offs.append("Some requirements are covered as a compromise rather than a clean full fit.")

        quantity = max(int(recommendation.get("estimated_quantity") or requirements.get("quantity") or requirements.get("team_size") or 1), 1)
        stock = recommendation.get("stock_quantity")
        if stock is not None and stock < quantity:
            trade_offs.append(f"Current stock covers only {stock} unit(s) against an estimated need of {quantity}.")

        if requirements.get("budget") is not None and requirements.get("budget_scope") not in {"per_unit", "project_total"}:
            trade_offs.append("Budget scope is not fully resolved, so price fit should be confirmed before purchase.")

        if recommendation.get("ram_gb") and target_profile.get("preferred_ram_gb"):
            if recommendation["ram_gb"] < target_profile["preferred_ram_gb"]:
                trade_offs.append(f"RAM meets enough to rank, but it is below the preferred {target_profile['preferred_ram_gb']}GB target.")

        if recommendation.get("storage_gb") and target_profile.get("preferred_storage_gb"):
            if recommendation["storage_gb"] < target_profile["preferred_storage_gb"]:
                trade_offs.append(f"Storage meets enough to rank, but it is below the preferred {target_profile['preferred_storage_gb']}GB target.")

        for reason in recommendation.get("reasons") or []:
            lowered = str(reason or "").lower()
            if any(token in lowered for token in ("slightly below", "under the target", "neutral", "incomplete", "penalized", "only ")):
                trade_offs.append(str(reason).strip())
            if len(trade_offs) >= 4:
                break

        if not trade_offs:
            trade_offs.append("No major trade-off was highlighted from the available catalog and requirement facts.")
        return self._normalize_trade_offs(trade_offs)

    def _split_explanation_sections(self, explanation):
        explanation = str(explanation or "").strip()
        sections = {
            "workload_fit": "",
            "upgrade_implications": "",
            "assumptions": "",
            "next_steps": "",
        }
        if not explanation:
            return sections

        heading_map = {
            "workload fit": "workload_fit",
            "upgrade implications": "upgrade_implications",
            "assumptions made": "assumptions",
            "next steps": "next_steps",
        }
        current_key = None
        current_lines = []

        def _flush_section():
            if current_key and current_lines:
                sections[current_key] = "\n".join(current_lines).strip()

        for raw_line in explanation.splitlines():
            line = str(raw_line or "")
            stripped = line.strip()
            if stripped.startswith("## "):
                normalized_heading = stripped[3:].strip()
                if ". " in normalized_heading:
                    normalized_heading = normalized_heading.split(". ", 1)[1].strip()
                normalized_heading = self._normalize_section_heading(normalized_heading)
                new_key = heading_map.get(normalized_heading)
                if new_key:
                    _flush_section()
                    current_key = new_key
                    current_lines = [line]
                    continue
            if current_key:
                current_lines.append(line)

        _flush_section()
        return sections

    def _normalize_section_heading(self, heading):
        heading = str(heading or "").strip().lower()
        for token in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2015", "\u2212"):
            heading = heading.replace(token, "-")
        heading = " ".join(heading.split())
        return heading

    def _business_reasoning(self, requirements, recommendation):
        persona = str(requirements.get("ranking_persona") or "balanced").strip().lower()
        fit_status = recommendation.get("fit_status")

        if persona == "finance-first":
            return ["This was favored for keeping budget exposure lower while still covering the stated use case."]
        if persona == "performance-first":
            return ["This ranked well because extra performance headroom mattered more than a lowest-cost configuration."]
        if persona == "support-first":
            return ["This was favored because operational support continuity mattered more than squeezing unit cost."]
        if persona == "standardization-first":
            return ["This benefited from standardization-oriented scoring around explicit brand or seller preferences and procurement consistency."]
        if persona == "availability-first":
            return ["This was favored because immediate rollout readiness mattered more than marginal spec headroom."]
        if fit_status == "stretch":
            return ["This stayed in view because it offers stronger headroom, even though it pushes beyond the preferred budget."]
        if fit_status == "limited_availability":
            return ["This ranked on technical fit, but inventory risk still needs attention before committing to rollout."]
        if fit_status == "partial_fit":
            return ["This remains viable mainly as a practical compromise between fit, cost, and availability."]
        return ["This balanced business fit, technical coverage, and deployability better than the nearby alternatives."]

    def _build_upgrade_implications(self, target_profile, recommendation):
        implications = []
        if recommendation.get("ram_gb") and target_profile.get("min_ram_gb"):
            if recommendation["ram_gb"] > target_profile["min_ram_gb"]:
                implications.append("Upgrading workload intensity should still be comfortable in the near term.")
        if recommendation.get("storage_gb") and target_profile.get("min_storage_gb"):
            if recommendation["storage_gb"] > target_profile["min_storage_gb"]:
                implications.append("There is storage headroom for moderate growth in apps and files.")
        return " ".join(implications).strip()

    def _build_structured_fallback_explanation(self, requirements, target_profile, recommendation):
        sections = [
            "## 1. Workload Fit",
            self._build_workload_fit_table(requirements, target_profile, recommendation),
            "",
            "## 2. Business Rationale",
            self._markdown_list(self._business_reasoning(requirements, recommendation)),
            "",
            "## 3. Upgrade Implications",
            self._markdown_list(self._upgrade_bullets(target_profile, recommendation)),
            "",
            "## 4. Assumptions Made",
            self._markdown_numbered_list(self.build_assumptions(requirements)),
            "",
            "## 5. Next Steps",
            self._markdown_numbered_list(self._next_steps(requirements, recommendation)),
        ]
        return "\n".join(str(part or "").rstrip() for part in sections if part is not None).strip()

    def _build_workload_fit_table(self, requirements, target_profile, recommendation):
        category = str(recommendation.get("category") or "").strip().lower()
        if category == "printers":
            return self._build_printer_fit_table(requirements, target_profile, recommendation)
        if category == "accessories":
            return self._build_accessory_fit_table(requirements, target_profile, recommendation)

        rows = []
        categories = target_profile.get("categories") or requirements.get("preferred_categories") or []
        minimum_category = " or ".join(self._humanize(value) for value in categories) or "Not specified"
        provided_category = self._humanize(recommendation.get("category")) or "Not provided"
        rows.append(
            ("Category", minimum_category, provided_category, self._category_comment(categories, recommendation))
        )

        min_cpu_score = target_profile.get("min_cpu_score")
        if min_cpu_score or recommendation.get("processor") or recommendation.get("cpu_tier"):
            minimum_cpu = f"score >= {min_cpu_score}" if min_cpu_score else "Not specified"
            provided_cpu = recommendation.get("processor") or self._humanize(recommendation.get("cpu_tier")) or "Not provided"
            rows.append(
                ("CPU", minimum_cpu, provided_cpu, self._cpu_comment(min_cpu_score, recommendation))
            )

        min_ram_gb = target_profile.get("min_ram_gb")
        preferred_ram_gb = target_profile.get("preferred_ram_gb")
        if min_ram_gb or recommendation.get("ram_gb") is not None:
            minimum_ram = f">= {min_ram_gb}GB" if min_ram_gb else "Not specified"
            if preferred_ram_gb:
                minimum_ram += f" (preferred {preferred_ram_gb}GB)"
            provided_ram = f"{recommendation.get('ram_gb')}GB" if recommendation.get("ram_gb") is not None else "Not provided"
            rows.append(
                ("RAM", minimum_ram, provided_ram, self._ram_comment(target_profile, recommendation))
            )

        min_storage_gb = target_profile.get("min_storage_gb")
        preferred_storage_gb = target_profile.get("preferred_storage_gb")
        if min_storage_gb or recommendation.get("storage_gb") is not None:
            minimum_storage = f">= {min_storage_gb}GB" if min_storage_gb else "Not specified"
            if preferred_storage_gb:
                minimum_storage += f" (preferred {preferred_storage_gb}GB)"
            provided_storage = f"{recommendation.get('storage_gb')}GB" if recommendation.get("storage_gb") is not None else "Not provided"
            rows.append(
                ("Storage", minimum_storage, provided_storage, self._storage_comment(target_profile, recommendation))
            )

        min_gpu_tier = target_profile.get("min_gpu_tier")
        if min_gpu_tier or recommendation.get("gpu_tier") or recommendation.get("gpu"):
            minimum_gpu = self._humanize(min_gpu_tier) or "Not specified"
            provided_gpu = self._humanize(recommendation.get("gpu_tier")) or recommendation.get("gpu") or "Not provided"
            rows.append(
                ("GPU", minimum_gpu, provided_gpu, self._gpu_comment(target_profile, recommendation))
            )

        return self._markdown_table(
            ["Requirement", "Minimum needed", "What the product provides", "Fit comment"],
            rows,
        )

    def _upgrade_bullets(self, target_profile, recommendation):
        bullets = []
        category = str(recommendation.get("category") or "").strip().lower()
        if category == "printers":
            if recommendation.get("print_speed_ppm") and target_profile.get("min_print_speed_ppm") and recommendation["print_speed_ppm"] < target_profile["min_print_speed_ppm"]:
                bullets.append("A faster print engine would improve queue handling for busier print volumes.")
            if target_profile.get("required_automatic_document_feeder") and not recommendation.get("automatic_document_feeder"):
                bullets.append("Moving to a model with an automatic document feeder would better suit scan-heavy workflows.")
        if category == "accessories" and recommendation.get("accessory_type") == "headset":
            bullets.append("A higher-tier headset could add comfort or longer battery life for heavier daily use.")
        upgrade_text = self._build_upgrade_implications(target_profile, recommendation)
        if upgrade_text:
            bullets.append(upgrade_text)
        if recommendation.get("ram_gb") and target_profile.get("preferred_ram_gb") and recommendation["ram_gb"] < target_profile["preferred_ram_gb"]:
            bullets.append(f"Moving to {target_profile['preferred_ram_gb']}GB RAM would add more headroom for heavier workloads.")
        if recommendation.get("storage_gb") and target_profile.get("preferred_storage_gb") and recommendation["storage_gb"] < target_profile["preferred_storage_gb"]:
            bullets.append(f"Moving to {target_profile['preferred_storage_gb']}GB storage would add more room for larger files and local assets.")
        if not bullets:
            bullets.append("No grounded upgrade implications were available from the current catalog fields.")
        return bullets

    def _next_steps(self, requirements, recommendation):
        steps = []
        quantity = max(int(recommendation.get("estimated_quantity") or requirements.get("quantity") or requirements.get("team_size") or 1), 1)
        stock = recommendation.get("stock_quantity")
        if stock is not None and stock < quantity:
            steps.append(f"Confirm how the remaining {quantity - stock} unit(s) will be sourced before finalizing the rollout.")
        steps.append("Review the selected configuration against any internal support, warranty, or procurement policy requirements.")
        steps.append("Use the shortlist comparison before purchase if you want to trade budget, stock, or performance differently.")
        return steps[:3]

    def _build_printer_fit_table(self, requirements, target_profile, recommendation):
        categories = target_profile.get("categories") or requirements.get("preferred_categories") or []
        rows = [
            (
                "Category",
                " or ".join(self._humanize(value) for value in categories) or "Not specified",
                self._humanize(recommendation.get("category")) or "Not provided",
                self._category_comment(categories, recommendation),
            ),
            (
                "Printer Type",
                self._humanize(target_profile.get("required_printer_type")) or "Not specified",
                self._humanize(recommendation.get("printer_type")) or "Not provided",
                self._printer_type_comment(target_profile, recommendation),
            ),
            (
                "Print Speed",
                f">= {target_profile.get('min_print_speed_ppm')} ppm" if target_profile.get("min_print_speed_ppm") else "Not specified",
                f"{recommendation.get('print_speed_ppm')} ppm" if recommendation.get("print_speed_ppm") is not None else "Not provided",
                self._printer_speed_comment(target_profile, recommendation),
            ),
            (
                "Duty Cycle",
                f">= {target_profile.get('min_monthly_duty_cycle_pages')} pages/month" if target_profile.get("min_monthly_duty_cycle_pages") else "Not specified",
                f"{recommendation.get('monthly_duty_cycle_pages')} pages/month" if recommendation.get("monthly_duty_cycle_pages") is not None else "Not provided",
                self._printer_duty_cycle_comment(target_profile, recommendation),
            ),
            (
                "Output / Workflow",
                self._printer_workflow_requirement_text(target_profile),
                self._printer_workflow_provided_text(recommendation),
                self._printer_workflow_comment(target_profile, recommendation),
            ),
        ]
        return self._markdown_table(
            ["Requirement", "Minimum needed", "What the product provides", "Fit comment"],
            rows,
        )

    def _build_accessory_fit_table(self, requirements, target_profile, recommendation):
        categories = target_profile.get("categories") or requirements.get("preferred_categories") or []
        rows = [
            (
                "Category",
                " or ".join(self._humanize(value) for value in categories) or "Not specified",
                self._humanize(recommendation.get("category")) or "Not provided",
                self._category_comment(categories, recommendation),
            ),
            (
                "Accessory Family",
                self._humanize(target_profile.get("required_accessory_type")) or "Not specified",
                self._humanize(recommendation.get("accessory_type")) or "Not provided",
                self._accessory_type_comment(target_profile, recommendation),
            ),
            (
                "Connectivity",
                "Not specified",
                recommendation.get("connectivity") or "Not provided",
                "Connectivity details are informational unless a host-interface requirement is stated explicitly.",
            ),
        ]
        return self._markdown_table(
            ["Requirement", "Minimum needed", "What the product provides", "Fit comment"],
            rows,
        )

    def _build_printer_tradeoff_table(self, requirements, target_profile, recommendation):
        rows = []
        quantity = max(int(recommendation.get("estimated_quantity") or requirements.get("quantity") or 1), 1)
        stock = recommendation.get("stock_quantity")
        if stock is not None:
            rows.append(
                (
                    "Availability",
                    f"{stock} unit(s) currently visible in stock.",
                    "Current stock fully covers the immediate need." if stock >= quantity else f"Current stock does not fully cover the estimated {quantity}-unit need.",
                )
            )
        rows.append(
            (
                "Cost",
                f"Unit price is {recommendation.get('price')} {recommendation.get('currency')}.",
                "None highlighted from budget fit." if recommendation.get("fit_status") != "stretch" else "It trades budget comfort for stronger print capability.",
            )
        )
        if recommendation.get("print_speed_ppm") is not None:
            rows.append(
                (
                    "Print Speed",
                    f"About {recommendation.get('print_speed_ppm')} ppm.",
                    self._printer_speed_comment(target_profile, recommendation),
                )
            )
        if recommendation.get("monthly_duty_cycle_pages") is not None:
            rows.append(
                (
                    "Duty Cycle",
                    f"About {recommendation.get('monthly_duty_cycle_pages')} pages/month.",
                    self._printer_duty_cycle_comment(target_profile, recommendation),
                )
            )
        return self._markdown_table(["Aspect", "What you get", "What you give up"], rows[:5])

    def _build_accessory_tradeoff_table(self, requirements, target_profile, recommendation):
        rows = []
        quantity = max(int(recommendation.get("estimated_quantity") or requirements.get("quantity") or requirements.get("team_size") or 1), 1)
        stock = recommendation.get("stock_quantity")
        if stock is not None:
            rows.append(
                (
                    "Availability",
                    f"{stock} unit(s) currently visible in stock.",
                    "Current stock fully covers the estimated need." if stock >= quantity else f"Current stock does not fully cover the estimated {quantity}-unit need.",
                )
            )
        rows.append(
            (
                "Cost",
                f"Unit price is {recommendation.get('price')} {recommendation.get('currency')}.",
                "None highlighted from budget fit." if recommendation.get("fit_status") != "stretch" else "It trades budget comfort for a better peripheral option.",
            )
        )
        if recommendation.get("connectivity"):
            rows.append(
                (
                    "Connectivity",
                    recommendation.get("connectivity"),
                    "Host compatibility should still be reviewed if your environment has a strict interface requirement.",
                )
            )
        return self._markdown_table(["Aspect", "What you get", "What you give up"], rows[:5])

    def _category_comment(self, categories, recommendation):
        category = recommendation.get("category")
        if category and category in set(categories or []):
            return "Matches an allowed category in the target profile."
        if category:
            return "This category is adjacent to the target scope and should be reviewed carefully."
        return "Category data was not explicit in the catalog payload."

    def _cpu_comment(self, min_cpu_score, recommendation):
        for reason in recommendation.get("reasons") or []:
            lowered = str(reason).lower()
            if "processor tier matches" in lowered:
                return "Processor tier matches the workload target."
            if "processor tier is lighter" in lowered:
                return "Processor tier is lighter than the workload target."
        if min_cpu_score:
            return f"CPU fit should be checked against the target score of {min_cpu_score}."
        return "CPU requirement was not explicit in the target profile."

    def _ram_comment(self, target_profile, recommendation):
        min_ram_gb = target_profile.get("min_ram_gb") or 0
        preferred_ram_gb = target_profile.get("preferred_ram_gb") or 0
        ram_gb = recommendation.get("ram_gb") or 0
        if not ram_gb:
            return "RAM data was not explicit in the catalog payload."
        if min_ram_gb and ram_gb < min_ram_gb:
            return "Below the minimum RAM target."
        if preferred_ram_gb and ram_gb < preferred_ram_gb:
            return "Meets the minimum, but not the preferred RAM target."
        if min_ram_gb:
            return "Meets the current RAM requirement."
        return "RAM looks adequate based on the available profile data."

    def _storage_comment(self, target_profile, recommendation):
        min_storage_gb = target_profile.get("min_storage_gb") or 0
        preferred_storage_gb = target_profile.get("preferred_storage_gb") or 0
        storage_gb = recommendation.get("storage_gb") or 0
        if not storage_gb:
            return "Storage data was not explicit in the catalog payload."
        if min_storage_gb and storage_gb < min_storage_gb:
            return "Below the minimum storage target."
        if preferred_storage_gb and storage_gb < preferred_storage_gb:
            return "Meets the minimum, but not the preferred storage target."
        if min_storage_gb:
            return "Meets the current storage requirement."
        return "Storage looks adequate based on the available profile data."

    def _gpu_comment(self, target_profile, recommendation):
        min_gpu_tier = target_profile.get("min_gpu_tier") or "integrated"
        current_gpu_tier = recommendation.get("gpu_tier") or "integrated"
        current_value = self.GPU_TIER_ORDER.get(current_gpu_tier, 1)
        required_value = self.GPU_TIER_ORDER.get(min_gpu_tier, 1)
        if current_value >= required_value:
            return "Graphics capability meets the expected workload tier."
        return "Graphics capability is below the expected workload tier."

    def _printer_type_comment(self, target_profile, recommendation):
        required_type = str(target_profile.get("required_printer_type") or "").strip().lower()
        current_type = str(recommendation.get("printer_type") or "").strip().lower()
        if not current_type:
            return "Printer subtype was not explicit in the catalog payload."
        if required_type and current_type != required_type:
            return "Printer subtype is different from the explicitly requested printer role."
        if required_type:
            return "Printer subtype matches the requested role."
        return "Printer subtype is usable for a general printing brief."

    def _printer_speed_comment(self, target_profile, recommendation):
        required = int(target_profile.get("min_print_speed_ppm") or 0)
        current = recommendation.get("print_speed_ppm")
        if current in {None, ""}:
            return "Print-speed metadata was not explicit in the catalog payload."
        if required and int(current) < required:
            return "Below the target print-speed threshold."
        if required:
            return "Meets the current print-speed requirement."
        return "Print speed looks reasonable based on the available profile data."

    def _printer_duty_cycle_comment(self, target_profile, recommendation):
        required = int(target_profile.get("min_monthly_duty_cycle_pages") or 0)
        current = recommendation.get("monthly_duty_cycle_pages")
        if current in {None, ""}:
            return "Duty-cycle metadata was not explicit in the catalog payload."
        if required and int(current) < required:
            return "Below the expected monthly print volume."
        if required:
            return "Meets the current monthly duty-cycle requirement."
        return "Duty-cycle capacity looks acceptable from the available profile data."

    def _printer_workflow_requirement_text(self, target_profile):
        requirements = []
        if target_profile.get("required_color_output"):
            requirements.append(self._humanize(target_profile.get("required_color_output")))
        if target_profile.get("required_duplex_printing"):
            requirements.append("Automatic duplex")
        if target_profile.get("required_scanner"):
            requirements.append("Scan / copy support")
        if target_profile.get("required_automatic_document_feeder"):
            requirements.append("ADF")
        if target_profile.get("required_paper_sizes"):
            requirements.append(", ".join(target_profile.get("required_paper_sizes") or []))
        return " + ".join(requirements) if requirements else "Not specified"

    def _printer_workflow_provided_text(self, recommendation):
        details = []
        if recommendation.get("color_output"):
            details.append(self._humanize(recommendation.get("color_output")))
        if recommendation.get("duplex_printing"):
            details.append("Automatic duplex")
        if recommendation.get("scanner_type"):
            details.append(self._humanize(recommendation.get("scanner_type")))
        if recommendation.get("automatic_document_feeder"):
            details.append("ADF")
        if recommendation.get("paper_size_support"):
            details.append(", ".join(recommendation.get("paper_size_support") or []))
        return " + ".join(details) if details else "Not provided"

    def _printer_workflow_comment(self, target_profile, recommendation):
        if target_profile.get("required_color_output") and recommendation.get("color_output") != target_profile.get("required_color_output"):
            return "Output mode does not match the request."
        if target_profile.get("required_duplex_printing") and not recommendation.get("duplex_printing"):
            return "Automatic duplex printing is missing."
        if target_profile.get("required_scanner") and not recommendation.get("scanner_type"):
            return "Scanning support is missing."
        if target_profile.get("required_automatic_document_feeder") and not recommendation.get("automatic_document_feeder"):
            return "Automatic document feeder support is missing."
        required_sizes = {str(item).upper() for item in (target_profile.get("required_paper_sizes") or [])}
        available_sizes = {str(item).upper() for item in (recommendation.get("paper_size_support") or [])}
        if required_sizes and not required_sizes.issubset(available_sizes):
            return "Paper-size support does not fully match the request."
        return "Workflow features align with the current printing requirement."

    def _accessory_type_comment(self, target_profile, recommendation):
        required = str(target_profile.get("required_accessory_type") or "").strip().lower()
        current = str(recommendation.get("accessory_type") or "").strip().lower()
        if not current:
            return "Accessory family was not explicit in the catalog payload."
        if required and current != required:
            return "Accessory family does not match the requested peripheral type."
        if required:
            return "Accessory family matches the requested peripheral type."
        return "Accessory family is suitable for a general peripheral brief."

    def _markdown_table(self, headers, rows):
        header_line = "| " + " | ".join(headers) + " |"
        divider_line = "| " + " | ".join(["---"] * len(headers)) + " |"
        body_lines = []
        for row in rows:
            body_lines.append("| " + " | ".join(self._table_cell(value) for value in row) + " |")
        return "\n".join([header_line, divider_line] + body_lines)

    def _markdown_list(self, items):
        items = [str(item).strip() for item in (items or []) if str(item or "").strip()]
        return "\n".join(f"- {item}" for item in items) if items else "- No additional detail was returned."

    def _markdown_numbered_list(self, items):
        items = [str(item).strip() for item in (items or []) if str(item or "").strip()]
        return "\n".join(f"{index}. {item}" for index, item in enumerate(items, start=1)) if items else "1. No additional detail was returned."

    def _table_cell(self, value):
        return str(value or "Not provided").replace("|", "\\|").replace("\n", "<br>")

    def _humanize(self, value):
        return str(value or "").replace("_", " ").strip().title()

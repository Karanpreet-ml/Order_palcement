BENCHMARK_SCENARIOS = [
    {
        "name": "office_laptop_rollout",
        "payload": {
            "category": "Laptop",
            "workload_types": ["office"],
            "team_size": "20",
            "budget": 5000,
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "OfficeBook 14",
            "ranking_deferred": False,
        },
    },
    {
        "name": "office_laptop_fully_specified",
        "payload": {
            "category": "Laptop",
            "workload_types": ["office"],
            "team_size": "20",
            "budget": 5000,
            "budget_scope": "per_unit",
            "purchase_scope": "team_rollout",
            "growth_expectation": "steady",
            "performance_priority": "balanced",
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "OfficeBook 14",
            "ranking_deferred": False,
            "recommendation_mode": "firm_recommendation",
            "recommended_question_budget": 0,
        },
        "release_gate_tags": {
            "adequately_specified": True,
        },
    },
    {
        "name": "office_net_new_rejects_refresh_template",
        "payload": {
            "category": "Laptop",
            "workload_types": ["office"],
            "team_size": "12",
            "budget": 5000,
            "budget_scope": "per_unit",
            "purchase_scope": "team_rollout",
            "replacement_mode": "net_new",
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "OfficeBook 14",
            "ranking_deferred": False,
            "selected_template_id": "office-starter-v1",
            "template_match_quality": "exact",
            "rejected_gap_types_include": ["unsupported_replacement_mode"],
        },
    },
    {
        "name": "developer_laptop_rollout",
        "payload": {
            "category": "Laptop",
            "workload_types": ["software development"],
            "team_size": "15",
            "budget": 6500,
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "Developer Pro 15",
            "ranking_deferred": False,
        },
    },
    {
        "name": "developer_laptop_fully_specified",
        "payload": {
            "category": "Laptop",
            "workload_types": ["software development"],
            "application_signals": ["developer_toolchain"],
            "team_size": "15",
            "budget": 6500,
            "budget_scope": "per_unit",
            "purchase_scope": "team_rollout",
            "growth_expectation": "moderate_growth",
            "performance_priority": "balanced",
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "Developer Pro 15",
            "ranking_deferred": False,
            "recommendation_mode": "firm_recommendation",
            "recommended_question_budget": 0,
        },
        "release_gate_tags": {
            "adequately_specified": True,
        },
    },
    {
        "name": "creative_laptop_rollout",
        "payload": {
            "category": "Laptop",
            "workload_types": ["creative design"],
            "team_size": "6",
            "budget": 9500,
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "Creative Studio 16",
            "ranking_deferred": False,
        },
    },
    {
        "name": "virtualization_server",
        "payload": {
            "chat_text": "Need one on-prem virtualization server for a small office with room for growth",
            "currency": "MYR",
            "budget": 20000,
        },
        "expectations": {
            "top_name": "VirtualEdge Server X1",
            "ranking_deferred": False,
        },
    },
    {
        "name": "network_connectivity",
        "payload": {
            "category": "Networking",
            "workload_types": ["networking"],
            "team_size": "1",
            "budget": 5000,
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "Secure Branch Router",
            "ranking_deferred": False,
        },
        "release_gate_tags": {
            "adequately_specified": True,
        },
    },
    {
        "name": "branch_office_networking",
        "payload": {
            "chat_text": "Opening a branch office and need networking gear under 4000 and it will be 100 in future",
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "Secure Branch Router",
            "ranking_deferred": False,
        },
    },
    {
        "name": "remote_hybrid_workforce",
        "payload": {
            "chat_text": "Need 12 laptops for a remote and hybrid team working from home under 5000 each",
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "OfficeBook 14",
            "ranking_deferred": False,
        },
    },
    {
        "name": "remote_hybrid_with_occasional_travel_boundary",
        "payload": {
            "chat_text": "Need 12 laptops for a remote and hybrid team, with occasional travel, mostly home office use under 5000 each",
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "OfficeBook 14",
            "ranking_deferred": False,
            "selected_template_id": "remote-hybrid-workforce-starter-v1",
            "template_match_quality": "exact",
        },
    },
    {
        "name": "startup_office_productivity",
        "payload": {
            "chat_text": "Need 5 laptops for a startup founding team doing email, spreadsheets, and browser work under 4500 each",
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "OfficeBook 14",
            "ranking_deferred": False,
        },
    },
    {
        "name": "budget_refresh_rollout",
        "payload": {
            "chat_text": "Need to refresh 20 office laptops for staff under 4000 each",
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "BudgetMate 15",
            "ranking_deferred": False,
        },
    },
    {
        "name": "urgent_in_stock_rollout",
        "payload": {
            "chat_text": "Need 8 office laptops in stock now under 4300 each",
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "OfficeBook 14",
            "ranking_deferred": False,
        },
    },
    {
        "name": "phased_rollout_devices",
        "payload": {
            "chat_text": "Need a phased rollout for 30 office laptops under 4500 each",
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "BudgetMate 15",
            "ranking_deferred": False,
        },
    },
    {
        "name": "field_sales_mobile_workforce",
        "payload": {
            "chat_text": "Need 10 lightweight laptops for field sales reps working on the road and at customer sites under 6500 each",
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "Developer Pro 15",
            "ranking_deferred": False,
        },
    },
    {
        "name": "virtualization_unknown_dependency_closest_match",
        "payload": {
            "category": "Server",
            "workload_types": ["server infrastructure"],
            "capability_tags": ["virtualization"],
            "budget": 20000,
            "notes": "Must work with our current environment",
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "VirtualEdge Server X1",
            "ranking_deferred": False,
            "recommendation_mode": "provisional_recommendation",
        },
    },
    {
        "name": "network_refresh_unknown_dependency_closest_match",
        "payload": {
            "chat_text": "Need to refresh our network gear but it must fit our current environment under 5000",
            "currency": "MYR",
        },
        "expectations": {
            "top_name": "Secure Branch Router",
            "ranking_deferred": False,
            "recommendation_mode": "provisional_recommendation",
        },
    },
    {
        "name": "urgent_server_coverage_gap",
        "payload": {
            "category": "Server",
            "workload_types": ["server infrastructure"],
            "capability_tags": ["virtualization"],
            "budget": 20000,
            "availability_need": "in_stock_now",
            "currency": "MYR",
        },
        "expectations": {
            "ranking_deferred": False,
            "recommendation_mode": "expert_review_recommended",
        },
    },
    {
        "name": "phased_server_coverage_gap",
        "payload": {
            "category": "Server",
            "workload_types": ["server infrastructure"],
            "capability_tags": ["virtualization"],
            "budget": 20000,
            "rollout_type": "phased",
            "currency": "MYR",
        },
        "expectations": {
            "ranking_deferred": False,
            "recommendation_mode": "expert_review_recommended",
        },
    },
    {
        "name": "incompatible_dependency_coverage_gap",
        "payload": {
            "category": "Server",
            "workload_types": ["server infrastructure"],
            "capability_tags": ["virtualization"],
            "budget": 20000,
            "existing_infrastructure": ["mac"],
            "notes": "Must stay compatible with our Mac-only environment",
            "currency": "MYR",
        },
        "expectations": {
            "ranking_deferred": False,
            "recommendation_mode": "expert_review_recommended",
        },
    },
    {
        "name": "unsupported_category_mix_coverage_gap",
        "payload": {
            "preferred_categories": ["laptops", "servers"],
            "workload_types": ["office"],
            "budget": 5000,
            "currency": "MYR",
        },
        "expectations": {
            "ranking_deferred": False,
            "recommendation_mode": "expert_review_recommended",
        },
    },
    {
        "name": "multi_intent_grouped_outputs",
        "payload": {
            "chat_text": "Need 15 laptops for software developers and a secure branch office router under 6500",
            "currency": "MYR",
        },
        "expectations": {
            "ranking_deferred": False,
            "group_count": 2,
            "group_top_names": ["Developer Pro 15", "Secure Branch Router"],
        },
    },
    {
        "name": "multi_intent_validated_bundle",
        "payload": {
            "chat_text": (
                "Need 12 laptops for software developers using VS Code and Docker under 6500 each "
                "and a secure branch office router for 40 VPN users under 5000 each with moderate growth"
            ),
            "currency": "MYR",
        },
        "expectations": {
            "ranking_deferred": False,
            "group_count": 2,
            "group_top_names": ["Developer Pro 15", "Secure Branch Router"],
            "recommendation_mode": "firm_recommendation",
            "recommended_question_budget": 0,
            "bundle_validated": True,
            "bundle_option_status": "validated",
        },
        "release_gate_tags": {
            "adequately_specified": True,
            "bundle_quality": True,
        },
    },
    {
        "name": "bundle_capacity_no_fit",
        "payload": {
            "chat_text": (
                "Need 16 laptops for software developers using VS Code and Docker under 6500 each "
                "and a secure branch office router for 40 VPN users under 5000 each with moderate growth"
            ),
            "currency": "MYR",
        },
        "expectations": {
            "ranking_deferred": False,
            "group_count": 2,
            "group_top_names": ["Developer Pro 15", "Secure Branch Router"],
            "recommendation_mode": "expert_review_recommended",
            "bundle_validated": False,
            "bundle_conflict_codes": ["bundle_capacity_shortfall"],
            "bundle_option_status": "rejected",
        },
        "release_gate_tags": {
            "bundle_quality": True,
            "bundle_no_fit": True,
        },
    },
    {
        "name": "returnable_server_no_fit",
        "payload": {
            "category": "Server",
            "workload_types": ["server infrastructure"],
            "budget": 20000,
            "currency": "MYR",
            "require_returnable": True,
        },
        "expectations": {
            "recommended_count": 0,
            "fallback_reason": "policy_rejected_all",
            "expert_review_eligible": True,
            "ranking_deferred": False,
        },
    },
    {
        "name": "ambiguous_brief_low_confidence",
        "payload": {
            "chat_text": "Need something sensible for a new 20-person team.",
            "currency": "MYR",
        },
        "expectations": {
            "recommended_count": 0,
            "fallback_reason": "blocking_clarification_required",
            "expert_review_eligible": True,
            "ranking_deferred": True,
        },
    },
]


PHASE2_VALIDATION_SCENARIOS = [
    {
        "name": "phase2_printer_shared_office_inr",
        "catalog_size": "corrected_json",
        "payload": {
            "chat_text": "Need a color duplex all-in-one printer with scan support for 20 users under 20000 INR.",
            "currency": "INR",
        },
        "expectations": {
            "ranking_deferred": False,
            "selected_template_id": "office-printing-starter-v1",
            "top_category": "printers",
            "recommended_count_min": 1,
        },
    },
    {
        "name": "phase2_keyboard_rollout_inr",
        "catalog_size": "corrected_json",
        "payload": {
            "chat_text": "Need 12 wireless keyboards for office staff under 2500 each.",
            "currency": "INR",
        },
        "expectations": {
            "ranking_deferred": False,
            "selected_template_id": "peripheral-accessory-starter-v1",
            "top_category": "accessories",
            "top_accessory_type": "keyboard",
            "recommended_count_min": 1,
        },
    },
    {
        "name": "phase2_mouse_rollout_inr",
        "catalog_size": "corrected_json",
        "payload": {
            "chat_text": "Need 12 wireless mice for office staff under 2000 each.",
            "currency": "INR",
        },
        "expectations": {
            "ranking_deferred": False,
            "selected_template_id": "peripheral-accessory-starter-v1",
            "top_category": "accessories",
            "top_accessory_type": "mouse",
            "recommended_count_min": 1,
        },
    },
    {
        "name": "phase2_headset_rollout_inr",
        "catalog_size": "corrected_json",
        "payload": {
            "chat_text": "Need 15 wireless headsets for a support team under 5000 each.",
            "currency": "INR",
        },
        "expectations": {
            "ranking_deferred": False,
            "selected_template_id": "peripheral-accessory-starter-v1",
            "top_category": "accessories",
            "top_accessory_type": "headset",
            "recommended_count_min": 1,
        },
    },
    {
        "name": "phase2_webcam_guardrail_inr",
        "catalog_size": "corrected_json",
        "payload": {
            "chat_text": "Need 10 webcams for a support team under 5000 each.",
            "currency": "INR",
        },
        "expectations": {
            "ranking_deferred": False,
            "selected_template_id": "peripheral-accessory-starter-v1",
            "recommended_count": 0,
            "catalog_validation_rejected_min": 1,
        },
    },
    {
        "name": "phase2_laptops_plus_headsets_bundle_inr",
        "catalog_size": "corrected_json",
        "payload": {
            "chat_text": (
                "Need 10 laptops for software developers using VS Code and Docker under 90000 each "
                "and 10 wireless headsets under 5000 each with moderate growth and balanced performance."
            ),
            "currency": "INR",
        },
        "expectations": {
            "ranking_deferred": False,
            "selected_template_id": "multi-intent-mixed-request-v1",
            "group_count": 2,
            "group_categories": ["accessories", "laptops"],
            "bundle_validated": True,
            "bundle_option_status": "validated",
        },
    },
    {
        "name": "phase2_router_plus_headsets_missing_host_bundle_inr",
        "catalog_size": "corrected_json",
        "payload": {
            "chat_text": "Need a secure branch office router for 40 VPN users under 50000 INR and 10 wireless headsets under 5000 each.",
            "currency": "INR",
        },
        "expectations": {
            "ranking_deferred": False,
            "selected_template_id": "multi-intent-mixed-request-v1",
            "group_count": 2,
            "group_categories": ["accessories", "networking"],
            "bundle_validated": False,
            "bundle_conflict_codes": ["bundle_accessory_host_missing"],
            "bundle_option_status": "rejected",
        },
    },
]


SOURCE_PARITY_SCENARIOS = [
    {
        "name": "parity_printer_shared_office_inr",
        "payload": {
            "chat_text": "Need a color duplex all-in-one printer with scan support for 20 users under 20000 INR.",
            "currency": "INR",
        },
    },
    {
        "name": "parity_developer_laptop_rollout_inr",
        "payload": {
            "chat_text": (
                "Need 10 laptops for software developers using VS Code and Docker under 90000 each "
                "with moderate growth and balanced performance."
            ),
            "currency": "INR",
        },
    },
    {
        "name": "parity_headset_rollout_inr",
        "payload": {
            "chat_text": "Need 15 wireless headsets for a support team under 5000 each.",
            "currency": "INR",
        },
    },
    {
        "name": "parity_webcam_guardrail_inr",
        "payload": {
            "chat_text": "Need 10 webcams for a support team under 5000 each.",
            "currency": "INR",
        },
    },
    {
        "name": "parity_branch_router_inr",
        "payload": {
            "chat_text": (
                "Need a secure branch office router for 40 VPN users under 50000 INR "
                "with moderate growth and balanced performance."
            ),
            "currency": "INR",
        },
    },
    {
        "name": "parity_virtualization_server_inr",
        "payload": {
            "chat_text": (
                "Need one on-prem virtualization server for a small office under 600000 INR "
                "with moderate growth and balanced performance."
            ),
            "currency": "INR",
        },
    },
    {
        "name": "parity_laptops_plus_headsets_bundle_inr",
        "payload": {
            "chat_text": (
                "Need 10 laptops for software developers using VS Code and Docker under 90000 each "
                "and 10 wireless headsets under 5000 each with moderate growth and balanced performance."
            ),
            "currency": "INR",
        },
    },
    {
        "name": "parity_router_plus_headsets_missing_host_bundle_inr",
        "payload": {
            "chat_text": (
                "Need a secure branch office router for 40 VPN users under 50000 INR "
                "and 10 wireless headsets under 5000 each."
            ),
            "currency": "INR",
        },
    },
]

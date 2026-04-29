def build_narrowing_guidance(preferences, readiness):
    preferences = dict(preferences or {})
    readiness = dict(readiness or {})
    missing_signals = list(readiness.get("missing_signals") or [])
    if not missing_signals:
        return []

    sections = []
    missing_set = set(missing_signals)

    if "workload_or_application_profile" in missing_set:
        sections.append(
            {
                "title": "Narrow Down The Work Profile",
                "description": (
                    "Pick the closest day-to-day usage pattern so the recommendations are based on real work, not just budget and team size."
                ),
                "options": _work_profile_options(preferences),
            }
        )
    elif "application_profile" in missing_set:
        sections.append(
            {
                "title": "Narrow Down The App Mix",
                "description": (
                    "Pick the closest tool profile so the system can size RAM, storage, and performance more accurately."
                ),
                "options": _application_profile_options(preferences),
            }
        )

    refinement_options = _refinement_options(readiness, preferences)
    if refinement_options:
        sections.append(
            {
                "title": "Tune The Recommendation",
                "description": "You can also steer the recommendations toward cost, performance, growth, support, or availability.",
                "options": refinement_options,
            }
        )

    return sections


def _work_profile_options(preferences):
    category = str(preferences.get("preferred_category") or "").strip().lower()
    if category == "networking":
        return [
            {"label": "Branch connectivity", "message": "This is mainly for branch connectivity, VPN, firewall, and secure office networking."},
            {"label": "Office switching", "message": "This is mainly for office switching, PoE access, VLANs, and internal connectivity."},
            {"label": "Wi-Fi coverage", "message": "This is mainly for Wi-Fi coverage, wireless clients, and office access points."},
            {"label": "Mixed network", "message": "This is a mixed network setup with branch connectivity, switching, and Wi-Fi needs."},
        ]
    if category == "servers":
        return [
            {"label": "Virtualization", "message": "This is mainly for virtualization with VMware, Hyper-V, or Proxmox."},
            {"label": "Business apps", "message": "This is mainly for line-of-business applications, shared services, and office systems."},
            {"label": "AI or analytics", "message": "This is mainly for AI, analytics, or heavier local compute workloads."},
            {"label": "Always-on infra", "message": "This is an always-on server environment where uptime and support matter."},
        ]
    return [
        {"label": "Office apps", "message": "They mainly use Excel, browser tools, email, meetings, and billing software."},
        {"label": "Software development", "message": "They mainly use VS Code, Docker, browser tools, and local databases."},
        {"label": "Design and creative", "message": "They mainly use Figma, Photoshop, Illustrator, and creative design tools."},
        {"label": "Video or media", "message": "They mainly use Premiere Pro, DaVinci Resolve, and large media files."},
        {"label": "Mixed business use", "message": "It is a mixed-use team with browser apps, documents, meetings, and light multitasking."},
    ]


def _application_profile_options(preferences):
    workloads = set(preferences.get("workload_types") or preferences.get("workloads") or [])
    if "software_development" in workloads:
        return [
            {"label": "Backend dev", "message": "They mainly use VS Code, Docker, containers, and local databases."},
            {"label": "Full-stack web", "message": "They mainly use VS Code, browser dev tools, local services, and some Docker."},
            {"label": "Cloud or remote dev", "message": "They mainly code in editors with browser tools and use cloud or remote environments."},
            {"label": "AI dev mix", "message": "They use Python tooling, local models, notebooks, and heavier local compute."},
        ]
    if "creative_design" in workloads:
        return [
            {"label": "Figma and Adobe", "message": "They mainly use Figma, Photoshop, Illustrator, and design assets."},
            {"label": "Video editing", "message": "They mainly use Premiere Pro, After Effects, DaVinci Resolve, and large media files."},
            {"label": "CAD or 3D", "message": "They mainly use AutoCAD, Revit, SolidWorks, or other 3D design tools."},
        ]
    if "server_infrastructure" in workloads:
        return [
            {"label": "Virtualization stack", "message": "This is mainly for VMware, Hyper-V, or Proxmox virtualization workloads."},
            {"label": "Business server", "message": "This is mainly for shared office apps, file services, and business workloads."},
            {"label": "Uptime critical", "message": "This is an always-on server setup where uptime, support, and resilience matter most."},
        ]
    if "ai_analytics" in workloads:
        return [
            {"label": "Analytics and notebooks", "message": "They mainly use notebooks, Python tools, analytics workflows, and local data processing."},
            {"label": "Local model work", "message": "They mainly use local models, PyTorch or TensorFlow, and heavier compute tasks."},
            {"label": "Mixed AI team", "message": "It is a mixed analytics and AI workflow with notebooks, Python tooling, and some model work."},
        ]
    return [
        {"label": "General office tools", "message": "They mainly use Excel, browser tools, email, and common office applications."},
        {"label": "Developer tools", "message": "They mainly use VS Code, Docker, browser tools, and local services."},
        {"label": "Creative tools", "message": "They mainly use Figma, Photoshop, Illustrator, or media applications."},
    ]


def _refinement_options(readiness, preferences):
    readiness = dict(readiness or {})
    if not readiness.get("is_ready"):
        return []

    missing_set = set(readiness.get("missing_signals") or [])
    options = []
    if "performance_priority" in missing_set:
        options.extend(
            [
                {"label": "Lower cost", "message": "Optimize more for cost than maximum performance."},
                {"label": "Balanced", "message": "Keep the recommendation balanced."},
                {"label": "More performance", "message": "Optimize more for stronger performance."},
            ]
        )
    if "growth_expectation" in missing_set:
        options.extend(
            [
                {"label": "Steady team", "message": "Plan for a steady team with no major growth right now."},
                {"label": "Moderate growth", "message": "Plan for moderate growth over the next year."},
                {"label": "Rapid growth", "message": "Plan for rapid growth and extra headroom."},
            ]
        )
    if "support_expectation" in missing_set:
        options.append({"label": "Better support", "message": "Business or premium support matters for this purchase."})
    if "availability_need" in missing_set:
        options.append({"label": "Need it fast", "message": "Immediate or near-term availability matters for this purchase."})

    unique = []
    seen_labels = set()
    for option in options:
        label = option["label"]
        if label in seen_labels:
            continue
        seen_labels.add(label)
        unique.append(option)
    return unique

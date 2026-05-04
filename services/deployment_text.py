def build_deployment_phrase(requirements, categories, seat_based_categories=None):
    requirements = requirements or {}
    category_set = set(categories or [])
    explicit_quantity = requirements.get("quantity")
    team_size = requirements.get("team_size")
    seat_based_categories = set(seat_based_categories or [])

    if not category_set:
        if team_size:
            return f"for about {team_size} planned users"
        return "for an unresolved deployment scope"

    if category_set.intersection(seat_based_categories):
        count = explicit_quantity or team_size or 1
        return f"for {count} seats"

    if "networking" in category_set:
        if team_size:
            return f"supporting about {team_size} users/endpoints"
        if explicit_quantity:
            unit_label = "infrastructure units" if explicit_quantity != 1 else "infrastructure unit"
            return f"for {explicit_quantity} planned {unit_label}"
        return "for a single reference network deployment"

    if "servers" in category_set:
        if team_size:
            return f"supporting about {team_size} users/workloads"
        if explicit_quantity:
            unit_label = "server units" if explicit_quantity != 1 else "server unit"
            return f"for {explicit_quantity} planned {unit_label}"
        return "for a single reference server environment"

    if "printers" in category_set:
        if explicit_quantity:
            unit_label = "printer units" if explicit_quantity != 1 else "printer unit"
            return f"for {explicit_quantity} planned {unit_label}"
        if team_size:
            return f"serving about {team_size} users"
        return "for a single reference print deployment"

    if "accessories" in category_set:
        count = explicit_quantity or team_size or 1
        return f"for {count} planned peripherals"

    count = explicit_quantity or team_size or 1
    return f"for {count} users"

def normalize_optional_bool(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value

    lowered = str(value).strip().lower()
    if lowered in {"true", "1", "yes", "required", "must"}:
        return True
    if lowered in {"false", "0", "no", "not required"}:
        return False
    return None


def normalize_availability_need(value):
    lowered = str(value or "").strip().lower()
    if not lowered:
        return None
    if lowered in {"in_stock_now", "in stock now", "available now", "ready stock"}:
        return "in_stock_now"
    if lowered in {"urgent", "asap", "immediately"}:
        return "urgent"
    if lowered in {"soon", "this week", "next week", "this month"}:
        return "soon"
    if lowered in {"standard", "normal"}:
        return "standard"
    return None


def normalize_rollout_type(value):
    lowered = str(value or "").strip().lower()
    if not lowered:
        return None
    if lowered in {"phased", "phased_rollout", "phased rollout", "phase 1", "phase one", "staggered"}:
        return "phased"
    if lowered in {"standard", "single_phase", "single phase", "full", "full rollout"}:
        return "standard"
    return None


def normalize_replacement_mode(value):
    lowered = str(value or "").strip().lower()
    if not lowered:
        return None
    if lowered in {"refresh", "replacement", "replace", "upgrade", "upgrade_existing"}:
        return "refresh"
    if lowered in {"net_new", "net new", "new_setup", "new setup", "new_purchase"}:
        return "net_new"
    return None


def normalize_purchase_scope(value, preferred_categories=None, quantity=None, team_size=None, hint_text=""):
    lowered = str(value or "").strip().lower()
    if lowered:
        if lowered in {"single", "single_unit", "single unit", "one device", "one unit"}:
            return "single_unit"
        if lowered in {"rollout", "team_rollout", "team rollout", "device rollout"}:
            return "team_rollout"
        if lowered in {"deployment", "site_deployment", "site deployment", "infrastructure deployment"}:
            return "site_deployment"

    categories = {
        str(category or "").strip().lower()
        for category in list(preferred_categories or [])
        if str(category or "").strip()
    }
    hint_text = str(hint_text or "").strip().lower()
    quantity = int(quantity or 0)
    team_size = int(team_size or 0)
    is_end_user_category = bool(categories.intersection({"laptops", "desktops", "accessories"}))

    if quantity == 1:
        return "single_unit"
    if quantity > 1:
        return "team_rollout" if is_end_user_category else "site_deployment"

    if any(token in hint_text for token in {"single laptop", "single desktop", "one laptop", "one desktop", "one device", "single unit"}):
        return "single_unit"
    if any(token in hint_text for token in {"rollout", "refresh", "for the team", "for all staff", "for all employees"}):
        return "team_rollout" if is_end_user_category else "site_deployment"

    if team_size > 1 and any(token in hint_text for token in {"staff", "employees", "developers", "designers", "users", "seats"}):
        return "team_rollout" if is_end_user_category else "site_deployment"
    if team_size > 1 and is_end_user_category:
        return "team_rollout"
    return None

import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from uuid import uuid4

import requests

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover
    st = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "service_project.settings")

import django

django.setup()

from ai_configurator.procurement.models import ProcurementExpertReviewRequest, ProcurementSession
from ai_configurator.procurement.serializers import (
    ProcurementConfigPublishRequestSerializer,
    ProcurementExpertReviewRequestSerializer,
    ProcurementRequestSerializer,
    build_guided_intake_schema,
)
from ai_configurator.procurement.services.clarification import ProcurementClarificationService
from ai_configurator.procurement.services.config_governance import ProcurementConfigGovernanceService
from ai_configurator.procurement.services.feature_flags import ProcurementFeatureFlagService
from ai_configurator.procurement.services.intake import RequirementIntakeService
from ai_configurator.procurement.services.observability import ProcurementRuntimeObservabilityService
from ai_configurator.procurement.services.recommendation_service import ProcurementRecommendationService
from ai_configurator.procurement.services.review_support import ProcurementReviewSupportService
from ai_configurator.procurement.services.rules_engine import ProcurementRulesEngine
from ai_configurator.procurement.services.template_service import ProcurementTemplateService
from test_support.catalog_dataset import build_catalog_repository, resolve_catalog_size


DEFAULT_HTTP_BASE = "http://127.0.0.1:8000"
EMPTY_VALUES = ("", None, [], {})
CONFIG_ASSETS = ["rules", "ranking", "policy", "templates"]
PROPOSAL_SOURCES = ["engineering", "business_ops", "platform_ops"]
REVIEW_MODES = ["not_set", "accept", "continue_editing"]
CATALOG_SIZE_OPTIONS = ["small", "large", "corrected_json", "mongo"]


def require_streamlit() -> None:
    if st is not None:
        return
    raise SystemExit(
        "Install Streamlit and run:\n\n"
        "  pip install streamlit requests\n"
        "  streamlit run ai_configurator_service/scripts/streamlit_chat_tester_final_v1.py\n"
    )


def normalize_http_base(value: str) -> str:
    return str(value or "").rstrip("/")


def safe_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"status_code": response.status_code, "text": response.text}


def humanize(value: Any) -> str:
    text = str(value or "").strip().replace("_", " ")
    return text.title() if text else "-"


def split_text_list(raw_value: Any) -> List[str]:
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    text = str(raw_value or "").replace("\n", ",")
    return [item.strip() for item in text.split(",") if item.strip()]


def parse_int_or_none(raw_value: Any) -> Optional[int]:
    text = str(raw_value or "").strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def set_error(message: str) -> None:
    st.session_state.last_error = str(message or "").strip()
    st.session_state.last_success = ""


def set_success(message: str) -> None:
    st.session_state.last_success = str(message or "").strip()
    st.session_state.last_error = ""


def init_state() -> None:
    defaults = {
        "http_base": DEFAULT_HTTP_BASE,
        "user_id": "",
        "business_id": "",
        "default_currency": "INR",
        "publish_token": "",
        "catalog_size": "corrected_json",
        "payload_chat_text": "",
        "payload_store_id": "",
        "payload_overrides_json": "{}",
        "schema_data": None,
        "schema_loaded_once": False,
        "assessment_result": None,
        "recommendation_result": None,
        "session_result": None,
        "expert_review_result": None,
        "observability_result": None,
        "history_result": None,
        "publish_result": None,
        "rollback_result": None,
        "session_lookup_id": "",
        "review_mode": "not_set",
        "persist_recommendation": True,
        "expert_review_reason": "manual_review",
        "expert_review_notes": "",
        "observability_limit": 50,
        "config_limit": 10,
        "publish_asset_types": [],
        "rollback_asset_types": [],
        "publish_proposal_source": "engineering",
        "rollback_proposal_source": "engineering",
        "publish_reason": "",
        "publish_notes": "",
        "rollback_reason": "",
        "rollback_notes": "",
        "publish_execute_request_id": "",
        "rollback_execute_request_id": "",
        "last_error": "",
        "last_success": "",
        "direct_service_signature": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def api_headers(include_publish_token: bool = False) -> Dict[str, str]:
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if st.session_state.user_id.strip():
        headers["X-User-Id"] = st.session_state.user_id.strip()
    if st.session_state.business_id.strip():
        headers["X-Business-Id"] = st.session_state.business_id.strip()
    if st.session_state.default_currency.strip():
        headers["X-Default-Currency"] = st.session_state.default_currency.strip()
    if include_publish_token and st.session_state.publish_token.strip():
        headers["X-Procurement-Config-Publish-Token"] = st.session_state.publish_token.strip()
    return headers


def call_api(
    method: str,
    path: str,
    json_body: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 60,
    include_publish_token: bool = False,
    success_message: str = "",
) -> Tuple[bool, Any]:
    base = normalize_http_base(st.session_state.http_base)
    if not base:
        set_error("HTTP base URL is required.")
        return False, None

    try:
        response = requests.request(
            method=method.upper(),
            url=f"{base}{path}",
            headers=api_headers(include_publish_token=include_publish_token),
            json=json_body,
            params=params,
            timeout=timeout,
        )
    except Exception as exc:  # pragma: no cover
        set_error(f"{method.upper()} {path} failed: {exc}")
        return False, None

    data = safe_json(response)
    if response.ok:
        if success_message:
            set_success(success_message)
        else:
            st.session_state.last_error = ""
        return True, data

    set_error(f"{method.upper()} {path} returned {response.status_code}: {json.dumps(data, ensure_ascii=False)}")
    return False, data


def schema_fields() -> List[Dict[str, Any]]:
    return list((st.session_state.schema_data or {}).get("fields") or [])


def schema_widget_key(field_key: str) -> str:
    return f"payload_field__{field_key}"


def review_widget_key(field_key: str) -> str:
    return f"review_field__{field_key}"


def ensure_schema_defaults() -> None:
    for field in schema_fields():
        widget_key = schema_widget_key(field["key"])
        if widget_key in st.session_state:
            continue
        field_type = str(field.get("type") or "")
        if field_type == "multi_select":
            st.session_state[widget_key] = []
        else:
            st.session_state[widget_key] = ""


def clear_review_edit_state() -> None:
    editable = ((st.session_state.assessment_result or {}).get("editable_inferred_values") or {})
    for field_key in editable:
        widget_key = review_widget_key(field_key)
        if widget_key in st.session_state:
            del st.session_state[widget_key]


def build_direct_context(catalog_size: str) -> Dict[str, Any]:
    recommendation_service = ProcurementRecommendationService(
        catalog_repository=build_catalog_repository(resolve_catalog_size(catalog_size))
    )
    if os.getenv("VALIDATION_DISABLE_EXPLANATION_LLM", "").strip().lower() == "true":
        recommendation_service.explanation_service.llm_client.provider = "groq"
        recommendation_service.explanation_service.llm_client.api_key = ""
    return {
        "recommendation_service": recommendation_service,
        "intake_service": RequirementIntakeService(),
        "rules_engine": ProcurementRulesEngine(),
        "clarification_service": ProcurementClarificationService(),
        "feature_flag_service": ProcurementFeatureFlagService(),
        "template_service": ProcurementTemplateService(),
        "review_support_service": ProcurementReviewSupportService(),
        "observability_service": ProcurementRuntimeObservabilityService(),
        "config_governance_service": ProcurementConfigGovernanceService(),
    }


def get_direct_context() -> Dict[str, Any]:
    signature = str(st.session_state.catalog_size or "corrected_json").strip().lower() or "corrected_json"
    if signature not in CATALOG_SIZE_OPTIONS:
        signature = "corrected_json"
        st.session_state.catalog_size = signature
    if st.session_state.get("direct_service_signature") != signature or "direct_context" not in st.session_state:
        st.session_state.direct_context = build_direct_context(signature)
        st.session_state.direct_service_signature = signature
    return st.session_state.direct_context


def validate_procurement_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    serializer = ProcurementRequestSerializer(data=payload)
    if not serializer.is_valid():
        raise ValueError(json.dumps(serializer.errors, ensure_ascii=False))
    return dict(serializer.validated_data)


def refresh_schema() -> None:
    st.session_state.schema_loaded_once = True
    st.session_state.schema_data = build_guided_intake_schema()
    ensure_schema_defaults()
    set_success("Procurement intake schema refreshed from direct service config.")


def parse_payload_overrides() -> Dict[str, Any]:
    raw = str(st.session_state.payload_overrides_json or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Payload overrides JSON is invalid: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Payload overrides JSON must be an object.")
    return parsed


def normalize_schema_value(field: Dict[str, Any], raw_value: Any) -> Any:
    field_type = str(field.get("type") or "")
    if field_type == "single_select":
        value = str(raw_value or "").strip()
        return None if value in {"", "not_sure"} else value
    if field_type == "multi_select":
        values = [str(item).strip() for item in list(raw_value or []) if str(item).strip()]
        return values or None
    if field_type == "number":
        return parse_int_or_none(raw_value)
    if field_type == "boolean":
        lowered = str(raw_value or "").strip().lower()
        if lowered == "yes":
            return True
        if lowered == "no":
            return False
        return None
    if field_type == "list":
        values = split_text_list(raw_value)
        return values or None
    value = str(raw_value or "").strip()
    return value or None


def build_payload(include_review: bool = True, include_persist: bool = False) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"channel": "streamlit_procurement_tester_final_v1"}
    if st.session_state.payload_chat_text.strip():
        payload["chat_text"] = st.session_state.payload_chat_text.strip()
    if st.session_state.payload_store_id.strip():
        payload["store_id"] = st.session_state.payload_store_id.strip()
    if st.session_state.default_currency.strip():
        payload["currency"] = st.session_state.default_currency.strip()

    for field in schema_fields():
        raw_value = st.session_state.get(schema_widget_key(field["key"]))
        normalized = normalize_schema_value(field, raw_value)
        if normalized in EMPTY_VALUES:
            continue
        payload_key = "category" if field["key"] == "preferred_category" else field["key"]
        payload[payload_key] = normalized

    overrides = parse_payload_overrides()
    payload.update(overrides)

    if include_review:
        edited = collect_review_edits()
        if edited:
            payload["edited_inferred_values"] = edited
        if st.session_state.review_mode == "accept":
            payload["review_acceptance"] = True
        elif st.session_state.review_mode == "continue_editing":
            payload["review_acceptance"] = False

    if include_persist:
        payload["persist"] = bool(st.session_state.persist_recommendation)

    return payload


def collect_review_edits() -> Dict[str, Any]:
    editable = ((st.session_state.assessment_result or {}).get("editable_inferred_values") or {})
    edits: Dict[str, Any] = {}
    for field_key, meta in editable.items():
        widget_key = review_widget_key(field_key)
        if widget_key not in st.session_state:
            continue
        raw = st.session_state.get(widget_key)
        current = meta.get("value")
        if isinstance(current, list):
            value = split_text_list(raw)
        elif isinstance(current, bool):
            lowered = str(raw or "").strip().lower()
            value = True if lowered == "yes" else False if lowered == "no" else None
        elif isinstance(current, int):
            value = parse_int_or_none(raw)
        else:
            value = str(raw or "").strip() or None
        if value in EMPTY_VALUES:
            continue
        edits[field_key] = value
    return edits


def run_assessment() -> None:
    payload = build_payload(include_review=False)
    validated = validate_procurement_payload(payload)
    context = get_direct_context()
    requirements = context["intake_service"].normalize(validated)
    target_profile = context["rules_engine"].build_target_profile(requirements)
    readiness = context["clarification_service"].assess(requirements)
    template_candidates = context["template_service"].select_candidates(requirements, target_profile)
    requirements["review_state"] = context["review_support_service"].enrich_review_state(
        requirements=requirements,
        readiness=readiness,
        template_candidates=template_candidates,
    )
    st.session_state.assessment_result = {
        "requirements": requirements,
        "target_profile_preview": target_profile,
        "readiness": readiness,
        "review_state": requirements.get("review_state") or {},
        "check_requirement_summary": context["review_support_service"].build_check_requirement_summary(
            requirements=requirements,
            readiness=readiness,
            template_candidates=template_candidates,
        ),
        "editable_inferred_values": context["review_support_service"].build_editable_inferred_values(requirements),
        "template_candidates": template_candidates,
    }
    clear_review_edit_state()
    set_success("Assessment completed directly through procurement services.")


def run_recommendation() -> None:
    payload = build_payload(include_review=True, include_persist=True)
    validated = validate_procurement_payload(payload)
    persist = bool(validated.pop("persist", True))
    context = get_direct_context()
    result = context["recommendation_service"].recommend(
        validated,
        user_id=str(st.session_state.user_id or "").strip(),
        business_id=str(st.session_state.business_id or "").strip(),
        persist=persist,
    )
    st.session_state.recommendation_result = result
    st.session_state.session_lookup_id = str(result.get("session_id") or st.session_state.session_lookup_id or "")
    set_success("Recommendation completed directly through procurement services.")


def load_session() -> None:
    session_id = str(st.session_state.session_lookup_id or "").strip()
    if not session_id:
        set_error("Enter a session id first.")
        return
    session = ProcurementSession.objects.filter(session_id=session_id).first()
    if not session:
        set_error("Unknown session id.")
        return
    st.session_state.session_result = {
        "session_id": session.session_id,
        "status": session.status,
        "channel": session.channel,
        "currency": session.currency,
        "raw_intake_snapshot": session.raw_intake_snapshot,
        "requirements": session.requirements,
        "target_profile": session.target_profile,
        "recommendations": session.recommendations,
        "summary": session.summary,
        "assumptions": session.assumptions,
        "meta": session.meta,
        "engine_version": session.engine_version,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
    }
    set_success("Session loaded directly from persisted procurement data.")


def submit_expert_review() -> None:
    source = st.session_state.recommendation_result or st.session_state.session_result or {}
    body = {
        "session_id": str(source.get("session_id") or st.session_state.session_lookup_id or "").strip(),
        "decision_trace_id": str(source.get("decision_trace_id") or "").strip(),
        "reason": str(st.session_state.expert_review_reason or "").strip(),
        "notes": str(st.session_state.expert_review_notes or "").strip(),
    }
    context = get_direct_context()
    if not context["feature_flag_service"].is_enabled("expert_review"):
        set_error("Expert review is currently disabled by feature flag.")
        return
    serializer = ProcurementExpertReviewRequestSerializer(data=body)
    if not serializer.is_valid():
        raise ValueError(json.dumps(serializer.errors, ensure_ascii=False))
    validated = dict(serializer.validated_data)
    review_request = ProcurementExpertReviewRequest.objects.create(
        request_id=str(uuid4()),
        session_id=str(validated.get("session_id") or "").strip(),
        decision_trace_id=str(validated.get("decision_trace_id") or "").strip(),
        user_id=str(st.session_state.user_id or "").strip(),
        business_id=str(st.session_state.business_id or "").strip(),
        reason=str(validated.get("reason") or "").strip(),
        notes=str(validated.get("notes") or "").strip(),
        meta={"source": "streamlit_direct_service_tester"},
    )
    st.session_state.expert_review_result = {
        "request_id": review_request.request_id,
        "session_id": review_request.session_id,
        "decision_trace_id": review_request.decision_trace_id,
        "reason": review_request.reason,
        "status": review_request.status,
        "notes": review_request.notes,
        "created_at": review_request.created_at,
    }
    set_success("Expert review request created through the direct procurement path.")


def refresh_observability() -> None:
    context = get_direct_context()
    st.session_state.observability_result = context["observability_service"].summarize_recent_runs(
        limit=st.session_state.observability_limit
    )
    set_success("Observability summary refreshed directly through procurement services.")


def refresh_config(kind: str) -> None:
    context = get_direct_context()
    governance = context["config_governance_service"]
    if kind == "history":
        st.session_state.history_result = governance.get_publish_summary(history_limit=st.session_state.config_limit)
    elif kind == "publish":
        st.session_state.publish_result = governance.get_publish_workflow_summary(
            history_limit=st.session_state.config_limit,
            pending_limit=st.session_state.config_limit,
        )
    else:
        st.session_state.rollback_result = governance.get_rollback_workflow_summary(
            history_limit=st.session_state.config_limit,
            pending_limit=st.session_state.config_limit,
        )
    set_success(f"{humanize(kind)} data refreshed directly through governance services.")


def create_config_request(kind: str) -> None:
    body = {
        "asset_types": list(st.session_state.get(f"{kind}_asset_types") or []),
        "proposal_source": str(st.session_state.get(f"{kind}_proposal_source") or "engineering"),
        "reason": str(st.session_state.get(f"{kind}_reason") or "").strip(),
        "notes": str(st.session_state.get(f"{kind}_notes") or "").strip(),
    }
    serializer = ProcurementConfigPublishRequestSerializer(data=body)
    if not serializer.is_valid():
        raise ValueError(json.dumps(serializer.errors, ensure_ascii=False))
    validated = dict(serializer.validated_data)
    governance = get_direct_context()["config_governance_service"]
    if kind == "publish":
        governance.create_publish_request(
            asset_types=validated.get("asset_types"),
            requested_by=str(st.session_state.user_id or "").strip(),
            proposal_source=str(validated.get("proposal_source") or "engineering").strip(),
            reason=str(validated.get("reason") or "").strip(),
            notes=str(validated.get("notes") or "").strip(),
        )
    else:
        governance.create_rollback_request(
            asset_types=validated.get("asset_types"),
            requested_by=str(st.session_state.user_id or "").strip(),
            proposal_source=str(validated.get("proposal_source") or "engineering").strip(),
            reason=str(validated.get("reason") or "").strip(),
            notes=str(validated.get("notes") or "").strip(),
        )
    refresh_config(kind)
    refresh_config("history")
    set_success(f"{humanize(kind)} request created directly through governance services.")


def execute_config_request(kind: str) -> None:
    request_id = str(st.session_state.get(f"{kind}_execute_request_id") or "").strip()
    if not request_id:
        set_error(f"Enter the {kind} request id first.")
        return
    governance = get_direct_context()["config_governance_service"]
    if kind == "publish":
        governance.execute_publish_request(
            request_id=request_id,
            authorization_token=str(st.session_state.publish_token or "").strip(),
            executed_by=str(st.session_state.user_id or "").strip(),
        )
    else:
        governance.execute_rollback_request(
            request_id=request_id,
            authorization_token=str(st.session_state.publish_token or "").strip(),
            executed_by=str(st.session_state.user_id or "").strip(),
        )
    refresh_config("publish")
    refresh_config("rollback")
    refresh_config("history")
    set_success(f"{humanize(kind)} request executed directly through governance services.")


def render_schema_field(field: Dict[str, Any]) -> None:
    label = str(field.get("label") or field["key"])
    widget_key = schema_widget_key(field["key"])
    field_type = str(field.get("type") or "")
    if field_type == "single_select":
        options = [""] + list(field.get("options") or [])
        current = st.session_state.get(widget_key, "")
        selected_index = options.index(current) if current in options else 0
        st.selectbox(label, options=options, index=selected_index, key=widget_key, format_func=humanize)
    elif field_type == "multi_select":
        st.multiselect(label, options=list(field.get("options") or []), key=widget_key, format_func=humanize)
    elif field_type == "number":
        st.text_input(label, key=widget_key, placeholder="Enter a whole number")
    elif field_type == "boolean":
        options = ["", "yes", "no"]
        current = st.session_state.get(widget_key, "")
        selected_index = options.index(current) if current in options else 0
        st.selectbox(label, options=options, index=selected_index, key=widget_key, format_func=humanize)
    elif field_type == "list":
        st.text_area(label, key=widget_key, placeholder="Comma separated or one per line")
    else:
        st.text_input(label, key=widget_key)


def render_review_editor(field_key: str, meta: Dict[str, Any]) -> None:
    widget_key = review_widget_key(field_key)
    label = str(meta.get("label") or humanize(field_key))
    value = meta.get("value")
    if isinstance(value, bool):
        options = ["", "yes", "no"]
        current = st.session_state.get(widget_key, "yes" if value else "no")
        selected_index = options.index(current) if current in options else 0
        st.selectbox(f"{label} (edit)", options=options, index=selected_index, key=widget_key, format_func=humanize)
    elif isinstance(value, list):
        st.text_area(f"{label} (edit)", key=widget_key, value=", ".join(str(item) for item in value))
    else:
        st.text_input(f"{label} (edit)", key=widget_key, value="" if value is None else str(value))


def render_recommendations(result: Dict[str, Any]) -> None:
    recommendations = list(result.get("recommendations") or [])
    groups = list(result.get("recommendation_groups") or [])
    if not recommendations and not groups:
        st.info("No recommendations returned.")
        return
    for index, item in enumerate(recommendations, start=1):
        with st.expander(f"{index}. {item.get('name') or 'Recommendation'}", expanded=index == 1):
            st.json(item)
    for group in groups:
        with st.expander(f"Group: {group.get('label') or group.get('group_id') or 'Recommendation Group'}"):
            st.json(group)


def render_top_messages() -> None:
    if st.session_state.last_error:
        st.error(st.session_state.last_error)
    elif st.session_state.last_success:
        st.success(st.session_state.last_success)


def render_sidebar() -> None:
    with st.sidebar:
        st.header("Tester Mode")
        st.selectbox("Catalog size", options=CATALOG_SIZE_OPTIONS, key="catalog_size")
        st.caption(
            "Use `corrected_json` for the INR fixture catalog, `mongo` for the live MongoDB catalog "
            "(via `CATALOG_MONGODB_URI` + `CATALOG_DB_NAME`), or the legacy fake datasets for regression checks."
        )
        st.text_input("HTTP base URL", key="http_base")
        st.text_input("X-User-Id", key="user_id")
        st.text_input("X-Business-Id", key="business_id")
        st.text_input("X-Default-Currency", key="default_currency")
        st.text_input("Publish Token", key="publish_token", type="password")
        if st.button("Refresh Intake Schema", use_container_width=True):
            refresh_schema()


def render_builder_tab() -> None:
    st.subheader("Payload Builder")
    st.caption("This tab verifies procurement services directly. It does not depend on REST or WebSocket transport.")
    if not st.session_state.schema_data:
        st.info("Load the backend schema first.")
    else:
        st.caption(f"Schema version: {st.session_state.schema_data.get('schema_version') or '-'}")
    st.text_area("Chat text", key="payload_chat_text", height=120)
    st.text_input("Store id (ignored for recommendations)", key="payload_store_id")

    ensure_schema_defaults()
    fields = schema_fields()
    columns = st.columns(2)
    for index, field in enumerate(fields):
        with columns[index % 2]:
            render_schema_field(field)

    st.text_area(
        "Payload overrides JSON",
        key="payload_overrides_json",
        height=160,
        help="Use this to pass newly added procurement fields without waiting for the Streamlit form to catch up.",
    )
    with st.expander("Current request payload preview", expanded=False):
        try:
            st.json(build_payload(include_review=True, include_persist=True))
        except ValueError as exc:
            st.error(str(exc))
    with st.expander("Raw schema JSON", expanded=False):
        st.json(st.session_state.schema_data or {})


def render_assessment_tab() -> None:
    st.subheader("Intake Assessment")
    if st.button("Run Direct Intake Assessment", type="primary"):
        try:
            run_assessment()
        except ValueError as exc:
            set_error(str(exc))
    result = st.session_state.assessment_result or {}
    if not result:
        st.info("Run the assessment to inspect readiness, inferred values, and review state.")
        return
    readiness = dict(result.get("readiness") or {})
    st.json(
        {
            "readiness": readiness,
            "review_state": result.get("review_state") or {},
            "check_requirement_summary": result.get("check_requirement_summary") or {},
            "template_candidates": result.get("template_candidates") or [],
        }
    )
    editable = dict(result.get("editable_inferred_values") or {})
    if editable:
        st.markdown("#### Editable inferred values")
        for field_key, meta in editable.items():
            render_review_editor(field_key, meta)
        selected_index = REVIEW_MODES.index(st.session_state.review_mode)
        st.selectbox(
            "Review mode",
            options=REVIEW_MODES,
            index=selected_index,
            key="review_mode",
            format_func=lambda value: {
                "not_set": "Do not send review acceptance yet",
                "accept": "Send review_acceptance = true",
                "continue_editing": "Send review_acceptance = false",
            }[value],
        )


def render_recommend_tab() -> None:
    st.subheader("Recommendation")
    st.checkbox("Persist recommendation", key="persist_recommendation")
    if st.button("Run Direct Recommendation", type="primary"):
        try:
            run_recommendation()
        except ValueError as exc:
            set_error(str(exc))
    result = st.session_state.recommendation_result or {}
    if not result:
        st.info("Run the recommendation endpoint to inspect the persisted procurement result.")
        return
    st.json(
        {
            "session_id": result.get("session_id"),
            "decision_trace_id": result.get("decision_trace_id"),
            "recommendation_mode": result.get("recommendation_mode"),
            "expert_review_eligible": result.get("expert_review_eligible"),
            "summary": result.get("summary"),
            "next_question": result.get("next_question"),
            "fallback_reason": result.get("fallback_reason"),
        }
    )
    render_recommendations(result)
    with st.expander("Full recommendation JSON", expanded=False):
        st.json(result)


def render_session_review_tab() -> None:
    st.subheader("Session And Expert Review")
    st.text_input("Session id", key="session_lookup_id")
    if st.button("Load Persisted Session"):
        load_session()
    if st.session_state.session_result:
        with st.expander("Loaded session JSON", expanded=False):
            st.json(st.session_state.session_result)

    st.markdown("#### Expert review")
    st.text_input("Reason", key="expert_review_reason")
    st.text_area("Notes", key="expert_review_notes", height=120)
    if st.button("Submit Expert Review", type="primary"):
        try:
            submit_expert_review()
        except ValueError as exc:
            set_error(str(exc))
    if st.session_state.expert_review_result:
        st.json(st.session_state.expert_review_result)


def render_observability_tab() -> None:
    st.subheader("Observability")
    st.number_input("Recent run limit", min_value=1, step=1, key="observability_limit")
    if st.button("Refresh Direct Observability"):
        refresh_observability()
    if st.session_state.observability_result:
        st.json(st.session_state.observability_result)


def render_config_tab() -> None:
    st.subheader("Config Governance")
    st.number_input("History and pending limit", min_value=1, step=1, key="config_limit")
    action_cols = st.columns(3)
    if action_cols[0].button("Refresh History"):
        refresh_config("history")
    if action_cols[1].button("Refresh Publish"):
        refresh_config("publish")
    if action_cols[2].button("Refresh Rollback"):
        refresh_config("rollback")

    tabs = st.tabs(["Publish", "Rollback", "History"])
    with tabs[0]:
        st.multiselect("Assets", options=CONFIG_ASSETS, key="publish_asset_types")
        st.selectbox("Proposal source", options=PROPOSAL_SOURCES, key="publish_proposal_source")
        st.text_input("Reason", key="publish_reason")
        st.text_area("Notes", key="publish_notes", height=100)
        if st.button("Create publish request"):
            try:
                create_config_request("publish")
            except ValueError as exc:
                set_error(str(exc))
        st.text_input("Publish request id to execute", key="publish_execute_request_id")
        if st.button("Execute publish request"):
            try:
                execute_config_request("publish")
            except (ValueError, PermissionError) as exc:
                set_error(str(exc))
        st.json(st.session_state.publish_result or {})
    with tabs[1]:
        st.multiselect("Assets", options=CONFIG_ASSETS, key="rollback_asset_types")
        st.selectbox("Proposal source", options=PROPOSAL_SOURCES, key="rollback_proposal_source")
        st.text_input("Reason", key="rollback_reason")
        st.text_area("Notes", key="rollback_notes", height=100)
        if st.button("Create rollback request"):
            try:
                create_config_request("rollback")
            except ValueError as exc:
                set_error(str(exc))
        st.text_input("Rollback request id to execute", key="rollback_execute_request_id")
        if st.button("Execute rollback request"):
            try:
                execute_config_request("rollback")
            except (ValueError, PermissionError) as exc:
                set_error(str(exc))
        st.json(st.session_state.rollback_result or {})
    with tabs[2]:
        st.json(st.session_state.history_result or {})


def main() -> None:
    require_streamlit()
    init_state()
    st.set_page_config(page_title="Procurement Tester Final v1", layout="wide")
    st.title("Procurement Tester Final v1")
    st.caption(
        "Direct procurement-service verification app for the current backend. This version does not use REST or WebSocket for the main validation path."
    )
    render_sidebar()
    render_top_messages()

    tabs = st.tabs(
        [
            "1. Payload Builder",
            "2. Assess",
            "3. Recommend",
            "4. Session And Review",
            "5. Observability",
            "6. Config Governance",
        ]
    )
    with tabs[0]:
        render_builder_tab()
    with tabs[1]:
        render_assessment_tab()
    with tabs[2]:
        render_recommend_tab()
    with tabs[3]:
        render_session_review_tab()
    with tabs[4]:
        render_observability_tab()
    with tabs[5]:
        render_config_tab()


if __name__ == "__main__":
    main()

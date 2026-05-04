import json
import sys
from typing import Any, Dict, Optional

import requests

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover
    st = None

try:
    import websocket  # websocket-client
except ImportError:  # pragma: no cover
    websocket = None


DEFAULT_HTTP_BASE = "http://127.0.0.1:8000"
DEFAULT_WS_URL = "ws://127.0.0.1:8000/ws/sales-bot/"


def normalize_http_base(value: str) -> str:
    return str(value or "").rstrip("/")


def latest_user_brief_from_transcript(chat_transcript: Any) -> str:
    if not isinstance(chat_transcript, list):
        return ""
    user_messages = []
    for message in chat_transcript:
        if isinstance(message, dict) and message.get("role") == "user":
            content = str(message.get("content") or "").strip()
            if content:
                user_messages.append(content)
    return "\n".join(user_messages).strip()


def extract_response_text(payload: Dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("response") or payload.get("error") or "").strip()


def build_recommend_payload_from_schema(
    schema: Optional[Dict[str, Any]],
    chat_text: str,
    default_currency: str,
) -> Dict[str, Any]:
    schema = dict(schema or {})
    payload: Dict[str, Any] = {
        "chat_text": str(chat_text or "").strip(),
        "channel": "streamlit_chat",
        "currency": str(default_currency or schema.get("currency") or "INR").strip() or "INR",
        "persist": True,
    }

    mapping = {
        "preferred_category": "category",
        "industry": "industry",
        "business_type": "business_type",
        "team_size": "team_size",
        "workload_types": "workload_types",
        "application_signals": "application_signals",
        "capability_tags": "capability_tags",
        "budget": "budget",
        "budget_scope": "budget_scope",
        "growth_expectation": "growth_expectation",
        "existing_infrastructure": "existing_infrastructure",
        "preferred_manufacturers": "preferred_manufacturers",
        "blocked_manufacturers": "blocked_manufacturers",
        "preferred_sellers": "preferred_sellers",
        "blocked_sellers": "blocked_sellers",
        "performance_priority": "performance_priority",
        "portability_need": "portability_need",
        "support_expectation": "support_expectation",
        "availability_need": "availability_need",
        "require_returnable": "require_returnable",
        "quantity": "quantity",
        "purchase_scope": "purchase_scope",
        "rollout_type": "rollout_type",
        "replacement_mode": "replacement_mode",
        "timeline": "timeline",
        "requested_ram": "requested_ram",
        "requested_storage": "requested_storage",
        "requested_ram_is_minimum": "requested_ram_is_minimum",
        "requested_storage_is_minimum": "requested_storage_is_minimum",
        "notes": "notes",
    }

    for source_key, target_key in mapping.items():
        value = schema.get(source_key)
        if value not in (None, "", [], {}):
            payload[target_key] = value

    if payload.get("team_size") is not None:
        payload["team_size"] = str(payload["team_size"])

    return payload


# -----------------------------
# Small self-tests for pure code
# -----------------------------

def _run_self_tests() -> None:
    assert normalize_http_base("http://127.0.0.1:8000/") == "http://127.0.0.1:8000"
    assert normalize_http_base("") == ""

    transcript = [
        {"role": "assistant", "content": "Hello"},
        {"role": "user", "content": "Need 10 laptops"},
        {"role": "user", "content": "Budget 5000 each"},
    ]
    assert latest_user_brief_from_transcript(transcript) == "Need 10 laptops\nBudget 5000 each"
    assert latest_user_brief_from_transcript(None) == ""

    assert extract_response_text({"response": "ok"}) == "ok"
    assert extract_response_text({"error": "bad"}) == "bad"
    assert extract_response_text({}) == ""

    payload = build_recommend_payload_from_schema(
        schema={
            "preferred_category": "laptop",
            "team_size": 15,
            "budget": 5000,
            "blocked_manufacturers": ["BrandX"],
            "notes": "fast rollout",
        },
        chat_text="Need laptops for developers",
        default_currency="INR",
    )
    assert payload["category"] == "laptop"
    assert payload["team_size"] == "15"
    assert payload["budget"] == 5000
    assert payload["blocked_manufacturers"] == ["BrandX"]
    assert payload["currency"] == "INR"
    assert payload["persist"] is True


# -----------------------------
# Streamlit-only app code below
# -----------------------------

def require_streamlit() -> None:
    if st is not None:
        return
    raise SystemExit(
        "This file is a Streamlit app. Install the missing dependency and run it with:\n\n"
        "  pip install streamlit requests websocket-client\n"
        "  streamlit run streamlit_procurement_chat_app.py\n\n"
        "If you want a non-Streamlit version, tell me whether you want a CLI or plain HTML app."
    )


def init_state() -> None:
    defaults = {
        "http_base": DEFAULT_HTTP_BASE,
        "ws_url": DEFAULT_WS_URL,
        "user_id": "",
        "business_id": "",
        "default_currency": "INR",
        "socket": None,
        "socket_status": "disconnected",
        "messages": [],
        "raw_payloads": [],
        "last_ws_payload": None,
        "latest_extracted_schema": {},
        "latest_recommendation": None,
        "latest_persisted_result": None,
        "latest_session_id": "",
        "chat_transcript": [],
        "last_error": "",
        "show_recommend_preview": False,
        "loaded_session": None,
        "expert_review_result": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def api_headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if st.session_state.user_id.strip():
        headers["X-User-Id"] = st.session_state.user_id.strip()
    if st.session_state.business_id.strip():
        headers["X-Business-Id"] = st.session_state.business_id.strip()
    if st.session_state.default_currency.strip():
        headers["X-Default-Currency"] = st.session_state.default_currency.strip()
    return headers


def append_chat(role: str, content: str, payload: Optional[Dict[str, Any]] = None) -> None:
    st.session_state.messages.append(
        {
            "role": role,
            "content": content,
            "payload": payload or {},
        }
    )
    st.session_state.chat_transcript.append({"role": role, "content": content})


def close_socket() -> None:
    sock = st.session_state.socket
    if sock is not None:
        try:
            sock.close()
        except Exception:
            pass
    st.session_state.socket = None
    st.session_state.socket_status = "disconnected"


def connect_socket() -> None:
    if websocket is None:
        st.session_state.last_error = (
            "Missing dependency: websocket-client. Install it with `pip install websocket-client`."
        )
        return

    close_socket()
    try:
        sock = websocket.create_connection(st.session_state.ws_url, timeout=20)
        st.session_state.socket = sock
        st.session_state.socket_status = "connected"
        initial_raw = sock.recv()
        initial_payload = json.loads(initial_raw)
        handle_server_payload(initial_payload)
        st.session_state.last_error = ""
    except Exception as exc:
        close_socket()
        st.session_state.last_error = f"WebSocket connection failed: {exc}"


def send_ws_message(user_text: str) -> None:
    sock = st.session_state.socket
    if sock is None:
        st.session_state.last_error = "WebSocket is not connected."
        return

    cleaned = str(user_text or "").strip()
    if not cleaned:
        return

    append_chat("user", cleaned)
    try:
        sock.send(json.dumps({"userSelection": cleaned}))
        raw_response = sock.recv()
        payload = json.loads(raw_response)
        handle_server_payload(payload)
        st.session_state.last_error = ""
    except Exception as exc:
        st.session_state.last_error = f"WebSocket send/receive failed: {exc}"
        close_socket()


def handle_server_payload(payload: Dict[str, Any]) -> None:
    st.session_state.last_ws_payload = payload
    st.session_state.raw_payloads.append(payload)

    response_text = extract_response_text(payload)
    if response_text:
        append_chat("assistant", response_text, payload=payload)

    extracted = payload.get("extracted_schema")
    if isinstance(extracted, dict) and extracted:
        st.session_state.latest_extracted_schema = extracted

    if payload.get("response_type") == "recommendation":
        st.session_state.latest_recommendation = payload


def reset_chat_state(keep_connection: bool = False) -> None:
    if not keep_connection:
        close_socket()
    st.session_state.messages = []
    st.session_state.raw_payloads = []
    st.session_state.last_ws_payload = None
    st.session_state.latest_extracted_schema = {}
    st.session_state.latest_recommendation = None
    st.session_state.latest_persisted_result = None
    st.session_state.latest_session_id = ""
    st.session_state.chat_transcript = []
    st.session_state.last_error = ""
    st.session_state.show_recommend_preview = False
    st.session_state.loaded_session = None
    st.session_state.expert_review_result = None


def restart_ws_session() -> None:
    if st.session_state.socket is None:
        connect_socket()
        return
    append_chat("user", "restart")
    try:
        st.session_state.socket.send(json.dumps({"userSelection": "restart"}))
        raw_response = st.session_state.socket.recv()
        payload = json.loads(raw_response)
        st.session_state.messages = []
        st.session_state.chat_transcript = []
        st.session_state.raw_payloads = []
        st.session_state.last_ws_payload = None
        st.session_state.latest_extracted_schema = {}
        st.session_state.latest_recommendation = None
        st.session_state.latest_persisted_result = None
        st.session_state.latest_session_id = ""
        st.session_state.loaded_session = None
        st.session_state.expert_review_result = None
        handle_server_payload(payload)
    except Exception as exc:
        st.session_state.last_error = f"Restart failed: {exc}"
        close_socket()


def latest_user_brief() -> str:
    return latest_user_brief_from_transcript(st.session_state.chat_transcript)


def build_recommend_payload() -> Dict[str, Any]:
    return build_recommend_payload_from_schema(
        schema=st.session_state.latest_extracted_schema,
        chat_text=latest_user_brief(),
        default_currency=st.session_state.default_currency,
    )


def _safe_json_response(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"status_code": response.status_code, "text": response.text}


def persist_current_recommendation() -> Optional[Dict[str, Any]]:
    payload = build_recommend_payload()
    if not payload.get("chat_text") and not payload.get("category") and not payload.get("budget"):
        st.session_state.last_error = "Not enough captured chat context to call /recommend/."
        return None

    url = f"{normalize_http_base(st.session_state.http_base)}/api/procurement/recommend/"
    try:
        response = requests.post(url, headers=api_headers(), json=payload, timeout=60)
        data = _safe_json_response(response)
        if response.ok and isinstance(data, dict):
            st.session_state.latest_persisted_result = data
            st.session_state.latest_session_id = str(data.get("session_id") or "")
            st.session_state.last_error = ""
            return data
        st.session_state.last_error = f"/recommend/ failed: {data}"
        return None
    except Exception as exc:
        st.session_state.last_error = f"/recommend/ request failed: {exc}"
        return None


def load_session(session_id: str) -> Optional[Dict[str, Any]]:
    session_id = str(session_id or "").strip()
    if not session_id:
        st.session_state.last_error = "Enter a session id first."
        return None

    url = f"{normalize_http_base(st.session_state.http_base)}/api/procurement/sessions/{session_id}/"
    try:
        response = requests.get(url, headers=api_headers(), timeout=30)
        data = _safe_json_response(response)
        if response.ok and isinstance(data, dict):
            st.session_state.last_error = ""
            return data
        st.session_state.last_error = f"Session lookup failed: {data}"
        return None
    except Exception as exc:
        st.session_state.last_error = f"Session lookup request failed: {exc}"
        return None


def submit_expert_review(reason: str, notes: str) -> Optional[Dict[str, Any]]:
    session_id = st.session_state.latest_session_id
    source = st.session_state.latest_persisted_result or st.session_state.latest_recommendation or {}
    decision_trace_id = str(source.get("decision_trace_id") or "")

    if not session_id and not decision_trace_id:
        st.session_state.last_error = (
            "Need either a persisted session_id or a decision_trace_id before raising expert review."
        )
        return None

    url = f"{normalize_http_base(st.session_state.http_base)}/api/procurement/expert-review/"
    body = {
        "session_id": session_id,
        "decision_trace_id": decision_trace_id,
        "reason": reason.strip(),
        "notes": notes.strip(),
    }
    try:
        response = requests.post(url, headers=api_headers(), json=body, timeout=30)
        data = _safe_json_response(response)
        if response.ok and isinstance(data, dict):
            st.session_state.last_error = ""
            return data
        st.session_state.last_error = f"Expert review request failed: {data}"
        return None
    except Exception as exc:
        st.session_state.last_error = f"Expert review request error: {exc}"
        return None


def render_top_bar() -> None:
    st.title("💬 TechPay Procurement Chat")
    st.caption(
        "Chat-first Streamlit client for your real backend. Primary path = WebSocket chat. "
        "Optional path = persist/load/escalate using procurement REST APIs."
    )


def render_sidebar() -> None:
    with st.sidebar:
        st.subheader("Connection")
        st.session_state.http_base = st.text_input("HTTP base URL", value=st.session_state.http_base)
        st.session_state.ws_url = st.text_input("WebSocket URL", value=st.session_state.ws_url)

        st.subheader("Request headers")
        st.session_state.user_id = st.text_input("X-User-Id", value=st.session_state.user_id)
        st.session_state.business_id = st.text_input("X-Business-Id", value=st.session_state.business_id)
        st.session_state.default_currency = st.text_input(
            "X-Default-Currency", value=st.session_state.default_currency
        )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Connect", use_container_width=True):
                connect_socket()
                st.rerun()
        with c2:
            if st.button("Disconnect", use_container_width=True):
                close_socket()
                st.rerun()

        c3, c4 = st.columns(2)
        with c3:
            if st.button("Restart chat", use_container_width=True):
                restart_ws_session()
                st.rerun()
        with c4:
            if st.button("Clear UI", use_container_width=True):
                reset_chat_state(keep_connection=True)
                st.rerun()

        st.info(f"Socket status: {st.session_state.socket_status}")

        if st.session_state.latest_session_id:
            st.success(f"Latest session_id: {st.session_state.latest_session_id}")

        if st.session_state.last_error:
            st.error(st.session_state.last_error)

        with st.expander("Current extracted schema", expanded=False):
            st.json(st.session_state.latest_extracted_schema or {})

        with st.expander("Last raw WebSocket payload", expanded=False):
            st.json(st.session_state.last_ws_payload or {})


def render_chat() -> None:
    for message in st.session_state.messages:
        with st.chat_message("assistant" if message["role"] == "assistant" else "user"):
            st.markdown(message["content"])
            payload = message.get("payload") or {}
            if payload:
                with st.expander("Payload", expanded=False):
                    st.json(payload)


def render_recommendation_panel() -> None:
    st.subheader("Latest recommendation")
    result = st.session_state.latest_recommendation or {}
    if not result:
        st.caption("No recommendation received from the chat yet.")
        return

    top_cols = st.columns(4)
    top_cols[0].metric("Mode", str(result.get("recommendation_mode") or "-"))
    top_cols[1].metric("Category", str(result.get("category") or result.get("preferred_category") or "-"))
    top_cols[2].metric("Decision trace", str(result.get("decision_trace_id") or "-"))
    top_cols[3].metric("Expert review eligible", str(bool(result.get("expert_review_eligible"))))

    recommendations = result.get("recommendations") or []
    groups = result.get("recommendation_groups") or []

    if recommendations:
        st.markdown("#### Ranked recommendations")
        for idx, rec in enumerate(recommendations, start=1):
            with st.container(border=True):
                st.markdown(f"**{idx}. {rec.get('name', 'Unnamed product')}**")
                st.write(
                    {
                        "category": rec.get("category"),
                        "price": rec.get("price"),
                        "currency": rec.get("currency"),
                        "sku_id": rec.get("sku_id"),
                        "manufacturer": rec.get("manufacturer"),
                    }
                )
                if rec.get("reasons"):
                    st.markdown("**Reasons**")
                    for reason in rec.get("reasons"):
                        st.write(f"- {reason}")
                if rec.get("explanation"):
                    st.markdown(f"**Explanation:** {rec['explanation']}")
                if rec.get("buy_url"):
                    st.markdown(f"[Open product link]({rec['buy_url']})")

    if groups:
        st.markdown("#### Recommendation groups")
        st.json(groups)

    with st.expander("Full recommendation payload", expanded=False):
        st.json(result)


def render_persist_panel() -> None:
    st.subheader("Persist current chat result into the real procurement session API")
    st.caption(
        "Your current WebSocket flow uses in-memory chat logic. This button calls /api/procurement/recommend/ "
        "with the latest extracted chat context so you also get a saved session and API-shaped result."
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Save latest chat as procurement session", type="primary", use_container_width=True):
            persist_current_recommendation()
            st.rerun()
    with col2:
        if st.button("Show recommend payload preview", use_container_width=True):
            st.session_state.show_recommend_preview = True

    if st.session_state.get("show_recommend_preview"):
        st.json(build_recommend_payload())

    persisted = st.session_state.latest_persisted_result or {}
    if persisted:
        st.success("Latest /recommend/ call succeeded.")
        st.json(
            {
                "session_id": persisted.get("session_id"),
                "decision_trace_id": persisted.get("decision_trace_id"),
                "recommendation_mode": persisted.get("recommendation_mode"),
                "expert_review_eligible": persisted.get("expert_review_eligible"),
            }
        )
        with st.expander("Full persisted API result", expanded=False):
            st.json(persisted)


def render_session_panel() -> None:
    st.subheader("Load saved procurement session")
    session_id = st.text_input(
        "Session ID",
        value=st.session_state.latest_session_id,
        help="Loads the saved result from GET /api/procurement/sessions/{session_id}/",
    )
    if st.button("Load session", use_container_width=False):
        session = load_session(session_id)
        if session:
            st.session_state.loaded_session = session
        st.rerun()

    loaded = st.session_state.loaded_session
    if loaded:
        st.json(loaded)


def render_expert_review_panel() -> None:
    st.subheader("Expert review")
    with st.form("expert_review_form"):
        reason = st.text_input("Reason", value="Need manual procurement review")
        notes = st.text_area("Notes", value="")
        submitted = st.form_submit_button("Raise expert review")

    if submitted:
        result = submit_expert_review(reason, notes)
        if result:
            st.session_state.expert_review_result = result
        st.rerun()

    if st.session_state.expert_review_result:
        st.success("Expert review request created.")
        st.json(st.session_state.expert_review_result)


def main() -> None:
    require_streamlit()
    st.set_page_config(page_title="TechPay Procurement Chat", page_icon="💬", layout="wide")
    init_state()

    render_top_bar()
    render_sidebar()

    left, right = st.columns([1.3, 1])

    with left:
        render_chat()
        prompt = st.chat_input(
            "Type your procurement requirement here... Example: We need 15 laptops for software developers under 6500 each"
        )
        if prompt:
            if st.session_state.socket is None:
                connect_socket()
            if st.session_state.socket is not None:
                send_ws_message(prompt)
            st.rerun()

    with right:
        render_recommendation_panel()
        st.divider()
        render_persist_panel()
        st.divider()
        render_session_panel()
        st.divider()
        render_expert_review_panel()

    with st.expander("Notes", expanded=False):
        st.markdown(
            """
- Primary conversation path uses `ws/sales-bot/`.
- Current backend keeps WebSocket chat state in memory, so restart/server refresh can drop chat context.
- `Save latest chat as procurement session` is the bridge that pushes the chat result into `/api/procurement/recommend/` with `persist=true`.
- This file is chat-first. It does not render the guided intake form.
            """
        )


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        _run_self_tests()
        print("Self-tests passed.")
    else:
        main()

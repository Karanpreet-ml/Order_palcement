# Standalone final Streamlit tester built from streamlit_chat_tester.py + v2 + v3.
# This file does not import the other tester scripts.

import html
import json
import os
import sys
import uuid
from copy import deepcopy
from pathlib import Path

import streamlit as st

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

PAGES_DIR = SCRIPTS_DIR / "streamlit_pages"
PAGE_FILES = {
    "intake": PAGES_DIR / "1_Intake.py",
    "results": PAGES_DIR / "2_Results.py",
    "studio": PAGES_DIR / "3_Studio.py",
    "debug": PAGES_DIR / "4_Debug.py",
}

from procurement_chat_runtime import build_procurement_chat_runtime
from ai_configurator.procurement.models import ProcurementExpertReviewRequest
from ai_configurator.procurement.serializers import ProcurementExpertReviewRequestSerializer
from ai_configurator.sales_chat.services.ui_guidance import build_narrowing_guidance

DEFAULT_PROVIDER_MODELS = {
    "groq": "openai/gpt-oss-120b",
    "gemini": "gemini-2.0-flash",
}
CATALOG_SIZE_OPTIONS = ["small", "large", "corrected_json", "mongo"]
CATEGORY_OPTIONS = ["", "laptops", "desktops", "servers", "networking", "printers", "accessories"]
WORKLOAD_OPTIONS = [
    "office_productivity",
    "retail_operations",
    "software_development",
    "creative_design",
    "ai_analytics",
    "server_infrastructure",
    "network_connectivity",
]
QUICK_PROMPTS = [
    {
        "label": "Developer laptops",
        "caption": "15 laptops, moderate growth, premium support",
        "prompt": "We need 15 lightweight laptops for software developers under 90000 each with moderate growth and premium support",
    },
    {
        "label": "Design team",
        "caption": "6 slim laptops, 32GB RAM, premium support",
        "prompt": "Need slim laptops for 6 designers with 32GB RAM under 140000 each and premium support",
    },
    {
        "label": "Branch networking",
        "caption": "Network gear for a new branch office",
        "prompt": "Opening a branch office and need networking gear under 50000",
    },
    {
        "label": "Virtualization server",
        "caption": "Single-office server, performance-first",
        "prompt": "Need a virtualization server for one office, budget 600000, premium support, moderate growth, performance first",
    },
]
FIT_LABELS = {
    "good_fit": "Good fit",
    "partial_fit": "Partial fit",
    "stretch": "Stretch",
    "limited_availability": "Limited availability",
    "fallback": "Fallback option",
}
FIT_TONES = {
    "good_fit": "teal",
    "partial_fit": "warm",
    "stretch": "rose",
    "limited_availability": "warm",
    "fallback": "info",
}
FALLBACK_LABELS = {
    "blocking_clarification_required": "Need clarification before recommendation",
    "semantic_unavailable": "Semantic retrieval unavailable",
    "lexical_unavailable": "Lexical retrieval unavailable",
    "semantic_and_lexical_sparse": "Retrieval signals were too sparse",
    "retrieval_broadened": "No exact retrieval match, broadened within safe scope",
    "compatibility_blocked_all": "All candidates failed item compatibility",
    "policy_rejected_all": "All compatible candidates were rejected by policy",
    "no_exact_fit": "No exact fit was found",
}
CONFIDENCE_TONES = {
    "high": "teal",
    "medium": "warm",
    "low": "rose",
}

APP_CSS = """
<style>
    :root {
        --proc-ink: #0f172a;
        --proc-surface-ink: #0f172a;
        --proc-muted: #475569;
        --proc-teal: #0f766e;
        --proc-teal-soft: #f0fdfa;
        --proc-warm: #a16207;
        --proc-warm-soft: #fffbeb;
        --proc-info: #1e40af;
        --proc-info-soft: #eff6ff;
        --proc-rose: #be123c;
        --proc-rose-soft: #fff1f2;
        --proc-bg: #f8fafc;
        --proc-bg-deep: #eef2f7;
        --proc-surface: #ffffff;
        --proc-surface-soft: #f8fafc;
        --proc-surface-strong: #f1f5f9;
        --proc-border: #d7e0ea;
        --proc-border-strong: #c4d0dd;
        --proc-shadow: 0 14px 36px rgba(15, 23, 42, 0.08);
    }

    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background:
            radial-gradient(circle at top left, rgba(161, 98, 7, 0.08), transparent 22%),
            radial-gradient(circle at top right, rgba(15, 118, 110, 0.06), transparent 22%),
            linear-gradient(180deg, var(--proc-bg) 0%, var(--proc-bg-deep) 100%) !important;
        color: var(--proc-ink) !important;
    }

    .block-container {
        max-width: 1380px;
        padding-top: 1.5rem;
        padding-bottom: 2.25rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    [data-testid="stSidebar"] {
        background: #f1f5f9 !important;
        border-right: 1px solid var(--proc-border);
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--proc-surface);
        border: 1px solid var(--proc-border);
        border-radius: 12px;
        box-shadow: var(--proc-shadow);
        padding: 0.15rem 0.45rem 0.55rem;
    }

    [data-testid="stMetric"] {
        background: var(--proc-info-soft);
        border: 1px solid #c9d8fb;
        border-radius: 12px;
        padding: 0.8rem;
    }

    [data-testid="stMetric"] *,
    [data-testid="stMetricLabel"],
    [data-testid="stMetricValue"] {
        color: var(--proc-surface-ink) !important;
    }

    [data-testid="stMetric"] p,
    [data-testid="stMetric"] div,
    [data-testid="stMetric"] label,
    [data-testid="stMetric"] span {
        color: var(--proc-surface-ink) !important;
        -webkit-text-fill-color: var(--proc-surface-ink) !important;
    }

    [data-testid="stChatMessage"] {
        background: var(--proc-surface);
        border: 1px solid var(--proc-border);
        border-radius: 12px;
        padding: 0.25rem 0.45rem;
    }

    div.stButton > button {
        min-height: 2.9rem;
        border-radius: 999px;
        border: 1px solid var(--proc-border-strong);
        background: var(--proc-surface);
        color: var(--proc-ink) !important;
        font-weight: 600;
        box-shadow: none;
    }

    div.stButton > button:hover {
        color: var(--proc-ink) !important;
        border-color: var(--proc-teal);
        background: var(--proc-teal-soft);
    }

    div.stButton > button[kind="primary"],
    div.stButton > button[data-testid="baseButton-primary"] {
        background: var(--proc-teal) !important;
        border-color: var(--proc-teal) !important;
        color: white !important;
    }

    div[data-testid="stForm"] {
        background: var(--proc-surface-soft);
        border-radius: 12px;
        padding: 0.8rem 0.2rem 0.2rem;
    }

    div[data-testid="stExpander"] {
        background: var(--proc-surface-soft);
        border: 1px solid var(--proc-border);
        border-radius: 12px;
        overflow: hidden;
    }

    [data-testid="stTabs"] button[role="tab"] {
        background: var(--proc-surface);
        border: 1px solid var(--proc-border);
        border-radius: 999px;
        color: var(--proc-muted);
        font-weight: 700;
        margin-right: 0.45rem;
    }

    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        background: var(--proc-info-soft);
        color: var(--proc-info);
        border-color: #bfd3ff;
    }

    div[data-testid="stChatInput"] {
        background: var(--proc-surface);
        border: 1px solid var(--proc-border);
        border-radius: 12px;
        padding: 0.25rem 0.35rem;
        max-width: 56rem;
        margin: 1rem auto 0;
    }

    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea,
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div,
    .stMultiSelect [data-baseweb="tag"] {
        background: var(--proc-surface) !important;
        border-color: var(--proc-border) !important;
        color: var(--proc-ink) !important;
    }

    .stTextInput label,
    .stNumberInput label,
    .stTextArea label,
    .stSelectbox label,
    .stMultiSelect label {
        color: var(--proc-ink) !important;
        font-weight: 700 !important;
    }

    div[data-baseweb="popover"],
    div[role="listbox"],
    ul[role="listbox"] {
        background: var(--proc-surface) !important;
        color: var(--proc-ink) !important;
        border: 1px solid var(--proc-border) !important;
    }

    div[role="option"],
    li[role="option"] {
        background: var(--proc-surface) !important;
        color: var(--proc-ink) !important;
    }

    div[role="option"]:hover,
    li[role="option"]:hover,
    div[role="option"][aria-selected="true"],
    li[role="option"][aria-selected="true"] {
        background: var(--proc-info-soft) !important;
        color: var(--proc-ink) !important;
    }

    div[data-baseweb="select"] span,
    div[data-baseweb="select"] input,
    div[data-baseweb="input"] input,
    div[data-baseweb="input"] span {
        color: var(--proc-ink) !important;
    }

    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    .stCaption,
    .stCaptionContainer {
        color: var(--proc-ink) !important;
    }

    [data-testid="stMarkdownContainer"] span:not(.proc-badge) {
        color: var(--proc-ink) !important;
    }

    .proc-hero {
        background: linear-gradient(180deg, #fffaf0 0%, #fffbeb 100%);
        border: 1px solid var(--proc-border);
        border-radius: 12px;
        padding: 1.6rem 1.7rem;
        box-shadow: var(--proc-shadow);
        margin-bottom: 1rem;
    }

    .proc-hero--intake {
        max-width: 56rem;
        margin: 2rem auto 1.35rem;
        padding: 2.5rem 2.35rem;
        text-align: center;
    }

    .proc-kicker {
        color: var(--proc-warm);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        margin-bottom: 0.35rem;
    }

    .proc-title {
        margin: 0;
        color: var(--proc-ink);
        font-size: 2.3rem;
        line-height: 1.05;
        letter-spacing: -0.04em;
    }

    .proc-copy {
        margin: 0.6rem 0 0;
        max-width: 60rem;
        color: var(--proc-muted);
        font-size: 1rem;
        line-height: 1.55;
    }

    .proc-hero--intake .proc-copy {
        margin-left: auto;
        margin-right: auto;
        max-width: 44rem;
    }

    .proc-section {
        margin: 0.15rem 0 0.65rem;
    }

    .proc-section__eyebrow {
        color: var(--proc-warm);
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        margin-bottom: 0.2rem;
    }

    .proc-section__title {
        margin: 0;
        color: var(--proc-ink);
        font-size: 1.25rem;
        letter-spacing: -0.02em;
    }

    .proc-section__copy {
        margin: 0.35rem 0 0;
        color: var(--proc-muted);
        line-height: 1.45;
    }

    .proc-badge-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin: 0.75rem 0 0.15rem;
    }

    .proc-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.34rem 0.74rem;
        border-radius: 999px;
        border: 1px solid transparent;
        font-size: 0.78rem;
        font-weight: 700;
        line-height: 1;
        white-space: nowrap;
    }

    .proc-badge--neutral {
        background: #f8fafc;
        border-color: var(--proc-border-strong);
        color: var(--proc-muted);
    }

    .proc-badge--teal {
        background: var(--proc-teal-soft);
        border-color: #7fd6ce;
        color: var(--proc-teal);
    }

    .proc-badge--warm {
        background: var(--proc-warm-soft);
        border-color: #f0c36a;
        color: var(--proc-warm);
    }

    .proc-badge--info {
        background: var(--proc-info-soft);
        border-color: #bfd3ff;
        color: var(--proc-info);
    }

    .proc-badge--rose {
        background: var(--proc-rose-soft);
        border-color: #f7bac9;
        color: var(--proc-rose);
    }

    .proc-price {
        font-size: 1.7rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: var(--proc-ink);
        margin: 0.1rem 0 0.35rem;
    }

    .proc-note {
        background: var(--proc-surface-strong);
        border: 1px solid var(--proc-border);
        border-radius: 12px;
        padding: 0.8rem 0.95rem;
        color: var(--proc-surface-ink);
        margin-top: 0.55rem;
    }

    .proc-note,
    .proc-note p,
    .proc-note li,
    .proc-note ul,
    .proc-note strong,
    .proc-note span,
    .proc-note div {
        color: var(--proc-surface-ink) !important;
        -webkit-text-fill-color: var(--proc-surface-ink) !important;
    }

    .proc-note--teal .proc-mini-label {
        color: var(--proc-teal) !important;
    }

    .proc-note--teal {
        background: var(--proc-teal-soft);
        border-color: #7fd6ce;
    }

    .proc-note--warm {
        background: var(--proc-warm-soft);
        border-color: #f0c36a;
    }

    .proc-note--warm .proc-mini-label {
        color: var(--proc-warm) !important;
    }

    .proc-note--info {
        background: var(--proc-info-soft);
        border-color: #bfd3ff;
    }

    .proc-note--info .proc-mini-label {
        color: var(--proc-info) !important;
    }

    .proc-note--rose {
        background: var(--proc-rose-soft);
        border-color: #f7bac9;
    }

    .proc-note--rose .proc-mini-label {
        color: var(--proc-rose) !important;
    }

    .proc-quote {
        border-left: 4px solid var(--proc-warm);
        background: var(--proc-warm-soft);
        border-radius: 0 12px 12px 0;
        padding: 0.85rem 1rem;
        margin-top: 0.4rem;
        color: var(--proc-surface-ink);
    }

    .proc-quote,
    .proc-quote p,
    .proc-quote li,
    .proc-quote span,
    .proc-quote div {
        color: var(--proc-surface-ink) !important;
        -webkit-text-fill-color: var(--proc-surface-ink) !important;
    }

    .proc-empty {
        background: var(--proc-surface);
        border: 1px dashed var(--proc-border-strong);
        border-radius: 12px;
        padding: 1rem 1.1rem;
        color: var(--proc-surface-ink);
    }

    .proc-empty,
    .proc-empty p,
    .proc-empty li,
    .proc-empty span,
    .proc-empty div {
        color: var(--proc-surface-ink) !important;
        -webkit-text-fill-color: var(--proc-surface-ink) !important;
    }

    .proc-mini-label {
        color: var(--proc-muted);
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }

    .proc-divider {
        height: 1px;
        background: linear-gradient(90deg, rgba(30, 64, 175, 0.24), rgba(30, 64, 175, 0));
        margin: 0.85rem 0 0.6rem;
    }

    .proc-clarify-card {
        background: var(--proc-warm-soft);
        border-left: 4px solid #d97706;
        border-top: 1px solid #f0c36a;
        border-right: 1px solid #f0c36a;
        border-bottom: 1px solid #f0c36a;
        border-radius: 12px;
        padding: 1.45rem 1.35rem;
        box-shadow: var(--proc-shadow);
        margin: 0.4rem 0 1rem;
    }

    .proc-clarify-card,
    .proc-clarify-card p,
    .proc-clarify-card span,
    .proc-clarify-card div {
        color: var(--proc-surface-ink) !important;
        -webkit-text-fill-color: var(--proc-surface-ink) !important;
    }

    .proc-clarify-card__question {
        font-size: 1.35rem;
        line-height: 1.4;
        color: var(--proc-surface-ink);
        font-weight: 700;
        margin-top: 0.35rem;
    }

    .proc-compact-card {
        background: var(--proc-surface);
        border: 1px solid var(--proc-border);
        border-radius: 12px;
        padding: 1rem 1rem 0.85rem;
        min-height: 100%;
    }

    .proc-compact-card,
    .proc-compact-card p,
    .proc-compact-card span,
    .proc-compact-card div {
        color: var(--proc-surface-ink) !important;
        -webkit-text-fill-color: var(--proc-surface-ink) !important;
    }

    .proc-compact-card__title {
        font-size: 1rem;
        font-weight: 700;
        color: var(--proc-surface-ink);
        margin-bottom: 0.25rem;
    }

    .proc-compact-card__copy {
        color: var(--proc-muted);
        font-size: 0.92rem;
        line-height: 1.5;
    }

    .proc-action-strip {
        background: var(--proc-surface);
        border: 1px solid var(--proc-border);
        border-radius: 12px;
        padding: 1rem 1rem 0.6rem;
        margin-top: 1rem;
    }

    .proc-detail-card {
        background: var(--proc-surface);
        border: 1px solid #bfd3ff;
        border-radius: 12px;
        padding: 1.1rem 1.1rem 0.85rem;
        margin-top: 1rem;
    }

    .proc-detail-card,
    .proc-detail-card p,
    .proc-detail-card span,
    .proc-detail-card div {
        color: var(--proc-surface-ink) !important;
        -webkit-text-fill-color: var(--proc-surface-ink) !important;
    }

    .proc-choice-card {
        background: var(--proc-surface);
        border: 1px solid var(--proc-border);
        border-radius: 12px;
        padding: 1.1rem 1rem 0.95rem;
        min-height: 100%;
    }

    .proc-quick-label {
        display: inline-flex;
        align-items: center;
        padding: 0.28rem 0.62rem;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        border: 1px solid transparent;
    }

    .proc-quick-label--teal {
        background: var(--proc-teal-soft);
        border-color: #7fd6ce;
        color: var(--proc-teal);
    }

    .proc-quick-label--warm {
        background: var(--proc-warm-soft);
        border-color: #f0c36a;
        color: var(--proc-warm);
    }

    .proc-quick-label--info {
        background: var(--proc-info-soft);
        border-color: #bfd3ff;
        color: var(--proc-info);
    }

    .proc-inline-callout {
        border-radius: 12px;
        padding: 0.78rem 0.9rem;
        margin-bottom: 0.6rem;
        border: 1px solid var(--proc-border);
    }

    .proc-inline-callout--rose {
        background: var(--proc-rose-soft);
        border-color: #f7bac9;
        color: var(--proc-rose);
    }

    .proc-inline-callout__title {
        font-size: 0.8rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-bottom: 0.2rem;
    }

    .proc-inline-callout__copy {
        font-size: 0.9rem;
        line-height: 1.45;
        color: inherit;
    }

    .proc-inline-callout,
    .proc-inline-callout p,
    .proc-inline-callout span,
    .proc-inline-callout div {
        color: inherit !important;
        -webkit-text-fill-color: currentColor !important;
    }

    .proc-studio-caption {
        color: var(--proc-muted);
        font-size: 0.92rem;
        line-height: 1.45;
        margin: 0.45rem 0 0;
    }

    .proc-compare-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        background: #f8faff;
        border: 1px solid #dbeafe;
        border-radius: 12px;
        overflow: hidden;
        margin-top: 0.9rem;
    }

    .proc-compare-table th,
    .proc-compare-table td {
        padding: 0.8rem 0.9rem;
        border-bottom: 1px solid #dbeafe;
        text-align: left;
        vertical-align: top;
        color: var(--proc-ink);
        font-size: 0.94rem;
    }

    .proc-compare-table th {
        background: #dbeafe;
        color: var(--proc-info);
        font-weight: 800;
    }

    .proc-compare-table tr:last-child td {
        border-bottom: none;
    }

    .proc-compare-table td.proc-compare-win {
        background: var(--proc-teal-soft);
        color: var(--proc-teal);
        font-weight: 800;
    }

    .proc-compare-table th.proc-compare-best,
    .proc-compare-table td.proc-compare-best {
        border-left: 4px solid var(--proc-teal);
    }

    @media (prefers-color-scheme: dark) {
        :root {
            --proc-ink: #f1f5f9;
            --proc-surface-ink: #f8fafc;
            --proc-muted: #cbd5e1;
            --proc-teal: #5eead4;
            --proc-teal-soft: rgba(20, 184, 166, 0.18);
            --proc-warm: #fbbf24;
            --proc-warm-soft: rgba(245, 158, 11, 0.18);
            --proc-info: #93c5fd;
            --proc-info-soft: rgba(59, 130, 246, 0.18);
            --proc-rose: #fb7185;
            --proc-rose-soft: rgba(244, 63, 94, 0.16);
            --proc-bg: #0f172a;
            --proc-bg-deep: #111827;
            --proc-surface: #1e293b;
            --proc-surface-soft: #172133;
            --proc-surface-strong: #233146;
            --proc-border: #334155;
            --proc-border-strong: #475569;
            --proc-shadow: 0 20px 42px rgba(2, 6, 23, 0.35);
        }

        [data-testid="stSidebar"] {
            background: #162132 !important;
        }

        .proc-hero {
            background: linear-gradient(180deg, rgba(161, 98, 7, 0.14) 0%, rgba(255, 251, 235, 0.06) 100%);
        }

        div[data-testid="stTable"] table,
        .proc-compare-table {
            background: #132033 !important;
            border-color: #29456d !important;
        }

        div[data-testid="stTable"] thead tr,
        .proc-compare-table th {
            background: #1a3050 !important;
        }

        .proc-compare-table td.proc-compare-win {
            background: rgba(15, 118, 110, 0.18);
        }
    }

    div[data-testid="stTable"] table {
        background: #f8faff !important;
        border: 1px solid #dbeafe !important;
    }

    div[data-testid="stTable"] thead tr {
        background: #dbeafe !important;
    }

    div[data-testid="stTable"] th {
        color: var(--proc-info) !important;
        font-weight: 700 !important;
    }
</style>
"""


def apply_runtime_env(provider, api_key, model, disable_explanation_llm):
    provider = (provider or "groq").strip().lower()
    model = (model or DEFAULT_PROVIDER_MODELS.get(provider) or "").strip()
    os.environ["LLM_PROVIDER"] = provider
    os.environ["VALIDATION_DISABLE_EXPLANATION_LLM"] = "true" if disable_explanation_llm else "false"
    if provider == "gemini":
        os.environ["GEMINI_API_KEY"] = api_key.strip()
        os.environ["GEMINI_MODEL"] = model or DEFAULT_PROVIDER_MODELS["gemini"]
    else:
        os.environ["GROQ_API_KEY"] = api_key.strip()
        os.environ["GROQ_MODEL"] = model or DEFAULT_PROVIDER_MODELS["groq"]


def get_current_model(service):
    llm_client = service.extraction_service.llm_client
    return llm_client.gemini_model_name if llm_client.provider == "gemini" else llm_client.model_name


def format_price(value, currency):
    if value is None:
        return "Price unavailable"
    return f"{currency or 'INR'} {int(value):,}"


def fit_label(value):
    return FIT_LABELS.get(value or "", "Unknown")


def fit_tone(value):
    return FIT_TONES.get(value or "", "neutral")


def fallback_label(value):
    return FALLBACK_LABELS.get(value or "", "")


def confidence_tone(value):
    return CONFIDENCE_TONES.get(str(value or "").strip().lower(), "neutral")


def compare_number(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def join_items(values):
    return ", ".join(str(item) for item in (values or []) if str(item).strip()) or "Not captured"


def as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def badge_html(label, tone="neutral"):
    return f"<span class='proc-badge proc-badge--{tone}'>{html.escape(str(label))}</span>"


def render_badges(items):
    badges = [badge_html(label, tone) for label, tone in items if label]
    if badges:
        st.markdown(f"<div class='proc-badge-row'>{''.join(badges)}</div>", unsafe_allow_html=True)


def render_section_header(title, subtitle="", eyebrow=""):
    bits = ["<div class='proc-section'>"]
    if eyebrow:
        bits.append(f"<div class='proc-section__eyebrow'>{html.escape(eyebrow)}</div>")
    bits.append(f"<h3 class='proc-section__title'>{html.escape(title)}</h3>")
    if subtitle:
        bits.append(f"<p class='proc-section__copy'>{html.escape(subtitle)}</p>")
    bits.append("</div>")
    st.markdown("".join(bits), unsafe_allow_html=True)


def render_empty_state(message):
    st.markdown(f"<div class='proc-empty'>{html.escape(message)}</div>", unsafe_allow_html=True)


def render_note(message, tone="neutral"):
    st.markdown(
        f"<div class='proc-note proc-note--{html.escape(str(tone))}'>{html.escape(message)}</div>",
        unsafe_allow_html=True,
    )


def render_quote(message):
    st.markdown(f"<div class='proc-quote'>{html.escape(message)}</div>", unsafe_allow_html=True)


def render_reason_box(title, items, tone="warm"):
    lines = "".join(f"<li>{html.escape(str(item))}</li>" for item in (items or []))
    if not lines:
        lines = "<li>No additional detail was returned.</li>"
    st.markdown(
        f"""
        <div class='proc-note proc-note--{html.escape(str(tone))}'>
            <div class='proc-mini-label' style='margin-bottom:0.45rem;'>{html.escape(title)}</div>
            <ul style='margin:0; padding-left:1rem;'>{lines}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def normalize_reason_columns(left_items, right_items, left_fallback, right_fallback, min_items=2, max_items=3):
    left = [str(item).strip() for item in (left_items or []) if str(item).strip()]
    right = [str(item).strip() for item in (right_items or []) if str(item).strip()]
    target = min(max(max(len(left), len(right), min_items), 1), max_items)
    if not left:
        left = [left_fallback]
    if not right:
        right = [right_fallback]
    left = left[:target]
    right = right[:target]
    while len(left) < target:
        left.append(left_fallback)
    while len(right) < target:
        right.append(right_fallback)
    return left, right


def render_quick_label(label, tone):
    st.markdown(
        f"<div class='proc-quick-label proc-quick-label--{html.escape(str(tone))}'>{html.escape(str(label))}</div>",
        unsafe_allow_html=True,
    )


def collect_snapshot(service, session_id, store_id):
    prefs = deepcopy(service.session_answers.get(session_id, {}))
    cached_payload = deepcopy((st.session_state.get("session_payloads") or {}).get(session_id) or {})
    result = deepcopy(cached_payload) if cached_payload else None
    if prefs:
        if hasattr(service, "recommend_current_preferences"):
            computed_result = service.recommend_current_preferences(
                prefs,
                session_id=session_id,
                persist=False,
            )
        else:
            computed_result = service.recommendation_service.recommend_from_chat_preferences(
                prefs,
                store_id=store_id,
                persist=False,
            )
        if result and not computed_result.get("next_question"):
            stale_question = str(result.pop("next_question", "") or "").strip()
            if stale_question and str(result.get("response") or "").strip() == stale_question:
                result.pop("response", None)
            if str(result.get("response_type") or "").strip() == "question":
                result.pop("response_type", None)
        result = {**(result or {}), **computed_result}
    llm_stats = {
        "provider": service.extraction_service.llm_client.provider,
        "model": get_current_model(service),
        "available": service.extraction_service.llm_client.is_available(),
        "extraction": deepcopy(service.extraction_service.llm_client.stats),
        "followup": deepcopy(service.followup_service.llm_client.stats),
        "explanation": deepcopy(service.recommendation_service.explanation_service.llm_client.stats),
    }
    return {
        "preferences": prefs,
        "result": result or {},
        "llm_stats": llm_stats,
    }


def render_compare_table(items):
    columns = [
        ("Price", "price", "min", lambda item: format_price(item.get("price"), item.get("currency"))),
        ("Fit", "fit_status", None, lambda item: fit_label(item.get("fit_status"))),
        ("RAM", "ram_gb", "max", lambda item: "n/a" if item.get("ram_gb") in (None, "") else str(item.get("ram_gb"))),
        ("Storage", "storage_gb", "max", lambda item: "n/a" if item.get("storage_gb") in (None, "") else str(item.get("storage_gb"))),
        ("Support", "support_score", "max", lambda item: "n/a" if item.get("support_score") in (None, "") else str(item.get("support_score"))),
        ("Warranty", "warranty_years", "max", lambda item: "n/a" if item.get("warranty_years") in (None, "") else str(item.get("warranty_years"))),
        ("Stock", "stock_quantity", "max", lambda item: "n/a" if item.get("stock_quantity") in (None, "") else str(item.get("stock_quantity"))),
    ]
    winners = {}
    for _, key, strategy, _ in columns:
        if not strategy:
            continue
        numeric_values = [compare_number(item.get(key)) for item in items]
        numeric_values = [value for value in numeric_values if value is not None]
        if not numeric_values:
            continue
        winners[key] = min(numeric_values) if strategy == "min" else max(numeric_values)

    header_cells = ["<th>Metric</th>"]
    for index, item in enumerate(items):
        classes = ["proc-compare-best"] if index == 0 else []
        label = str(item.get("name") or "Recommendation")
        header_cells.append(f"<th class='{' '.join(classes)}'>{html.escape(label)}</th>")

    rows_html = []
    for label, key, strategy, formatter in columns:
        row = [f"<td>{html.escape(label)}</td>"]
        for index, item in enumerate(items):
            classes = ["proc-compare-best"] if index == 0 else []
            if strategy and compare_number(item.get(key)) is not None and winners.get(key) == compare_number(item.get(key)):
                classes.append("proc-compare-win")
            row.append(f"<td class='{' '.join(classes)}'>{html.escape(formatter(item))}</td>")
        rows_html.append(f"<tr>{''.join(row)}</tr>")

    st.markdown(
        f"""
        <table class='proc-compare-table'>
            <thead><tr>{''.join(header_cells)}</tr></thead>
            <tbody>{''.join(rows_html)}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )


def should_render_transparency_panel(result):
    if not result:
        return False
    meta = result.get("meta") or {}
    compatibility = meta.get("compatibility_rejections_sample") or []
    policy = meta.get("policy_rejections_sample") or []
    return bool(
        result.get("fallback_reason")
        or compatibility
        or policy
        or result.get("assumptions")
        or result.get("recommendation_groups")
    )


TOOL_PROFILE_FIELDS = {"workload_or_application_profile", "application_profile"}
APPLICATION_TOOL_QUICK_ANSWERS = [
    {
        "label": "Excel / Sheets",
        "message_fragment": "Excel, spreadsheets, and browser-based business apps",
    },
    {
        "label": "Browser-heavy work",
        "message_fragment": "browser tools, web apps, and lots of tabs",
    },
    {
        "label": "Development tools",
        "message_fragment": "VS Code, IntelliJ, and software development tools",
    },
    {
        "label": "Docker / Containers",
        "message_fragment": "Docker, containers, and local databases",
    },
    {
        "label": "Photoshop / Illustrator",
        "message_fragment": "Photoshop and Illustrator",
    },
    {
        "label": "Premiere / Video editing",
        "message_fragment": "Premiere, After Effects, and video editing",
    },
    {
        "label": "VMware / Virtual machines",
        "message_fragment": "VMware, Hyper-V, Proxmox, and virtual machines",
    },
    {
        "label": "Data / BI tools",
        "message_fragment": "Power BI dashboards, spreadsheets, and Jupyter notebooks",
    },
]


def clarification_field(snapshot):
    result = snapshot.get("result") or current_result(snapshot) or {}
    readiness = result.get("readiness") or {}
    return str(readiness.get("highest_priority_missing_field") or "").strip()


def clarification_supports_tool_multiselect(snapshot):
    return clarification_field(snapshot) in TOOL_PROFILE_FIELDS


def clarification_multiselect_key(snapshot, prefix):
    session_id = str(st.session_state.get("active_session_id") or "session").strip() or "session"
    field = clarification_field(snapshot) or "unknown"
    return f"{prefix}-clarify-tools-{session_id}-{field}"


def clarification_freeform_placeholder(snapshot):
    if clarification_supports_tool_multiselect(snapshot):
        return "e.g. Excel, browser tools, Docker, or VMware"
    return "Start your own conversation"


def build_tool_profile_message(options, selected_labels):
    selected_labels = [str(label or "").strip() for label in selected_labels or [] if str(label or "").strip()]
    if not selected_labels:
        return ""
    fragments_by_label = {
        str(option.get("label") or "").strip(): str(option.get("message_fragment") or "").strip()
        for option in options or []
        if str(option.get("label") or "").strip()
    }
    selected_fragments = [
        fragments_by_label[label]
        for label in selected_labels
        if fragments_by_label.get(label)
    ]
    if not selected_fragments:
        return ""
    return "The main apps and tools are {}.".format(join_items(selected_fragments))


def clarification_quick_answers(snapshot):
    result = snapshot.get("result") or {}
    field = clarification_field(snapshot)
    requirements = result.get("requirements") or {}
    currency = requirements.get("currency") or "INR"
    category = requirements.get("preferred_category") or ""
    quantity = int(requirements.get("quantity") or requirements.get("team_size") or 0)

    if field in {"preferred_category", "category_or_workload"}:
        return [
            {"label": "Laptops", "message": "We need laptops."},
            {"label": "Desktops", "message": "We need desktops."},
            {"label": "Servers", "message": "We need servers."},
            {"label": "Networking", "message": "We need networking equipment."},
        ]
    if field in TOOL_PROFILE_FIELDS:
        return list(APPLICATION_TOOL_QUICK_ANSWERS)
    if field == "budget":
        if category in {"servers"}:
            return [
                {"label": f"{currency} 400k", "message": f"Budget is around {currency} 400000."},
                {"label": f"{currency} 600k", "message": f"Budget is around {currency} 600000."},
                {"label": f"{currency} 900k+", "message": f"Budget is above {currency} 900000."},
            ]
        if category in {"networking"}:
            return [
                {"label": f"{currency} 20k", "message": f"Budget is around {currency} 20000."},
                {"label": f"{currency} 50k", "message": f"Budget is around {currency} 50000."},
                {"label": f"{currency} 90k+", "message": f"Budget is above {currency} 90000."},
            ]
        return [
            {"label": f"{currency} 60k", "message": f"Budget is around {currency} 60000 each."},
            {"label": f"{currency} 90k", "message": f"Budget is around {currency} 90000 each."},
            {"label": f"{currency} 130k+", "message": f"Budget is above {currency} 130000 each."},
        ]
    if field == "budget_scope":
        project_label = "Total project" if quantity > 1 else "Total budget"
        return [
            {"label": "Per device", "message": "Treat the budget as per device."},
            {"label": project_label, "message": "Treat the budget as the total project budget."},
            {"label": "I'm not sure yet", "action": "skip"},
        ]
    if field == "team_size":
        suffix = "users or endpoints" if category in {"servers", "networking"} else "users"
        return [
            {"label": "Up to 5", "message": f"We need this for up to 5 {suffix}."},
            {"label": "6 to 20", "message": f"We need this for about 12 {suffix}."},
            {"label": "20+", "message": f"We need this for about 30 {suffix}."},
        ]
    if field == "growth_expectation":
        return [
            {"label": "Stable", "message": "Assume a stable team with no major growth."},
            {"label": "Moderate growth", "message": "Assume moderate growth over the next year."},
            {"label": "Rapid growth", "message": "Assume rapid growth and leave more headroom."},
        ]
    if field == "performance_priority":
        return [
            {"label": "Cost", "message": "Optimize for cost."},
            {"label": "Balanced", "message": "Keep it balanced."},
            {"label": "Performance", "message": "Optimize for performance."},
        ]
    return [
        {"label": "Tell me more", "message": "Let me add a bit more detail to the requirement."},
        {"label": "Use a safe default", "action": "skip"},
        {"label": "I'm not sure yet", "message": "I'm not sure yet. Please use a reasonable default and continue."},
    ]


def skip_clarification_with_assumption(snapshot):
    result = snapshot.get("result") or {}
    readiness = result.get("readiness") or {}
    target_profile = result.get("target_profile") or {}
    requirements = result.get("requirements") or {}
    field = readiness.get("highest_priority_missing_field") or ""
    categories = target_profile.get("categories") or []
    inferred_category = (result.get("requirements") or {}).get("preferred_category") or (categories[0] if categories else "laptops")
    quantity = int(requirements.get("quantity") or requirements.get("team_size") or 0)

    if field in {"preferred_category", "category_or_workload"}:
        changes = {"preferred_category": inferred_category}
    elif field in {"workload_or_application_profile", "application_profile"}:
        default_workload = {
            "networking": ["network_connectivity"],
            "servers": ["server_infrastructure"],
            "desktops": ["office_productivity"],
        }.get(inferred_category, ["office_productivity"])
        changes = {"workload_types": default_workload}
    elif field == "budget":
        default_budget = {
            "networking": 4000,
            "servers": 18000,
            "desktops": 4500,
        }.get(inferred_category, 5000)
        changes = {"budget": default_budget}
    elif field == "budget_scope":
        default_scope = "project_total" if quantity > 1 else "per_unit"
        changes = {"budget_scope": default_scope}
    elif field == "team_size":
        changes = {"team_size": 25 if inferred_category in {"networking", "servers"} else 10}
    elif field == "growth_expectation":
        changes = {"growth_expectation": "moderate_growth"}
    elif field == "performance_priority":
        changes = {"performance_priority": "balanced"}
    else:
        changes = {}

    update_preferences(
        changes,
        note="Proceeded with a safe assumption so the recommendation can continue. You can edit it later.",
    )


def refresh_snapshot():
    service = st.session_state.service
    session_id = st.session_state.active_session_id
    store_id = st.session_state.store_id
    service.set_store_id(session_id, store_id)
    st.session_state.snapshot = collect_snapshot(service, session_id, store_id)
    cache_active_session_state(snapshot=st.session_state.snapshot)


def cache_active_session_state(snapshot=None):
    session_id = str(st.session_state.get("active_session_id") or "").strip()
    if not session_id:
        return
    if "messages" in st.session_state:
        st.session_state.session_messages_map[session_id] = deepcopy(st.session_state.messages)
    if snapshot is not None:
        st.session_state.session_snapshots[session_id] = deepcopy(snapshot)


def clear_cached_session_state(session_id):
    session_id = str(session_id or "").strip()
    if not session_id:
        return
    st.session_state.get("session_messages_map", {}).pop(session_id, None)
    st.session_state.get("session_snapshots", {}).pop(session_id, None)
    st.session_state.get("session_payloads", {}).pop(session_id, None)


def ensure_cached_session_loaded(service, session_id):
    session_id = str(session_id or "").strip()
    if not session_id:
        return False
    cached_snapshot = deepcopy((st.session_state.get("session_snapshots") or {}).get(session_id) or {})
    cached_messages = deepcopy((st.session_state.get("session_messages_map") or {}).get(session_id) or [])
    cached_payload = deepcopy((st.session_state.get("session_payloads") or {}).get(session_id) or {})
    cached_prefs = deepcopy((cached_snapshot.get("preferences") or {}) or cached_payload.get("extracted_schema") or {})

    if not cached_snapshot and not cached_messages and not cached_payload and not cached_prefs:
        return False

    service.set_store_id(session_id, st.session_state.store_id)
    if cached_prefs:
        service.session_answers[session_id] = dict(cached_prefs)
    if cached_messages:
        service.session_histories[session_id] = [
            {"role": str(item.get("role") or "assistant"), "content": str(item.get("content") or "")}
            for item in cached_messages
        ]
        st.session_state.messages = cached_messages
    elif "messages" not in st.session_state:
        st.session_state.messages = []

    if cached_snapshot:
        st.session_state.snapshot = cached_snapshot
    else:
        st.session_state.snapshot = collect_snapshot(service, session_id, st.session_state.store_id)

    cache_active_session_state(snapshot=st.session_state.snapshot)
    return True


def ensure_runtime(force_reset=False):
    config = {
        "provider": st.session_state.provider,
        "api_key": st.session_state.api_key,
        "model": st.session_state.model,
        "store_id": st.session_state.store_id,
        "disable_explanation_llm": st.session_state.disable_explanation_llm,
        "catalog_size": st.session_state.catalog_size,
    }
    signature = json.dumps(config, sort_keys=True)
    if not force_reset and st.session_state.get("runtime_signature") == signature and "service" in st.session_state:
        service = st.session_state.service
        session_id = st.session_state.get("active_session_id") or f"manual-{uuid.uuid4().hex[:8]}"
        service.set_store_id(session_id, config["store_id"])
        ensure_cached_session_loaded(service, session_id)
        return

    apply_runtime_env(
        config["provider"],
        config["api_key"],
        config["model"],
        config["disable_explanation_llm"],
    )
    service = build_procurement_chat_runtime(catalog_size=config["catalog_size"])
    session_id = st.session_state.get("active_session_id") or f"manual-{uuid.uuid4().hex[:8]}"
    st.session_state.active_session_id = session_id
    service.set_store_id(session_id, config["store_id"])
    st.session_state.service = service
    st.session_state.runtime_signature = signature
    st.session_state.last_review_request_id = ""
    st.session_state.studio_mode = ""
    st.session_state.selected_product_id = ""
    st.session_state.selected_product_name = ""
    if not force_reset and ensure_cached_session_loaded(service, session_id):
        return
    welcome = service.get_response("", session_id)
    st.session_state.messages = [{"role": "assistant", "content": welcome}]
    refresh_snapshot()


def append_message(role, content):
    st.session_state.messages.append({"role": role, "content": str(content or "").strip()})
    cache_active_session_state()


def send_message(message):
    text = str(message or "").strip()
    if not text:
        return
    ensure_runtime()
    service = st.session_state.service
    session_id = st.session_state.active_session_id
    service.set_store_id(session_id, st.session_state.store_id)
    append_message("user", text)
    payload = service.get_response_payload(text, session_id)
    st.session_state.session_payloads[session_id] = deepcopy(payload)
    append_message("assistant", payload.get("response", ""))
    refresh_snapshot()


def submit_message_and_route(message, page_key=None):
    send_message(message)
    if page_key:
        switch_to_page(page_key)
    st.rerun()


def update_preferences(changes, note="Updated assumptions and reran the recommendation."):
    ensure_runtime()
    service = st.session_state.service
    session_id = st.session_state.active_session_id
    prefs = deepcopy(service.session_answers.get(session_id, {}))
    for key, value in changes.items():
        if value in (None, ""):
            prefs.pop(key, None)
        else:
            prefs[key] = value
    if "preferred_category" in changes:
        prefs["category"] = prefs.get("preferred_category")
    if "workload_types" in changes:
        prefs["workloads"] = list(prefs.get("workload_types") or [])
    if "requested_ram" in changes:
        if prefs.get("requested_ram"):
            prefs["specifications.ram_size"] = prefs["requested_ram"]
        else:
            prefs.pop("specifications.ram_size", None)
    if "requested_storage" in changes:
        if prefs.get("requested_storage"):
            prefs["specifications.storage_size"] = prefs["requested_storage"]
        else:
            prefs.pop("specifications.storage_size", None)
    prefs["store_id"] = st.session_state.store_id
    prefs["channel"] = "streamlit_chat"
    if not prefs.get("raw_chat"):
        prefs["raw_chat"] = "Structured procurement brief"
    service.session_answers[session_id] = prefs
    st.session_state.session_payloads.pop(session_id, None)
    append_message("assistant", note)
    refresh_snapshot()


def submit_expert_review(notes):
    ensure_runtime()
    service = st.session_state.service
    snapshot = st.session_state.get("snapshot") or {}
    result = snapshot.get("result") or {}
    if not result.get("expert_review_eligible"):
        return
    feature_flag_service = getattr(service.recommendation_service, "feature_flag_service", None)
    if feature_flag_service and not feature_flag_service.is_enabled("expert_review"):
        return
    payload = {
        "session_id": st.session_state.active_session_id,
        "decision_trace_id": str(result.get("decision_trace_id") or ""),
        "reason": str(result.get("meta", {}).get("expert_review_reason") or result.get("fallback_reason") or "manual_review"),
        "notes": str(notes or "").strip(),
    }
    serializer = ProcurementExpertReviewRequestSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    validated = dict(serializer.validated_data)
    review = ProcurementExpertReviewRequest.objects.create(
        request_id=str(uuid.uuid4()),
        session_id=str(validated.get("session_id") or "").strip(),
        decision_trace_id=str(validated.get("decision_trace_id") or "").strip(),
        user_id=str(st.session_state.review_user_id or ""),
        business_id=str(st.session_state.review_business_id or ""),
        reason=str(validated.get("reason") or "").strip(),
        notes=str(validated.get("notes") or "").strip(),
        meta={"source": "streamlit_prototype"},
    )
    st.session_state.last_review_request_id = review.request_id


def render_app_css():
    st.markdown(APP_CSS, unsafe_allow_html=True)


def initialize_session_defaults():
    st.session_state.setdefault("provider", "groq")
    st.session_state.setdefault("model", DEFAULT_PROVIDER_MODELS["groq"])
    st.session_state.setdefault("api_key", "")
    st.session_state.setdefault("store_id", "")
    st.session_state.setdefault("catalog_size", "corrected_json")
    st.session_state.setdefault("disable_explanation_llm", True)
    st.session_state.setdefault("active_session_id", f"manual-{uuid.uuid4().hex[:8]}")
    st.session_state.setdefault("session_id_input", st.session_state.active_session_id)
    st.session_state.setdefault("review_user_id", "")
    st.session_state.setdefault("review_business_id", "")
    st.session_state.setdefault("studio_mode", "")
    st.session_state.setdefault("selected_product_id", "")
    st.session_state.setdefault("selected_product_name", "")
    st.session_state.setdefault("session_messages_map", {})
    st.session_state.setdefault("session_snapshots", {})
    st.session_state.setdefault("session_payloads", {})


def page_target(page_key):
    return f"streamlit_pages/{PAGE_FILES[page_key].name}"


def switch_to_page(page_key):
    st.switch_page(page_target(page_key))


def open_studio(mode=""):
    st.session_state.studio_mode = str(mode or "").strip()
    switch_to_page("studio")


def open_product_detail(product_id, product_name=""):
    st.session_state.selected_product_id = str(product_id or "")
    st.session_state.selected_product_name = str(product_name or "")


def find_recommendation(result, product_id):
    product_id = str(product_id or "").strip()
    if not product_id:
        return None
    recommendations = list((result or {}).get("recommendations") or [])
    for item in recommendations:
        if str(item.get("product_id") or "") == product_id:
            return item
    for group in (result or {}).get("recommendation_groups") or []:
        for item in group.get("recommendations") or []:
            if str(item.get("product_id") or "") == product_id:
                found = dict(item)
                found["recommendation_group_label"] = group.get("label")
                found["recommendation_group_id"] = group.get("group_id")
                return found
    return None


def is_top_recommendation_selected(result, product_id):
    product_id = str(product_id or "").strip()
    if not product_id:
        return False
    recommendations = list((result or {}).get("recommendations") or [])
    if recommendations and str(recommendations[0].get("product_id") or "") == product_id:
        return True
    for group in (result or {}).get("recommendation_groups") or []:
        group_recommendations = group.get("recommendations") or []
        if group_recommendations and str(group_recommendations[0].get("product_id") or "") == product_id:
            return True
    return False


def bootstrap_page():
    render_app_css()
    initialize_session_defaults()
    render_sidebar()
    ensure_runtime()
    return st.session_state.get("snapshot") or {}


def render_sidebar():
    st.sidebar.header("Procurement Advisor")
    st.sidebar.caption("Guided procurement prototype on top of the current backend contract.")
    with st.sidebar.expander("Runtime settings", expanded=False):
        st.selectbox("LLM provider", ["groq", "gemini"], key="provider")
        if not st.session_state.get("model"):
            st.session_state.model = DEFAULT_PROVIDER_MODELS[st.session_state.provider]
        st.text_input("Model", key="model")
        st.text_input("API key", type="password", key="api_key")
        st.text_input("Store id (ignored for recommendations)", key="store_id")
        st.selectbox("Catalog source", CATALOG_SIZE_OPTIONS, key="catalog_size")
        st.caption(
            "Use `corrected_json` for the INR fixture catalog, `mongo` for the live MongoDB catalog "
            "(via `CATALOG_MONGODB_URI` + `CATALOG_DB_NAME`), or the legacy fake datasets for regression checks."
        )
        st.checkbox("Disable explanation LLM calls", key="disable_explanation_llm")
        st.text_input("Session id", key="session_id_input")
        st.text_input("Review user id", key="review_user_id")
        st.text_input("Review business id", key="review_business_id")
        if st.button("Apply / restart session", use_container_width=True):
            session_id = st.session_state.session_id_input.strip() or f"manual-{uuid.uuid4().hex[:8]}"
            clear_cached_session_state(session_id)
            st.session_state.active_session_id = session_id
            ensure_runtime(force_reset=True)
            st.rerun()
        if st.button("New session id", use_container_width=True):
            new_session_id = f"manual-{uuid.uuid4().hex[:8]}"
            st.session_state.active_session_id = new_session_id
            st.session_state.session_id_input = new_session_id
            clear_cached_session_state(new_session_id)
            ensure_runtime(force_reset=True)
            st.rerun()


def render_hero(snapshot):
    st.markdown(
        """
        <div class='proc-hero proc-hero--intake'>
            <div class='proc-kicker'>SMB Procurement Assistant</div>
            <h1 class='proc-title'>What do you need?</h1>
            <p class='proc-copy'>
                Describe the requirement in plain language. We infer most of it automatically, ask at most one
                clarification if needed, and then return explainable recommendations.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_prompt_chips(route_to=None):
    st.markdown("<div class='proc-mini-label' style='margin-bottom:0.55rem;'>Suggestions</div>", unsafe_allow_html=True)
    cols = st.columns(4)
    for index, prompt in enumerate(QUICK_PROMPTS):
        with cols[index % len(cols)]:
            if st.button(prompt["label"], key=f"quick-{index}", use_container_width=True):
                submit_message_and_route(prompt["prompt"], route_to)


def render_summary(snapshot):
    result = snapshot.get("result") or {}
    if not result:
        render_section_header(
            "System summary",
            "Once you submit a brief, this panel shows what the engine understood, what it assumed, and how confident it is.",
            eyebrow="Transparency",
        )
        render_empty_state("No recommendation has been evaluated yet. Enter a procurement brief to populate the summary.")
        return

    req = result.get("requirements") or {}
    readiness = result.get("readiness") or {}
    target_profile = result.get("target_profile") or {}
    fallback_reason = result.get("fallback_reason")
    confidence = str(readiness.get("decision_confidence_band") or "Unknown").title()

    with st.container(border=True):
        render_section_header(
            "System summary",
            "What the engine understood, what it assumed, and the current recommendation state.",
            eyebrow="Transparency",
        )
        render_badges(
            [
                (f"Confidence {confidence}", confidence_tone(confidence)),
                (f"{len(result.get('recommendations') or [])} options", "info"),
                (f"{str(result.get('compatibility_report', {}).get('scope') or 'item').title()} compatibility", "info"),
                (fallback_label(fallback_reason) or "", "rose" if fallback_reason else "neutral"),
            ]
        )
        metric_cols = st.columns(3)
        metric_cols[0].metric("Confidence", confidence)
        metric_cols[1].metric("Recommendations", len(result.get("recommendations") or []))
        metric_cols[2].metric("Compatibility scope", str(result.get("compatibility_report", {}).get("scope") or "item").title())

        understood_col, assumptions_col = st.columns(2)
        with understood_col:
            st.markdown("**We understood**")
            st.write(f"- Category: {req.get('preferred_category') or join_items(target_profile.get('categories'))}")
            st.write(f"- Use case: {join_items(req.get('workloads') or req.get('workload_types'))}")
            st.write(f"- Quantity / scale: {req.get('quantity') or req.get('team_size') or 'Not captured'}")
            st.write(f"- Budget: {req.get('budget') or 'Not captured'} {req.get('currency') or ''}".strip())
            if result.get("summary"):
                render_note(str(result.get("summary")), tone="info")
        with assumptions_col:
            assumptions = as_list(result.get("assumptions"))
            if assumptions:
                render_reason_box("Assumptions", assumptions[:5], tone="warm")
            else:
                render_note("No assumptions were needed for this result.", tone="warm")
            if fallback_reason:
                render_note(f"Fallback state: {fallback_label(fallback_reason) or fallback_reason}", tone="rose")


def render_clarification(snapshot):
    result = snapshot.get("result") or {}
    if not result:
        return
    next_question = result.get("next_question")
    if not next_question:
        return
    readiness = result.get("readiness") or {}
    question_candidates = readiness.get("question_candidates") or []
    render_section_header(
        "One quick clarification",
        "We only need one answer to continue. You can also skip and let the system proceed with a safe assumption.",
        eyebrow="Clarification",
    )
    st.markdown(
        f"""
        <div class='proc-clarify-card'>
            <div class='proc-kicker'>Minimal friction promise</div>
            <div class='proc-clarify-card__question'>{html.escape(str(next_question))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_badges([("1 question only", "warm"), ("Recommendations paused", "teal")])
    options = clarification_quick_answers(snapshot)
    if options:
        if clarification_supports_tool_multiselect(snapshot):
            st.caption("Choose all that apply. Tool-level answers usually map to hardware needs more accurately than broad work buckets.")
            selection_key = clarification_multiselect_key(snapshot, "clarify")
            selected_labels = st.multiselect(
                "Tools that matter most",
                [option["label"] for option in options],
                key=selection_key,
                placeholder="Select one or more tools",
                label_visibility="collapsed",
            )
            if st.button(
                "Use selected tools",
                key="clarify-tools-submit",
                use_container_width=True,
                type="primary",
                disabled=not selected_labels,
            ):
                message = build_tool_profile_message(options, selected_labels)
                if message:
                    st.session_state.pop(selection_key, None)
                    submit_message_and_route(message, "results")
        else:
            option_cols = st.columns(len(options))
            for index, option in enumerate(options):
                with option_cols[index]:
                    if st.button(option["label"], key=f"clarify-option-{index}", use_container_width=True):
                        if option.get("action") == "skip":
                            skip_clarification_with_assumption(snapshot)
                            st.rerun()
                        else:
                            submit_message_and_route(option.get("message"), "results")
    action_cols = st.columns([1, 1.4])
    if action_cols[0].button("Skip for now", use_container_width=True):
        skip_clarification_with_assumption(snapshot)
        st.rerun()
    clarification_text = action_cols[1].text_input(
        "Or answer in your own words",
        key="clarification-freeform",
        placeholder=clarification_freeform_placeholder(snapshot),
    )
    if clarification_text.strip() and st.button(
        "Send answer",
        use_container_width=True,
        key="clarification-send",
        type="primary",
    ):
        submit_message_and_route(clarification_text, "results")

    candidate_labels = []
    for item in question_candidates[:3]:
        if isinstance(item, dict):
            candidate_labels.append(item.get("key") or item.get("label") or item.get("question"))
        else:
            candidate_labels.append(str(item))
    candidate_labels = [label for label in candidate_labels if label]
    if candidate_labels:
        st.caption(f"Focus area: {join_items(candidate_labels)}")


def render_recommendation_card(item, best=False):
    title = str(item.get("name") or "Recommendation")
    reason_block, tradeoffs = normalize_reason_columns(
        as_list(item.get("reasons")),
        as_list(item.get("trade_offs")),
        "No additional fit rationale was reported.",
        "No additional trade-offs were reported.",
    )
    header_badges = [
        ("Best match" if best else "Alternative", "teal" if best else "neutral"),
        (fit_label(item.get("fit_status")), fit_tone(item.get("fit_status"))),
    ]
    if item.get("recommendation_group_label"):
        header_badges.append((item.get("recommendation_group_label"), "info"))
    if item.get("stock_quantity") is not None:
        header_badges.append((f"Stock {item.get('stock_quantity')}", "info"))
    if item.get("warranty_years"):
        header_badges.append((f"{item.get('warranty_years')}y warranty", "info"))

    with st.container(border=True):
        if best:
            render_note("This is the main recommendation to focus on first.", tone="teal")
        render_badges(header_badges)
        render_section_header(
            title,
            "Highlighted as the strongest available match right now." if best else "Valid alternative kept for comparison and re-run decisions.",
            eyebrow="Recommendation" if best else "Other option",
        )

        price_col, support_col, availability_col = st.columns([1.4, 1, 1])
        with price_col:
            st.markdown(f"<div class='proc-price'>{html.escape(format_price(item.get('price'), item.get('currency')))}</div>", unsafe_allow_html=True)
            seller_bits = [item.get("manufacturer"), item.get("seller")]
            seller_line = " | ".join(bit for bit in seller_bits if bit)
            if seller_line:
                st.caption(seller_line)
        with support_col:
            st.metric("Support", item.get("support_score") if item.get("support_score") is not None else "n/a")
        with availability_col:
            stock_value = item.get("stock_quantity")
            st.metric("Stock", stock_value if stock_value is not None else "Unknown")

        spec_badges = []
        if item.get("processor"):
            spec_badges.append((f"CPU {item.get('processor')}", "info"))
        if item.get("ram_gb"):
            spec_badges.append((f"RAM {item.get('ram_gb')}GB", "info"))
        if item.get("storage_gb"):
            spec_badges.append((f"Storage {item.get('storage_gb')}GB", "info"))
        if spec_badges:
            render_badges(spec_badges)

        detail_cols = st.columns(2)
        with detail_cols[0]:
            render_reason_box("Why this works", reason_block[:3], tone="warm")
        with detail_cols[1]:
            render_reason_box("Trade-offs / watch-outs", tradeoffs[:3], tone="rose")

        if item.get("explanation"):
            render_note(str(item.get("explanation")), tone="warm")

        action_cols = st.columns(2)
        if action_cols[0].button(
            "View details",
            key=f"detail-{item.get('product_id')}-{best}",
            use_container_width=True,
            type="primary" if best else "secondary",
        ):
            open_product_detail(item.get("product_id"), item.get("name"))
            st.rerun()
        if action_cols[1].button(
            "Compare this",
            key=f"compare-{item.get('product_id')}-{best}",
            use_container_width=True,
        ):
            open_product_detail(item.get("product_id"), item.get("name"))
            open_studio("compare")


def render_compact_recommendation_card(item, index_key=""):
    reason_block = as_list(item.get("reasons"))
    st.markdown(
        f"""
        <div class='proc-compact-card'>
            <div class='proc-mini-label'>{html.escape(fit_label(item.get("fit_status")))}</div>
            <div class='proc-compact-card__title'>{html.escape(str(item.get("name") or "Recommendation"))}</div>
            <div class='proc-compact-card__copy'>{html.escape(format_price(item.get("price"), item.get("currency")))}</div>
            <div class='proc-compact-card__copy'>{html.escape(str(reason_block[0] if reason_block else "Valid alternative that ranked lower than the top match."))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    if cols[0].button("Details", key=f"compact-detail-{index_key}", use_container_width=True):
        open_product_detail(item.get("product_id"), item.get("name"))
        st.rerun()
    if cols[1].button("Compare", key=f"compact-compare-{index_key}", use_container_width=True):
        open_product_detail(item.get("product_id"), item.get("name"))
        open_studio("compare")


def render_recommendations(snapshot):
    result = snapshot.get("result") or {}
    if not result:
        return
    recs = result.get("recommendations") or []
    recommendation_groups = result.get("recommendation_groups") or []
    with st.container(border=True):
        render_section_header(
            "Recommendations",
            "The result set below stays within the current backend contract: item-level compatibility first, then policy, then ranking.",
            eyebrow="Decision output",
        )
        if not recs:
            render_badges(
                [
                    (fallback_label(result.get("fallback_reason")) or "No recommendation yet", "rose"),
                    ("Expert review available" if result.get("expert_review_eligible") else "", "rose"),
                ]
            )
            render_empty_state(fallback_label(result.get("fallback_reason")) or "No recommendation has been produced yet.")
            return
        if result.get("fallback_reason"):
            render_note(f"Fallback mode: {fallback_label(result.get('fallback_reason')) or result.get('fallback_reason')}", tone="rose")
    if recommendation_groups:
        for index, group in enumerate(recommendation_groups):
            group_recs = group.get("recommendations") or []
            if not group_recs:
                continue
            render_section_header(
                group.get("label") or f"Intent {index + 1}",
                group.get("summary") or "Grouped recommendation output for this intent.",
                eyebrow="Recommendation group",
            )
            top_item = dict(group_recs[0])
            top_item["recommendation_group_label"] = group.get("label")
            render_recommendation_card(top_item, best=True)
            others = list(group_recs[1:])
            if others:
                cols = st.columns(min(3, len(others)))
                for alt_index, item in enumerate(others):
                    alt_item = dict(item)
                    alt_item["recommendation_group_label"] = group.get("label")
                    with cols[alt_index % len(cols)]:
                        render_compact_recommendation_card(alt_item, index_key=f"{group.get('group_id')}-{alt_index}")
        return

    render_recommendation_card(recs[0], best=True)
    others = recs[1:]
    if others:
        render_section_header(
            "Other valid options",
            "These passed item compatibility and policy checks but ranked lower than the highlighted recommendation.",
            eyebrow="Compare",
        )
        cols = st.columns(min(3, len(others)))
        for index, item in enumerate(others):
            with cols[index % len(cols)]:
                render_compact_recommendation_card(item, index_key=index)


def render_recommendation_detail(snapshot):
    result = snapshot.get("result") or {}
    product_id = st.session_state.get("selected_product_id") or ""
    if not result or not product_id:
        return
    item = find_recommendation(result, product_id)
    if not item:
        return

    meta = result.get("meta") or {}
    compatibility_rejections = meta.get("compatibility_rejections_sample") or []
    policy_rejections = meta.get("policy_rejections_sample") or []
    selected_reasons, selected_tradeoffs = normalize_reason_columns(
        as_list(item.get("reasons")),
        as_list(item.get("trade_offs")),
        "No additional selection rationale was reported.",
        "No additional trade-offs were reported.",
        min_items=2,
        max_items=4,
    )
    with st.container(border=True):
        render_section_header(
            f"Why {item.get('name')} was selected",
            "A deeper explanation view for the currently selected recommendation.",
            eyebrow="Detail",
        )
        info_cols = st.columns(3)
        info_cols[0].metric("Price", format_price(item.get("price"), item.get("currency")))
        info_cols[1].metric("Stock", item.get("stock_quantity") if item.get("stock_quantity") is not None else "Unknown")
        info_cols[2].metric("Support", item.get("support_score") if item.get("support_score") is not None else "n/a")

        left, right = st.columns(2)
        with left:
            render_reason_box("Why selected", selected_reasons[:4], tone="warm")
            if item.get("explanation"):
                render_note(str(item.get("explanation")), tone="warm")
        with right:
            render_reason_box("Trade-offs / warnings", selected_tradeoffs[:4], tone="rose")
            st.markdown("**Availability**")
            st.write(f"- Seller: {item.get('seller') or 'Not captured'}")
            st.write(f"- Warranty: {item.get('warranty_years') or 'Unknown'} year(s)")

        st.markdown("**Why others were not selected**")
        if compatibility_rejections or policy_rejections:
            if compatibility_rejections:
                st.write("- Some candidates failed item compatibility or required metadata checks.")
            if policy_rejections:
                st.write("- Some candidates passed compatibility but were screened out by policy constraints.")
            for rejected in (compatibility_rejections + policy_rejections)[:4]:
                reasons = rejected.get("reason_codes") or rejected.get("reasons") or []
                st.write(f"- {rejected.get('name')}: {join_items(reasons)}")
        else:
            st.write("- Lower-ranked valid options remained available but scored below this recommendation.")
        if st.button("Close detail", key="close-detail", use_container_width=False):
            st.session_state.selected_product_id = ""
            st.session_state.selected_product_name = ""
            st.rerun()


def render_results_actions(snapshot):
    result = snapshot.get("result") or {}
    if not result or not (result.get("recommendations") or result.get("expert_review_eligible")):
        return
    with st.container(border=True):
        render_section_header(
            "Next step",
            "Choose what you want to do next. These actions open only when you ask for them.",
            eyebrow="Actions",
        )
        cols = st.columns(3)
        if cols[0].button("Compare", use_container_width=True, key="results-compare"):
            open_studio("compare")
        if cols[1].button("Modify / re-run", use_container_width=True, key="results-modify"):
            open_studio("modify")
        with cols[2]:
            st.markdown(
                """
                <div class='proc-inline-callout proc-inline-callout--rose'>
                    <div class='proc-inline-callout__title'>Escalation path</div>
                    <div class='proc-inline-callout__copy'>Use expert help when the fit, confidence, or fallback state still needs a human decision.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(
                "Request expert help",
                use_container_width=True,
                key="results-expert",
                disabled=not result.get("expert_review_eligible"),
            ):
                open_studio("expert")


def render_rejection_group(title, items):
    with st.container(border=True):
        st.markdown(f"<div class='proc-mini-label'>{html.escape(title)}</div>", unsafe_allow_html=True)
        st.markdown("<div class='proc-divider'></div>", unsafe_allow_html=True)
        for item in items:
            reasons = item.get("reason_codes") or item.get("reasons") or []
            st.write(f"**{item.get('name')}**")
            st.write(f"- {join_items(reasons)}")


def render_rejections(snapshot):
    result = snapshot.get("result") or {}
    meta = result.get("meta") or {}
    compatibility = meta.get("compatibility_rejections_sample") or []
    policy = meta.get("policy_rejections_sample") or []
    if not compatibility and not policy:
        return

    render_section_header(
        "Rejected before ranking",
        "These were screened out before the ranking stage. That is different from valid options that simply scored lower.",
        eyebrow="Transparency",
    )
    if compatibility and policy:
        left, right = st.columns(2)
        with left:
            render_rejection_group("Item compatibility rejects", compatibility)
        with right:
            render_rejection_group("Policy rejects", policy)
        return
    if compatibility:
        render_rejection_group("Item compatibility rejects", compatibility)
    if policy:
        render_rejection_group("Policy rejects", policy)


def render_transparency_panel(snapshot):
    result = snapshot.get("result") or {}
    if not result:
        return
    meta = result.get("meta") or {}
    compatibility = meta.get("compatibility_rejections_sample") or []
    policy = meta.get("policy_rejections_sample") or []
    trace_id = str(result.get("decision_trace_id") or "")
    with st.container(border=True):
        render_section_header(
            "Why this result happened",
            "A lightweight user-facing view of the current decision trace: what path ran, what was filtered out, and what state the recommendation is in.",
            eyebrow="Transparency",
        )
        render_badges(
            [
                (f"Trace {trace_id[:8]}" if trace_id else "", "neutral"),
                (f"{str(result.get('compatibility_report', {}).get('scope') or 'item').title()} compatibility", "info"),
                (fallback_label(result.get("fallback_reason")) or "Standard path", "rose" if result.get("fallback_reason") else "info"),
            ]
        )
        metric_cols = st.columns(3)
        metric_cols[0].metric("Compatibility rejects", len(compatibility))
        metric_cols[1].metric("Policy rejects", len(policy))
        metric_cols[2].metric("Valid options", len(result.get("recommendations") or []))
        st.markdown("**Decision path**")
        st.write("- Intake and requirement extraction completed")
        st.write("- Item-level compatibility checked before ranking")
        st.write("- Policy screening applied before final scoring")
        st.write("- Ranking produced the current recommendation set")


def render_guidance(snapshot):
    prefs = snapshot.get("preferences") or {}
    result = snapshot.get("result") or {}
    sections = build_narrowing_guidance(prefs, result.get("readiness") or {})
    if not sections:
        return
    render_section_header(
        "Guided refinement",
        "These are safe next moves generated from the current context. They let the user adjust direction without opening a heavy form.",
        eyebrow="Next actions",
    )
    for section_index, section in enumerate(sections):
        with st.container(border=True):
            st.write(f"**{section['title']}**")
            if section.get("description"):
                st.caption(section["description"])
            cols = st.columns(2)
            for option_index, option in enumerate(section.get("options") or []):
                with cols[option_index % 2]:
                    if st.button(option["label"], key=f"guide-{section_index}-{option_index}", use_container_width=True):
                        send_message(option["message"])
                        st.rerun()


def render_conversation():
    messages = st.session_state.get("messages", [])
    user_messages = [message for message in messages if message.get("role") == "user"]
    if not user_messages:
        return
    with st.expander("Recent conversation", expanded=False):
        render_section_header(
            "Conversation",
            "The recommendation flow stays chat-first. You can continue refining here without leaving the result context.",
            eyebrow="Chat",
        )
        for message in messages[-3:]:
            role = "assistant" if message.get("role") == "assistant" else "user"
            with st.chat_message(role):
                st.write(message.get("content") or "")


def render_compare(snapshot):
    result = snapshot.get("result") or {}
    recs = list(result.get("recommendations") or [])
    if not recs:
        for group in result.get("recommendation_groups") or []:
            for item in group.get("recommendations") or []:
                merged_item = dict(item)
                merged_item["recommendation_group_label"] = group.get("label")
                recs.append(merged_item)
    with st.container(border=True):
        render_section_header(
            "Compare",
            "Use side-by-side comparison to decide between the current valid options.",
            eyebrow="Decision support",
        )
        if len(recs) < 2:
            render_empty_state("Comparison becomes available when at least two recommendations are present.")
            return
        ranking_order = {str(item.get("product_id") or ""): index for index, item in enumerate(recs)}
        choices = {f"{item['name']} ({fit_label(item.get('fit_status'))})": item for item in recs}
        selected = st.multiselect("Choose 2-3 options", list(choices.keys()), max_selections=3)
        if len(selected) < 2:
            st.caption("Select at least two recommendations to compare.")
            return
        selected_items = [choices[label] for label in selected]
        selected_items.sort(key=lambda item: ranking_order.get(str(item.get("product_id") or ""), 999))
        render_compare_table(selected_items)
        st.markdown("**Select an option to proceed**")
        select_cols = st.columns(min(3, len(selected_items)))
        for index, item in enumerate(selected_items):
            with select_cols[index % len(select_cols)]:
                if st.button(f"Choose {item.get('name')}", key=f"choose-compare-{index}", use_container_width=True):
                    open_product_detail(item.get("product_id"), item.get("name"))
                    switch_to_page("results")


def render_modify(snapshot):
    prefs = snapshot.get("preferences") or {}
    with st.container(border=True):
        render_section_header(
            "Modify and re-run",
            "Tell the assistant what changed first. Quick adjustments are here for common rerun moves, and advanced editing stays tucked away.",
            eyebrow="Refine",
        )
        render_note("Warm cues in this section mean the recommendation may change through assumptions, budget trade-offs, or preference shifts.", tone="warm")
        st.markdown("**Natural-language change**")
        modify_text = st.text_area(
            "Tell the assistant what changed",
            key="modify-text-area",
            placeholder="Increase budget to 7500 and optimize for stronger performance",
            height=100,
        )
        if st.button(
            "Re-run from this change",
            use_container_width=True,
            key="send-modification",
            type="primary",
        ) and modify_text.strip():
            send_message(modify_text)
            switch_to_page("results")

        st.markdown("**Quick adjustments**")
        qcols = st.columns(3)
        with qcols[0]:
            render_quick_label("Budget headroom", "warm")
            if st.button("Budget +15%", use_container_width=True):
                current = int(prefs.get("budget") or 0)
                if current:
                    update_preferences({"budget": int(round(current * 1.15))})
                    switch_to_page("results")
        with qcols[1]:
            render_quick_label("Cost lens", "info")
            if st.button("Optimize for cost", use_container_width=True):
                update_preferences({"performance_priority": "cost"})
                switch_to_page("results")
        with qcols[2]:
            render_quick_label("Performance", "teal")
            if st.button("Optimize for performance", use_container_width=True):
                update_preferences({"performance_priority": "performance"})
                switch_to_page("results")

        with st.expander("Edit all assumptions", expanded=False):
            st.caption("Use the advanced editor only when the natural-language change or quick actions are not enough.")
            with st.form("modify_form"):
                category = st.selectbox(
                    "Category",
                    CATEGORY_OPTIONS,
                    index=CATEGORY_OPTIONS.index((prefs.get("preferred_category") or "") if (prefs.get("preferred_category") or "") in CATEGORY_OPTIONS else ""),
                )
                workloads = st.multiselect(
                    "Workloads",
                    WORKLOAD_OPTIONS,
                    default=[w for w in (prefs.get("workload_types") or []) if w in WORKLOAD_OPTIONS],
                )
                budget = st.number_input("Budget", min_value=0, value=int(prefs.get("budget") or 0), step=100)
                team_size = st.number_input("Team size", min_value=0, value=int(prefs.get("team_size") or 0), step=1)
                quantity = st.number_input("Quantity", min_value=0, value=int(prefs.get("quantity") or 0), step=1)
                performance_priority = st.selectbox(
                    "Priority",
                    ["", "cost", "balanced", "performance"],
                    index=["", "cost", "balanced", "performance"].index(str(prefs.get("performance_priority") or "")) if str(prefs.get("performance_priority") or "") in ["", "cost", "balanced", "performance"] else 0,
                )
                support_expectation = st.selectbox(
                    "Support",
                    ["", "basic", "business", "premium"],
                    index=["", "basic", "business", "premium"].index(str(prefs.get("support_expectation") or "")) if str(prefs.get("support_expectation") or "") in ["", "basic", "business", "premium"] else 0,
                )
                availability_need = st.selectbox(
                    "Availability",
                    ["", "standard", "soon", "urgent", "in_stock_now"],
                    index=["", "standard", "soon", "urgent", "in_stock_now"].index(str(prefs.get("availability_need") or "")) if str(prefs.get("availability_need") or "") in ["", "standard", "soon", "urgent", "in_stock_now"] else 0,
                )
                preferred_manufacturers = st.text_input("Preferred manufacturers", value=", ".join(prefs.get("preferred_manufacturers") or []))
                blocked_manufacturers = st.text_input("Blocked manufacturers", value=", ".join(prefs.get("blocked_manufacturers") or []))
                requested_ram = st.text_input("Requested RAM", value=str(prefs.get("requested_ram") or ""))
                requested_storage = st.text_input("Requested storage", value=str(prefs.get("requested_storage") or ""))
                submitted = st.form_submit_button("Re-run recommendation", use_container_width=True)
            if submitted:
                changes = {
                    "preferred_category": category or None,
                    "workload_types": workloads,
                    "budget": budget or None,
                    "team_size": team_size or None,
                    "quantity": quantity or None,
                    "performance_priority": performance_priority or None,
                    "support_expectation": support_expectation or None,
                    "availability_need": availability_need or None,
                    "preferred_manufacturers": [item.strip() for item in preferred_manufacturers.split(",") if item.strip()],
                    "blocked_manufacturers": [item.strip() for item in blocked_manufacturers.split(",") if item.strip()],
                    "requested_ram": requested_ram.strip() or None,
                    "requested_storage": requested_storage.strip() or None,
                }
                update_preferences(changes)
                switch_to_page("results")


def render_expert_review(snapshot):
    result = snapshot.get("result") or {}
    with st.container(border=True):
        render_section_header(
            "Expert review",
            "Use this when there is no exact fit, the confidence is too low, or you want a human to review the recommendation before acting.",
            eyebrow="Fallback",
        )
        if not result:
            render_empty_state("Expert review becomes available after the system evaluates a real procurement brief.")
            return
        if not result.get("expert_review_eligible"):
            render_note("Expert review is not currently recommended for this result.", tone="info")
            return
        reason = result.get("meta", {}).get("expert_review_reason") or result.get("fallback_reason") or "manual_review"
        render_badges([("Expert review eligible", "rose"), (str(reason).replace("_", " ").title(), "rose")])
        render_note("Submitting this creates a review request tied to the current decision trace so a specialist can inspect the brief, the filters, and the fallback path.", tone="rose")
        notes = st.text_area(
            "Notes for the reviewer",
            key="expert-review-notes",
            placeholder="Need urgent delivery, approval on a stretch budget, or help choosing between two valid options.",
        )
        if st.button("Request expert help", use_container_width=True):
            submit_expert_review(notes)
            st.rerun()
        if st.session_state.get("last_review_request_id"):
            st.success(f"Expert review request created: {st.session_state.last_review_request_id}")


def render_studio_choice(snapshot):
    result = snapshot.get("result") or {}
    if not result:
        return
    render_section_header(
        "Choose a next step",
        "The assistant keeps this stage focused. Open only the action you want right now.",
        eyebrow="Studio",
    )
    cols = st.columns(3)
    choices = [
        (
            "Compare options",
            "Open a side-by-side table and choose one option to proceed with.",
            "compare",
        ),
        (
            "Modify / re-run",
            "Adjust the requirement with a natural-language change or a few quick controls.",
            "modify",
        ),
        (
            "Request expert help",
            "Escalate the current result when confidence or fit is not good enough.",
            "expert",
        ),
    ]
    for index, (title, copy, mode) in enumerate(choices):
        with cols[index]:
            if st.button(title, key=f"studio-choice-{mode}", use_container_width=True):
                st.session_state.studio_mode = mode
                st.rerun()
            st.markdown(f"<div class='proc-studio-caption'>{html.escape(copy)}</div>", unsafe_allow_html=True)


def render_internal(snapshot):
    with st.expander("Internal debug drawer"):
        tab1, tab2, tab3, tab4 = st.tabs(["Preferences", "Result", "Decision trace", "LLM stats"])
        with tab1:
            st.json(snapshot.get("preferences") or {})
        with tab2:
            st.json(snapshot.get("result") or {})
        with tab3:
            st.json(((snapshot.get("result") or {}).get("meta") or {}).get("decision_trace") or {})
        with tab4:
            st.json(snapshot.get("llm_stats") or {})
        st.markdown("### Conversation")
        for message in st.session_state.get("messages", []):
            st.write(f"- {message['role']}: {message['content']}")


def render_empty_page_state(title, message, target_key="intake"):
    render_section_header(title, message, eyebrow="Navigation")
    render_empty_state(message)
    if st.button("Go to intake", use_container_width=False, key=f"go-{target_key}-{title}"):
        switch_to_page(target_key)


def render_intake_page(snapshot):
    result = snapshot.get("result") or {}
    _, center_col, _ = st.columns([1, 3, 1])
    with center_col:
        render_hero(snapshot)
        render_prompt_chips(route_to="results")
        if result:
            with st.container(border=True):
                render_section_header(
                    "Current session",
                    "You already have a live recommendation. Open the next step when you are ready.",
                    eyebrow="Continue",
                )
                cols = st.columns(3)
                if cols[0].button("Open results", use_container_width=True):
                    switch_to_page("results")
                if cols[1].button("Open compare / modify", use_container_width=True):
                    open_studio("compare")
                if cols[2].button("Start fresh", use_container_width=True):
                    clear_cached_session_state(st.session_state.active_session_id)
                    ensure_runtime(force_reset=True)
                    st.rerun()
    user_input = st.chat_input("Describe what you need")
    if user_input:
        submit_message_and_route(user_input, "results")


def render_results_page(snapshot):
    result = snapshot.get("result") or {}
    if not result:
        render_empty_page_state(
            "No results yet",
            "Start from Intake, submit a procurement brief, and the app will route you here automatically once a result exists.",
        )
        return
    render_section_header(
        "Results",
        "This screen stays focused on understanding, recommendation output, and the next deliberate action.",
        eyebrow="Screen 2",
    )
    if result.get("next_question"):
        render_clarification(snapshot)
        if st.button("Open debug", use_container_width=False, key="results-debug-clarify"):
            switch_to_page("debug")
        return

    selected_product_id = st.session_state.get("selected_product_id") or ""
    show_top_detail = bool(selected_product_id) and is_top_recommendation_selected(result, selected_product_id)
    show_inline_detail = bool(selected_product_id) and not show_top_detail

    render_summary(snapshot)
    if show_top_detail:
        render_recommendation_detail(snapshot)
    render_recommendations(snapshot)
    if show_inline_detail:
        render_recommendation_detail(snapshot)
    meta = result.get("meta") or {}
    if (meta.get("compatibility_rejections_sample") or meta.get("policy_rejections_sample")):
        render_rejections(snapshot)
    if should_render_transparency_panel(result):
        render_transparency_panel(snapshot)
    if result.get("recommendations") or result.get("expert_review_eligible") or result.get("recommendation_groups"):
        render_results_actions(snapshot)
    render_conversation()
    footer_cols = st.columns([1, 1])
    if footer_cols[0].button("Open Studio", use_container_width=True, key="results-open-studio"):
        switch_to_page("studio")
    if footer_cols[1].button("Open Debug", use_container_width=True, key="results-open-debug"):
        switch_to_page("debug")


def render_studio_page(snapshot):
    result = snapshot.get("result") or {}
    if not result:
        render_empty_page_state(
            "Studio is empty",
            "There is nothing to compare or modify yet. Submit a brief in Intake first, then come here to work with the result.",
        )
        return
    render_section_header(
        "Studio",
        "Open one secondary action at a time so compare, modify, and expert review do not compete with the main recommendation screen.",
        eyebrow="Screen 3",
    )
    mode = str(st.session_state.get("studio_mode") or "").strip().lower()
    top_cols = st.columns([1, 1, 2])
    if top_cols[0].button("Back to results", use_container_width=True, key="studio-back-results"):
        switch_to_page("results")
    if top_cols[1].button("Choose another action", use_container_width=True, key="studio-reset-mode"):
        st.session_state.studio_mode = ""
        st.rerun()

    if not mode:
        render_studio_choice(snapshot)
        return
    if mode == "compare":
        render_compare(snapshot)
        return
    if mode == "modify":
        render_modify(snapshot)
        return
    if mode == "expert":
        render_expert_review(snapshot)
        return
    render_studio_choice(snapshot)


def render_debug_page(snapshot):
    render_section_header(
        "Debug",
        "Developer-only inspection for the current session, including the decision trace, raw result, and LLM usage stats.",
        eyebrow="Screen 4",
    )
    render_internal(snapshot)


def main():
    st.set_page_config(
        page_title="SMB Procurement Advisor",
        page_icon=":material/tune:",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    pages = [
        st.Page(page_target("intake"), title="Intake", icon=":material/edit_note:", default=True),
        st.Page(page_target("results"), title="Results", icon=":material/insights:"),
        st.Page(page_target("studio"), title="Studio", icon=":material/tune:"),
        st.Page(page_target("debug"), title="Debug", icon=":material/terminal:"),
    ]
    navigator = st.navigation(pages, position="top")
    navigator.run()

import html
import re
import sys
import uuid
from pathlib import Path

import streamlit as st

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


STAGES = [
    ("intake", "1. Intake"),
    ("clarify", "2. Clarify"),
    ("recommendations", "3. Recommendations"),
    ("product_detail", "4. Product Detail"),
    ("compare", "5. Compare"),
    ("modify", "6. Modify"),
    ("fallback", "7. Fallback"),
    ("expert_review", "8. Expert Review"),
]

V2_CSS = """
<style>
    :root {
        --v2-bg: #23221f; --v2-bg-soft: #2b2a26; --v2-surface: #302f2c; --v2-surface-soft: #353430;
        --v2-border: rgba(255,255,255,0.14); --v2-border-strong: rgba(255,255,255,0.22);
        --v2-text: #f2efe9; --v2-muted: #b7b0a4; --v2-blue: #60a5fa; --v2-amber: #f0c36a; --v2-rose: #f3b2ba;
        --v2-shadow: 0 18px 40px rgba(0,0,0,0.18);
    }
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: var(--v2-bg) !important; color: var(--v2-text) !important; }
    .block-container { max-width: 920px; padding: 1.35rem 1.2rem 3rem; }
    [data-testid="stSidebar"] { background: #1f1e1b !important; border-right: 1px solid var(--v2-border); }
    [data-testid="stSidebar"] * { color: var(--v2-text) !important; }
    div.stButton > button { min-height: 2.8rem; border-radius: 12px; background: transparent; border: 1px solid var(--v2-border-strong); color: var(--v2-text) !important; font-weight: 700; }
    div.stButton > button:hover { background: rgba(255,255,255,0.04); border-color: rgba(255,255,255,0.28); }
    div.stButton > button[kind="primary"], div.stButton > button[data-testid="baseButton-primary"] { background: var(--v2-surface-soft) !important; border-color: rgba(255,255,255,0.28) !important; color: var(--v2-text) !important; }
    .stTextInput input, .stNumberInput input, .stTextArea textarea, div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, .stMultiSelect [data-baseweb="tag"] { background: var(--v2-surface) !important; color: var(--v2-text) !important; border-color: var(--v2-border) !important; }
    .stTextInput label, .stNumberInput label, .stTextArea label, .stSelectbox label, .stMultiSelect label, .stSlider label { color: var(--v2-muted) !important; font-weight: 700 !important; }
    [data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] li, [data-testid="stMarkdownContainer"] span, .stCaption, .stCaptionContainer { color: var(--v2-text) !important; }
    .v2-shell { padding-top: 0.2rem; }
    .v2-divider { height: 1px; background: var(--v2-border); margin: 1.2rem 0 1.4rem; }
    .v2-screen-label { color: var(--v2-muted); font-size: 0.9rem; margin-bottom: 0.55rem; }
    .v2-page-title { font-size: 2rem; line-height: 1.05; color: var(--v2-text); margin: 0; letter-spacing: -0.03em; }
    .v2-page-copy { color: var(--v2-muted); font-size: 1.04rem; line-height: 1.55; margin: 0.6rem 0 0; }
    .v2-card, .v2-progress-card, .v2-summary-card { background: var(--v2-surface); border: 1px solid var(--v2-border); border-radius: 16px; box-shadow: var(--v2-shadow); }
    .v2-card { padding: 1.35rem 1.3rem; }
    .v2-card--hero { padding: 1.55rem 1.45rem; }
    .v2-card--highlight { border-color: rgba(96,165,250,0.8); background: linear-gradient(135deg, #343129 0%, #2b2f39 100%); box-shadow: 0 0 0 1px rgba(96,165,250,0.18), 0 12px 32px rgba(0,0,0,0.24); }
    .v2-card--soft { background: var(--v2-bg-soft); }
    .v2-progress-card { padding: 1rem 1.1rem 1.15rem; }
    .v2-progress-top { display: flex; justify-content: space-between; gap: 1rem; align-items: flex-start; margin-bottom: 0.8rem; }
    .v2-progress-label { color: var(--v2-muted); font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.35rem; }
    .v2-progress-title, .v2-summary-title, .v2-card__title { color: var(--v2-text); font-weight: 800; }
    .v2-progress-title { font-size: 1.05rem; line-height: 1.35; }
    .v2-progress-copy, .v2-summary-copy, .v2-nav-copy, .v2-meta, .v2-inline-note { color: var(--v2-muted); line-height: 1.45; }
    .v2-progress-copy, .v2-meta { font-size: 0.92rem; margin-top: 0.25rem; }
    .v2-nav-copy, .v2-inline-note { font-size: 0.9rem; margin-bottom: 0.75rem; }
    .v2-progress-step, .v2-badge, .v2-reason-chip { border-radius: 999px; font-weight: 800; white-space: nowrap; }
    .v2-progress-step { background: rgba(96,165,250,0.12); border: 1px solid rgba(96,165,250,0.22); color: #dbeafe; font-size: 0.82rem; padding: 0.45rem 0.75rem; }
    .v2-chip-row, .v2-reason-chip-row { display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 0.9rem; }
    .v2-badge { display: inline-flex; align-items: center; padding: 0.32rem 0.7rem; font-size: 0.78rem; line-height: 1; border: 1px solid transparent; color: inherit !important; }
    .v2-badge--blue { background: rgba(96,165,250,0.18); color: #dbeafe !important; border-color: rgba(96,165,250,0.3); }
    .v2-badge--green { background: rgba(196,228,159,0.18); color: #d6f0b8 !important; border-color: rgba(196,228,159,0.28); }
    .v2-badge--violet { background: rgba(201,196,255,0.18); color: #e5e2ff !important; border-color: rgba(201,196,255,0.28); }
    .v2-badge--amber { background: rgba(240,195,106,0.16); color: #f6d89d !important; border-color: rgba(240,195,106,0.28); }
    .v2-badge--rose { background: rgba(243,178,186,0.16); color: #ffd7dc !important; border-color: rgba(243,178,186,0.28); }
    .v2-badge--muted { background: rgba(255,255,255,0.06); color: var(--v2-muted) !important; border-color: var(--v2-border); }
    .v2-summary-card { padding: 0.95rem 0.95rem 0.8rem; margin: 0.85rem 0 1rem; }
    .v2-summary-title { font-size: 0.98rem; margin-bottom: 0.15rem; }
    .v2-summary-copy { font-size: 0.82rem; margin-bottom: 0.8rem; }
    .v2-summary-row { display: flex; justify-content: space-between; gap: 0.8rem; align-items: baseline; padding: 0.42rem 0; border-top: 1px solid rgba(255,255,255,0.06); }
    .v2-summary-row:first-of-type { border-top: none; padding-top: 0; }
    .v2-summary-key { color: var(--v2-muted); font-size: 0.82rem; }
    .v2-summary-value { color: var(--v2-text); font-size: 0.84rem; font-weight: 700; text-align: right; }
    .v2-price { font-size: 2rem; font-weight: 900; color: var(--v2-text); letter-spacing: -0.04em; text-align: right; }
    .v2-price-copy { color: var(--v2-muted); text-align: right; font-size: 0.92rem; line-height: 1.45; }
    .v2-reason-box { border-radius: 12px; padding: 1rem 1rem 0.9rem; border: 1px solid var(--v2-border); margin-top: 1rem; }
    .v2-reason-box--blue { border-left: 3px solid var(--v2-blue); background: var(--v2-bg-soft); }
    .v2-reason-box--amber { border-left: 3px solid var(--v2-amber); background: rgba(240,195,106,0.08); }
    .v2-reason-box--rose { border-left: 3px solid var(--v2-rose); background: rgba(243,178,186,0.08); }
    .v2-reason-box__title { font-size: 1rem; font-weight: 800; color: var(--v2-text); margin-bottom: 0.55rem; }
    .v2-reason-box ul { margin: 0; padding-left: 1.1rem; color: var(--v2-muted); line-height: 1.55; }
    .v2-reason-chip { display: inline-flex; align-items: center; padding: 0.4rem 0.72rem; background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); color: var(--v2-text); font-size: 0.78rem; line-height: 1.2; }
    .v2-table-wrap { overflow-x: auto; margin-top: 0.6rem; }
    .v2-grid-table { width: 100%; min-width: 560px; border-collapse: collapse; margin-top: 0; }
    .v2-grid-table td, .v2-grid-table th { padding: 0.72rem 0; border-bottom: 1px solid var(--v2-border); color: var(--v2-text); text-align: left; }
    .v2-grid-table td:last-child, .v2-grid-table th:last-child { text-align: right; font-weight: 700; }
    .v2-grid-table tr:last-child td, .v2-grid-table tr:last-child th { border-bottom: none; }
    .v2-alert { width: 86px; height: 86px; border-radius: 999px; background: rgba(161,98,7,0.42); display: flex; align-items: center; justify-content: center; font-size: 2rem; margin: 0 auto 1.3rem; color: #f6d089; }
    .v2-center { text-align: center; }
    .v2-spacer-sm { height: 0.65rem; }
    .v2-spacer-md { height: 1rem; }
    @media (max-width: 768px) {
        .block-container { padding-left: 0.85rem; padding-right: 0.85rem; }
        .v2-page-title { font-size: 1.55rem; }
        .v2-page-copy { font-size: 0.98rem; }
        .v2-card, .v2-card--hero, .v2-progress-card { padding: 1rem; }
        .v2-progress-top { flex-direction: column; }
        .v2-price, .v2-price-copy { text-align: left; }
        .v2-chip-row, .v2-reason-chip-row { gap: 0.4rem; }
    }
</style>
"""


def prettify_workload(value):
    return str(value or "").replace("_", " ").strip().title() or "Not captured"


def current_snapshot():
    initialize_session_defaults()
    ensure_runtime()
    return st.session_state.get("snapshot") or {}


def current_result(snapshot):
    return snapshot.get("result") or {}


def current_preferences(snapshot):
    return snapshot.get("preferences") or {}


def active_follow_up_question(result):
    result = dict(result or {})
    readiness = dict(result.get("readiness") or {})
    return (
        result.get("next_question")
        or readiness.get("next_question")
        or ""
    )


def compact_text(value, max_length=48):
    text = " ".join(str(value or "").split())
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3].rstrip()}..."


def humanize_label(value):
    return str(value or "").replace("_", " ").strip().title()


def format_compact_number(value):
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        number = float(text.replace(",", ""))
    except ValueError:
        return text
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,.2f}".rstrip("0").rstrip(".")


def humanize_budget_scope(value):
    mapping = {
        "per_unit": "Per device",
        "project_total": "Total project",
        "total_project": "Total project",
    }
    return mapping.get(str(value or "").strip().lower(), humanize_label(value))


def humanize_purchase_scope(value):
    mapping = {
        "single_item": "Single item",
        "single_device": "Single device",
        "team_rollout": "Team rollout",
        "project_rollout": "Project rollout",
        "site_refresh": "Site refresh",
    }
    return mapping.get(str(value or "").strip().lower(), humanize_label(value))


def format_workload_summary(values):
    cleaned = [prettify_workload(item) for item in as_list(values) if str(item or "").strip()]
    return ", ".join(cleaned)


def requirement_context_badges(result):
    result = dict(result or {})
    requirements = result.get("requirements") or {}
    target_profile = result.get("target_profile") or {}
    badges = []

    category = requirements.get("preferred_category")
    if not category:
        categories = as_list(target_profile.get("categories"))
        category = categories[0] if categories else ""
    if category:
        badges.append((f"Category {humanize_label(category)}", "blue"))

    workloads = format_workload_summary(requirements.get("workloads") or requirements.get("workload_types"))
    if workloads:
        badges.append((f"Use case {compact_text(workloads, 32)}", "violet"))

    quantity = requirements.get("quantity") or requirements.get("team_size")
    if quantity:
        badges.append((f"Quantity {quantity}", "green"))

    budget = requirements.get("budget")
    currency = str(requirements.get("currency") or "").strip()
    if budget not in {None, ""}:
        budget_bits = [format_compact_number(budget)]
        if currency:
            budget_bits.append(currency)
        badges.append((f"Budget {' '.join(bit for bit in budget_bits if bit)}", "amber"))

    budget_scope = requirements.get("budget_scope")
    if budget_scope:
        badges.append((f"Scope {humanize_budget_scope(budget_scope)}", "green"))
    elif budget not in {None, ""}:
        badges.append(("Scope unresolved", "rose"))

    purchase_scope = requirements.get("purchase_scope")
    if purchase_scope:
        badges.append((f"Purchase {humanize_purchase_scope(purchase_scope)}", "muted"))

    return badges


def latest_requirement_value(snapshot, *keys):
    result = current_result(snapshot)
    requirements = result.get("requirements") or {}
    prefs = current_preferences(snapshot)

    def has_value(value):
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, set, dict)):
            return bool(value)
        return True

    for key in keys:
        value = requirements.get(key)
        if has_value(value):
            return value
    for key in keys:
        value = prefs.get(key)
        if has_value(value):
            return value
    return None


def live_summary_budget(snapshot):
    budget = latest_requirement_value(snapshot, "budget")
    currency = str(latest_requirement_value(snapshot, "currency") or "").strip()
    budget_scope = latest_requirement_value(snapshot, "budget_scope")

    if budget in {None, ""}:
        return "Not captured", "Not captured"

    budget_parts = [format_compact_number(budget)]
    if currency:
        budget_parts.append(currency)
    budget_value = " ".join(bit for bit in budget_parts if bit)
    budget_scope_value = humanize_budget_scope(budget_scope) if budget_scope else "Not confirmed"
    return budget_value, budget_scope_value


def queue_toast(message, icon="✅"):
    if message:
        st.session_state.v2_pending_toast = {"message": str(message), "icon": icon}


def show_pending_toast():
    payload = st.session_state.pop("v2_pending_toast", None)
    if payload:
        st.toast(payload["message"], icon=payload.get("icon", "✅"))


def last_user_message():
    messages = st.session_state.get("messages", [])
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content") or "").strip()
    return ""


def recent_conversation_messages(limit=4):
    messages = st.session_state.get("messages", [])
    if not any(message.get("role") == "user" for message in messages):
        return []
    return messages[-limit:]


def flattened_recommendations(result):
    direct = list(result.get("recommendations") or [])
    if direct:
        return direct
    flattened = []
    for group in result.get("recommendation_groups") or []:
        for item in group.get("recommendations") or []:
            clone = dict(item)
            clone["recommendation_group_label"] = group.get("label")
            flattened.append(clone)
    return flattened


def primary_recommendation(result):
    recommendations = flattened_recommendations(result)
    return recommendations[0] if recommendations else None


def secondary_recommendations(result):
    recommendations = flattened_recommendations(result)
    return recommendations[1:4]


def recommendation_identity(item):
    return str(item.get("candidate_id") or item.get("product_id") or item.get("name") or "")


def recommendation_cost_basis(item):
    def to_number(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    total_cost = item.get("estimated_total_cost")
    total_number = to_number(total_cost)
    if total_number is not None:
        return total_number, "total"
    price = item.get("price")
    price_number = to_number(price)
    if price_number is not None:
        return price_number, "unit"
    return float("inf"), "unit"


def premium_signal_score(item):
    cpu_tier_order = {
        "entry": 1,
        "mainstream": 2,
        "performance": 3,
        "workstation": 4,
        "server": 4,
    }
    gpu_tier_order = {
        "integrated": 1,
        "entry_discrete": 2,
        "performance": 3,
        "workstation": 4,
    }
    cpu_score = cpu_tier_order.get(str(item.get("cpu_tier") or "").strip().lower(), 0)
    gpu_score = gpu_tier_order.get(str(item.get("gpu_tier") or "").strip().lower(), 0)
    def to_number(value):
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    ram_score = to_number(item.get("ram_gb")) / 8.0
    storage_score = to_number(item.get("storage_gb")) / 256.0
    support_score = to_number(item.get("support_score"))
    warranty_score = to_number(item.get("warranty_years"))
    return round((cpu_score * 4.0) + (gpu_score * 3.0) + ram_score + storage_score + (support_score * 0.5) + (warranty_score * 0.4), 4)


def shortlist_recommendation_badges(result, limit=3):
    shortlist = flattened_recommendations(result)[:limit]
    badge_map = {}
    if not shortlist:
        return badge_map

    def add_badge(item, label, tone):
        identity = recommendation_identity(item)
        if not identity:
            return
        badge_map.setdefault(identity, [])
        badge_tuple = (label, tone)
        if badge_tuple not in badge_map[identity]:
            badge_map[identity].append(badge_tuple)

    budget_item = min(shortlist, key=lambda item: (recommendation_cost_basis(item)[0], shortlist.index(item)))
    add_badge(budget_item, "Budget pick", "green")

    premium_item = max(shortlist, key=lambda item: (premium_signal_score(item), -(recommendation_cost_basis(item)[0]), -shortlist.index(item)))
    add_badge(premium_item, "High spec", "violet")

    return badge_map


def concise_reason_label(reason):
    text = " ".join(str(reason or "").split())
    lower = text.lower()
    if not text:
        return ""
    if "category match" in lower:
        return "Category match"
    if "within the stated budget" in lower or "stays within" in lower or "price fit stayed neutral" in lower:
        return "Within budget"
    if "budget scope remained unresolved" in lower or "scope unresolved" in lower:
        return "Scope unresolved"
    if "ram meets the target" in lower:
        match = re.search(r"(\d+)\s*gb", lower)
        return f"{match.group(1)}GB RAM" if match else "RAM fit"
    if "storage meets the target" in lower:
        match = re.search(r"(\d+)\s*gb", lower)
        return f"{match.group(1)}GB storage" if match else "Storage fit"
    if "stock" in lower or "availability" in lower:
        return "Availability"
    if "support" in lower:
        return "Support"
    if "warranty" in lower:
        return "Warranty"
    if "portability" in lower or "portable" in lower:
        return "Portable"
    if "processor" in lower or "cpu" in lower:
        return "CPU fit"
    return compact_text(text, 18)


def selected_recommendation(snapshot):
    product_id = st.session_state.get("selected_product_id") or ""
    if not product_id:
        return None
    return find_recommendation(current_result(snapshot), product_id)


def fallback_candidates(result):
    meta = result.get("meta") or {}
    candidates = []
    for rejected in (meta.get("compatibility_rejections_sample") or [])[:2]:
        candidates.append(
            {
                "name": rejected.get("name") or "Candidate",
                "reason": join_items(rejected.get("reason_codes") or rejected.get("reasons") or []),
            }
        )
    for rejected in (meta.get("policy_rejections_sample") or [])[:1]:
        candidates.append(
            {
                "name": rejected.get("name") or "Candidate",
                "reason": join_items(rejected.get("reason_codes") or rejected.get("reasons") or []),
            }
        )
    return candidates[:3]


def available_stages(snapshot):
    result = current_result(snapshot)
    recommendations = flattened_recommendations(result)
    selected_item = selected_recommendation(snapshot)
    available = {"intake", "modify", "expert_review"}
    if active_follow_up_question(result):
        available.add("clarify")
    if recommendations:
        available.add("recommendations")
    if len(recommendations) >= 2:
        available.add("compare")
    if selected_item:
        available.add("product_detail")
    if result.get("fallback_reason") and not recommendations:
        available.add("fallback")
    return available


def recommended_stage(snapshot):
    result = current_result(snapshot)
    recommendations = flattened_recommendations(result)
    if selected_recommendation(snapshot):
        return "product_detail"
    if active_follow_up_question(result):
        return "clarify"
    if result.get("fallback_reason") and not recommendations:
        return "fallback"
    if recommendations:
        return "recommendations"
    return "intake"


def set_stage(stage):
    st.session_state.v2_stage = stage


def sync_session_id_widget():
    pending_value = str(st.session_state.pop("pending_session_id_input", "") or "").strip()
    if pending_value:
        st.session_state.session_id_input = pending_value
        return
    active_session_id = str(st.session_state.get("active_session_id") or "").strip()
    current_input = str(st.session_state.get("session_id_input") or "").strip()
    if active_session_id and not current_input:
        st.session_state.session_id_input = active_session_id


def jump_to_stage(stage):
    cache_active_session_state(snapshot=st.session_state.get("snapshot"))
    if st.session_state.get("active_session_id"):
        st.session_state.pending_session_id_input = st.session_state.active_session_id
    set_stage(stage)
    st.rerun()


def reroute_after_state_change(snapshot=None, toast_message=None, toast_icon="✅"):
    queue_toast(toast_message, toast_icon)
    snapshot = snapshot or st.session_state.get("snapshot") or {}
    set_stage(recommended_stage(snapshot))
    st.rerun()


def stage_chip_rows():
    return [
        ["intake", "clarify", "recommendations", "product_detail", "compare"],
        ["modify", "fallback", "expert_review"],
    ]


def render_v2_runtime_sidebar():
    snapshot = st.session_state.get("snapshot") or {}
    result = current_result(snapshot)
    primary = primary_recommendation(result)
    workload_source = latest_requirement_value(snapshot, "workload_types", "workloads")
    workload_value = prettify_workload((workload_source or [None])[0] if isinstance(workload_source, list) else workload_source)
    budget_value, budget_scope_value = live_summary_budget(snapshot)
    quantity_value = str(latest_requirement_value(snapshot, "quantity", "team_size") or "Not captured")
    priority_value = str(latest_requirement_value(snapshot, "performance_priority") or "balanced").replace("_", " ").title()
    mode_value = str(result.get("recommendation_mode") or "collecting inputs").replace("_", " ").title()

    st.sidebar.header("Procurement Tester v2")
    st.sidebar.caption("Centered product-style flow with the same backend contract.")
    st.sidebar.markdown(
        f"""
        <div class='v2-summary-card'>
            <div class='v2-summary-title'>Live summary</div>
            <div class='v2-summary-copy'>Keep the key requirement inputs visible while you move between screens.</div>
            <div class='v2-summary-row'><div class='v2-summary-key'>Current screen</div><div class='v2-summary-value'>{html.escape(dict(STAGES).get(st.session_state.get("v2_stage", "intake"), "1. Intake"))}</div></div>
            <div class='v2-summary-row'><div class='v2-summary-key'>Recommendation mode</div><div class='v2-summary-value'>{html.escape(mode_value)}</div></div>
            <div class='v2-summary-row'><div class='v2-summary-key'>Budget</div><div class='v2-summary-value'>{html.escape(budget_value)}</div></div>
            <div class='v2-summary-row'><div class='v2-summary-key'>Budget type</div><div class='v2-summary-value'>{html.escape(budget_scope_value)}</div></div>
            <div class='v2-summary-row'><div class='v2-summary-key'>Quantity</div><div class='v2-summary-value'>{html.escape(quantity_value)}</div></div>
            <div class='v2-summary-row'><div class='v2-summary-key'>Use case</div><div class='v2-summary-value'>{html.escape(workload_value)}</div></div>
            <div class='v2-summary-row'><div class='v2-summary-key'>Priority</div><div class='v2-summary-value'>{html.escape(priority_value)}</div></div>
            <div class='v2-summary-row'><div class='v2-summary-key'>Current top match</div><div class='v2-summary-value'>{html.escape(compact_text(primary.get("name") if primary else "Not selected yet", 34))}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.sidebar.expander("Runtime settings", expanded=False):
        st.selectbox("LLM provider", ["groq", "gemini"], key="provider")
        if not st.session_state.get("model"):
            st.session_state.model = DEFAULT_PROVIDER_MODELS[st.session_state.provider]
        st.text_input("Model", key="model")
        st.text_input("API key", type="password", key="api_key")
        st.text_input("Store id (ignored for recommendations)", key="store_id")
        st.checkbox("Disable explanation LLM calls", key="disable_explanation_llm")
        st.text_input("Session id", key="session_id_input")
        st.text_input("Review user id", key="review_user_id")
        st.text_input("Review business id", key="review_business_id")
        if st.button("Apply Session Settings", use_container_width=True, key="v2-apply-runtime"):
            session_id = st.session_state.session_id_input.strip() or f"manual-{uuid.uuid4().hex[:8]}"
            with st.spinner("Refreshing the tester session..."):
                clear_cached_session_state(session_id)
                st.session_state.active_session_id = session_id
                ensure_runtime(force_reset=True)
            queue_toast("Session settings applied", "✅")
            set_stage("intake")
            st.rerun()
        if st.button("Generate New Session", use_container_width=True, key="v2-new-session"):
            new_session_id = f"manual-{uuid.uuid4().hex[:8]}"
            with st.spinner("Creating a fresh session..."):
                clear_cached_session_state(new_session_id)
                st.session_state.active_session_id = new_session_id
                st.session_state.pending_session_id_input = new_session_id
                ensure_runtime(force_reset=True)
            queue_toast("Started a new session", "✅")
            set_stage("intake")
            st.rerun()


def render_stage_chips(snapshot):
    available = available_stages(snapshot)
    active = st.session_state.get("v2_stage", "intake")
    stage_labels = dict(STAGES)
    for row_index, row in enumerate(stage_chip_rows()):
        cols = st.columns(len(row))
        for index, stage in enumerate(row):
            with cols[index]:
                if st.button(
                    stage_labels[stage],
                    key=f"v2-stage-{stage}",
                    type="primary" if active == stage else "secondary",
                    disabled=stage not in available and stage != "intake",
                    use_container_width=True,
                ):
                    jump_to_stage(stage)
        if row_index == 0:
            st.markdown("<div class='v2-spacer-sm'></div>", unsafe_allow_html=True)


def render_progress_header(snapshot):
    active = st.session_state.get("v2_stage", "intake")
    stage_ids = [stage for stage, _ in STAGES]
    stage_labels = dict(STAGES)
    step_number = stage_ids.index(active) + 1 if active in stage_ids else 1
    available_count = max(len(available_stages(snapshot)), 1)
    st.markdown(
        f"""
        <div class='v2-progress-card'>
            <div class='v2-progress-top'>
                <div>
                    <div class='v2-progress-label'>Flow progress</div>
                    <div class='v2-progress-title'>{html.escape(stage_labels.get(active, "1. Intake"))}</div>
                    <div class='v2-progress-copy'>Step {step_number} of {len(stage_ids)}. {available_count} screens are currently available for this requirement.</div>
                </div>
                <div class='v2-progress-step'>Step {step_number}/{len(stage_ids)}</div>
            </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Jump between screens without losing the current session.")
    st.markdown("</div>", unsafe_allow_html=True)
    with st.expander("Jump to another screen", expanded=False):
        st.markdown(
            "<div class='v2-nav-copy'>Use this to inspect another screen directly. Your current chat session and recommendation state stay active while you jump.</div>",
            unsafe_allow_html=True,
        )
        render_stage_chips(snapshot)


def render_header(screen_label, title, copy):
    if screen_label:
        render_badges([(screen_label, "muted")])
    if title:
        st.markdown(f"<h1 class='v2-page-title'>{html.escape(title)}</h1>", unsafe_allow_html=True)
    if copy:
        st.markdown(f"<p class='v2-page-copy'>{html.escape(copy)}</p>", unsafe_allow_html=True)


def render_badges(items):
    html_bits = []
    for label, tone in items:
        if label:
            html_bits.append(f"<span class='v2-badge v2-badge--{html.escape(str(tone))}'>{html.escape(str(label))}</span>")
    if html_bits:
        st.markdown(f"<div class='v2-chip-row'>{''.join(html_bits)}</div>", unsafe_allow_html=True)


def render_reason_box(title, items, tone="blue"):
    entries = "".join(f"<li>{html.escape(str(item))}</li>" for item in (items or [])) or "<li>No detail returned.</li>"
    st.markdown(
        f"""
        <div class='v2-reason-box v2-reason-box--{html.escape(str(tone))}'>
            <div class='v2-reason-box__title'>{html.escape(title)}</div>
            <ul>{entries}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_reason_chips(items, limit=3):
    chips = []
    seen = set()
    for item in as_list(items):
        label = concise_reason_label(item)
        if not label:
            continue
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        chips.append(label)
        if len(chips) >= limit:
            break
    if not chips:
        return
    html_bits = "".join(f"<span class='v2-reason-chip'>{html.escape(str(item))}</span>" for item in chips)
    st.markdown(f"<div class='v2-reason-chip-row'>{html_bits}</div>", unsafe_allow_html=True)


def render_recent_conversation(limit=4, expanded=False):
    transcript = recent_conversation_messages(limit=limit)
    if not transcript:
        return
    session_id = str(st.session_state.get("active_session_id") or "").strip() or "current session"
    with st.expander("Recent conversation", expanded=expanded):
        st.markdown(
            f"<div class='v2-inline-note'>You are still in the same live chat session: <strong>{html.escape(session_id)}</strong>. Jumping between screens only changes the view.</div>",
            unsafe_allow_html=True,
        )
        for message in transcript:
            role = "assistant" if message.get("role") == "assistant" else "user"
            with st.chat_message(role):
                st.write(message.get("content") or "")


def render_top_shell(snapshot):
    st.markdown("<div class='v2-shell'>", unsafe_allow_html=True)
    render_progress_header(snapshot)
    st.markdown("<div class='v2-divider'></div>", unsafe_allow_html=True)


def close_shell():
    st.markdown("</div>", unsafe_allow_html=True)


def submit_v2_message(message):
    with st.spinner("Finding the best match..."):
        send_message(message)
    reroute_after_state_change(st.session_state.get("snapshot") or {}, toast_message="Flow updated", toast_icon="✅")


def render_intake(snapshot):
    render_header(
        "screen 1 - intake",
        "What do you need?",
        "Describe your requirement in plain language. We'll figure out the rest.",
    )
    if (st.session_state.get("messages") or [])[1:] or current_result(snapshot):
        st.markdown(
            "<div class='v2-inline-note'>This is still the same active session. Jumping back here does not reset the conversation. Use the sidebar only if you want to start fresh with a new session id.</div>",
            unsafe_allow_html=True,
        )
        render_recent_conversation(limit=4, expanded=True)
    with st.form("v2-intake-form", clear_on_submit=False):
        cols = st.columns([5, 1])
        prompt = cols[0].text_input("Requirement", label_visibility="collapsed", placeholder="e.g. 20 laptops for developers")
        submitted = cols[1].form_submit_button("Get Recommendations", use_container_width=True)
    if submitted and prompt.strip():
        submit_v2_message(prompt)

    st.markdown("<div class='v2-spacer-md'></div>", unsafe_allow_html=True)
    chip_cols = st.columns(3)
    for index, prompt in enumerate(QUICK_PROMPTS):
        with chip_cols[index % len(chip_cols)]:
            if st.button(prompt["prompt"], key=f"v2-quick-{index}", use_container_width=True):
                submit_v2_message(prompt["prompt"])


def render_clarify(snapshot):
    result = current_result(snapshot)
    question = str(active_follow_up_question(result) or "One quick question")
    tool_multiselect = clarification_supports_tool_multiselect(snapshot)
    render_header(
        "screen 2 - clarification",
        "One quick question to find the best match",
        "Choose the tools that matter most and we will keep going." if tool_multiselect else "Answer this one item and we will keep going.",
    )
    render_badges(requirement_context_badges(result))
    options = clarification_quick_answers(snapshot)
    st.markdown("<div class='v2-card v2-card--hero'>", unsafe_allow_html=True)
    render_badges([("AI", "blue")])
    st.markdown(
        f"<div class='v2-page-copy' style='margin-top:0.9rem; color:var(--v2-text); font-size:1.65rem; font-weight:800;'>{html.escape(question)}</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div class='v2-spacer-md'></div>", unsafe_allow_html=True)
    if tool_multiselect:
        st.caption("Choose all that apply. Tool-level answers improve sizing for RAM, storage, GPU, and virtualization needs.")
        selection_key = clarification_multiselect_key(snapshot, "v2")
        selected_labels = st.multiselect(
            "Tools that matter most",
            [option["label"] for option in options],
            key=selection_key,
            placeholder="Select one or more tools",
            label_visibility="collapsed",
        )
        if st.button(
            "Use selected tools",
            key="v2-clarify-tools-submit",
            use_container_width=True,
            disabled=not selected_labels,
        ):
            message = build_tool_profile_message(options, selected_labels)
            if message:
                st.session_state.pop(selection_key, None)
                submit_v2_message(message)
    else:
        for index, option in enumerate(options):
            if st.button(option["label"], key=f"v2-clarify-{index}", use_container_width=True):
                if option.get("action") == "skip":
                    with st.spinner("Continuing with a cautious assumption..."):
                        skip_clarification_with_assumption(snapshot)
                    reroute_after_state_change(
                        st.session_state.get("snapshot") or {},
                        toast_message="Moved ahead with a saved assumption",
                        toast_icon="ℹ️",
                    )
                else:
                    submit_v2_message(option.get("message"))
    st.markdown("<div class='v2-divider'></div>", unsafe_allow_html=True)
    lower_cols = st.columns([1, 2.2])
    if lower_cols[0].button("Skip for Now", use_container_width=True, key="v2-clarify-skip"):
        with st.spinner("Continuing with a cautious assumption..."):
            skip_clarification_with_assumption(snapshot)
        reroute_after_state_change(
            st.session_state.get("snapshot") or {},
            toast_message="Moved ahead with a saved assumption",
            toast_icon="ℹ️",
        )
    freeform = lower_cols[1].text_input(
        "Start your own conversation",
        key="v2-clarify-freeform",
        label_visibility="collapsed",
        placeholder=clarification_freeform_placeholder(snapshot),
    )
    if freeform.strip() and st.button("Send Answer", key="v2-clarify-send", use_container_width=True):
        submit_v2_message(freeform)
    st.markdown("</div>", unsafe_allow_html=True)


def render_recommendations(snapshot):
    result = current_result(snapshot)
    top_item = primary_recommendation(result)
    others = secondary_recommendations(result)
    badge_map = shortlist_recommendation_badges(result, limit=1 + len(others))
    readiness = result.get("readiness") or {}
    if not top_item:
        set_stage("fallback")
        st.rerun()

    render_header(
        "screen 3 - recommendations",
        "Here's what we recommend",
        f"Based on: {last_user_message() or 'the current requirement brief'}",
    )
    top_cols = st.columns([4, 1])
    if top_cols[1].button("Adjust Inputs", key="v2-open-modify", use_container_width=True):
        jump_to_stage("modify")

    top_badges = [("Best match", "blue")]
    with st.container(border=True):
        header_cols = st.columns([3, 1])
        with header_cols[0]:
            render_badges(top_badges)
            st.markdown(
                f"<div class='v2-card__title' style='font-size:1.9rem; margin-top:0.6rem;'>{html.escape(str(top_item.get('name') or 'Recommendation'))}</div>",
                unsafe_allow_html=True,
            )
            spec_bits = []
            if top_item.get("processor"):
                spec_bits.append(top_item.get("processor"))
            if top_item.get("ram_gb"):
                spec_bits.append(f"{top_item.get('ram_gb')}GB RAM")
            if top_item.get("storage_gb"):
                spec_bits.append(f"{top_item.get('storage_gb')}GB SSD")
            st.markdown(f"<div class='v2-meta'>{html.escape(' | '.join(spec_bits) or 'Specs depend on catalog completeness')}</div>", unsafe_allow_html=True)
            render_reason_chips(top_item.get("reasons"))
        with header_cols[1]:
            st.markdown(f"<div class='v2-price'>{html.escape(format_price(top_item.get('price'), top_item.get('currency')))}</div>", unsafe_allow_html=True)
            stock_copy = f"stock {top_item.get('stock_quantity')}" if top_item.get("stock_quantity") is not None else "availability pending"
            st.markdown(f"<div class='v2-price-copy'>{html.escape(stock_copy)}</div>", unsafe_allow_html=True)

        render_reason_box("Why recommended", as_list(top_item.get("reasons"))[:3], tone="blue")
        button_cols = st.columns([1, 1, 2.2])
        if button_cols[0].button("View Details", use_container_width=True, key="v2-top-detail"):
            st.session_state.selected_product_id = str(top_item.get("product_id") or "")
            st.session_state.selected_product_name = str(top_item.get("name") or "")
            jump_to_stage("product_detail")
        if button_cols[1].button("Compare Options", use_container_width=True, key="v2-top-compare"):
            jump_to_stage("compare")

    if others:
        st.markdown("<div class='v2-spacer-md'></div>", unsafe_allow_html=True)
        st.markdown("<div class='v2-screen-label' style='margin-bottom:0.7rem; color:var(--v2-text);'>Other options</div>", unsafe_allow_html=True)
        cols = st.columns(min(3, len(others)))
        for index, item in enumerate(others):
            with cols[index % len(cols)]:
                with st.container(border=True):
                    item_badges = list(badge_map.get(recommendation_identity(item), []))
                    if item.get("recommendation_group_label"):
                        item_badges.append((item.get("recommendation_group_label"), "muted"))
                    if not item_badges:
                        item_badges = [("Alternative", "muted")]
                    if item_badges:
                        render_badges(item_badges)
                    st.markdown(f"<div class='v2-card__title' style='margin-top:0.7rem;'>{html.escape(str(item.get('name') or 'Option'))}</div>", unsafe_allow_html=True)
                    small_specs = []
                    if item.get("processor"):
                        small_specs.append(item.get("processor"))
                    if item.get("ram_gb"):
                        small_specs.append(f"{item.get('ram_gb')}GB")
                    if item.get("storage_gb"):
                        small_specs.append(f"{item.get('storage_gb')}GB")
                    st.markdown(f"<div class='v2-meta'>{html.escape(' | '.join(small_specs) or 'Specs pending')}</div>", unsafe_allow_html=True)
                    render_reason_chips(item.get("reasons"), limit=2)
                    st.markdown(f"<div style='font-size:1.6rem; font-weight:900; margin:1rem 0 0.6rem;'>{html.escape(format_price(item.get('price'), item.get('currency')))}</div>", unsafe_allow_html=True)
                    if st.button("View Details", key=f"v2-other-detail-{index}", use_container_width=True):
                        st.session_state.selected_product_id = str(item.get("product_id") or "")
                        st.session_state.selected_product_name = str(item.get("name") or "")
                        jump_to_stage("product_detail")

    action_cols = st.columns(3)
    if action_cols[0].button("Compare Shortlist", use_container_width=True, key="v2-compare-all"):
        jump_to_stage("compare")
    if action_cols[1].button("Adjust Inputs", use_container_width=True, key="v2-rerun"):
        jump_to_stage("modify")
    if action_cols[2].button("Request Expert Review", use_container_width=True, key="v2-expert"):
        jump_to_stage("expert_review")

    refinement_question = str(readiness.get("recommended_refinement_question") or "").strip()
    if refinement_question:
        st.markdown("<div class='v2-spacer-md'></div>", unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class='v2-card v2-card--soft'>
                <div class='v2-card__title'>Further enhance the need</div>
                <div class='v2-inline-note'>{html.escape(refinement_question)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Open Fine-Tuning Controls", use_container_width=True, key="v2-open-fine-tuning"):
            jump_to_stage("modify")


def render_product_detail(snapshot):
    item = selected_recommendation(snapshot)
    result = current_result(snapshot)
    if not item:
        set_stage("recommendations")
        st.rerun()

    render_header(
        "screen 4 - product detail",
        str(item.get("name") or "Product detail"),
        "Explainability view for the selected recommendation.",
    )
    st.markdown("<div class='v2-card'>", unsafe_allow_html=True)
    top_cols = st.columns([3, 1])
    with top_cols[0]:
        spec_bits = []
        if item.get("processor"):
            spec_bits.append(item.get("processor"))
        if item.get("ram_gb"):
            spec_bits.append(f"{item.get('ram_gb')}GB RAM")
        if item.get("storage_gb"):
            spec_bits.append(f"{item.get('storage_gb')}GB SSD")
        st.markdown(f"<div class='v2-meta'>{html.escape(' | '.join(spec_bits) or 'Specs depend on catalog completeness')}</div>", unsafe_allow_html=True)
        render_reason_chips(item.get("reasons"))
    with top_cols[1]:
        st.markdown(f"<div class='v2-price'>{html.escape(format_price(item.get('price'), item.get('currency')))}</div>", unsafe_allow_html=True)
        availability_copy = "In stock" if item.get("stock_quantity") else "Availability pending"
        st.markdown(f"<div class='v2-price-copy'>{html.escape(availability_copy)}</div>", unsafe_allow_html=True)

    rows = [
        ("Processor", item.get("processor") or "Not captured"),
        ("RAM", f"{item.get('ram_gb')}GB" if item.get("ram_gb") else "Not captured"),
        ("Storage", f"{item.get('storage_gb')}GB" if item.get("storage_gb") else "Not captured"),
        ("Warranty", f"{item.get('warranty_years')} year(s)" if item.get("warranty_years") else "Not captured"),
        ("Seller", item.get("seller") or "Not captured"),
        ("Support", item.get("support_score") if item.get("support_score") is not None else "Not captured"),
    ]
    row_html = "".join(f"<tr><th>{html.escape(str(label))}</th><td>{html.escape(str(value))}</td></tr>" for label, value in rows)
    st.markdown(f"<div class='v2-table-wrap'><table class='v2-grid-table'>{row_html}</table></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    render_reason_box("Why this was selected", as_list(item.get("reasons"))[:4], tone="blue")
    rejected = []
    meta = result.get("meta") or {}
    for candidate in (meta.get("compatibility_rejections_sample") or [])[:2]:
        rejected.append(f"{candidate.get('name')}: {join_items(candidate.get('reason_codes') or candidate.get('reasons') or [])}")
    for candidate in (meta.get("policy_rejections_sample") or [])[:2]:
        rejected.append(f"{candidate.get('name')}: {join_items(candidate.get('reason_codes') or candidate.get('reasons') or [])}")
    if not rejected:
        for other in secondary_recommendations(result)[:2]:
            rejected.append(f"{other.get('name')}: ranked lower than the selected recommendation.")
    render_reason_box("Why other options were not selected", rejected[:4], tone="rose")

    action_cols = st.columns(3)
    if action_cols[0].button("Back to Recommendations", use_container_width=True, key="v2-back-recs"):
        jump_to_stage("recommendations")
    if action_cols[1].button("Compare Options", use_container_width=True, key="v2-detail-compare"):
        jump_to_stage("compare")
    if action_cols[2].button("Request Expert Review", use_container_width=True, key="v2-detail-expert"):
        jump_to_stage("expert_review")


def render_compare(snapshot):
    result = current_result(snapshot)
    recommendations = flattened_recommendations(result)[:3]
    if len(recommendations) < 2:
        set_stage("recommendations")
        st.rerun()

    render_header(
        "screen 5 - compare",
        "Side-by-side comparison",
        "Compare the strongest available options before deciding.",
    )
    selected_names = [item.get("name") for item in recommendations]
    selected = st.multiselect("Choose 2-3 options", selected_names, default=selected_names, max_selections=3)
    selected_items = [item for item in recommendations if item.get("name") in selected]
    if len(selected_items) < 2:
        st.markdown("<div class='v2-inline-note'>Select at least two recommendations to compare.</div>", unsafe_allow_html=True)
        return

    headers = "".join(f"<th>{html.escape(str(item.get('name') or 'Recommendation'))}</th>" for item in selected_items)
    feature_rows = [
        ("Price / unit", [format_price(item.get("price"), item.get("currency")) for item in selected_items]),
        ("CPU", [item.get("processor") or "Not captured" for item in selected_items]),
        ("RAM", [f"{item.get('ram_gb')}GB" if item.get("ram_gb") else "Not captured" for item in selected_items]),
        ("Storage", [f"{item.get('storage_gb')}GB" if item.get("storage_gb") else "Not captured" for item in selected_items]),
        ("Warranty", [f"{item.get('warranty_years')} year(s)" if item.get("warranty_years") else "Not captured" for item in selected_items]),
        ("Availability", [f"Stock {item.get('stock_quantity')}" if item.get("stock_quantity") is not None else "Unknown" for item in selected_items]),
    ]
    rows_html = []
    for feature, values in feature_rows:
        cells = "".join(f"<td>{html.escape(str(value))}</td>" for value in values)
        rows_html.append(f"<tr><th>{html.escape(feature)}</th>{cells}</tr>")

    st.markdown(
        f"""
        <div class='v2-card'>
            <div class='v2-table-wrap'>
                <table class='v2-grid-table'>
                    <thead><tr><th>Feature</th>{headers}</tr></thead>
                    <tbody>{''.join(rows_html)}</tbody>
                </table>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(len(selected_items) + 1)
    if cols[0].button("Back", use_container_width=True, key="v2-compare-back"):
        jump_to_stage("recommendations")
    for index, item in enumerate(selected_items):
        with cols[index + 1]:
            if st.button(f"View {compact_text(item.get('name'), 18)}", key=f"v2-compare-view-{index}", use_container_width=True):
                st.session_state.selected_product_id = str(item.get("product_id") or "")
                st.session_state.selected_product_name = str(item.get("name") or "")
                jump_to_stage("product_detail")


def render_modify(snapshot):
    prefs = current_preferences(snapshot)
    render_header(
        "screen 6 - modify and re-run",
        "Adjust your requirements",
        "Use a smaller set of controls for the first rerun, then ask for a full conversation if needed.",
    )
    with st.form("v2-modify-form"):
        st.markdown("<div class='v2-card'>", unsafe_allow_html=True)
        budget = st.slider("Budget per unit", min_value=1000, max_value=25000, value=int(prefs.get("budget") or 6500), step=500)
        quantity = st.number_input("Quantity", min_value=1, value=int(prefs.get("quantity") or prefs.get("team_size") or 10), step=1)
        current_workload = (prefs.get("workload_types") or ["office_productivity"])[0]
        workload = st.selectbox(
            "Use case",
            WORKLOAD_OPTIONS,
            index=WORKLOAD_OPTIONS.index(current_workload) if current_workload in WORKLOAD_OPTIONS else 0,
            format_func=prettify_workload,
        )
        current_priority = str(prefs.get("performance_priority") or "balanced")
        priority = st.selectbox(
            "Priority",
            ["balanced", "cost", "performance"],
            index=["balanced", "cost", "performance"].index(current_priority) if current_priority in ["balanced", "cost", "performance"] else 0,
        )
        submitted = st.form_submit_button("Update Recommendation", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    if submitted:
        with st.spinner("Updating the recommendation..."):
            update_preferences(
                {
                    "budget": budget,
                    "quantity": quantity,
                    "team_size": quantity,
                    "workload_types": [workload],
                    "performance_priority": priority,
                }
            )
        reroute_after_state_change(st.session_state.get("snapshot") or {}, toast_message="Recommendation updated", toast_icon="✅")


def render_modify(snapshot):
    prefs = current_preferences(snapshot)
    quantity_value = int(prefs.get("quantity") or prefs.get("team_size") or 10)
    default_budget_scope = str(prefs.get("budget_scope") or ("project_total" if quantity_value > 1 else "per_unit"))
    default_purchase_scope = str(prefs.get("purchase_scope") or ("team_rollout" if quantity_value > 1 else "single_unit"))
    budget_scope_options = ["per_unit", "project_total", "unspecified"]
    purchase_scope_options = ["single_unit", "team_rollout", "site_deployment", "unspecified"]
    ram_options = ["", "8GB", "16GB", "32GB", "64GB"]
    storage_options = ["", "256GB", "512GB", "1TB", "2TB"]
    portability_options = ["", "low", "medium", "high"]
    support_options = ["", "basic", "business", "premium"]
    availability_options = ["", "standard", "soon", "urgent", "in_stock_now"]

    render_header(
        "screen 6 - modify and re-run",
        "Adjust your requirements",
        "Tune the budget, rollout size, and product preferences before rerunning the recommendation.",
    )
    with st.form("v2-modify-form"):
        st.markdown("<div class='v2-card'>", unsafe_allow_html=True)
        budget_scope = st.selectbox(
            "Budget scope",
            budget_scope_options,
            index=budget_scope_options.index(default_budget_scope) if default_budget_scope in budget_scope_options else 0,
            format_func=lambda value: {
                "per_unit": "Per device",
                "project_total": "Total project",
                "unspecified": "Not sure yet",
            }.get(value, value),
        )
        budget = st.number_input(
            "Budget amount",
            min_value=0,
            value=int(prefs.get("budget") or (6500 if budget_scope != "project_total" else 150000)),
            step=500,
        )
        quantity = st.number_input("Quantity", min_value=1, value=quantity_value, step=1)
        purchase_scope = st.selectbox(
            "Purchase scope",
            purchase_scope_options,
            index=purchase_scope_options.index(default_purchase_scope) if default_purchase_scope in purchase_scope_options else 0,
            format_func=lambda value: {
                "single_unit": "Single device",
                "team_rollout": "Team rollout",
                "site_deployment": "Site deployment",
                "unspecified": "Not sure yet",
            }.get(value, value),
        )
        current_workload = (prefs.get("workload_types") or ["office_productivity"])[0]
        workload = st.selectbox(
            "Use case",
            WORKLOAD_OPTIONS,
            index=WORKLOAD_OPTIONS.index(current_workload) if current_workload in WORKLOAD_OPTIONS else 0,
            format_func=prettify_workload,
        )
        current_priority = str(prefs.get("performance_priority") or "balanced")
        priority = st.selectbox(
            "Priority",
            ["balanced", "cost", "performance"],
            index=["balanced", "cost", "performance"].index(current_priority) if current_priority in ["balanced", "cost", "performance"] else 0,
        )
        with st.expander("Further enhance the need", expanded=False):
            requested_ram = st.selectbox(
                "Preferred RAM",
                ram_options,
                index=ram_options.index(str(prefs.get("requested_ram") or "")) if str(prefs.get("requested_ram") or "") in ram_options else 0,
                format_func=lambda value: value or "Not specified",
            )
            requested_ram_is_minimum = st.checkbox(
                "Treat RAM as a minimum requirement",
                value=bool(prefs.get("requested_ram_is_minimum")),
            )
            requested_storage = st.selectbox(
                "Preferred storage",
                storage_options,
                index=storage_options.index(str(prefs.get("requested_storage") or "")) if str(prefs.get("requested_storage") or "") in storage_options else 0,
                format_func=lambda value: value or "Not specified",
            )
            requested_storage_is_minimum = st.checkbox(
                "Treat storage as a minimum requirement",
                value=bool(prefs.get("requested_storage_is_minimum")),
            )
            portability_need = st.selectbox(
                "Portability",
                portability_options,
                index=portability_options.index(str(prefs.get("portability_need") or "")) if str(prefs.get("portability_need") or "") in portability_options else 0,
                format_func=lambda value: {
                    "": "Not specified",
                    "low": "Low",
                    "medium": "Medium",
                    "high": "High",
                }.get(value, value),
            )
            support_expectation = st.selectbox(
                "Support expectation",
                support_options,
                index=support_options.index(str(prefs.get("support_expectation") or "")) if str(prefs.get("support_expectation") or "") in support_options else 0,
                format_func=lambda value: {
                    "": "Not specified",
                    "basic": "Basic",
                    "business": "Business",
                    "premium": "Premium",
                }.get(value, value),
            )
            availability_need = st.selectbox(
                "Availability need",
                availability_options,
                index=availability_options.index(str(prefs.get("availability_need") or "")) if str(prefs.get("availability_need") or "") in availability_options else 0,
                format_func=lambda value: {
                    "": "Not specified",
                    "standard": "Standard",
                    "soon": "Soon",
                    "urgent": "Urgent",
                    "in_stock_now": "In stock now",
                }.get(value, value),
            )
        submitted = st.form_submit_button("Update Recommendation", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    if submitted:
        with st.spinner("Updating the recommendation..."):
            update_preferences(
                {
                    "budget": int(budget),
                    "budget_scope": None if budget_scope == "unspecified" else budget_scope,
                    "quantity": quantity,
                    "team_size": quantity,
                    "purchase_scope": None if purchase_scope == "unspecified" else purchase_scope,
                    "workload_types": [workload],
                    "performance_priority": priority,
                    "requested_ram": requested_ram or None,
                    "requested_ram_is_minimum": requested_ram_is_minimum if requested_ram else None,
                    "requested_storage": requested_storage or None,
                    "requested_storage_is_minimum": requested_storage_is_minimum if requested_storage else None,
                    "portability_need": portability_need or None,
                    "support_expectation": support_expectation or None,
                    "availability_need": availability_need or None,
                }
            )
        reroute_after_state_change(st.session_state.get("snapshot") or {}, toast_message="Recommendation updated", toast_icon="âœ…")


def render_fallback(snapshot):
    result = current_result(snapshot)
    candidates = fallback_candidates(result)
    render_header(
        "screen 7 - no match or fallback",
        "No exact match found",
        "We couldn't find a product that meets all your criteria. Budget, availability, or fit may be blocking the current result.",
    )
    st.markdown("<div class='v2-center'><div class='v2-alert'>!</div></div>", unsafe_allow_html=True)
    if candidates:
        rows = "".join(f"<tr><th>{html.escape(candidate['name'])}</th><td>{html.escape(candidate['reason'])}</td></tr>" for candidate in candidates)
        st.markdown(
            f"""
            <div class='v2-card'>
                <div class='v2-card__title'>Closest alternatives</div>
                <div class='v2-table-wrap'><table class='v2-grid-table'>{rows}</table></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class='v2-card'>
                <div class='v2-card__title'>Fallback reason</div>
                <div class='v2-card__copy'>{html.escape(fallback_label(result.get('fallback_reason')) or str(result.get('fallback_reason') or 'No exact fit was found.'))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    cols = st.columns(2)
    if cols[0].button("Request Expert Review", use_container_width=True, key="v2-fallback-expert"):
        jump_to_stage("expert_review")
    if cols[1].button("Adjust Inputs", use_container_width=True, key="v2-fallback-modify"):
        jump_to_stage("modify")


def render_expert_review(snapshot):
    prefs = current_preferences(snapshot)
    summary = last_user_message() or f"{prefs.get('quantity') or prefs.get('team_size') or 1} units | {join_items(prefs.get('workload_types') or [])}"
    render_header(
        "screen 8 - expert review request",
        "Talk to a procurement expert",
        "An expert will review your requirements and follow up within 1 business day.",
    )
    with st.form("v2-expert-form"):
        st.markdown("<div class='v2-card'>", unsafe_allow_html=True)
        name = st.text_input("Your name", placeholder="Amit Sharma")
        email = st.text_input("Email", placeholder="amit@company.com")
        summary_text = st.text_area("Requirement summary (auto-filled)", value=summary, height=120)
        notes = st.text_area("Additional notes (optional)", placeholder="Preferred brand, extended warranty, urgent delivery, or anything else.")
        submitted = st.form_submit_button("Submit Expert Review", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    if submitted:
        payload_notes = notes.strip()
        contact_lines = [f"Name: {name.strip()}" if name.strip() else "", f"Email: {email.strip()}" if email.strip() else ""]
        payload_notes = "\n".join([line for line in contact_lines if line] + [f"Summary: {summary_text.strip()}"] + ([payload_notes] if payload_notes else []))
        with st.spinner("Submitting the expert review request..."):
            submit_expert_review(payload_notes)
        queue_toast("Expert review request submitted", "✅")
        set_stage("expert_review")
        st.rerun()


def render_internal_debug(snapshot):
    with st.expander("Developer debug"):
        st.write("Active stage:", st.session_state.get("v2_stage"))
        st.write("Session id:", st.session_state.get("active_session_id"))
        st.json(snapshot.get("preferences") or {})
        st.json(snapshot.get("result") or {})


def ensure_v2_defaults():
    initialize_session_defaults()
    sync_session_id_widget()
    st.session_state.setdefault("v2_stage", "intake")


def render_current_stage(snapshot):
    stage = st.session_state.get("v2_stage", "intake")
    valid = available_stages(snapshot)
    if stage != "intake" and stage not in valid:
        stage = recommended_stage(snapshot)
        st.session_state.v2_stage = stage
    if stage == "clarify":
        render_clarify(snapshot)
    elif stage == "recommendations":
        render_recommendations(snapshot)
    elif stage == "product_detail":
        render_product_detail(snapshot)
    elif stage == "compare":
        render_compare(snapshot)
    elif stage == "modify":
        render_modify(snapshot)
    elif stage == "fallback":
        render_fallback(snapshot)
    elif stage == "expert_review":
        render_expert_review(snapshot)
    else:
        render_intake(snapshot)


def main():
    st.set_page_config(
        page_title="SMB Procurement Tester v2",
        page_icon=":material/auto_awesome:",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.markdown(V2_CSS, unsafe_allow_html=True)
    ensure_v2_defaults()
    snapshot = current_snapshot()
    render_v2_runtime_sidebar()
    show_pending_toast()
    render_top_shell(snapshot)
    render_current_stage(snapshot)
    if st.session_state.get("v2_stage", "intake") != "intake":
        render_recent_conversation(limit=4, expanded=False)
    render_internal_debug(snapshot)
    close_shell()

v2 = sys.modules[__name__]

import html
import re
import sys
import uuid
from pathlib import Path

import streamlit as st

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


V3_EXTRA_CSS = """
<style>
    .v3-panel {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 1rem 1.05rem;
        margin-bottom: 1rem;
    }

    .v3-panel__title {
        color: var(--v2-text);
        font-size: 1rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }

    .v3-panel__copy {
        color: var(--v2-muted);
        font-size: 0.92rem;
        line-height: 1.5;
        margin-bottom: 0.9rem;
    }

    .v3-note {
        border-radius: 12px;
        padding: 0.68rem 0.8rem;
        margin-top: 0.55rem;
        line-height: 1.55;
        border: 1px solid rgba(255,255,255,0.08);
    }

    .v3-note--info {
        background: rgba(96,165,250,0.1);
        border-color: rgba(96,165,250,0.22);
        color: #dbeafe;
    }

    .v3-note--warm {
        background: rgba(240,195,106,0.1);
        border-color: rgba(240,195,106,0.2);
        color: #f6d89d;
    }

    .v3-note--rose {
        background: rgba(243,178,186,0.1);
        border-color: rgba(243,178,186,0.2);
        color: #ffd7dc;
    }

    .v3-bullet-list {
        margin: 0;
        padding-left: 1rem;
        color: var(--v2-muted);
        line-height: 1.55;
    }

    .v3-mini-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.9rem;
    }

    div[data-testid="stMarkdownContainer"] table {
        width: 100%;
        border-collapse: collapse;
        margin: 0.85rem 0 1rem;
    }

    div[data-testid="stMarkdownContainer"] table th,
    div[data-testid="stMarkdownContainer"] table td {
        border: 1px solid rgba(255,255,255,0.12);
        padding: 0.75rem 0.8rem;
        vertical-align: top;
    }

    div[data-testid="stMarkdownContainer"] table th {
        background: rgba(255,255,255,0.04);
        color: var(--v2-text);
        font-weight: 800;
        text-align: left;
    }

    div[data-testid="stMarkdownContainer"] table td {
        color: var(--v2-text);
    }

    div[data-testid="stMarkdownContainer"] ul,
    div[data-testid="stMarkdownContainer"] ol {
        padding-left: 1.3rem;
        margin-bottom: 0.9rem;
    }

    @media (max-width: 768px) {
        .v3-mini-grid {
            grid-template-columns: 1fr;
        }
    }
</style>
"""


def queue_toast(message, icon=None):
    if message:
        st.session_state.v3_pending_toast = {
            "message": str(message),
            "icon": icon,
        }


def show_pending_toast():
    payload = st.session_state.pop("v3_pending_toast", None)
    if payload:
        icon = payload.get("icon")
        if icon:
            st.toast(payload["message"], icon=icon)
        else:
            st.toast(payload["message"])


v2.queue_toast = queue_toast


def render_note(message, tone="info"):
    if not message:
        return
    st.markdown(
        f"<div class='v3-note v3-note--{html.escape(str(tone))}'>{html.escape(str(message))}</div>",
        unsafe_allow_html=True,
    )


def clean_preview_markdown(text):
    cleaned = str(text or "").replace("\r", "\n")
    if not cleaned.strip():
        return ""
    cleaned = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"`{1,3}", "", cleaned)
    cleaned = re.sub(r"^#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*[-*_]{3,}\s*$", " ", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*\|?(\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$", " ", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.replace("|", " ")
    cleaned = cleaned.replace("**", "")
    cleaned = cleaned.replace("__", "")
    cleaned = re.sub(r"-{4,}", " ", cleaned)
    cleaned = re.sub(r"\.{4,}", "...", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def narrative_preview(text, max_length=420):
    cleaned = clean_preview_markdown(text)
    if not cleaned:
        return ""
    return v2.compact_text(cleaned, max_length=max_length)


def narrative_option_preview(text, max_length=180):
    bullets = narrative_preview_bullets(text, max_items=2)
    if bullets:
        return bullets[0]

    cleaned = clean_preview_markdown(text)
    if not cleaned:
        return ""
    cleaned = re.sub(
        r"^recommendation overview\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.split(
        r"\b1\.\s+[A-Z]|\b2\.\s+[A-Z]|\b3\.\s+[A-Z]|\b4\.\s+[A-Z]|\b5\.\s+[A-Z]|\b6\.\s+[A-Z]",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip()
    return v2.compact_text(cleaned, max_length=max_length)


def narrative_preview_bullets(text, max_items=4):
    parsed = parse_explanation_sections(text)
    bullets = []
    seen = set()
    section_plan = [
        ("Overview", 1),
        ("Work fit", 2),
        ("Trade-offs", 1),
        ("Upgrade implications", 1),
        ("Bottom line for your team", 1),
    ]

    for section_name, section_limit in section_plan:
        remaining = max_items - len(bullets)
        if remaining <= 0:
            break
        section_text = parsed.get(section_name)
        if not section_text:
            continue
        for item in preview_section_bullets(section_text, max_items=min(section_limit, remaining)):
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            bullets.append(item)
            if len(bullets) >= max_items:
                return bullets

    if bullets:
        return bullets

    cleaned = clean_preview_markdown(text)
    if not cleaned:
        return []

    fallback = []
    for sentence in re.split(r"(?<=[.!?])\s+", cleaned):
        item = compact_preview_bullet(sentence)
        if not item:
            continue
        fallback.append(item)
        if len(fallback) >= max_items:
            break
    return fallback


def fallback_preview_bullets(item, max_items=3):
    bullets = []
    name = str(item.get("name") or "This recommendation").strip()
    price = v2.format_price(item.get("price"), item.get("currency"))
    if price and price != "Price unavailable":
        bullets.append(f"{name} is the current top match at {price}.")
    else:
        bullets.append(f"{name} is the current top match for the captured requirement.")

    for reason in v2.as_list(item.get("reasons")):
        text = " ".join(str(reason or "").split())
        if not text:
            continue
        bullets.append(text)
        if len(bullets) >= max_items:
            break

    return bullets[:max_items]


DETAIL_SECTION_RULES = [
    ("Overview", [r"recommendation overview", r"overview"]),
    ("Work fit", [r"how .* fits", r"work fit", r"fit[s]?\b", r"meets? the .* workload"]),
    ("Trade-offs", [r"trade[- ]?offs?", r"watch[- ]?outs?", r"considerations?"]),
    ("Upgrade implications", [r"upgrade implications?", r"upgrade options?", r"upgrades?"]),
    ("Downgrade implications", [r"downgrade implications?", r"downgrades?"]),
    ("Key assumptions", [r"key assumptions?", r"assumptions we made", r"assumptions behind this recommendation", r"assumptions"]),
    ("Bottom line for your team", [r"bottom line", r"what to do next", r"next steps"]),
]


def explanation_heading_name(line):
    raw_line = str(line or "").strip()
    if not raw_line or raw_line.startswith("|"):
        return ""
    cleaned = re.sub(r"^\s*(#{1,6}\s*|\d+\.\s*|\*\*|\*|[-–]\s*)", "", raw_line)
    cleaned = cleaned.strip("*: ").lower()
    if not cleaned:
        return ""
    for title, patterns in DETAIL_SECTION_RULES:
        if any(re.search(pattern, cleaned, flags=re.IGNORECASE) for pattern in patterns):
            return title
    return ""


def parse_explanation_sections(text):
    lines = str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    sections = {}
    current_title = ""
    current_lines = []
    preamble = []

    def commit(title, body_lines):
        body = "\n".join(body_lines).strip()
        if title and body:
            sections[title] = body

    for raw_line in lines:
        line = raw_line.rstrip()
        title = explanation_heading_name(line)
        if title:
            if current_title:
                commit(current_title, current_lines)
            elif preamble:
                commit("Overview", preamble)
                preamble = []
            current_title = title
            current_lines = []
            continue

        if current_title:
            current_lines.append(line)
        else:
            preamble.append(line)

    if current_title:
        commit(current_title, current_lines)
    elif preamble:
        commit("Overview", preamble)

    return sections


def compact_preview_bullet(text, max_length=170):
    cleaned = clean_preview_markdown(text)
    cleaned = re.sub(r"^(?:\d+[\.\)]\s+)+", "", cleaned).strip(" -:;")
    if not cleaned:
        return ""
    lower = cleaned.lower()
    if re.fullmatch(r"\d+[.)]?", cleaned):
        return ""
    if lower in {
        "requirement",
        "minimum needed",
        "what the product provides",
        "fit comment",
        "aspect",
        "what you get",
        "what you give up",
    }:
        return ""
    if any(
        noise in lower
        for noise in [
            "requirement what the laptop provides",
            "why it matters",
            "what the recommendation offers",
            "what you may need to consider",
        ]
    ):
        return ""
    return v2.compact_text(cleaned, max_length=max_length)


def parse_markdown_table(text):
    rows = []
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or "|" not in line[1:]:
            continue
        raw_cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not any(raw_cells):
            continue
        if all(re.fullmatch(r":?-{3,}:?", cell) for cell in raw_cells if cell):
            continue
        cells = [clean_preview_markdown(cell) for cell in raw_cells]
        if any(cells):
            rows.append(cells)
    if len(rows) < 2:
        return [], []
    headers = rows[0]
    data_rows = [row for row in rows[1:] if len(row) == len(headers)]
    return headers, data_rows


def preview_table_bullets(text, max_items=2):
    headers, rows = parse_markdown_table(text)
    if not headers or not rows:
        return []

    lowered_headers = [header.lower() for header in headers]

    def find_index(options):
        for option in options:
            for index, header in enumerate(lowered_headers):
                if option in header:
                    return index
        return None

    label_index = find_index(["requirement", "aspect"])
    if label_index is None:
        label_index = 0
    detail_index = find_index(["fit comment", "what you give up", "comment"])
    secondary_index = find_index(["what the product provides", "what you get", "minimum needed"])

    bullets = []
    for row in rows:
        label = row[label_index].rstrip(":") if label_index < len(row) else ""
        detail = row[detail_index] if detail_index is not None and detail_index < len(row) else ""
        if not detail and secondary_index is not None and secondary_index < len(row):
            detail = row[secondary_index]
        if not detail:
            detail = " ".join(cell for idx, cell in enumerate(row) if idx != label_index and cell)
        item = f"{label}: {detail}" if label and detail else detail or label
        item = compact_preview_bullet(item)
        if not item:
            continue
        bullets.append(item)
        if len(bullets) >= max_items:
            break
    return bullets


def preview_list_bullets(text, max_items=2):
    bullets = []
    for raw_line in str(text or "").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("|"):
            continue
        match = re.match(r"^\s*(?:[-*+]\s+|\d+[\.\)]\s+)(.+)$", raw_line)
        if not match:
            continue
        item = compact_preview_bullet(match.group(1))
        if not item:
            continue
        bullets.append(item)
        if len(bullets) >= max_items:
            break
    return bullets


def preview_sentence_bullets(text, max_items=2):
    bullets = []
    cleaned = clean_preview_markdown(text)
    for sentence in re.split(r"(?<=[.!?])\s+", cleaned):
        item = compact_preview_bullet(sentence)
        if not item:
            continue
        bullets.append(item)
        if len(bullets) >= max_items:
            break
    return bullets


def preview_section_bullets(text, max_items=2):
    return (
        preview_table_bullets(text, max_items=max_items)
        or preview_list_bullets(text, max_items=max_items)
        or preview_sentence_bullets(text, max_items=max_items)
    )


def bullet_markdown(items, empty_text):
    lines = [f"- {str(item).strip()}" for item in (items or []) if str(item or "").strip()]
    return "\n".join(lines) if lines else empty_text


def explanation_overview_fallback(result, item, explanation):
    overview = narrative_preview(explanation, max_length=280)
    if overview:
        return overview
    summary = str(result.get("summary") or "").strip()
    if summary:
        return summary
    return f"{item.get('name') or 'This recommendation'} is the current best match for the captured requirement."


def build_detail_sections(result, item):
    explanation = item.get("explanation")
    parsed = parse_explanation_sections(explanation)
    assumptions = v2.as_list(result.get("assumptions"))
    trade_offs = v2.as_list(item.get("trade_offs"))
    reasons = v2.as_list(item.get("reasons"))

    sections = [
        ("Overview", parsed.get("Overview") or explanation_overview_fallback(result, item, explanation)),
        ("Work fit", parsed.get("Work fit") or bullet_markdown(reasons[:5], "No explicit work-fit explanation was returned for this recommendation.")),
        ("Trade-offs", parsed.get("Trade-offs") or bullet_markdown(trade_offs[:5], "No additional trade-offs were reported for this recommendation.")),
        ("Upgrade implications", parsed.get("Upgrade implications") or "No explicit upgrade implications were returned for this recommendation."),
        ("Downgrade implications", parsed.get("Downgrade implications") or "No explicit downgrade implications were returned for this recommendation."),
        ("Key assumptions", parsed.get("Key assumptions") or bullet_markdown(assumptions[:5], "No extra assumptions were captured for this recommendation.")),
        ("Bottom line for your team", parsed.get("Bottom line for your team") or str(result.get("summary") or "").strip() or f"{item.get('name') or 'This recommendation'} remains the current best fit based on the captured requirement and available catalog data."),
    ]
    return [(title, body) for title, body in sections if str(body or "").strip()]


def render_detail_sections(result, item):
    for title, body in build_detail_sections(result, item):
        with st.container(border=True):
            st.markdown(f"#### {title}")
            st.markdown(body)


def recommendation_count(result):
    recs = result.get("recommendations") or []
    if recs:
        return len(recs)
    total = 0
    for group in result.get("recommendation_groups") or []:
        total += len(group.get("recommendations") or [])
    return total


def render_transparency_panel(snapshot):
    result = v2.current_result(snapshot)
    if not result:
        return

    requirements = result.get("requirements") or {}
    readiness = result.get("readiness") or {}
    target_profile = result.get("target_profile") or {}
    confidence = str(readiness.get("decision_confidence_band") or "unknown").replace("_", " ").title()
    recommendation_mode = str(result.get("recommendation_mode") or "not_set").replace("_", " ").title()
    compatibility_scope = str(result.get("compatibility_report", {}).get("scope") or "item").title()
    fallback_reason = result.get("fallback_reason")
    assumptions = v2.as_list(result.get("assumptions"))
    intake_badges = v2.requirement_context_badges(result)
    clarification_reasons = v2.as_list(result.get("clarification_required_reasons") or readiness.get("clarification_required_reasons"))
    missing_field = readiness.get("highest_priority_missing_field")
    with st.container(border=True):
        st.markdown("<div class='v3-panel__title'>System summary</div>", unsafe_allow_html=True)
        v2.render_badges(
            [
                (f"Confidence {confidence}", "blue"),
                (f"Mode {recommendation_mode}", "muted"),
                (f"{compatibility_scope} compatibility", "muted"),
                (f"{recommendation_count(result)} options", "muted"),
                (v2.fallback_label(fallback_reason) or "", "rose" if fallback_reason else "muted"),
            ]
        )

        if intake_badges:
            st.markdown(
                "<div class='v3-panel__title' style='margin-top:0.75rem; margin-bottom:0.3rem;'>Captured intake</div>",
                unsafe_allow_html=True,
            )
            v2.render_badges(intake_badges)

        summary_cols = st.columns(2)
        with summary_cols[0]:
            if clarification_reasons:
                v2.render_reason_box("Needs clarity", clarification_reasons[:4], tone="rose")
            elif missing_field:
                render_note(f"Still checking {v2.humanize_label(missing_field)} before fully locking this recommendation.", tone="rose")
            else:
                render_note("No open clarification blockers right now.", tone="warm")
        with summary_cols[1]:
            if assumptions:
                v2.render_reason_box("Assumptions", assumptions[:5], tone="amber")
            else:
                render_note("No assumptions were needed for this result.", tone="warm")

        if st.session_state.get("disable_explanation_llm"):
            st.markdown(
                "<div class='v2-inline-note'>Explanation LLM calls are disabled right now, so narrative fields can be shorter or missing.</div>",
                unsafe_allow_html=True,
            )


def render_recommendation_narrative(snapshot):
    result = v2.current_result(snapshot)
    top_item = v2.primary_recommendation(result)
    if not top_item:
        return

    trade_offs = v2.as_list(top_item.get("trade_offs"))
    explanation = top_item.get("explanation")
    preview_bullets = narrative_preview_bullets(explanation)
    if not preview_bullets:
        preview_bullets = fallback_preview_bullets(top_item)
    if not preview_bullets:
        preview_bullets = ["Use `View Details` to open the full product explanation."]

    with st.container(border=True):
        st.markdown("<div class='v3-panel__title'>Recommendation preview</div>", unsafe_allow_html=True)
        v2.render_reason_box("Preview highlights", preview_bullets, tone="blue")
        st.caption("Use `View Details` to open the full product explanation.")

    columns = st.columns(2)
    with columns[0]:
        v2.render_reason_box("Why this works", v2.as_list(top_item.get("reasons"))[:4], tone="blue")
    with columns[1]:
        v2.render_reason_box(
            "Trade-offs / watch-outs",
            trade_offs[:4] or ["No additional trade-offs were reported for the current top match."],
            tone="rose",
        )


def render_detail_narrative(snapshot):
    result = v2.current_result(snapshot)
    item = v2.selected_recommendation(snapshot)
    if not item:
        return

    trade_offs = v2.as_list(item.get("trade_offs"))
    explanation = item.get("explanation")
    fallback_reason = result.get("fallback_reason")

    with st.container(border=True):
        st.markdown("<div class='v3-panel__title'>Detailed explanation</div>", unsafe_allow_html=True)

        if explanation:
            with st.container(border=True):
                st.markdown(explanation)
        else:
            render_note("No long-form product explanation was returned for this recommendation.", tone="warm")

        grid = st.columns(2)
        with grid[0]:
            v2.render_reason_box("Selection rationale", v2.as_list(item.get("reasons"))[:4], tone="blue")
        with grid[1]:
            v2.render_reason_box(
                "Trade-offs / warnings",
                trade_offs[:4] or ["No additional trade-offs were reported for this selection."],
                tone="rose",
            )

        if fallback_reason:
            render_note(f"Current fallback state: {v2.fallback_label(fallback_reason) or fallback_reason}", tone="rose")


def render_llm_drawer(snapshot):
    llm_stats = snapshot.get("llm_stats") or {}
    with st.expander("LLM narrative and debug stats", expanded=False):
        if st.session_state.get("disable_explanation_llm"):
            render_note("Explanation calls are currently disabled in runtime settings.", tone="rose")
        if llm_stats:
            st.json(llm_stats)
        else:
            st.write("No LLM stats are available yet for this session.")


def render_v3_runtime_sidebar():
    snapshot = st.session_state.get("snapshot") or {}
    result = v2.current_result(snapshot)
    primary = v2.primary_recommendation(result)
    workload_source = v2.latest_requirement_value(snapshot, "workload_types", "workloads")
    workload_value = v2.prettify_workload((workload_source or [None])[0] if isinstance(workload_source, list) else workload_source)
    budget_value, budget_scope_value = v2.live_summary_budget(snapshot)
    quantity_value = str(v2.latest_requirement_value(snapshot, "quantity", "team_size") or "Not captured")

    st.sidebar.header("Procurement Tester v3")
    st.sidebar.markdown(
        f"""
        <div class='v2-summary-card'>
            <div class='v2-summary-title'>Live summary</div>
            <div class='v2-summary-row'><div class='v2-summary-key'>Current screen</div><div class='v2-summary-value'>{html.escape(dict(v2.STAGES).get(st.session_state.get("v2_stage", "intake"), "1. Intake"))}</div></div>
            <div class='v2-summary-row'><div class='v2-summary-key'>Top match</div><div class='v2-summary-value'>{html.escape(v2.compact_text(primary.get('name') if primary else 'Not selected yet', 34))}</div></div>
            <div class='v2-summary-row'><div class='v2-summary-key'>Budget</div><div class='v2-summary-value'>{html.escape(budget_value)}</div></div>
            <div class='v2-summary-row'><div class='v2-summary-key'>Budget type</div><div class='v2-summary-value'>{html.escape(budget_scope_value)}</div></div>
            <div class='v2-summary-row'><div class='v2-summary-key'>Quantity</div><div class='v2-summary-value'>{html.escape(quantity_value)}</div></div>
            <div class='v2-summary-row'><div class='v2-summary-key'>Use case</div><div class='v2-summary-value'>{html.escape(workload_value)}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.sidebar.expander("Runtime settings", expanded=False):
        st.selectbox("LLM provider", ["groq", "gemini"], key="provider")
        if not st.session_state.get("model"):
            st.session_state.model = v2.DEFAULT_PROVIDER_MODELS[st.session_state.provider]
        st.text_input("Model", key="model")
        st.text_input("API key", type="password", key="api_key")
        st.text_input("Store id (ignored for recommendations)", key="store_id")
        st.checkbox("Disable explanation LLM calls", key="disable_explanation_llm")
        st.text_input("Session id", key="session_id_input")
        st.text_input("Review user id", key="review_user_id")
        st.text_input("Review business id", key="review_business_id")
        if st.button("Apply Session Settings", use_container_width=True, key="v3-apply-runtime"):
            session_id = st.session_state.session_id_input.strip() or f"manual-{uuid.uuid4().hex[:8]}"
            with st.spinner("Refreshing the tester session..."):
                v2.clear_cached_session_state(session_id)
                st.session_state.active_session_id = session_id
                v2.ensure_runtime(force_reset=True)
            queue_toast("Session settings applied")
            v2.set_stage("intake")
            st.rerun()
        if st.button("Generate New Session", use_container_width=True, key="v3-new-session"):
            new_session_id = f"manual-{uuid.uuid4().hex[:8]}"
            with st.spinner("Creating a fresh session..."):
                v2.clear_cached_session_state(new_session_id)
                st.session_state.active_session_id = new_session_id
                st.session_state.pending_session_id_input = new_session_id
                v2.ensure_runtime(force_reset=True)
            queue_toast("Started a new session")
            v2.set_stage("intake")
            st.rerun()


def ensure_v3_defaults():
    v2.initialize_session_defaults()
    v2.sync_session_id_widget()
    st.session_state.setdefault("v2_stage", "intake")
    if "v3_defaults_applied" not in st.session_state:
        st.session_state.disable_explanation_llm = False
        st.session_state.v3_defaults_applied = True


def render_current_stage(snapshot):
    stage = st.session_state.get("v2_stage", "intake")
    valid = v2.available_stages(snapshot)
    if stage != "intake" and stage not in valid:
        stage = v2.recommended_stage(snapshot)
        st.session_state.v2_stage = stage

    if stage != "intake" and v2.current_result(snapshot):
        render_transparency_panel(snapshot)

    if stage == "clarify":
        v2.render_clarify(snapshot)
    elif stage == "recommendations":
        v2.render_recommendations(snapshot)
        render_recommendation_narrative(snapshot)
    elif stage == "product_detail":
        v2.render_product_detail(snapshot)
        render_detail_narrative(snapshot)
    elif stage == "compare":
        v2.render_compare(snapshot)
    elif stage == "modify":
        v2.render_modify(snapshot)
    elif stage == "fallback":
        v2.render_fallback(snapshot)
    elif stage == "expert_review":
        v2.render_expert_review(snapshot)
    else:
        v2.render_intake(snapshot)

    render_llm_drawer(snapshot)


def main():
    st.set_page_config(
        page_title="SMB Procurement Tester v3",
        page_icon=":material/auto_awesome:",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.markdown(v2.V2_CSS + V3_EXTRA_CSS, unsafe_allow_html=True)
    ensure_v3_defaults()
    snapshot = v2.current_snapshot()
    render_v3_runtime_sidebar()
    show_pending_toast()
    v2.render_top_shell(snapshot)
    render_current_stage(snapshot)
    if st.session_state.get("v2_stage", "intake") != "intake":
        v2.render_recent_conversation(limit=4, expanded=False)
    v2.render_internal_debug(snapshot)
    v2.close_shell()

if __name__ == "__main__":
    main()

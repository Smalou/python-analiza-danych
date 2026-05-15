

from __future__ import annotations

import html
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pandas as pd
import streamlit as st

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from presentation_demo.demo_agent_flow import (  # noqa: E402
    build_prompt,
    mock_llm_generate_sql,
    summarize_result,
)
from presentation_demo.finance_kpi_example import (  # noqa: E402
    top_by_gross_margin,
    top_by_gross_profit,
    top_by_revenue,
)
from presentation_demo.metadata_context import STRONG_CONTEXT, WEAK_CONTEXT  # noqa: E402
from presentation_demo.mock_warehouse import (  # noqa: E402
    LAST_CLOSED_QUARTER,
    create_customer_profitability_data,
    execute_mock_query,
)
from presentation_demo.observability_demo import compute_summary, get_agent_logs  # noqa: E402
from presentation_demo.sql_guardrails import (  # noqa: E402
    Severity,
    ValidationResult,
    validate_sql,
)


DEFAULT_QUESTION = "Którzy klienci byli najbardziej rentowni w ostatnim kwartale?"


# -----------------------------------------------------------------------------
# Page config + design system
# -----------------------------------------------------------------------------

st.set_page_config(
    page_title="Python w erze AI — prezentacja",
    page_icon="•",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        :root {
            --bg: #0A1A2F;
            --surface: rgba(255, 255, 255, 0.045);
            --surface-strong: rgba(255, 255, 255, 0.065);
            --line: rgba(255, 255, 255, 0.12);
            --line-strong: rgba(255, 255, 255, 0.20);
            --text: rgba(255, 255, 255, 0.96);
            --muted: rgba(255, 255, 255, 0.66);
            --soft: rgba(255, 255, 255, 0.46);
            --accent: #86A8FF;
            --accent-strong: #A8C0FF;
            --success: #45D49A;
            --warning: #F4C16B;
            --danger: #F58E91;
        }

        html, body, [data-testid="stAppViewContainer"], .stApp {
            background:
                radial-gradient(1200px 600px at 18% -10%, rgba(134, 168, 255, 0.13), transparent 60%),
                radial-gradient(900px 500px at 85% 110%, rgba(69, 212, 154, 0.07), transparent 60%),
                var(--bg) !important;
            color: var(--text) !important;
        }

        [data-testid="stHeader"] {
            background: transparent !important;
        }

        [data-testid="stSidebar"],
        [data-testid="stSidebarNav"],
        [data-testid="collapsedControl"] {
            display: none !important;
        }

        [data-testid="stMarkdownContainer"],
        [data-testid="stText"] {
            color: inherit;
        }

        .stCaptionContainer,
        [data-testid="stCaptionContainer"],
        small,
        [data-testid="stCaption"] {
            color: var(--muted) !important;
        }

        pre, code {
            background: rgba(0, 0, 0, 0.30) !important;
            color: rgba(255, 255, 255, 0.94) !important;
            border-radius: 12px !important;
        }

        div[data-testid="stDataFrame"] {
            background: var(--surface) !important;
            border-radius: 16px;
            border: 1px solid var(--line);
        }

        .block-container {
            padding-top: 1rem;
            padding-bottom: 1.5rem;
            max-width: 1480px;
        }

        h1, h2, h3, h4, h5 {
            letter-spacing: -0.025em;
            color: var(--text);
        }

        /* Buttons */
        .stButton > button,
        [data-testid="baseButton-secondary"] {
            background: rgba(255, 255, 255, 0.06) !important;
            color: var(--text) !important;
            border: 1px solid var(--line-strong) !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            box-shadow: none !important;
            transition: all 0.15s ease;
            padding: 0.55rem 1.1rem !important;
        }

        .stButton > button:hover,
        [data-testid="baseButton-secondary"]:hover {
            background: rgba(134, 168, 255, 0.18) !important;
            border-color: var(--accent) !important;
            color: #FFFFFF !important;
        }

        [data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, var(--accent), var(--accent-strong)) !important;
            color: #0A1A2F !important;
            border: none !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            box-shadow: 0 10px 28px rgba(134, 168, 255, 0.32) !important;
            padding: 0.7rem 1.4rem !important;
        }

        [data-testid="baseButton-primary"]:hover {
            transform: translateY(-1px);
            box-shadow: 0 14px 36px rgba(134, 168, 255, 0.42) !important;
            color: #0A1A2F !important;
        }

        .stButton > button:disabled {
            background: rgba(255, 255, 255, 0.025) !important;
            color: var(--soft) !important;
            border-color: var(--line) !important;
            cursor: not-allowed !important;
        }

        .stButton > button p,
        [data-testid="baseButton-secondary"] p,
        [data-testid="baseButton-primary"] p {
            color: inherit !important;
        }

        /* Metrics */
        div[data-testid="stMetric"] {
            background: var(--surface);
            border: 1px solid var(--line);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
            color: rgba(255, 255, 255, 0.92) !important;
        }

        div[data-testid="stMetricLabel"],
        div[data-testid="stMetricLabel"] p,
        div[data-testid="stMetricLabel"] span,
        div[data-testid="stMetricLabel"] label,
        [data-testid="stMetric"] label {
            color: rgba(255, 255, 255, 0.88) !important;
            -webkit-text-fill-color: rgba(255, 255, 255, 0.88) !important;
            opacity: 1 !important;
            visibility: visible !important;
            font-weight: 600 !important;
            font-size: 0.84rem !important;
            letter-spacing: 0.04em !important;
            text-transform: uppercase !important;
        }

        div[data-testid="stMetricValue"],
        div[data-testid="stMetricValue"] div,
        div[data-testid="stMetricValue"] p,
        div[data-testid="stMetricValue"] span {
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            font-size: 1.95rem !important;
            font-weight: 800 !important;
            letter-spacing: -0.03em !important;
            opacity: 1 !important;
        }

        div[data-testid="stMetricDelta"],
        div[data-testid="stMetricDelta"] p,
        div[data-testid="stMetricDelta"] span {
            opacity: 1 !important;
        }

        /* Top navigation */
        .top-bar-title {
            font-size: 0.72rem;
            color: var(--accent);
            letter-spacing: 0.16em;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 0.1rem;
        }

        .top-bar-current {
            font-size: 1rem;
            font-weight: 600;
            color: var(--text);
        }

        .scene-counter {
            display: inline-block;
            background: rgba(134, 168, 255, 0.16);
            color: var(--accent);
            font-weight: 700;
            font-size: 0.72rem;
            letter-spacing: 0.08em;
            padding: 0.18rem 0.55rem;
            border-radius: 999px;
            margin-right: 0.55rem;
            vertical-align: middle;
        }

        .progress-line {
            height: 4px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.08);
            overflow: hidden;
            margin: 0.55rem 0 0.1rem 0;
        }

        .progress-fill {
            height: 4px;
            border-radius: 999px;
            background: linear-gradient(90deg, var(--accent), var(--success));
            transition: width 0.4s ease;
        }

        .nav-spacer {
            height: 0.4rem;
        }

        /* Typography */
        .big-title {
            font-size: 3.2rem;
            line-height: 1.04;
            font-weight: 800;
            letter-spacing: -0.04em;
            color: var(--text);
            margin: 0 0 0.85rem 0;
            max-width: 1150px;
        }

        .medium-title {
            font-size: 2.05rem;
            line-height: 1.12;
            font-weight: 750;
            letter-spacing: -0.03em;
            color: var(--text);
            margin: 0 0 0.55rem 0;
            max-width: 1120px;
        }

        .subtitle {
            font-size: 1.12rem;
            line-height: 1.55;
            color: var(--muted);
            max-width: 940px;
            margin: 0 0 1.5rem 0;
        }

        .eyebrow {
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: var(--accent);
            margin-bottom: 0.45rem;
        }

        .section-title {
            font-size: 1rem;
            font-weight: 700;
            color: var(--text);
            margin: 0 0 0.6rem 0;
            letter-spacing: -0.005em;
        }

        .statement {
            font-size: 1.18rem;
            line-height: 1.5;
            font-weight: 600;
            padding: 1rem 1.25rem;
            border-left: 3px solid var(--accent);
            background: linear-gradient(90deg, rgba(134, 168, 255, 0.10), transparent 75%);
            border-radius: 0 14px 14px 0;
            margin: 1.4rem 0 0.4rem 0;
            max-width: 1120px;
            color: var(--text);
        }

        .hero-panel {
            padding: 2rem 2.2rem;
            border-radius: 24px;
            border: 1px solid var(--line);
            background:
                radial-gradient(circle at 12% 0%, rgba(134, 168, 255, 0.20), transparent 38%),
                radial-gradient(circle at 100% 100%, rgba(69, 212, 154, 0.10), transparent 30%),
                linear-gradient(135deg, rgba(20, 40, 75, 0.7), rgba(10, 26, 47, 0.95));
            margin-bottom: 1.4rem;
        }

        .hero-meta {
            margin-top: 1.15rem;
            padding-top: 1.1rem;
            border-top: 1px solid var(--line);
            font-size: 0.98rem;
            line-height: 1.55;
            color: var(--muted);
            max-width: 940px;
        }

        .hero-meta a.hero-repo-link {
            color: var(--accent-strong);
            font-weight: 600;
            text-decoration: none;
            border-bottom: 1px solid rgba(168, 192, 255, 0.45);
        }

        .hero-meta a.hero-repo-link:hover {
            color: #FFFFFF;
            border-bottom-color: var(--accent-strong);
        }

        .hero-author {
            margin-top: 0.55rem;
            font-size: 0.92rem;
            color: var(--soft);
        }

        .card, .card-strong {
            border: 1px solid var(--line);
            border-radius: 18px;
            background: var(--surface);
            padding: 1.15rem 1.25rem;
            height: 100%;
        }

        .card-strong {
            background:
                radial-gradient(circle at 90% 0%, rgba(134, 168, 255, 0.14), transparent 40%),
                var(--surface-strong);
            border-color: rgba(134, 168, 255, 0.35);
        }

        .card-title {
            font-weight: 700;
            font-size: 1.05rem;
            color: var(--text);
            margin-bottom: 0.4rem;
        }

        .muted {
            color: var(--muted);
            font-size: 0.96rem;
            line-height: 1.5;
        }

        .huge-number {
            font-size: 3.6rem;
            line-height: 1;
            letter-spacing: -0.05em;
            font-weight: 800;
            color: var(--text);
            margin-bottom: 0.25rem;
        }

        .huge-number-accent {
            color: var(--accent);
        }

        .flow-step-spacer {
            height: 0.4rem;
        }

        .flow-step-num {
            flex-shrink: 0;
            width: 28px;
            height: 28px;
            margin-top: 0.1rem;
            border-radius: 50%;
            background: rgba(134, 168, 255, 0.18);
            color: var(--accent);
            font-weight: 700;
            font-size: 0.88rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }

        .pill {
            display: inline-block;
            border: 1px solid var(--line);
            border-radius: 999px;
            padding: 0.3rem 0.78rem;
            margin: 0.16rem 0.16rem 0.16rem 0;
            background: var(--surface);
            color: var(--text);
            font-size: 0.88rem;
            font-weight: 500;
        }

        .insight-row {
            display: flex;
            align-items: flex-start;
            gap: 0.6rem;
            padding: 0.4rem 0;
            color: var(--text);
            font-size: 0.96rem;
        }

        .insight-row .ico {
            flex-shrink: 0;
            width: 22px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
        }

        .insight-row.good .ico { color: var(--success); }
        .insight-row.bad .ico { color: var(--danger); }

        .foundation-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.9rem;
            margin-top: 0.3rem;
        }

        .foundation-item {
            border: 1px solid var(--line);
            border-radius: 16px;
            background: var(--surface);
            padding: 0.95rem 1rem;
        }

        .foundation-item strong {
            color: var(--text);
        }

        .foundation-item span {
            display: block;
            color: var(--muted);
            margin-top: 0.25rem;
            line-height: 1.45;
        }

        .real-code-explain {
            color: rgba(255, 255, 255, 0.88) !important;
            line-height: 1.58;
            font-size: 1.02rem;
            max-width: 52ch;
            margin-bottom: 1rem !important;
        }

        .before-code-tabs {
            height: 0.75rem;
            min-height: 0.75rem;
        }

        [data-testid="stTabs"] [data-testid="stAlert"] {
            margin-top: 0.6rem !important;
        }

        div[data-testid="stTabs"] {
            margin-top: 0.5rem !important;
            margin-bottom: 0.25rem !important;
        }

        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            display: flex !important;
            flex-wrap: wrap !important;
            align-items: flex-end !important;
            gap: 0.65rem 1.1rem !important;
            row-gap: 0.7rem !important;
            padding: 0.35rem 0 1.1rem 0 !important;
            margin-bottom: 0.35rem !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.12) !important;
            background: transparent !important;
        }

        div[data-testid="stTabs"] [data-baseweb="tab"],
        div[data-testid="stTabs"] button[role="tab"] {
            flex: 0 1 auto !important;
            margin: 0 !important;
            padding: 0.55rem 1.15rem !important;
            min-height: 2.5rem !important;
            border-radius: 12px !important;
            border: 1px solid rgba(255, 255, 255, 0.14) !important;
            background: rgba(255, 255, 255, 0.055) !important;
            color: rgba(255, 255, 255, 0.82) !important;
            font-weight: 500 !important;
            font-size: 0.9rem !important;
            letter-spacing: 0.01em !important;
            line-height: 1.25 !important;
            transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease !important;
            box-shadow: none !important;
        }

        div[data-testid="stTabs"] [data-baseweb="tab"]:hover,
        div[data-testid="stTabs"] button[role="tab"]:hover {
            color: #FFFFFF !important;
            background: rgba(134, 168, 255, 0.14) !important;
            border-color: rgba(134, 168, 255, 0.35) !important;
        }

        div[data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"],
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            color: #FFFFFF !important;
            background: linear-gradient(180deg, rgba(134, 168, 255, 0.28), rgba(134, 168, 255, 0.1)) !important;
            border-color: rgba(134, 168, 255, 0.55) !important;
            border-bottom: 2px solid var(--accent) !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 18px rgba(0, 0, 0, 0.2) !important;
        }

        div[data-testid="stTabs"] [role="tabpanel"],
        div[data-testid="stTabs"] [data-baseweb="tab-panel"] {
            padding-top: 1.35rem !important;
        }

        div[data-testid="stTabs"] > div:nth-child(2) {
            padding-top: 0.15rem !important;
        }

        div[data-testid="stAlert"],
        div[data-testid="stAlertContainer"] {
            background: linear-gradient(135deg, rgba(25, 52, 95, 0.95), rgba(12, 28, 52, 0.92)) !important;
            border: 1px solid rgba(134, 168, 255, 0.45) !important;
            border-radius: 14px !important;
        }

        div[data-testid="stAlert"] p,
        div[data-testid="stAlert"] span,
        div[data-testid="stAlert"] div[data-testid="stMarkdownContainer"] p,
        div[data-testid="stAlertContainer"] p,
        div[data-testid="stAlertContainer"] span {
            color: rgba(255, 255, 255, 0.94) !important;
            -webkit-text-fill-color: rgba(255, 255, 255, 0.94) !important;
        }

        div[data-testid="stAlert"] [data-testid="stIcon"],
        div[data-testid="stAlertContainer"] [data-testid="stIcon"] {
            color: var(--accent-strong) !important;
            fill: var(--accent-strong) !important;
        }

        [data-testid="stCodeBlock"],
        [data-testid="stCode"] {
            background: #061525 !important;
            border: 1px solid rgba(134, 168, 255, 0.35) !important;
            border-radius: 14px !important;
            box-shadow:
                inset 0 1px 0 rgba(255, 255, 255, 0.06),
                0 8px 28px rgba(0, 0, 0, 0.35) !important;
        }

        [data-testid="stCodeBlock"] pre,
        [data-testid="stCodeBlock"] code,
        [data-testid="stCode"] pre,
        [data-testid="stCode"] code {
            background: transparent !important;
            color: #EEF2FF !important;
        }

        [data-testid="stCodeBlock"] .hljs-keyword,
        [data-testid="stCode"] .hljs-keyword,
        [data-testid="stCodeBlock"] .hljs-selector-tag,
        [data-testid="stCode"] .hljs-selector-tag,
        [data-testid="stCodeBlock"] .hljs-built_in,
        [data-testid="stCode"] .hljs-built_in,
        [data-testid="stCodeBlock"] .hljs-name,
        [data-testid="stCode"] .hljs-name {
            color: #7EE7FF !important;
        }

        [data-testid="stCodeBlock"] .hljs-string,
        [data-testid="stCode"] .hljs-string,
        [data-testid="stCodeBlock"] .hljs-attr,
        [data-testid="stCode"] .hljs-attr,
        [data-testid="stCodeBlock"] .hljs-template-variable,
        [data-testid="stCode"] .hljs-template-variable {
            color: #9EF0B8 !important;
        }

        [data-testid="stCodeBlock"] .hljs-comment,
        [data-testid="stCode"] .hljs-comment {
            color: rgba(255, 255, 255, 0.50) !important;
            font-style: italic;
        }

        [data-testid="stCodeBlock"] .hljs-number,
        [data-testid="stCode"] .hljs-number,
        [data-testid="stCodeBlock"] .hljs-literal,
        [data-testid="stCode"] .hljs-literal {
            color: #FFD49A !important;
        }

        [data-testid="stCodeBlock"] .hljs-title,
        [data-testid="stCode"] .hljs-title,
        [data-testid="stCodeBlock"] .hljs-function .hljs-title,
        [data-testid="stCode"] .hljs-function .hljs-title {
            color: #D4B8FF !important;
        }

        [data-testid="stCodeBlock"] .hljs-params,
        [data-testid="stCode"] .hljs-params,
        [data-testid="stCodeBlock"] .hljs-variable,
        [data-testid="stCode"] .hljs-variable {
            color: #C8D8F0 !important;
        }

        /* Expander + st.status: Streamlit na summary w stanie „open” nakłada bgMix (często jasne),
           a aplikacja wymusza jasny tekst na .stApp — po rozwinięciu wygląda to jak biały na białym. */
        [data-testid="stExpander"] details {
            background: linear-gradient(135deg, rgba(16, 36, 68, 0.92), rgba(8, 20, 40, 0.98)) !important;
            border: 1px solid var(--line) !important;
            border-radius: 14px !important;
        }

        [data-testid="stExpander"] summary {
            background: linear-gradient(135deg, rgba(16, 36, 68, 0.88), rgba(8, 20, 40, 0.95)) !important;
            color: var(--text) !important;
        }

        [data-testid="stExpander"] summary:hover,
        [data-testid="stExpander"] summary:focus-visible,
        [data-testid="stExpander"] summary:active {
            background: rgba(134, 168, 255, 0.16) !important;
            color: var(--text) !important;
        }

        [data-testid="stExpander"] summary p,
        [data-testid="stExpander"] summary span,
        [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] p,
        [data-testid="stExpander"] summary [data-testid="stMarkdownContainer"] span {
            color: var(--text) !important;
        }

        [data-testid="stExpander"] details > div,
        [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
            background: rgba(6, 18, 38, 0.96) !important;
            color: var(--text) !important;
        }

        [data-testid="stExpander"] [data-testid="stMarkdownContainer"],
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stExpander"] [data-testid="stMarkdownContainer"] span {
            color: rgba(255, 255, 255, 0.92) !important;
        }

        [data-testid="stExpander"] [data-testid="stCodeBlock"],
        [data-testid="stExpander"] [data-testid="stCode"] {
            background: #061525 !important;
            border: 1px solid rgba(134, 168, 255, 0.4) !important;
        }

        [data-testid="stExpander"] [data-testid="stCodeBlock"] code.hljs,
        [data-testid="stExpander"] [data-testid="stCode"] code.hljs {
            color: #EEF2FF !important;
        }

        .footer-note {
            margin-top: 1.4rem;
            padding-top: 0.9rem;
            border-top: 1px solid var(--line);
            color: var(--soft);
            font-size: 0.82rem;
            text-align: center;
            line-height: 1.55;
        }

        .footer-note a {
            color: var(--accent);
            text-decoration: none;
            border-bottom: 1px solid rgba(134, 168, 255, 0.35);
        }

        .footer-note a:hover {
            color: var(--accent-strong);
            border-bottom-color: var(--accent-strong);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# State models
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class DemoState:
    question: str
    weak_sql: str
    strong_sql: str
    validation: ValidationResult


@dataclass(frozen=True)
class Scene:
    key: str
    title: str
    render: Callable[[DemoState], None]


@dataclass(frozen=True)
class PresentationCodeSnippet:
    title: str
    business_message: str
    code: str
    discussion_point: str


# -----------------------------------------------------------------------------
# Curated code snippets for scene 10
# -----------------------------------------------------------------------------


PRESENTATION_CODE_SNIPPETS = [
    PresentationCodeSnippet(
        title="1. Słownik — definicja KPI jako dane wejściowe dla AI",
        business_message=(
            "To jest zwykły słownik Pythona. Ale w praktyce może reprezentować definicję KPI, "
            "którą model AI dostaje jako kontekst."
        ),
        code='''kpi_definition = {
    "name": "gross_margin_pct",
    "business_definition": "Marża brutto jako procent przychodu",
    "formula": "(revenue - cost) / revenue",
    "owner": "Finance Controlling",
}

question = "Które oddziały mają największy spadek wyników rok do roku?"

# AI nie powinno zgadywać, czym jest „wynik”.
# Python przekazuje mu definicję biznesową.
''',
        discussion_point=(
            "To łączy Waszą wiedzę finansową z technologią. KPI nie jest magicznym polem w raporcie — "
            "to definicja, którą można zapisać i przekazać systemowi."
        ),
    ),
    PresentationCodeSnippet(
        title="2. Funkcja — Python buduje instrukcję dla AI",
        business_message=(
            "Funkcja bierze pytanie, definicję KPI i opis danych, a potem składa z tego prompt dla modelu."
        ),
        code='''def build_prompt(question, kpi_definition, table_description):
    return f"""
    Pytanie użytkownika:
    {question}

    Definicja KPI:
    {kpi_definition["name"]}: {kpi_definition["business_definition"]}
    Wzór: {kpi_definition["formula"]}

    Dostępne dane:
    {table_description}

    Wygeneruj SQL zgodny z definicją KPI.
    """


prompt = build_prompt(
    question,
    kpi_definition,
    "branch_monthly_performance: branch, month, revenue, cost",
)
''',
        discussion_point=(
            "To nie jest zaawansowana magia. To funkcja. Różnica polega na tym, że dziś taka funkcja "
            "może sterować modelem AI, a nie tylko liczyć wartość w tabeli."
        ),
    ),
    PresentationCodeSnippet(
        title="3. If — Python kontroluje wynik AI",
        business_message=(
            "Warunki z podstaw Pythona mogą być prostą warstwą bezpieczeństwa dla wygenerowanego SQL."
        ),
        code='''blocked_words = ["DROP", "DELETE", "TRUNCATE", "UPDATE"]

generated_sql = "SELECT * FROM branch_monthly_performance"
issues = []

for word in blocked_words:
    if word in generated_sql.upper():
        issues.append(f"Zablokowane słowo: {word}")

if "WHERE" not in generated_sql.upper():
    issues.append("Brak filtra — zapytanie może pobrać za dużo danych")

if issues:
    print("Nie uruchamiamy zapytania:", issues)
else:
    print("Zapytanie może zostać wykonane")
''',
        discussion_point=(
            "AI może wygenerować kod, ale nie musi dostać pełnego zaufania. Prosty `if` może zdecydować, "
            "czy wynik AI przechodzi dalej, czy zostaje zatrzymany."
        ),
    ),
    PresentationCodeSnippet(
        title="4. Pandas — mierzymy, czy agentowi można ufać",
        business_message=(
            "DataFrame z logami pozwala sprawdzić, czy agent działa dobrze i gdzie popełnia błędy."
        ),
        code='''import pandas as pd

logs = pd.DataFrame([
    {"context": "strong", "status": "success"},
    {"context": "strong", "status": "success"},
    {"context": "weak", "status": "failed"},
    {"context": "weak", "status": "failed"},
])

logs["failed"] = logs["status"] == "failed"

failure_rate = logs.groupby("context")["failed"].mean()

print(failure_rate)
''',
        discussion_point=(
            "To jest dokładnie ten sam pandas, którego używa się w analizie danych. Tylko tutaj analizujemy nie sprzedaż, "
            "ale jakość działania systemu AI."
        ),
    ),
]


# -----------------------------------------------------------------------------
# Data helpers
# -----------------------------------------------------------------------------


@st.cache_data(show_spinner=False)
def load_observability_data() -> tuple[pd.DataFrame, object]:
    logs_df = get_agent_logs()
    summary = compute_summary(logs_df)
    return logs_df, summary


@st.cache_data(show_spinner=False)
def load_customer_data() -> pd.DataFrame:
    return create_customer_profitability_data()


def build_demo_state() -> DemoState:
    weak_sql = mock_llm_generate_sql(DEFAULT_QUESTION, WEAK_CONTEXT)
    strong_sql = mock_llm_generate_sql(DEFAULT_QUESTION, STRONG_CONTEXT)
    validation = validate_sql(strong_sql)
    return DemoState(
        question=DEFAULT_QUESTION,
        weak_sql=weak_sql,
        strong_sql=strong_sql,
        validation=validation,
    )


# -----------------------------------------------------------------------------
# UI helpers
# -----------------------------------------------------------------------------


def render_eyebrow(text: str) -> None:
    st.markdown(f'<div class="eyebrow">{text}</div>', unsafe_allow_html=True)


def render_big_title(text: str) -> None:
    st.markdown(f'<div class="big-title">{text}</div>', unsafe_allow_html=True)


def render_medium_title(text: str) -> None:
    st.markdown(f'<div class="medium-title">{text}</div>', unsafe_allow_html=True)


def render_subtitle(text: str) -> None:
    st.markdown(f'<div class="subtitle">{text}</div>', unsafe_allow_html=True)


def render_section_title(text: str) -> None:
    st.markdown(f'<div class="section-title">{text}</div>', unsafe_allow_html=True)


def render_progress(scene_no: int, total: int) -> None:
    progress_pct = int(scene_no / total * 100)
    st.markdown(
        f'<div class="progress-line"><div class="progress-fill" style="width: {progress_pct}%"></div></div>',
        unsafe_allow_html=True,
    )


def render_pills(labels: list[str]) -> None:
    html_text = "".join(f'<span class="pill">{label}</span>' for label in labels)
    st.markdown(html_text, unsafe_allow_html=True)


def render_card(title: str, body: str, *, strong: bool = False) -> None:
    class_name = "card-strong" if strong else "card"
    st.markdown(
        f"""
        <div class="{class_name}">
            <div class="card-title">{title}</div>
            <div class="muted">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_big_number(number: str, caption: str, *, accent: bool = False) -> None:
    accent_class = " huge-number-accent" if accent else ""
    st.markdown(
        f"""
        <div class="card-strong">
            <div class="huge-number{accent_class}">{number}</div>
            <div class="muted">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_statement(text: str) -> None:
    st.markdown(f'<div class="statement">{text}</div>', unsafe_allow_html=True)


def render_flow_steps(steps: list[tuple[str, str]]) -> None:
    """Numerowany przepływ kroków w stabilnym układzie Streamlit columns."""
    for idx, (label, hint) in enumerate(steps, start=1):
        num_col, text_col = st.columns([0.085, 0.915], vertical_alignment="top")
        with num_col:
            st.markdown(
                f'<div class="flow-step-num" aria-hidden="true">{idx}</div>',
                unsafe_allow_html=True,
            )
        with text_col:
            st.markdown(f"**{label}**")
            st.caption(hint)
        if idx < len(steps):
            st.markdown('<div class="flow-step-spacer"></div>', unsafe_allow_html=True)


def render_insight_list(items: list[tuple[bool, str]]) -> None:
    rows = []
    for is_good, text in items:
        cls = "good" if is_good else "bad"
        ico = "✓" if is_good else "✕"
        rows.append(
            f'<div class="insight-row {cls}"><span class="ico">{ico}</span>{text}</div>'
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


def render_foundation_item(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="foundation-item">
            <strong>{html.escape(title)}</strong>
            <span>{html.escape(body)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_validation(result: ValidationResult) -> None:
    if not result.issues:
        st.success("Zapytanie jest bezpieczne — przeszło wszystkie sprawdzenia.")
        return

    if result.is_valid:
        st.warning(f"Zapytanie przeszło, ale z uwagami ({len(result.issues)}).")
    else:
        st.error(f"Zapytanie zatrzymane — wykryto ryzyko ({len(result.issues)}).")

    severity_label = {
        Severity.HIGH: ("BLOKADA", "🚫"),
        Severity.MEDIUM: ("UWAGA", "⚠️"),
        Severity.LOW: ("INFO", "ℹ️"),
    }
    for issue in result.issues:
        label, icon = severity_label[issue.severity]
        line = f"{label} — {issue.message}"
        if issue.severity is Severity.HIGH:
            st.error(line, icon=icon)
        elif issue.severity is Severity.MEDIUM:
            st.warning(line, icon=icon)
        else:
            st.info(line, icon=icon)


def run_agent(state: DemoState) -> None:
    """Live demo: pokazuje pięć kroków przepływu z animowanym statusem."""
    with st.status("Asystent AI pracuje…", expanded=True) as status:
        st.write("1. Łączy pytanie z definicjami biznesowymi.")
        time.sleep(0.25)
        prompt = build_prompt(state.question, STRONG_CONTEXT)

        st.write("2. Pisze zapytanie do bazy danych.")
        time.sleep(0.25)

        st.write("3. Sprawdza, czy zapytanie jest bezpieczne.")
        time.sleep(0.25)

        if not state.validation.is_valid:
            status.update(label="Zapytanie zatrzymane.", state="error")
            st.error("Wynik nie powstał — sprawdzenie wykryło ryzyko.")
            render_section_title("Wygenerowane SQL (zatrzymane przed hurtownią)")
            st.code(state.strong_sql, language="sql")
            render_validation(state.validation)
            return

        st.write("4. Wykonuje zapytanie w hurtowni i pobiera dane.")
        time.sleep(0.25)
        result = execute_mock_query(state.strong_sql)

        st.write(
            "5. Prezentuje wynik: tabela (wizualizacja danych) oraz krótkie podsumowanie "
            "tekstowe zrozumiałe dla użytkownika biznesowego."
        )
        time.sleep(0.25)
        insight = summarize_result(result)
        status.update(label="Gotowe.", state="complete")

    render_section_title("Wygenerowane SQL (mock LLM)")
    st.code(state.strong_sql, language="sql")
    render_section_title("Walidacja przed hurtownią")
    render_validation(state.validation)
    st.markdown('<div style="height: 0.45rem;"></div>', unsafe_allow_html=True)

    left, right = st.columns([1.05, 1.95], vertical_alignment="top")
    with left:
        render_section_title("Odpowiedź dla biznesu")
        st.success(insight)
        st.metric("Liczba wierszy w wyniku", result.row_count)
        st.caption(result.note)

    with right:
        render_section_title("Dane z bazy")
        st.dataframe(result.rows, width="stretch", hide_index=True)

    with st.expander("Co dokładnie zobaczył model AI"):
        st.code(prompt, language="text")


def go_previous() -> None:
    st.session_state.scene_idx = max(0, st.session_state.scene_idx - 1)


def go_next() -> None:
    st.session_state.scene_idx = min(len(SCENES) - 1, st.session_state.scene_idx + 1)


def render_top_navigation() -> None:
    current_scene = SCENES[st.session_state.scene_idx]
    total = len(SCENES)
    scene_no = st.session_state.scene_idx + 1

    nav_left, nav_middle, nav_right = st.columns([0.75, 3.8, 0.75], vertical_alignment="center")

    with nav_left:
        st.button(
            "← Wstecz",
            use_container_width=True,
            disabled=st.session_state.scene_idx == 0,
            on_click=go_previous,
            key="top_prev",
        )

    with nav_middle:
        st.markdown(
            f"""
            <div class="top-bar-title">Python w erze AI · Demo</div>
            <div class="top-bar-current">
                <span class="scene-counter">{scene_no}/{total}</span>
                {current_scene.title}
            </div>
            """,
            unsafe_allow_html=True,
        )
        render_progress(scene_no, total)

    with nav_right:
        st.button(
            "Dalej →",
            use_container_width=True,
            disabled=st.session_state.scene_idx == total - 1,
            on_click=go_next,
            key="top_next",
        )

    st.markdown('<div class="nav-spacer"></div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Scenes
# -----------------------------------------------------------------------------


def scene_hook(_: DemoState) -> None:
    st.markdown(
        """
        <div class="hero-panel">
            <div class="eyebrow">Python w erze AI</div>
            <div class="big-title">AI odpowiada szybko. Ale czy odpowiada na właściwe pytanie?</div>
            <div class="subtitle">
                Wiarygodnie brzmiąca odpowiedź od AI może być technicznie poprawna
                i biznesowo błędna jednocześnie. Ta prezentacja pokazuje, co tworzy różnicę.
            </div>
            <div class="hero-meta">
                Ta prezentacja w przeglądarce — interfejs, logika i demo — jest w całości napisana
                w Pythonie (Streamlit). Kod i instrukcje uruchomienia:
                <a class="hero-repo-link" href="https://github.com/Smalou/python-analiza-danych" target="_blank" rel="noopener noreferrer">github.com/Smalou/python-analiza-danych</a>.
                <div class="hero-author">Autorka materiału: Sylwia Malinowska.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_statement(
        "Technicznie poprawny kod może nadal dawać błędną odpowiedź biznesową."
    )


def scene_python_pipeline(state: DemoState) -> None:
    render_eyebrow("Python łączy biznes z AI")
    render_medium_title("Pytanie po polsku — wynik z bazy. Python prowadzi wszystko pomiędzy.")
    render_subtitle(
        "Użytkownik nie musi znać SQL ani Pythona. Pisze pytanie tak, jak zapytałby "
        "kolegę z działu finansów. Reszta dzieje się pod spodem."
    )

    left, right = st.columns([1, 1.25], vertical_alignment="top")
    with left:
        render_section_title("Pytanie od osoby z działu finansów")
        st.info(f'"{state.question}"')
        render_section_title("Trudność zaczyna się pod spodem")
        render_insight_list(
            [
                (False, 'Co znaczy „rentowny" — najwyższy przychód, najwyższy zysk, czy najwyższa marża %?'),
                (False, 'Kto to „klient" — firma fakturowana czy każdy oddział?'),
                (False, 'Jakiego okresu dotyczy „ostatni kwartał" — bieżący, ostatni zamknięty?'),
            ]
        )
    with right:
        render_section_title("Co Python robi z tym pytaniem — krok po kroku")
        render_flow_steps(
            [
                ("Pytanie biznesowe", "Użytkownik pisze normalne pytanie po polsku."),
                ("Kontekst biznesowy", "Python sięga po definicje KPI, opisy tabel, słownik firmy."),
                ("Polecenie dla AI", "Składa pytanie + kontekst w jedną instrukcję dla modelu."),
                ("Zapytanie do bazy", "Model zwraca SQL — Python go przejmuje."),
                ("Sprawdzenie bezpieczeństwa", "Czy zapytanie nie usuwa danych? Czy ma sens?"),
                ("Wynik dla biznesu", "Tabela z bazy + krótki komentarz w języku użytkownika."),
            ]
        )

    render_statement(
        "Python nie jest tu „kolejnym językiem programowania”. Jest warstwą, która łączy "
        "język biznesu, model AI i hurtownię danych."
    )


def scene_ambiguity(_: DemoState) -> None:
    """Trzy interpretacje 'rentownego klienta' — każda daje innego zwycięzcę."""
    render_eyebrow("To samo pytanie. Trzy możliwe odpowiedzi")
    render_medium_title('AI nie wie, co znaczy „rentowny", dopóki organizacja tego nie zdefiniuje.')
    render_subtitle(
        'Bez słownika firmy pytanie ma trzy technicznie poprawne odpowiedzi — '
        'i każda wskazuje innego klienta jako „najlepszego".'
    )

    df = load_customer_data()
    revenue_df = top_by_revenue(df)
    profit_df = top_by_gross_profit(df)
    margin_df = top_by_gross_margin(df)

    top_rev = revenue_df.iloc[0]
    top_prof = profit_df.iloc[0]
    top_marg = margin_df.iloc[0]

    c1, c2, c3 = st.columns(3, vertical_alignment="top")

    with c1:
        render_section_title("1. Wg przychodu netto")
        st.metric("Top klient", top_rev["customer_name"], f'{top_rev["net_revenue"]/1e6:.2f} M PLN')
        st.dataframe(
            revenue_df.rename(columns={
                "customer_name": "Klient",
                "net_revenue": "Przychód",
                "gross_profit": "Zysk",
                "gross_margin_pct": "Marża %",
            }).style.format({"Przychód": "{:,.0f}", "Zysk": "{:,.0f}", "Marża %": "{:.1f}"}),
            hide_index=True,
            width="stretch",
        )
        st.caption('Interpretacja: „rentowny" = ma duży obrót.')

    with c2:
        render_section_title("2. Wg zysku brutto")
        st.metric("Top klient", top_prof["customer_name"], f'{top_prof["gross_profit"]/1e3:.0f} k PLN')
        st.dataframe(
            profit_df.rename(columns={
                "customer_name": "Klient",
                "net_revenue": "Przychód",
                "gross_profit": "Zysk",
                "gross_margin_pct": "Marża %",
            }).style.format({"Przychód": "{:,.0f}", "Zysk": "{:,.0f}", "Marża %": "{:.1f}"}),
            hide_index=True,
            width="stretch",
        )
        st.caption('Interpretacja: „rentowny" = zostawia najwięcej zysku w PLN.')

    with c3:
        render_section_title("3. Wg marży brutto %")
        st.metric("Top klient", top_marg["customer_name"], f'{top_marg["gross_margin_pct"]:.0f}%')
        st.dataframe(
            margin_df.rename(columns={
                "customer_name": "Klient",
                "net_revenue": "Przychód",
                "gross_profit": "Zysk",
                "gross_margin_pct": "Marża %",
            }).style.format({"Przychód": "{:,.0f}", "Zysk": "{:,.0f}", "Marża %": "{:.1f}"}),
            hide_index=True,
            width="stretch",
        )
        st.caption('Interpretacja: „rentowny" = najwyższy procent marży.')

    st.markdown('<div style="height: 0.6rem;"></div>', unsafe_allow_html=True)
    st.warning(
        f"**Trzej zwycięzcy, ta sama firma:** {top_rev['customer_name']} (przychód), "
        f"{top_prof['customer_name']} (zysk), {top_marg['customer_name']} (marża %). "
        "Bez metadanych model nie analizuje finansów. On zgaduje finanse."
    )

    render_statement(
        "Technicznie poprawny kod może nadal dawać błędną odpowiedź biznesową."
    )


def scene_metadata_resolution(state: DemoState) -> None:
    """Definicje słownika firmy zamieniają trzy odpowiedzi w jedną poprawną."""
    render_eyebrow("Metadane zmieniają wszystko")
    render_medium_title("Niejednoznaczny prompt → kontrolowane pytanie analityczne.")
    render_subtitle(
        'Słownik firmy ustala, co znaczy „rentowny", „klient" i „kwartał". '
        'Te trzy definicje zamieniają niejednoznaczność w jedną odpowiedź.'
    )

    left, right = st.columns([1, 1.15], vertical_alignment="top")

    with left:
        render_section_title("Co mówi słownik firmy")
        st.markdown(
            "- **Klient** — podmiot fakturowany w danym kwartale\n"
            "- **Rentowność** — ranking po **`gross_profit`** "
            "(marża % to miara wspierająca, nie podstawowa)\n"
            "- **Ostatni kwartał** — ostatni w pełni zamknięty kwartał kalendarzowy "
            f"(dziś: **{LAST_CLOSED_QUARTER}**)\n"
            "- **Przychód** — `net_revenue` (bez VAT, po korektach faktur)\n"
            "- **Koszt** — `direct_service_cost` (bez kosztów ogólnozakładowych)\n"
            "- **Mali klienci** — poniżej 100 tys. PLN wykluczeni z rankingu marżowego, "
            "by uniknąć mylących wyników procentowych"
        )

        render_section_title("Wygenerowane zapytanie SQL")
        st.code(state.strong_sql, language="sql")

    with right:
        render_section_title("Jednoznaczna odpowiedź")

        result = execute_mock_query(state.strong_sql)
        top = result.rows.iloc[0]

        st.success(
            f"**Najbardziej rentowny klient w {LAST_CLOSED_QUARTER}: "
            f"{top['customer_name']}**"
        )

        k1, k2, k3 = st.columns(3)
        k1.metric("Zysk brutto", f"{top['gross_profit']/1e3:,.0f} k PLN")
        k2.metric("Przychód netto", f"{top['net_revenue']/1e3:,.0f} k PLN")
        k3.metric("Marża brutto", f"{top['gross_margin_pct']:.1f}%")

        st.markdown('<div style="height: 0.4rem;"></div>', unsafe_allow_html=True)
        render_section_title("Pełny ranking po zysku brutto")
        st.dataframe(
            result.rows.rename(columns={
                "customer_name": "Klient",
                "net_revenue": "Przychód",
                "gross_profit": "Zysk brutto",
                "gross_margin_pct": "Marża %",
            }).style.format({"Przychód": "{:,.0f}", "Zysk brutto": "{:,.0f}", "Marża %": "{:.1f}"}),
            hide_index=True,
            width="stretch",
        )

    render_statement(
        "Dobre metadane zamieniają niejednoznaczny prompt w kontrolowane pytanie analityczne."
    )


def scene_live_demo(state: DemoState) -> None:
    render_eyebrow("Demo na żywo")
    render_medium_title("Cały pipeline z poprzednich slajdów — w jednym kliknięciu.")

    if "live_demo_question" not in st.session_state:
        st.session_state.live_demo_question = DEFAULT_QUESTION

    st.markdown('<div style="height: 0.35rem;"></div>', unsafe_allow_html=True)
    render_section_title("Pytanie od użytkownika")
    st.text_area(
        "Pytanie biznesowe",
        key="live_demo_question",
        height=110,
        label_visibility="collapsed",
    )

    if st.button("▶ Uruchom asystenta AI", type="primary", use_container_width=False):
        q = st.session_state.live_demo_question
        run_sql = mock_llm_generate_sql(q, STRONG_CONTEXT)
        live_state = DemoState(
            question=q,
            weak_sql=state.weak_sql,
            strong_sql=run_sql,
            validation=validate_sql(run_sql),
        )
        run_agent(live_state)


def scene_trust(state: DemoState) -> None:
    render_eyebrow("Skąd wiemy, że agentowi można ufać")
    render_medium_title("Walidacja sprawdza jedno pytanie. Pomiar — tysiąc pytań.")
    render_subtitle(
        "Zaufanie do AI nie wynika z wiary. Wynika z dwóch warstw kontroli: "
        "blokady ryzykownych zapytań i pomiaru, jak agent radzi sobie na dłuższą metę."
    )

    render_section_title("1. Kontrola pojedynczego zapytania — zanim trafi do hurtowni")

    risky_sql = "DROP TABLE branch_monthly_performance"
    c1, c2 = st.columns(2, vertical_alignment="top")
    with c1:
        st.markdown("**✓ Zapytanie wygenerowane z kontekstem**")
        st.code(state.strong_sql, language="sql")
        render_validation(validate_sql(state.strong_sql))
    with c2:
        st.markdown("**✕ Zapytanie, które zniszczyłoby dane**")
        st.code(risky_sql, language="sql")
        render_validation(validate_sql(risky_sql))

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)
    render_section_title("2. Pomiar tysiąca zapytań — czy agent jest skuteczny")

    logs_df, summary = load_observability_data()
    success_pct = (
        round((summary.successful_runs / summary.total_runs) * 100, 1)
        if summary.total_runs
        else 0.0
    )

    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Zadanych pytań", summary.total_runs)
    kpi2.metric("Odpowiedzi nadających się do raportu", f"{success_pct}%")
    kpi3.metric("Średni czas odpowiedzi", f"{summary.avg_response_time_seconds}s")

    chart_col, table_col = st.columns([1, 1.6], vertical_alignment="top")
    with chart_col:
        st.markdown("**Wynik zależy od jakości kontekstu**")
        failure_df = (
            pd.DataFrame({"% błędnych odpowiedzi": summary.failure_rate_by_metadata})
            .rename_axis("Jakość kontekstu")
            .reset_index()
        )
        st.bar_chart(failure_df, x="Jakość kontekstu", y="% błędnych odpowiedzi", height=280)
        st.caption(
            "Z dobrym kontekstem agent pomyłki praktycznie nie robi. Bez kontekstu — zgaduje."
        )
    with table_col:
        st.markdown("**Ostatnie pytania i ich wyniki**")
        logs_view = logs_df.rename(
            columns={
                "question_id": "id",
                "user_question": "pytanie",
                "metadata_quality": "kontekst",
                "sql_validation_status": "sprawdzenie",
                "execution_status": "wynik",
                "response_time_seconds": "czas (s)",
                "rows_returned": "wierszy",
            }
        )
        st.dataframe(logs_view, width="stretch", hide_index=True, height=280)

    render_statement(
        "W realnym świecie nie pytamy „czy AI dało odpowiedź”. Pytamy: ile razy odpowiedź "
        "była poprawna, użyteczna i bezpieczna — a sam pomiar to audyt jakości AI, "
        "ta sama dyscyplina, co audyt finansowy."
    )


def scene_foundations_code(_: DemoState) -> None:
    render_eyebrow("Moment aha")
    render_medium_title("Wszystko, co właśnie zobaczyliście, zbudowane jest z tego, co znacie z zajęć.")
    render_subtitle(
        "Zaawansowany system AI to nie magia. To słownik, funkcja, warunek i pandas — "
        "ułożone w przepływ."
    )

    render_section_title("Fundament z zajęć ↔ rola w systemie AI")
    left, right = st.columns([1.05, 1.15], vertical_alignment="top")
    with left:
        st.markdown('<div class="foundation-grid">', unsafe_allow_html=True)
        render_foundation_item("Słowniki", "Przechowują definicje KPI, konfigurację i kontekst biznesowy.")
        render_foundation_item("Funkcje", "Dzielą proces na kroki: prompt, walidacja, wykonanie, wynik.")
        render_foundation_item("if / warunki", "Kontrolują, czy wynik AI można bezpiecznie wykonać.")
        render_foundation_item("pandas", "Analizuje dane, logi, skuteczność i błędy działania systemu.")
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        render_flow_steps(
            [
                ("Słownik KPI", "Definicja marży, właściciel, wzór, opis biznesowy."),
                ("Funkcja promptu", "Składa pytanie użytkownika z kontekstem dla AI."),
                ("Warunek bezpieczeństwa", "Blokuje ryzykowne zapytania przed wykonaniem."),
                ("DataFrame z logami", "Pokazuje, kiedy agent działa, a kiedy się myli."),
            ]
        )

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)
    render_section_title("A teraz dokładnie ten sam kod — w czterech fragmentach")
    st.markdown('<div class="before-code-tabs"></div>', unsafe_allow_html=True)

    snippet_tabs = st.tabs([snippet.title.split(" — ")[0] for snippet in PRESENTATION_CODE_SNIPPETS])
    for tab, snippet in zip(snippet_tabs, PRESENTATION_CODE_SNIPPETS):
        with tab:
            l, r = st.columns([0.9, 1.45], vertical_alignment="top", gap="large")
            with l:
                render_section_title(snippet.title)
                st.markdown(
                    f"<div class='real-code-explain'>{html.escape(snippet.business_message)}</div>",
                    unsafe_allow_html=True,
                )
                st.info(snippet.discussion_point)
            with r:
                st.code(snippet.code, language="python")

    render_statement(
        "Jeśli rozumiecie słownik, funkcję, if i pandas — rozumiecie fundament. "
        "Reszta to ułożenie tych klocków w przepływ."
    )


def scene_conclusion(_: DemoState) -> None:
    st.markdown(
        """
        <div class="hero-panel">
            <div class="eyebrow">Podsumowanie</div>
            <div class="big-title">Metadane to nie dokumentacja. To warstwa kontroli.</div>
            <div class="subtitle">
                AI-augmented analytics jest wiarygodne tylko wtedy, gdy AI ma dostęp
                do jasnych definicji biznesowych. Bez nich generuje wiarygodnie brzmiące,
                ale biznesowo błędne odpowiedzi.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        render_card(
            "Bez metadanych",
            'AI zgaduje, co znaczy „rentowny", „klient" i „okres". '
            'Trzy interpretacje, trzy odpowiedzi, brak kontroli.',
        )
    with c2:
        render_card(
            "Z metadanymi",
            "Słownik firmy zamienia niejednoznaczny prompt w kontrolowane pytanie "
            "analityczne. Jedna definicja, jedna odpowiedź.",
            strong=True,
        )

    render_statement(
        "Największą przewagą nie będzie samo używanie AI. Będzie nią umiejętność zdefiniowania "
        "metadanych, które robią z modelu narzędzie biznesowe — a nie generator wiarygodnych odpowiedzi."
    )


SCENES: list[Scene] = [
    Scene("hook", "AI odpowiada szybko. Ale czy właściwie?", scene_hook),
    Scene("python_pipeline", "Python łączy biznes z AI", scene_python_pipeline),
    Scene("ambiguity", "To samo pytanie. Trzy możliwe odpowiedzi.", scene_ambiguity),
    Scene("metadata_resolution", "Metadane zmieniają wszystko", scene_metadata_resolution),
    Scene("live_demo", "Demo na żywo", scene_live_demo),
    Scene("trust", "Skąd wiemy, że agentowi można ufać", scene_trust),
    Scene("foundations_code", "Słownik, funkcja, if, pandas", scene_foundations_code),
    Scene("conclusion", "Metadane jako warstwa kontroli", scene_conclusion),
]


# -----------------------------------------------------------------------------
# App state + render
# -----------------------------------------------------------------------------

if "scene_idx" not in st.session_state:
    st.session_state.scene_idx = 0

state = build_demo_state()
render_top_navigation()
current_scene = SCENES[st.session_state.scene_idx]
current_scene.render(state)

st.markdown(
    '<div class="footer-note">'
    "Demo prezentacyjne · mock dane, mock AI · "
    "Python jako warstwa integracyjna między biznesem, danymi i AI · "
    "interfejs i logika w Streamlicie (Python).<br>"
    '<a href="https://github.com/Smalou/python-analiza-danych" target="_blank" rel="noopener noreferrer">'
    "Repozytorium na GitHubie"
    "</a>"
    " · Autorka materiałów: Sylwia Malinowska."
    "</div>",
    unsafe_allow_html=True,
)

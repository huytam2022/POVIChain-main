"""Reusable Streamlit widgets and CSS injector for the PoVIChain dashboard."""
import os
from typing import Optional

import streamlit as st

CSS = """
<style>
:root {
    --povi-primary: #7d3c98;
    --povi-accent:  #2980b9;
    --povi-good:    #27ae60;
    --povi-warn:    #e67e22;
    --povi-danger:  #c0392b;
    --povi-muted:   #7f8c8d;
}

/* App-wide font polish */
html, body, [class*="st-"] {
    font-family: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
}

/* Hero header gradient */
.povi-hero {
    background: linear-gradient(135deg, #2c3e50 0%, #7d3c98 100%);
    padding: 32px 28px 26px 28px;
    border-radius: 14px;
    color: #ffffff;
    margin-bottom: 18px;
    box-shadow: 0 6px 26px rgba(0,0,0,0.35);
}
.povi-hero h1 {
    margin: 0 0 6px 0;
    font-size: 30px;
    font-weight: 700;
    letter-spacing: -0.5px;
}
.povi-hero .subtitle {
    font-size: 14px;
    opacity: 0.85;
    margin-bottom: 8px;
}
.povi-hero .meta {
    font-size: 12px;
    opacity: 0.75;
}

/* Section header bar */
.povi-section {
    background: #1f2533;
    border-left: 4px solid var(--povi-primary);
    padding: 10px 16px;
    border-radius: 6px;
    margin: 18px 0 12px 0;
}
.povi-section h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    color: #ffffff;
}
.povi-section .caption {
    font-size: 12px;
    color: #aaaaaa;
    margin-top: 2px;
}

/* Metric tile */
.povi-tile {
    background: #1a1f2e;
    border: 1px solid #2a3144;
    border-radius: 10px;
    padding: 14px 16px;
    height: 100%;
}
.povi-tile .label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: #aaa;
    margin-bottom: 6px;
}
.povi-tile .value {
    font-size: 26px;
    font-weight: 700;
    color: #ffffff;
    line-height: 1.0;
}
.povi-tile .sub {
    font-size: 12px;
    color: #aaa;
    margin-top: 6px;
}

/* Card grid */
.povi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
}

/* Footer */
.povi-footer {
    text-align: center;
    color: #888;
    font-size: 11px;
    margin-top: 30px;
    padding-top: 14px;
    border-top: 1px solid #2a3144;
}

/* Banner (informational only) */
.povi-banner {
    padding: 10px 14px;
    border-radius: 8px;
    margin: 8px 0;
    font-size: 13px;
}
.povi-banner.ok    { background: rgba(39,174,96,0.12);  border-left: 3px solid #27ae60; color: #abf0c5; }
.povi-banner.warn  { background: rgba(230,126,34,0.12); border-left: 3px solid #e67e22; color: #f7c79b; }
.povi-banner.info  { background: rgba(41,128,185,0.12); border-left: 3px solid #2980b9; color: #b8dbf2; }

/* Chip row */
.povi-chip {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 11px;
    background: #2a3144;
    color: #d0d0d0;
    margin-right: 4px;
    margin-bottom: 4px;
}
.povi-chip.primary { background: var(--povi-primary); color: #fff; }
.povi-chip.accent  { background: var(--povi-accent);  color: #fff; }

/* De-emphasize sidebar default Streamlit footer */
[data-testid="stDecoration"] { display: none !important; }
</style>
"""


def inject_css() -> None:
    """Inject the dashboard's custom CSS exactly once per session."""
    if not st.session_state.get("_povi_css_injected"):
        st.markdown(CSS, unsafe_allow_html=True)
        st.session_state["_povi_css_injected"] = True


def hero(title: str, subtitle: str = "", meta: str = "") -> None:
    parts = [f"<h1>{title}</h1>"]
    if subtitle:
        parts.append(f"<div class='subtitle'>{subtitle}</div>")
    if meta:
        parts.append(f"<div class='meta'>{meta}</div>")
    st.markdown(
        f"<div class='povi-hero'>{''.join(parts)}</div>",
        unsafe_allow_html=True,
    )


def section(title: str, caption: str = "") -> None:
    cap = f"<div class='caption'>{caption}</div>" if caption else ""
    st.markdown(
        f"<div class='povi-section'><h2>{title}</h2>{cap}</div>",
        unsafe_allow_html=True,
    )


def tile(label: str, value: str, sub: str = "") -> None:
    """Plain metric tile: label / value / optional sub-text. No badges."""
    sub_html = f"<div class='sub'>{sub}</div>" if sub else ""
    st.markdown(
        f"<div class='povi-tile'><div class='label'>{label}</div>"
        f"<div class='value'>{value}</div>{sub_html}</div>",
        unsafe_allow_html=True,
    )


def banner(text: str, kind: str = "info") -> None:
    st.markdown(
        f"<div class='povi-banner {kind}'>{text}</div>",
        unsafe_allow_html=True,
    )


def chips(items, primary_first: bool = True) -> None:
    htmls = []
    for i, item in enumerate(items):
        cls = "primary" if (primary_first and i == 0) else ""
        htmls.append(f"<span class='povi-chip {cls}'>{item}</span>")
    st.markdown(" ".join(htmls), unsafe_allow_html=True)


def figure(image_path: str, caption: Optional[str] = None) -> None:
    if image_path and os.path.isfile(image_path):
        st.image(image_path, caption=caption, use_container_width=True)
    else:
        banner(
            f"Figure not yet generated: <code>{image_path}</code>. "
            "Run the corresponding experiment from the <em>Run Experiments</em> page.",
            kind="warn",
        )


def footer(extra: str = "") -> None:
    parts = [
        "PoVIChain — Smart City Platform",
        "Deterministic simulation — no protocol-logic edits",
    ]
    if extra:
        parts.append(extra)
    sep = "  ·  "
    st.markdown(
        f"<div class='povi-footer'>{sep.join(parts)}</div>",
        unsafe_allow_html=True,
    )

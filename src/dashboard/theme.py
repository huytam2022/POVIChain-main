"""Cinematic theme overlay for the demo page."""
from __future__ import annotations

import streamlit as st

CINEMATIC_CSS = """
<style>
/* ── Font ─────────────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');

/* ── Design tokens ────────────────────────────────────────────────────────── */
:root {
  --bg:        #080c15;
  --bg-2:      #0d1422;
  --bg-3:      #131c2e;
  --border:    rgba(255,255,255,0.065);
  --accent:    #2dd4bf;
  --accent-lo: rgba(45,212,191,0.10);
  --accent-md: rgba(45,212,191,0.22);
  --text:      #dce5f0;
  --text-2:    #8699b4;
  --text-3:    #4a5e78;
  --good:      #34d399;
  --warn:      #fbbf24;
  --bad:       #f87171;

  /* Legacy aliases kept for any existing component refs */
  --c-bg:        #080c15;
  --c-bg-soft:   #0d1422;
  --c-card:      rgba(13,20,34,0.85);
  --c-card-edge: rgba(45,212,191,0.18);
  --c-primary:   #2dd4bf;
  --c-primary-2: #60a5fa;
  --c-accent:    #2dd4bf;
  --c-good:      #34d399;
  --c-warn:      #fbbf24;
  --c-danger:    #f87171;
  --c-text:      #dce5f0;
  --c-text-dim:  #8699b4;
  --c-text-mute: #4a5e78;
}

/* ── Font application ─────────────────────────────────────────────────────── */
html, body, [class*="st-"], button, input, select, textarea {
  font-family: 'Outfit', 'Segoe UI', system-ui, -apple-system, sans-serif !important;
}
/* Khôi phục font icon của Streamlit — nếu không, ligature (vd "keyboard_arrow_right")
   render thành chữ thô đè lên nhãn (expander, nút...). */
span[data-testid="stIconMaterial"],
[data-testid="stExpanderToggleIcon"],
.material-icons, .material-icons-outlined,
[class*="material-symbols"] {
  font-family: 'Material Symbols Rounded', 'Material Symbols Outlined',
               'Material Icons', 'Material Icons Outlined' !important;
}

/* ── Kill ALL Streamlit chrome ────────────────────────────────────────────── */
#MainMenu, footer,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
.stDeployButton,
[data-testid="collapsedControl"] {
  display: none !important;
  visibility: hidden !important;
}
[data-testid="stHeader"] {
  background: transparent !important;
  height: 0 !important;
  min-height: 0 !important;
  overflow: hidden !important;
}

/* ── App shell ────────────────────────────────────────────────────────────── */
html, body { background: var(--bg) !important; }
section[data-testid="stMain"] > div { background: var(--bg) !important; }
section[data-testid="stMain"] .block-container {
  padding-top: 1.4rem !important;
  padding-bottom: 2rem !important;
  max-width: 1400px !important;
}

/* Custom scrollbar */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #1e2d40; border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: #2a3f58; }

/* Subtle noise overlay — breaks sterile flat look */
body::after {
  content: '';
  position: fixed; inset: 0;
  pointer-events: none;
  z-index: 9999;
  opacity: 0.55;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.035'/%3E%3C/svg%3E");
}

/* ── Tabs ─────────────────────────────────────────────────────────────────── */
[data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid var(--border) !important;
  gap: 0 !important;
  padding-bottom: 0 !important;
}
[data-baseweb="tab"] {
  background: transparent !important;
  color: var(--text-2) !important;
  font-size: 13.5px !important;
  font-weight: 500 !important;
  padding: 10px 18px !important;
  border-bottom: 2px solid transparent !important;
  border-radius: 0 !important;
  transition: color 0.15s, border-color 0.15s !important;
  letter-spacing: 0.1px !important;
}
[data-baseweb="tab"]:hover {
  color: var(--text) !important;
  background: rgba(255,255,255,0.02) !important;
}
[aria-selected="true"][data-baseweb="tab"] {
  color: var(--accent) !important;
  border-bottom-color: var(--accent) !important;
  background: transparent !important;
  font-weight: 600 !important;
}
[data-baseweb="tab-panel"] { padding-top: 18px !important; }

/* ── Text inputs ──────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input {
  background: var(--bg-3) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
  font-size: 14px !important;
  padding: 9px 12px !important;
  transition: border-color 0.15s, box-shadow 0.15s !important;
}
[data-testid="stTextInput"] input:hover {
  border-color: rgba(255,255,255,0.12) !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: var(--accent-md) !important;
  box-shadow: 0 0 0 3px var(--accent-lo) !important;
  outline: none !important;
}
[data-testid="stTextInput"] label p {
  color: var(--text-2) !important;
  font-size: 12.5px !important;
  font-weight: 500 !important;
  margin-bottom: 4px !important;
}

/* Number input */
[data-testid="stNumberInput"] input {
  background: var(--bg-3) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
}
[data-testid="stNumberInput"] label p {
  color: var(--text-2) !important;
  font-size: 12.5px !important;
  font-weight: 500 !important;
}

/* ── Slider ───────────────────────────────────────────────────────────────── */
[data-testid="stSlider"] label p {
  color: var(--text-2) !important;
  font-size: 12.5px !important;
  font-weight: 500 !important;
}
[data-testid="stSlider"] [role="slider"] {
  background: var(--accent) !important;
  border: 2px solid var(--bg) !important;
  box-shadow: 0 0 0 3px var(--accent-lo) !important;
}
[data-testid="stSlider-track"] { background: var(--bg-3) !important; }
[data-testid="stSlider-track-filled"] { background: var(--accent) !important; }
[data-testid="stSlider"] [data-testid="stTickBarMin"],
[data-testid="stSlider"] [data-testid="stTickBarMax"] {
  color: var(--text-3) !important;
  font-size: 11px !important;
}

/* ── Radio (segmented pills) ──────────────────────────────────────────────── */
[data-testid="stRadio"] > label p {
  color: var(--text-2) !important;
  font-size: 12.5px !important;
  font-weight: 500 !important;
  margin-bottom: 6px !important;
}
/* Horizontal radio → segmented control look */
[data-testid="stRadio"] [role="radiogroup"] {
  gap: 7px !important;
}
[data-testid="stRadio"] [role="radiogroup"] > label {
  background: var(--bg-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 9px !important;
  padding: 8px 14px !important;
  margin: 0 !important;
  transition: border-color 0.15s, background 0.15s !important;
  cursor: pointer !important;
}
[data-testid="stRadio"] [role="radiogroup"] > label:hover {
  border-color: var(--accent-md) !important;
  background: var(--bg-3) !important;
}
/* Selected pill */
[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {
  border-color: var(--accent) !important;
  background: var(--accent-lo) !important;
}
[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) p {
  color: var(--accent) !important;
  font-weight: 600 !important;
}
/* Hide the actual radio dot — the pill itself shows state */
[data-testid="stRadio"] [role="radiogroup"] > label > div:first-child {
  display: none !important;
}
[data-testid="stRadio"] [role="radiogroup"] > label p {
  color: var(--text-2) !important;
  font-size: 13px !important;
}

/* ── Buttons ──────────────────────────────────────────────────────────────── */
[data-testid="stBaseButton-primary"] {
  background: var(--accent) !important;
  border: none !important;
  color: #030e0c !important;
  font-weight: 600 !important;
  font-size: 13.5px !important;
  border-radius: 8px !important;
  letter-spacing: 0.15px !important;
  transition: filter 0.15s, transform 0.1s !important;
}
[data-testid="stBaseButton-primary"]:hover  { filter: brightness(1.12) !important; }
[data-testid="stBaseButton-primary"]:active { transform: scale(0.98) translateY(1px) !important; }
[data-testid="stBaseButton-secondary"] {
  background: transparent !important;
  border: 1px solid var(--border) !important;
  color: var(--text-2) !important;
  font-weight: 500 !important;
  border-radius: 8px !important;
  transition: border-color 0.15s, color 0.15s !important;
}
[data-testid="stBaseButton-secondary"]:hover {
  border-color: var(--accent-md) !important;
  color: var(--text) !important;
}
[data-testid="stFormSubmitButton"] button {
  background: var(--accent) !important;
  border: none !important;
  color: #030e0c !important;
  font-weight: 600 !important;
  border-radius: 8px !important;
  transition: filter 0.15s !important;
}
[data-testid="stFormSubmitButton"] button:hover { filter: brightness(1.12) !important; }

/* ── Selectbox ────────────────────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
  background: var(--bg-3) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
}
[data-testid="stSelectbox"] label p {
  color: var(--text-2) !important;
  font-size: 12.5px !important;
  font-weight: 500 !important;
}

/* ── Form container ───────────────────────────────────────────────────────── */
[data-testid="stForm"] {
  background: var(--bg-2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  padding: 16px !important;
}

/* ── Divider ──────────────────────────────────────────────────────────────── */
hr, [data-testid="stDivider"] hr {
  border-color: var(--border) !important;
  margin: 10px 0 !important;
}

/* ── Caption ──────────────────────────────────────────────────────────────── */
[data-testid="stCaptionContainer"] p {
  color: var(--text-3) !important;
  font-size: 11.5px !important;
  line-height: 1.65 !important;
}

/* ── Alerts ───────────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
  border-radius: 8px !important;
  background: rgba(248,113,113,0.07) !important;
  border: 1px solid rgba(248,113,113,0.22) !important;
  color: var(--text) !important;
}
[data-testid="stAlert"][data-type="warning"] {
  background: rgba(251,191,36,0.07) !important;
  border-color: rgba(251,191,36,0.22) !important;
}
[data-testid="stAlert"][data-type="info"] {
  background: var(--accent-lo) !important;
  border-color: var(--accent-md) !important;
}

/* ── Inline code ──────────────────────────────────────────────────────────── */
code {
  background: var(--bg-3) !important;
  color: var(--accent) !important;
  border-radius: 4px !important;
  padding: 1px 6px !important;
  font-size: 0.88em !important;
}

/* ── Markdown text ────────────────────────────────────────────────────────── */
[data-testid="stMarkdownContainer"] p { color: var(--text) !important; }

/* ── Tabular numbers for data ─────────────────────────────────────────────── */
[data-testid="stMetricValue"] {
  font-variant-numeric: tabular-nums !important;
  font-weight: 700 !important;
}

/* ═══════════════════════════════════════════════════════════════════════════ */
/* CUSTOM COMPONENT CLASSES                                                    */
/* ═══════════════════════════════════════════════════════════════════════════ */

/* ── Login screen ─────────────────────────────────────────────────────────── */
/* Căn giữa do .block-container được scope ở trang login (xem 0_Demo.py) */
.login-mark {
  width: 50px; height: 50px; border-radius: 14px;
  background: var(--bg-3);
  border: 1px solid var(--accent-md);
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; color: var(--accent);
  margin: 0 auto 18px;
}
.login-eyebrow {
  font-size: 10px; letter-spacing: 3px; text-transform: uppercase;
  color: var(--accent); font-weight: 600; margin-bottom: 8px; text-align: center;
}
.login-title {
  font-size: 22px; font-weight: 700; color: var(--text);
  letter-spacing: -0.3px; margin-bottom: 4px; text-align: center;
}
.login-sub {
  font-size: 13px; color: var(--text-2);
  text-align: center; margin-bottom: 26px; line-height: 1.5;
}
.login-hint {
  font-size: 11px; color: var(--text-3);
  text-align: center; margin-top: 14px; line-height: 2;
}

/* ── App header bar ───────────────────────────────────────────────────────── */
.app-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 0 14px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 14px;
}
.app-bar-left { display: flex; align-items: center; gap: 11px; }
.app-bar-mark {
  width: 32px; height: 32px; border-radius: 8px;
  background: var(--bg-3); border: 1px solid var(--accent-md);
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; color: var(--accent);
}
.app-bar-eyebrow {
  font-size: 9px; letter-spacing: 2.5px; text-transform: uppercase;
  color: var(--accent); font-weight: 600; line-height: 1;
}
.app-bar-name {
  font-size: 14.5px; font-weight: 600; color: var(--text);
  letter-spacing: -0.15px; margin-top: 3px; line-height: 1;
  display: flex; align-items: center; gap: 9px;
}
.app-bar-role {
  font-size: 9px; letter-spacing: 1.6px; text-transform: uppercase;
  color: var(--accent); font-weight: 600;
  background: var(--accent-lo); border: 1px solid var(--accent-md);
  border-radius: 5px; padding: 3px 8px; line-height: 1;
}

/* ── Section anchors ──────────────────────────────────────────────────────── */
.scene-anchor {
  display: flex; align-items: center; gap: 11px;
  margin: 26px 0 12px;
}
.scene-no {
  width: 32px; height: 32px; border-radius: 9px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 13px;
  background: var(--accent-lo); border: 1px solid var(--accent-md);
  color: var(--accent);
}
.scene-title { font-size: 17px; font-weight: 700; color: var(--text); }
.scene-sub   { font-size: 11.5px; color: var(--text-2); margin-top: 1px; }

/* ── KPI / data cards ─────────────────────────────────────────────────────── */
.cine-card {
  background: var(--bg-2); border: 1px solid var(--border);
  border-radius: 12px; padding: 15px 17px; height: 100%;
}
.cine-card .k {
  font-size: 10px; letter-spacing: 1.5px; text-transform: uppercase;
  color: var(--text-3); margin-bottom: 6px;
}
.cine-card .v {
  font-size: 28px; font-weight: 800; color: var(--text);
  line-height: 1.0; font-variant-numeric: tabular-nums;
}
.cine-card .v small { font-size: 12px; color: var(--text-2); font-weight: 500; margin-left: 3px; }
.cine-card .s { font-size: 11.5px; color: var(--text-2); margin-top: 6px; line-height: 1.45; }
.cine-card .delta-up   { color: var(--good); font-weight: 700; }
.cine-card .delta-down { color: var(--bad);  font-weight: 700; }
.cine-card .delta-flat { color: var(--text-3); }
.cine-card.problem  { border-left: 2px solid var(--bad); }
.cine-card.solution { border-left: 2px solid var(--good); }

/* ── Hero banner ──────────────────────────────────────────────────────────── */
.cine-hero {
  position: relative; padding: 34px 30px 30px;
  border-radius: 14px; overflow: hidden;
  background:
    radial-gradient(50% 70% at 100% 0%, rgba(45,212,191,0.10) 0%, transparent 60%),
    radial-gradient(35% 55% at 0%  100%, rgba(96,165,250,0.07) 0%, transparent 60%),
    var(--bg-2);
  border: 1px solid var(--border);
}
.cine-hero-eyebrow {
  font-size: 10px; letter-spacing: 2.8px; text-transform: uppercase;
  color: var(--accent); font-weight: 600; margin-bottom: 10px;
}
.cine-hero-title {
  font-size: 30px; line-height: 1.1; font-weight: 800;
  letter-spacing: -0.5px; margin: 0 0 11px; color: var(--text);
}
.cine-hero-sub {
  font-size: 14px; color: var(--text-2); max-width: 780px; line-height: 1.6;
}
.cine-hero-meta { margin-top: 14px; display: flex; flex-wrap: wrap; gap: 7px; }
.cine-pill {
  display: inline-flex; align-items: center;
  padding: 3px 10px; border-radius: 5px;
  font-size: 11px; letter-spacing: 0.2px;
  background: var(--bg-3); color: var(--text-2); border: 1px solid var(--border);
}
.cine-pill.accent { background: var(--accent-lo); color: var(--accent); border-color: var(--accent-md); }
.cine-pill.primary { background: rgba(96,165,250,0.1); color: #93c5fd; border-color: rgba(96,165,250,0.2); }

/* ── Stage controls (admin overview) ─────────────────────────────────────── */
.stage-wrap {
  position: relative; width: 100%;
  border-radius: 12px; background: var(--bg-2);
  border: 1px solid var(--border); overflow: hidden;
}
.stage-wrap svg { width: 100%; height: auto; display: block; }

.stage-controls {
  display: grid; grid-template-columns: 1.5fr 1fr 1fr 1fr;
  gap: 10px; margin: 8px 0 12px;
}
.stage-kpi {
  background: var(--bg-3); border: 1px solid var(--border);
  border-radius: 10px; padding: 11px 13px; text-align: left;
}
.stage-kpi .k { font-size: 10px; letter-spacing: 1.4px; text-transform: uppercase; color: var(--text-3); }
.stage-kpi .v { font-size: 21px; font-weight: 800; color: var(--text); margin-top: 3px; line-height: 1; font-variant-numeric: tabular-nums; }
.stage-kpi .v small { font-size: 11px; color: var(--text-2); font-weight: 500; margin-left: 3px; }
.stage-kpi .s { font-size: 10.5px; color: var(--text-2); margin-top: 3px; }

.zone-tally {
  display: grid; grid-template-columns: repeat(6, 1fr);
  gap: 7px; margin-top: 11px;
}
.zone-tally .z {
  background: var(--accent-lo); border: 1px solid var(--accent-md);
  border-radius: 8px; padding: 7px; text-align: center;
}
.zone-tally .z .nm { font-size: 9.5px; letter-spacing: 0.8px; text-transform: uppercase; color: var(--text-2); }
.zone-tally .z .ct { font-size: 19px; font-weight: 800; color: var(--text); margin-top: 2px; line-height: 1; font-variant-numeric: tabular-nums; }
.zone-tally .z.empty .ct { color: var(--text-3); }

.stage-legend {
  display: flex; flex-wrap: wrap; gap: 12px;
  margin-top: 10px; font-size: 11px; color: var(--text-2);
  padding: 7px 10px; border-radius: 8px;
  background: var(--bg-3); border: 1px solid var(--border);
}
.stage-legend .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }
.stage-legend .dot.acc { background: var(--accent); }
.stage-legend .dot.pri { background: var(--accent); }
.stage-legend .dot.p2  { background: #60a5fa; }

/* ── Color band chips ─────────────────────────────────────────────────────── */
.band-ok    { color: var(--good);   }
.band-over  { color: var(--warn);   }
.band-under { color: var(--warn);   }
.band-na    { color: var(--text-3); }
.band-chip  {
  display: inline-block; padding: 2px 8px; border-radius: 5px;
  font-size: 10px; letter-spacing: 0.4px; text-transform: uppercase; margin-left: 6px;
}
.band-chip.ok    { background: rgba(52,211,153,0.1);  color: var(--good); }
.band-chip.over  { background: rgba(251,191,36,0.1);  color: var(--warn); }
.band-chip.under { background: rgba(251,191,36,0.1);  color: var(--warn); }
.band-chip.na    { background: var(--bg-3); color: var(--text-3); }

/* ── Trace / hash chip ────────────────────────────────────────────────────── */
.trace-chip {
  display: inline-flex; flex-wrap: wrap; gap: 5px;
  margin-top: 8px; padding: 6px 8px;
  background: var(--bg-3); border: 1px solid var(--border);
  border-radius: 7px; font-size: 10.5px; color: var(--text-2);
  font-family: ui-monospace, 'Cascadia Code', Menlo, Consolas, monospace;
}
.trace-chip-key { color: var(--text-3); margin-right: 2px; }
.trace-chip-val { color: var(--text); margin-right: 7px; }

/* ── Split layout ─────────────────────────────────────────────────────────── */
.split { display: grid; grid-template-columns: 1fr 1fr; gap: 13px; }
.split .panel { padding: 14px; border-radius: 11px; background: var(--bg-2); border: 1px solid var(--border); }
.split .panel.danger  { border-top: 2px solid var(--bad); }
.split .panel.safe    { border-top: 2px solid var(--good); }
.split .panel h4 { margin: 0 0 7px; color: var(--text); font-size: 14px; font-weight: 700; }
.split .panel .tag { font-size: 10px; letter-spacing: 1.3px; text-transform: uppercase; color: var(--text-3); }
.split .panel.danger .tag { color: var(--bad); }
.split .panel.safe   .tag { color: var(--good); }
.split .panel .row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 7px 0; border-bottom: 1px solid var(--border);
  font-size: 12.5px; color: var(--text-2);
}
.split .panel .row:last-child { border-bottom: 0; }
.split .panel .row b { color: var(--text); font-weight: 600; }

/* ── Tier grid ────────────────────────────────────────────────────────────── */
.tier-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 11px; }
.tier {
  border-radius: 11px; padding: 14px 15px 12px;
  background: var(--bg-2); border: 1px solid var(--border); min-height: 200px;
}
.tier .tier-tag { font-size: 10px; letter-spacing: 1.3px; text-transform: uppercase; color: var(--accent); margin-bottom: 7px; }
.tier .tier-title { font-size: 15px; font-weight: 700; color: var(--text); margin-bottom: 5px; }
.tier ul { margin: 7px 0 0; padding-left: 16px; color: var(--text-2); font-size: 12.5px; line-height: 1.65; }
.tier li::marker { color: var(--accent); }
.tier.l1 { border-top: 2px solid var(--accent); }
.tier.l2 { border-top: 2px solid #60a5fa; }
.tier.l3 { border-top: 2px solid #a78bfa; }

/* ── Flow rail ────────────────────────────────────────────────────────────── */
.flow-rail { position: relative; padding: 4px 0; }
.flow-rail .step {
  display: grid; grid-template-columns: 50px 1fr 130px;
  align-items: flex-start; column-gap: 12px;
  padding: 9px 0; border-bottom: 1px dashed var(--border);
}
.flow-rail .step:last-child { border-bottom: 0; }
.flow-rail .badge {
  width: 36px; height: 36px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 13px;
  background: var(--accent-lo); border: 1px solid var(--accent-md); color: var(--accent);
}
.flow-rail .step.l3 .badge {
  background: rgba(167,139,250,0.08); border-color: rgba(167,139,250,0.22); color: #a78bfa;
}
.flow-rail .step .ttl   { color: var(--text); font-weight: 600; font-size: 13.5px; }
.flow-rail .step .ttl small { color: var(--text-2); font-weight: 500; margin-left: 5px; }
.flow-rail .step .desc  { color: var(--text-2); font-size: 11.5px; margin-top: 2px; }
.flow-rail .step .dur   { color: var(--accent); font-size: 11.5px; font-variant-numeric: tabular-nums; text-align: right; }

/* ── Contrib highlight box ────────────────────────────────────────────────── */
.contrib {
  background: var(--accent-lo); border: 1px solid var(--accent-md);
  border-radius: 12px; padding: 15px 18px; color: var(--text);
}
.contrib h3 { margin: 0 0 7px; font-size: 16px; font-weight: 700; }
.contrib ul { margin: 5px 0 0; padding-left: 17px; color: var(--text-2); line-height: 1.75; font-size: 13px; }
.contrib li::marker { color: var(--accent); }
.cite { color: var(--text-3); font-size: 11px; margin-top: 5px; }

/* ── Minimal fade-up (motivated: entry reveal only) ───────────────────────── */
@keyframes fade-up {
  from { opacity: 0; transform: translateY(5px); }
  to   { opacity: 1; transform: translateY(0); }
}
.fade-up { animation: fade-up 0.35s ease both; }

/* ── SVG helpers ──────────────────────────────────────────────────────────── */
.spark-svg { width: 100%; height: 60px; display: block; }
.svg-arch  { width: 100%; height: auto; display: block; }
.stage-wrap svg { width: 100%; height: auto; display: block; }

/* ── Smooth scroll ────────────────────────────────────────────────────────── */
html { scroll-behavior: smooth; }

/* ── Inner-page components ────────────────────────────────────────────────── */

/* Transaction / confirmation banner */
.tx-banner {
  padding: 8px 13px; border-radius: 8px; margin: 6px 0 10px;
  background: var(--accent-lo); border: 1px solid var(--accent-md);
  color: var(--text); font-size: 12.5px; font-weight: 500;
}

/* Inner section heading (all-caps label between sections) */
.inner-sect {
  font-size: 9px; letter-spacing: 2.2px; text-transform: uppercase;
  color: var(--text-3); font-weight: 600; margin: 16px 0 8px;
  border-top: 1px solid var(--border); padding-top: 14px;
}

/* Node management table */
.node-tbl { width: 100%; border-collapse: collapse; }
.node-tbl th {
  text-align: left; font-size: 9.5px; letter-spacing: 1.5px;
  text-transform: uppercase; color: var(--text-3); padding: 5px 10px 9px;
  font-weight: 600; border-bottom: 1px solid var(--border);
}
.node-tbl td {
  padding: 9px 10px; border-bottom: 1px solid rgba(255,255,255,0.026);
  vertical-align: middle;
}
.node-tbl tr:last-child td { border-bottom: 0; }
.node-tbl tr:hover td { background: rgba(255,255,255,0.012); }

/* Monospace ID chip — reused in node & penalty tables */
.id-chip {
  font-family: ui-monospace, 'Cascadia Code', Menlo, Consolas, monospace;
  font-size: 11.5px; color: var(--accent);
  background: var(--accent-lo); border: 1px solid var(--accent-md);
  border-radius: 5px; padding: 2px 8px; display: inline-block;
  font-variant-numeric: tabular-nums; white-space: nowrap;
}

/* Reputation mini-bar */
.rep-bar {
  display: inline-block; width: 36px; height: 3px;
  border-radius: 2px; background: var(--bg-3);
  vertical-align: middle; margin-right: 7px; overflow: hidden;
}
.rep-fill { display: block; height: 100%; border-radius: 2px; }

/* Penalty log table */
.plog-tbl { width: 100%; border-collapse: collapse; }
.plog-tbl th {
  text-align: left; font-size: 9px; letter-spacing: 1.5px;
  text-transform: uppercase; color: var(--text-3); padding: 5px 8px 9px;
  font-weight: 600; border-bottom: 1px solid var(--border);
}
.plog-tbl td {
  padding: 8px 8px; border-bottom: 1px solid rgba(255,255,255,0.026);
  color: var(--text-2); vertical-align: middle;
}
.plog-tbl tr:last-child td { border-bottom: 0; }
.rep-before { font-variant-numeric: tabular-nums; color: var(--text-2); }
.rep-after  { font-variant-numeric: tabular-nums; font-weight: 700; color: var(--bad); }
.delta-chip {
  font-size: 10.5px; color: var(--bad);
  background: rgba(248,113,113,0.08); border: 1px solid rgba(248,113,113,0.2);
  border-radius: 4px; padding: 1px 6px; margin-left: 5px;
  font-variant-numeric: tabular-nums;
}

/* Per-service context strip (citizen tab) */
.svc-ctx {
  display: flex; align-items: center; gap: 11px;
  padding: 9px 13px; border-radius: 8px;
  background: var(--bg-2); border: 1px solid var(--border);
  margin: 6px 0 14px;
}
.svc-ctx .svc-icon { font-size: 19px; flex-shrink: 0; line-height: 1; }
.svc-ctx .svc-desc { color: var(--text-2); font-size: 12.5px; line-height: 1.5; }
.svc-ctx .svc-desc b { color: var(--text); font-weight: 600; }

/* ZK scenario card (requester tab) */
.zk-scenario {
  display: flex; align-items: flex-start; gap: 13px;
  padding: 12px 15px; border-radius: 10px;
  background: var(--bg-2); border: 1px solid var(--border);
  margin: 8px 0 14px;
}
.zk-icon {
  width: 36px; height: 36px; border-radius: 9px; flex-shrink: 0;
  background: var(--accent-lo); border: 1px solid var(--accent-md);
  display: flex; align-items: center; justify-content: center; font-size: 16px;
}
.zk-ttl { font-size: 13.5px; font-weight: 600; color: var(--text); margin-bottom: 3px; }
.zk-sub { font-size: 12px; color: var(--text-2); line-height: 1.5; }
.zk-hidden {
  margin-top: 6px; font-size: 10.5px; color: var(--text-3);
  display: flex; align-items: center; gap: 5px; flex-wrap: wrap;
}
.zk-hidden .zk-tag {
  background: var(--bg-3); border: 1px solid var(--border);
  border-radius: 4px; padding: 1px 7px; color: var(--text-3);
}
</style>
"""


def inject_cinematic() -> None:
    st.markdown(CINEMATIC_CSS, unsafe_allow_html=True)


def cinematic_hero(eyebrow: str, title: str, subtitle: str, pills: list[tuple[str, str]]) -> None:
    pill_html = "".join(
        f"<span class='cine-pill {kind}'>{label}</span>" for label, kind in pills
    )
    st.markdown(
        f"""
<div class='cine-hero'>
  <div class='cine-hero-eyebrow'>{eyebrow}</div>
  <h1 class='cine-hero-title'>{title}</h1>
  <div class='cine-hero-sub'>{subtitle}</div>
  <div class='cine-hero-meta'>{pill_html}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def scene_anchor(number: int, title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""
<div class='scene-anchor'>
  <div class='scene-no'>{number}</div>
  <div>
    <div class='scene-title'>{title}</div>
    <div class='scene-sub'>{subtitle}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

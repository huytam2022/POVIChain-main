"""Cinematic visual primitives — SVG diagrams, flow rails and Plotly figures.

All numerical inputs to figures arrive from :mod:`dashboard.artifact_trace`.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence

import streamlit as st

from dashboard.artifact_trace import (
    TracedMetric,
    band_check,
    percent_delta,
    source_chip,
)


def cine_metric(
    label: str,
    metric: TracedMetric,
    digits: int = 1,
    sub: str = "",
    band_label: str = "",
    band_kind: str = "ok",
    show_source: bool = True,
) -> None:
    value_html = (
        f"{metric.format_value(digits)}<small>{metric.unit}</small>"
        if metric.unit
        else f"{metric.format_value(digits)}"
    )
    chip = (
        f"<span class='band-chip {band_kind}'>{band_label}</span>"
        if band_label
        else ""
    )
    src = source_chip(metric) if show_source else ""
    sub_html = f"<div class='s'>{sub}</div>" if sub else ""
    st.markdown(
        f"""
<div class='cine-card'>
  <div class='k'>{label}{chip}</div>
  <div class='v'>{value_html}</div>
  {sub_html}
  {src}
</div>
""",
        unsafe_allow_html=True,
    )


def cine_delta_metric(
    label: str,
    primary: TracedMetric,
    versus: TracedMetric,
    higher_is_better: bool,
    digits: int = 1,
    ref_band: Optional[tuple[float, float]] = None,
) -> None:
    delta = percent_delta(primary.value, versus.value, higher_is_better)
    if delta is None:
        delta_html = "<span class='delta-flat'>—</span>"
        band_html = ""
    else:
        arrow = "▲" if delta >= 0 else "▼"
        delta_html = f"<span class='delta-up'>{arrow} {abs(delta):.1f}%</span>"
        if ref_band is not None:
            kind, message = band_check(abs(delta), *ref_band)
            band_html = f"<span class='band-chip {kind}'>{message}</span>"
        else:
            band_html = ""
    value_html = (
        f"{primary.format_value(digits)}<small>{primary.unit}</small>"
        if primary.unit
        else f"{primary.format_value(digits)}"
    )
    versus_label = "vs " + (
        f"{versus.format_value(digits)} {versus.unit}".strip()
    )
    src = source_chip(primary)
    st.markdown(
        f"""
<div class='cine-card'>
  <div class='k'>{label} {band_html}</div>
  <div class='v'>{value_html}</div>
  <div class='s'><b>{delta_html}</b> &nbsp;{versus_label} &nbsp;<i>({versus.label})</i></div>
  {src}
</div>
""",
        unsafe_allow_html=True,
    )


def problem_card(tag: str, title: str, body: str) -> None:
    st.markdown(
        f"""
<div class='cine-card problem'>
  <div class='k'>{tag}</div>
  <div class='v' style='font-size:18px;line-height:1.25;'>{title}</div>
  <div class='s'>{body}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def solution_card(tag: str, title: str, body: str) -> None:
    st.markdown(
        f"""
<div class='cine-card solution'>
  <div class='k'>{tag}</div>
  <div class='v' style='font-size:18px;line-height:1.25;'>{title}</div>
  <div class='s'>{body}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def architecture_svg() -> str:
    return """
<svg viewBox='0 0 980 460' xmlns='http://www.w3.org/2000/svg' class='svg-arch'>
  <defs>
    <linearGradient id='gL1' x1='0' x2='1'><stop offset='0' stop-color='#0e2a44'/><stop offset='1' stop-color='#0b1f33'/></linearGradient>
    <linearGradient id='gL2' x1='0' x2='1'><stop offset='0' stop-color='#2c1645'/><stop offset='1' stop-color='#1a0b2e'/></linearGradient>
    <linearGradient id='gL3' x1='0' x2='1'><stop offset='0' stop-color='#102043'/><stop offset='1' stop-color='#0b1737'/></linearGradient>
    <linearGradient id='accentP' x1='0' x2='1'><stop offset='0' stop-color='#b56cff'/><stop offset='1' stop-color='#6d8bff'/></linearGradient>
    <linearGradient id='accentA' x1='0' x2='1'><stop offset='0' stop-color='#38f0d4'/><stop offset='1' stop-color='#2bd0b4'/></linearGradient>
    <filter id='soft' x='-20%' y='-20%' width='140%' height='140%'>
      <feGaussianBlur stdDeviation='3' result='b'/>
      <feMerge><feMergeNode in='b'/><feMergeNode in='SourceGraphic'/></feMerge>
    </filter>
  </defs>

  <rect x='10' y='10' width='960' height='130' rx='14' fill='url(#gL1)' stroke='#1c2c44'/>
  <text x='28' y='38' fill='#38f0d4' font-family='Inter, system-ui' font-size='11' letter-spacing='3'>LAYER 1 · TRANSACTION &amp; PROOF</text>
  <text x='28' y='62' fill='#ffffff' font-family='Inter' font-weight='700' font-size='18'>User · IoT / MCU Verifier · Hybrid Light Client</text>
  <text x='28' y='84' fill='#9aa3bd' font-family='Inter' font-size='12'>Constant-time O(1) Merkle inclusion · no consensus participation · ESP32-class hardware</text>
  <g transform='translate(640,28)'>
    <rect width='312' height='86' rx='10' fill='#0b1830' stroke='#38f0d4' opacity='0.85'/>
    <text x='14' y='22' fill='#88f0d4' font-family='Inter' font-size='10' letter-spacing='2'>HLC RESIDENT</text>
    <text x='14' y='44' fill='#fff' font-family='Inter' font-weight='700' font-size='16'>~100 KB</text>
    <text x='14' y='62' fill='#88f0d4' font-family='Inter' font-size='10' letter-spacing='2'>VERIFY PEAK</text>
    <text x='14' y='80' fill='#fff' font-family='Inter' font-weight='700' font-size='16'>~250 KB</text>
    <text x='150' y='44' fill='#9aa3bd' font-family='Inter' font-size='11'>against</text>
    <text x='150' y='62' fill='#9aa3bd' font-family='Inter' font-size='11'>520 KB device limit</text>
  </g>

  <line x1='400' y1='140' x2='400' y2='168' stroke='#38f0d4' stroke-width='2'/>
  <polygon points='400,170 393,158 407,158' fill='#38f0d4'/>
  <text x='412' y='162' fill='#88f0d4' font-family='ui-monospace' font-size='10'>ZKP + Merkle bundle</text>

  <rect x='10' y='170' width='960' height='130' rx='14' fill='url(#gL2)' stroke='#3a1e58'/>
  <text x='28' y='198' fill='#d9bcff' font-family='Inter' font-size='11' letter-spacing='3'>LAYER 2 · CROSS-DOMAIN HYBRID VERIFICATION</text>
  <text x='28' y='222' fill='#ffffff' font-family='Inter' font-weight='700' font-size='18'>Gateway Validator-Provers · PoVI Core</text>
  <text x='28' y='244' fill='#bcb0d4' font-family='Inter' font-size='12'>ZKP Verifier · Proof Aggregator · VRF-sampled committee · Reputation engine</text>

  <g transform='translate(620,186)'>
    <rect width='332' height='100' rx='10' fill='#1a0e2b' stroke='url(#accentP)' filter='url(#soft)'/>
    <text x='14' y='22' fill='#d9bcff' font-family='Inter' font-size='10' letter-spacing='2'>COMMITTEE ADMISSION</text>
    <text x='14' y='46' fill='#ffffff' font-family='ui-monospace' font-size='13'>y_i / 2^l  &lt;  θ · R'(n_i) / Σ R'(n_j)</text>
    <text x='14' y='66' fill='#ffffff' font-family='ui-monospace' font-size='13'>R'(n_i) ≥ R_min</text>
    <text x='14' y='88' fill='#bcb0d4' font-family='Inter' font-size='11'>VRF-seeded · non-interactive · auditable</text>
  </g>

  <line x1='400' y1='300' x2='400' y2='328' stroke='#6d8bff' stroke-width='2'/>
  <polygon points='400,330 393,318 407,318' fill='#6d8bff'/>
  <text x='412' y='322' fill='#aab8ff' font-family='ui-monospace' font-size='10'>verified receipt (zone-bound)</text>

  <rect x='10' y='330' width='960' height='120' rx='14' fill='url(#gL3)' stroke='#1d2e58'/>
  <text x='28' y='358' fill='#aab8ff' font-family='Inter' font-size='11' letter-spacing='3'>LAYER 3 · SETTLEMENT &amp; SMART ZONES</text>
  <text x='28' y='382' fill='#ffffff' font-family='Inter' font-weight='700' font-size='18'>Smart Zone Dispatcher · No Single-Point-of-Value</text>
  <text x='28' y='404' fill='#9bb0e6' font-family='Inter' font-size='12'>zoneID committed to ZKP public inputs · fault isolation across zones · fee split after verify</text>

  <g transform='translate(540,344)' font-family='Inter' font-size='11' fill='#fff'>
    <g><rect width='86' height='28' rx='8' fill='#16204a' stroke='#6d8bff'/><text x='12' y='19'>Identity</text></g>
    <g transform='translate(96,0)'><rect width='86' height='28' rx='8' fill='#16204a' stroke='#6d8bff'/><text x='14' y='19'>Finance</text></g>
    <g transform='translate(192,0)'><rect width='86' height='28' rx='8' fill='#16204a' stroke='#6d8bff'/><text x='16' y='19'>Traffic</text></g>
    <g transform='translate(288,0)'><rect width='100' height='28' rx='8' fill='#16204a' stroke='#6d8bff'/><text x='12' y='19'>Environment</text></g>
    <g transform='translate(96,38)'><rect width='86' height='28' rx='8' fill='#16204a' stroke='#6d8bff'/><text x='18' y='19'>Energy</text></g>
    <g transform='translate(192,38)'><rect width='110' height='28' rx='8' fill='#16204a' stroke='#6d8bff'/><text x='12' y='19'>Governance</text></g>
  </g>
</svg>
"""


def render_architecture(traced_ram_peak: Optional[float] = None) -> None:
    st.markdown(architecture_svg(), unsafe_allow_html=True)
    if traced_ram_peak is not None:
        st.caption(
            f"Resident / peak ESP32 RAM in the diagram is calibrated from "
            f"outputs/end_device/aggregated.json (measured peak: {traced_ram_peak:.1f} KB)."
        )


def render_three_tier_explainer() -> None:
    st.markdown(
        """
<div class='tier-grid'>
  <div class='tier l1'>
    <div class='tier-tag'>Layer 1 · Edge</div>
    <div class='tier-title'>MCU Verifier</div>
    <ul>
      <li>Only Merkle inclusion against authenticated headers</li>
      <li>O(1) verify · 100 KB resident · 250 KB peak</li>
      <li>Does not trust gateways</li>
      <li>Liberated from heavy cryptography it cannot afford</li>
    </ul>
  </div>
  <div class='tier l2'>
    <div class='tier-tag'>Layer 2 · Gateway</div>
    <div class='tier-title'>Validator-Prover (PoVI)</div>
    <ul>
      <li>ZKP generation &amp; verification (Groth16 / STARK)</li>
      <li>VRF-sampled committee weighted by R'(n)</li>
      <li>Reputation accrues only from verified cross-domain interactions</li>
      <li>Logarithmic stake → Sybil resistance</li>
    </ul>
  </div>
  <div class='tier l3'>
    <div class='tier-tag'>Layer 3 · Settlement</div>
    <div class='tier-title'>Smart Zone Dispatcher</div>
    <ul>
      <li>zoneID bound to ZKP public inputs · no ex-post reroute</li>
      <li>Identity · Finance · Traffic · Energy · Governance · Environment</li>
      <li>Fault &amp; congestion isolation across zones</li>
      <li>Defeats Single-Point-of-Value concentration</li>
    </ul>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_flow_steps(steps: Sequence[Dict[str, Any]]) -> None:
    rows: List[str] = []
    for i, step in enumerate(steps, start=1):
        layer_class = step.get("layer_class", "l2")
        title = step.get("title", "")
        layer = step.get("layer", "")
        desc = step.get("desc", "")
        dur = step.get("dur", "")
        rows.append(
            f"""
<div class='step {layer_class}'>
  <div class='badge'>{i}</div>
  <div>
    <div class='ttl'>{title}<small>· {layer}</small></div>
    <div class='desc'>{desc}</div>
  </div>
  <div class='dur'>{dur}</div>
</div>
"""
        )
    st.markdown(
        f"<div class='flow-rail'>{''.join(rows)}</div>",
        unsafe_allow_html=True,
    )


def adversarial_split(
    honest_fraction_pct: float,
    sybil_row: Optional[Dict[str, Any]],
    partition_row: Optional[Dict[str, Any]],
) -> None:
    if sybil_row is None or partition_row is None:
        st.info("Resilience aggregates not present — run resilience.multi_run_driver first.")
        return

    inv = sybil_row.get("invalid_accept_pct")
    block_loss = sybil_row.get("block_loss_pct")
    trust = sybil_row.get("trust_ratio")
    delay = sybil_row.get("penalty_delay_rounds")
    runs = sybil_row.get("num_runs")

    fork = partition_row.get("fork_resolution_pct")
    conflict = partition_row.get("conflict_ratio_pct")
    recovery = partition_row.get("recovery_rounds")
    p_runs = partition_row.get("num_runs")
    p_dur = partition_row.get("partition_rounds")

    def fmt(v: Optional[float], digits: int = 2) -> str:
        if v is None:
            return "—"
        return f"{v:.{digits}f}"

    st.markdown(
        f"""
<div class='split'>
  <div class='panel danger'>
    <div class='tag'>Adversary · Sybil &amp; collusion</div>
    <h4>Malicious fraction = {honest_fraction_pct:.0f}%</h4>
    <div class='row'><span>Invalid accept rate</span><b>{fmt(inv,3)} %</b></div>
    <div class='row'><span>Block loss rate</span><b>{fmt(block_loss,3)} %</b></div>
    <div class='row'><span>Trust ratio (mal / honest)</span><b>{fmt(trust,3)}</b></div>
    <div class='row'><span>Penalty delay</span><b>{fmt(delay,2)} rounds</b></div>
    <div class='cite'>aggregated over {runs} runs · outputs/sybil_collusion/aggregated_multi_run.json</div>
  </div>
  <div class='panel safe'>
    <div class='tag'>Adversary · network partition</div>
    <h4>Partition duration = {p_dur} rounds</h4>
    <div class='row'><span>Fork resolution accuracy</span><b>{fmt(fork,2)} %</b></div>
    <div class='row'><span>Conflict ratio</span><b>{fmt(conflict,3)} %</b></div>
    <div class='row'><span>Recovery time</span><b>{fmt(recovery,2)} rounds</b></div>
    <div class='row'><span>—</span><b>—</b></div>
    <div class='cite'>aggregated over {p_runs} runs · outputs/network_partitions/aggregated_multi_run.json</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def bar_compare_throughput(values: Sequence[float], labels: Sequence[str]) -> Any:
    import plotly.graph_objects as go

    colors = ["#5b6b9b", "#7d8aba", "#b56cff"]
    fig = go.Figure(
        data=[
            go.Bar(
                x=list(labels),
                y=list(values),
                marker_color=colors[: len(values)],
                text=[f"{v:.1f}" for v in values],
                textposition="outside",
                hovertemplate="%{x}: %{y:.2f} tx/s<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        height=320,
        margin=dict(l=20, r=20, t=10, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cfd6ea", family="Inter"),
        yaxis=dict(title="tx/s", gridcolor="rgba(255,255,255,0.08)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.0)"),
    )
    return fig


def bar_compare_generic(
    values: Sequence[float],
    labels: Sequence[str],
    y_title: str,
    higher_is_better: bool,
) -> Any:
    import plotly.graph_objects as go

    best = max(values) if higher_is_better else min(values)
    colors = [
        "#b56cff" if v == best else "#5b6b9b" for v in values
    ]
    fig = go.Figure(
        data=[
            go.Bar(
                x=list(labels),
                y=list(values),
                marker_color=colors,
                text=[f"{v:.2f}" for v in values],
                textposition="outside",
                hovertemplate="%{x}: %{y:.3f}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        height=300,
        margin=dict(l=20, r=20, t=10, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cfd6ea", family="Inter"),
        yaxis=dict(title=y_title, gridcolor="rgba(255,255,255,0.08)"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.0)"),
    )
    return fig


def ablation_waterfall(summaries: Sequence[Dict[str, Any]]) -> Any:
    import plotly.graph_objects as go

    names = [s.get("name", "?") for s in summaries]
    thr = [s.get("thr_mean_pct", 0.0) for s in summaries]
    lat = [s.get("lat_mean_pct", 0.0) for s in summaries]
    en = [s.get("energy_mean_pct", 0.0) for s in summaries]

    fig = go.Figure()
    fig.add_bar(name="Throughput ↓", x=names, y=thr, marker_color="#b56cff")
    fig.add_bar(name="Latency ↑",    x=names, y=lat, marker_color="#6d8bff")
    fig.add_bar(name="Energy ↑",     x=names, y=en,  marker_color="#38f0d4")
    fig.update_layout(
        barmode="group",
        height=340,
        margin=dict(l=20, r=20, t=10, b=80),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cfd6ea", family="Inter"),
        yaxis=dict(title="Degradation vs full PoVIChain (%)", gridcolor="rgba(255,255,255,0.08)"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.35, x=0),
    )
    fig.update_xaxes(tickangle=-15)
    return fig


def energy_breakdown_chart(rows: Sequence[Dict[str, Any]]) -> Any:
    import plotly.graph_objects as go

    labels = [r.get("protocol", "?") for r in rows]
    crypto = [r.get("crypto_verify_mj", 0.0) for r in rows]
    hash_  = [r.get("hash_check_mj", 0.0) for r in rows]
    state  = [r.get("state_update_mj", 0.0) for r in rows]
    net    = [r.get("network_io_mj", 0.0) for r in rows]
    idle   = [r.get("idle_baseline_mj", 0.0) for r in rows]

    fig = go.Figure()
    fig.add_bar(name="Crypto verify", x=labels, y=crypto, marker_color="#b56cff")
    fig.add_bar(name="Hash check",    x=labels, y=hash_,  marker_color="#6d8bff")
    fig.add_bar(name="State update",  x=labels, y=state,  marker_color="#38f0d4")
    fig.add_bar(name="Network I/O",   x=labels, y=net,    marker_color="#ffb454")
    fig.add_bar(name="Idle baseline", x=labels, y=idle,   marker_color="#3a4666")
    fig.update_layout(
        barmode="stack",
        height=320,
        margin=dict(l=20, r=20, t=10, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cfd6ea", family="Inter"),
        yaxis=dict(title="mJ per transaction", gridcolor="rgba(255,255,255,0.08)"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, x=0),
    )
    return fig

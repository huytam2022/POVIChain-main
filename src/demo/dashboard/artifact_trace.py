"""Source-of-truth artifact tracer.

Every headline number rendered in the cinematic demo flows through here so
viewers can click "show source" and see the exact outputs/.../*.json file
the value came from.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUTPUTS_DIR = os.path.join(ROOT, "outputs")


def _read_json(rel_path: str) -> Optional[Dict[str, Any]]:
    abs_path = os.path.join(OUTPUTS_DIR, rel_path)
    if not os.path.isfile(abs_path):
        return None
    try:
        with open(abs_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def _walk(node: Any, path: str) -> Any:
    cur = node
    for raw in path.split("."):
        if cur is None:
            return None
        key: Any = raw
        if raw.isdigit():
            try:
                cur = cur[int(raw)]
                continue
            except Exception:
                return None
        if isinstance(cur, list):
            try:
                cur = cur[int(raw)]
                continue
            except Exception:
                return None
        if isinstance(cur, dict):
            cur = cur.get(key)
            continue
        return None
    return cur


@dataclass(frozen=True)
class TracedMetric:
    label: str
    value: Optional[float]
    unit: str
    source_file: str
    source_pointer: str

    @property
    def available(self) -> bool:
        return self.value is not None

    def format_value(self, digits: int = 1) -> str:
        if self.value is None:
            return "—"
        if abs(self.value) >= 1000:
            return f"{self.value:,.{digits}f}"
        return f"{self.value:.{digits}f}"


def _trace(
    label: str,
    rel_file: str,
    pointer: str,
    unit: str,
) -> TracedMetric:
    doc = _read_json(rel_file)
    raw = _walk(doc, pointer) if doc is not None else None
    val: Optional[float]
    if isinstance(raw, (int, float)):
        val = float(raw)
    else:
        val = None
    return TracedMetric(
        label=label,
        value=val,
        unit=unit,
        source_file=f"outputs/{rel_file}",
        source_pointer=pointer,
    )


def headline_throughput() -> Tuple[TracedMetric, TracedMetric, TracedMetric]:
    povi = _trace(
        "PoVIChain throughput",
        "main_comparison_mode_b/aggregated_metrics.json",
        "results.throughput_tps",
        "tx/s",
    )
    relay = _trace(
        "Relay protocol throughput",
        "relay_protocol_comparison/relay_protocol_comparison_summary.json",
        "metrics.throughput_tps",
        "tx/s",
    )
    oracle = _trace(
        "Oracle protocol throughput",
        "oracle_protocol_comparison/oracle_protocol_comparison_summary.json",
        "metrics.throughput_tps",
        "tx/s",
    )
    return povi, relay, oracle


def headline_latency() -> Tuple[TracedMetric, TracedMetric, TracedMetric]:
    povi = _trace(
        "PoVIChain protocol latency",
        "main_comparison_mode_b/aggregated_metrics.json",
        "results.protocol_latency_ms",
        "ms",
    )
    relay = _trace(
        "Relay protocol latency",
        "relay_protocol_comparison/relay_protocol_comparison_summary.json",
        "metrics.protocol_latency_ms",
        "ms",
    )
    oracle = _trace(
        "Oracle protocol latency",
        "oracle_protocol_comparison/oracle_protocol_comparison_summary.json",
        "metrics.protocol_latency_ms",
        "ms",
    )
    return povi, relay, oracle


def headline_energy() -> Tuple[TracedMetric, TracedMetric, TracedMetric]:
    povi = _trace(
        "PoVIChain normalized energy",
        "main_comparison_mode_b/aggregated_metrics.json",
        "results.normalized_energy",
        "",
    )
    relay = _trace(
        "Relay protocol normalized energy",
        "relay_protocol_comparison/relay_protocol_comparison_summary.json",
        "metrics.normalized_energy",
        "",
    )
    oracle = _trace(
        "Oracle protocol normalized energy",
        "oracle_protocol_comparison/oracle_protocol_comparison_summary.json",
        "metrics.normalized_energy",
        "",
    )
    return povi, relay, oracle


def headline_cpu() -> Tuple[TracedMetric, TracedMetric, TracedMetric]:
    povi = _trace(
        "PoVIChain CPU utilisation",
        "main_comparison_mode_b/aggregated_metrics.json",
        "results.cpu_utilization_percent",
        "%",
    )
    relay = _trace(
        "Relay protocol CPU utilisation",
        "relay_protocol_comparison/relay_protocol_comparison_summary.json",
        "metrics.cpu_utilization_percent",
        "%",
    )
    oracle = _trace(
        "Oracle protocol CPU utilisation",
        "oracle_protocol_comparison/oracle_protocol_comparison_summary.json",
        "metrics.cpu_utilization_percent",
        "%",
    )
    return povi, relay, oracle


def headline_e2e_latency() -> TracedMetric:
    return _trace(
        "PoVIChain end-to-end latency",
        "main_comparison_mode_b/aggregated_metrics.json",
        "results.end_to_end_latency_ms",
        "ms",
    )


def sybil_per_fraction() -> List[Dict[str, Any]]:
    doc = _read_json("sybil_collusion/aggregated_multi_run.json")
    if doc is None:
        return []
    out: List[Dict[str, Any]] = []
    for entry in doc.get("per_fraction", []) or []:
        stats = entry.get("stats", {}) or {}
        out.append({
            "malicious_fraction": entry.get("malicious_fraction"),
            "num_runs": entry.get("num_runs"),
            "invalid_accept_pct": (stats.get("invalid_accept_ratio_percent") or {}).get("mean"),
            "block_loss_pct": (stats.get("block_loss_percent") or {}).get("mean"),
            "trust_ratio": (stats.get("trust_ratio_malicious_over_honest") or {}).get("mean"),
            "penalty_delay_rounds": (stats.get("penalty_delay_rounds") or {}).get("mean"),
        })
    return out


def partition_per_duration() -> List[Dict[str, Any]]:
    doc = _read_json("network_partitions/aggregated_multi_run.json")
    if doc is None:
        return []
    out: List[Dict[str, Any]] = []
    for entry in doc.get("per_duration", []) or []:
        stats = entry.get("stats", {}) or {}
        out.append({
            "partition_rounds": entry.get("partition_duration_rounds"),
            "num_runs": entry.get("num_runs"),
            "fork_resolution_pct": (stats.get("fork_resolution_accuracy_percent") or {}).get("mean"),
            "conflict_ratio_pct": (stats.get("conflict_ratio_percent") or {}).get("mean"),
            "recovery_rounds": (stats.get("recovery_time_rounds") or {}).get("mean"),
        })
    return out


def energy_per_tx_table() -> List[Dict[str, Any]]:
    doc = _read_json("end_device/aggregated.json")
    if doc is None:
        return []
    return list(doc.get("energy_per_tx", []) or [])


def esp32_ram_envelope() -> Dict[str, Any]:
    doc = _read_json("end_device/aggregated.json")
    if doc is None:
        return {}
    return {
        "ram_peak_kb": doc.get("esp32_ram_cycle_max_kb"),
        "ram_limit_kb": doc.get("esp32_ram_limit_kb"),
        "ram_resident_kb": (doc.get("config") or {}).get("esp32_ram_cycle", {}).get("idle_baseline_kb"),
    }


def ablations_summary() -> List[Dict[str, Any]]:
    doc = _read_json("ablations/aggregated.json")
    if doc is None:
        return []
    return list(doc.get("summaries", []) or [])


def percent_delta(better: Optional[float], worse: Optional[float], higher_is_better: bool) -> Optional[float]:
    if better is None or worse is None or worse == 0:
        return None
    if higher_is_better:
        return (better / worse - 1.0) * 100.0
    return (1.0 - better / worse) * 100.0


def check_percentage_range(value: Optional[float], low_pct: float, high_pct: float) -> Tuple[str, str]:
    if value is None:
        return ("na", "no data")
    if low_pct <= value <= high_pct:
        return ("ok", f"within range {low_pct:.0f}–{high_pct:.0f}%")
    if value > high_pct:
        return ("over", f"above range ({value:.1f}% > {high_pct:.0f}%)")
    return ("under", f"below range ({value:.1f}% < {low_pct:.0f}%)")


def source_chip(metric: TracedMetric) -> str:
    return (
        f"<span class='trace-chip'>"
        f"<span class='trace-chip-key'>source</span>"
        f"<span class='trace-chip-val'>{metric.source_file}</span>"
        f"<span class='trace-chip-key'>field</span>"
        f"<span class='trace-chip-val'>{metric.source_pointer}</span>"
        f"</span>"
    )

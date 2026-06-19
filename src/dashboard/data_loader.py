"""Centralized loader for output artifacts produced by the experiment runners.

All loaders are tolerant of missing files (return None) so the dashboard can
display a "not yet generated — click Run" placeholder instead of crashing.
"""
import csv
import json
import os
from typing import Any, Dict, List, Optional

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUTS_DIR = os.path.join(ROOT, "outputs")
CONFIGS_DIR = os.path.join(ROOT, "configs")


def _read_json(path: str) -> Optional[Dict[str, Any]]:
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _read_csv(path: str) -> List[Dict[str, str]]:
    if not os.path.isfile(path):
        return []
    rows: List[Dict[str, str]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def output_path(*parts: str) -> str:
    return os.path.join(OUTPUTS_DIR, *parts)


def file_exists(*parts: str) -> bool:
    return os.path.isfile(output_path(*parts))



def load_main_comparison() -> Optional[Dict[str, Any]]:
    """Load the PoVIChain main-comparison output.

    The povichain runner stores raw metrics under the ``results`` key, while
    the baseline comparators store theirs under ``metrics``. We normalize so
    all three system payloads expose ``metrics`` uniformly, which the home +
    Main Comparison pages rely on.
    """
    raw = _read_json(output_path("main_comparison_mode_b", "aggregated_metrics.json"))
    if raw is None:
        return None
    if "metrics" not in raw and isinstance(raw.get("results"), dict):
        raw = dict(raw)
        raw["metrics"] = raw["results"]
    return raw


def load_relay_baseline() -> Optional[Dict[str, Any]]:
    return _read_json(output_path("relay_protocol_comparison", "relay_protocol_comparison_summary.json"))


def load_oracle_baseline() -> Optional[Dict[str, Any]]:
    return _read_json(output_path("oracle_protocol_comparison", "oracle_protocol_comparison_summary.json"))



def load_sybil_multi() -> Optional[Dict[str, Any]]:
    return _read_json(output_path("sybil_collusion", "aggregated_multi_run.json"))


def load_partition_multi() -> Optional[Dict[str, Any]]:
    return _read_json(output_path("network_partitions", "aggregated_multi_run.json"))


def load_recovery_overhead() -> Optional[Dict[str, Any]]:
    return _read_json(output_path("recovery_overhead", "aggregated.json"))



def load_stress_epochs() -> Optional[Dict[str, Any]]:
    return _read_json(output_path("stress_epochs", "aggregated.json"))


def load_multidomain() -> Optional[Dict[str, Any]]:
    return _read_json(output_path("multidomain_load", "aggregated.json"))



def load_gateway_profile() -> Optional[Dict[str, Any]]:
    return _read_json(output_path("gateway_profile", "aggregated.json"))


def load_end_device() -> Optional[Dict[str, Any]]:
    return _read_json(output_path("end_device", "aggregated.json"))


def load_hardware_costs() -> Optional[Dict[str, Any]]:
    return _read_json(output_path("hardware_costs", "aggregated.json"))



def load_ablations() -> Optional[Dict[str, Any]]:
    return _read_json(output_path("ablations", "aggregated.json"))


def load_vrf_sweep() -> Optional[Dict[str, Any]]:
    return _read_json(output_path("vrf_sweep", "aggregated.json"))



def load_security_ecoc() -> Optional[Dict[str, Any]]:
    return _read_json(output_path("security_ecoc_sensitivity", "aggregated.json"))


def load_security_centralization() -> Optional[Dict[str, Any]]:
    return _read_json(output_path("security_centralization", "aggregated.json"))



ARTIFACT_MAP: List[Dict[str, str]] = [
    {
        "id": "main_comparison",
        "name": "Main system comparison",
        "category": "Headline",
        "json": "main_comparison_mode_b/aggregated_metrics.json",
        "figure": "",
        "config": "configs/experiments/main_comparison_mode_b.yaml",
        "command": "PYTHONPATH=src py -m povichain.simulation --config configs/experiments/main_comparison_mode_b.yaml",
    },
    {
        "id": "relay_baseline",
        "name": "Relay protocol baseline",
        "category": "Headline",
        "json": "relay_protocol_comparison/relay_protocol_comparison_summary.json",
        "figure": "",
        "config": "configs/experiments/relay_protocol_comparison.yaml",
        "command": "PYTHONPATH=src py -m relay_protocol --config configs/experiments/relay_protocol_comparison.yaml",
    },
    {
        "id": "oracle_baseline",
        "name": "Oracle protocol baseline",
        "category": "Headline",
        "json": "oracle_protocol_comparison/oracle_protocol_comparison_summary.json",
        "figure": "",
        "config": "configs/experiments/oracle_protocol_comparison.yaml",
        "command": "PYTHONPATH=src py -m oracle_protocol --config configs/experiments/oracle_protocol_comparison.yaml",
    },
    {
        "id": "sybil_collusion",
        "name": "Sybil & collusion resilience",
        "category": "Resilience",
        "json": "sybil_collusion/aggregated_multi_run.json",
        "figure": "sybil_collusion/sybil_multi.png",
        "config": "configs/experiments/sybil_collusion.yaml",
        "command": "PYTHONPATH=src py -m resilience.multi_run_driver --config configs/experiments/sybil_collusion.yaml --mal-init-scale-override 1.0",
    },
    {
        "id": "network_partitions",
        "name": "Network partition resilience",
        "category": "Resilience",
        "json": "network_partitions/aggregated_multi_run.json",
        "figure": "network_partitions/partition_multi.png",
        "config": "configs/experiments/network_partitions.yaml",
        "command": "PYTHONPATH=src py -m resilience.multi_run_driver --config configs/experiments/network_partitions.yaml",
    },
    {
        "id": "multidomain_load",
        "name": "Multi-domain load sweep",
        "category": "Performance",
        "json": "multidomain_load/aggregated.json",
        "figure": "multidomain_load/multidomain_load.png",
        "config": "configs/experiments/multidomain_load.yaml",
        "command": "PYTHONPATH=src py -m performance.multidomain_load_runner --config configs/experiments/multidomain_load.yaml",
    },
    {
        "id": "recovery_overhead",
        "name": "Recovery overhead",
        "category": "Resilience",
        "json": "recovery_overhead/aggregated.json",
        "figure": "recovery_overhead/recovery_overhead.png",
        "config": "configs/experiments/recovery_overhead.yaml",
        "command": "PYTHONPATH=src py -m resilience.recovery_overhead_runner --config configs/experiments/recovery_overhead.yaml",
    },
    {
        "id": "stress_epochs",
        "name": "Long-horizon stress",
        "category": "Performance",
        "json": "stress_epochs/aggregated.json",
        "figure": "stress_epochs/stress_epochs.png",
        "config": "configs/experiments/stress_epochs.yaml",
        "command": "PYTHONPATH=src py -m performance.runner --config configs/experiments/stress_epochs.yaml",
    },
    {
        "id": "gateway_profile",
        "name": "Gateway profile",
        "category": "Resource",
        "json": "gateway_profile/aggregated.json",
        "figure": "gateway_profile/gateway_profile.png",
        "config": "configs/experiments/gateway_profile.yaml",
        "command": "PYTHONPATH=src py -m resource_usage.runner --config configs/experiments/gateway_profile.yaml",
    },
    {
        "id": "end_device",
        "name": "ESP32 end-device energy",
        "category": "Resource",
        "json": "end_device/aggregated.json",
        "figure": "end_device/end_device.png",
        "config": "configs/experiments/end_device.yaml",
        "command": "PYTHONPATH=src py -m resource_usage.end_device_runner --config configs/experiments/end_device.yaml",
    },
    {
        "id": "hardware_costs",
        "name": "Hardware costs",
        "category": "Resource",
        "json": "hardware_costs/aggregated.json",
        "figure": "hardware_costs/hardware_costs.png",
        "config": "configs/experiments/hardware_costs.yaml",
        "command": "PYTHONPATH=src py -m resource_usage.hardware_costs_runner --config configs/experiments/hardware_costs.yaml",
    },
    {
        "id": "ablations",
        "name": "Architectural ablations (measured)",
        "category": "Ablation",
        "json": "rq4_ablations/measured_summary.json",
        "figure": "",
        "config": "configs/experiments/rq4_ablation_base.yaml",
        "command": "py run_ablation.py --base configs/experiments/rq4_ablation_base.yaml --output-dir outputs/rq4_ablations",
    },
    {
        "id": "vrf_sweep",
        "name": "VRF threshold sweep",
        "category": "Ablation",
        "json": "vrf_sweep/aggregated.json",
        "figure": "vrf_sweep/vrf_sweep.png",
        "config": "configs/experiments/vrf_sweep.yaml",
        "command": "PYTHONPATH=src py -m ablation.vrf_sweep_runner --config configs/experiments/vrf_sweep.yaml",
    },
    {
        "id": "ecoc_sensitivity",
        "name": "ECoC sensitivity",
        "category": "Security",
        "json": "security_ecoc_sensitivity/aggregated.json",
        "figure": "security_ecoc_sensitivity/ecoc_sensitivity.png",
        "config": "configs/experiments/security_ecoc_sensitivity.yaml",
        "command": "PYTHONPATH=src py -m security_analysis.ecoc_runner --config configs/experiments/security_ecoc_sensitivity.yaml",
    },
    {
        "id": "centralization",
        "name": "Centralization mitigation",
        "category": "Security",
        "json": "security_centralization/aggregated.json",
        "figure": "security_centralization/centralization.png",
        "config": "configs/experiments/security_centralization.yaml",
        "command": "PYTHONPATH=src py -m security_analysis.centralization_runner --config configs/experiments/security_centralization.yaml",
    },
]


def coverage_summary() -> Dict[str, int]:
    total = len(ARTIFACT_MAP)
    have_json = sum(1 for a in ARTIFACT_MAP if file_exists(*a["json"].split("/")))
    have_fig = sum(
        1 for a in ARTIFACT_MAP
        if a["figure"] and file_exists(*a["figure"].split("/"))
    )
    return {"total": total, "data_present": have_json, "figures_present": have_fig}

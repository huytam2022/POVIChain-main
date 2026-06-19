from typing import Dict

from ..simulation.runner import RunResult


def aggregate_run(result: RunResult) -> Dict[str, float]:
    snap = result.metrics
    summary: Dict[str, float] = {
        "tps": snap.throughput_tps,
        "protocol_latency_ms": snap.protocol_latency_ms,
        "e2e_latency_ms": snap.e2e_latency_ms,
        "normalized_energy": snap.normalized_energy,
        "total_energy_mj": snap.total_energy_mj,
        "gateway_cpu_percent": snap.gateway_cpu_percent,
        "gateway_memory_mb": snap.gateway_memory_mb,
        "esp32_resident_kb": snap.mcu_resident_kb,
        "esp32_peak_kb": snap.mcu_peak_kb,
        "invalid_accepts": float(snap.invalid_accepts),
        "block_loss": float(snap.block_loss),
        "fork_resolution_accuracy": snap.fork_resolution_accuracy,
        "dispatcher_efficiency": snap.dispatcher_efficiency,
        "orphan_stale_rate": snap.orphan_stale_rate,
        "conflict_ratio": snap.conflict_ratio,
        "recovery_time_ms": snap.recovery_time_ms,
        "malicious_effective_reputation": snap.effective_malicious_reputation,
        "penalty_rounds": float(snap.penalty_rounds_to_convergence),
    }
    return summary

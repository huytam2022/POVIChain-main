"""Output formatters - EXACT match to target format."""
from typing import List
from .simulator import SimResult


def format_rq1_1(results: List[SimResult]) -> str:
    lines = [
        "Scenario 1.1: | Malicious fraction (%) | Invalid-accept ratio (%) | Block loss (%) | Trust ratio (malicious/honest) | Penalty delay (rounds) |",
        "| ---------------------- | ------------------------ | -------------- | ------------------------------ | ---------------------- |",
    ]
    for r in results:
        m = r.metrics
        lines.append(
            f"| {m['malicious_fraction']*100:<22.0f} | "
            f"{m['invalid_accept_ratio']:<24.2f} | "
            f"{m['block_loss_pct']:<14.2f} | "
            f"{m['trust_ratio_malicious_honest']:<30.2f} | "
            f"{m['penalty_delay_rounds']:<22.2f} |"
        )
    return '\n'.join(lines)


def format_rq1_2(results: List[SimResult]) -> str:
    lines = [
        "Scenario 1.2: | Partition duration (rounds) | Fork accuracy (%) | Conflict ratio (%) | Recovery time (rounds) |",
        "| --------------------------- | ----------------- | ------------------ | ---------------------- |",
    ]
    for r in results:
        m = r.metrics
        lines.append(
            f"| {m['partition_duration']:<27} | "
            f"{m['fork_accuracy_pct']:<17.1f} | "
            f"{m['conflict_ratio_pct']:<18.1f} | "
            f"{m['recovery_time_rounds']:<22} |"
        )
    return '\n'.join(lines)


def format_rq2_1(results: List[SimResult]) -> str:
    """Scenario 2.1 malicious table."""
    lines = [
        "Scenario 2.1: ",
        "| Malicious fraction (%) | Invalid-accept (%) | Block loss (%) | Trust ratio (m/h) | Penalty delay (rounds) |",
        "| ---------------------- | ------------------ | -------------- | ----------------- | ---------------------- |",
    ]
    for r in results:
        m = r.metrics
        lines.append(
            f"| {m['malicious_fraction']*100:<22.0f} | "
            f"{m['invalid_accept']:<18.2f} | "
            f"{m['block_loss']:<14.2f} | "
            f"{m['trust_ratio']:<17.2f} | "
            f"{m['penalty_delay']:<22.1f} |"
        )
    return '\n'.join(lines)


def format_rq2_recovery(results: List[SimResult]) -> str:
    lines = [
        "",
        "| Partition duration (rounds) | Backlog peak (tx) | Orphan block rate (%) |",
        "| --------------------------- | ----------------- | --------------------- |",
    ]
    for r in results:
        m = r.metrics
        lines.append(
            f"| {m['partition_duration']:<27} | "
            f"~{m['backlog_peak']:<16} | "
            f"~{m['orphan_block_rate']:<21} |"
        )
    lines.append("")
    return '\n'.join(lines)


def format_rq2_3(results: List[SimResult]) -> str:
    lines = ["Long-horizon sensitivity and throughput stability\n"]
    
    # Table 1: 0% loss
    m = results[0].metrics
    lines.extend([
        "| Metric                              | Value   |",
        "| ----------------------------------- | ------- |",
        f"| Steady-state mean throughput (tx/s) | ~{m['steady_throughput']:.0f}   |",
        f"| Std deviation (± band)              | ~±{m['std_deviation']:.0f}   |",
        f"| Warm-up convergence epoch           | ~{m['warmup_epoch']} |",
        "",
        "",
    ])
    
    # Table 2: 5% loss
    m = results[1].metrics
    lines.extend([
        "| Metric                              | Value    |",
        "| ----------------------------------- | -------- |",
        f"| Steady-state mean throughput (tx/s) | ~{m['steady_throughput']:.0f}    |",
        f"| Std deviation (± band)              | ~±{m['std_deviation']:.0f}    |",
        f"| Warm-up convergence epoch           | ~{m['warmup_epoch']}  |",
        "",
        "",
    ])
    
    # Table 3: 10% loss (with plateau)
    m = results[2].metrics
    lines.extend([
        "| Metric                                | Value          |",
        "| ------------------------------------- | -------------- |",
        f"| Early plateau throughput (~epoch 100) | ~{m['early_plateau_throughput']:.0f}          |",
        f"| Final mean throughput (~epoch 500)    | ~{m['steady_throughput']:.0f}          |",
        f"| Std deviation (± band)                | ~±{m['std_deviation']:.0f}          |",
        "",
        "",
    ])
    
    # Table 4: 20% loss (with plateau)
    m = results[3].metrics
    lines.extend([
        "| Metric                                   | Value                |",
        "| ---------------------------------------- | -------------------- |",
        f"| Early plateau throughput (~epoch 80–100) | ~{m['early_plateau_throughput']:.0f}                |",
        f"| Final mean throughput (~epoch 500)       | ~{m['steady_throughput']:.0f}                |",
        f"| Std deviation (± band)                   | ~±{m['std_deviation']:.0f}                |",
    ])
    
    return '\n'.join(lines)


def format_rq3_1(result: SimResult) -> str:
    lines = [
        "Scenario 3.1: Trace-driven simulation with Device Calibration\n",
        "| Epoch | CPU utilization (%) | Memory usage (MB) |",
        "| ----- | ------------------- | ----------------- |",
    ]
    for epoch_data in result.metrics['epochs']:
        lines.append(
            f"| {epoch_data['epoch']:<5} | "
            f"{epoch_data['cpu']:<19} | "
            f"{epoch_data['memory']:<17} |"
        )
    return '\n'.join(lines)


def format_rq3_2(result: SimResult) -> str:
    lines = [
        " Scenario 3.2: ZKP Choice (Groth16 vs. STARKs)\n",
        "| Epoch | Groth16 – Prover (s) | STARKs – Prover (s) |",
        "| ----- | -------------------- | ------------------- |",
    ]
    for i, (g, s) in enumerate(zip(
        result.metrics['groth16_times'],
        result.metrics['stark_times']
    ), 1):
        lines.append(f"| {i:<5} | {g:<20} | {s:<19} |")
    return '\n'.join(lines)


def format_rq3_3(result: SimResult) -> str:
    lines = [
        " Scenario 3.3: MCU-Grade Verification and Energy Profile",
    ]
    lines.extend([
        "| Time (ms) | RAM Usage (KB) | Phase             |",
        "| --------- | -------------- | ----------------- |",
    ])
    for p in result.metrics['ram_profile']:
        lines.append(
            f"| {p['time']:<9} | "
            f"{p['ram']:<14} | "
            f"{p['phase']:<17} |"
        )
    lines.extend([
        "",
        "",
        "| Protocol         | Energy per Tx (mJ) |",
        "| ---------------- | ------------------ |",
    ])
    energy = result.metrics['energy_per_tx']
    lines.append(f"| Cosmos IBC       | {energy['cosmos_ibc_mj']:<18} |")
    lines.append(f"| LayerZero        | {energy['layerzero_mj']:<18} |")
    lines.append(f"| PoVIChain (Ours) | {energy['povichain_mj']:<18} |")
    return '\n'.join(lines)


def format_rq4(results: List[SimResult]) -> str:
    lines = [
        "\nRQ4: Ablation Studies and Parameter Sensitivity",
        "| Scenario       | Thr. ↓ (%) | Lat. ↑ (%) | Energy ↑ (%) |",
        "| -------------- | ---------- | ---------- | ------------ |",
    ]
    for r in results:
        m = r.metrics
        lines.append(
            f"| {m['scenario']:<14} | "
            f"{m['throughput_degradation_pct']:<10} | "
            f"{m['latency_increase_pct']:<10} | "
            f"{m['energy_increase_pct']:<12} |"
        )
    lines.append("")
    return '\n'.join(lines)

"""Result formatters for experiment outputs."""
from typing import List, Dict, Any
from .runner import ExperimentResult


class MarkdownFormatter:
    """Format results as markdown tables."""
    
    @staticmethod
    def format_rq1_1(results: List[ExperimentResult]) -> str:
        """Format RQ1.1 results."""
        lines = [
            "Scenario 1.1: | Malicious fraction (%) | Invalid-accept ratio (%) | Block loss (%) | Trust ratio (malicious/honest) | Penalty delay (rounds) |",
            "| ---------------------- | ------------------------ | -------------- | ------------------------------ | ---------------------- |",
        ]
        
        for r in results:
            m = r.metrics
            lines.append(
                f"| {m['malicious_fraction']*100:<22} | "
                f"{m['invalid_accept_ratio']*100:<24.2f} | "
                f"{m['block_loss_pct']:<14.2f} | "
                f"{m['trust_ratio_malicious_honest']:<30.2f} | "
                f"{m['penalty_delay_rounds']:<22.2f} |"
            )
        
        return '\n'.join(lines)
    
    @staticmethod
    def format_rq1_2(results: List[ExperimentResult]) -> str:
        """Format RQ1.2 results."""
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
    
    @staticmethod
    def format_rq2_1(results: List[ExperimentResult]) -> str:
        """Format RQ2.1 multi-domain results."""
        lines = [
            "Scenario 2.1: Multi-domain throughput and dispatcher efficiency",
            "",
            "| Load Factor | Throughput (tx/s) | Dispatcher Efficiency |",
            "| ----------- | ----------------- | --------------------- |",
        ]
        
        for r in results:
            m = r.metrics
            lines.append(
                f"| {m['load_factor']:<11} | "
                f"{m['throughput']:<17.0f} | "
                f"{m['dispatcher_efficiency']:<21.2f} |"
            )
        
        return '\n'.join(lines)
    
    @staticmethod
    def format_rq2_3(results: List[ExperimentResult]) -> str:
        """Format RQ2.3 long-horizon results."""
        lines = [
            "Long-horizon sensitivity and throughput stability",
            "",
        ]
        
        for r in results:
            m = r.metrics
            lines.extend([
                f"### Packet Loss: {m['packet_loss_rate']*100}%",
                "",
                f"| Metric                              | Value   |",
                f"| ----------------------------------- | ------- |",
                f"| Steady-state mean throughput (tx/s) | ~{m['steady_throughput']:.0f}   |",
                f"| Std deviation (± band)              | ~±{m['std_deviation']:.0f}   |",
                f"| Warm-up convergence epoch           | ~{m['warmup_epoch']}  |",
                "",
            ])
        
        return '\n'.join(lines)
    
    @staticmethod
    def format_rq3_1(result: ExperimentResult) -> str:
        """Format RQ3.1 device calibration."""
        lines = [
            "Scenario 3.1: Trace-driven simulation with Device Calibration",
            "",
            "| Epoch | CPU utilization (%) | Memory usage (MB) |",
            "| ----- | ------------------- | ----------------- |",
        ]
        
        for epoch_data in result.metrics['epochs']:
            lines.append(
                f"| {epoch_data['epoch']:<5} | "
                f"{epoch_data['cpu_utilization']:<19} | "
                f"{epoch_data['memory_mb']:<17} |"
            )
        
        return '\n'.join(lines)
    
    @staticmethod
    def format_rq3_2(result: ExperimentResult) -> str:
        """Format RQ3.2 ZKP choice."""
        lines = [
            "Scenario 3.2: ZKP Choice (Groth16 vs. STARKs)",
            "",
            "| Epoch | Groth16 - Prover (s) | STARKs - Prover (s) |",
            "| ----- | -------------------- | ------------------- |",
        ]
        
        groth16 = result.metrics['groth16_times']
        starks = result.metrics['stark_times']
        
        for i, (g, s) in enumerate(zip(groth16, starks), 1):
            lines.append(
                f"| {i:<5} | {g:<20} | {s:<19} |"
            )
        
        return '\n'.join(lines)
    
    @staticmethod
    def format_rq3_3(result: ExperimentResult) -> str:
        """Format RQ3.3 MCU profile."""
        lines = [
            "Scenario 3.3: MCU-Grade Verification and Energy Profile",
            "",
            "| Time (ms) | RAM Usage (KB) | Phase             |",
            "| --------- | -------------- | ----------------- |",
        ]
        
        for p in result.metrics['ram_profile']:
            lines.append(
                f"| {p['time_ms']:<9} | {p['ram_kb']:<14} | {p['phase']:<17} |"
            )
        
        lines.extend([
            "",
            "| Protocol         | Energy per Tx (mJ) |",
            "| ---------------- | ------------------ |",
        ])
        
        energy = result.metrics['energy_per_tx']
        lines.append(f"| Cosmos IBC       | {energy['cosmos_ibc_mj']:<18} |")
        lines.append(f"| LayerZero        | {energy['layerzero_mj']:<18} |")
        lines.append(f"| PoVIChain (Ours) | {energy['povichain_mj']:<18} |")
        
        return '\n'.join(lines)
    
    @staticmethod
    def format_rq4(results: List[ExperimentResult]) -> str:
        """Format RQ4 ablation studies."""
        lines = [
            "RQ4: Ablation Studies and Parameter Sensitivity",
            "",
            "| Scenario       | Thr. down (%) | Lat. up (%) | Energy up (%) |",
            "| -------------- | ------------- | ----------- | ------------- |",
        ]
        
        for r in results:
            if r.scenario == 'baseline':
                continue
            
            m = r.metrics
            lines.append(
                f"| {r.scenario.replace('_', ' ').title():<14} | "
                f"{m.get('throughput_degradation_pct', 0):<13.1f} | "
                f"{m.get('latency_increase_pct', 0):<11.1f} | "
                f"{m.get('energy_increase_pct', 0):<13.1f} |"
            )
        
        return '\n'.join(lines)


def format_all_results(rq1_1, rq1_2, rq2_1, rq2_3, rq3_1, rq3_2, rq3_3, rq4) -> str:
    """Format all results into single output."""
    formatter = MarkdownFormatter()
    
    sections = [
        formatter.format_rq1_1(rq1_1),
        "",
        formatter.format_rq1_2(rq1_2),
        "",
        formatter.format_rq2_1(rq2_1),
        "",
        formatter.format_rq2_3(rq2_3),
        "",
        formatter.format_rq3_1(rq3_1),
        "",
        formatter.format_rq3_2(rq3_2),
        "",
        formatter.format_rq3_3(rq3_3),
        "",
        formatter.format_rq4(rq4),
    ]
    
    return '\n'.join(sections)

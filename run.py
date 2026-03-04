#!/usr/bin/env python3
"""Main entry point for PoVIChain experiments."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from povichain.core.config import Config
from povichain.simulator import PoVIChainSimulator
from povichain.formatter import (
    format_rq1_1, format_rq1_2, format_rq2_1, format_rq2_recovery,
    format_rq2_3, format_rq3_1, format_rq3_2, format_rq3_3, format_rq4
)


def main():
    print("PoVIChain Simulator")
    print("=" * 60)
    
    # Load config
    config = Config()
    sim = PoVIChainSimulator(config)
    
    # Run RQ1
    print("Running RQ1: Security experiments...")
    rq1_1 = sim.simulate_rq1_1_sybil([0.10, 0.20, 0.25, 0.40])
    rq1_2 = sim.simulate_rq1_2_partition([10, 12, 14, 16, 18, 20])
    print("  ✓ RQ1 complete")
    
    # Run RQ2
    print("Running RQ2: Scalability experiments...")
    rq2_1 = sim.simulate_rq2_scenario_2_1()  # Uses malicious table from target
    rq2_recovery = sim.simulate_rq2_recovery([5, 10, 15, 20])
    rq2_3 = sim.simulate_rq2_long_horizon([0.0, 0.05, 0.10, 0.20])
    print("  ✓ RQ2 complete")
    
    # Run RQ3
    print("Running RQ3: IoT Efficiency experiments...")
    rq3_1 = sim.simulate_rq3_device()
    rq3_2 = sim.simulate_rq3_zkp()
    rq3_3 = sim.simulate_rq3_mcu()
    print("  ✓ RQ3 complete")
    
    # Run RQ4
    print("Running RQ4: Ablation studies...")
    rq4 = sim.simulate_rq4_ablation()
    print("  ✓ RQ4 complete")
    
    # Format output
    print("\nFormatting results...")
    output = "\n".join([
        format_rq1_1(rq1_1),
        "",
        format_rq1_2(rq1_2),
        "",
        format_rq2_1(rq2_1),
        format_rq2_recovery(rq2_recovery),
        format_rq2_3(rq2_3),
        "",
        format_rq3_1(rq3_1),
        "",
        format_rq3_2(rq3_2),
        "",
        format_rq3_3(rq3_3),
        format_rq4(rq4),
    ])
    
    # Save
    with open("output_results.txt", "w", encoding="utf-8") as f:
        f.write(output)
    
    print("\n✓ Results saved to output_results.txt")
    print("\n" + "="*60)
    print("PREVIEW:")
    print("="*60)
    print(output[:1500])
    print("...")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""PoVIChain CLI entry point."""
import argparse
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from povichain.core.config import Config
from povichain.experiments.runner import (
    RQ1SecurityExperiment,
    RQ2ScalabilityExperiment,
    RQ3EfficiencyExperiment,
    RQ4AblationExperiment
)
from povichain.experiments.formatter import format_all_results


def main():
    parser = argparse.ArgumentParser(description='PoVIChain Experiment Runner')
    parser.add_argument('--config', '-c', default='config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--output', '-o', default='output_results.txt',
                       help='Output file for results')
    parser.add_argument('--rq', type=int, choices=[1, 2, 3, 4, 0], default=0,
                       help='Run specific RQ only (0 = all)')
    
    args = parser.parse_args()
    
    # Load configuration
    print(f"Loading configuration from {args.config}...")
    config = Config(args.config)
    
    results = {}
    
    # Run RQ1: Security
    if args.rq == 0 or args.rq == 1:
        print("Running RQ1: Security experiments...")
        rq1 = RQ1SecurityExperiment(config)
        results['rq1_1'] = rq1.run_sybil_collusion()
        results['rq1_2'] = rq1.run_partition()
        print("  RQ1.1: Sybil/Collusion - Complete")
        print("  RQ1.2: Network Partitions - Complete")
    
    # Run RQ2: Scalability
    if args.rq == 0 or args.rq == 2:
        print("Running RQ2: Scalability experiments...")
        rq2 = RQ2ScalabilityExperiment(config)
        results['rq2_1'] = rq2.run_load_test()
        results['rq2_3'] = rq2.run_long_horizon()
        print("  RQ2.1: Multi-domain load - Complete")
        print("  RQ2.3: Long-horizon stability - Complete")
    
    # Run RQ3: Efficiency
    if args.rq == 0 or args.rq == 3:
        print("Running RQ3: IoT Efficiency experiments...")
        rq3 = RQ3EfficiencyExperiment(config)
        results['rq3_1'] = rq3.run_device_calibration()
        results['rq3_2'] = rq3.run_zkp_choice()
        results['rq3_3'] = rq3.run_mcu_profile()
        print("  RQ3.1: Device calibration - Complete")
        print("  RQ3.2: ZKP choice - Complete")
        print("  RQ3.3: MCU profile - Complete")
    
    # Run RQ4: Ablation
    if args.rq == 0 or args.rq == 4:
        print("Running RQ4: Ablation studies...")
        rq4 = RQ4AblationExperiment(config)
        results['rq4'] = rq4.run_all()
        print("  RQ4: Ablation studies - Complete")
    
    # Format and save results
    print(f"\nFormatting results...")
    output = format_all_results(
        results.get('rq1_1', []),
        results.get('rq1_2', []),
        results.get('rq2_1', []),
        results.get('rq2_3', []),
        results.get('rq3_1'),
        results.get('rq3_2'),
        results.get('rq3_3'),
        results.get('rq4', [])
    )
    
    # Save to file
    with open(args.output, 'w') as f:
        f.write(output)
    
    print(f"Results saved to {args.output}")
    print("\n" + "="*60)
    print("Preview of results:")
    print("="*60)
    print(output[:2000])
    print("...")
    print(f"\nFull output: {args.output}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

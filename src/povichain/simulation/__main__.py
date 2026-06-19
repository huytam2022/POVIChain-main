import argparse
import json
import os
import sys
import time

from .runner import Runner
from ..reporting.export import export_run_result


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="povichain.simulation",
        description="Run a PoVIChain simulation experiment from a YAML manifest.",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to the experiment manifest YAML file.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for output artifacts. Defaults to outputs/<experiment_id>/.",
    )
    parser.add_argument(
        "--configs-root",
        default="configs",
        help="Root directory for config presets (default: configs).",
    )
    parser.add_argument(
        "--schemas-root",
        default="schemas",
        help="Root directory for JSON schemas (default: schemas).",
    )
    parser.add_argument(
        "--data-root",
        default="data",
        help="Root directory for data files (default: data).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output except errors.",
    )
    args = parser.parse_args(argv)

    if not os.path.isfile(args.config):
        print(f"ERROR: manifest not found: {args.config}", file=sys.stderr)
        sys.exit(1)

    runner = Runner(
        configs_root=args.configs_root,
        schemas_root=args.schemas_root,
        data_root=args.data_root,
    )

    if not args.quiet:
        print(f"Loading manifest: {args.config}")

    t0 = time.time()
    result = runner.run_manifest(args.config)
    elapsed = time.time() - t0

    output_dir = args.output_dir or os.path.join("outputs", result.experiment_id)
    os.makedirs(output_dir, exist_ok=True)

    exported = export_run_result(output_dir, result)

    s = result.metrics
    agg_path = os.path.join(output_dir, "aggregated_metrics.json")
    agg = {
        "experiment_id": result.experiment_id,
        "conditions": result.provenance,
        "results": {
            "throughput_tps": round(s.throughput_tps, 4),
            "protocol_latency_ms": round(s.protocol_latency_ms, 4),
            "end_to_end_latency_ms": round(s.e2e_latency_ms, 4),
            "cpu_utilization_percent": round(s.gateway_cpu_percent, 4),
            "normalized_energy": round(s.normalized_energy, 6),
            "gateway_memory_mb": round(s.gateway_memory_mb, 4),
            "mcu_resident_kb": round(s.mcu_resident_kb, 4),
            "mcu_peak_kb": round(s.mcu_peak_kb, 4),
            "total_energy_mj": round(s.total_energy_mj, 6),
            "wall_time_ms": round(s.wall_time_ms, 4),
            "blocks_finalized": s.blocks_finalized,
            "blocks_attempted": s.blocks_attempted,
            "tx_finalized": s.tx_finalized,
            "block_loss": s.block_loss,
        },
    }
    with open(agg_path, "w", encoding="utf-8") as f:
        json.dump(agg, f, indent=2, default=str)

    if not args.quiet:
        print(f"Simulation completed in {elapsed:.2f}s")
        print(f"Blocks finalized: {s.blocks_finalized}/{s.blocks_attempted}")
        print(f"TX finalized:     {s.tx_finalized}")
        print(f"Wall time:        {s.wall_time_ms:.1f} ms")
        print()
        print("Output files:")
        for label, path in exported.items():
            print(f"  {label}: {path}")
        print(f"  aggregated: {agg_path}")

    sys.exit(0)


if __name__ == "__main__":
    main()

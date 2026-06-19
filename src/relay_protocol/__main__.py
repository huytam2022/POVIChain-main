import argparse
import json
import os
import sys
import time
from dataclasses import asdict

from .runner import RelayRunner


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        prog="relay_protocol",
        description="Run a relay protocol baseline experiment from a YAML manifest.",
    )
    parser.add_argument("--config", required=True, help="Path to relay protocol manifest YAML file.")
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
    parser.add_argument("--quiet", action="store_true", help="Suppress console output except errors.")
    args = parser.parse_args(argv)

    if not os.path.isfile(args.config):
        print("ERROR: manifest not found: " + args.config, file=sys.stderr)
        sys.exit(1)

    runner = RelayRunner(
        configs_root=args.configs_root,
        schemas_root=args.schemas_root,
        data_root=args.data_root,
    )

    if not args.quiet:
        print("Loading relay protocol manifest: " + args.config)

    t0 = time.time()
    result = runner.run_manifest(args.config)
    elapsed = time.time() - t0

    output_dir = args.output_dir or os.path.join("outputs", result.experiment_id)
    os.makedirs(output_dir, exist_ok=True)
    summary_path = os.path.join(output_dir, result.experiment_id + "_summary.json")
    payload = {
        "experiment_id": result.experiment_id,
        "baseline": result.baseline,
        "mode": result.mode,
        "protocol_profile": result.protocol_profile_name,
        "network_preset": result.network_preset,
        "replay_mode": result.replay_mode,
        "calibration_sha256": result.calibration_hash,
        "provenance": result.provenance,
        "metrics": asdict(result.metrics),
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True, default=str)
    raw_path = os.path.join(output_dir, "raw_metrics.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "experiment_id": result.experiment_id,
                "metrics": asdict(result.metrics),
                "packet_outcomes": [asdict(o) for o in result.outcomes],
                "provenance": result.provenance,
            },
            f,
            indent=2,
            sort_keys=True,
            default=str,
        )
    aggregated_path = os.path.join(output_dir, "aggregated_metrics.json")
    with open(aggregated_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "experiment_id": result.experiment_id,
                "metrics": asdict(result.metrics),
            },
            f,
            indent=2,
            sort_keys=True,
            default=str,
        )

    if not args.quiet:
        s = result.metrics
        print("Simulation completed in " + ("%.2fs" % elapsed))
        print("Packets submitted: " + str(s.packets_submitted))
        print("Packets received:  " + str(s.packets_received))
        print("Packets acked:     " + str(s.packets_acknowledged))
        print("Wall time:         " + ("%.1f ms" % s.wall_time_ms))
        print()
        print("Output summary: " + summary_path)

    sys.exit(0)


if __name__ == "__main__":
    main()

import argparse
import csv
import json
import os
import sys
from typing import Dict, List

import yaml

from .sim_core import (
    build_nodes,
    make_reputation_params,
    run_partition_scenario,
)
from .plot_sybil import plot_partitions


def _load_yaml(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _aggregate_partition_run(
    partition_duration: int,
    warmup_rounds: int,
    recovery_rounds_budget: int,
    params_dict: Dict,
    theta: float,
    split_ratio: float,
    post_reconnect_agreement_window: int,
    tie_margin: float,
) -> Dict:
    params = make_reputation_params(params_dict)
    nodes = build_nodes(
        node_count=100,
        malicious_fraction=0.0,
        sybil_identity_multiplier=1,
        partition_split_ratio=split_ratio,
    )
    result = run_partition_scenario(
        nodes=nodes,
        params=params,
        warmup_rounds=warmup_rounds,
        partition_duration_rounds=partition_duration,
        recovery_rounds_budget=recovery_rounds_budget,
        theta=theta,
        post_reconnect_agreement_window=post_reconnect_agreement_window,
        tie_margin=tie_margin,
    )
    fork_total = result.fork_events_total
    fork_correct = result.fork_events_correct
    fork_failed = result.fork_events_failed
    if fork_total > 0:
        accuracy_pct = 100.0 * float(fork_correct) / float(fork_total)
    else:
        accuracy_pct = 100.0
    conflict_window_rounds = partition_duration + result.recovery_time_rounds
    conflict_ratio_pct = 0.0
    if conflict_window_rounds > 0:
        conflict_ratio_pct = 100.0 * float(fork_failed) / float(conflict_window_rounds)
    partition_block_dump = [
        {
            "round_no": b.round_no,
            "partition_id": b.partition_id,
            "proposer": b.proposer,
            "cumulative_weight": b.cumulative_weight,
            "committee_weight_total": b.committee_weight_total,
            "local_accept_ratio": b.local_accept_ratio,
            "finalized": b.finalized,
        }
        for b in result.partition_blocks
    ]
    warmup_dump = [
        {
            "round_no": rec.round_no,
            "proposer": rec.proposer,
            "committee_size": len(rec.committee_members),
            "finalized": rec.finalized,
        }
        for rec in result.warmup_records
    ]
    recovery_dump = [
        {
            "round_no": rec.round_no,
            "proposer": rec.proposer,
            "committee_size": len(rec.committee_members),
            "accept_weight": rec.accept_weight,
            "reject_weight": rec.reject_weight,
            "abstain_weight": rec.abstain_weight,
            "finalized": rec.finalized,
        }
        for rec in result.recovery_records
    ]
    return {
        "partition_duration_rounds": partition_duration,
        "warmup_rounds": warmup_rounds,
        "split_ratio": split_ratio,
        "side_a_size": sum(1 for n in nodes if n.partition_id == 0),
        "side_b_size": sum(1 for n in nodes if n.partition_id == 1),
        "fork_events_total": fork_total,
        "fork_events_correct": fork_correct,
        "fork_events_failed": fork_failed,
        "orphan_blocks": result.orphan_blocks,
        "total_finalized": result.total_finalized,
        "recovery_time_rounds": result.recovery_time_rounds,
        "metrics": {
            "fork_resolution_accuracy_percent": accuracy_pct,
            "conflict_ratio_percent": conflict_ratio_pct,
            "recovery_time_rounds": float(result.recovery_time_rounds),
        },
        "warmup_rounds_dump": warmup_dump,
        "partition_blocks": partition_block_dump,
        "recovery_rounds_dump": recovery_dump,
    }


def _write_figure5b_csv(path: str, runs: List[Dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "partition_duration_rounds",
                "fork_resolution_accuracy_percent",
                "conflict_ratio_percent",
                "recovery_time_rounds",
            ]
        )
        for run in runs:
            m = run["metrics"]
            writer.writerow(
                [
                    run["partition_duration_rounds"],
                    round(m["fork_resolution_accuracy_percent"], 6),
                    round(m["conflict_ratio_percent"], 6),
                    round(m["recovery_time_rounds"], 6),
                ]
            )


def _write_summary(path: str, cfg: Dict, runs: List[Dict], targets: Dict) -> None:
    lines: List[str] = []
    lines.append("# network-partition analysis")
    lines.append("")
    lines.append("## Scenario")
    lines.append("- Node count: 100")
    lines.append("- Partition durations: " + ", ".join(str(d) for d in cfg["partition_durations_rounds"]))
    lines.append("- Warmup rounds: " + str(cfg.get("warmup_rounds", 0)))
    lines.append("- Recovery budget rounds: " + str(cfg.get("recovery_rounds_budget", 0)))
    lines.append("- Split ratio: " + str(cfg["partition_profile"].get("split_ratio", 0.5)))
    lines.append("- Partition model: " + str(cfg["partition_profile"].get("model", "hard_isolation")))
    lines.append("- Tie margin (fork resolution failure threshold): " + str(cfg["partition_profile"].get("tie_margin", 0.005)))
    lines.append("- Mode: " + str(cfg.get("mode", "A")))
    lines.append("")
    lines.append("## Partition model semantics")
    lines.append(
        "- Hard isolation: during partition rounds, each side runs an independent committee selection, proposal, vote, and finalize loop using only its own validators."
    )
    lines.append("- Both sides extend local chains during isolation; reputation updates continue locally.")
    lines.append(
        "- At reconnect: for each partition round where both sides finalized, a fork event is recorded. Canonical resolution picks the side with greater cumulative accept weight; if relative margin |wa-wb|/(wa+wb) <= tie_margin, resolution fails (committee weights too close to assign canonicity deterministically)."
    )
    lines.append(
        "- Recovery: each validator imports 1 block of catch-up per round, modeled as a per-validator sync-weight scale that ramps from 0.0 to 1.0 over partition_duration rounds. A proposal can only finalize when the effective unified committee weight clears the 2/3 quorum. Recovery ends once post_reconnect_agreement_window consecutive fully-synced finalized blocks have been observed."
    )
    lines.append("")
    lines.append("## Metric definitions")
    lines.append("- fork_resolution_accuracy_percent = fork_events_correct / fork_events_total * 100 (100.0 when no forks)")
    lines.append("- conflict_ratio_percent = fork_events_failed / (partition_duration + recovery_time_rounds) * 100")
    lines.append("- recovery_time_rounds = number of post-reconnect rounds until agreement re-established")
    lines.append("")
    lines.append("## Observed metrics")
    header = "| Partition rounds | Fork-res acc % | Conflict ratio % | Recovery rounds |"
    sep = "|------------------|----------------|------------------|------------------|"
    lines.append(header)
    lines.append(sep)
    for run in runs:
        m = run["metrics"]
        lines.append(
            "| {0:>16d} | {1:>14.4f} | {2:>16.4f} | {3:>16.4f} |".format(
                run["partition_duration_rounds"],
                m["fork_resolution_accuracy_percent"],
                m["conflict_ratio_percent"],
                m["recovery_time_rounds"],
            )
        )
    lines.append("")
    lines.append("## Notes")
    lines.append(
        "Simulation uses povichain.consensus primitives (CommitteeSelector, ReputationLedger, tally_votes, finalize_block). "
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run(cfg_path: str) -> int:
    cfg = _load_yaml(cfg_path)
    out_dir = cfg["output"]["output_dir"]
    os.makedirs(out_dir, exist_ok=True)
    part_cfg = cfg.get("partition_profile", {})
    split_ratio = float(part_cfg.get("split_ratio", 0.5))
    agreement_window = int(part_cfg.get("post_reconnect_agreement_window", 3))
    tie_margin = float(part_cfg.get("tie_margin", 0.005))
    runs: List[Dict] = []
    for dur in cfg["partition_durations_rounds"]:
        payload = _aggregate_partition_run(
            partition_duration=int(dur),
            warmup_rounds=int(cfg.get("warmup_rounds", 5)),
            recovery_rounds_budget=int(cfg.get("recovery_rounds_budget", 40)),
            params_dict=cfg["reputation_weights"],
            theta=float(cfg["committee_threshold_theta"]),
            split_ratio=split_ratio,
            post_reconnect_agreement_window=agreement_window,
            tie_margin=tie_margin,
        )
        runs.append(payload)
    raw_payload = {
        "experiment_id": cfg["experiment_id"],
        "scenario": cfg["scenario"],
        "config": cfg,
        "runs": runs,
    }
    with open(os.path.join(out_dir, "raw_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(raw_payload, f, indent=2, default=str)
    agg_payload = {
        "experiment_id": cfg["experiment_id"],
        "scenario": cfg["scenario"],
        "per_duration": [
            {
                "partition_duration_rounds": r["partition_duration_rounds"],
                "metrics": r["metrics"],
                "fork_events_total": r["fork_events_total"],
                "fork_events_correct": r["fork_events_correct"],
                "fork_events_failed": r["fork_events_failed"],
                "orphan_blocks": r["orphan_blocks"],
                "total_finalized": r["total_finalized"],
                "side_a_size": r["side_a_size"],
                "side_b_size": r["side_b_size"],
            }
            for r in runs
        ],
    }
    with open(os.path.join(out_dir, "aggregated_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(agg_payload, f, indent=2, default=str)
    csv_path = os.path.join(out_dir, "figure5b.csv")
    _write_figure5b_csv(csv_path, runs)
    png_path = os.path.join(out_dir, "figure5b.png")
    plot_partitions(csv_path, png_path, "Resilience - Network partitions (Network partition analysis)")
    targets = cfg.get("targets", {})
    _write_summary(os.path.join(out_dir, "summary.md"), cfg, runs, targets)
    print("=== (Network Partitions) ===")
    for r in runs:
        m = r["metrics"]
        print(
            "  partition_rounds={0}  fork_acc%={1:.4f}  conflict%={2:.4f}  recovery_rounds={3:.4f}".format(
                r["partition_duration_rounds"],
                m["fork_resolution_accuracy_percent"],
                m["conflict_ratio_percent"],
                m["recovery_time_rounds"],
            )
        )
    print("outputs: " + out_dir)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="resilience.network_partition_runner")
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    if not os.path.isfile(args.config):
        print("ERROR: config not found: " + args.config, file=sys.stderr)
        return 2
    return run(args.config)


if __name__ == "__main__":
    sys.exit(main())

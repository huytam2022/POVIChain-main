"""
Multi-run deterministic aggregation driver.

For each scenario (sybil_collusion or network_partitions), runs N deterministic
replicates of the simulation, where each replicate gets a unique seed_tag suffix
appended to the VRF randao hash; each (scenario,
seed_tag) pair is bit-identical across re-invocations.

Per-replicate metrics are aggregated into mean/std/min/max/p50/p90 to give an
ensemble distribution that smooths the rare-event quantization that affects
the ensemble distribution that smooths rare-event quantization in single-run outputs.

Outputs (per scenario) are written next to the existing single-run outputs:
  raw_multi_run.json
  aggregated_multi_run.json
  multi_run_summary.md

The single-run pipeline is unchanged; this driver only ADDS new output files.
"""
import argparse
import csv
import json
import math
import os
import sys
from typing import Dict, List, Tuple

import yaml

from .plot_sybil_multirun import plot_sybil_multirun, plot_partitions_multirun
from .sim_core import (
    build_nodes,
    compute_first_penalty_rounds,
    honest_initial_mean_rep,
    initial_reputation,
    make_reputation_params,
    run_partition_scenario,
    run_sybil_rounds,
)


def _load_yaml(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _seed_tag_for_run(run_index: int) -> str:
    if run_index == 0:
        return ""
    return "|r" + str(run_index)


def _stats(values: List[float]) -> Dict[str, float]:
    n = len(values)
    if n == 0:
        return {
            "count": 0,
            "mean": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "p50": 0.0,
            "p90": 0.0,
        }
    mean = sum(values) / float(n)
    if n > 1:
        var = sum((v - mean) ** 2 for v in values) / float(n - 1)
        std = math.sqrt(var)
    else:
        std = 0.0
    sorted_v = sorted(values)
    p50_idx = max(0, min(n - 1, int(round(0.50 * (n - 1)))))
    p90_idx = max(0, min(n - 1, int(round(0.90 * (n - 1)))))
    return {
        "count": n,
        "mean": float(mean),
        "std": float(std),
        "min": float(sorted_v[0]),
        "max": float(sorted_v[-1]),
        "p50": float(sorted_v[p50_idx]),
        "p90": float(sorted_v[p90_idx]),
    }


def _tabulate_sybil_records(records) -> Dict[str, int]:
    attempted = 0
    finalized = 0
    invalid_accepts = 0
    valid_proposed = 0
    valid_finalized = 0
    invalid_proposed = 0
    invalid_finalized = 0
    for rec in records:
        attempted += 1
        if rec.block_valid:
            valid_proposed += 1
            if rec.finalized:
                valid_finalized += 1
                finalized += 1
        else:
            invalid_proposed += 1
            if rec.finalized:
                invalid_finalized += 1
                invalid_accepts += 1
                finalized += 1
    return {
        "attempted": attempted,
        "finalized": finalized,
        "invalid_accepts": invalid_accepts,
        "valid_proposed": valid_proposed,
        "valid_finalized": valid_finalized,
        "invalid_proposed": invalid_proposed,
        "invalid_finalized": invalid_finalized,
    }


def _run_sybil_replicate(
    cfg: Dict,
    malicious_fraction: float,
    seed_tag: str,
    theta_override: float = None,
    rounds_override: int = None,
    mal_init_scale_override: float = None,
) -> Dict:
    params = make_reputation_params(cfg["reputation_weights"])
    adv = cfg.get("adversary_profile", {})
    sybil_mult = int(adv.get("sybil_identity_multiplier", 1))
    invalid_proposal = bool(adv.get("malicious_proposal_invalid", True))
    mal_initial_scale = (
        float(mal_init_scale_override)
        if mal_init_scale_override is not None
        else float(adv.get("mal_initial_reputation_scale", 0.5))
    )
    penalty_per_round = float(cfg.get("penalty_malicious_per_round", 0.3))
    detection_probability = float(adv.get("detection_probability", 1.0))
    network_wide_detection = bool(adv.get("network_wide_detection", False))
    continuous_availability = bool(adv.get("continuous_availability", False))
    availability_delta = float(cfg.get("availability_delta", 0.05))
    rounds_per_run = int(rounds_override) if rounds_override else int(cfg["rounds_per_run"])
    theta = float(theta_override) if theta_override else float(cfg["committee_threshold_theta"])

    nodes = build_nodes(
        node_count=100,
        malicious_fraction=malicious_fraction,
        sybil_identity_multiplier=sybil_mult,
    )
    bag, ledger = run_sybil_rounds(
        nodes=nodes,
        params=params,
        rounds_per_run=rounds_per_run,
        theta=theta,
        adversary_invalid_proposal=invalid_proposal,
        penalty_malicious_per_round=penalty_per_round,
        availability_delta=availability_delta,
        mal_initial_scale=mal_initial_scale,
        detection_probability=detection_probability,
        network_wide_detection=network_wide_detection,
        continuous_availability=continuous_availability,
        seed_tag=seed_tag,
    )
    tab = _tabulate_sybil_records(bag.records)
    eff_final = ledger.effective_map()
    mal_ids = tuple(n.validator_id for n in nodes if n.malicious)
    base_mal_ids = tuple(n.validator_id for n in nodes if n.malicious and n.sybil_alias_of is None)
    honest_ids = tuple(
        n.validator_id for n in nodes if (not n.malicious) and n.sybil_alias_of is None
    )
    mal_eff = [eff_final[v] for v in mal_ids if v in eff_final]
    honest_eff = [eff_final[v] for v in honest_ids if v in eff_final]
    honest_mean_final = sum(honest_eff) / len(honest_eff) if honest_eff else 1.0
    mal_mean_final = sum(mal_eff) / len(mal_eff) if mal_eff else 0.0
    penalty_delay = compute_first_penalty_rounds(bag.penalized_per_round, mal_ids)
    penalty_delay_base = compute_first_penalty_rounds(bag.penalized_per_round, base_mal_ids)
    invalid_accept_ratio_pct = (
        100.0 * (tab["invalid_accepts"] / tab["attempted"]) if tab["attempted"] > 0 else 0.0
    )
    valid_lost = tab["valid_proposed"] - tab["valid_finalized"]
    block_loss_pct = (
        100.0 * (valid_lost / tab["valid_proposed"]) if tab["valid_proposed"] > 0 else 0.0
    )
    trust_ratio = (mal_mean_final / honest_mean_final) if honest_mean_final > 0 else 0.0
    return {
        "seed_tag": seed_tag,
        "malicious_fraction": malicious_fraction,
        "blocks_attempted": tab["attempted"],
        "blocks_finalized": tab["finalized"],
        "invalid_accepts": tab["invalid_accepts"],
        "valid_blocks_proposed": tab["valid_proposed"],
        "valid_blocks_finalized": tab["valid_finalized"],
        "invalid_proposed": tab["invalid_proposed"],
        "invalid_finalized": tab["invalid_finalized"],
        "honest_effective_mean_final": honest_mean_final,
        "malicious_effective_mean_final": mal_mean_final,
        "metrics": {
            "invalid_accept_ratio_percent": invalid_accept_ratio_pct,
            "block_loss_percent": block_loss_pct,
            "trust_ratio_malicious_over_honest": trust_ratio,
            "penalty_delay_rounds": penalty_delay,
            "penalty_delay_rounds_base_mal_only": penalty_delay_base,
        },
    }


def _run_partition_replicate(
    cfg: Dict,
    partition_duration: int,
    seed_tag: str,
    theta_override: float = None,
    tie_margin_override: float = None,
) -> Dict:
    params = make_reputation_params(cfg["reputation_weights"])
    part_cfg = cfg.get("partition_profile", {})
    split_ratio = float(part_cfg.get("split_ratio", 0.5))
    agreement_window = int(part_cfg.get("post_reconnect_agreement_window", 3))
    tie_margin = float(tie_margin_override) if tie_margin_override else float(part_cfg.get("tie_margin", 0.005))
    warmup_rounds = int(cfg.get("warmup_rounds", 5))
    recovery_rounds_budget = int(cfg.get("recovery_rounds_budget", 40))
    theta = float(theta_override) if theta_override else float(cfg["committee_threshold_theta"])

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
        post_reconnect_agreement_window=agreement_window,
        tie_margin=tie_margin,
        seed_tag=seed_tag,
    )
    fork_total = result.fork_events_total
    fork_correct = result.fork_events_correct
    fork_failed = result.fork_events_failed
    accuracy_pct = (
        100.0 * float(fork_correct) / float(fork_total) if fork_total > 0 else 100.0
    )
    conflict_window = partition_duration + result.recovery_time_rounds
    conflict_ratio_pct = (
        100.0 * float(fork_failed) / float(conflict_window)
        if conflict_window > 0
        else 0.0
    )
    return {
        "seed_tag": seed_tag,
        "partition_duration_rounds": partition_duration,
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
    }


SYBIL_METRICS = (
    "invalid_accept_ratio_percent",
    "block_loss_percent",
    "trust_ratio_malicious_over_honest",
    "penalty_delay_rounds",
    "penalty_delay_rounds_base_mal_only",
)
PARTITION_METRICS = (
    "fork_resolution_accuracy_percent",
    "conflict_ratio_percent",
    "recovery_time_rounds",
)


def _aggregate_param_replicates(
    replicates: List[Dict],
    metric_keys: Tuple[str, ...],
) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for key in metric_keys:
        values = [float(rep["metrics"][key]) for rep in replicates]
        out[key] = _stats(values)
    return out


def _write_sybil_csv(path: str, per_fraction: List[Dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        header = [
            "malicious_fraction",
            "malicious_fraction_percent",
            "num_runs",
        ]
        for k in SYBIL_METRICS:
            header.extend([k + "_mean", k + "_std", k + "_min", k + "_max", k + "_p50", k + "_p90"])
        writer.writerow(header)
        for entry in per_fraction:
            row = [
                entry["malicious_fraction"],
                entry["malicious_fraction"] * 100.0,
                entry["num_runs"],
            ]
            for k in SYBIL_METRICS:
                s = entry["stats"][k]
                row.extend(
                    [
                        round(s["mean"], 6),
                        round(s["std"], 6),
                        round(s["min"], 6),
                        round(s["max"], 6),
                        round(s["p50"], 6),
                        round(s["p90"], 6),
                    ]
                )
            writer.writerow(row)


def _write_partition_csv(path: str, per_duration: List[Dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        header = ["partition_duration_rounds", "num_runs"]
        for k in PARTITION_METRICS:
            header.extend([k + "_mean", k + "_std", k + "_min", k + "_max", k + "_p50", k + "_p90"])
        writer.writerow(header)
        for entry in per_duration:
            row = [entry["partition_duration_rounds"], entry["num_runs"]]
            for k in PARTITION_METRICS:
                s = entry["stats"][k]
                row.extend(
                    [
                        round(s["mean"], 6),
                        round(s["std"], 6),
                        round(s["min"], 6),
                        round(s["max"], 6),
                        round(s["p50"], 6),
                        round(s["p90"], 6),
                    ]
                )
            writer.writerow(row)


def _format_metric_line(label: str, stats: Dict[str, float]) -> str:
    return (
        "  - " + label
        + ": mean=" + f"{stats['mean']:.4f}"
        + " std=" + f"{stats['std']:.4f}"
        + " min=" + f"{stats['min']:.4f}"
        + " max=" + f"{stats['max']:.4f}"
        + " p50=" + f"{stats['p50']:.4f}"
        + " p90=" + f"{stats['p90']:.4f}"
        + " (n=" + str(stats["count"]) + ")"
    )


def _write_sybil_summary(
    path: str,
    cfg: Dict,
    num_runs: int,
    per_fraction: List[Dict],
    single_run_path: str,
    overrides: Dict = None,
) -> None:
    overrides = overrides or {}
    active_overrides = {k: v for k, v in overrides.items() if v is not None}
    lines: List[str] = []
    lines.append("# sybil-collusion multi-run aggregation")
    lines.append("")
    if active_overrides:
        lines.append("## Refinement applied (vs canonical config)")
        for k, v in active_overrides.items():
            lines.append("- " + k + " = " + str(v))
        lines.append("")
        lines.append("These overrides are passed via CLI flags on multi_run_driver and DO NOT")
        lines.append("modify the YAML config.")
        lines.append("With overrides active, replicate 0 is NOT bit-identical to the legacy")
        lines.append("single-run baseline; the legacy outputs are preserved with `_legacy` suffix.")
        lines.append("")
    lines.append("## Multi-run design")
    lines.append("- Replicates per malicious fraction: " + str(num_runs))
    lines.append("- Variation: per-replicate seed_tag appended to VRF randao hash.")
    if not active_overrides:
        lines.append("  Replicate 0 uses seed_tag='' (bit-identical to legacy single-run).")
    else:
        lines.append("  Replicate 0 uses seed_tag='' (bit-identical to single-run only when")
        lines.append("  no overrides are active; here overrides ARE active, see top section).")
    lines.append("  each (fraction, seed_tag) pair is bit-reproducible across invocations.")
    lines.append("- Metric definitions are unchanged from the single-run pipeline:")
    lines.append("  invalid_accept_ratio_percent, block_loss_percent,")
    lines.append("  trust_ratio_malicious_over_honest, penalty_delay_rounds (median).")
    lines.append("- ADD-ONLY diagnostic column: penalty_delay_rounds_base_mal_only — same")
    lines.append("  median-first-round computation but restricted to base malicious identities")
    lines.append("  (sybil aliases excluded). The original penalty_delay_rounds is unchanged.")
    lines.append("")
    lines.append("## Per-fraction ensemble statistics")
    for entry in per_fraction:
        lines.append("")
        lines.append("### malicious_fraction = " + f"{entry['malicious_fraction']:.2f}")
        for k in SYBIL_METRICS:
            lines.append(_format_metric_line(k, entry["stats"][k]))
    lines.append("")
    lines.append("## Notes")
    lines.append("Driver lives in src/resilience/multi_run_driver.py. Plots in")
    lines.append("src/resilience/plot_sybil_multirun.py. No protocol logic was changed; the")
    lines.append("seed_tag parameter on sim_core has default '' which preserves the")
    lines.append("legacy single-run hash exactly (verified bit-identical).")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _write_partition_summary(
    path: str,
    cfg: Dict,
    num_runs: int,
    per_duration: List[Dict],
    single_run_path: str,
) -> None:
    lines: List[str] = []
    lines.append("# network-partition multi-run deterministic aggregation")
    lines.append("")
    lines.append("## Multi-run design")
    lines.append("- Replicates per partition duration: " + str(num_runs))
    lines.append("- Variation: per-replicate seed_tag appended to VRF randao hash.")
    lines.append("  Replicate 0 uses seed_tag='' (bit-identical to legacy single-run).")
    lines.append("  each (duration, seed_tag) pair is bit-reproducible.")
    lines.append("- Metric definitions are unchanged from the single-run pipeline:")
    lines.append("  fork_resolution_accuracy_percent, conflict_ratio_percent,")
    lines.append("  recovery_time_rounds.")
    lines.append("")
    lines.append("## Per-duration ensemble statistics")
    for entry in per_duration:
        lines.append("")
        lines.append("### partition_duration_rounds = " + str(entry["partition_duration_rounds"]))
        for k in PARTITION_METRICS:
            lines.append(_format_metric_line(k, entry["stats"][k]))
    lines.append("")
    lines.append("## Notes")
    lines.append("Driver lives in src/resilience/multi_run_driver.py. Plots in")
    lines.append("src/resilience/plot_sybil_multirun.py. No protocol logic was changed; the")
    lines.append("seed_tag parameter on sim_core has default '' which preserves the")
    lines.append("legacy single-run hash exactly (verified bit-identical).")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _read_single_run_metrics(path: str, malicious_fraction: float):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    for entry in data.get("per_fraction", []):
        if abs(float(entry.get("malicious_fraction", -1)) - malicious_fraction) < 1e-9:
            return entry.get("metrics", {})
    return None


def _read_single_run_partition_metrics(path: str, duration: int):
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None
    for entry in data.get("per_duration", []):
        if int(entry.get("partition_duration_rounds", -1)) == int(duration):
            return entry.get("metrics", {})
    return None


def _run_sybil_multi(
    cfg: Dict,
    num_runs: int,
    out_dir: str,
    theta_override: float = None,
    rounds_override: int = None,
    mal_init_scale_override: float = None,
) -> int:
    per_fraction: List[Dict] = []
    raw_per_fraction: List[Dict] = []
    for m_frac in cfg["malicious_fractions"]:
        m_frac = float(m_frac)
        replicates: List[Dict] = []
        for i in range(num_runs):
            seed_tag = _seed_tag_for_run(i)
            rep = _run_sybil_replicate(
                cfg, m_frac, seed_tag,
                theta_override=theta_override,
                rounds_override=rounds_override,
                mal_init_scale_override=mal_init_scale_override,
            )
            rep["replicate_index"] = i
            replicates.append(rep)
        stats = _aggregate_param_replicates(replicates, SYBIL_METRICS)
        per_fraction.append(
            {
                "malicious_fraction": m_frac,
                "num_runs": num_runs,
                "stats": stats,
            }
        )
        raw_per_fraction.append(
            {
                "malicious_fraction": m_frac,
                "num_runs": num_runs,
                "replicates": replicates,
            }
        )
    raw_payload = {
        "experiment_id": cfg["experiment_id"],
        "scenario": cfg["scenario"],
        "num_runs": num_runs,
        "config": cfg,
        "overrides_applied": {
            "theta_override": theta_override,
            "rounds_override": rounds_override,
            "mal_init_scale_override": mal_init_scale_override,
        },
        "per_fraction": raw_per_fraction,
    }
    with open(os.path.join(out_dir, "raw_multi_run.json"), "w", encoding="utf-8") as f:
        json.dump(raw_payload, f, indent=2, default=str)
    agg_payload = {
        "experiment_id": cfg["experiment_id"],
        "scenario": cfg["scenario"],
        "num_runs": num_runs,
        "overrides_applied": {
            "theta_override": theta_override,
            "rounds_override": rounds_override,
            "mal_init_scale_override": mal_init_scale_override,
        },
        "per_fraction": per_fraction,
    }
    with open(os.path.join(out_dir, "aggregated_multi_run.json"), "w", encoding="utf-8") as f:
        json.dump(agg_payload, f, indent=2, default=str)
    csv_path = os.path.join(out_dir, "figure5a_multi.csv")
    _write_sybil_csv(csv_path, per_fraction)
    png_path = os.path.join(out_dir, "figure5a_multi.png")
    plot_sybil_multirun(
        csv_path, png_path, "Resilience - Sybil & collusion (multi-run, n=" + str(num_runs) + ")"
    )
    summary_path = os.path.join(out_dir, "multi_run_summary.md")
    single_path = os.path.join(out_dir, "aggregated_metrics.json")
    _write_sybil_summary(
        summary_path, cfg, num_runs, per_fraction, single_path,
        overrides={
            "theta_override": theta_override,
            "rounds_override": rounds_override,
            "mal_init_scale_override": mal_init_scale_override,
        },
    )
    print("=== sybil multi-run (n=" + str(num_runs) + ") ===")
    for entry in per_fraction:
        s = entry["stats"]
        print(
            "  malicious={0:.2f}  invalid_accept%=mean {1:.4f} std {2:.4f}  trust=mean {3:.4f} std {4:.4f}  penalty_delay=mean {5:.4f} std {6:.4f}".format(
                entry["malicious_fraction"],
                s["invalid_accept_ratio_percent"]["mean"],
                s["invalid_accept_ratio_percent"]["std"],
                s["trust_ratio_malicious_over_honest"]["mean"],
                s["trust_ratio_malicious_over_honest"]["std"],
                s["penalty_delay_rounds"]["mean"],
                s["penalty_delay_rounds"]["std"],
            )
        )
    print("outputs: " + out_dir)
    return 0


def _run_partition_multi(
    cfg: Dict,
    num_runs: int,
    out_dir: str,
    theta_override: float = None,
    tie_margin_override: float = None,
) -> int:
    per_duration: List[Dict] = []
    raw_per_duration: List[Dict] = []
    for dur in cfg["partition_durations_rounds"]:
        dur = int(dur)
        replicates: List[Dict] = []
        for i in range(num_runs):
            seed_tag = _seed_tag_for_run(i)
            rep = _run_partition_replicate(
                cfg, dur, seed_tag,
                theta_override=theta_override,
                tie_margin_override=tie_margin_override,
            )
            rep["replicate_index"] = i
            replicates.append(rep)
        stats = _aggregate_param_replicates(replicates, PARTITION_METRICS)
        per_duration.append(
            {
                "partition_duration_rounds": dur,
                "num_runs": num_runs,
                "stats": stats,
            }
        )
        raw_per_duration.append(
            {
                "partition_duration_rounds": dur,
                "num_runs": num_runs,
                "replicates": replicates,
            }
        )
    raw_payload = {
        "experiment_id": cfg["experiment_id"],
        "scenario": cfg["scenario"],
        "num_runs": num_runs,
        "config": cfg,
        "per_duration": raw_per_duration,
    }
    with open(os.path.join(out_dir, "raw_multi_run.json"), "w", encoding="utf-8") as f:
        json.dump(raw_payload, f, indent=2, default=str)
    agg_payload = {
        "experiment_id": cfg["experiment_id"],
        "scenario": cfg["scenario"],
        "num_runs": num_runs,
        "per_duration": per_duration,
    }
    with open(os.path.join(out_dir, "aggregated_multi_run.json"), "w", encoding="utf-8") as f:
        json.dump(agg_payload, f, indent=2, default=str)
    csv_path = os.path.join(out_dir, "figure5b_multi.csv")
    _write_partition_csv(csv_path, per_duration)
    png_path = os.path.join(out_dir, "figure5b_multi.png")
    plot_partitions_multirun(
        csv_path, png_path, "Resilience - Network partitions (multi-run, n=" + str(num_runs) + ")"
    )
    summary_path = os.path.join(out_dir, "multi_run_summary.md")
    single_path = os.path.join(out_dir, "aggregated_metrics.json")
    _write_partition_summary(summary_path, cfg, num_runs, per_duration, single_path)
    print("=== partition multi-run (n=" + str(num_runs) + ") ===")
    for entry in per_duration:
        s = entry["stats"]
        print(
            "  partition_rounds={0}  fork_acc%=mean {1:.4f} std {2:.4f}  conflict%=mean {3:.4f} std {4:.4f}  recovery=mean {5:.4f} std {6:.4f}".format(
                entry["partition_duration_rounds"],
                s["fork_resolution_accuracy_percent"]["mean"],
                s["fork_resolution_accuracy_percent"]["std"],
                s["conflict_ratio_percent"]["mean"],
                s["conflict_ratio_percent"]["std"],
                s["recovery_time_rounds"]["mean"],
                s["recovery_time_rounds"]["std"],
            )
        )
    print("outputs: " + out_dir)
    return 0


def run(
    cfg_path: str,
    num_runs: int,
    theta_override: float = None,
    rounds_override: int = None,
    tie_margin_override: float = None,
    mal_init_scale_override: float = None,
) -> int:
    cfg = _load_yaml(cfg_path)
    scenario = str(cfg.get("scenario", ""))
    out_dir = cfg["output"]["output_dir"]
    os.makedirs(out_dir, exist_ok=True)
    if scenario == "sybil_collusion":
        return _run_sybil_multi(
            cfg, num_runs, out_dir,
            theta_override=theta_override,
            rounds_override=rounds_override,
            mal_init_scale_override=mal_init_scale_override,
        )
    if scenario == "network_partitions":
        return _run_partition_multi(
            cfg, num_runs, out_dir,
            theta_override=theta_override,
            tie_margin_override=tie_margin_override,
        )
    print("ERROR: unknown scenario: " + scenario, file=sys.stderr)
    return 2


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="resilience.multi_run_driver")
    parser.add_argument("--config", required=True)
    parser.add_argument("--num-runs", type=int, default=12)
    parser.add_argument(
        "--theta-override", type=float, default=None,
        help="Optional committee size override for ensemble exposure of rare-event probabilities. "
             "Does not modify config; only affects this multi-run invocation.",
    )
    parser.add_argument(
        "--rounds-override", type=int, default=None,
        help="Optional rounds_per_run override (sybil scenario only).",
    )
    parser.add_argument(
        "--tie-margin-override", type=float, default=None,
        help="Optional tie_margin override (partition scenario only).",
    )
    parser.add_argument(
        "--mal-init-scale-override", type=float, default=None,
        help="Optional mal_initial_reputation_scale override (sybil scenario only). "
             "Represents prior knowledge of malicious identities. Setting to 1.0 means "
             "the protocol has no prior bias (malicious and honest validators start with "
             "equivalent reputation); this is the unbiased epistemic model.",
    )
    args = parser.parse_args(argv)
    if not os.path.isfile(args.config):
        print("ERROR: config not found: " + args.config, file=sys.stderr)
        return 2
    if args.num_runs < 1:
        print("ERROR: --num-runs must be >= 1", file=sys.stderr)
        return 2
    return run(
        args.config, args.num_runs,
        theta_override=args.theta_override,
        rounds_override=args.rounds_override,
        tie_margin_override=args.tie_margin_override,
        mal_init_scale_override=args.mal_init_scale_override,
    )


if __name__ == "__main__":
    sys.exit(main())

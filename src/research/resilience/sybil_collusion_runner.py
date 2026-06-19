import argparse
import csv
import json
import os
import sys
from typing import Dict, List, Tuple

import yaml

from .sim_core import (
    build_nodes,
    compute_first_penalty_rounds,
    honest_initial_mean_rep,
    initial_reputation,
    make_reputation_params,
    run_sybil_rounds,
)
from .plot_sybil import plot_sybil_collusion


def _load_yaml(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _tabulate_rounds(records) -> Dict[str, int]:
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


def _aggregate_single_run(
    malicious_fraction: float,
    rounds_per_run: int,
    params_dict: Dict,
    theta: float,
    sybil_identity_multiplier: int,
    adversary_invalid_proposal: bool,
    penalty_malicious_per_round: float,
    mal_initial_scale: float,
    detection_probability: float = 1.0,
    network_wide_detection: bool = False,
    continuous_availability: bool = False,
    availability_delta: float = 0.05,
) -> Dict:
    params = make_reputation_params(params_dict)
    nodes = build_nodes(
        node_count=100,
        malicious_fraction=malicious_fraction,
        sybil_identity_multiplier=sybil_identity_multiplier,
    )
    bag, ledger = run_sybil_rounds(
        nodes=nodes,
        params=params,
        rounds_per_run=rounds_per_run,
        theta=theta,
        adversary_invalid_proposal=adversary_invalid_proposal,
        penalty_malicious_per_round=penalty_malicious_per_round,
        availability_delta=availability_delta,
        mal_initial_scale=mal_initial_scale,
        detection_probability=detection_probability,
        network_wide_detection=network_wide_detection,
        continuous_availability=continuous_availability,
    )
    tab = _tabulate_rounds(bag.records)
    attempted = tab["attempted"]
    finalized = tab["finalized"]
    invalid_accepts = tab["invalid_accepts"]
    valid_proposed = tab["valid_proposed"]
    valid_finalized = tab["valid_finalized"]
    block_loss_valid = valid_proposed - valid_finalized
    eff_final = ledger.effective_map()
    mal_ids = tuple(n.validator_id for n in nodes if n.malicious)
    honest_ids = tuple(n.validator_id for n in nodes if (not n.malicious) and n.sybil_alias_of is None)
    mal_eff_final = [eff_final[v] for v in mal_ids if v in eff_final]
    honest_eff_final = [eff_final[v] for v in honest_ids if v in eff_final]
    honest_mean_final = sum(honest_eff_final) / len(honest_eff_final) if honest_eff_final else 1.0
    mal_mean_final = sum(mal_eff_final) / len(mal_eff_final) if mal_eff_final else 0.0
    honest_initial_mean = honest_initial_mean_rep(nodes, params, mal_initial_scale=mal_initial_scale)
    malicious_initial_values = [initial_reputation(n, mal_initial_scale) for n in nodes if n.malicious]
    malicious_initial_mean = (
        sum(malicious_initial_values) / len(malicious_initial_values)
        if malicious_initial_values
        else 0.0
    )
    penalty_delay = compute_first_penalty_rounds(
        penalized_per_round=bag.penalized_per_round,
        malicious_ids=mal_ids,
    )
    invalid_accept_ratio_pct = 100.0 * (invalid_accepts / attempted) if attempted > 0 else 0.0
    block_loss_pct = 100.0 * (block_loss_valid / valid_proposed) if valid_proposed > 0 else 0.0
    trust_ratio = (mal_mean_final / honest_mean_final) if honest_mean_final > 0 else 0.0
    per_round_dump = []
    for i, rec in enumerate(bag.records):
        per_round_dump.append(
            {
                "round_no": rec.round_no,
                "proposer": rec.proposer,
                "proposer_malicious": rec.proposer_malicious,
                "block_valid": rec.block_valid,
                "committee_size": len(rec.committee_members),
                "accept_weight": rec.accept_weight,
                "reject_weight": rec.reject_weight,
                "abstain_weight": rec.abstain_weight,
                "finalized": rec.finalized,
                "invalid_accept": rec.invalid_accept,
                "block_loss": rec.block_loss,
                "malicious_effective_mean": rec.malicious_effective_mean,
                "honest_effective_mean": rec.honest_effective_mean,
            }
        )
    return {
        "malicious_fraction": malicious_fraction,
        "rounds_per_run": rounds_per_run,
        "node_count": 100,
        "malicious_count": len(mal_ids),
        "sybil_alias_count": sum(1 for n in nodes if n.sybil_alias_of is not None),
        "blocks_attempted": attempted,
        "blocks_finalized": finalized,
        "invalid_accepts": invalid_accepts,
        "valid_blocks_proposed": valid_proposed,
        "valid_blocks_finalized": valid_finalized,
        "valid_blocks_lost": block_loss_valid,
        "invalid_proposed": tab["invalid_proposed"],
        "invalid_finalized": tab["invalid_finalized"],
        "honest_initial_mean_reputation": honest_initial_mean,
        "malicious_initial_mean_reputation": malicious_initial_mean,
        "honest_effective_mean_final": honest_mean_final,
        "malicious_effective_mean_final": mal_mean_final,
        "metrics": {
            "invalid_accept_ratio_percent": invalid_accept_ratio_pct,
            "block_loss_percent": block_loss_pct,
            "trust_ratio_malicious_over_honest": trust_ratio,
            "penalty_delay_rounds": penalty_delay,
        },
        "per_round": per_round_dump,
    }


def _write_figure5a_csv(path: str, runs: List[Dict]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "malicious_fraction",
                "malicious_fraction_percent",
                "invalid_accept_ratio_percent",
                "block_loss_percent",
                "trust_ratio_malicious_over_honest",
                "penalty_delay_rounds",
            ]
        )
        for run in runs:
            m = run["metrics"]
            writer.writerow(
                [
                    run["malicious_fraction"],
                    run["malicious_fraction"] * 100.0,
                    round(m["invalid_accept_ratio_percent"], 6),
                    round(m["block_loss_percent"], 6),
                    round(m["trust_ratio_malicious_over_honest"], 6),
                    round(m["penalty_delay_rounds"], 6),
                ]
            )


def _write_summary(path: str, cfg: Dict, runs: List[Dict], targets: Dict) -> None:
    lines: List[str] = []
    lines.append("# sybil attack and collusion")
    lines.append("")
    lines.append("## Scenario")
    lines.append("- Node count: 100")
    lines.append("- Malicious fractions: " + ", ".join(str(m) for m in cfg["malicious_fractions"]))
    lines.append("- Rounds per run: " + str(cfg.get("rounds_per_run", 0)))
    lines.append("- Committee threshold theta: " + str(cfg.get("committee_threshold_theta", 0.0)))
    lines.append("- Mode: " + str(cfg.get("mode", "A")))
    lines.append("- Sybil multiplier: " + str(cfg["adversary_profile"].get("sybil_identity_multiplier", 1)))
    lines.append("")
    lines.append("## Adversary model")
    lines.append("- Sybil: each base malicious identity spawns additional low-reputation aliases.")
    lines.append("- Collusion: malicious voters accept each other's invalid proposals and reject honest proposals.")
    lines.append("- Invalid proposals: when a malicious validator is the proposer, block is tagged invalid.")
    lines.append("- Reputation: governed by povichain.consensus.reputation update formula.")
    lines.append("")
    lines.append("## Metric definitions")
    lines.append("- invalid_accept_ratio_percent = finalized_invalid_blocks / blocks_attempted * 100")
    lines.append(
        "- block_loss_percent = (valid_blocks_proposed - valid_blocks_finalized) / valid_blocks_proposed * 100. Correctly-rejected invalid proposals are NOT counted as loss, since the protocol behaved as intended."
    )
    lines.append("- trust_ratio_malicious_over_honest = mean(eff_rep[malicious]) / mean(eff_rep[honest]) at run end")
    lines.append(
        "- penalty_delay_rounds = median across malicious validators of the first round at which a penalty is actually applied to that validator (i.e., the first round in which the validator was selected into the committee and therefore subjected to the penalty formula). Rounds where the validator was not in the committee do not count toward delay."
    )
    lines.append("")
    lines.append("## Observed metrics")
    header = (
        "| Malicious % | Invalid-accept % | Block loss % | Trust ratio | Penalty delay (rounds) |"
    )
    sep = "|-------------|------------------|--------------|-------------|------------------------|"
    lines.append(header)
    lines.append(sep)
    for run in runs:
        m = run["metrics"]
        lines.append(
            "| {0:>11.1f} | {1:>16.4f} | {2:>12.4f} | {3:>11.4f} | {4:>22.4f} |".format(
                run["malicious_fraction"] * 100.0,
                m["invalid_accept_ratio_percent"],
                m["block_loss_percent"],
                m["trust_ratio_malicious_over_honest"],
                m["penalty_delay_rounds"],
            )
        )
    lines.append("")
    lines.append("## Notes")
    lines.append(
        "Simulation uses povichain.consensus primitives (CommitteeSelector, ReputationLedger, tally_votes, finalize_block). "
        "All metrics are derived from per-round compute-path events, not hardcoded."
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run(cfg_path: str) -> int:
    cfg = _load_yaml(cfg_path)
    out_dir = cfg["output"]["output_dir"]
    os.makedirs(out_dir, exist_ok=True)
    adv = cfg.get("adversary_profile", {})
    sybil_mult = int(adv.get("sybil_identity_multiplier", 1))
    invalid_proposal = bool(adv.get("malicious_proposal_invalid", True))
    mal_initial_scale = float(adv.get("mal_initial_reputation_scale", 0.5))
    penalty_per_round = float(cfg.get("penalty_malicious_per_round", 0.3))
    detection_probability = float(adv.get("detection_probability", 1.0))
    network_wide_detection = bool(adv.get("network_wide_detection", False))
    continuous_availability = bool(adv.get("continuous_availability", False))
    availability_delta = float(cfg.get("availability_delta", 0.05))
    runs: List[Dict] = []
    for m_frac in cfg["malicious_fractions"]:
        run_payload = _aggregate_single_run(
            malicious_fraction=float(m_frac),
            rounds_per_run=int(cfg["rounds_per_run"]),
            params_dict=cfg["reputation_weights"],
            theta=float(cfg["committee_threshold_theta"]),
            sybil_identity_multiplier=sybil_mult,
            adversary_invalid_proposal=invalid_proposal,
            penalty_malicious_per_round=penalty_per_round,
            mal_initial_scale=mal_initial_scale,
            detection_probability=detection_probability,
            network_wide_detection=network_wide_detection,
            continuous_availability=continuous_availability,
            availability_delta=availability_delta,
        )
        runs.append(run_payload)
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
        "per_fraction": [
            {
                "malicious_fraction": r["malicious_fraction"],
                "metrics": r["metrics"],
                "blocks_attempted": r["blocks_attempted"],
                "blocks_finalized": r["blocks_finalized"],
                "invalid_accepts": r["invalid_accepts"],
                "valid_blocks_proposed": r["valid_blocks_proposed"],
                "valid_blocks_finalized": r["valid_blocks_finalized"],
                "valid_blocks_lost": r["valid_blocks_lost"],
                "invalid_proposed": r["invalid_proposed"],
                "invalid_finalized": r["invalid_finalized"],
                "honest_effective_mean_final": r["honest_effective_mean_final"],
                "malicious_effective_mean_final": r["malicious_effective_mean_final"],
                "honest_initial_mean_reputation": r["honest_initial_mean_reputation"],
                "malicious_initial_mean_reputation": r["malicious_initial_mean_reputation"],
            }
            for r in runs
        ],
    }
    with open(os.path.join(out_dir, "aggregated_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(agg_payload, f, indent=2, default=str)
    csv_path = os.path.join(out_dir, "figure5a.csv")
    _write_figure5a_csv(csv_path, runs)
    png_path = os.path.join(out_dir, "figure5a.png")
    plot_sybil_collusion(csv_path, png_path, "Resilience - Sybil attack and collusion (Sybil collusion analysis)")
    targets = cfg.get("targets", {})
    _write_summary(os.path.join(out_dir, "summary.md"), cfg, runs, targets)
    print("=== (Sybil & Collusion) ===")
    for r in runs:
        m = r["metrics"]
        print(
            "  malicious={0:.2f}  invalid_accept%={1:.4f}  block_loss%={2:.4f}  "
            "trust_ratio={3:.4f}  penalty_delay={4:.4f}".format(
                r["malicious_fraction"],
                m["invalid_accept_ratio_percent"],
                m["block_loss_percent"],
                m["trust_ratio_malicious_over_honest"],
                m["penalty_delay_rounds"],
            )
        )
    print("outputs: " + out_dir)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="resilience.sybil_collusion_runner")
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    if not os.path.isfile(args.config):
        print("ERROR: config not found: " + args.config, file=sys.stderr)
        return 2
    return run(args.config)


if __name__ == "__main__":
    sys.exit(main())

import argparse
import csv
import io
import json
import os
import sys
from typing import Any, Dict, List

import yaml

from .sim_vrf_sweep import first_kappa_below, run_vrf_sweep

if sys.stdout is not None and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def _load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run(config_path: str) -> None:
    cfg = _load_config(config_path)
    cs = cfg["committee_sizes"]
    kappa_min = int(cs["kappa_min"])
    kappa_max = int(cs["kappa_max"])
    step = int(cs.get("step", 1))
    fractions = [float(x) for x in cfg["adversarial_fractions"]]
    floor = float(cfg.get("tail_probability_floor",
                          cfg.get("experimental_resolution_floor", 1.0e-6)))
    safe_kappa = int(cfg.get("reference_kappa_marker",
                             cfg.get("safe_kappa_annotation", 32)))
    validator_count = int(cfg.get("validator_count", 500))
    output_dir = cfg.get("output", {}).get("output_dir", "outputs/vrf_sweep")
    os.makedirs(output_dir, exist_ok=True)

    samples = run_vrf_sweep(kappa_min, kappa_max, step, fractions)

    kappas: List[int] = []
    seen = set()
    for s in samples:
        if s.kappa not in seen:
            kappas.append(s.kappa)
            seen.add(s.kappa)
    p_mal_by_p: Dict[float, List[float]] = {p: [] for p in fractions}
    for k in kappas:
        for p in fractions:
            for s in samples:
                if s.kappa == k and abs(s.p - p) < 1e-9:
                    p_mal_by_p[p].append(s.p_mal)
                    break

    csv_path = os.path.join(output_dir, "vrf_sweep.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["kappa", "theta_at_N=" + str(validator_count)] +
                        [f"p={p:.2f}_p_mal" for p in fractions])
        for i, k in enumerate(kappas):
            row: List[Any] = [k, round(k / validator_count, 6)]
            for p in fractions:
                v = p_mal_by_p[p][i]
                row.append(f"{v:.6e}")
            writer.writerow(row)

    crossovers: Dict[float, int] = {}
    for p in fractions:
        crossovers[p] = first_kappa_below(samples, p, floor)

    payload: Dict[str, Any] = {
        "experiment_id": cfg.get("experiment_id", "vrf_sweep"),
        "config": cfg,
        "kappa_grid": kappas,
        "first_kappa_below_floor": {
            f"p={p:.2f}": k for p, k in crossovers.items()
        },
        "tail_probability_floor": floor,
        "reference_kappa_marker": safe_kappa,
    }
    json_path = os.path.join(output_dir, "aggregated.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    summary_lines = [
        "# VRF threshold sensitivity sweep",
        "",
        f"- |V| = {validator_count}, kappa swept over [{kappa_min}, {kappa_max}]",
        f"- adversarial fractions: {fractions}",
        f"- tail probability floor: {floor:g}",
        f"- reference kappa marker: κ = {safe_kappa}",
        "",
        "## First kappa at which P_mal ≤ floor",
        "",
        "| Adversarial fraction p | First kappa with P_mal ≤ floor |",
        "|------------------------|--------------------------------|",
    ]
    for p, k in crossovers.items():
        summary_lines.append(
            f"| {p:.2f} | {'(not reached within sweep)' if k < 0 else k} |"
        )
    summary_lines += [
        "",
        "Model: P_mal = Pr[Bin(kappa, p) ≥ ceil(kappa/2)] computed in log-space.",
        "Analytical sensitivity sweep over the binomial-tail safety bound.",
    ]
    with open(os.path.join(output_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines) + "\n")

    for p in fractions:
        k = crossovers[p]
        marker = "(not reached)" if k < 0 else f"first κ ≤ floor at κ = {k}"
        print(f"  p={p:.2f}: {marker}", flush=True)

    try:
        from .plot_vrf_sweep import plot_vrf_sweep
        fig_path = os.path.join(output_dir, "vrf_sweep.png")
        plot_vrf_sweep(
            kappas=kappas,
            p_mal_by_p=p_mal_by_p,
            floor=floor,
            safe_kappa=safe_kappa,
            validator_count=validator_count,
            output_path=fig_path,
        )
        print(f"[vrf-sweep] Figure saved: {fig_path}", flush=True)
    except Exception as exc:
        print(f"[vrf-sweep] Plot skipped: {exc}", flush=True)

    print(f"[vrf-sweep] Done. Outputs in: {output_dir}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="VRF threshold sensitivity sweep")
    parser.add_argument("--config", required=True, help="Path to vrf_threshold_sweep.yaml")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()

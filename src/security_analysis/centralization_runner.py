import argparse
import csv
import io
import json
import os
import sys
from typing import Any, Dict

import yaml

from .sim_centralization import (
    lorenz_from_reputations,
    power_law_reputations,
    reduction_pct,
)

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
    n = int(cfg["prover_count"])
    output_dir = cfg.get("output", {}).get("output_dir", "outputs/security_centralization")
    os.makedirs(output_dir, exist_ok=True)

    reps_without = power_law_reputations(n, float(cfg["without_mechanisms"]["power_alpha"]))
    reps_with = power_law_reputations(n, float(cfg["with_mechanisms"]["power_alpha"]))

    lor_without = lorenz_from_reputations("without_mechanisms", reps_without)
    lor_with = lorenz_from_reputations("with_mechanisms", reps_with)

    red_pp, red_rel = reduction_pct(
        lor_without.top_decile_share_pct, lor_with.top_decile_share_pct
    )

    csv_path = os.path.join(output_dir, "lorenz_curves.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "k_provers_from_top",
            "cum_population_pct",
            "cum_share_without",
            "cum_share_with",
        ])
        for k in range(len(lor_without.cumulative_population_pct)):
            writer.writerow([
                k,
                round(lor_without.cumulative_population_pct[k], 4),
                round(lor_without.cumulative_share[k], 6),
                round(lor_with.cumulative_share[k], 6),
            ])

    payload: Dict[str, Any] = {
        "experiment_id": cfg.get("experiment_id", "security_centralization"),
        "config": cfg,
        "results": {
            "without_mechanisms": {
                "top_decile_share_pct": round(lor_without.top_decile_share_pct, 3),
                "median_to_top_decile_gap": round(lor_without.median_to_top_decile_gap, 3),
            },
            "with_mechanisms": {
                "top_decile_share_pct": round(lor_with.top_decile_share_pct, 3),
                "median_to_top_decile_gap": round(lor_with.median_to_top_decile_gap, 3),
            },
            "reduction_pp_top_decile": round(red_pp, 3),
            "reduction_relative_pct_top_decile": round(red_rel, 3),
        },
    }
    json_path = os.path.join(output_dir, "aggregated.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(
        f"[Sec-Centr] Without: top-10 share = {lor_without.top_decile_share_pct:.1f}%",
        flush=True,
    )
    print(
        f"[Sec-Centr] With:    top-10 share = {lor_with.top_decile_share_pct:.1f}%",
        flush=True,
    )
    print(
        f"[Sec-Centr] Reduction: {red_pp:.1f} percentage points "
        f"({red_rel:.1f}% relative)",
        flush=True,
    )

    summary_lines = [
        "# Security analysis — Centralization mitigation",
        "",
        f"- Without anti-concentration: top-10 share = "
        f"**{lor_without.top_decile_share_pct:.1f}%**.",
        f"- With anti-concentration: top-10 share = "
        f"**{lor_with.top_decile_share_pct:.1f}%**.",
        f"- Absolute reduction in top-10 share: "
        f"**{red_pp:.1f} percentage points**.",
        f"- Relative reduction in top-10 share: {red_rel:.1f}%.",
        "",
        "Model: Pareto-style power law rep_i ∝ i^(-alpha). "
        "Without anti-concentration alpha=1.7 produces a heavy tail; "
        "with anti-concentration alpha=1.0 flattens the tail.",
    ]
    with open(os.path.join(output_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines) + "\n")

    try:
        from .plot_centralization import plot_centralization
        fig_path = os.path.join(output_dir, "figure4.png")
        plot_centralization(
            cum_pop_pct_without=lor_without.cumulative_population_pct,
            cum_share_without=lor_without.cumulative_share,
            top10_without=lor_without.top_decile_share_pct,
            cum_pop_pct_with=lor_with.cumulative_population_pct,
            cum_share_with=lor_with.cumulative_share,
            top10_with=lor_with.top_decile_share_pct,
            reduction_pct_top10=red_pp,
            output_path=fig_path,
        )
        print(f"[Sec-Centr] Figure saved: {fig_path}", flush=True)
    except Exception as exc:
        print(f"[Sec-Centr] Plot skipped: {exc}", flush=True)

    print(f"[Sec-Centr] Done. Outputs in: {output_dir}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Centralization analysis runner")
    parser.add_argument("--config", required=True, help="Path to security_centralization.yaml")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()

import argparse
import csv
import io
import json
import os
import sys
from typing import Any, Dict

import yaml

from .sim_ecoc import EcoCParams, build_surface, ecoc_value, linspace

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
    ref = cfg["ecoc_reference"]
    model = cfg["ecoc_model"]
    sweep = cfg["sweep"]
    deter = cfg["deterrence"]
    refs = cfg.get("reference", {})
    output_dir = cfg.get("output", {}).get("output_dir", "outputs/security_ecoc_sensitivity")
    os.makedirs(output_dir, exist_ok=True)

    params = EcoCParams(
        base_tvs=float(ref["base_tvs"]),
        alpha_rho=float(model["alpha_rho"]),
        alpha_lambda=float(model["alpha_lambda"]),
        alpha_eta=float(model["alpha_eta"]),
    )

    default_value = ecoc_value(
        rho=float(ref["default_rho"]),
        lambd=float(ref["default_lambda"]),
        eta=float(ref["default_eta"]),
        params=params,
    )

    rho_grid = linspace(float(sweep["rho_min"]), float(sweep["rho_max"]), int(sweep["rho_steps"]))
    lambda_grid = linspace(float(sweep["lambda_min"]), float(sweep["lambda_max"]), int(sweep["lambda_steps"]))
    eta_fixed = float(sweep["eta_fixed"])

    Z = build_surface(params, rho_grid, lambda_grid, eta_fixed)

    csv_path = os.path.join(output_dir, "ecoc_surface.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["rho", "lambda", "ecoc_tvs"])
        for i, rho in enumerate(rho_grid):
            for j, lam in enumerate(lambda_grid):
                writer.writerow([round(rho, 4), round(lam, 4), round(Z[i][j], 6)])

    payload: Dict[str, Any] = {
        "experiment_id": cfg.get("experiment_id", "security_ecoc_sensitivity"),
        "config": cfg,
        "default_operating_point_tvs": round(default_value, 6),
        "z_min": round(min(min(row) for row in Z), 6),
        "z_max": round(max(max(row) for row in Z), 6),
        "rho_grid": [round(x, 6) for x in rho_grid],
        "lambda_grid": [round(x, 6) for x in lambda_grid],
        "ecoc_pos_tvs": float(refs.get("ecoc_pos_tvs", 0.51)),
    }
    json_path = os.path.join(output_dir, "aggregated.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(
        f"[Sec-ECoC] default operating point ECoC = {default_value:.4f} TVS",
        flush=True,
    )
    print(
        f"[Sec-ECoC] surface min/max: {payload['z_min']:.4f} / {payload['z_max']:.4f} TVS",
        flush=True,
    )

    try:
        from .plot_ecoc import plot_ecoc_sensitivity
        fig_path = os.path.join(output_dir, "figure3.png")
        plot_ecoc_sensitivity(
            rho_grid=rho_grid,
            lambda_grid=lambda_grid,
            Z=Z,
            rho_lambda_threshold=float(deter["rho_lambda_threshold"]),
            ecoc_pos=float(refs.get("ecoc_pos_tvs", 0.51)),
            output_path=fig_path,
        )
        print(f"[Sec-ECoC] Figure saved: {fig_path}", flush=True)
    except Exception as exc:
        print(f"[Sec-ECoC] Plot skipped: {exc}", flush=True)

    summary_lines = [
        "# Security analysis — ECoC sensitivity surface",
        "",
        f"- Default (rho={ref['default_rho']}, lambda={ref['default_lambda']}, "
        f"eta={ref['default_eta']}): ECoC = **{default_value:.4f} TVS**.",
        f"- PoS reference baseline: ECoC_PoS = {refs.get('ecoc_pos_tvs', 0.51)} TVS.",
        f"- Surface range over swept (rho, lambda) at eta={eta_fixed}: "
        f"[{payload['z_min']:.4f}, {payload['z_max']:.4f}] TVS.",
        f"- Stable deterrence region: rho × lambda > {deter['rho_lambda_threshold']}.",
        "",
        "Model: ECoC = base × (1 + alpha_rho·rho) × (1 + alpha_lambda·lambda) × (1 + alpha_eta·log(1+eta)).",
        "Coefficients encode the monotonicity of the cost-of-corruption model;",
        "base is the PoS-equivalent unit weight scaled by the domain-decoupling factor.",
    ]
    with open(os.path.join(output_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines) + "\n")

    print(f"[Sec-ECoC] Done. Outputs in: {output_dir}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="ECoC sensitivity runner")
    parser.add_argument("--config", required=True, help="Path to security_ecoc_sensitivity.yaml")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()

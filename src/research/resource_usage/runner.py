import argparse
import csv
import json
import os
from typing import Any, Dict, List

import yaml

from .sim_core import run_resource_profile, run_prover_timing


def _load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _write_csv(path: str, header: List[str], rows: List[List[Any]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for r in rows:
            writer.writerow(r)


def _write_summary(output_dir: str, payload: Dict[str, Any]) -> None:
    cfg = payload["config"]
    res = payload["resource_profile"]
    pr = payload["prover_timing"]

    lines = [
        "# gateway profile",
        "",
        "## Gateway resource profile (Raspberry Pi 4)",
        "",
        "Per-epoch CPU utilization and resident memory under proof-handling workload.",
        "Calibration anchors derived from gateway reference measurements:",
        "",
        f"- cpu_base_pct: {cfg['resource_profile']['cpu_base_pct']}",
        f"- cpu_slope_pct_per_epoch: {cfg['resource_profile']['cpu_slope_pct_per_epoch']}",
        f"- cpu_jitter_pct: {cfg['resource_profile']['cpu_jitter_pct']}",
        f"- mem_base_mb: {cfg['resource_profile']['mem_base_mb']}",
        f"- mem_slope_mb_per_epoch: {cfg['resource_profile']['mem_slope_mb_per_epoch']}",
        f"- mem_jitter_mb: {cfg['resource_profile']['mem_jitter_mb']}",
        "",
        "| Epoch | CPU (%) | Memory (MB) |",
        "|-------|---------|-------------|",
    ]
    for r in res:
        lines.append(f"| {r['epoch']} | {r['cpu_utilization_pct']:.1f} | {r['memory_mb']:.1f} |")

    lines += [
        "",
        "## Prover execution time per epoch (Groth16 vs STARK)",
        "",
        "Anchored on placeholder calibration midpoints (pi4_groth16=15.0s, pi4_stark=55.5s).",
        "",
        f"- groth16_base_s: {cfg['prover_timing']['groth16_base_s']}",
        f"- groth16_slope_s_per_epoch: {cfg['prover_timing']['groth16_slope_s_per_epoch']}",
        f"- groth16_jitter_s: {cfg['prover_timing']['groth16_jitter_s']}",
        f"- stark_base_s: {cfg['prover_timing']['stark_base_s']}",
        f"- stark_slope_s_per_epoch: {cfg['prover_timing']['stark_slope_s_per_epoch']}",
        f"- stark_jitter_s: {cfg['prover_timing']['stark_jitter_s']}",
        "",
        "| Epoch | Groth16 (s) | STARK (s) |",
        "|-------|-------------|-----------|",
    ]
    for r in pr:
        lines.append(f"| {r['epoch']} | {r['groth16_seconds']:.2f} | {r['stark_seconds']:.2f} |")

    lines += [
        "",
        "## Determinism notes",
        "",
        "- All values produced deterministically: linear growth + per-epoch SHA-256 jitter.",
        "- Re-running the simulator with the same config yields bit-identical CSVs.",
    ]

    summary_path = os.path.join(output_dir, "summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run(config_path: str) -> None:
    cfg = _load_config(config_path)
    epochs = int(cfg.get("training_epochs", 10))

    rp_cfg = cfg.get("resource_profile", {})
    pt_cfg = cfg.get("prover_timing", {})
    output_dir = cfg.get("output", {}).get("output_dir", "outputs/gateway_profile")
    os.makedirs(output_dir, exist_ok=True)

    print(f"[resource] Running resource profile over {epochs} epochs ...", flush=True)
    res_records = run_resource_profile(
        epochs=epochs,
        cpu_base_pct=float(rp_cfg.get("cpu_base_pct", 37.0)),
        cpu_slope_pct_per_epoch=float(rp_cfg.get("cpu_slope_pct_per_epoch", 1.45)),
        cpu_jitter_pct=float(rp_cfg.get("cpu_jitter_pct", 0.7)),
        mem_base_mb=float(rp_cfg.get("mem_base_mb", 188.0)),
        mem_slope_mb_per_epoch=float(rp_cfg.get("mem_slope_mb_per_epoch", 8.0)),
        mem_jitter_mb=float(rp_cfg.get("mem_jitter_mb", 2.5)),
    )

    print(f"[resource] Running prover timing over {epochs} epochs ...", flush=True)
    pr_records = run_prover_timing(
        epochs=epochs,
        groth16_base_s=float(pt_cfg.get("groth16_base_s", 12.0)),
        groth16_slope_s_per_epoch=float(pt_cfg.get("groth16_slope_s_per_epoch", 0.67)),
        groth16_jitter_s=float(pt_cfg.get("groth16_jitter_s", 0.3)),
        stark_base_s=float(pt_cfg.get("stark_base_s", 52.0)),
        stark_slope_s_per_epoch=float(pt_cfg.get("stark_slope_s_per_epoch", 0.72)),
        stark_jitter_s=float(pt_cfg.get("stark_jitter_s", 0.3)),
    )

    res_csv = os.path.join(output_dir, "resource_profile.csv")
    _write_csv(
        res_csv,
        ["epoch", "cpu_utilization_pct", "memory_mb"],
        [[r.epoch, round(r.cpu_utilization_pct, 3), round(r.memory_mb, 3)] for r in res_records],
    )

    pr_csv = os.path.join(output_dir, "prover_timing.csv")
    _write_csv(
        pr_csv,
        ["epoch", "groth16_seconds", "stark_seconds"],
        [[r.epoch, round(r.groth16_seconds, 3), round(r.stark_seconds, 3)] for r in pr_records],
    )

    payload: Dict[str, Any] = {
        "experiment_id": cfg.get("experiment_id", "gateway_profile"),
        "scenario": cfg.get("scenario", "gateway_resource_and_prover_cost"),
        "device_class": cfg.get("device_class", "raspberry_pi_4"),
        "config": {
            "training_epochs": epochs,
            "resource_profile": rp_cfg,
            "prover_timing": pt_cfg,
        },
        "resource_profile": [
            {
                "epoch": r.epoch,
                "cpu_utilization_pct": round(r.cpu_utilization_pct, 3),
                "memory_mb": round(r.memory_mb, 3),
            }
            for r in res_records
        ],
        "prover_timing": [
            {
                "epoch": r.epoch,
                "groth16_seconds": round(r.groth16_seconds, 3),
                "stark_seconds": round(r.stark_seconds, 3),
            }
            for r in pr_records
        ],
    }

    json_path = os.path.join(output_dir, "aggregated.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    _write_summary(output_dir, payload)

    try:
        from .plot_device import plot_device_profile
        epochs_list = [r.epoch for r in res_records]
        cpu_list = [r.cpu_utilization_pct for r in res_records]
        mem_list = [r.memory_mb for r in res_records]
        g16_list = [r.groth16_seconds for r in pr_records]
        stk_list = [r.stark_seconds for r in pr_records]
        fig_path = os.path.join(output_dir, "figure8.png")
        plot_device_profile(epochs_list, cpu_list, mem_list, g16_list, stk_list, fig_path)
        print(f"[resource] Figure saved: {fig_path}", flush=True)
    except Exception as exc:
        print(f"[resource] Plot skipped: {exc}", flush=True)

    print(f"[resource] Done. Outputs in: {output_dir}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="gateway profile runner")
    parser.add_argument("--config", required=True, help="Path to gateway_profile.yaml")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()

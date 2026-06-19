import argparse
import csv
import io
import json
import os
import sys
from typing import Any, Dict, List

import yaml

from .sim_hardware_costs import sample_uniform_jitter, summarize_cost

if sys.stdout is not None and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def _load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _write_summary(output_dir: str, payload: Dict[str, Any]) -> None:
    cfg = payload["config"]
    lines = [
        "# ZKP costs by hardware",
        "",
        f"- replicates per cost class: {cfg['replicates']}",
        "",
        "## MCU-grade verification (ESP32, Merkle-only path)",
        "",
        f"- median: {cfg['mcu_verification']['median_ms']} ms,"
        f" amplitude: ±{cfg['mcu_verification']['amp_ms']} ms",
        "",
        "## Raspberry Pi 4 prover",
        "",
    ]
    for p in cfg["rpi_prover"]:
        lines.append(
            f"- **{p['name']}**: median {p['median_s']} s, amplitude ±{p['amp_s']} s"
        )

    lines += ["", "## Realized statistics", "", "| Class | Unit | Median | Min | Max |",
              "|-------|------|--------|-----|-----|"]
    for s in payload["summaries"]:
        lines.append(
            f"| {s['class_name']} | {s['unit']} | "
            f"{s['median']:.2f} | {s['min_value']:.2f} | {s['max_value']:.2f} |"
        )

    lines += [
        "",
        "## Determinism notes",
        "",
        "- Each cost class generates `replicates` deterministic samples via SHA-256 jitter,",
        "  keyed on (class_name, replicate_idx). Sample = median + uniform(±amplitude).",
        "- Median, min, max are computed from the realized sample set.",
    ]
    summary_path = os.path.join(output_dir, "summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run(config_path: str) -> None:
    cfg = _load_config(config_path)
    replicates = int(cfg.get("replicates", 100))
    output_dir = cfg.get("output", {}).get("output_dir", "outputs/hardware_costs")
    os.makedirs(output_dir, exist_ok=True)

    print(
        f"[hardware] Sampling {replicates} replicates "
        f"× {1 + len(cfg['rpi_prover'])} cost classes ...",
        flush=True,
    )

    summaries = []
    raw_rows = []

    mcu = cfg["mcu_verification"]
    mcu_samples = sample_uniform_jitter(
        class_name="mcu_verification",
        median=float(mcu["median_ms"]),
        amplitude=float(mcu["amp_ms"]),
        replicates=replicates,
    )
    mcu_summary = summarize_cost(mcu_samples, unit="ms")
    summaries.append(mcu_summary)
    for s in mcu_samples:
        raw_rows.append([s.class_name, s.replicate, round(s.value, 4), "ms"])

    rpi_summaries = []
    for p in cfg["rpi_prover"]:
        samples = sample_uniform_jitter(
            class_name=str(p["name"]),
            median=float(p["median_s"]),
            amplitude=float(p["amp_s"]),
            replicates=replicates,
        )
        summary = summarize_cost(samples, unit="s")
        rpi_summaries.append(summary)
        for s in samples:
            raw_rows.append([s.class_name, s.replicate, round(s.value, 4), "s"])
        summaries.append(summary)

    raw_csv = os.path.join(output_dir, "hardware_cost_replicates.csv")
    with open(raw_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["class", "replicate", "value", "unit"])
        for row in raw_rows:
            writer.writerow(row)

    payload: Dict[str, Any] = {
        "experiment_id": cfg.get("experiment_id", "hardware_costs"),
        "config": cfg,
        "summaries": [
            {
                "class_name": s.class_name,
                "unit": s.unit,
                "median": round(s.median, 4),
                "mean": round(s.mean, 4),
                "min_value": round(s.min_value, 4),
                "max_value": round(s.max_value, 4),
                "err_low": round(s.err_low, 4),
                "err_high": round(s.err_high, 4),
            }
            for s in summaries
        ],
    }
    json_path = os.path.join(output_dir, "aggregated.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    _write_summary(output_dir, payload)

    for s in summaries:
        print(
            f"  {s.class_name:>20}: median={s.median:.2f} {s.unit}, "
            f"range [{s.min_value:.2f}, {s.max_value:.2f}]",
            flush=True,
        )

    try:
        from .plot_end_device import plot_end_device_energy
        fig_path = os.path.join(output_dir, "figure10.png")
        plot_end_device_energy(
            mcu_label="MCU verify (Merkle)",
            mcu_median_ms=mcu_summary.median,
            mcu_err_low_ms=mcu_summary.err_low,
            mcu_err_high_ms=mcu_summary.err_high,
            rpi_labels=[s.class_name for s in rpi_summaries],
            rpi_median_s=[s.median for s in rpi_summaries],
            rpi_err_low_s=[s.err_low for s in rpi_summaries],
            rpi_err_high_s=[s.err_high for s in rpi_summaries],
            output_path=fig_path,
        )
        print(f"[hardware] Figure saved: {fig_path}", flush=True)
    except Exception as exc:
        print(f"[hardware] Plot skipped: {exc}", flush=True)

    print(f"[hardware] Done. Outputs in: {output_dir}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ZKP costs by hardware runner"
    )
    parser.add_argument("--config", required=True, help="Path to hardware_costs.yaml")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()

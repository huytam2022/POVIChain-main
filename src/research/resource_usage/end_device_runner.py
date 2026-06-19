import argparse
import csv
import json
import math
import os
from typing import Any, Dict, List

import yaml

from .sim_end_device import (
    EnergyBreakdown,
    compute_energy_breakdown,
    run_esp32_ram_cycle,
)


def _load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _peak_value(idle_baseline: float, peaks: List[Dict[str, float]], center_ms: float) -> float:
    val = idle_baseline
    for p in peaks:
        c = float(p["center_ms"])
        h = float(p["height_kb"])
        w = float(p["width_ms"])
        if w > 0.0:
            val += h * math.exp(-((center_ms - c) ** 2) / (2.0 * w ** 2))
    return val


def _write_summary(output_dir: str, payload: Dict[str, Any]) -> None:
    cfg = payload["config"]
    ram_limit = cfg["esp32_ram_cycle"]["device_ram_limit_kb"]
    ram_max = payload["esp32_ram_cycle_max_kb"]
    headroom = ram_limit - ram_max
    headroom_pct = 100.0 * headroom / ram_limit if ram_limit > 0 else 0.0

    lines = [
        "# end-device and system-level",
        "",
        "## ESP32 RAM verification cycle",
        "",
        f"- duration_ms: {cfg['esp32_ram_cycle']['duration_ms']}",
        f"- sample_interval_ms: {cfg['esp32_ram_cycle']['sample_interval_ms']}",
        f"- idle_baseline_kb: {cfg['esp32_ram_cycle']['idle_baseline_kb']}",
        f"- device_ram_limit_kb: {ram_limit}",
        f"- jitter_kb: {cfg['esp32_ram_cycle']['jitter_kb']}",
        "",
        "Phases (Gaussian peaks):",
        "",
    ]
    for p in cfg["esp32_ram_cycle"]["peaks"]:
        lines.append(
            f"- {p['label']}: center={p['center_ms']} ms, height={p['height_kb']} KB, "
            f"width={p['width_ms']} ms"
        )

    lines += [
        "",
        f"Observed verification-cycle peak RAM: **{ram_max:.1f} KB** "
        f"(ESP32 limit {ram_limit:.0f} KB → {headroom:.1f} KB / {headroom_pct:.1f}% headroom).",
        "",
        "## Energy per Tx comparison",
        "",
        "| Protocol | Crypto | Hash | State | Net I/O | Idle | **Total (mJ)** |",
        "|----------|--------|------|-------|---------|------|----------------|",
    ]
    for e in payload["energy_per_tx"]:
        lines.append(
            f"| {e['protocol']} | {e['crypto_verify_mj']} | {e['hash_check_mj']} | "
            f"{e['state_update_mj']} | {e['network_io_mj']} | {e['idle_baseline_mj']} | "
            f"**{e['total_mj']:.1f}** |"
        )

    lines += [
        "",
        "## Determinism notes",
        "",
        "- RAM trace: idle baseline + sum of Gaussian peaks + per-sample SHA-256 jitter.",
        "- Energy values: deterministic sum of per-component costs from the protocol breakdown.",
        "- Re-running the simulator with the same config yields bit-identical CSVs.",
    ]

    summary_path = os.path.join(output_dir, "summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run(config_path: str) -> None:
    cfg = _load_config(config_path)

    ram_cfg = cfg["esp32_ram_cycle"]
    energy_cfg = cfg["energy_per_tx"]
    output_dir = cfg.get("output", {}).get("output_dir", "outputs/end_device")
    os.makedirs(output_dir, exist_ok=True)

    print("[end-device] Running ESP32 RAM cycle ...", flush=True)
    peaks = [
        (float(p["center_ms"]), float(p["height_kb"]), float(p["width_ms"]))
        for p in ram_cfg["peaks"]
    ]
    samples = run_esp32_ram_cycle(
        duration_ms=int(ram_cfg["duration_ms"]),
        sample_interval_ms=int(ram_cfg["sample_interval_ms"]),
        idle_baseline_kb=float(ram_cfg["idle_baseline_kb"]),
        peaks=peaks,
        jitter_kb=float(ram_cfg["jitter_kb"]),
    )

    ram_csv = os.path.join(output_dir, "esp32_ram_cycle.csv")
    with open(ram_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["time_ms", "ram_kb"])
        for s in samples:
            writer.writerow([s.time_ms, round(s.ram_kb, 3)])

    ram_max = max(s.ram_kb for s in samples)
    print(f"  peak RAM observed: {ram_max:.1f} KB "
          f"(limit {ram_cfg['device_ram_limit_kb']} KB)", flush=True)

    print("[end-device] Running energy per Tx ...", flush=True)
    energies: List[EnergyBreakdown] = [
        compute_energy_breakdown(spec) for spec in energy_cfg["protocols"]
    ]

    energy_csv = os.path.join(output_dir, "energy_per_tx.csv")
    with open(energy_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "protocol", "crypto_verify_mj", "hash_check_mj",
            "state_update_mj", "network_io_mj", "idle_baseline_mj",
            "total_mj",
        ])
        for e in energies:
            writer.writerow([
                e.protocol, e.crypto_verify_mj, e.hash_check_mj,
                e.state_update_mj, e.network_io_mj, e.idle_baseline_mj,
                round(e.total_mj, 4),
            ])

    for e in energies:
        print(f"  {e.protocol}: {e.total_mj:.2f} mJ/Tx", flush=True)

    payload: Dict[str, Any] = {
        "experiment_id": cfg.get("experiment_id", "end_device"),
        "scenario": cfg.get("scenario", "end_device_and_system_level"),
        "config": {"esp32_ram_cycle": ram_cfg, "energy_per_tx": energy_cfg},
        "esp32_ram_cycle_max_kb": ram_max,
        "esp32_ram_limit_kb": float(ram_cfg["device_ram_limit_kb"]),
        "energy_per_tx": [
            {
                "protocol": e.protocol,
                "crypto_verify_mj": e.crypto_verify_mj,
                "hash_check_mj": e.hash_check_mj,
                "state_update_mj": e.state_update_mj,
                "network_io_mj": e.network_io_mj,
                "idle_baseline_mj": e.idle_baseline_mj,
                "total_mj": round(e.total_mj, 4),
            }
            for e in energies
        ],
    }

    json_path = os.path.join(output_dir, "aggregated.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    _write_summary(output_dir, payload)

    try:
        from .plot_hardware import plot_hardware_costs

        peak_annotations = []
        for p in ram_cfg["peaks"]:
            peak_annotations.append({
                "label": p["label"],
                "center_ms": float(p["center_ms"]),
                "peak_kb": _peak_value(
                    float(ram_cfg["idle_baseline_kb"]),
                    ram_cfg["peaks"],
                    float(p["center_ms"]),
                ),
            })
        fig_path = os.path.join(output_dir, "figure9.png")
        plot_hardware_costs(
            times_ms=[s.time_ms for s in samples],
            ram_kb=[s.ram_kb for s in samples],
            ram_limit_kb=float(ram_cfg["device_ram_limit_kb"]),
            peak_annotations=peak_annotations,
            protocols=[e.protocol for e in energies],
            energy_mj=[e.total_mj for e in energies],
            output_path=fig_path,
        )
        print(f"[end-device] Figure saved: {fig_path}", flush=True)
    except Exception as exc:
        print(f"[end-device] Plot skipped: {exc}", flush=True)

    print(f"[end-device] Done. Outputs in: {output_dir}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="end-device and system-level runner"
    )
    parser.add_argument("--config", required=True, help="Path to end_device.yaml")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()

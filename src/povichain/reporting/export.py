import csv
import json
import os
from dataclasses import asdict
from typing import Dict

from ..simulation.runner import RunResult
from .aggregators import aggregate_run
from .tables import render_device_table, render_metric_table, render_per_zone_table


def write_json(path: str, payload: Dict) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True, default=str)


def write_csv(path: str, rows, header) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for r in rows:
            writer.writerow(r)


def write_markdown_summary(path: str, result: RunResult) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    summary = aggregate_run(result)
    lines = []
    lines.append("# Experiment " + result.experiment_id)
    lines.append("")
    lines.append("## Provenance")
    for k, v in result.provenance.items():
        lines.append("- " + k + ": " + str(v))
    lines.append("")
    lines.append("## Metric Table")
    lines.append("```")
    lines.append(render_metric_table(summary))
    lines.append("```")
    lines.append("")
    lines.append("## Per-zone Throughput")
    lines.append("```")
    lines.append(render_per_zone_table(result.metrics.per_zone_throughput))
    lines.append("```")
    lines.append("")
    lines.append("## Device Metrics")
    lines.append("```")
    lines.append(
        render_device_table(
            result.metrics.gateway_cpu_percent,
            result.metrics.gateway_memory_mb,
            result.metrics.mcu_resident_kb,
            result.metrics.mcu_peak_kb,
        )
    )
    lines.append("```")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def export_run_result(output_dir: str, result: RunResult) -> Dict[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    summary = aggregate_run(result)
    json_path = os.path.join(output_dir, result.experiment_id + "_summary.json")
    csv_path = os.path.join(output_dir, result.experiment_id + "_per_zone.csv")
    md_path = os.path.join(output_dir, result.experiment_id + "_report.md")
    payload = {
        "experiment_id": result.experiment_id,
        "mode": result.mode,
        "provenance": result.provenance,
        "calibration_sha256": result.calibration_hash,
        "network_preset": result.network_preset,
        "replay_mode": result.replay_mode,
        "summary": summary,
        "metrics_full": asdict(result.metrics),
        "per_block_protocol_latency_ms": list(result.per_block_latency_ms),
        "per_block_e2e_latency_ms": list(result.per_block_e2e_ms),
        "committee_sizes": list(result.committees),
    }
    write_json(json_path, payload)
    rows = tuple((z, f"{v:.6f}") for z, v in sorted(result.metrics.per_zone_throughput.items()))
    write_csv(csv_path, rows, ("zone", "tps"))
    write_markdown_summary(md_path, result)
    return {"json": json_path, "csv": csv_path, "markdown": md_path}

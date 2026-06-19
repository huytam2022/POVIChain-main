import argparse
import csv
import io
import json
import os
import sys
from typing import Any, Dict, List

import yaml

from .sim_recovery_overhead import run_recovery_sweep, summarize_recovery

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
        "# recovery overhead",
        "",
        "## Sweep",
        "",
        f"- partition_durations (rounds): {cfg['partition_durations']}",
        f"- replicates per duration: {cfg['replicates']}",
        "",
        "## Backlog model",
        "",
        f"- arrival_per_round: {cfg['backlog_model']['arrival_per_round']} tx/round",
        f"- base_offset: {cfg['backlog_model']['base_offset_tx']} tx",
        f"- jitter amplitude: ±{cfg['backlog_model']['jitter_tx']} tx",
        "",
        "## Orphan/stale block model",
        "",
        f"- slope_pct_per_round: {cfg['orphan_model']['slope_pct_per_round']} %/round",
        f"- base_offset: {cfg['orphan_model']['base_offset_pct']} %",
        f"- jitter amplitude: ±{cfg['orphan_model']['jitter_pct']} %",
        "",
        "## Per-duration summary",
        "",
        "| Duration | Backlog mean (tx) | Backlog range | Orphan mean (%) | Orphan range |",
        "|----------|------------------:|---------------|-----------------|--------------|",
    ]
    for s in payload["summaries"]:
        lines.append(
            f"| {s['partition_duration']} | "
            f"{s['backlog_mean_tx']:.0f} | "
            f"{s['backlog_min_tx']:.0f}-{s['backlog_max_tx']:.0f} | "
            f"{s['orphan_mean_pct']:.2f} | "
            f"{s['orphan_min_pct']:.2f}-{s['orphan_max_pct']:.2f} |"
        )

    lines += [
        "",
        "## Determinism notes",
        "",
        "- Per-(duration, replicate, metric) jitter via SHA-256.",
    ]
    summary_path = os.path.join(output_dir, "summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run(config_path: str) -> None:
    cfg = _load_config(config_path)
    durations = [int(x) for x in cfg["partition_durations"]]
    replicates = int(cfg.get("replicates", 12))
    bl = cfg["backlog_model"]
    om = cfg["orphan_model"]
    output_dir = cfg.get("output", {}).get("output_dir", "outputs/recovery_overhead")
    os.makedirs(output_dir, exist_ok=True)

    print(
        f"[recovery] Sweeping {len(durations)} partition durations "
        f"× {replicates} replicates ...",
        flush=True,
    )

    samples = run_recovery_sweep(
        partition_durations=durations,
        replicates=replicates,
        backlog_arrival_per_round=float(bl["arrival_per_round"]),
        backlog_base_offset_tx=float(bl["base_offset_tx"]),
        backlog_jitter_tx=float(bl["jitter_tx"]),
        orphan_slope_pct_per_round=float(om["slope_pct_per_round"]),
        orphan_base_offset_pct=float(om["base_offset_pct"]),
        orphan_jitter_pct=float(om["jitter_pct"]),
    )

    summaries = summarize_recovery(samples)

    raw_csv = os.path.join(output_dir, "recovery_replicates.csv")
    with open(raw_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "partition_duration", "replicate",
            "backlog_peak_tx", "orphan_stale_rate_pct",
        ])
        for s in samples:
            writer.writerow([
                s.partition_duration, s.replicate,
                round(s.backlog_peak_tx, 2),
                round(s.orphan_stale_rate_pct, 4),
            ])

    payload: Dict[str, Any] = {
        "experiment_id": cfg.get("experiment_id", "recovery_overhead"),
        "config": cfg,
        "summaries": [
            {
                "partition_duration": s.partition_duration,
                "backlog_mean_tx": round(s.backlog_mean_tx, 2),
                "backlog_min_tx": round(s.backlog_min_tx, 2),
                "backlog_max_tx": round(s.backlog_max_tx, 2),
                "orphan_mean_pct": round(s.orphan_mean_pct, 4),
                "orphan_min_pct": round(s.orphan_min_pct, 4),
                "orphan_max_pct": round(s.orphan_max_pct, 4),
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
            f"  duration={s.partition_duration:>2} rounds: "
            f"backlog={s.backlog_mean_tx:.0f} tx "
            f"[{s.backlog_min_tx:.0f}-{s.backlog_max_tx:.0f}], "
            f"orphan={s.orphan_mean_pct:.2f}% "
            f"[{s.orphan_min_pct:.2f}-{s.orphan_max_pct:.2f}]",
            flush=True,
        )

    try:
        from .plot_recovery import plot_recovery_overhead
        backlog_mean = [s.backlog_mean_tx for s in summaries]
        backlog_low = [s.backlog_mean_tx - s.backlog_min_tx for s in summaries]
        backlog_high = [s.backlog_max_tx - s.backlog_mean_tx for s in summaries]
        orphan_mean = [s.orphan_mean_pct for s in summaries]
        orphan_low = [s.orphan_mean_pct - s.orphan_min_pct for s in summaries]
        orphan_high = [s.orphan_max_pct - s.orphan_mean_pct for s in summaries]
        fig_path = os.path.join(output_dir, "figure6b.png")
        plot_recovery_overhead(
            durations=[s.partition_duration for s in summaries],
            backlog_mean=backlog_mean,
            backlog_err_low=backlog_low,
            backlog_err_high=backlog_high,
            orphan_mean=orphan_mean,
            orphan_err_low=orphan_low,
            orphan_err_high=orphan_high,
            output_path=fig_path,
        )
        print(f"[recovery] Figure saved: {fig_path}", flush=True)
    except Exception as exc:
        print(f"[recovery] Plot skipped: {exc}", flush=True)

    print(f"[recovery] Done. Outputs in: {output_dir}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Partition recovery overhead runner"
    )
    parser.add_argument("--config", required=True, help="Path to recovery_overhead.yaml")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()

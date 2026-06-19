import argparse
import csv
import json
import os
from typing import Any, Dict, List

import yaml

from povichain.consensus.reputation import ReputationParams
from .sim_core import run_stress_epochs


def _load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_network_profile(name: str, project_root: str) -> Dict[str, Any]:
    profile_path = os.path.join(project_root, "configs", "defaults", name + ".yaml")
    with open(profile_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _mean_delay_ms(profile: Dict[str, Any]) -> float:
    series = profile.get("delay_series_ms", [50])
    return sum(series) / len(series)


def _rolling_stats(values: List[float], window: int):
    means: List[float] = []
    stds: List[float] = []
    for i in range(len(values)):
        lo = max(0, i - window + 1)
        window_vals = values[lo : i + 1]
        m = sum(window_vals) / len(window_vals)
        means.append(m)
        if len(window_vals) > 1:
            var = sum((v - m) ** 2 for v in window_vals) / (len(window_vals) - 1)
            stds.append(var ** 0.5)
        else:
            stds.append(0.0)
    return means, stds


def _write_summary(output_dir: str, payload: Dict[str, Any], results: Dict[str, Any]) -> None:
    cfg = payload["config"]
    tpeak = (
        cfg["tx_per_block"] * cfg["blocks_per_epoch"] / (cfg["epoch_duration_ms"] / 1000.0)
    )
    expected = {0.00: "~2000", 0.05: "~1900", 0.10: "~1800", 0.20: "~1600"}

    lines = [
        "# multi-domain stress simulation",
        "",
        "## Configuration",
        "",
        f"- node_count: {cfg['node_count']}",
        f"- training_epochs: {cfg['training_epochs']}",
        f"- blocks_per_epoch: {cfg['blocks_per_epoch']}",
        f"- tx_per_block: {cfg['tx_per_block']}",
        f"- epoch_duration_ms: {cfg['epoch_duration_ms']:.1f}",
        f"- network_mean_delay_ms: {cfg['network_mean_delay_ms']:.1f}",
        f"- workload_ramp_epochs: {cfg['workload_ramp_epochs']}",
        f"- workload_min_fraction: {cfg['workload_min_fraction']}",
        f"- theta: {cfg['theta']}",
        f"- rolling_window_epochs: {cfg['rolling_window_epochs']}",
        f"- network_jitter_ms: {cfg['network_jitter_ms']}",
        f"- recovery_overhead_per_drop_ms: {cfg['recovery_overhead_per_drop_ms']}",
        f"- recovery_drain_per_epoch_ms: {cfg['recovery_drain_per_epoch_ms']}",
        f"- max_overhead_ms: {cfg['max_overhead_ms']}",
        "",
        "## Theoretical peak throughput",
        "",
        (
            f"- {cfg['tx_per_block']} tx/block × {cfg['blocks_per_epoch']} blocks "
            f"/ {cfg['epoch_duration_ms']/1000.0:.3f}s = {tpeak:.1f} tx/s"
        ),
        "",
        "## Steady-state results (last 100 epochs)",
        "",
        "| Loss rate | Steady-state mean (tx/s) | Std (tx/s) |",
        "|-----------|--------------------------|------------|",
    ]
    for label, info in sorted(results.items(), key=lambda x: x[1]["loss_rate"]):
        lr = info["loss_rate"]
        lines.append(
            f"| {lr:.2f} | {info['steady_state_mean_tps']:.1f} | {info['steady_state_std_tps']:.1f} |"
        )
    lines += [
        "",
        "## Determinism notes",
        "",
        "- Warmup: workload ramp from 10% to 100% injection over 80 epochs.",
        "- Packet loss: deterministic per (epoch, block_idx) via SHA-256 hash.",
        "- Rolling mean/std: causal window of 20 epochs.",
        "- Committee selection: deterministic VRF (same as resilience sim_core).",
    ]

    summary_path = os.path.join(output_dir, "summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run(config_path: str) -> None:
    cfg = _load_config(config_path)

    abs_cfg = os.path.abspath(config_path)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(abs_cfg)))

    network_name = cfg.get("network_profile", "network_fast")
    net_profile = _load_network_profile(network_name, project_root)
    mean_delay = _mean_delay_ms(net_profile)

    rw = cfg.get("reputation_weights", {})
    rep_params = ReputationParams(
        alpha=float(rw.get("alpha", 0.7)),
        beta=float(rw.get("beta", 0.15)),
        gamma=float(rw.get("gamma", 0.10)),
        lambd=float(rw.get("lambda", 0.25)),
        delta=float(rw.get("delta", 0.25)),
        eta=float(rw.get("eta", 0.02)),
        mu=float(rw.get("mu", 0.15)),
        r_min=float(rw.get("r_min", 0.05)),
    )

    node_count = int(cfg.get("node_count", 100))
    training_epochs = int(cfg.get("training_epochs", 500))
    blocks_per_epoch = int(cfg.get("blocks_per_epoch", 4))
    tx_per_block = int(cfg.get("tx_per_block", 200))
    ramp_epochs = int(cfg.get("workload_ramp_epochs", 80))
    min_frac = float(cfg.get("workload_min_fraction", 0.10))
    theta = float(cfg.get("committee_threshold_theta", 20.0))
    loss_levels = list(cfg.get("loss_levels", [0.00, 0.05, 0.10, 0.20]))
    rolling_window = int(cfg.get("rolling_window_epochs", 20))

    network_jitter_ms = float(cfg.get("network_jitter_ms", 0.0))
    recovery_overhead_per_drop_ms = float(cfg.get("recovery_overhead_per_drop_ms", 0.0))
    recovery_drain_per_epoch_ms = float(cfg.get("recovery_drain_per_epoch_ms", 0.0))
    max_overhead_ms = float(cfg.get("max_overhead_ms", 0.0))

    output_cfg = cfg.get("output", {})
    output_dir = output_cfg.get("output_dir", "outputs/stress_epochs")
    os.makedirs(output_dir, exist_ok=True)

    epoch_duration_ms = 2.0 * mean_delay * blocks_per_epoch

    results_by_loss: Dict[str, Any] = {}
    csv_paths: Dict[float, str] = {}

    for loss_rate in loss_levels:
        label = "loss_" + f"{loss_rate:.2f}".replace(".", "_")
        print(f"[performance] Running loss_rate={loss_rate:.2f} ...", flush=True)

        records = run_stress_epochs(
            node_count=node_count,
            training_epochs=training_epochs,
            blocks_per_epoch=blocks_per_epoch,
            tx_per_block=tx_per_block,
            workload_ramp_epochs=ramp_epochs,
            workload_min_fraction=min_frac,
            epoch_duration_ms=epoch_duration_ms,
            loss_rate=loss_rate,
            theta=theta,
            rep_params=rep_params,
            network_jitter_ms=network_jitter_ms,
            recovery_overhead_per_drop_ms=recovery_overhead_per_drop_ms,
            recovery_drain_per_epoch_ms=recovery_drain_per_epoch_ms,
            max_overhead_ms=max_overhead_ms,
        )

        tps_values = [r.throughput_tps for r in records]
        rolling_means, rolling_stds = _rolling_stats(tps_values, rolling_window)

        csv_path = os.path.join(output_dir, label + ".csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "epoch", "inject_tx", "committed_tx", "dropped_blocks",
                "throughput_tps", "rolling_mean_tps", "rolling_std_tps",
                "effective_epoch_ms", "overhead_pool_ms",
                "mean_effective_rep", "committee_size_mean",
            ])
            for i, r in enumerate(records):
                writer.writerow([
                    r.epoch, r.inject_tx, r.committed_tx, r.dropped_blocks,
                    round(r.throughput_tps, 4), round(rolling_means[i], 4),
                    round(rolling_stds[i], 4),
                    round(r.effective_epoch_ms, 3), round(r.overhead_pool_ms, 3),
                    round(r.mean_effective_rep, 6),
                    round(r.committee_size_mean, 2),
                ])

        csv_paths[loss_rate] = csv_path

        steady = tps_values[-100:]
        steady_mean = sum(steady) / len(steady)
        steady_std = (
            sum((v - steady_mean) ** 2 for v in steady) / max(1, len(steady) - 1)
        ) ** 0.5

        results_by_loss[label] = {
            "loss_rate": loss_rate,
            "steady_state_mean_tps": round(steady_mean, 2),
            "steady_state_std_tps": round(steady_std, 2),
            "peak_tps": round(max(tps_values), 2),
            "epoch_count": len(records),
            "csv_path": csv_path,
        }

        print(
            f"  steady-state tps: {steady_mean:.1f} +/- {steady_std:.1f} tx/s",
            flush=True,
        )

    payload: Dict[str, Any] = {
        "experiment_id": cfg.get("experiment_id", "stress_epochs"),
        "config": {
            "node_count": node_count,
            "training_epochs": training_epochs,
            "blocks_per_epoch": blocks_per_epoch,
            "tx_per_block": tx_per_block,
            "epoch_duration_ms": epoch_duration_ms,
            "network_mean_delay_ms": mean_delay,
            "workload_ramp_epochs": ramp_epochs,
            "workload_min_fraction": min_frac,
            "theta": theta,
            "rolling_window_epochs": rolling_window,
            "network_jitter_ms": network_jitter_ms,
            "recovery_overhead_per_drop_ms": recovery_overhead_per_drop_ms,
            "recovery_drain_per_epoch_ms": recovery_drain_per_epoch_ms,
            "max_overhead_ms": max_overhead_ms,
        },
        "results": results_by_loss,
    }

    json_path = os.path.join(output_dir, "aggregated.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    _write_summary(output_dir, payload, results_by_loss)

    try:
        from .plot_throughput import plot_throughput_sweep

        data_for_plot: Dict[float, Any] = {}
        for loss_rate in loss_levels:
            label = "loss_" + f"{loss_rate:.2f}".replace(".", "_")
            info = results_by_loss[label]
            epochs_list, tps_list, rmean_list, rstd_list = [], [], [], []
            with open(info["csv_path"], "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    epochs_list.append(int(row["epoch"]))
                    tps_list.append(float(row["throughput_tps"]))
                    rmean_list.append(float(row["rolling_mean_tps"]))
                    rstd_list.append(float(row["rolling_std_tps"]))
            data_for_plot[loss_rate] = {
                "epochs": epochs_list,
                "tps": tps_list,
                "rolling_mean": rmean_list,
                "rolling_std": rstd_list,
            }

        fig_path = os.path.join(output_dir, "figure6.png")
        plot_throughput_sweep(data_for_plot, fig_path)
        print(f"[performance] Figure saved: {fig_path}", flush=True)
    except Exception as exc:
        print(f"[performance] Plot skipped: {exc}", flush=True)

    print(f"[performance] Done. Outputs in: {output_dir}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="epoch-based stress simulation runner")
    parser.add_argument("--config", required=True, help="Path to stress_epochs.yaml")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()

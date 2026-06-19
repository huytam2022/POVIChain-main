import csv
import os
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _read_csv(path: str) -> Tuple[List[str], List[Dict[str, float]]]:
    rows: List[Dict[str, float]] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        headers = list(reader.fieldnames or [])
        for row in reader:
            rows.append({k: float(v) for k, v in row.items()})
    return headers, rows


def plot_sybil_multirun(csv_path: str, png_path: str, title: str) -> None:
    """
    Plots Sybil collusion multi-run aggregation.

    Expected CSV columns:
      malicious_fraction_percent,
      invalid_accept_ratio_percent_mean, invalid_accept_ratio_percent_std,
      block_loss_percent_mean, block_loss_percent_std,
      trust_ratio_malicious_over_honest_mean, trust_ratio_malicious_over_honest_std,
      penalty_delay_rounds_mean, penalty_delay_rounds_std

    Each metric is plotted with mean +/- std error bars.
    """
    _, rows = _read_csv(csv_path)
    if not rows:
        return
    xs = [r["malicious_fraction_percent"] for r in rows]
    iar_mean = [r["invalid_accept_ratio_percent_mean"] for r in rows]
    iar_std = [r["invalid_accept_ratio_percent_std"] for r in rows]
    bl_mean = [r["block_loss_percent_mean"] for r in rows]
    bl_std = [r["block_loss_percent_std"] for r in rows]
    tr_mean = [r["trust_ratio_malicious_over_honest_mean"] for r in rows]
    tr_std = [r["trust_ratio_malicious_over_honest_std"] for r in rows]
    pd_mean = [r["penalty_delay_rounds_mean"] for r in rows]
    pd_std = [r["penalty_delay_rounds_std"] for r in rows]

    fig, ax_left = plt.subplots(figsize=(8.5, 5.5))
    ax_right = ax_left.twinx()
    ax_left.errorbar(
        xs, iar_mean, yerr=iar_std, marker="o", color="#c0392b",
        label="invalid_accept_ratio %", capsize=3, linewidth=1.5,
    )
    ax_left.errorbar(
        xs, bl_mean, yerr=bl_std, marker="s", color="#e67e22",
        label="block_loss %", capsize=3, linewidth=1.5,
    )
    ax_left.errorbar(
        xs, tr_mean, yerr=tr_std, marker="^", color="#2980b9",
        label="trust_ratio (mal/honest)", capsize=3, linewidth=1.5,
    )
    ax_right.errorbar(
        xs, pd_mean, yerr=pd_std, marker="D", color="#27ae60",
        label="penalty_delay (rounds)", capsize=3, linewidth=1.5,
    )
    ax_left.set_xlabel("Malicious fraction (%)")
    ax_left.set_ylabel("Percent / ratio")
    ax_right.set_ylabel("Penalty delay (rounds)")
    ax_left.set_title(title)
    ax_left.grid(True, alpha=0.3)
    h1, l1 = ax_left.get_legend_handles_labels()
    h2, l2 = ax_right.get_legend_handles_labels()
    ax_left.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9)
    fig.tight_layout()
    os.makedirs(os.path.dirname(png_path) or ".", exist_ok=True)
    fig.savefig(png_path, dpi=140)
    plt.close(fig)


def plot_partitions_multirun(csv_path: str, png_path: str, title: str) -> None:
    """
    Plots Network partition multi-run aggregation.

    Expected CSV columns:
      partition_duration_rounds,
      fork_resolution_accuracy_percent_mean, fork_resolution_accuracy_percent_std,
      conflict_ratio_percent_mean, conflict_ratio_percent_std,
      recovery_time_rounds_mean, recovery_time_rounds_std

    Each metric is plotted with mean +/- std error bars.
    """
    _, rows = _read_csv(csv_path)
    if not rows:
        return
    xs = [r["partition_duration_rounds"] for r in rows]
    fa_mean = [r["fork_resolution_accuracy_percent_mean"] for r in rows]
    fa_std = [r["fork_resolution_accuracy_percent_std"] for r in rows]
    cr_mean = [r["conflict_ratio_percent_mean"] for r in rows]
    cr_std = [r["conflict_ratio_percent_std"] for r in rows]
    rt_mean = [r["recovery_time_rounds_mean"] for r in rows]
    rt_std = [r["recovery_time_rounds_std"] for r in rows]

    fig, ax_left = plt.subplots(figsize=(8.5, 5.5))
    ax_right = ax_left.twinx()
    ax_left.errorbar(
        xs, fa_mean, yerr=fa_std, marker="o", color="#27ae60",
        label="fork_resolution_accuracy %", capsize=3, linewidth=1.5,
    )
    ax_left.errorbar(
        xs, cr_mean, yerr=cr_std, marker="s", color="#c0392b",
        label="conflict_ratio %", capsize=3, linewidth=1.5,
    )
    ax_right.errorbar(
        xs, rt_mean, yerr=rt_std, marker="D", color="#2980b9",
        label="recovery_time (rounds)", capsize=3, linewidth=1.5,
    )
    ax_left.set_xlabel("Partition duration (rounds)")
    ax_left.set_ylabel("Percent")
    ax_right.set_ylabel("Recovery time (rounds)")
    ax_left.set_title(title)
    ax_left.grid(True, alpha=0.3)
    h1, l1 = ax_left.get_legend_handles_labels()
    h2, l2 = ax_right.get_legend_handles_labels()
    ax_left.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9)
    fig.tight_layout()
    os.makedirs(os.path.dirname(png_path) or ".", exist_ok=True)
    fig.savefig(png_path, dpi=140)
    plt.close(fig)

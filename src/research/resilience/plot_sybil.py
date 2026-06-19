import csv
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_sybil_collusion(csv_path: str, png_path: str, title: str) -> None:
    xs: List[float] = []
    invalid_accept: List[float] = []
    block_loss: List[float] = []
    trust_ratio: List[float] = []
    penalty_delay: List[float] = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            xs.append(float(row["malicious_fraction_percent"]))
            invalid_accept.append(float(row["invalid_accept_ratio_percent"]))
            block_loss.append(float(row["block_loss_percent"]))
            trust_ratio.append(float(row["trust_ratio_malicious_over_honest"]))
            penalty_delay.append(float(row["penalty_delay_rounds"]))
    fig, ax1 = plt.subplots(figsize=(8.0, 5.2))
    ax1.set_xlabel("Malicious fraction (%)")
    ax1.set_ylabel("Percentage (%) / Ratio")
    l1, = ax1.plot(xs, invalid_accept, marker="o", color="#d62728", label="Invalid-accept ratio (%)")
    l2, = ax1.plot(xs, block_loss, marker="s", color="#ff7f0e", label="Block loss (%)")
    l3, = ax1.plot(xs, trust_ratio, marker="^", color="#1f77b4", label="Trust ratio (malicious/honest)")
    ax2 = ax1.twinx()
    ax2.set_ylabel("Penalty delay (rounds)")
    l4, = ax2.plot(xs, penalty_delay, marker="D", color="#2ca02c", linestyle="--", label="Penalty delay (rounds)")
    lines = [l1, l2, l3, l4]
    labels = [ln.get_label() for ln in lines]
    ax1.legend(lines, labels, loc="upper left", fontsize=9)
    ax1.set_title(title)
    ax1.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(png_path, dpi=150)
    plt.close(fig)


def plot_partitions(csv_path: str, png_path: str, title: str) -> None:
    xs: List[float] = []
    fork_acc: List[float] = []
    conflict_ratio: List[float] = []
    recovery_time: List[float] = []
    with open(csv_path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            xs.append(float(row["partition_duration_rounds"]))
            fork_acc.append(float(row["fork_resolution_accuracy_percent"]))
            conflict_ratio.append(float(row["conflict_ratio_percent"]))
            recovery_time.append(float(row["recovery_time_rounds"]))
    fig, ax1 = plt.subplots(figsize=(8.0, 5.2))
    ax1.set_xlabel("Partition duration (rounds)")
    ax1.set_ylabel("Percentage (%)")
    l1, = ax1.plot(xs, fork_acc, marker="o", color="#1f77b4", label="Fork resolution accuracy (%)")
    l2, = ax1.plot(xs, conflict_ratio, marker="s", color="#d62728", label="Conflict ratio (%)")
    ax2 = ax1.twinx()
    ax2.set_ylabel("Recovery time (rounds)")
    l3, = ax2.plot(xs, recovery_time, marker="D", color="#2ca02c", linestyle="--", label="Recovery time (rounds)")
    lines = [l1, l2, l3]
    labels = [ln.get_label() for ln in lines]
    ax1.legend(lines, labels, loc="center right", fontsize=9)
    ax1.set_title(title)
    ax1.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(png_path, dpi=150)
    plt.close(fig)

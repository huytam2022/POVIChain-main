from typing import List


def plot_recovery_overhead(
    durations: List[int],
    backlog_mean: List[float],
    backlog_err_low: List[float],
    backlog_err_high: List[float],
    orphan_mean: List[float],
    orphan_err_low: List[float],
    orphan_err_high: List[float],
    output_path: str,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax_left = plt.subplots(figsize=(9, 5.5))
    ax_right = ax_left.twinx()

    backlog_color = "#c0392b"
    orphan_color = "#2980b9"

    line_b, = ax_left.plot(
        durations, backlog_mean,
        color=backlog_color, marker="o", linewidth=1.6, markersize=6,
        label="Backlog peak (left y-axis)",
    )
    ax_left.errorbar(
        durations, backlog_mean,
        yerr=[backlog_err_low, backlog_err_high],
        fmt="none", ecolor=backlog_color, elinewidth=1.0, capsize=4,
    )

    line_o, = ax_right.plot(
        durations, orphan_mean,
        color=orphan_color, marker="s", linewidth=1.6, markersize=6,
        linestyle="--", label="Orphan block rate (right y-axis)",
    )
    ax_right.errorbar(
        durations, orphan_mean,
        yerr=[orphan_err_low, orphan_err_high],
        fmt="none", ecolor=orphan_color, elinewidth=1.0, capsize=4,
    )

    ax_left.set_xlabel("Partition duration (rounds)")
    ax_left.set_ylabel("Backlog peak (transactions)", color=backlog_color)
    ax_right.set_ylabel("Orphan block rate (%)", color=orphan_color)

    ax_left.set_xticks(durations)
    ax_left.set_ylim(0, max(backlog_mean) * 1.25 + 200)
    ax_right.set_ylim(0, max(orphan_mean) * 1.4 + 1.0)
    ax_left.grid(True, alpha=0.3)

    ax_left.annotate(
        "Re-convergence induces\ntransient queue buildup",
        xy=(durations[1], backlog_mean[1]),
        xytext=(durations[1] - 3, backlog_mean[1] + 1200),
        arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
        fontsize=9,
    )
    ax_left.annotate(
        "Longer partitions amplify\nreconciliation overhead",
        xy=(durations[-1], backlog_mean[-1]),
        xytext=(durations[-1] - 6, backlog_mean[-1] + 600),
        arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
        fontsize=9,
    )

    handles = [line_b, line_o]
    labels = [h.get_label() for h in handles]
    ax_left.legend(handles, labels, loc="upper left", fontsize=9)

    ax_left.set_title(
        "Recovery overhead after partitions: backlog peak (tx) "
        "and orphan/stale block rate (%) vs partition duration",
        fontsize=10,
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

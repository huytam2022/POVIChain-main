from typing import List


def plot_centralization(
    cum_pop_pct_without: List[float],
    cum_share_without: List[float],
    top10_without: float,
    cum_pop_pct_with: List[float],
    cum_share_with: List[float],
    top10_with: float,
    reduction_pct_top10: float,
    output_path: str,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax_left, ax_right) = plt.subplots(1, 2, figsize=(13, 5.4), sharey=True)

    cum_share_pct_without = [v * 100.0 for v in cum_share_without]
    ax_left.plot(
        cum_pop_pct_without, cum_share_pct_without,
        color="#2c4a8c", linewidth=2.0,
    )
    ax_left.fill_between(
        cum_pop_pct_without, cum_share_pct_without, alpha=0.18, color="#2c4a8c",
    )
    ax_left.plot([0, 100], [0, 100], color="#888888", linestyle="--",
                 linewidth=0.9, label="Perfect equality")
    ax_left.axvline(10, color="#c0392b", linestyle=":", linewidth=1.0)
    ax_left.text(
        12, top10_without - 5, f"Top-10 share: {top10_without:.0f}%+",
        fontsize=10, color="#c0392b",
        bbox=dict(facecolor="#fdf2f0", edgecolor="#c0392b",
                  boxstyle="round,pad=0.3"),
    )
    ax_left.set_title("Without Anti-Concentration", fontsize=11, fontweight="bold")
    ax_left.set_xlabel("Prover population (cumulative %, top → bottom)")
    ax_left.set_ylabel("Reputation (cumulative %)")
    ax_left.set_xlim(0, 100)
    ax_left.set_ylim(0, 100)
    ax_left.grid(True, alpha=0.3)
    ax_left.legend(loc="lower right", fontsize=8)

    cum_share_pct_with = [v * 100.0 for v in cum_share_with]
    ax_right.plot(
        cum_pop_pct_with, cum_share_pct_with,
        color="#2ca02c", linewidth=2.0,
    )
    ax_right.fill_between(
        cum_pop_pct_with, cum_share_pct_with, alpha=0.18, color="#2ca02c",
    )
    ax_right.plot([0, 100], [0, 100], color="#888888", linestyle="--",
                  linewidth=0.9, label="Perfect equality")
    ax_right.axvline(10, color="#1e6e1e", linestyle=":", linewidth=1.0)
    ax_right.text(
        12, top10_with - 5, f"Top-10 share: {top10_with:.0f}%",
        fontsize=10, color="#1e6e1e",
        bbox=dict(facecolor="#eef7ee", edgecolor="#1e6e1e",
                  boxstyle="round,pad=0.3"),
    )
    ax_right.set_title("With Anti-Concentration\n(rotation cap + decay + HW-aware reward)",
                       fontsize=11, fontweight="bold")
    ax_right.set_xlabel("Prover population (cumulative %, top → bottom)")
    ax_right.set_xlim(0, 100)
    ax_right.set_ylim(0, 100)
    ax_right.grid(True, alpha=0.3)
    ax_right.legend(loc="lower right", fontsize=8)

    fig.suptitle(
        "Impact of rotation, decay and cooldown on prover reputation concentration "
        f"(top-10 share reduction: {reduction_pct_top10:.0f} pp)",
        fontsize=11, y=1.02,
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

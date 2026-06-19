from typing import List


def plot_hardware_costs(
    times_ms: List[float],
    ram_kb: List[float],
    ram_limit_kb: float,
    peak_annotations: List[dict],
    protocols: List[str],
    energy_mj: List[float],
    output_path: str,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.0))

    ax_a = axes[0]
    ax_a.plot(times_ms, ram_kb, color="steelblue", linewidth=1.6)
    ax_a.axhline(
        ram_limit_kb, color="crimson", linestyle="--", linewidth=1.2,
        label=f"ESP32 RAM Limit",
    )
    ax_a.text(
        max(times_ms) * 0.78, ram_limit_kb + 8, "ESP32 RAM Limit",
        color="crimson", fontsize=9,
    )
    for pk in peak_annotations:
        ax_a.annotate(
            pk["label"],
            xy=(pk["center_ms"], pk["peak_kb"]),
            xytext=(pk["center_ms"] - 25, pk["peak_kb"] + 30),
            arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
            fontsize=9,
        )
    ax_a.annotate(
        "Idle",
        xy=(450, 105),
        xytext=(440, 145),
        arrowprops=dict(arrowstyle="->", color="black", lw=0.8),
        fontsize=9,
    )
    ax_a.set_xlabel("Time (ms)")
    ax_a.set_ylabel("RAM Usage (KB)")
    ax_a.set_xlim(0, max(times_ms))
    ax_a.set_ylim(0, max(ram_limit_kb + 30, max(ram_kb) + 30))
    ax_a.grid(True, alpha=0.3)
    ax_a.set_title(
        "(a) ESP32 RAM usage during a verification cycle, "
        "with the device RAM limit indicated by the dashed line.",
        fontsize=9,
    )

    ax_b = axes[1]
    bar_colors = ["#e29846", "#9168a7", "#7fb98a"]
    while len(bar_colors) < len(protocols):
        bar_colors.append("#888888")
    bars = ax_b.bar(protocols, energy_mj, color=bar_colors[: len(protocols)],
                     edgecolor="#333333", linewidth=0.6, width=0.6)
    for bar, val in zip(bars, energy_mj):
        ax_b.annotate(
            f"{val:.1f}",
            xy=(bar.get_x() + bar.get_width() / 2, val),
            xytext=(0, 4), textcoords="offset points",
            ha="center", va="bottom", fontsize=10,
        )
    ax_b.set_ylabel("Energy per Tx (mJ)")
    y_top = max(energy_mj) * 1.25 if energy_mj else 10.0
    ax_b.set_ylim(0, max(10.0, y_top))
    ax_b.grid(True, axis="y", alpha=0.3)
    ax_b.set_title(
        "(b) Energy per transaction (normalized), "
        "comparing PoVIChain against Cosmos IBC and LayerZero.",
        fontsize=9,
    )

    fig.suptitle(
        "End-device hardware costs: "
        "bounded verification footprint on ESP32 and energy-per-transaction comparison",
        fontsize=10, y=1.03,
    )
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

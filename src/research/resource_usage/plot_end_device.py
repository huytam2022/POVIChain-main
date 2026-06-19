from typing import List


def plot_end_device_energy(
    mcu_label: str,
    mcu_median_ms: float,
    mcu_err_low_ms: float,
    mcu_err_high_ms: float,
    rpi_labels: List[str],
    rpi_median_s: List[float],
    rpi_err_low_s: List[float],
    rpi_err_high_s: List[float],
    output_path: str,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(11, 5.0))

    bar_a = ax_a.bar(
        [mcu_label], [mcu_median_ms],
        yerr=[[mcu_err_low_ms], [mcu_err_high_ms]],
        color="#2c3e80", edgecolor="#1a1f3d", linewidth=0.6,
        width=0.55, capsize=8, error_kw={"elinewidth": 1.4},
    )
    for rect, val in zip(bar_a, [mcu_median_ms]):
        ax_a.annotate(
            f"{val:.0f} ms",
            xy=(rect.get_x() + rect.get_width() / 2, val),
            xytext=(0, 6), textcoords="offset points",
            ha="center", va="bottom", fontsize=10,
        )
    ax_a.set_ylabel("Time (ms)")
    ax_a.set_title("Verification Time (MCU-Grade)", fontsize=11, fontweight="bold")
    ax_a.set_ylim(0, max(mcu_median_ms + mcu_err_high_ms, 220))
    ax_a.grid(True, axis="y", alpha=0.3)

    rpi_colors = ["#2ca02c", "#9b3a3a"]
    while len(rpi_colors) < len(rpi_labels):
        rpi_colors.append("#888888")
    bars_b = ax_b.bar(
        rpi_labels, rpi_median_s,
        yerr=[rpi_err_low_s, rpi_err_high_s],
        color=rpi_colors[: len(rpi_labels)], edgecolor="#444",
        linewidth=0.6, width=0.55, capsize=8,
        error_kw={"elinewidth": 1.4},
    )
    for rect, val in zip(bars_b, rpi_median_s):
        ax_b.annotate(
            f"{val:.0f} s",
            xy=(rect.get_x() + rect.get_width() / 2, val),
            xytext=(0, 6), textcoords="offset points",
            ha="center", va="bottom", fontsize=10,
        )
    ax_b.set_ylabel("Time (s)")
    ax_b.set_title("Proving Time (Raspberry Pi-Grade)", fontsize=11, fontweight="bold")
    ax_b.set_ylim(0, max([m + e for m, e in zip(rpi_median_s, rpi_err_high_s)]) * 1.15)
    ax_b.grid(True, axis="y", alpha=0.3)

    fig.suptitle(
        "ZKP proving costs by hardware (Raspberry Pi 4 vs MCUs)",
        fontsize=11, y=1.02,
    )
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

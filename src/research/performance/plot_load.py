from typing import Dict, List


def plot_multidomain_load(
    load_levels: List[float],
    per_domain_tps: Dict[str, List[float]],
    dispatcher_efficiency: List[float],
    output_path: str,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax_left = plt.subplots(figsize=(9, 5.5))
    ax_right = ax_left.twinx()

    domain_styles = {
        "traffic":     {"color": "#c0392b", "marker": "o", "label": "Traffic-dominated"},
        "energy":      {"color": "#2980b9", "marker": "s", "label": "Energy-dominated"},
        "environment": {"color": "#27ae60", "marker": "^", "label": "Environment-dominated"},
    }

    left_handles = []
    for name, series in per_domain_tps.items():
        style = domain_styles.get(name, {"color": "#555555", "marker": "x", "label": name})
        line, = ax_left.plot(
            load_levels, series,
            color=style["color"], marker=style["marker"],
            linewidth=1.6, markersize=5,
            label=style["label"],
        )
        left_handles.append(line)

    right_line, = ax_right.plot(
        load_levels, dispatcher_efficiency,
        color="#7d3c98", marker="D", linewidth=1.4, markersize=5,
        linestyle="--", label="Dispatcher efficiency",
    )

    ax_left.set_xlabel("Load index (× nominal arrival rate)")
    ax_left.set_ylabel("Per-domain committed throughput (tx/s)")
    ax_right.set_ylabel("Smart-Zone dispatcher efficiency", color="#7d3c98")

    ax_left.set_xlim(min(load_levels), max(load_levels))
    ax_left.set_ylim(0, max(3000, max(max(s) for s in per_domain_tps.values()) + 200))
    ax_right.set_ylim(0.70, 1.00)

    ax_left.grid(True, alpha=0.3)
    ax_left.axhline(2200, color="#888888", linestyle=":", linewidth=0.8)
    ax_left.text(
        max(load_levels) - 0.4, 2230, "2200 tx/s reference",
        fontsize=8, color="#666666",
    )

    handles = left_handles + [right_line]
    labels = [h.get_label() for h in handles]
    ax_left.legend(handles, labels, loc="lower left", fontsize=9)

    ax_left.set_title(
        "Per-domain throughput and Smart-Zone dispatcher efficiency vs load",
        fontsize=10,
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

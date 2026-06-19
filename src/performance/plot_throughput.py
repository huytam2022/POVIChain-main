from typing import Any, Dict, List


def plot_throughput_sweep(data: Dict[float, Dict[str, Any]], output_path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    loss_levels = [0.00, 0.05, 0.10, 0.20]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), sharex=True)
    axes_flat = [axes[0][0], axes[0][1], axes[1][0], axes[1][1]]

    for ax, loss_rate in zip(axes_flat, loss_levels):
        if loss_rate not in data:
            ax.text(0.5, 0.5, f"No data for loss={loss_rate:.2f}", ha="center", va="center",
                    transform=ax.transAxes)
            continue

        d = data[loss_rate]
        epochs = [e + 1 for e in d["epochs"]]
        tps = d["tps"]
        rmean = d["rolling_mean"]
        rstd = d["rolling_std"]

        upper = [m + s for m, s in zip(rmean, rstd)]
        lower = [max(0.0, m - s) for m, s in zip(rmean, rstd)]

        ax.fill_between(epochs, lower, upper, alpha=0.22, color="steelblue", label="±1 std")
        ax.plot(epochs, tps, color="lightsteelblue", linewidth=0.4, alpha=0.6, label="raw")
        ax.plot(epochs, rmean, color="steelblue", linewidth=1.8, label="rolling mean")

        peak = max(rmean[-200:]) if len(rmean) >= 200 else max(rmean)
        ax.axhline(peak, color="steelblue", linewidth=0.7, linestyle="--", alpha=0.5)

        ax.set_title(f"Packet loss = {loss_rate:.0%}", fontsize=11, fontweight="bold")
        ax.set_ylabel("Committed Throughput (tx/s)")
        ax.set_xlim(1, max(epochs))
        ax.set_ylim(bottom=0, top=2400)
        ax.legend(fontsize=8, loc="lower right")
        ax.grid(True, alpha=0.25)

    for ax in axes_flat[2:]:
        ax.set_xlabel("Training Epoch")

    fig.suptitle(
        "Multi-Domain Stress: Committed Throughput vs Epoch",
        fontsize=12, y=1.01,
    )
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

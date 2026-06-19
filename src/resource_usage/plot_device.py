from typing import List


def plot_device_profile(
    epochs: List[int],
    cpu_pct: List[float],
    memory_mb: List[float],
    groth16_s: List[float],
    stark_s: List[float],
    output_path: str,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5))

    ax_a = axes[0]
    ax_a2 = ax_a.twinx()

    cpu_color = "#1f3b73"
    mem_color = "#3aa6a0"

    line_cpu, = ax_a.plot(
        epochs, cpu_pct, marker="o", color=cpu_color, linewidth=1.6,
        label="CPU utilization (%)",
    )
    line_mem, = ax_a2.plot(
        epochs, memory_mb, marker="o", color=mem_color, linewidth=1.6,
        label="Memory usage (MB)",
    )

    for x, y in zip(epochs, cpu_pct):
        ax_a.annotate(f"{int(round(y))}", (x, y), textcoords="offset points",
                      xytext=(0, -14), ha="center", fontsize=8, color=cpu_color)
    for x, y in zip(epochs, memory_mb):
        ax_a2.annotate(f"{int(round(y))}", (x, y), textcoords="offset points",
                       xytext=(0, 8), ha="center", fontsize=8, color=mem_color)

    ax_a.set_xlabel("Training epoch (fixed dataset size and batch configuration)")
    ax_a.set_ylabel("CPU utilization (% of total available cores)", color=cpu_color)
    ax_a2.set_ylabel("Memory usage (MB, resident set size)", color=mem_color)
    ax_a.set_title("(a) Gateway resource profile on Raspberry Pi 4", fontsize=10)
    ax_a.set_xticks(epochs)
    ax_a.set_ylim(30, 60)
    ax_a2.set_ylim(180, 270)
    ax_a.grid(True, alpha=0.3)

    handles = [line_cpu, line_mem]
    labels = [h.get_label() for h in handles]
    ax_a.legend(handles, labels, loc="upper left", fontsize=9)

    ax_b = axes[1]
    g16_color = "#1f3b73"
    stk_color = "#3aa6a0"

    ax_b.plot(epochs, groth16_s, marker="o", color=g16_color, linewidth=1.6,
              label="Groth16 — Prover (s)")
    ax_b.plot(epochs, stark_s, marker="o", color=stk_color, linewidth=1.6,
              label="STARKs — Prover (s)")

    for x, y in zip(epochs, groth16_s):
        ax_b.annotate(f"{y:g}", (x, y), textcoords="offset points",
                      xytext=(0, -14), ha="center", fontsize=8, color=g16_color)
    for x, y in zip(epochs, stark_s):
        ax_b.annotate(f"{y:g}", (x, y), textcoords="offset points",
                      xytext=(0, 8), ha="center", fontsize=8, color=stk_color)

    ax_b.set_xlabel("Training epoch (fixed circuit structure and input size)")
    ax_b.set_ylabel("Prover execution time per epoch (seconds)")
    ax_b.set_title("(b) Gateway prover execution time per epoch — Groth16 vs STARKs", fontsize=10)
    ax_b.set_xticks(epochs)
    ax_b.set_ylim(0, 65)
    ax_b.grid(True, alpha=0.3)
    ax_b.legend(loc="center right", fontsize=9)

    fig.suptitle(
        "Resource and cryptographic cost profiling on gateway-class hardware",
        fontsize=11, y=1.02,
    )
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

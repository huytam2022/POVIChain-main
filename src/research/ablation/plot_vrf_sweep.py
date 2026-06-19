from typing import Dict, List


def plot_vrf_sweep(
    kappas: List[int],
    p_mal_by_p: Dict[float, List[float]],
    floor: float,
    safe_kappa: int,
    validator_count: int,
    output_path: str,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 6.2))

    palette = {
        0.10: "#2980b9",
        0.20: "#27ae60",
        0.25: "#e67e22",
        0.33: "#c0392b",
    }

    floor_clip = max(floor, 1.0e-300)
    for p_val, p_mal_series in sorted(p_mal_by_p.items()):
        color = palette.get(round(p_val, 4), "#555555")
        clipped = [max(v, 1.0e-300) for v in p_mal_series]
        ax.semilogy(
            kappas, clipped,
            color=color, linewidth=1.6, marker=".", markersize=3,
            label=f"p (adversarial fraction) = {p_val:.2f}",
        )

    ax.axhline(
        floor, color="#555555", linestyle="--", linewidth=1.0,
        label=f"experimental resolution {floor:g}",
    )
    ax.axvline(
        safe_kappa, color="#7d3c98", linestyle=":", linewidth=1.2,
        label=f"reference kappa marker = {safe_kappa}",
    )

    ax.set_xlabel("Committee size κ (kappa)")
    ax.set_ylabel("Prob. malicious majority  P_mal  (binomial tail)")
    ax.set_title(
        f"VRF threshold sensitivity: P_mal vs committee size κ "
        f"(|V| = {validator_count})",
        fontsize=11,
    )
    ax.set_xlim(min(kappas), max(kappas))
    ax.set_ylim(floor_clip / 1e6, 1.0)
    ax.grid(True, which="both", alpha=0.3)
    ax.legend(loc="lower left", fontsize=9)

    sec = ax.secondary_xaxis(
        "top",
        functions=(lambda k: k / validator_count, lambda t: t * validator_count),
    )
    sec.set_xlabel(f"VRF threshold θ = κ / |V|  (|V| = {validator_count})")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

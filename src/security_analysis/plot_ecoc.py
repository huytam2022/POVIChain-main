from typing import List


def plot_ecoc_sensitivity(
    rho_grid: List[float],
    lambda_grid: List[float],
    Z: List[List[float]],
    rho_lambda_threshold: float,
    ecoc_pos: float,
    output_path: str,
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib import cm
    from mpl_toolkits.mplot3d import Axes3D  # noqa: F401  (registers 3D projection)

    fig = plt.figure(figsize=(9, 6.5))
    ax = fig.add_subplot(111, projection="3d")

    R = rho_grid
    L = lambda_grid
    X = np.array([[R[i] for _ in L] for i in range(len(R))], dtype=float)
    Y = np.array([[L[j] for j in range(len(L))] for _ in R], dtype=float)
    Z = np.array(Z, dtype=float)

    surf = ax.plot_surface(
        X, Y, Z,
        cmap=cm.coolwarm, edgecolor="none",
        antialiased=True, alpha=0.92,
    )

    z_max = float(Z.max())
    if ecoc_pos < z_max * 1.05:
        floor_z = np.full_like(Z, ecoc_pos)
        ax.plot_surface(
            X, Y, floor_z,
            color="#888888", alpha=0.18, edgecolor="none",
        )

    boundary_pts_rho = []
    boundary_pts_lambda = []
    boundary_pts_z = []
    for i, rho in enumerate(R):
        if rho <= 0.0:
            continue
        lam = rho_lambda_threshold / rho
        if lam < L[0] or lam > L[-1]:
            continue
        boundary_pts_rho.append(rho)
        boundary_pts_lambda.append(lam)
        j_lo = 0
        while j_lo < len(L) - 1 and L[j_lo + 1] < lam:
            j_lo += 1
        j_hi = min(len(L) - 1, j_lo + 1)
        if L[j_hi] == L[j_lo]:
            z_val = float(Z[i, j_lo])
        else:
            t = (lam - L[j_lo]) / (L[j_hi] - L[j_lo])
            z_val = float(Z[i, j_lo]) * (1 - t) + float(Z[i, j_hi]) * t
        boundary_pts_z.append(z_val)

    if boundary_pts_rho:
        ax.plot(
            boundary_pts_rho, boundary_pts_lambda, boundary_pts_z,
            color="#222222", linewidth=2.0, linestyle="--",
            label=f"rho × lambda = {rho_lambda_threshold} (deterrence boundary)",
        )

    ax.set_xlabel("Detection probability (rho)")
    ax.set_ylabel("Penalty weight (lambda)")
    ax.set_zlabel("ECoC_PoVI (TVS)")
    ax.set_title(
        "Sensitivity of ECoC_PoVI to (rho, lambda) at eta=0.05, delta=0.25",
        fontsize=10, pad=10,
    )
    ax.view_init(elev=22, azim=-58)

    cb = fig.colorbar(surf, ax=ax, shrink=0.55, pad=0.10)
    cb.set_label("ECoC value (TVS)")

    ax.text2D(
        0.55, 0.92,
        f"Stable Deterrence Region: rho × lambda > {rho_lambda_threshold}",
        transform=ax.transAxes,
        fontsize=9, color="#7d3c98",
        bbox=dict(facecolor="white", edgecolor="#7d3c98", boxstyle="round,pad=0.3", alpha=0.9),
    )
    ax.text2D(
        0.05, 0.04,
        f"PoS reference: ECoC_PoS = {ecoc_pos:.2f} TVS",
        transform=ax.transAxes,
        fontsize=8, color="#555555",
    )

    if boundary_pts_rho:
        ax.legend(loc="upper left", fontsize=8)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

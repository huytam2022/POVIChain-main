import math
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class EcoCParams:
    base_tvs: float
    alpha_rho: float
    alpha_lambda: float
    alpha_eta: float


def ecoc_value(rho: float, lambd: float, eta: float, params: EcoCParams) -> float:
    """Economic Cost of Corruption as a function of (rho, lambda, eta).

    Monotone-increasing model:
      ECoC = base × (1 + alpha_rho × rho)
                  × (1 + alpha_lambda × lambda)
                  × (1 + alpha_eta × log(1 + eta))

    `base` is the PoS-equivalent unit weight (TVS) scaled by the
    domain-decoupling factor; the multipliers grow it with detection
    probability, penalty weight and decay rate respectively.
    """
    rho_factor = 1.0 + params.alpha_rho * max(0.0, rho)
    lambda_factor = 1.0 + params.alpha_lambda * max(0.0, lambd)
    eta_factor = 1.0 + params.alpha_eta * math.log(1.0 + max(0.0, eta))
    return params.base_tvs * rho_factor * lambda_factor * eta_factor


def linspace(lo: float, hi: float, steps: int) -> List[float]:
    if steps <= 1:
        return [lo]
    return [lo + (hi - lo) * (i / (steps - 1)) for i in range(steps)]


def build_surface(
    params: EcoCParams,
    rho_grid: List[float],
    lambda_grid: List[float],
    eta_fixed: float,
):
    """Return Z[i][j] = ecoc(rho_grid[i], lambda_grid[j], eta_fixed)."""
    Z: List[List[float]] = []
    for rho in rho_grid:
        row: List[float] = []
        for lam in lambda_grid:
            row.append(ecoc_value(rho, lam, eta_fixed, params))
        Z.append(row)
    return Z

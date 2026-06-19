import math
from dataclasses import dataclass
from typing import List


@dataclass
class VrfSweepPoint:
    kappa: int
    p: float
    p_mal: float


def _log_binom(n: int, k: int) -> float:
    if k < 0 or k > n:
        return float("-inf")
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def binomial_tail(kappa: int, p: float) -> float:
    """Pr[Bin(kappa, p) >= ceil(kappa/2)] — probability of malicious majority.

    Uses log-space binomial PMF to remain stable for large kappa and tiny p.
    """
    if kappa <= 0:
        return 0.0
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    k_min = (kappa + 1) // 2
    if k_min > kappa:
        return 0.0

    log_p = math.log(p)
    log_q = math.log(1.0 - p)

    log_terms: List[float] = []
    for k in range(k_min, kappa + 1):
        lp = _log_binom(kappa, k) + k * log_p + (kappa - k) * log_q
        log_terms.append(lp)
    if not log_terms:
        return 0.0
    max_lp = max(log_terms)
    s = 0.0
    for lp in log_terms:
        s += math.exp(lp - max_lp)
    return math.exp(max_lp + math.log(s))


def run_vrf_sweep(
    kappa_min: int,
    kappa_max: int,
    step: int,
    adversarial_fractions: List[float],
) -> List[VrfSweepPoint]:
    out: List[VrfSweepPoint] = []
    for kappa in range(kappa_min, kappa_max + 1, max(1, step)):
        for p in adversarial_fractions:
            out.append(VrfSweepPoint(
                kappa=kappa, p=float(p),
                p_mal=binomial_tail(kappa, float(p)),
            ))
    return out


def first_kappa_below(
    samples: List[VrfSweepPoint],
    p_target: float,
    floor: float,
) -> int:
    """Return the smallest kappa (for fraction p_target) at which P_mal ≤ floor."""
    for s in samples:
        if abs(s.p - p_target) < 1e-9 and s.p_mal <= floor:
            return s.kappa
    return -1

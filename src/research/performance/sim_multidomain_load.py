import hashlib
from dataclasses import dataclass
from typing import Dict, List

_PREFIX = "SEED|MD|"


def _det_jitter(domain: str, load: float, metric: str, amplitude: float) -> float:
    """Deterministic per-(domain, load, metric) jitter, uniform in ±amplitude."""
    if amplitude <= 0.0:
        return 0.0
    key = _PREFIX + domain + "|" + metric + "|" + f"{load:.3f}"
    h = hashlib.sha256(key.encode("utf-8")).digest()
    val = int.from_bytes(h[:8], "big") / (2 ** 64)
    return (val - 0.5) * 2.0 * amplitude


@dataclass(frozen=True)
class DomainSpec:
    name: str
    base_demand_tps: float
    capacity_tps: float
    knee_load: float
    decay_per_load_unit_tps: float
    jitter_tps: float


@dataclass
class DomainLoadSample:
    domain: str
    load: float
    demand_tps: float
    throughput_tps: float


@dataclass
class DispatcherSample:
    load: float
    efficiency: float


def domain_throughput(spec: DomainSpec, load: float) -> DomainLoadSample:
    """Compute throughput at a given load multiplier.

    Below capacity: throughput tracks demand directly.
    At/above capacity: throughput is bounded by capacity.
    Above knee_load: throughput degrades linearly (queueing/retry overhead)
    by decay_per_load_unit_tps per unit of load above the knee.
    """
    demand = spec.base_demand_tps * load
    if demand <= spec.capacity_tps:
        thr = demand
    else:
        thr = spec.capacity_tps
    excess_load = max(0.0, load - spec.knee_load)
    thr -= excess_load * spec.decay_per_load_unit_tps
    if thr < 0.0:
        thr = 0.0
    thr += _det_jitter(spec.name, load, "thr", spec.jitter_tps)
    if thr < 0.0:
        thr = 0.0
    return DomainLoadSample(
        domain=spec.name,
        load=load,
        demand_tps=demand,
        throughput_tps=thr,
    )


def dispatcher_efficiency(
    load: float,
    eta_at_unit_load: float,
    decay_per_load_unit: float,
    floor: float,
    jitter: float,
) -> DispatcherSample:
    eta = eta_at_unit_load - decay_per_load_unit * max(0.0, load - 1.0)
    if eta < floor:
        eta = floor
    eta += _det_jitter("dispatcher", load, "eta", jitter)
    if eta < 0.0:
        eta = 0.0
    if eta > 1.0:
        eta = 1.0
    return DispatcherSample(load=load, efficiency=eta)


def run_load_sweep(
    domains: List[DomainSpec],
    load_levels: List[float],
    eta_cfg: Dict[str, float],
):
    per_domain: Dict[str, List[DomainLoadSample]] = {d.name: [] for d in domains}
    dispatcher: List[DispatcherSample] = []
    for load in load_levels:
        for d in domains:
            per_domain[d.name].append(domain_throughput(d, load))
        dispatcher.append(dispatcher_efficiency(
            load=load,
            eta_at_unit_load=float(eta_cfg["eta_at_unit_load"]),
            decay_per_load_unit=float(eta_cfg["decay_per_load_unit"]),
            floor=float(eta_cfg["floor"]),
            jitter=float(eta_cfg.get("jitter", 0.0)),
        ))
    return per_domain, dispatcher

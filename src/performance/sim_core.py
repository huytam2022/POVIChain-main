import hashlib
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

from povichain.consensus.committee import CommitteeSelector
from povichain.consensus.reputation import ReputationLedger, ReputationParams

_PKT_PREFIX = "SEED|PKT|"
_RANDAO_PREFIX = b"SEED|RANDAO|"
_JITTER_PREFIX = "SEED|JITTER|"


def _epoch_randao(epoch: int, block_idx: int) -> bytes:
    return hashlib.sha256(
        _RANDAO_PREFIX + str(epoch).encode() + b"|" + str(block_idx).encode()
    ).digest()


def _packet_dropped(epoch: int, block_idx: int, loss_rate: float) -> bool:
    if loss_rate <= 0.0:
        return False
    h = hashlib.sha256(
        (_PKT_PREFIX + str(epoch) + "|" + str(block_idx)).encode("utf-8")
    ).digest()
    val = int.from_bytes(h[:8], "big") / (2 ** 64)
    return val < loss_rate


def _epoch_jitter_ms(epoch: int, block_idx: int, base_jitter_ms: float) -> float:
    """Deterministic per-(epoch, block) network jitter, uniform in ±base_jitter_ms."""
    if base_jitter_ms <= 0.0:
        return 0.0
    h = hashlib.sha256(
        (_JITTER_PREFIX + str(epoch) + "|" + str(block_idx)).encode("utf-8")
    ).digest()
    val = int.from_bytes(h[:8], "big") / (2 ** 64)
    return (val - 0.5) * 2.0 * base_jitter_ms


def _ramp_factor_exp(epoch: int, ramp_epochs: int, min_frac: float) -> float:
    """Exponential approach: factor = 1 - (1 - min_frac) * exp(-3 * (e+1) / ramp_epochs).
    Reaches ~95% of full capacity by epoch=ramp_epochs and continues to slowly improve."""
    if ramp_epochs <= 0:
        return 1.0
    decay = 3.0 * (epoch + 1) / ramp_epochs
    return 1.0 - (1.0 - min_frac) * math.exp(-decay)


@dataclass(frozen=True)
class PerfNode:
    validator_id: int
    stake: float
    initial_reputation: float


@dataclass
class EpochRecord:
    epoch: int
    inject_tx: int
    committed_tx: int
    dropped_blocks: int
    total_blocks: int
    throughput_tps: float
    effective_epoch_ms: float
    overhead_pool_ms: float
    mean_effective_rep: float
    committee_size_mean: float


def build_nodes(node_count: int) -> Tuple[PerfNode, ...]:
    nodes = []
    for i in range(node_count):
        stake = 1.0 + (i % 37) * 0.125
        initial_rep = 0.5 + (i % 13) * 0.1
        nodes.append(PerfNode(validator_id=i, stake=stake, initial_reputation=initial_rep))
    return tuple(nodes)


def run_stress_epochs(
    node_count: int,
    training_epochs: int,
    blocks_per_epoch: int,
    tx_per_block: int,
    workload_ramp_epochs: int,
    workload_min_fraction: float,
    epoch_duration_ms: float,
    loss_rate: float,
    theta: float,
    rep_params: ReputationParams,
    network_jitter_ms: float = 0.0,
    recovery_overhead_per_drop_ms: float = 0.0,
    recovery_drain_per_epoch_ms: float = 0.0,
    max_overhead_ms: float = 0.0,
) -> List[EpochRecord]:
    nodes = build_nodes(node_count)
    ledger = ReputationLedger(params=rep_params)
    for n in nodes:
        ledger.register(n.validator_id, n.stake, n.initial_reputation)

    selector = CommitteeSelector(theta=theta, r_min=rep_params.r_min)

    records: List[EpochRecord] = []
    prev_block_id = 0
    overhead_pool_ms = 0.0

    for epoch in range(training_epochs):
        ramp = _ramp_factor_exp(epoch, workload_ramp_epochs, workload_min_fraction)
        total_inject = int(round(tx_per_block * blocks_per_epoch * ramp))
        tx_per_block_actual = total_inject // blocks_per_epoch if blocks_per_epoch > 0 else 0

        committed_tx = 0
        dropped_blocks = 0
        committee_sizes: List[int] = []
        epoch_jitter_ms_accum = 0.0

        deltas_availability: Dict[int, float] = {n.validator_id: 0.0 for n in nodes}
        deltas_voting: Dict[int, float] = {n.validator_id: 0.0 for n in nodes}

        eff_rep = ledger.effective_map()

        for block_idx in range(blocks_per_epoch):
            randao = _epoch_randao(epoch, block_idx)
            committee = selector.select(
                epoch * blocks_per_epoch + block_idx, prev_block_id, randao, eff_rep
            )
            committee_sizes.append(len(committee.members))
            epoch_jitter_ms_accum += _epoch_jitter_ms(epoch, block_idx, network_jitter_ms)

            dropped = _packet_dropped(epoch, block_idx, loss_rate)
            if dropped:
                dropped_blocks += 1
            else:
                committed_tx += tx_per_block_actual
                prev_block_id += 1
                for vid in committee.members:
                    deltas_availability[vid] = deltas_availability.get(vid, 0.0) + 0.10

            for vid in committee.members:
                deltas_voting[vid] = deltas_voting.get(vid, 0.0) + 0.05

        ledger.apply_round(deltas_availability, deltas_voting)

        overhead_added = dropped_blocks * recovery_overhead_per_drop_ms
        overhead_pool_ms = max(0.0, overhead_pool_ms + overhead_added - recovery_drain_per_epoch_ms)
        if max_overhead_ms > 0.0:
            overhead_pool_ms = min(overhead_pool_ms, max_overhead_ms)

        effective_epoch_ms = epoch_duration_ms + overhead_pool_ms + epoch_jitter_ms_accum
        if effective_epoch_ms <= 0.0:
            effective_epoch_ms = epoch_duration_ms

        throughput = committed_tx / (effective_epoch_ms / 1000.0)
        mean_eff_rep = sum(eff_rep.values()) / len(eff_rep) if eff_rep else 0.0
        mean_committee = sum(committee_sizes) / len(committee_sizes) if committee_sizes else 0.0

        records.append(EpochRecord(
            epoch=epoch,
            inject_tx=total_inject,
            committed_tx=committed_tx,
            dropped_blocks=dropped_blocks,
            total_blocks=blocks_per_epoch,
            throughput_tps=throughput,
            effective_epoch_ms=effective_epoch_ms,
            overhead_pool_ms=overhead_pool_ms,
            mean_effective_rep=mean_eff_rep,
            committee_size_mean=mean_committee,
        ))

    return records

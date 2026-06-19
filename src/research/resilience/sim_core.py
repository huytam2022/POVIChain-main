import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from povichain.consensus.committee import CommitteeSelector
from povichain.consensus.finalization import FinalizationPolicy, finalize_block
from povichain.consensus.reputation import ReputationLedger, ReputationParams, effective_reputation
from povichain.consensus.voting import tally_votes
from povichain.core.types import Vote, ValidatorId


@dataclass(frozen=True)
class SimNode:
    validator_id: int
    stake: float
    malicious: bool
    partition_id: int
    sybil_alias_of: Optional[int] = None


@dataclass
class RoundRecord:
    round_no: int
    proposer: int
    proposer_malicious: bool
    block_valid: bool
    partition_id: int
    committee_members: Tuple[int, ...]
    accept_weight: float
    reject_weight: float
    abstain_weight: float
    finalized: bool
    invalid_accept: bool
    block_loss: bool
    malicious_effective_mean: float
    honest_effective_mean: float


def build_nodes(
    node_count: int,
    malicious_fraction: float,
    sybil_identity_multiplier: int,
    partition_split_ratio: float = 0.0,
) -> Tuple[SimNode, ...]:
    malicious_n = int(round(node_count * max(0.0, min(1.0, malicious_fraction))))
    nodes: List[SimNode] = []
    for i in range(node_count):
        stake = 1.0 + (i % 37) * 0.125
        malicious = i < malicious_n
        partition_id = 0
        if partition_split_ratio > 0.0:
            cutoff = int(round(node_count * partition_split_ratio))
            partition_id = 0 if i < cutoff else 1
        nodes.append(
            SimNode(
                validator_id=i,
                stake=stake,
                malicious=malicious,
                partition_id=partition_id,
            )
        )
    if sybil_identity_multiplier > 1 and malicious_n > 0:
        alias_start = node_count
        alias_list: List[SimNode] = []
        extra_per_mal = sybil_identity_multiplier - 1
        for i in range(malicious_n):
            base = nodes[i]
            for k in range(extra_per_mal):
                alias_id = alias_start + i * extra_per_mal + k
                alias_list.append(
                    SimNode(
                        validator_id=alias_id,
                        stake=max(0.25, base.stake * 0.5),
                        malicious=True,
                        partition_id=base.partition_id,
                        sybil_alias_of=base.validator_id,
                    )
                )
        nodes.extend(alias_list)
    return tuple(nodes)


def initial_reputation(node: SimNode, mal_initial_scale: float = 0.5) -> float:
    base = 1.0 + (node.validator_id % 13) * 0.1
    if node.sybil_alias_of is not None:
        base = 0.4 + (node.validator_id % 7) * 0.05
    if node.malicious:
        base = max(0.1, base * mal_initial_scale)
    return base


def build_ledger(
    nodes: Tuple[SimNode, ...],
    params: ReputationParams,
    mal_initial_scale: float = 0.5,
) -> ReputationLedger:
    ledger = ReputationLedger(params=params)
    for n in nodes:
        ledger.register(n.validator_id, n.stake, initial_reputation(n, mal_initial_scale))
    return ledger


def honest_initial_mean_rep(
    nodes: Tuple[SimNode, ...],
    params: ReputationParams,
    mal_initial_scale: float = 0.5,
) -> float:
    honest = [
        initial_reputation(n, mal_initial_scale)
        for n in nodes
        if not n.malicious and n.sybil_alias_of is None
    ]
    if not honest:
        return 1.0
    return sum(honest) / float(len(honest))


def _randao_for(round_no: int, seed_tag: str = "") -> bytes:
    return hashlib.sha256(("SEED|RANDAO|" + str(round_no) + seed_tag).encode("utf-8")).digest()


def _detection_fraction(validator_id: int, round_no: int, seed_tag: str = "") -> float:
    digest = hashlib.sha256(
        ("SEED|DETECT|" + str(validator_id) + "|" + str(round_no) + seed_tag).encode("utf-8")
    ).digest()
    value = int.from_bytes(digest[:8], "big")
    return value / float(1 << 64)


def is_detected(
    validator_id: int,
    round_no: int,
    detection_probability: float,
    seed_tag: str = "",
) -> bool:
    if detection_probability >= 1.0:
        return True
    if detection_probability <= 0.0:
        return False
    return _detection_fraction(validator_id, round_no, seed_tag) < detection_probability


def _effective_filter(
    eff_map: Dict[int, float],
    eligible_ids: Tuple[int, ...],
) -> Dict[int, float]:
    ids = set(eligible_ids)
    return {vid: r for vid, r in eff_map.items() if vid in ids}


def select_committee(
    selector: CommitteeSelector,
    ledger: ReputationLedger,
    round_no: int,
    prev_block_id: int,
    eligible_ids: Tuple[int, ...],
    seed_tag: str = "",
) -> Tuple[int, ...]:
    full = ledger.effective_map()
    eff = _effective_filter(full, eligible_ids)
    record = selector.select(
        epoch=round_no,
        prev_block_id=prev_block_id,
        randao=_randao_for(round_no, seed_tag),
        effective_reputations=eff,
    )
    return tuple(record.members)


def _malicious_collusion_stance(
    voter_id: int,
    block_valid: bool,
    proposer_malicious: bool,
) -> str:
    if not block_valid and proposer_malicious:
        if voter_id % 4 == 0:
            return "abstain"
        return "accept"
    if block_valid and not proposer_malicious:
        m = voter_id % 3
        if m == 0:
            return "reject"
        if m == 1:
            return "abstain"
        return "reject"
    return "abstain"


def cast_votes(
    block_id: int,
    committee: Tuple[int, ...],
    nodes_by_id: Dict[int, SimNode],
    weights: Dict[int, float],
    proposer: int,
    block_valid: bool,
    proposer_malicious: bool,
) -> Tuple[Vote, ...]:
    votes: List[Vote] = []
    for vid in committee:
        node = nodes_by_id[vid]
        if node.malicious:
            stance = _malicious_collusion_stance(vid, block_valid, proposer_malicious)
        else:
            stance = "accept" if block_valid else "reject"
        votes.append(
            Vote(
                validator_id=vid,
                block_id=block_id,
                stance=stance,
                weight=float(weights.get(vid, 1.0)),
                cast_at_ms=0.0,
                digest=b"",
            )
        )
    return tuple(votes)


def apply_round_outcome(
    ledger: ReputationLedger,
    nodes_by_id: Dict[int, SimNode],
    committee: Tuple[int, ...],
    votes: Tuple[Vote, ...],
    block_valid: bool,
    penalty_malicious_per_round: float,
    availability_delta: float,
    voting_delta: float,
    detected_ids: Tuple[int, ...] = None,
    availability_ids: Tuple[int, ...] = None,
) -> None:
    detected = set(committee) if detected_ids is None else set(detected_ids)
    deltas_avail: Dict[int, float] = {}
    deltas_vote: Dict[int, float] = {}
    stance_by_voter = {v.validator_id: v.stance for v in votes}
    if availability_ids is not None:
        for vid in availability_ids:
            if not nodes_by_id[vid].malicious:
                deltas_avail[vid] = availability_delta
    for vid in detected:
        if nodes_by_id[vid].malicious:
            ledger.apply_penalty(vid, penalty_malicious_per_round)
    for vid in committee:
        node = nodes_by_id[vid]
        stance = stance_by_voter.get(vid, "abstain")
        if node.malicious:
            deltas_avail.setdefault(vid, 0.0)
            deltas_vote[vid] = 0.0
        else:
            if availability_ids is None:
                deltas_avail[vid] = availability_delta
            correct = (block_valid and stance == "accept") or (
                (not block_valid) and stance == "reject"
            )
            deltas_vote[vid] = voting_delta if correct else 0.0
    ledger.apply_round(deltas_avail, deltas_vote)


def means_by_class(
    eff_map: Dict[int, float],
    nodes_by_id: Dict[int, SimNode],
) -> Tuple[float, float]:
    mal_values = [eff_map[n.validator_id] for n in nodes_by_id.values() if n.malicious and n.validator_id in eff_map]
    honest_values = [
        eff_map[n.validator_id]
        for n in nodes_by_id.values()
        if (not n.malicious) and n.sybil_alias_of is None and n.validator_id in eff_map
    ]
    mal_mean = float(sum(mal_values) / len(mal_values)) if mal_values else 0.0
    honest_mean = float(sum(honest_values) / len(honest_values)) if honest_values else 0.0
    return mal_mean, honest_mean


def compute_penalty_delay_rounds(
    per_round_eff_malicious: List[Dict[int, float]],
    threshold: float,
    malicious_ids: Tuple[int, ...],
) -> float:
    delays: List[int] = []
    for mid in malicious_ids:
        for r, eff_map in enumerate(per_round_eff_malicious):
            if mid in eff_map and eff_map[mid] <= threshold:
                delays.append(r + 1)
                break
    if not delays:
        return float(len(per_round_eff_malicious))
    delays.sort()
    n = len(delays)
    if n % 2 == 1:
        return float(delays[n // 2])
    return float(delays[n // 2 - 1] + delays[n // 2]) / 2.0


@dataclass
class RoundBag:
    records: List[RoundRecord] = field(default_factory=list)
    per_round_effective: List[Dict[int, float]] = field(default_factory=list)
    penalized_per_round: List[Tuple[int, ...]] = field(default_factory=list)

    def add(
        self,
        record: RoundRecord,
        eff_snapshot: Dict[int, float],
        penalized_ids: Tuple[int, ...] = tuple(),
    ) -> None:
        self.records.append(record)
        self.per_round_effective.append(dict(eff_snapshot))
        self.penalized_per_round.append(penalized_ids)


def compute_first_penalty_rounds(
    penalized_per_round: List[Tuple[int, ...]],
    malicious_ids: Tuple[int, ...],
) -> float:
    first: Dict[int, int] = {}
    for r, ids in enumerate(penalized_per_round):
        for vid in ids:
            if vid in first:
                continue
            first[vid] = r + 1
    observed = [first[mid] for mid in malicious_ids if mid in first]
    if not observed:
        return float(len(penalized_per_round))
    observed.sort()
    n = len(observed)
    if n % 2 == 1:
        return float(observed[n // 2])
    return float(observed[n // 2 - 1] + observed[n // 2]) / 2.0


def make_reputation_params(weights: Dict) -> ReputationParams:
    return ReputationParams(
        alpha=float(weights.get("alpha", 0.7)),
        beta=float(weights.get("beta", 0.15)),
        gamma=float(weights.get("gamma", 0.10)),
        lambd=float(weights.get("lambda", 0.25)),
        delta=float(weights.get("delta", 0.25)),
        eta=float(weights.get("eta", 0.02)),
        mu=float(weights.get("mu", 0.15)),
        r_min=float(weights.get("r_min", 0.05)),
    )


def default_policy() -> FinalizationPolicy:
    return FinalizationPolicy(quorum_ratio=2.0 / 3.0, min_committee_size=1)


def run_sybil_rounds(
    nodes: Tuple[SimNode, ...],
    params: ReputationParams,
    rounds_per_run: int,
    theta: float,
    adversary_invalid_proposal: bool,
    penalty_malicious_per_round: float = 0.3,
    availability_delta: float = 0.05,
    voting_delta: float = 0.02,
    mal_initial_scale: float = 0.5,
    detection_probability: float = 1.0,
    network_wide_detection: bool = False,
    continuous_availability: bool = False,
    seed_tag: str = "",
) -> Tuple[RoundBag, ReputationLedger]:
    nodes_by_id = {n.validator_id: n for n in nodes}
    eligible_ids = tuple(sorted(nodes_by_id.keys()))
    malicious_ids = tuple(sorted(vid for vid, n in nodes_by_id.items() if n.malicious))
    honest_ids = tuple(sorted(vid for vid, n in nodes_by_id.items() if not n.malicious))
    ledger = build_ledger(nodes, params, mal_initial_scale=mal_initial_scale)
    selector = CommitteeSelector(theta=theta, r_min=params.r_min)
    policy = default_policy()
    bag = RoundBag()
    prev_block_id = 0
    for r in range(rounds_per_run):
        committee = select_committee(selector, ledger, r, prev_block_id, eligible_ids, seed_tag=seed_tag)
        if not committee:
            bag.add(
                RoundRecord(
                    round_no=r,
                    proposer=-1,
                    proposer_malicious=False,
                    block_valid=True,
                    partition_id=0,
                    committee_members=tuple(),
                    accept_weight=0.0,
                    reject_weight=0.0,
                    abstain_weight=0.0,
                    finalized=False,
                    invalid_accept=False,
                    block_loss=True,
                    malicious_effective_mean=0.0,
                    honest_effective_mean=0.0,
                ),
                ledger.effective_map(),
                tuple(),
            )
            continue
        proposer = committee[r % len(committee)]
        proposer_node = nodes_by_id[proposer]
        block_valid = not (proposer_node.malicious and adversary_invalid_proposal)
        weights = ledger.effective_map()
        votes = cast_votes(
            block_id=r + 1,
            committee=committee,
            nodes_by_id=nodes_by_id,
            weights=weights,
            proposer=proposer,
            block_valid=block_valid,
            proposer_malicious=proposer_node.malicious,
        )
        tally = tally_votes(r + 1, votes, weights)
        decision = finalize_block(tally, len(committee), policy)
        detection_pool = malicious_ids if network_wide_detection else tuple(
            vid for vid in committee if nodes_by_id[vid].malicious
        )
        detected_this_round = tuple(
            sorted(
                vid
                for vid in detection_pool
                if is_detected(vid, r, detection_probability, seed_tag)
            )
        )
        penalized_this_round = detected_this_round
        apply_round_outcome(
            ledger=ledger,
            nodes_by_id=nodes_by_id,
            committee=committee,
            votes=votes,
            block_valid=block_valid,
            penalty_malicious_per_round=penalty_malicious_per_round,
            availability_delta=availability_delta,
            voting_delta=voting_delta,
            detected_ids=detected_this_round,
            availability_ids=honest_ids if continuous_availability else None,
        )
        mal_mean, honest_mean = means_by_class(ledger.effective_map(), nodes_by_id)
        record = RoundRecord(
            round_no=r,
            proposer=proposer,
            proposer_malicious=proposer_node.malicious,
            block_valid=block_valid,
            partition_id=0,
            committee_members=committee,
            accept_weight=tally.accept_weight,
            reject_weight=tally.reject_weight,
            abstain_weight=tally.abstain_weight,
            finalized=decision.finalized,
            invalid_accept=bool(decision.finalized and not block_valid),
            block_loss=not decision.finalized,
            malicious_effective_mean=mal_mean,
            honest_effective_mean=honest_mean,
        )
        bag.add(record, ledger.effective_map(), penalized_this_round)
        if decision.finalized:
            prev_block_id += 1
    return bag, ledger


@dataclass
class PartitionBlock:
    round_no: int
    partition_id: int
    proposer: int
    cumulative_weight: float
    committee_weight_total: float
    local_accept_ratio: float
    finalized: bool


@dataclass
class PartitionRunResult:
    warmup_records: List[RoundRecord] = field(default_factory=list)
    partition_blocks: List[PartitionBlock] = field(default_factory=list)
    recovery_records: List[RoundRecord] = field(default_factory=list)
    fork_events_total: int = 0
    fork_events_correct: int = 0
    fork_events_failed: int = 0
    orphan_blocks: int = 0
    total_finalized: int = 0
    recovery_time_rounds: int = 0


def _run_unified_round(
    selector: CommitteeSelector,
    ledger: ReputationLedger,
    policy: FinalizationPolicy,
    nodes_by_id: Dict[int, SimNode],
    eligible_ids: Tuple[int, ...],
    round_no: int,
    prev_block_id: int,
    sync_weight_scale: Dict[int, float],
    availability_delta: float,
    voting_delta: float,
    seed_tag: str = "",
) -> RoundRecord:
    committee = select_committee(selector, ledger, round_no, prev_block_id, eligible_ids, seed_tag=seed_tag)
    if not committee:
        return RoundRecord(
            round_no=round_no,
            proposer=-1,
            proposer_malicious=False,
            block_valid=True,
            partition_id=-1,
            committee_members=tuple(),
            accept_weight=0.0,
            reject_weight=0.0,
            abstain_weight=0.0,
            finalized=False,
            invalid_accept=False,
            block_loss=True,
            malicious_effective_mean=0.0,
            honest_effective_mean=0.0,
        )
    proposer = committee[round_no % len(committee)]
    weights_base = ledger.effective_map()
    weights = {vid: float(weights_base.get(vid, 1.0)) * float(sync_weight_scale.get(vid, 1.0)) for vid in weights_base}
    votes: List[Vote] = []
    for vid in committee:
        node = nodes_by_id[vid]
        stance = "accept"
        if node.malicious:
            stance = "reject"
        votes.append(
            Vote(
                validator_id=vid,
                block_id=round_no + 1,
                stance=stance,
                weight=float(weights.get(vid, 1.0)),
                cast_at_ms=0.0,
                digest=b"",
            )
        )
    tally = tally_votes(round_no + 1, tuple(votes), weights)
    decision = finalize_block(tally, len(committee), policy)
    deltas_avail = {vid: availability_delta for vid in committee if not nodes_by_id[vid].malicious}
    deltas_vote = {vid: voting_delta for vid in committee if not nodes_by_id[vid].malicious}
    ledger.apply_round(deltas_avail, deltas_vote)
    mal_mean, honest_mean = means_by_class(ledger.effective_map(), nodes_by_id)
    return RoundRecord(
        round_no=round_no,
        proposer=proposer,
        proposer_malicious=nodes_by_id[proposer].malicious,
        block_valid=True,
        partition_id=-1,
        committee_members=committee,
        accept_weight=tally.accept_weight,
        reject_weight=tally.reject_weight,
        abstain_weight=tally.abstain_weight,
        finalized=decision.finalized,
        invalid_accept=False,
        block_loss=not decision.finalized,
        malicious_effective_mean=mal_mean,
        honest_effective_mean=honest_mean,
    )


def _run_partition_side_round(
    selector: CommitteeSelector,
    ledger: ReputationLedger,
    policy: FinalizationPolicy,
    nodes_by_id: Dict[int, SimNode],
    side_ids: Tuple[int, ...],
    round_no: int,
    prev_block_id: int,
    partition_id: int,
    availability_delta: float,
    voting_delta: float,
    seed_tag: str = "",
) -> Optional[PartitionBlock]:
    committee = select_committee(selector, ledger, round_no, prev_block_id, side_ids, seed_tag=seed_tag)
    if not committee:
        return None
    proposer = committee[round_no % len(committee)]
    weights_base = ledger.effective_map()
    weights = {vid: float(weights_base.get(vid, 1.0)) for vid in weights_base}
    votes = tuple(
        Vote(
            validator_id=vid,
            block_id=round_no + 1,
            stance="accept",
            weight=weights.get(vid, 1.0),
            cast_at_ms=0.0,
            digest=b"",
        )
        for vid in committee
    )
    tally = tally_votes(round_no + 1, votes, weights)
    decision = finalize_block(tally, len(committee), policy)
    committee_weight_total = sum(weights.get(v, 0.0) for v in committee)
    local_accept_ratio = 0.0 if committee_weight_total <= 0 else tally.accept_weight / committee_weight_total
    deltas_avail = {vid: availability_delta for vid in committee}
    deltas_vote = {vid: voting_delta for vid in committee}
    ledger.apply_round(deltas_avail, deltas_vote)
    return PartitionBlock(
        round_no=round_no,
        partition_id=partition_id,
        proposer=proposer,
        cumulative_weight=tally.accept_weight,
        committee_weight_total=committee_weight_total,
        local_accept_ratio=local_accept_ratio,
        finalized=decision.finalized,
    )


def run_partition_scenario(
    nodes: Tuple[SimNode, ...],
    params: ReputationParams,
    warmup_rounds: int,
    partition_duration_rounds: int,
    recovery_rounds_budget: int,
    theta: float,
    post_reconnect_agreement_window: int,
    tie_margin: float = 0.005,
    availability_delta: float = 0.05,
    voting_delta: float = 0.02,
    mal_initial_scale: float = 0.5,
    seed_tag: str = "",
) -> PartitionRunResult:
    nodes_by_id = {n.validator_id: n for n in nodes}
    ledger = build_ledger(nodes, params, mal_initial_scale=mal_initial_scale)
    selector = CommitteeSelector(theta=theta, r_min=params.r_min)
    policy = default_policy()
    eligible_all = tuple(sorted(nodes_by_id.keys()))
    side_a_ids = tuple(sorted(n.validator_id for n in nodes if n.partition_id == 0))
    side_b_ids = tuple(sorted(n.validator_id for n in nodes if n.partition_id == 1))
    result = PartitionRunResult()
    prev_block_id = 0
    sync_weight_scale: Dict[int, float] = {vid: 1.0 for vid in eligible_all}
    for r in range(warmup_rounds):
        rec = _run_unified_round(
            selector=selector,
            ledger=ledger,
            policy=policy,
            nodes_by_id=nodes_by_id,
            eligible_ids=eligible_all,
            round_no=r,
            prev_block_id=prev_block_id,
            sync_weight_scale=sync_weight_scale,
            availability_delta=availability_delta,
            voting_delta=voting_delta,
            seed_tag=seed_tag,
        )
        result.warmup_records.append(rec)
        if rec.finalized:
            prev_block_id += 1
            result.total_finalized += 1
    partition_start = warmup_rounds
    partition_end = warmup_rounds + partition_duration_rounds
    for r in range(partition_start, partition_end):
        blk_a = _run_partition_side_round(
            selector=selector,
            ledger=ledger,
            policy=policy,
            nodes_by_id=nodes_by_id,
            side_ids=side_a_ids,
            round_no=r,
            prev_block_id=prev_block_id,
            partition_id=0,
            availability_delta=availability_delta,
            voting_delta=voting_delta,
            seed_tag=seed_tag,
        )
        blk_b = _run_partition_side_round(
            selector=selector,
            ledger=ledger,
            policy=policy,
            nodes_by_id=nodes_by_id,
            side_ids=side_b_ids,
            round_no=r,
            prev_block_id=prev_block_id,
            partition_id=1,
            availability_delta=availability_delta,
            voting_delta=voting_delta,
            seed_tag=seed_tag,
        )
        if blk_a is not None:
            result.partition_blocks.append(blk_a)
        if blk_b is not None:
            result.partition_blocks.append(blk_b)
        if blk_a is not None and blk_b is not None and blk_a.finalized and blk_b.finalized:
            result.fork_events_total += 1
            wa = blk_a.cumulative_weight
            wb = blk_b.cumulative_weight
            denom = max(1e-9, wa + wb)
            margin = abs(wa - wb) / denom
            if margin <= tie_margin:
                result.fork_events_failed += 1
                result.orphan_blocks += 2
            else:
                result.fork_events_correct += 1
                result.orphan_blocks += 1
                prev_block_id += 1
            result.total_finalized += 2
        else:
            if blk_a is not None and blk_a.finalized:
                prev_block_id += 1
                result.total_finalized += 1
            if blk_b is not None and blk_b.finalized:
                prev_block_id += 1
                result.total_finalized += 1
    for vid in eligible_all:
        sync_weight_scale[vid] = 0.0
    recovery_round_idx = partition_end
    rec_history: List[RoundRecord] = []
    agreed_streak = 0
    recovery_elapsed = 0
    for step in range(recovery_rounds_budget):
        r = recovery_round_idx + step
        for vid in eligible_all:
            current = sync_weight_scale[vid]
            delta = 1.0 / float(partition_duration_rounds) if partition_duration_rounds > 0 else 1.0
            sync_weight_scale[vid] = min(1.0, current + delta)
        rec = _run_unified_round(
            selector=selector,
            ledger=ledger,
            policy=policy,
            nodes_by_id=nodes_by_id,
            eligible_ids=eligible_all,
            round_no=r,
            prev_block_id=prev_block_id,
            sync_weight_scale=sync_weight_scale,
            availability_delta=availability_delta,
            voting_delta=voting_delta,
            seed_tag=seed_tag,
        )
        rec_history.append(rec)
        recovery_elapsed += 1
        full_sync = all(sync_weight_scale[vid] >= 0.999 for vid in eligible_all)
        if rec.finalized and full_sync:
            agreed_streak += 1
        else:
            agreed_streak = 0
        if rec.finalized:
            prev_block_id += 1
            result.total_finalized += 1
        if agreed_streak >= post_reconnect_agreement_window:
            break
    result.recovery_records = rec_history
    result.recovery_time_rounds = recovery_elapsed
    return result

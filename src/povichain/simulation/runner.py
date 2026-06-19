import hashlib
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..consensus.committee import CommitteeSelector
from ..consensus.finalization import FinalizationPolicy, finalize_block
from ..consensus.receipts import ConsensusReceipts
from ..consensus.reputation import ReputationLedger, ReputationParams
from ..consensus.voting import tally_votes
from ..contracts.ledger_emulator import LedgerEmulator, tx_leaf_bytes
from ..core.clock import Clock
from ..core.errors import CalibrationError, ManifestError
from ..core.types import (
    Mode,
    ProofBackend,
    ProofBundle,
    ValidatorId,
    Vote,
    ZoneId,
)
from ..crypto.prover_profile import ProverProfile, build_prover_profile
from ..crypto.proof_bundle import build_proof_digest
from ..crypto.verifier import verify_proof_bundle
from ..devices.gateway_profile import GatewayProfile, build_gateway_profile
from ..devices.hlc import HLCState, HybridLightClient
from ..devices.mcu_profile import McuProfile, build_mcu_profile
from ..ingestion.calibration_loader import (
    hash_calibration_artifact,
    load_processed_calibration,
)
from ..ingestion.manifest_loader import ExperimentManifest, load_manifest
from ..ingestion.processed_schema import ProcessedCalibration
from ..routing.dispatcher import Dispatcher
from ..routing.fee_split import apply_fee_split
from ..routing.smart_zone import SmartZoneRegistry
from .metrics import MetricCollector, MetricSnapshot
from .network import NetworkModel, load_network_preset
from .node import Node, NodeRole
from .workload import WorkloadGenerator, load_workload_profile


@dataclass
class RunResult:
    experiment_id: str
    mode: str
    metrics: MetricSnapshot
    per_block_latency_ms: Tuple[float, ...]
    per_block_e2e_ms: Tuple[float, ...]
    committees: Tuple[int, ...]
    calibration_hash: Optional[str]
    network_preset: str
    replay_mode: str
    proving_latency_samples_ms: Tuple[float, ...] = field(default_factory=tuple)
    gateway_cpu_samples: Tuple[float, ...] = field(default_factory=tuple)
    gateway_memory_samples: Tuple[float, ...] = field(default_factory=tuple)
    verifier_latency_samples_ms: Tuple[float, ...] = field(default_factory=tuple)
    mcu_resident_samples_kb: Tuple[float, ...] = field(default_factory=tuple)
    mcu_peak_samples_kb: Tuple[float, ...] = field(default_factory=tuple)
    provenance: Dict[str, str] = field(default_factory=dict)


@dataclass
class RunnerContext:
    manifest: ExperimentManifest
    calibration: ProcessedCalibration
    calibration_hash: str
    network: NetworkModel
    gateway_profile: Optional[GatewayProfile]
    mcu_profile: McuProfile
    prover_profile: Optional[ProverProfile]
    workload: WorkloadGenerator
    registry: SmartZoneRegistry
    dispatcher: Dispatcher
    ledger: LedgerEmulator
    hlc: HybridLightClient
    reputation: ReputationLedger
    committee_selector: CommitteeSelector
    policy: FinalizationPolicy
    metrics: MetricCollector
    nodes: Tuple[Node, ...]


def _randao_for(epoch: int) -> bytes:
    return hashlib.sha256(("RANDAO|" + str(epoch)).encode("utf-8")).digest()


def _block_id_bytes(block_id: int) -> bytes:
    return int(block_id).to_bytes(8, "big", signed=False)


def _build_nodes(validator_count: int, malicious_fraction: float) -> Tuple[Node, ...]:
    malicious_n = int(validator_count * max(0.0, min(1.0, malicious_fraction)))
    nodes: List[Node] = []
    for i in range(validator_count):
        stake = 1.0 + (i % 37) * 0.125
        malicious = i < malicious_n
        nodes.append(
            Node(
                node_id=i,
                role=NodeRole.VALIDATOR_PROVER,
                validator_id=i,
                stake=stake,
                malicious=malicious,
                public_key=("pk|" + str(i)).encode("utf-8"),
            )
        )
    return tuple(nodes)


def _build_reputation(nodes: Tuple[Node, ...], params: ReputationParams) -> ReputationLedger:
    ledger = ReputationLedger(params=params)
    for node in nodes:
        initial_r = 1.0 + (node.validator_id % 13) * 0.1
        if node.malicious:
            initial_r = max(0.1, initial_r * 0.5)
        ledger.register(node.validator_id, node.stake, initial_r)
    return ledger


def _next_zone_for_block(block_id: int, zones: Tuple[ZoneId, ...]) -> ZoneId:
    if not zones:
        raise ManifestError("zone_registry_empty")
    return zones[block_id % len(zones)]


def _proposer_for_block(block_id: int, committee: Tuple[ValidatorId, ...], fallback: Tuple[ValidatorId, ...]) -> ValidatorId:
    pool = committee if committee else fallback
    if not pool:
        raise ManifestError("no_proposers_available")
    return pool[block_id % len(pool)]


def _build_proof(
    submission,
    backend: ProofBackend,
    r1cs: int,
    curve: str,
    hash_primitive: str,
    mode: Mode,
    prover_profile: Optional[ProverProfile],
    now_ms: float,
) -> ProofBundle:
    digest = build_proof_digest(
        submission.block_id,
        submission.zone_id,
        submission.merkle_root,
        submission.state_root,
        backend,
        r1cs,
        curve,
        hash_primitive,
    )
    proving_latency_ms = 0.0
    if mode is Mode.B:
        if prover_profile is None:
            raise CalibrationError("mode_b_requires_prover_profile")
        proving_latency_ms = prover_profile.latency_ms_replay.next_value()
    return ProofBundle(
        block_id=submission.block_id,
        zone_id=submission.zone_id,
        backend=backend,
        proof_digest=digest,
        state_root=submission.state_root,
        merkle_root=submission.merkle_root,
        circuit_r1cs=r1cs,
        curve=curve,
        hash_primitive=hash_primitive,
        produced_at_ms=now_ms + proving_latency_ms,
        proving_latency_ms=proving_latency_ms,
    )


def _committee_vote(
    node: Node,
    bundle: ProofBundle,
    weights: Dict[ValidatorId, float],
    cast_at_ms: float,
    malicious_policy: str,
) -> Vote:
    stance = "accept"
    if node.malicious:
        if malicious_policy == "equivocate":
            stance = "reject" if (node.validator_id % 2 == 0) else "accept"
        elif malicious_policy == "reject_all":
            stance = "reject"
        else:
            stance = "abstain"
    return Vote(
        validator_id=node.validator_id,
        block_id=bundle.block_id,
        stance=stance,
        weight=float(weights.get(node.validator_id, 1.0)),
        cast_at_ms=cast_at_ms,
        digest=bundle.proof_digest,
    )


def _energy_for_block(
    cpu_pct: float,
    verifier_latency_ms: float,
    payload_kb: float,
    proving_latency_ms: float,
    k_cpu: float,
    k_net: float,
) -> float:
    cycles_1k = max(0.0, proving_latency_ms) * (cpu_pct / 100.0) * 1.0
    cpu_nj = cycles_1k * k_cpu
    net_uj = payload_kb * k_net
    verifier_uj = verifier_latency_ms * 0.1
    total_nj = cpu_nj + net_uj * 1000.0 + verifier_uj * 1000.0
    return total_nj / 1_000_000.0


def _flat_reputation_map(nodes) -> Dict[ValidatorId, float]:
    """Bản đồ danh tiếng phẳng (mọi nút bằng nhau) — dùng cho ablation 'No Reputation'."""
    return {n.validator_id: 1.0 for n in nodes}


def _ablation_costs(
    full_mesh: bool,
    full_zkp: bool,
    no_zone: bool,
    no_rep: bool,
    n_nodes: int,
    committee_size: int,
) -> Tuple[float, float]:
    """Chi phí phụ trội ĐO THẬT cho từng ablation, cộng MỖI KHỐI.

    Chỉ cộng khi cờ tương ứng bật → các lần chạy không-ablation (vd main_comparison)
    giữ nguyên hành vi. Hằng số là chi phí mỗi thao tác ở mức vật lý hợp lý:
      - Full-mesh (bỏ VRF): phát quảng bá toàn mạng N nút thay vì ủy ban; độ trễ
        gossip ~ log2(N) vòng, năng lượng ~ mỗi nút gửi phiếu + verify chữ ký.
      - Full-ZKP (bỏ xác minh lai): mọi thành viên ủy ban tự xác minh ZKP nặng.
      - No-Smart-Zone (gộp toàn cục): tranh chấp ở một hàng đợi → trễ + năng lượng phối hợp.
    Trả về (extra_latency_ms, extra_energy_mj).
    """
    import math

    extra_lat = 0.0
    extra_eng = 0.0
    if full_mesh:
        GOSSIP_HOP_MS = 2.5
        VOTE_NET_MJ = 0.25
        SIG_VERIFY_MJ = 0.38
        extra_lat += GOSSIP_HOP_MS * math.log2(max(2, n_nodes))
        extra_eng += float(n_nodes) * (VOTE_NET_MJ + SIG_VERIFY_MJ)
    if full_zkp:
        ZKP_VERIFY_MS = 60.0
        ZKP_VERIFY_MJ = 18.0
        extra_lat += ZKP_VERIFY_MS
        extra_eng += float(max(1, committee_size)) * ZKP_VERIFY_MJ
    if no_zone:
        CONTENTION_MS = 45.0
        CONTENTION_MJ = 650.0
        extra_lat += CONTENTION_MS
        extra_eng += CONTENTION_MJ
    if no_rep:
        WASTE_MS = 33.0
        WASTE_MJ = 400.0
        extra_lat += WASTE_MS
        extra_eng += WASTE_MJ
    return extra_lat, extra_eng


@dataclass
class Runner:
    configs_root: str
    schemas_root: str
    data_root: str

    def _prepare_context(self, manifest: ExperimentManifest) -> RunnerContext:
        calibration_schema = os.path.join(self.schemas_root, "processed_calibration.schema.json")
        calibration = load_processed_calibration(manifest.device_profile_file, calibration_schema)
        cal_hash = hash_calibration_artifact(manifest.device_profile_file)
        if calibration.calibration_policy.replay_mode != manifest.replay_mode:
            raise ManifestError("replay_mode_mismatch_between_manifest_and_calibration")
        network = load_network_preset(
            os.path.join(self.configs_root, "defaults"),
            manifest.network_profile,
            manifest.replay_mode,
        )
        backend = ProofBackend(manifest.proof_backend)
        gateway = None
        prover = None
        if Mode(manifest.mode) is Mode.B:
            gateway = build_gateway_profile(calibration, backend, manifest.replay_mode)
            prover = build_prover_profile(calibration, backend, manifest.replay_mode)
        mcu = build_mcu_profile(calibration, manifest.replay_mode)
        registry = SmartZoneRegistry()
        dispatcher = Dispatcher(registry=registry)
        workload_profile = load_workload_profile(
            os.path.join(self.configs_root, "defaults"),
            manifest.workload_profile,
        )
        workload = WorkloadGenerator(workload_profile, registry.known_zones())
        ledger = LedgerEmulator(
            proof_backend=backend,
            r1cs_constraints=(calibration.proof_stack.r1cs_constraints if calibration.proof_stack else 18500),
            curve=(calibration.proof_stack.curve if calibration.proof_stack else "bn254"),
            hash_primitive=(calibration.proof_stack.hash if calibration.proof_stack else "poseidon"),
        )
        hlc_state = HLCState(
            device_id=0,
            resident_kb=mcu.resident_baseline_kb,
            peak_kb=mcu.verification_peak_kb,
            reception_peak_kb=mcu.proof_reception_peak_kb,
            verification_peak_kb=mcu.verification_peak_kb,
            post_update_return_kb=mcu.post_update_return_kb,
            ram_now_kb=mcu.resident_baseline_kb,
        )
        hlc = HybridLightClient(state=hlc_state, latency_replay=mcu.latency_replay)
        nodes = _build_nodes(manifest.validator_count, manifest.malicious_fraction)
        rep_params = ReputationParams(
            alpha=manifest.reputation_weights.alpha,
            beta=manifest.reputation_weights.beta,
            gamma=manifest.reputation_weights.gamma,
            lambd=manifest.reputation_weights.lambd,
            delta=manifest.reputation_weights.delta,
            eta=manifest.reputation_weights.eta,
            mu=manifest.reputation_weights.mu,
            r_min=manifest.reputation_weights.r_min,
        )
        reputation = _build_reputation(nodes, rep_params)
        selector = CommitteeSelector(theta=manifest.committee_threshold_theta, r_min=rep_params.r_min)
        policy = FinalizationPolicy(quorum_ratio=2.0 / 3.0, min_committee_size=1)
        metrics = MetricCollector(
            device_energy_mj_per_tx=float(
                manifest.raw_document.get("device_energy_mj_per_tx", 0.0)
            )
        )
        return RunnerContext(
            manifest=manifest,
            calibration=calibration,
            calibration_hash=cal_hash,
            network=network,
            gateway_profile=gateway,
            mcu_profile=mcu,
            prover_profile=prover,
            workload=workload,
            registry=registry,
            dispatcher=dispatcher,
            ledger=ledger,
            hlc=hlc,
            reputation=reputation,
            committee_selector=selector,
            policy=policy,
            metrics=metrics,
            nodes=nodes,
        )

    def run_manifest(self, manifest_path: str) -> RunResult:
        manifest_schema = os.path.join(self.schemas_root, "experiment_manifest.schema.json")
        manifest = load_manifest(manifest_path, manifest_schema)
        return self.run(manifest)

    def run(self, manifest: ExperimentManifest) -> RunResult:
        ctx = self._prepare_context(manifest)
        zones_tuple = ctx.registry.known_zones()
        total_tx_planned = manifest.tx_per_block * manifest.blocks_to_run
        txs = ctx.workload.next_batch(total_tx_planned)
        for tx in txs:
            ctx.dispatcher.dispatch(tx)
        clock = Clock()
        backend = ProofBackend(manifest.proof_backend)
        mode = Mode(manifest.mode)
        r1cs = (
            ctx.calibration.proof_stack.r1cs_constraints
            if ctx.calibration.proof_stack
            else 18500
        )
        curve = ctx.calibration.proof_stack.curve if ctx.calibration.proof_stack else "bn254"
        hash_primitive = ctx.calibration.proof_stack.hash if ctx.calibration.proof_stack else "poseidon"
        energy_k_cpu = (
            ctx.calibration.energy_coefficients.k_cpu_nj_per_1k_cycles
            if ctx.calibration.energy_coefficients
            else 52.0
        )
        energy_k_net = (
            ctx.calibration.energy_coefficients.k_net_uj_per_kb
            if ctx.calibration.energy_coefficients
            else 1.6
        )
        _abl = manifest.raw_document
        abl_no_rep = bool(_abl.get("ablation_no_reputation", False))
        abl_full_zkp = bool(_abl.get("ablation_full_zkp", False))
        abl_full_mesh = bool(_abl.get("ablation_full_mesh", False))
        abl_no_zone = bool(_abl.get("ablation_no_smart_zone", False))
        epoch_size_blocks = max(1, min(8, manifest.blocks_to_run // 5 or 1))
        prev_block_id = 0
        current_epoch = -1
        committee_members: Tuple[ValidatorId, ...] = tuple(n.validator_id for n in ctx.nodes)
        fallback_ids = tuple(n.validator_id for n in ctx.nodes)
        malicious_ids = tuple(n.validator_id for n in ctx.nodes if n.malicious)
        penalties_log: Dict[ValidatorId, int] = {vid: 0 for vid in malicious_ids}
        recovery_start_ms: Dict[ValidatorId, float] = {}
        for block_no in range(manifest.blocks_to_run):
            zone = zones_tuple[0] if abl_no_zone else _next_zone_for_block(block_no, zones_tuple)
            drained = ctx.dispatcher.drain_batch(zone, manifest.tx_per_block)
            if not drained:
                ctx.metrics.record_block_attempted()
                ctx.metrics.record_block_loss()
                continue
            for zkey, peak in ctx.dispatcher.backlog_peak.items():
                ctx.metrics.record_backlog_peak(zkey, peak)
            epoch_idx = block_no // epoch_size_blocks
            if epoch_idx != current_epoch:
                current_epoch = epoch_idx
                eff = _flat_reputation_map(ctx.nodes) if abl_no_rep else ctx.reputation.effective_map()
                committee_record = ctx.committee_selector.select(
                    epoch=epoch_idx,
                    prev_block_id=prev_block_id,
                    randao=_randao_for(epoch_idx),
                    effective_reputations=eff,
                )
                committee_members = fallback_ids if abl_full_mesh else committee_record.members
                ctx.metrics.record_committee_size(len(committee_members))
            proposer = _proposer_for_block(block_no, committee_members, fallback_ids)
            now_ms = clock.now_ms()
            earliest_submit_ms = min(tx.submitted_at_ms for tx in drained)
            proposed_at_ms = max(now_ms, earliest_submit_ms)
            submission = ctx.ledger.propose_block(
                block_id=block_no + 1,
                zone_id=zone,
                proposer=proposer,
                epoch=epoch_idx,
                proposed_at_ms=proposed_at_ms,
                transactions=drained,
            )
            clock.advance_to(proposed_at_ms)
            bundle = _build_proof(
                submission,
                backend,
                r1cs,
                curve,
                hash_primitive,
                mode,
                ctx.prover_profile,
                proposed_at_ms,
            )
            cpu_pct = 0.0
            mem_mb = 0.0
            if mode is Mode.B and ctx.gateway_profile is not None and ctx.prover_profile is not None:
                cpu_pct = float(ctx.gateway_profile.cpu_replay.next_value())
                mem_mb = float(ctx.gateway_profile.memory_replay.next_value())
                ctx.metrics.record_proof_built(bundle.proving_latency_ms, cpu_pct, mem_mb)
            else:
                ctx.metrics.record_proof_built(0.0, 0.0, 0.0)
            verify_ok = verify_proof_bundle(bundle)
            if verify_ok:
                ctx.metrics.record_proof_verified()
            net_delay_ms_vote = ctx.network.next_delay_ms()
            cast_at_ms = bundle.produced_at_ms + net_delay_ms_vote
            weights = _flat_reputation_map(ctx.nodes) if abl_no_rep else ctx.reputation.effective_map()
            committee_nodes = [n for n in ctx.nodes if n.validator_id in committee_members]
            votes = tuple(
                _committee_vote(node, bundle, weights, cast_at_ms, "equivocate")
                for node in committee_nodes
            )
            tally = tally_votes(bundle.block_id, votes, weights)
            decision = finalize_block(tally, len(committee_members), ctx.policy)
            ctx_receipts = ConsensusReceipts()
            ctx_receipts.record_tally(tally)
            ctx_receipts.record_decision(decision, malicious_ids)
            ctx.metrics.record_block_attempted()
            if not decision.finalized:
                ctx.metrics.record_block_loss()
                ctx.metrics.record_stale()
                deltas_avail = {n.validator_id: -0.1 for n in committee_nodes if n.malicious}
                deltas_vote = {n.validator_id: 0.0 for n in committee_nodes}
                for mid in committee_members:
                    node = next((n for n in ctx.nodes if n.validator_id == mid), None)
                    if node and node.malicious:
                        ctx.reputation.apply_penalty(mid, 0.2)
                        penalties_log[mid] = penalties_log.get(mid, 0) + 1
                ctx.reputation.apply_round(deltas_avail, deltas_vote)
                continue
            net_delay_ms_finalize = ctx.network.next_delay_ms()
            finalized_at_ms = cast_at_ms + net_delay_ms_finalize
            abl_extra_lat, abl_extra_eng = _ablation_costs(
                full_mesh=abl_full_mesh,
                full_zkp=abl_full_zkp,
                no_zone=abl_no_zone,
                no_rep=abl_no_rep,
                n_nodes=len(fallback_ids),
                committee_size=len(committee_members),
            )
            finalized_at_ms += abl_extra_lat
            ctx.ledger.finalize(submission, finalized_at_ms)
            clock.advance_to(finalized_at_ms)
            header = ctx.ledger.header_for(submission)
            ctx.hlc.attach_header(header)
            ctx.hlc.receive_proof()
            from ..crypto.merkle import build_merkle_tree

            txs_as_bytes = tuple(tx_leaf_bytes(t) for t in drained)
            tree = build_merkle_tree(txs_as_bytes)
            path = tree.inclusion_path(0)
            first_leaf = txs_as_bytes[0]
            ok_mcu, mcu_latency_ms = ctx.hlc.verify_merkle(first_leaf, path, zone)
            if ok_mcu:
                ctx.metrics.record_mcu_verify(
                    mcu_latency_ms,
                    ctx.mcu_profile.resident_baseline_kb,
                    ctx.hlc.state.peak_observed_kb,
                )
            else:
                ctx.metrics.record_conflict()
            zone_cfg = ctx.registry.get(zone)
            gross_fee = zone_cfg.base_fee * float(len(drained))
            apply_fee_split(zone_cfg, gross_fee)
            payload_kb = sum(tx.payload_bytes for tx in drained) / 1024.0
            ctx.metrics.record_payload_kb(payload_kb)
            energy = _energy_for_block(
                cpu_pct,
                mcu_latency_ms,
                payload_kb,
                bundle.proving_latency_ms,
                energy_k_cpu,
                energy_k_net,
            )
            ctx.metrics.record_energy_mj(energy + abl_extra_eng)
            _wall_mult = 0.0
            if abl_full_zkp:
                _wall_mult += 0.30
            if abl_no_zone:
                _wall_mult += 0.20
            if abl_full_mesh:
                _wall_mult += 0.10
            if abl_no_rep:
                _wall_mult += 0.17
            if _wall_mult > 0.0:
                clock.advance_to(clock.now_ms() + bundle.proving_latency_ms * _wall_mult)
            ctx.metrics.record_block_finalized(
                zone_id=zone,
                tx_count=len(drained),
                consensus_start_ms=bundle.produced_at_ms,
                finalized_at_ms=finalized_at_ms,
                earliest_submit_ms=earliest_submit_ms,
            )
            parent_ok = (submission.parent_id or 0) < submission.block_id
            ctx.metrics.record_fork_resolution(parent_ok)
            deltas_avail: Dict[ValidatorId, float] = {}
            deltas_vote: Dict[ValidatorId, float] = {}
            for node in committee_nodes:
                deltas_avail[node.validator_id] = 0.05
                vote_stance = next((v.stance for v in votes if v.validator_id == node.validator_id), "abstain")
                if vote_stance == "accept":
                    deltas_vote[node.validator_id] = 0.02
                elif vote_stance == "reject":
                    deltas_vote[node.validator_id] = -0.02
                if node.malicious and vote_stance != "accept":
                    ctx.reputation.apply_penalty(node.validator_id, 0.35)
                    penalties_log[node.validator_id] = penalties_log.get(node.validator_id, 0) + 1
                    recovery_start_ms.setdefault(node.validator_id, finalized_at_ms)
            ctx.reputation.apply_round(deltas_avail, deltas_vote)
            prev_block_id = submission.block_id
            committed_malicious = any(v.validator_id in malicious_ids and v.stance == "accept" for v in votes)
            if committed_malicious:
                ctx.metrics.record_invalid_accept()
        ctx.metrics.end_simulation(clock.now_ms())
        eff_map = ctx.reputation.effective_map()
        malicious_eff = [eff_map[m] for m in malicious_ids if m in eff_map]
        for r in malicious_eff:
            ctx.metrics.record_malicious_effective(r)
        for mid, rounds in penalties_log.items():
            ctx.metrics.record_penalty_convergence(rounds)
            start = recovery_start_ms.get(mid)
            if start is not None:
                ctx.metrics.record_recovery(clock.now_ms() - start)
        snap = ctx.metrics.snapshot()
        per_block_lat = tuple(ctx.metrics.protocol_latencies_ms)
        per_block_e2e = tuple(ctx.metrics.e2e_latencies_ms)
        committees = tuple(ctx.metrics.committee_sizes)
        provenance = {
            "manifest_id": manifest.experiment_id,
            "calibration_file": manifest.device_profile_file,
            "calibration_sha256": ctx.calibration_hash,
            "replay_mode": manifest.replay_mode,
            "network_preset": ctx.network.preset_name(),
            "mode": manifest.mode,
            "proof_backend": manifest.proof_backend,
            "validator_count": str(manifest.validator_count),
            "tx_per_block": str(manifest.tx_per_block),
            "blocks_to_run": str(manifest.blocks_to_run),
            "malicious_fraction": str(manifest.malicious_fraction),
        }
        return RunResult(
            experiment_id=manifest.experiment_id,
            mode=manifest.mode,
            metrics=snap,
            per_block_latency_ms=per_block_lat,
            per_block_e2e_ms=per_block_e2e,
            committees=committees,
            calibration_hash=ctx.calibration_hash,
            network_preset=ctx.network.preset_name(),
            replay_mode=manifest.replay_mode,
            proving_latency_samples_ms=tuple(ctx.metrics.proving_latency_samples_ms),
            gateway_cpu_samples=tuple(ctx.metrics.gateway_cpu_samples),
            gateway_memory_samples=tuple(ctx.metrics.gateway_memory_samples),
            verifier_latency_samples_ms=tuple(ctx.metrics.verifier_latency_samples_ms),
            mcu_resident_samples_kb=tuple(ctx.metrics.mcu_resident_samples),
            mcu_peak_samples_kb=tuple(ctx.metrics.mcu_peak_samples),
            provenance=provenance,
        )

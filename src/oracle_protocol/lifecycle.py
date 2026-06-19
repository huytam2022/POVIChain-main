from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from povichain.ingestion.trace_loader import TraceReplay

from .dvn import DvnVerification, OracleVerifierNetwork
from .endpoint import OracleDestinationEndpoint, OracleSourceEndpoint
from .executor import L0ExecutorOutcome
from .message import OracleMessage, L0MessageEnvelope
from .metrics_collector import OracleMetricsCollector


@dataclass
class L0LifecycleOutcome:
    message: OracleMessage
    submitted_at_ms: float
    formatted_at_ms: float
    dvn_dispatched_at_ms: float
    verified_at_ms: float
    committed_at_ms: float
    executed_at_ms: float
    wait_due_to_nonce_ms: float
    payload_kb: float
    dvn_fanout: int
    quorum_size: int
    required_quorum: int


@dataclass
class OraclePacketLifecycle:
    source_endpoint: OracleSourceEndpoint
    destination_endpoint: OracleDestinationEndpoint
    dvn: OracleVerifierNetwork
    metrics: OracleMetricsCollector
    source_cpu_replay: TraceReplay
    dvn_cpu_replay: TraceReplay
    destination_cpu_replay: TraceReplay
    k_cpu_nj_per_1k_cycles: float
    k_net_uj_per_kb: float
    k_dvn_verify_mj_per_vote: float
    k_commit_verification_mj: float
    dvn_verification_payload_bytes: int = 512
    _outcomes: List[L0LifecycleOutcome] = field(default_factory=list)

    def submit_message(
        self,
        counterparty_chain: str,
        counterparty_oapp: str,
        sender: int,
        payload_bytes: int,
        submitted_at_ms: float,
    ) -> L0MessageEnvelope:
        envelope = self.source_endpoint.send(
            counterparty_chain=counterparty_chain,
            counterparty_oapp=counterparty_oapp,
            sender=sender,
            payload_bytes=payload_bytes,
            submitted_at_ms=submitted_at_ms,
        )
        self.metrics.record_submitted()
        self.metrics.record_formatted()
        source_cpu_pct = float(self.source_cpu_replay.next_value())
        source_runtime_ms = max(0.0, envelope.formatted_at_ms - envelope.message.submitted_at_ms)
        self.metrics.record_cpu_sample(source_cpu_pct, source_runtime_ms)
        payload_kb = envelope.message.payload_bytes / 1024.0
        self.metrics.record_energy(
            self._cpu_energy_mj(source_cpu_pct, source_runtime_ms)
            + self._net_energy_mj(payload_kb)
        )
        self.dvn.enqueue(envelope)
        self.metrics.record_verification_queue_depth(self.dvn.pending_depth())
        return envelope

    def dispatch_verification(self, dispatched_at_ms: float) -> Tuple[L0LifecycleOutcome, ...]:
        verifications = self.dvn.verify_pending(dispatched_at_ms=dispatched_at_ms)
        self.metrics.record_verification_queue_depth(self.dvn.pending_depth())
        outcomes: List[L0LifecycleOutcome] = []
        dvn_cpu_pct = float(self.dvn_cpu_replay.next_value())
        dvn_batch_wall_ms = 0.0
        dvn_payload_kb = 0.0
        for ver in verifications:
            attestation = ver.attestation
            for vote in ver.votes:
                self.metrics.record_verification_vote()
            self.metrics.record_quorum_reached()
            committed_at_ms = self.destination_endpoint.commit_verification(
                envelope=ver.envelope,
                attestation=attestation,
                verified_at_ms=attestation.last_vote_at_ms,
            )
            commit_delay_ms = max(0.0, committed_at_ms - attestation.last_vote_at_ms)
            self.metrics.record_commit_verification(delay_ms=commit_delay_ms)
            self.metrics.record_energy(
                self.k_dvn_verify_mj_per_vote * float(len(ver.votes))
            )
            self.metrics.record_energy(self.k_commit_verification_mj)
            envelope_wall_ms = float(attestation.last_vote_at_ms - ver.dispatched_at_ms)
            if envelope_wall_ms > dvn_batch_wall_ms:
                dvn_batch_wall_ms = envelope_wall_ms
            dvn_payload_kb += float(self.dvn_verification_payload_bytes) / 1024.0
            outcomes.append(
                L0LifecycleOutcome(
                    message=ver.envelope.message,
                    submitted_at_ms=ver.envelope.message.submitted_at_ms,
                    formatted_at_ms=ver.envelope.formatted_at_ms,
                    dvn_dispatched_at_ms=ver.dispatched_at_ms,
                    verified_at_ms=attestation.last_vote_at_ms,
                    committed_at_ms=committed_at_ms,
                    executed_at_ms=0.0,
                    wait_due_to_nonce_ms=0.0,
                    payload_kb=ver.envelope.message.payload_bytes / 1024.0,
                    dvn_fanout=self.dvn.fanout(),
                    quorum_size=attestation.quorum_size,
                    required_quorum=attestation.required_quorum,
                )
            )
        self.metrics.record_cpu_sample(dvn_cpu_pct, dvn_batch_wall_ms)
        self.metrics.record_energy(
            self._cpu_energy_mj(dvn_cpu_pct, dvn_batch_wall_ms)
            + self._net_energy_mj(dvn_payload_kb * float(self.dvn.fanout()))
        )
        return tuple(outcomes)

    def drain_execution(self) -> Tuple[L0LifecycleOutcome, ...]:
        executor_outcomes = self.destination_endpoint.drain_executor()
        if not executor_outcomes:
            return ()
        dest_cpu_pct = float(self.destination_cpu_replay.next_value())
        dest_runtime_ms = 0.0
        dest_payload_kb = 0.0
        updated: List[L0LifecycleOutcome] = []
        for exec_outcome in executor_outcomes:
            path_key = (
                exec_outcome.message.src_chain_id
                + ":"
                + exec_outcome.message.src_oapp
                + "->"
                + exec_outcome.message.dst_chain_id
                + ":"
                + exec_outcome.message.dst_oapp
            )
            self.metrics.record_execution(
                path_key=path_key,
                submitted_at_ms=exec_outcome.message.submitted_at_ms,
                committed_at_ms=exec_outcome.committed_at_ms,
                executed_at_ms=exec_outcome.executed_at_ms,
                wait_due_to_nonce_ms=exec_outcome.wait_due_to_nonce_ms,
                dvn_fanout=exec_outcome.dvn_fanout,
                payload_kb=exec_outcome.payload_kb,
            )
            dest_runtime_ms += max(
                0.0,
                (exec_outcome.executed_at_ms - exec_outcome.committed_at_ms)
                - exec_outcome.wait_due_to_nonce_ms,
            )
            dest_payload_kb += exec_outcome.payload_kb
            out = L0LifecycleOutcome(
                message=exec_outcome.message,
                submitted_at_ms=exec_outcome.message.submitted_at_ms,
                formatted_at_ms=exec_outcome.message.submitted_at_ms,
                dvn_dispatched_at_ms=exec_outcome.verified_at_ms,
                verified_at_ms=exec_outcome.verified_at_ms,
                committed_at_ms=exec_outcome.committed_at_ms,
                executed_at_ms=exec_outcome.executed_at_ms,
                wait_due_to_nonce_ms=exec_outcome.wait_due_to_nonce_ms,
                payload_kb=exec_outcome.payload_kb,
                dvn_fanout=exec_outcome.dvn_fanout,
                quorum_size=exec_outcome.attestation.quorum_size,
                required_quorum=exec_outcome.attestation.required_quorum,
            )
            updated.append(out)
            self._outcomes.append(out)
        self.metrics.record_cpu_sample(dest_cpu_pct, dest_runtime_ms)
        self.metrics.record_energy(
            self._cpu_energy_mj(dest_cpu_pct, dest_runtime_ms)
            + self._net_energy_mj(dest_payload_kb)
        )
        return tuple(updated)

    def outcomes(self) -> Tuple[L0LifecycleOutcome, ...]:
        return tuple(self._outcomes)

    def _cpu_energy_mj(self, cpu_pct: float, runtime_ms: float) -> float:
        cpu_cycles_1k = max(0.0, runtime_ms) * (cpu_pct / 100.0)
        cpu_nj = cpu_cycles_1k * self.k_cpu_nj_per_1k_cycles
        return cpu_nj / 1_000_000.0

    def _net_energy_mj(self, payload_kb: float) -> float:
        net_uj = payload_kb * self.k_net_uj_per_kb
        return net_uj / 1000.0

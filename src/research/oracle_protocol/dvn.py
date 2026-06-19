from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from povichain.ingestion.trace_loader import TraceReplay

from .message import L0MessageEnvelope, L0VerificationVote, OracleAttestation


@dataclass
class OracleVerifier:
    verifier_id: str
    verify_latency_replay: TraceReplay
    network_rtt_replay: TraceReplay
    _verifications: int = 0
    _total_latency_ms: float = 0.0

    def verify(
        self,
        envelope: L0MessageEnvelope,
        arrived_at_ms: float,
    ) -> L0VerificationVote:
        verify_latency_ms = float(self.verify_latency_replay.next_value())
        network_rtt_ms = float(self.network_rtt_replay.next_value())
        vote_latency_ms = max(0.0, verify_latency_ms) + max(0.0, network_rtt_ms)
        cast_at_ms = arrived_at_ms + vote_latency_ms
        self._verifications += 1
        self._total_latency_ms += vote_latency_ms
        return L0VerificationVote(
            verifier_id=self.verifier_id,
            packet_hash=envelope.packet_hash,
            cast_at_ms=cast_at_ms,
            latency_ms=vote_latency_ms,
        )

    def verifications(self) -> int:
        return self._verifications


@dataclass
class DvnVerification:
    envelope: L0MessageEnvelope
    votes: Tuple[L0VerificationVote, ...]
    attestation: OracleAttestation
    dispatched_at_ms: float


@dataclass
class OracleVerifierNetwork:
    verifiers: Tuple[OracleVerifier, ...]
    required_quorum: int
    total_verifiers: int
    _pending: List[L0MessageEnvelope] = field(default_factory=list)
    _attestations_by_hash: Dict[bytes, OracleAttestation] = field(default_factory=dict)
    _rounds: int = 0
    _votes_cast: int = 0

    def __post_init__(self) -> None:
        if self.required_quorum <= 0:
            raise ValueError("oracle_dvn_quorum_must_be_positive")
        if self.total_verifiers <= 0:
            raise ValueError("oracle_dvn_total_verifiers_must_be_positive")
        if self.required_quorum > self.total_verifiers:
            raise ValueError("oracle_dvn_quorum_exceeds_total_verifiers")
        if len(self.verifiers) != self.total_verifiers:
            raise ValueError("oracle_dvn_verifier_count_mismatch")

    def enqueue(self, envelope: L0MessageEnvelope) -> int:
        self._pending.append(envelope)
        return len(self._pending)

    def pending_depth(self) -> int:
        return len(self._pending)

    def verify_pending(self, dispatched_at_ms: float) -> Tuple[DvnVerification, ...]:
        outputs: List[DvnVerification] = []
        while self._pending:
            envelope = self._pending.pop(0)
            self._rounds += 1
            votes: List[L0VerificationVote] = []
            for verifier in self.verifiers:
                vote = verifier.verify(envelope=envelope, arrived_at_ms=dispatched_at_ms)
                votes.append(vote)
                self._votes_cast += 1
            sorted_votes = sorted(votes, key=lambda v: v.cast_at_ms)
            quorum_votes = sorted_votes[: self.required_quorum]
            last_vote_at_ms = quorum_votes[-1].cast_at_ms
            committed_ids = tuple(v.verifier_id for v in quorum_votes)
            attestation = OracleAttestation(
                packet_hash=envelope.packet_hash,
                committed_verifier_ids=committed_ids,
                quorum_size=len(committed_ids),
                required_quorum=self.required_quorum,
                last_vote_at_ms=last_vote_at_ms,
                committed_at_ms=last_vote_at_ms,
            )
            self._attestations_by_hash[envelope.packet_hash] = attestation
            outputs.append(
                DvnVerification(
                    envelope=envelope,
                    votes=tuple(sorted_votes),
                    attestation=attestation,
                    dispatched_at_ms=dispatched_at_ms,
                )
            )
        return tuple(outputs)

    def attestation_for(self, packet_hash: bytes) -> OracleAttestation:
        return self._attestations_by_hash[packet_hash]

    def rounds(self) -> int:
        return self._rounds

    def votes_cast(self) -> int:
        return self._votes_cast

    def fanout(self) -> int:
        return self.total_verifiers

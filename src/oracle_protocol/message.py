from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class OracleMessage:
    src_chain_id: str
    dst_chain_id: str
    src_oapp: str
    dst_oapp: str
    nonce: int
    payload_bytes: int
    sender: int
    submitted_at_ms: float
    guid: bytes


@dataclass(frozen=True)
class L0MessageEnvelope:
    message: OracleMessage
    packet_header_bytes: int
    packet_bytes: int
    packet_hash: bytes
    formatted_at_ms: float


@dataclass(frozen=True)
class L0VerificationVote:
    verifier_id: str
    packet_hash: bytes
    cast_at_ms: float
    latency_ms: float


@dataclass(frozen=True)
class OracleAttestation:
    packet_hash: bytes
    committed_verifier_ids: Tuple[str, ...]
    quorum_size: int
    required_quorum: int
    last_vote_at_ms: float
    committed_at_ms: float


@dataclass(frozen=True)
class L0ExecutionResult:
    message: OracleMessage
    envelope: L0MessageEnvelope
    attestation: OracleAttestation
    verified_at_ms: float
    committed_at_ms: float
    executed_at_ms: float
    wait_due_to_nonce_ms: float
    dvn_fanout: int
    payload_kb: float

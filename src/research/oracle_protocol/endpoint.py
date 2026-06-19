import hashlib
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .channel_state import OracleChannelState
from .dvn import OracleVerifierNetwork
from .executor import OracleExecutor, L0ExecutorOutcome
from .message import OracleMessage, L0MessageEnvelope, OracleAttestation
from .message_lib import OracleMessageLib
from .nonce_manager import OracleNonceManager


def _guid(
    src_chain_id: str,
    dst_chain_id: str,
    src_oapp: str,
    dst_oapp: str,
    nonce: int,
    sender: int,
    payload_bytes: int,
    submitted_at_ms: float,
) -> bytes:
    h = hashlib.sha256()
    h.update(b"L0_GUID|")
    h.update(src_chain_id.encode("utf-8"))
    h.update(b"|")
    h.update(dst_chain_id.encode("utf-8"))
    h.update(b"|")
    h.update(src_oapp.encode("utf-8"))
    h.update(b"|")
    h.update(dst_oapp.encode("utf-8"))
    h.update(b"|")
    h.update(int(nonce).to_bytes(8, "big", signed=False))
    h.update(b"|")
    h.update(int(sender).to_bytes(8, "big", signed=False))
    h.update(b"|")
    h.update(int(payload_bytes).to_bytes(8, "big", signed=False))
    h.update(b"|")
    h.update(str(int(submitted_at_ms * 1000.0)).encode("utf-8"))
    return h.digest()


@dataclass(frozen=True)
class OracleEndpoint:
    chain_id: str
    oapp_identifier: str

    def path_id(self, counterparty_chain: str, counterparty_oapp: str) -> str:
        return (
            self.chain_id
            + ":"
            + self.oapp_identifier
            + "->"
            + counterparty_chain
            + ":"
            + counterparty_oapp
        )


@dataclass
class OracleSourceEndpoint:
    endpoint: OracleEndpoint
    message_lib: OracleMessageLib
    nonce_manager: OracleNonceManager
    channel_state: OracleChannelState
    _sent_messages: List[OracleMessage] = field(default_factory=list)

    def send(
        self,
        counterparty_chain: str,
        counterparty_oapp: str,
        sender: int,
        payload_bytes: int,
        submitted_at_ms: float,
    ) -> L0MessageEnvelope:
        nonce = self.nonce_manager.assign_outbound(
            src_chain=self.endpoint.chain_id,
            dst_chain=counterparty_chain,
            src_oapp=self.endpoint.oapp_identifier,
            dst_oapp=counterparty_oapp,
        )
        guid = _guid(
            src_chain_id=self.endpoint.chain_id,
            dst_chain_id=counterparty_chain,
            src_oapp=self.endpoint.oapp_identifier,
            dst_oapp=counterparty_oapp,
            nonce=nonce,
            sender=sender,
            payload_bytes=payload_bytes,
            submitted_at_ms=submitted_at_ms,
        )
        message = OracleMessage(
            src_chain_id=self.endpoint.chain_id,
            dst_chain_id=counterparty_chain,
            src_oapp=self.endpoint.oapp_identifier,
            dst_oapp=counterparty_oapp,
            nonce=nonce,
            payload_bytes=int(payload_bytes),
            sender=int(sender),
            submitted_at_ms=float(submitted_at_ms),
            guid=guid,
        )
        self.channel_state.register_outbound(message)
        envelope = self.message_lib.format_packet(message)
        self._sent_messages.append(message)
        return envelope

    def sent_messages(self) -> Tuple[OracleMessage, ...]:
        return tuple(self._sent_messages)


@dataclass
class OracleDestinationEndpoint:
    endpoint: OracleEndpoint
    message_lib: OracleMessageLib
    dvn: OracleVerifierNetwork
    executor: OracleExecutor
    channel_state: OracleChannelState
    _commit_count: int = 0

    def commit_verification(
        self,
        envelope: L0MessageEnvelope,
        attestation: OracleAttestation,
        verified_at_ms: float,
    ) -> float:
        if envelope.message.dst_chain_id != self.endpoint.chain_id:
            raise ValueError("l0_endpoint_chain_mismatch_on_commit")
        if envelope.message.dst_oapp != self.endpoint.oapp_identifier:
            raise ValueError("l0_endpoint_oapp_mismatch_on_commit")
        if envelope.packet_hash != attestation.packet_hash:
            raise ValueError("l0_endpoint_attestation_hash_mismatch")
        if attestation.quorum_size < attestation.required_quorum:
            raise ValueError("l0_endpoint_insufficient_quorum")
        commit_latency_ms = self.message_lib.next_commit_verification_latency_ms()
        committed_at_ms = verified_at_ms + max(0.0, commit_latency_ms)
        self.channel_state.record_commit_verification(envelope.message, attestation)
        self._commit_count += 1
        self.executor.enqueue_verified(
            envelope=envelope,
            attestation=attestation,
            verified_at_ms=verified_at_ms,
            committed_at_ms=committed_at_ms,
        )
        return committed_at_ms

    def drain_executor(self) -> Tuple[L0ExecutorOutcome, ...]:
        return self.executor.drain_ready(dvn_fanout=self.dvn.fanout())

    def commit_count(self) -> int:
        return self._commit_count

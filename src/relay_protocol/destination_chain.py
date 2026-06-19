import hashlib
from dataclasses import dataclass, field
from typing import Dict, Set, Tuple

from .merkle_verifier import RelayMerkleVerifier
from .packet import RelayPacket, PacketProofBundle


def _ack_digest(packet: RelayPacket, success: bool) -> bytes:
    h = hashlib.sha256()
    h.update(b"IBC_ACK|")
    h.update(str(packet.sequence).encode("utf-8"))
    h.update(b"|")
    h.update(packet.source_channel.encode("utf-8"))
    h.update(b"|")
    h.update(packet.destination_channel.encode("utf-8"))
    h.update(b"|")
    h.update(b"ok" if success else b"err")
    return h.digest()


@dataclass
class ReceiveResult:
    accepted: bool
    reason: str
    received_at_ms: float
    ack_commit_at_ms: float
    ack_digest: bytes
    sequence: int


@dataclass
class RelayDestinationChain:
    chain_id: str
    verifier: RelayMerkleVerifier
    _received_sequences: Set[int] = field(default_factory=set)
    _ack_store: Dict[int, bytes] = field(default_factory=dict)
    _receive_count: int = 0
    _replay_rejections: int = 0
    _unverified_rejections: int = 0
    _accepted_count: int = 0
    _packet_events: list = field(default_factory=list)

    def receive_packet(
        self,
        bundle: PacketProofBundle,
        received_at_ms: float,
        execute_latency_ms: float,
        ack_commit_latency_ms: float,
    ) -> ReceiveResult:
        packet = bundle.packet
        if packet.destination_channel == "" or packet.destination_port == "":
            raise ValueError("ibc_channel_or_port_missing")
        self._receive_count += 1
        if packet.sequence in self._received_sequences:
            self._replay_rejections += 1
            return ReceiveResult(
                accepted=False,
                reason="replay",
                received_at_ms=received_at_ms,
                ack_commit_at_ms=received_at_ms,
                ack_digest=b"",
                sequence=packet.sequence,
            )
        if not self.verifier.verify(bundle):
            self._unverified_rejections += 1
            return ReceiveResult(
                accepted=False,
                reason="proof_invalid_or_untrusted_header",
                received_at_ms=received_at_ms,
                ack_commit_at_ms=received_at_ms,
                ack_digest=b"",
                sequence=packet.sequence,
            )
        executed_at_ms = received_at_ms + max(0.0, execute_latency_ms)
        ack_at_ms = executed_at_ms + max(0.0, ack_commit_latency_ms)
        self._received_sequences.add(packet.sequence)
        digest = _ack_digest(packet, True)
        self._ack_store[packet.sequence] = digest
        self._accepted_count += 1
        self._packet_events.append(
            {
                "sequence": packet.sequence,
                "received_at_ms": received_at_ms,
                "executed_at_ms": executed_at_ms,
                "ack_commit_at_ms": ack_at_ms,
            }
        )
        return ReceiveResult(
            accepted=True,
            reason="ok",
            received_at_ms=executed_at_ms,
            ack_commit_at_ms=ack_at_ms,
            ack_digest=digest,
            sequence=packet.sequence,
        )

    def ack_for(self, sequence: int) -> bytes:
        return self._ack_store.get(sequence, b"")

    def has_received(self, sequence: int) -> bool:
        return sequence in self._received_sequences

    def accepted_count(self) -> int:
        return self._accepted_count

    def replay_rejections(self) -> int:
        return self._replay_rejections

    def unverified_rejections(self) -> int:
        return self._unverified_rejections

    def events(self) -> Tuple[Dict, ...]:
        return tuple(self._packet_events)

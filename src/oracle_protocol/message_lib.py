import hashlib
from dataclasses import dataclass

from povichain.ingestion.trace_loader import TraceReplay

from .message import OracleMessage, L0MessageEnvelope


def _packet_hash(
    src_chain_id: str,
    dst_chain_id: str,
    src_oapp: str,
    dst_oapp: str,
    nonce: int,
    sender: int,
    payload_bytes: int,
    submitted_at_ms: float,
    guid: bytes,
) -> bytes:
    h = hashlib.sha256()
    h.update(b"L0_PACKET|")
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
    h.update(b"|")
    h.update(guid)
    return h.digest()


@dataclass
class OracleMessageLib:
    packet_header_bytes: int
    format_latency_replay: TraceReplay
    commit_verification_latency_replay: TraceReplay
    _format_count: int = 0
    _commit_count: int = 0
    _total_format_latency_ms: float = 0.0
    _total_commit_latency_ms: float = 0.0

    def format_packet(self, message: OracleMessage) -> L0MessageEnvelope:
        format_latency = float(self.format_latency_replay.next_value())
        formatted_at_ms = message.submitted_at_ms + max(0.0, format_latency)
        packet_bytes = int(message.payload_bytes) + int(self.packet_header_bytes)
        packet_hash = _packet_hash(
            src_chain_id=message.src_chain_id,
            dst_chain_id=message.dst_chain_id,
            src_oapp=message.src_oapp,
            dst_oapp=message.dst_oapp,
            nonce=message.nonce,
            sender=message.sender,
            payload_bytes=message.payload_bytes,
            submitted_at_ms=message.submitted_at_ms,
            guid=message.guid,
        )
        self._format_count += 1
        self._total_format_latency_ms += format_latency
        return L0MessageEnvelope(
            message=message,
            packet_header_bytes=int(self.packet_header_bytes),
            packet_bytes=packet_bytes,
            packet_hash=packet_hash,
            formatted_at_ms=formatted_at_ms,
        )

    def next_commit_verification_latency_ms(self) -> float:
        latency = float(self.commit_verification_latency_replay.next_value())
        self._commit_count += 1
        self._total_commit_latency_ms += latency
        return latency

    def format_count(self) -> int:
        return self._format_count

    def commit_count(self) -> int:
        return self._commit_count

    def total_format_latency_ms(self) -> float:
        return self._total_format_latency_ms

    def total_commit_latency_ms(self) -> float:
        return self._total_commit_latency_ms

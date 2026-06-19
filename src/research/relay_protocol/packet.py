from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class RelayPacket:
    sequence: int
    source_channel: str
    destination_channel: str
    source_port: str
    destination_port: str
    sender: int
    payload_bytes: int
    submitted_at_ms: float
    commit_digest: bytes


@dataclass(frozen=True)
class PacketProofBundle:
    packet: RelayPacket
    source_block_id: int
    source_merkle_root: bytes
    source_state_root: bytes
    commit_leaf: bytes
    inclusion_path: Tuple[Tuple[bytes, bool], ...]
    produced_at_ms: float

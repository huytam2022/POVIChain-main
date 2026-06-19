import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from povichain.crypto.merkle import MerkleTree, build_merkle_tree

from .packet import RelayPacket


def _genesis_root(chain_id: str) -> bytes:
    return hashlib.sha256(b"IBC_GENESIS|" + chain_id.encode("utf-8")).digest()


def _state_root(prev_root: bytes, merkle_root: bytes, block_id: int) -> bytes:
    h = hashlib.sha256()
    h.update(b"IBC_STATE|")
    h.update(prev_root)
    h.update(merkle_root)
    h.update(block_id.to_bytes(8, "big", signed=False))
    return h.digest()


def packet_commit_leaf(packet: RelayPacket) -> bytes:
    parts = [
        b"IBC_PKT|",
        str(packet.sequence).encode("utf-8"),
        b"|",
        packet.source_channel.encode("utf-8"),
        b"|",
        packet.destination_channel.encode("utf-8"),
        b"|",
        str(packet.sender).encode("utf-8"),
        b"|",
        str(packet.payload_bytes).encode("utf-8"),
        b"|",
        packet.commit_digest,
    ]
    return b"".join(parts)


@dataclass
class SourceBlock:
    block_id: int
    chain_id: str
    merkle_root: bytes
    state_root: bytes
    parent_state_root: bytes
    packets: Tuple[RelayPacket, ...]
    proposed_at_ms: float
    committed_at_ms: float
    tree: MerkleTree


@dataclass
class RelaySourceChain:
    chain_id: str
    head_block_id: int = 0
    head_state_root: bytes = field(default=b"")
    _packet_commitments: Dict[int, RelayPacket] = field(default_factory=dict)
    _packets_by_block: Dict[int, Tuple[RelayPacket, ...]] = field(default_factory=dict)
    _blocks: Dict[int, SourceBlock] = field(default_factory=dict)
    _pending_packets: List[RelayPacket] = field(default_factory=list)
    _sequence_counter: int = 0

    def __post_init__(self) -> None:
        if not self.head_state_root:
            self.head_state_root = _genesis_root(self.chain_id)

    def next_sequence(self) -> int:
        self._sequence_counter += 1
        return self._sequence_counter

    def enqueue_packet(self, packet: RelayPacket) -> None:
        if packet.sequence in self._packet_commitments:
            raise ValueError("ibc_packet_sequence_already_used")
        self._pending_packets.append(packet)

    def pending_packet_count(self) -> int:
        return len(self._pending_packets)

    def propose_block(
        self,
        max_packets: int,
        proposed_at_ms: float,
        committed_at_ms: float,
    ) -> Optional[SourceBlock]:
        if not self._pending_packets:
            return None
        take = min(max_packets, len(self._pending_packets))
        batch = tuple(self._pending_packets[:take])
        del self._pending_packets[:take]
        leaves = tuple(packet_commit_leaf(p) for p in batch)
        tree = build_merkle_tree(leaves)
        root = tree.root()
        next_id = self.head_block_id + 1
        new_state = _state_root(self.head_state_root, root, next_id)
        block = SourceBlock(
            block_id=next_id,
            chain_id=self.chain_id,
            merkle_root=root,
            state_root=new_state,
            parent_state_root=self.head_state_root,
            packets=batch,
            proposed_at_ms=proposed_at_ms,
            committed_at_ms=committed_at_ms,
            tree=tree,
        )
        for packet in batch:
            self._packet_commitments[packet.sequence] = packet
        self._packets_by_block[next_id] = batch
        self._blocks[next_id] = block
        self.head_block_id = next_id
        self.head_state_root = new_state
        return block

    def block(self, block_id: int) -> Optional[SourceBlock]:
        return self._blocks.get(block_id)

    def commitments_for(self, block_id: int) -> Tuple[RelayPacket, ...]:
        return self._packets_by_block.get(block_id, ())

    def has_packet_commitment(self, sequence: int) -> bool:
        return sequence in self._packet_commitments

    def blocks(self) -> Tuple[SourceBlock, ...]:
        return tuple(self._blocks[bid] for bid in sorted(self._blocks.keys()))

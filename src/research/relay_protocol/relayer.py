from dataclasses import dataclass, field
from typing import List, Tuple

from povichain.ingestion.trace_loader import TraceReplay

from .packet import RelayPacket, PacketProofBundle
from .source_chain import RelaySourceChain, SourceBlock, packet_commit_leaf


@dataclass
class RelayBatchResult:
    bundles: Tuple[PacketProofBundle, ...]
    dispatched_at_ms: float
    bundle_ready_at_ms: float
    delivered_at_ms: float
    rpc_rtt_ms: float
    processing_ms: float
    header_update_block: int
    header_verify_ms: float
    header_applied_at_ms: float


@dataclass
class RelayAgent:
    relayer_id: str
    concurrent_packets: int
    rpc_rtt_replay: TraceReplay
    processing_ms_per_packet_replay: TraceReplay
    header_verify_ms_replay: TraceReplay
    ack_return_ms_replay: TraceReplay
    _observed_blocks: List[int] = field(default_factory=list)
    _pending_bundles: List[PacketProofBundle] = field(default_factory=list)
    _delivered_bundles: int = 0
    _headers_updated: int = 0
    _cpu_busy_ms: float = 0.0
    _backlog_peak: int = 0
    _batches: int = 0
    _last_dispatch_end_ms: float = 0.0

    def observe_source_block(self, block: SourceBlock) -> None:
        if block.block_id in self._observed_blocks:
            return
        self._observed_blocks.append(block.block_id)
        for idx, packet in enumerate(block.packets):
            leaf = packet_commit_leaf(packet)
            path = block.tree.inclusion_path(idx)
            bundle = PacketProofBundle(
                packet=packet,
                source_block_id=block.block_id,
                source_merkle_root=block.merkle_root,
                source_state_root=block.state_root,
                commit_leaf=leaf,
                inclusion_path=path,
                produced_at_ms=block.committed_at_ms,
            )
            self._pending_bundles.append(bundle)
        if len(self._pending_bundles) > self._backlog_peak:
            self._backlog_peak = len(self._pending_bundles)

    def backlog(self) -> int:
        return len(self._pending_bundles)

    def backlog_peak(self) -> int:
        return self._backlog_peak

    def headers_updated(self) -> int:
        return self._headers_updated

    def cpu_busy_ms(self) -> float:
        return self._cpu_busy_ms

    def batches_run(self) -> int:
        return self._batches

    def delivered_count(self) -> int:
        return self._delivered_bundles

    def last_dispatch_end_ms(self) -> float:
        return self._last_dispatch_end_ms

    def dispatch_batch(
        self,
        dispatch_at_ms: float,
        source_chain: RelaySourceChain,
    ) -> RelayBatchResult:
        if not self._pending_bundles:
            raise RuntimeError("ibc_relayer_no_pending_bundles")
        take = min(self.concurrent_packets, len(self._pending_bundles))
        batch = tuple(self._pending_bundles[:take])
        del self._pending_bundles[:take]
        rpc_rtt = float(self.rpc_rtt_replay.next_value())
        per_packet_ms = float(self.processing_ms_per_packet_replay.next_value())
        processing_ms = per_packet_ms * float(take)
        header_verify_ms = float(self.header_verify_ms_replay.next_value())
        latest_block = batch[-1].source_block_id
        header_applied_at_ms = dispatch_at_ms + rpc_rtt + header_verify_ms
        bundle_ready_at_ms = header_applied_at_ms + processing_ms
        delivered_at_ms = bundle_ready_at_ms + rpc_rtt
        self._cpu_busy_ms += processing_ms + header_verify_ms
        self._delivered_bundles += take
        self._headers_updated += 1
        self._batches += 1
        self._last_dispatch_end_ms = delivered_at_ms
        return RelayBatchResult(
            bundles=batch,
            dispatched_at_ms=dispatch_at_ms,
            bundle_ready_at_ms=bundle_ready_at_ms,
            delivered_at_ms=delivered_at_ms,
            rpc_rtt_ms=rpc_rtt,
            processing_ms=processing_ms,
            header_update_block=latest_block,
            header_verify_ms=header_verify_ms,
            header_applied_at_ms=header_applied_at_ms,
        )

    def return_ack(
        self,
        ack_commit_at_ms: float,
    ) -> float:
        rtt = float(self.ack_return_ms_replay.next_value())
        self._cpu_busy_ms += rtt * 0.1
        return ack_commit_at_ms + rtt

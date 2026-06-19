from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from povichain.ingestion.trace_loader import TraceReplay

from .destination_chain import RelayDestinationChain
from .light_client import RelayLightClient
from .metrics_collector import RelayMetricsCollector
from .packet import RelayPacket
from .relayer import RelayAgent, RelayBatchResult
from .source_chain import RelaySourceChain, SourceBlock


@dataclass
class PacketLifecycleOutcome:
    sequence: int
    channel: str
    submitted_at_ms: float
    source_committed_at_ms: float
    relayer_delivered_at_ms: float
    destination_received_at_ms: float
    destination_executed_at_ms: float
    ack_committed_at_ms: float
    ack_returned_at_ms: float
    accepted: bool
    payload_kb: float


@dataclass
class RelayPacketLifecycle:
    source_chain: RelaySourceChain
    destination_chain: RelayDestinationChain
    light_client: RelayLightClient
    relayer: RelayAgent
    metrics: RelayMetricsCollector
    receive_exec_ms_replay: TraceReplay
    ack_commit_ms_replay: TraceReplay
    source_cpu_replay: TraceReplay
    destination_cpu_replay: TraceReplay
    relayer_cpu_replay: TraceReplay
    k_cpu_nj_per_1k_cycles: float
    k_net_uj_per_kb: float
    k_header_mj_per_update: float
    k_verify_mj_per_proof: float
    _submit_times: Dict[int, float] = field(default_factory=dict)
    _outcomes: List[PacketLifecycleOutcome] = field(default_factory=list)

    def submit_packet(self, packet: RelayPacket) -> None:
        self.source_chain.enqueue_packet(packet)
        self._submit_times[packet.sequence] = packet.submitted_at_ms
        self.metrics.record_packet_submitted()

    def commit_source_block(
        self,
        max_packets_per_block: int,
        proposed_at_ms: float,
        committed_at_ms: float,
    ) -> SourceBlock:
        block = self.source_chain.propose_block(
            max_packets=max_packets_per_block,
            proposed_at_ms=proposed_at_ms,
            committed_at_ms=committed_at_ms,
        )
        if block is None:
            raise RuntimeError("ibc_source_block_empty")
        self.metrics.record_source_committed(len(block.packets))
        cpu_pct = float(self.source_cpu_replay.next_value())
        runtime_ms = max(0.0, committed_at_ms - proposed_at_ms)
        self.metrics.record_cpu_sample(cpu_pct, runtime_ms)
        payload_kb = sum(p.payload_bytes for p in block.packets) / 1024.0
        block_energy = self._source_block_energy(
            cpu_pct=cpu_pct,
            runtime_ms=runtime_ms,
            payload_kb=payload_kb,
        )
        self.metrics.record_energy(block_energy)
        self.relayer.observe_source_block(block)
        return block

    def relay_and_deliver(
        self,
        dispatch_at_ms: float,
    ) -> RelayBatchResult:
        batch = self.relayer.dispatch_batch(
            dispatch_at_ms=dispatch_at_ms,
            source_chain=self.source_chain,
        )
        self.light_client.apply_header_update(
            source_block=self.source_chain.block(batch.header_update_block),
            verify_latency_ms=batch.header_verify_ms,
            applied_at_ms=batch.header_applied_at_ms,
        )
        self.metrics.record_header_update(batch.header_verify_ms)
        self.metrics.record_relayer_batch(
            delivered=len(batch.bundles),
            backlog_after=self.relayer.backlog(),
        )
        cpu_pct = float(self.relayer_cpu_replay.next_value())
        runtime_ms = max(0.0, batch.delivered_at_ms - batch.dispatched_at_ms)
        self.metrics.record_cpu_sample(cpu_pct, runtime_ms)
        payload_kb = sum(b.packet.payload_bytes for b in batch.bundles) / 1024.0
        self.metrics.record_energy(
            self._relayer_energy(cpu_pct=cpu_pct, runtime_ms=runtime_ms, payload_kb=payload_kb)
        )
        self.metrics.record_energy(self.k_header_mj_per_update)
        return batch

    def receive_batch(
        self,
        batch: RelayBatchResult,
        receive_start_ms: float = None,
    ) -> Tuple[PacketLifecycleOutcome, ...]:
        outcomes: List[PacketLifecycleOutcome] = []
        cumulative_exec_ms = 0.0
        destination_cpu_pct = float(self.destination_cpu_replay.next_value())
        block_receive_runtime_ms = 0.0
        block_payload_kb = 0.0
        start_ms = float(receive_start_ms) if receive_start_ms is not None else batch.delivered_at_ms
        if start_ms < batch.delivered_at_ms:
            start_ms = batch.delivered_at_ms
        for bundle in batch.bundles:
            execute_ms = float(self.receive_exec_ms_replay.next_value())
            ack_ms = float(self.ack_commit_ms_replay.next_value())
            received_at_ms = start_ms + cumulative_exec_ms
            result = self.destination_chain.receive_packet(
                bundle=bundle,
                received_at_ms=received_at_ms,
                execute_latency_ms=execute_ms,
                ack_commit_latency_ms=ack_ms,
            )
            self.metrics.record_merkle_verification(result.accepted)
            self.metrics.record_energy(self.k_verify_mj_per_proof)
            if not result.accepted:
                continue
            cumulative_exec_ms += execute_ms + ack_ms
            block_receive_runtime_ms += execute_ms + ack_ms
            payload_kb = bundle.packet.payload_bytes / 1024.0
            block_payload_kb += payload_kb
            ack_returned_at_ms = self.relayer.return_ack(
                ack_commit_at_ms=result.ack_commit_at_ms
            )
            submitted = self._submit_times.get(
                bundle.packet.sequence, bundle.packet.submitted_at_ms
            )
            source_block = self.source_chain.block(bundle.source_block_id)
            source_committed_at = (
                source_block.committed_at_ms if source_block is not None else bundle.produced_at_ms
            )
            outcome = PacketLifecycleOutcome(
                sequence=bundle.packet.sequence,
                channel=bundle.packet.source_channel,
                submitted_at_ms=submitted,
                source_committed_at_ms=source_committed_at,
                relayer_delivered_at_ms=batch.delivered_at_ms,
                destination_received_at_ms=received_at_ms,
                destination_executed_at_ms=result.received_at_ms,
                ack_committed_at_ms=result.ack_commit_at_ms,
                ack_returned_at_ms=ack_returned_at_ms,
                accepted=True,
                payload_kb=payload_kb,
            )
            outcomes.append(outcome)
            self.metrics.record_received(
                channel=bundle.packet.source_channel,
                submitted_at_ms=submitted,
                source_committed_at_ms=source_committed_at,
                destination_executed_at_ms=result.received_at_ms,
                ack_committed_at_ms=result.ack_commit_at_ms,
                ack_return_at_ms=ack_returned_at_ms,
                payload_kb=payload_kb,
            )
        self.metrics.record_destination_block()
        self.metrics.record_cpu_sample(destination_cpu_pct, block_receive_runtime_ms)
        self.metrics.record_energy(
            self._destination_block_energy(
                cpu_pct=destination_cpu_pct,
                runtime_ms=block_receive_runtime_ms,
                payload_kb=block_payload_kb,
            )
        )
        self._outcomes.extend(outcomes)
        return tuple(outcomes)

    def outcomes(self) -> Tuple[PacketLifecycleOutcome, ...]:
        return tuple(self._outcomes)

    def _source_block_energy(
        self, cpu_pct: float, runtime_ms: float, payload_kb: float
    ) -> float:
        cpu_cycles_1k = max(0.0, runtime_ms) * (cpu_pct / 100.0)
        cpu_nj = cpu_cycles_1k * self.k_cpu_nj_per_1k_cycles
        net_uj = payload_kb * self.k_net_uj_per_kb
        total_nj = cpu_nj + net_uj * 1000.0
        return total_nj / 1_000_000.0

    def _destination_block_energy(
        self, cpu_pct: float, runtime_ms: float, payload_kb: float
    ) -> float:
        return self._source_block_energy(cpu_pct, runtime_ms, payload_kb)

    def _relayer_energy(
        self, cpu_pct: float, runtime_ms: float, payload_kb: float
    ) -> float:
        cpu_cycles_1k = max(0.0, runtime_ms) * (cpu_pct / 100.0)
        cpu_nj = cpu_cycles_1k * self.k_cpu_nj_per_1k_cycles
        net_uj = payload_kb * self.k_net_uj_per_kb * 2.0
        total_nj = cpu_nj + net_uj * 1000.0
        return total_nj / 1_000_000.0

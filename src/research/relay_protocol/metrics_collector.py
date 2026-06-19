from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class IbcMetricsSnapshot:
    packets_submitted: int = 0
    packets_source_committed: int = 0
    packets_delivered_by_relayer: int = 0
    packets_received: int = 0
    packets_acknowledged: int = 0
    blocks_produced_source: int = 0
    blocks_produced_destination: int = 0
    header_updates_applied: int = 0
    merkle_verifications: int = 0
    merkle_verification_failures: int = 0
    relayer_backlog_peak: int = 0
    relayer_backlog_mean: float = 0.0
    relayer_batches: int = 0
    wall_time_ms: float = 0.0
    throughput_tps: float = 0.0
    protocol_latency_ms: float = 0.0
    end_to_end_latency_ms: float = 0.0
    packet_ack_roundtrip_ms: float = 0.0
    cpu_utilization_percent: float = 0.0
    total_energy_mj: float = 0.0
    normalized_energy: float = 0.0
    header_sync_overhead_ms: float = 0.0
    header_sync_overhead_ratio: float = 0.0
    per_channel_throughput: Dict[str, float] = field(default_factory=dict)


@dataclass
class RelayMetricsCollector:
    packets_submitted: int = 0
    packets_source_committed: int = 0
    packets_delivered_by_relayer: int = 0
    packets_received: int = 0
    packets_acknowledged: int = 0
    blocks_produced_source: int = 0
    blocks_produced_destination: int = 0
    header_updates_applied: int = 0
    merkle_verifications: int = 0
    merkle_verification_failures: int = 0
    relayer_backlog_peak: int = 0
    relayer_backlog_samples: List[int] = field(default_factory=list)
    relayer_batches: int = 0
    simulation_end_ms: float = 0.0
    simulation_start_ms: float = 0.0
    protocol_latencies_ms: List[float] = field(default_factory=list)
    e2e_latencies_ms: List[float] = field(default_factory=list)
    ack_roundtrip_ms_samples: List[float] = field(default_factory=list)
    cpu_samples: List[float] = field(default_factory=list)
    cpu_weights: List[float] = field(default_factory=list)
    energy_samples_mj: List[float] = field(default_factory=list)
    header_sync_overhead_ms_total: float = 0.0
    runtime_ms_total: float = 0.0
    per_channel_tx: Dict[str, int] = field(default_factory=dict)
    payload_kb_total: float = 0.0

    def record_packet_submitted(self) -> None:
        self.packets_submitted += 1

    def record_source_committed(self, packets: int) -> None:
        self.packets_source_committed += packets
        self.blocks_produced_source += 1

    def record_destination_block(self) -> None:
        self.blocks_produced_destination += 1

    def record_relayer_batch(self, delivered: int, backlog_after: int) -> None:
        self.packets_delivered_by_relayer += delivered
        self.relayer_batches += 1
        self.relayer_backlog_samples.append(int(backlog_after))
        if backlog_after > self.relayer_backlog_peak:
            self.relayer_backlog_peak = int(backlog_after)

    def record_header_update(self, verify_ms: float) -> None:
        self.header_updates_applied += 1
        self.header_sync_overhead_ms_total += float(verify_ms)

    def record_merkle_verification(self, ok: bool) -> None:
        self.merkle_verifications += 1
        if not ok:
            self.merkle_verification_failures += 1

    def record_received(
        self,
        channel: str,
        submitted_at_ms: float,
        source_committed_at_ms: float,
        destination_executed_at_ms: float,
        ack_committed_at_ms: float,
        ack_return_at_ms: float,
        payload_kb: float,
    ) -> None:
        self.packets_received += 1
        self.packets_acknowledged += 1
        self.per_channel_tx[channel] = self.per_channel_tx.get(channel, 0) + 1
        self.payload_kb_total += float(payload_kb)
        self.protocol_latencies_ms.append(
            max(0.0, destination_executed_at_ms - source_committed_at_ms)
        )
        self.e2e_latencies_ms.append(
            max(0.0, destination_executed_at_ms - submitted_at_ms)
        )
        self.ack_roundtrip_ms_samples.append(
            max(0.0, ack_return_at_ms - submitted_at_ms)
        )

    def record_cpu_sample(self, cpu_percent: float, weight_ms: float) -> None:
        self.cpu_samples.append(float(cpu_percent))
        self.cpu_weights.append(float(weight_ms))
        self.runtime_ms_total += float(weight_ms)

    def record_energy(self, mj: float) -> None:
        self.energy_samples_mj.append(float(mj))

    def set_simulation_window(self, start_ms: float, end_ms: float) -> None:
        self.simulation_start_ms = float(start_ms)
        self.simulation_end_ms = float(end_ms)

    def _median(self, xs: List[float]) -> float:
        if not xs:
            return 0.0
        s = sorted(xs)
        n = len(s)
        m = n // 2
        if n % 2 == 1:
            return float(s[m])
        return float((s[m - 1] + s[m]) / 2.0)

    def _weighted_mean(self, values: List[float], weights: List[float]) -> float:
        if not values:
            return 0.0
        total_w = float(sum(weights)) if weights else 0.0
        if total_w <= 0.0:
            return float(sum(values) / len(values))
        acc = 0.0
        for v, w in zip(values, weights):
            acc += float(v) * float(w)
        return acc / total_w

    def snapshot(self) -> IbcMetricsSnapshot:
        wall_ms = max(1.0, self.simulation_end_ms - self.simulation_start_ms)
        tps = (self.packets_received / (wall_ms / 1000.0)) if wall_ms > 0 else 0.0
        per_channel = {
            ch: (n / (wall_ms / 1000.0)) if wall_ms > 0 else 0.0
            for ch, n in self.per_channel_tx.items()
        }
        total_energy = float(sum(self.energy_samples_mj))
        norm_energy = 0.0
        if self.packets_received > 0 and total_energy > 0.0:
            norm_energy = total_energy / float(self.packets_received)
        backlog_mean = 0.0
        if self.relayer_backlog_samples:
            backlog_mean = float(sum(self.relayer_backlog_samples)) / float(
                len(self.relayer_backlog_samples)
            )
        cpu = self._weighted_mean(self.cpu_samples, self.cpu_weights)
        header_ratio = 0.0
        if self.runtime_ms_total > 0.0:
            header_ratio = self.header_sync_overhead_ms_total / self.runtime_ms_total
        return IbcMetricsSnapshot(
            packets_submitted=self.packets_submitted,
            packets_source_committed=self.packets_source_committed,
            packets_delivered_by_relayer=self.packets_delivered_by_relayer,
            packets_received=self.packets_received,
            packets_acknowledged=self.packets_acknowledged,
            blocks_produced_source=self.blocks_produced_source,
            blocks_produced_destination=self.blocks_produced_destination,
            header_updates_applied=self.header_updates_applied,
            merkle_verifications=self.merkle_verifications,
            merkle_verification_failures=self.merkle_verification_failures,
            relayer_backlog_peak=self.relayer_backlog_peak,
            relayer_backlog_mean=backlog_mean,
            relayer_batches=self.relayer_batches,
            wall_time_ms=wall_ms,
            throughput_tps=tps,
            protocol_latency_ms=self._median(self.protocol_latencies_ms),
            end_to_end_latency_ms=self._median(self.e2e_latencies_ms),
            packet_ack_roundtrip_ms=self._median(self.ack_roundtrip_ms_samples),
            cpu_utilization_percent=cpu,
            total_energy_mj=total_energy,
            normalized_energy=norm_energy,
            header_sync_overhead_ms=self.header_sync_overhead_ms_total,
            header_sync_overhead_ratio=header_ratio,
            per_channel_throughput=per_channel,
        )

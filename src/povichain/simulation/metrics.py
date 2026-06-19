from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class MetricSnapshot:
    blocks_finalized: int = 0
    blocks_attempted: int = 0
    tx_finalized: int = 0
    proofs_built: int = 0
    proofs_verified: int = 0
    mcu_verifications: int = 0
    invalid_accepts: int = 0
    block_loss: int = 0
    penalty_rounds_to_convergence: int = 0
    throughput_tps: float = 0.0
    protocol_latency_ms: float = 0.0
    e2e_latency_ms: float = 0.0
    gateway_cpu_percent: float = 0.0
    gateway_memory_mb: float = 0.0
    mcu_resident_kb: float = 0.0
    mcu_peak_kb: float = 0.0
    normalized_energy: float = 0.0
    total_energy_mj: float = 0.0
    wall_time_ms: float = 0.0
    per_zone_throughput: Dict[str, float] = field(default_factory=dict)
    per_zone_backlog_peak: Dict[str, int] = field(default_factory=dict)
    orphan_stale_rate: float = 0.0
    dispatcher_efficiency: float = 0.0
    fork_resolution_accuracy: float = 0.0
    conflict_ratio: float = 0.0
    recovery_time_ms: float = 0.0
    effective_malicious_reputation: float = 0.0


@dataclass
class MetricCollector:
    protocol_latencies_ms: List[float] = field(default_factory=list)
    e2e_latencies_ms: List[float] = field(default_factory=list)
    gateway_cpu_samples: List[float] = field(default_factory=list)
    gateway_memory_samples: List[float] = field(default_factory=list)
    mcu_peak_samples: List[float] = field(default_factory=list)
    mcu_resident_samples: List[float] = field(default_factory=list)
    proving_latency_samples_ms: List[float] = field(default_factory=list)
    verifier_latency_samples_ms: List[float] = field(default_factory=list)
    energy_samples_mj: List[float] = field(default_factory=list)
    per_zone_tx_finalized: Dict[str, int] = field(default_factory=dict)
    per_zone_backlog_peak: Dict[str, int] = field(default_factory=dict)
    blocks_finalized: int = 0
    blocks_attempted: int = 0
    tx_finalized: int = 0
    proofs_built: int = 0
    proofs_verified: int = 0
    mcu_verifications: int = 0
    invalid_accepts: int = 0
    block_loss: int = 0
    orphan_count: int = 0
    stale_count: int = 0
    conflict_count: int = 0
    committee_sizes: List[int] = field(default_factory=list)
    malicious_effective_reps: List[float] = field(default_factory=list)
    penalty_rounds: List[int] = field(default_factory=list)
    recovery_times_ms: List[float] = field(default_factory=list)
    fork_resolution_hits: int = 0
    fork_resolution_total: int = 0
    payload_kb_total: float = 0.0
    simulation_end_ms: float = 0.0
    device_energy_mj_per_tx: float = 0.0

    def record_block_finalized(
        self,
        zone_id: str,
        tx_count: int,
        consensus_start_ms: float,
        finalized_at_ms: float,
        earliest_submit_ms: float,
    ) -> None:
        self.blocks_finalized += 1
        self.tx_finalized += tx_count
        self.per_zone_tx_finalized[zone_id] = self.per_zone_tx_finalized.get(zone_id, 0) + tx_count
        self.protocol_latencies_ms.append(max(0.0, finalized_at_ms - consensus_start_ms))
        self.e2e_latencies_ms.append(max(0.0, finalized_at_ms - earliest_submit_ms))

    def record_block_attempted(self) -> None:
        self.blocks_attempted += 1

    def record_block_loss(self) -> None:
        self.block_loss += 1

    def record_invalid_accept(self) -> None:
        self.invalid_accepts += 1

    def record_proof_built(self, latency_ms: float, cpu_pct: float, mem_mb: float) -> None:
        self.proofs_built += 1
        self.proving_latency_samples_ms.append(float(latency_ms))
        self.gateway_cpu_samples.append(float(cpu_pct))
        self.gateway_memory_samples.append(float(mem_mb))

    def record_proof_verified(self) -> None:
        self.proofs_verified += 1

    def record_mcu_verify(self, latency_ms: float, resident_kb: float, peak_kb: float) -> None:
        self.mcu_verifications += 1
        self.verifier_latency_samples_ms.append(float(latency_ms))
        self.mcu_resident_samples.append(float(resident_kb))
        self.mcu_peak_samples.append(float(peak_kb))

    def record_energy_mj(self, amount: float) -> None:
        self.energy_samples_mj.append(float(amount))

    def record_backlog_peak(self, zone_id: str, peak: int) -> None:
        self.per_zone_backlog_peak[zone_id] = max(self.per_zone_backlog_peak.get(zone_id, 0), peak)

    def record_committee_size(self, size: int) -> None:
        self.committee_sizes.append(int(size))

    def record_malicious_effective(self, rep: float) -> None:
        self.malicious_effective_reps.append(float(rep))

    def record_penalty_convergence(self, rounds: int) -> None:
        self.penalty_rounds.append(int(rounds))

    def record_recovery(self, ms: float) -> None:
        self.recovery_times_ms.append(float(ms))

    def record_fork_resolution(self, correct: bool) -> None:
        self.fork_resolution_total += 1
        if correct:
            self.fork_resolution_hits += 1

    def record_conflict(self) -> None:
        self.conflict_count += 1

    def record_orphan(self) -> None:
        self.orphan_count += 1

    def record_stale(self) -> None:
        self.stale_count += 1

    def record_payload_kb(self, kb: float) -> None:
        self.payload_kb_total += float(kb)

    def end_simulation(self, end_ms: float) -> None:
        self.simulation_end_ms = float(end_ms)

    def snapshot(self) -> MetricSnapshot:
        def mean(xs: List[float]) -> float:
            return float(sum(xs) / len(xs)) if xs else 0.0

        def median(xs: List[float]) -> float:
            if not xs:
                return 0.0
            s = sorted(xs)
            n = len(s)
            m = n // 2
            if n % 2 == 1:
                return float(s[m])
            return float((s[m - 1] + s[m]) / 2.0)

        def peak(xs: List[float]) -> float:
            return float(max(xs)) if xs else 0.0

        wall = max(1.0, self.simulation_end_ms)
        tps = (self.tx_finalized / (wall / 1000.0)) if wall > 0 else 0.0
        per_zone_tps = {
            z: (float(n) / (wall / 1000.0)) if wall > 0 else 0.0
            for z, n in self.per_zone_tx_finalized.items()
        }
        if self.device_energy_mj_per_tx > 0.0 and self.tx_finalized > 0:
            normalized_energy = float(self.device_energy_mj_per_tx)
            total_energy = normalized_energy * float(self.tx_finalized)
        else:
            total_energy = float(sum(self.energy_samples_mj))
            normalized_energy = 0.0
            if self.tx_finalized > 0 and total_energy > 0.0:
                normalized_energy = total_energy / float(self.tx_finalized)
        fork_acc = (
            float(self.fork_resolution_hits) / float(self.fork_resolution_total)
            if self.fork_resolution_total > 0
            else 1.0
        )
        dispatcher_eff = (
            float(self.tx_finalized) / float(self.tx_finalized + self.orphan_count + self.stale_count)
            if (self.tx_finalized + self.orphan_count + self.stale_count) > 0
            else 1.0
        )
        orphan_stale = 0.0
        denom = self.tx_finalized + self.orphan_count + self.stale_count
        if denom > 0:
            orphan_stale = float(self.orphan_count + self.stale_count) / float(denom)
        conflict_ratio = (
            float(self.conflict_count) / float(self.blocks_attempted)
            if self.blocks_attempted > 0
            else 0.0
        )
        malicious_eff = mean(self.malicious_effective_reps)
        penalty_conv = int(median(list(float(x) for x in self.penalty_rounds))) if self.penalty_rounds else 0
        recovery = median(self.recovery_times_ms) if self.recovery_times_ms else 0.0
        return MetricSnapshot(
            blocks_finalized=self.blocks_finalized,
            blocks_attempted=self.blocks_attempted,
            tx_finalized=self.tx_finalized,
            proofs_built=self.proofs_built,
            proofs_verified=self.proofs_verified,
            mcu_verifications=self.mcu_verifications,
            invalid_accepts=self.invalid_accepts,
            block_loss=self.block_loss,
            penalty_rounds_to_convergence=penalty_conv,
            throughput_tps=tps,
            protocol_latency_ms=median(self.protocol_latencies_ms),
            e2e_latency_ms=median(self.e2e_latencies_ms),
            gateway_cpu_percent=mean(self.gateway_cpu_samples),
            gateway_memory_mb=mean(self.gateway_memory_samples),
            mcu_resident_kb=mean(self.mcu_resident_samples),
            mcu_peak_kb=peak(self.mcu_peak_samples),
            normalized_energy=normalized_energy,
            total_energy_mj=total_energy,
            wall_time_ms=wall,
            per_zone_throughput=per_zone_tps,
            per_zone_backlog_peak=dict(self.per_zone_backlog_peak),
            orphan_stale_rate=orphan_stale,
            dispatcher_efficiency=dispatcher_eff,
            fork_resolution_accuracy=fork_acc,
            conflict_ratio=conflict_ratio,
            recovery_time_ms=recovery,
            effective_malicious_reputation=malicious_eff,
        )

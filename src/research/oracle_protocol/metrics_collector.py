from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class L0MetricsSnapshot:
    messages_submitted: int = 0
    messages_formatted: int = 0
    verification_votes_cast: int = 0
    verification_quorum_reached: int = 0
    commit_verifications: int = 0
    messages_executed: int = 0
    wall_time_ms: float = 0.0
    throughput_tps: float = 0.0
    protocol_latency_ms: float = 0.0
    end_to_end_latency_ms: float = 0.0
    cpu_utilization_percent: float = 0.0
    total_energy_mj: float = 0.0
    normalized_energy: float = 0.0
    dvn_verification_fanout: float = 0.0
    verification_queue_depth_peak: int = 0
    verification_queue_depth_mean: float = 0.0
    commit_verification_delay_ms: float = 0.0
    executor_wait_due_to_nonce_ordering_ms: float = 0.0
    per_path_throughput: Dict[str, float] = field(default_factory=dict)


@dataclass
class OracleMetricsCollector:
    messages_submitted: int = 0
    messages_formatted: int = 0
    verification_votes_cast: int = 0
    verification_quorum_reached: int = 0
    commit_verifications: int = 0
    messages_executed: int = 0
    simulation_start_ms: float = 0.0
    simulation_end_ms: float = 0.0
    protocol_latencies_ms: List[float] = field(default_factory=list)
    e2e_latencies_ms: List[float] = field(default_factory=list)
    commit_delays_ms: List[float] = field(default_factory=list)
    nonce_wait_ms: List[float] = field(default_factory=list)
    dvn_fanout_samples: List[int] = field(default_factory=list)
    verification_queue_samples: List[int] = field(default_factory=list)
    verification_queue_peak: int = 0
    cpu_samples: List[float] = field(default_factory=list)
    cpu_weights: List[float] = field(default_factory=list)
    energy_samples_mj: List[float] = field(default_factory=list)
    runtime_ms_total: float = 0.0
    per_path_messages: Dict[str, int] = field(default_factory=dict)
    payload_kb_total: float = 0.0

    def record_submitted(self) -> None:
        self.messages_submitted += 1

    def record_formatted(self) -> None:
        self.messages_formatted += 1

    def record_verification_vote(self) -> None:
        self.verification_votes_cast += 1

    def record_quorum_reached(self) -> None:
        self.verification_quorum_reached += 1

    def record_commit_verification(self, delay_ms: float) -> None:
        self.commit_verifications += 1
        self.commit_delays_ms.append(float(delay_ms))

    def record_verification_queue_depth(self, depth: int) -> None:
        self.verification_queue_samples.append(int(depth))
        if depth > self.verification_queue_peak:
            self.verification_queue_peak = int(depth)

    def record_execution(
        self,
        path_key: str,
        submitted_at_ms: float,
        committed_at_ms: float,
        executed_at_ms: float,
        wait_due_to_nonce_ms: float,
        dvn_fanout: int,
        payload_kb: float,
    ) -> None:
        self.messages_executed += 1
        self.per_path_messages[path_key] = self.per_path_messages.get(path_key, 0) + 1
        self.protocol_latencies_ms.append(max(0.0, committed_at_ms - submitted_at_ms))
        self.e2e_latencies_ms.append(max(0.0, executed_at_ms - submitted_at_ms))
        self.nonce_wait_ms.append(max(0.0, wait_due_to_nonce_ms))
        self.dvn_fanout_samples.append(int(dvn_fanout))
        self.payload_kb_total += float(payload_kb)

    def record_cpu_sample(self, cpu_percent: float, weight_ms: float) -> None:
        if weight_ms <= 0.0:
            return
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

    def snapshot(self) -> L0MetricsSnapshot:
        wall_ms = max(1.0, self.simulation_end_ms - self.simulation_start_ms)
        tps = (self.messages_executed / (wall_ms / 1000.0)) if wall_ms > 0 else 0.0
        per_path = {
            p: (n / (wall_ms / 1000.0)) if wall_ms > 0 else 0.0
            for p, n in self.per_path_messages.items()
        }
        total_energy = float(sum(self.energy_samples_mj))
        norm_energy = 0.0
        if self.messages_executed > 0 and total_energy > 0.0:
            norm_energy = total_energy / float(self.messages_executed)
        queue_mean = 0.0
        if self.verification_queue_samples:
            queue_mean = float(sum(self.verification_queue_samples)) / float(
                len(self.verification_queue_samples)
            )
        fanout_mean = 0.0
        if self.dvn_fanout_samples:
            fanout_mean = float(sum(self.dvn_fanout_samples)) / float(len(self.dvn_fanout_samples))
        cpu = self._weighted_mean(self.cpu_samples, self.cpu_weights)
        return L0MetricsSnapshot(
            messages_submitted=self.messages_submitted,
            messages_formatted=self.messages_formatted,
            verification_votes_cast=self.verification_votes_cast,
            verification_quorum_reached=self.verification_quorum_reached,
            commit_verifications=self.commit_verifications,
            messages_executed=self.messages_executed,
            wall_time_ms=wall_ms,
            throughput_tps=tps,
            protocol_latency_ms=self._median(self.protocol_latencies_ms),
            end_to_end_latency_ms=self._median(self.e2e_latencies_ms),
            cpu_utilization_percent=cpu,
            total_energy_mj=total_energy,
            normalized_energy=norm_energy,
            dvn_verification_fanout=fanout_mean,
            verification_queue_depth_peak=self.verification_queue_peak,
            verification_queue_depth_mean=queue_mean,
            commit_verification_delay_ms=self._median(self.commit_delays_ms),
            executor_wait_due_to_nonce_ordering_ms=self._median(self.nonce_wait_ms),
            per_path_throughput=per_path,
        )

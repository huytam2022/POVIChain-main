from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from povichain.ingestion.trace_loader import TraceReplay

from .channel_state import OracleChannelState
from .message import L0ExecutionResult, OracleMessage, L0MessageEnvelope, OracleAttestation


@dataclass
class L0ExecutorOutcome:
    message: OracleMessage
    verified_at_ms: float
    committed_at_ms: float
    executed_at_ms: float
    wait_due_to_nonce_ms: float
    payload_kb: float
    dvn_fanout: int
    attestation: OracleAttestation


@dataclass
class _PendingExecution:
    envelope: L0MessageEnvelope
    attestation: OracleAttestation
    verified_at_ms: float
    committed_at_ms: float


@dataclass
class OracleExecutor:
    execute_latency_replay: TraceReplay
    channel_state: OracleChannelState
    _pending_by_path: Dict[tuple, List[_PendingExecution]] = field(default_factory=dict)
    _executed: int = 0
    _last_executed_at_by_path: Dict[tuple, float] = field(default_factory=dict)

    def _path_key_for(self, envelope: L0MessageEnvelope) -> tuple:
        m = envelope.message
        return (m.src_chain_id, m.dst_chain_id, m.src_oapp, m.dst_oapp)

    def enqueue_verified(
        self,
        envelope: L0MessageEnvelope,
        attestation: OracleAttestation,
        verified_at_ms: float,
        committed_at_ms: float,
    ) -> None:
        key = self._path_key_for(envelope)
        bucket = self._pending_by_path.setdefault(key, [])
        bucket.append(
            _PendingExecution(
                envelope=envelope,
                attestation=attestation,
                verified_at_ms=verified_at_ms,
                committed_at_ms=committed_at_ms,
            )
        )
        bucket.sort(key=lambda x: int(x.envelope.message.nonce))

    def drain_ready(self, dvn_fanout: int) -> Tuple[L0ExecutorOutcome, ...]:
        outcomes: List[L0ExecutorOutcome] = []
        progressed = True
        while progressed:
            progressed = False
            for key, bucket in list(self._pending_by_path.items()):
                if not bucket:
                    continue
                pending = bucket[0]
                msg = pending.envelope.message
                expected = self.channel_state.next_expected_inbound(
                    msg.src_chain_id, msg.dst_chain_id, msg.src_oapp, msg.dst_oapp
                )
                if int(msg.nonce) != expected:
                    continue
                bucket.pop(0)
                outcome = self._execute(pending=pending, dvn_fanout=dvn_fanout, path_key=key)
                outcomes.append(outcome)
                progressed = True
        return tuple(outcomes)

    def _execute(
        self,
        pending: _PendingExecution,
        dvn_fanout: int,
        path_key: tuple,
    ) -> L0ExecutorOutcome:
        execute_latency_ms = float(self.execute_latency_replay.next_value())
        msg = pending.envelope.message
        prior_executed_at = self._last_executed_at_by_path.get(path_key, 0.0)
        start_ms = max(pending.committed_at_ms, prior_executed_at)
        wait_due_to_nonce_ms = max(0.0, start_ms - pending.committed_at_ms)
        executed_at_ms = start_ms + max(0.0, execute_latency_ms)
        self._last_executed_at_by_path[path_key] = executed_at_ms
        self.channel_state.record_executed(msg)
        self._executed += 1
        payload_kb = msg.payload_bytes / 1024.0
        return L0ExecutorOutcome(
            message=msg,
            verified_at_ms=pending.verified_at_ms,
            committed_at_ms=pending.committed_at_ms,
            executed_at_ms=executed_at_ms,
            wait_due_to_nonce_ms=wait_due_to_nonce_ms,
            payload_kb=payload_kb,
            dvn_fanout=dvn_fanout,
            attestation=pending.attestation,
        )

    def executed_count(self) -> int:
        return self._executed

    def pending_count(self) -> int:
        return sum(len(v) for v in self._pending_by_path.values())

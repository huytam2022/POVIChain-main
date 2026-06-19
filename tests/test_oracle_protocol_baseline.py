import hashlib
import os

import pytest

from oracle_protocol.channel_state import OracleChannelState
from oracle_protocol.dvn import OracleVerifierNetwork, OracleVerifier
from oracle_protocol.endpoint import OracleDestinationEndpoint, OracleEndpoint, OracleSourceEndpoint
from oracle_protocol.executor import OracleExecutor
from oracle_protocol.lifecycle import OraclePacketLifecycle
from oracle_protocol.manifest import load_oracle_manifest
from oracle_protocol.message import OracleMessage, OracleAttestation
from oracle_protocol.message_lib import OracleMessageLib
from oracle_protocol.metrics_collector import OracleMetricsCollector
from oracle_protocol.nonce_manager import OracleNonceManager
from oracle_protocol.protocol_profile import (
    build_verifier_replays,
    build_replays,
    load_oracle_protocol_profile,
)
from oracle_protocol.runner import OracleRunner
from povichain.ingestion.trace_loader import ExactCycleReplay


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIGS_ROOT = os.path.join(ROOT, "configs")
SCHEMAS_ROOT = os.path.join(ROOT, "schemas")
DATA_ROOT = os.path.join(ROOT, "data")
MANIFEST_PATH = os.path.join(CONFIGS_ROOT, "experiments", "oracle_protocol_comparison.yaml")
PROTOCOL_DIR = os.path.join(CONFIGS_ROOT, "profiles")


def _fixed_replay(value: float) -> ExactCycleReplay:
    return ExactCycleReplay((float(value),))


def _build_pipeline(required_quorum: int = 2, total_verifiers: int = 3):
    channel_state = OracleChannelState()
    nonce_manager = OracleNonceManager()
    message_lib = OracleMessageLib(
        packet_header_bytes=96,
        format_latency_replay=_fixed_replay(0.30),
        commit_verification_latency_replay=_fixed_replay(0.20),
    )
    verifiers = []
    base_rtts = [60.0, 65.0, 70.0]
    for i in range(total_verifiers):
        verifiers.append(
            OracleVerifier(
                verifier_id="dvn_" + str(i),
                verify_latency_replay=_fixed_replay(0.35),
                network_rtt_replay=_fixed_replay(base_rtts[i % len(base_rtts)]),
            )
        )
    dvn = OracleVerifierNetwork(
        verifiers=tuple(verifiers),
        required_quorum=required_quorum,
        total_verifiers=total_verifiers,
    )
    executor = OracleExecutor(
        execute_latency_replay=_fixed_replay(0.34),
        channel_state=channel_state,
    )
    src_ep = OracleEndpoint(chain_id="chain_a", oapp_identifier="oapp_a")
    dst_ep = OracleEndpoint(chain_id="chain_b", oapp_identifier="oapp_b")
    source_endpoint = OracleSourceEndpoint(
        endpoint=src_ep,
        message_lib=message_lib,
        nonce_manager=nonce_manager,
        channel_state=channel_state,
    )
    destination_endpoint = OracleDestinationEndpoint(
        endpoint=dst_ep,
        message_lib=message_lib,
        dvn=dvn,
        executor=executor,
        channel_state=channel_state,
    )
    metrics = OracleMetricsCollector()
    lifecycle = OraclePacketLifecycle(
        source_endpoint=source_endpoint,
        destination_endpoint=destination_endpoint,
        dvn=dvn,
        metrics=metrics,
        source_cpu_replay=_fixed_replay(70.0),
        dvn_cpu_replay=_fixed_replay(72.0),
        destination_cpu_replay=_fixed_replay(71.0),
        k_cpu_nj_per_1k_cycles=11538.4615,
        k_net_uj_per_kb=300.0,
        k_dvn_verify_mj_per_vote=0.0003,
        k_commit_verification_mj=0.0002,
    )
    return (
        channel_state,
        nonce_manager,
        message_lib,
        dvn,
        executor,
        source_endpoint,
        destination_endpoint,
        metrics,
        lifecycle,
    )


def test_message_does_not_execute_without_dvn_quorum():
    (
        channel_state,
        nonce_manager,
        message_lib,
        _,
        executor,
        source_endpoint,
        destination_endpoint,
        _,
        _,
    ) = _build_pipeline(required_quorum=2, total_verifiers=3)
    envelope = source_endpoint.send(
        counterparty_chain="chain_b",
        counterparty_oapp="oapp_b",
        sender=1,
        payload_bytes=512,
        submitted_at_ms=0.0,
    )
    insufficient_attestation = OracleAttestation(
        packet_hash=envelope.packet_hash,
        committed_verifier_ids=("dvn_0",),
        quorum_size=1,
        required_quorum=2,
        last_vote_at_ms=10.0,
        committed_at_ms=10.0,
    )
    with pytest.raises(ValueError, match="l0_endpoint_insufficient_quorum"):
        destination_endpoint.commit_verification(
            envelope=envelope,
            attestation=insufficient_attestation,
            verified_at_ms=10.0,
        )
    assert executor.executed_count() == 0
    assert not channel_state.has_committed_verification(envelope.message)


def test_message_does_not_execute_with_only_one_dvn_vote():
    (
        channel_state,
        _,
        _,
        _,
        executor,
        source_endpoint,
        destination_endpoint,
        _,
        _,
    ) = _build_pipeline(required_quorum=2, total_verifiers=3)
    envelope = source_endpoint.send(
        counterparty_chain="chain_b",
        counterparty_oapp="oapp_b",
        sender=1,
        payload_bytes=512,
        submitted_at_ms=0.0,
    )
    single_vote_attestation = OracleAttestation(
        packet_hash=envelope.packet_hash,
        committed_verifier_ids=("dvn_0",),
        quorum_size=1,
        required_quorum=2,
        last_vote_at_ms=10.0,
        committed_at_ms=10.0,
    )
    with pytest.raises(ValueError, match="l0_endpoint_insufficient_quorum"):
        destination_endpoint.commit_verification(
            envelope=envelope,
            attestation=single_vote_attestation,
            verified_at_ms=10.0,
        )
    assert executor.pending_count() == 0
    assert executor.executed_count() == 0
    assert destination_endpoint.commit_count() == 0
    assert not channel_state.has_committed_verification(envelope.message)


def test_verification_out_of_order_execution_in_order():
    (
        channel_state,
        _,
        _,
        dvn,
        executor,
        source_endpoint,
        destination_endpoint,
        _,
        lifecycle,
    ) = _build_pipeline(required_quorum=2, total_verifiers=3)
    e1 = source_endpoint.send(
        counterparty_chain="chain_b",
        counterparty_oapp="oapp_b",
        sender=1,
        payload_bytes=256,
        submitted_at_ms=0.0,
    )
    e2 = source_endpoint.send(
        counterparty_chain="chain_b",
        counterparty_oapp="oapp_b",
        sender=1,
        payload_bytes=256,
        submitted_at_ms=1.0,
    )
    e3 = source_endpoint.send(
        counterparty_chain="chain_b",
        counterparty_oapp="oapp_b",
        sender=1,
        payload_bytes=256,
        submitted_at_ms=2.0,
    )
    assert e1.message.nonce == 1
    assert e2.message.nonce == 2
    assert e3.message.nonce == 3

    dvn.enqueue(e1)
    dvn.enqueue(e2)
    dvn.enqueue(e3)
    verifications = dvn.verify_pending(dispatched_at_ms=10.0)
    attestations = {v.envelope.message.nonce: (v.envelope, v.attestation) for v in verifications}

    envelope_b, attestation_b = attestations[2]
    destination_endpoint.commit_verification(
        envelope=envelope_b, attestation=attestation_b, verified_at_ms=50.0
    )
    executed_before = lifecycle.drain_execution()
    assert executed_before == ()

    envelope_c, attestation_c = attestations[3]
    destination_endpoint.commit_verification(
        envelope=envelope_c, attestation=attestation_c, verified_at_ms=45.0
    )
    executed_still_blocked = lifecycle.drain_execution()
    assert executed_still_blocked == ()

    envelope_a, attestation_a = attestations[1]
    destination_endpoint.commit_verification(
        envelope=envelope_a, attestation=attestation_a, verified_at_ms=60.0
    )
    executed_now = lifecycle.drain_execution()
    assert len(executed_now) == 3
    nonces = [o.message.nonce for o in executed_now]
    assert nonces == [1, 2, 3]


def test_commit_verification_is_separate_state_transition():
    (
        channel_state,
        _,
        message_lib,
        dvn,
        executor,
        source_endpoint,
        destination_endpoint,
        _,
        _,
    ) = _build_pipeline(required_quorum=2, total_verifiers=3)
    envelope = source_endpoint.send(
        counterparty_chain="chain_b",
        counterparty_oapp="oapp_b",
        sender=2,
        payload_bytes=384,
        submitted_at_ms=0.0,
    )
    assert not channel_state.has_committed_verification(envelope.message)
    assert destination_endpoint.commit_count() == 0

    dvn.enqueue(envelope)
    verifications = dvn.verify_pending(dispatched_at_ms=5.0)
    assert len(verifications) == 1

    assert not channel_state.has_committed_verification(envelope.message)
    assert executor.pending_count() == 0

    committed_at_ms = destination_endpoint.commit_verification(
        envelope=verifications[0].envelope,
        attestation=verifications[0].attestation,
        verified_at_ms=verifications[0].attestation.last_vote_at_ms,
    )
    assert committed_at_ms > verifications[0].attestation.last_vote_at_ms
    assert channel_state.has_committed_verification(envelope.message)
    assert destination_endpoint.commit_count() == 1
    assert executor.pending_count() == 1
    assert executor.executed_count() == 0


def test_verified_message_waits_for_prior_nonce_execution():
    (
        channel_state,
        _,
        _,
        dvn,
        executor,
        source_endpoint,
        destination_endpoint,
        _,
        lifecycle,
    ) = _build_pipeline(required_quorum=2, total_verifiers=3)
    e1 = source_endpoint.send("chain_b", "oapp_b", 1, 256, 0.0)
    e2 = source_endpoint.send("chain_b", "oapp_b", 1, 256, 1.0)
    dvn.enqueue(e1)
    dvn.enqueue(e2)

    verifications = {v.envelope.message.nonce: v for v in dvn.verify_pending(dispatched_at_ms=5.0)}

    v2 = verifications[2]
    destination_endpoint.commit_verification(
        envelope=v2.envelope, attestation=v2.attestation, verified_at_ms=v2.attestation.last_vote_at_ms
    )
    executed_first = lifecycle.drain_execution()
    assert executed_first == ()
    assert executor.pending_count() == 1

    v1 = verifications[1]
    destination_endpoint.commit_verification(
        envelope=v1.envelope, attestation=v1.attestation, verified_at_ms=v1.attestation.last_vote_at_ms
    )
    executed_after = lifecycle.drain_execution()
    assert len(executed_after) == 2
    assert [o.message.nonce for o in executed_after] == [1, 2]


def test_removing_dvn_fanout_breaks_oracle_fanout():
    runner = OracleRunner(
        configs_root=CONFIGS_ROOT,
        schemas_root=SCHEMAS_ROOT,
        data_root=DATA_ROOT,
    )
    manifest = load_oracle_manifest(MANIFEST_PATH)
    from dataclasses import replace
    from oracle_protocol.manifest import OracleQuorumOverride

    single_manifest = replace(
        manifest,
        dvn_quorum_override=OracleQuorumOverride(total_verifiers=3, required=1),
    )
    three_manifest = replace(
        manifest,
        dvn_quorum_override=OracleQuorumOverride(total_verifiers=3, required=3),
    )
    two_of_three = runner.run(manifest)
    one_of_three = runner.run(single_manifest)
    three_of_three = runner.run(three_manifest)

    baseline_latency = two_of_three.metrics.end_to_end_latency_ms
    stripped_latency = one_of_three.metrics.end_to_end_latency_ms
    strict_latency = three_of_three.metrics.end_to_end_latency_ms

    assert stripped_latency < baseline_latency
    assert strict_latency > baseline_latency


def test_baseline_does_not_bypass_lifecycle():
    runner = OracleRunner(
        configs_root=CONFIGS_ROOT,
        schemas_root=SCHEMAS_ROOT,
        data_root=DATA_ROOT,
    )
    manifest = load_oracle_manifest(MANIFEST_PATH)
    result = runner.run(manifest)
    snap = result.metrics
    assert snap.messages_submitted > 0
    assert snap.messages_executed > 0
    assert snap.messages_formatted == snap.messages_submitted
    assert snap.verification_quorum_reached == snap.messages_submitted
    assert snap.commit_verifications == snap.messages_submitted
    for outcome in result.outcomes:
        assert outcome.submitted_at_ms <= outcome.formatted_at_ms
        assert outcome.formatted_at_ms <= outcome.verified_at_ms
        assert outcome.verified_at_ms <= outcome.committed_at_ms
        assert outcome.committed_at_ms <= outcome.executed_at_ms
        assert outcome.quorum_size >= outcome.required_quorum


def test_output_is_derived_from_live_pipeline_not_mocked():
    runner = OracleRunner(
        configs_root=CONFIGS_ROOT,
        schemas_root=SCHEMAS_ROOT,
        data_root=DATA_ROOT,
    )
    manifest = load_oracle_manifest(MANIFEST_PATH)
    result = runner.run(manifest)
    snap = result.metrics
    assert snap.messages_submitted > 0
    assert snap.messages_executed > 0
    assert snap.wall_time_ms > 0.0
    assert snap.throughput_tps > 0.0
    assert snap.protocol_latency_ms > 0.0
    assert snap.end_to_end_latency_ms > 0.0
    assert snap.total_energy_mj > 0.0
    assert snap.dvn_verification_fanout == pytest.approx(float(result.dvn_quorum["total_verifiers"]))
    assert len(result.outcomes) == snap.messages_executed


def test_determinism_same_inputs_same_outputs():
    runner = OracleRunner(
        configs_root=CONFIGS_ROOT,
        schemas_root=SCHEMAS_ROOT,
        data_root=DATA_ROOT,
    )
    manifest = load_oracle_manifest(MANIFEST_PATH)
    first = runner.run(manifest)
    second = runner.run(manifest)
    assert first.metrics.throughput_tps == pytest.approx(second.metrics.throughput_tps)
    assert first.metrics.protocol_latency_ms == pytest.approx(second.metrics.protocol_latency_ms)
    assert first.metrics.end_to_end_latency_ms == pytest.approx(second.metrics.end_to_end_latency_ms)
    assert first.metrics.cpu_utilization_percent == pytest.approx(second.metrics.cpu_utilization_percent)
    assert first.metrics.normalized_energy == pytest.approx(second.metrics.normalized_energy)
    assert first.calibration_hash == second.calibration_hash


def test_nonce_manager_assigns_gapless_sequence():
    nm = OracleNonceManager()
    a1 = nm.assign_outbound("chain_a", "chain_b", "oapp_a", "oapp_b")
    a2 = nm.assign_outbound("chain_a", "chain_b", "oapp_a", "oapp_b")
    a3 = nm.assign_outbound("chain_a", "chain_b", "oapp_a", "oapp_b")
    assert (a1, a2, a3) == (1, 2, 3)
    b1 = nm.assign_outbound("chain_a", "chain_c", "oapp_a", "oapp_x")
    b2 = nm.assign_outbound("chain_a", "chain_c", "oapp_a", "oapp_x")
    assert (b1, b2) == (1, 2)

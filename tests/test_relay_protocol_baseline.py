import hashlib
import os

import pytest

from relay_protocol.destination_chain import RelayDestinationChain
from relay_protocol.light_client import RelayLightClient
from relay_protocol.manifest import load_relay_manifest
from relay_protocol.merkle_verifier import RelayMerkleVerifier
from relay_protocol.metrics_collector import RelayMetricsCollector
from relay_protocol.packet import RelayPacket
from relay_protocol.packet_lifecycle import RelayPacketLifecycle
from relay_protocol.protocol_profile import build_replays, load_relay_protocol_profile
from relay_protocol.relayer import RelayAgent
from relay_protocol.runner import RelayRunner
from relay_protocol.source_chain import RelaySourceChain


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIGS_ROOT = os.path.join(ROOT, "configs")
SCHEMAS_ROOT = os.path.join(ROOT, "schemas")
DATA_ROOT = os.path.join(ROOT, "data")
MANIFEST_PATH = os.path.join(CONFIGS_ROOT, "experiments", "relay_protocol_comparison.yaml")
PROTOCOL_DIR = os.path.join(CONFIGS_ROOT, "profiles")


def _digest(sequence: int, channel: str, sender: int, payload_bytes: int) -> bytes:
    h = hashlib.sha256()
    h.update(b"IBC_TEST_DIGEST|")
    h.update(str(sequence).encode("utf-8"))
    h.update(b"|")
    h.update(channel.encode("utf-8"))
    h.update(b"|")
    h.update(str(sender).encode("utf-8"))
    h.update(b"|")
    h.update(str(payload_bytes).encode("utf-8"))
    return h.digest()


def _make_packet(sequence: int, channel: str = "energy", submitted_at_ms: float = 0.0) -> RelayPacket:
    return RelayPacket(
        sequence=sequence,
        source_channel=channel,
        destination_channel=channel + ".counterparty",
        source_port="transfer",
        destination_port="transfer",
        sender=1,
        payload_bytes=512,
        submitted_at_ms=submitted_at_ms,
        commit_digest=_digest(sequence, channel, 1, 512),
    )


def _build_profile_and_replays():
    profile = load_relay_protocol_profile(PROTOCOL_DIR, "relay_protocol")
    replays = build_replays(profile)
    return profile, replays


def _build_pipeline():
    profile, replays = _build_profile_and_replays()
    source = RelaySourceChain(chain_id=profile.source_chain_id)
    light_client = RelayLightClient(
        counterparty_chain_id=profile.source_chain_id,
        storage_footprint_per_header_kb=profile.light_client.storage_per_header_kb,
        retention_headers=profile.light_client.retention_headers,
    )
    verifier = RelayMerkleVerifier(light_client=light_client)
    destination = RelayDestinationChain(
        chain_id=profile.destination_chain_id,
        verifier=verifier,
    )
    relayer = RelayAgent(
        relayer_id="relayer_test",
        concurrent_packets=profile.relayer.concurrent_packets,
        rpc_rtt_replay=replays.relayer_rpc_rtt,
        processing_ms_per_packet_replay=replays.relayer_processing,
        header_verify_ms_replay=replays.light_client_header_verify,
        ack_return_ms_replay=replays.relayer_ack_return,
    )
    metrics = RelayMetricsCollector()
    lifecycle = RelayPacketLifecycle(
        source_chain=source,
        destination_chain=destination,
        light_client=light_client,
        relayer=relayer,
        metrics=metrics,
        receive_exec_ms_replay=replays.destination_receive_execute,
        ack_commit_ms_replay=replays.destination_ack_commit,
        source_cpu_replay=replays.source_cpu,
        destination_cpu_replay=replays.destination_cpu,
        relayer_cpu_replay=replays.relayer_cpu,
        k_cpu_nj_per_1k_cycles=profile.energy.k_cpu_nj_per_1k_cycles,
        k_net_uj_per_kb=profile.energy.k_net_uj_per_kb,
        k_header_mj_per_update=profile.energy.k_header_mj_per_update,
        k_verify_mj_per_proof=profile.energy.k_verify_mj_per_proof,
    )
    return profile, replays, source, light_client, verifier, destination, relayer, metrics, lifecycle


def test_packet_receive_fails_without_trusted_header():
    _, _, source, _, _, destination, relayer, _, lifecycle = _build_pipeline()
    packet = _make_packet(source.next_sequence(), submitted_at_ms=0.0)
    lifecycle.submit_packet(packet)
    block = source.propose_block(max_packets=4, proposed_at_ms=100.0, committed_at_ms=101.0)
    assert block is not None
    relayer.observe_source_block(block)
    bundles = list(relayer._pending_bundles)
    assert len(bundles) == 1
    bundle = bundles[0]
    result = destination.receive_packet(
        bundle=bundle,
        received_at_ms=200.0,
        execute_latency_ms=0.3,
        ack_commit_latency_ms=0.2,
    )
    assert result.accepted is False
    assert result.reason == "proof_invalid_or_untrusted_header"
    assert destination.unverified_rejections() == 1


def test_packet_receive_passes_after_header_sync():
    _, _, source, light_client, _, destination, relayer, _, lifecycle = _build_pipeline()
    packet = _make_packet(source.next_sequence(), submitted_at_ms=0.0)
    lifecycle.submit_packet(packet)
    block = source.propose_block(max_packets=4, proposed_at_ms=100.0, committed_at_ms=101.0)
    assert block is not None
    relayer.observe_source_block(block)
    light_client.apply_header_update(
        source_block=block, verify_latency_ms=50.0, applied_at_ms=150.0
    )
    bundle = relayer._pending_bundles[0]
    result = destination.receive_packet(
        bundle=bundle,
        received_at_ms=200.0,
        execute_latency_ms=0.3,
        ack_commit_latency_ms=0.2,
    )
    assert result.accepted is True
    assert result.reason == "ok"
    assert destination.has_received(packet.sequence)
    assert light_client.has_trusted_header_for(block.block_id)


def test_relayer_delay_increases_end_to_end_latency():
    _, replays, source, light_client, _, _, relayer, _, lifecycle = _build_pipeline()
    packet = _make_packet(source.next_sequence(), submitted_at_ms=0.0)
    lifecycle.submit_packet(packet)
    lifecycle.commit_source_block(
        max_packets_per_block=4, proposed_at_ms=50.0, committed_at_ms=51.0
    )
    baseline_batch = lifecycle.relay_and_deliver(dispatch_at_ms=100.0)
    baseline_outcomes = lifecycle.receive_batch(baseline_batch, receive_start_ms=baseline_batch.delivered_at_ms)
    assert baseline_outcomes
    baseline_latency = baseline_outcomes[0].destination_executed_at_ms - baseline_outcomes[0].submitted_at_ms

    _, _, source2, light2, _, _, relayer2, _, lifecycle2 = _build_pipeline()
    packet2 = _make_packet(source2.next_sequence(), submitted_at_ms=0.0)
    lifecycle2.submit_packet(packet2)
    lifecycle2.commit_source_block(
        max_packets_per_block=4, proposed_at_ms=50.0, committed_at_ms=51.0
    )
    delayed_dispatch_at_ms = 100.0 + 500.0
    delayed_batch = lifecycle2.relay_and_deliver(dispatch_at_ms=delayed_dispatch_at_ms)
    delayed_outcomes = lifecycle2.receive_batch(
        delayed_batch, receive_start_ms=delayed_batch.delivered_at_ms
    )
    delayed_latency = delayed_outcomes[0].destination_executed_at_ms - delayed_outcomes[0].submitted_at_ms
    assert delayed_latency > baseline_latency + 400.0


def test_header_sync_creates_continuous_overhead():
    _, _, source, light_client, _, _, relayer, metrics, lifecycle = _build_pipeline()
    for i in range(3):
        packet = _make_packet(source.next_sequence(), submitted_at_ms=float(i * 10))
        lifecycle.submit_packet(packet)
        lifecycle.commit_source_block(
            max_packets_per_block=1,
            proposed_at_ms=float(i * 100 + 50),
            committed_at_ms=float(i * 100 + 51),
        )
        batch = lifecycle.relay_and_deliver(dispatch_at_ms=float(i * 100 + 60))
        lifecycle.receive_batch(batch, receive_start_ms=batch.delivered_at_ms)
    snap = metrics.snapshot()
    assert snap.header_updates_applied == 3
    assert snap.header_sync_overhead_ms > 0.0
    assert light_client.updates_applied() == 3
    assert light_client.cumulative_verify_ms() > 0.0


def test_lifecycle_stages_are_all_executed():
    _, _, source, light_client, verifier, destination, relayer, metrics, lifecycle = _build_pipeline()
    packet = _make_packet(source.next_sequence(), submitted_at_ms=0.0)
    lifecycle.submit_packet(packet)
    assert metrics.packets_submitted == 1
    lifecycle.commit_source_block(
        max_packets_per_block=4, proposed_at_ms=50.0, committed_at_ms=51.0
    )
    assert metrics.packets_source_committed == 1
    batch = lifecycle.relay_and_deliver(dispatch_at_ms=100.0)
    assert metrics.packets_delivered_by_relayer == 1
    assert light_client.updates_applied() == 1
    outcomes = lifecycle.receive_batch(batch, receive_start_ms=batch.delivered_at_ms)
    assert metrics.packets_received == 1
    assert metrics.packets_acknowledged == 1
    assert verifier.verifications() == 1
    assert verifier.failures() == 0
    outcome = outcomes[0]
    assert outcome.submitted_at_ms <= outcome.source_committed_at_ms
    assert outcome.source_committed_at_ms <= outcome.relayer_delivered_at_ms
    assert outcome.relayer_delivered_at_ms <= outcome.destination_received_at_ms
    assert outcome.destination_received_at_ms <= outcome.destination_executed_at_ms
    assert outcome.destination_executed_at_ms <= outcome.ack_committed_at_ms
    assert outcome.ack_committed_at_ms <= outcome.ack_returned_at_ms


def test_output_is_derived_from_live_pipeline_not_mocked():
    runner = RelayRunner(
        configs_root=CONFIGS_ROOT,
        schemas_root=SCHEMAS_ROOT,
        data_root=DATA_ROOT,
    )
    manifest = load_relay_manifest(MANIFEST_PATH)
    result = runner.run(manifest)
    snap = result.metrics
    assert snap.packets_submitted > 0
    assert snap.packets_received > 0
    assert snap.packets_acknowledged == snap.packets_received
    assert snap.blocks_produced_source > 0
    assert snap.blocks_produced_destination > 0
    assert snap.header_updates_applied > 0
    assert snap.merkle_verifications >= snap.packets_received
    assert snap.merkle_verification_failures == 0
    assert snap.wall_time_ms > 0.0
    assert snap.throughput_tps > 0.0
    assert snap.protocol_latency_ms > 0.0
    assert snap.end_to_end_latency_ms >= snap.protocol_latency_ms
    assert snap.total_energy_mj > 0.0
    assert len(result.outcomes) == snap.packets_received
    for outcome in result.outcomes:
        assert outcome.accepted is True
        assert outcome.source_committed_at_ms <= outcome.relayer_delivered_at_ms
        assert outcome.relayer_delivered_at_ms <= outcome.destination_executed_at_ms


def test_determinism_same_inputs_same_outputs():
    runner = RelayRunner(
        configs_root=CONFIGS_ROOT,
        schemas_root=SCHEMAS_ROOT,
        data_root=DATA_ROOT,
    )
    manifest = load_relay_manifest(MANIFEST_PATH)
    first = runner.run(manifest)
    second = runner.run(manifest)
    assert first.metrics.throughput_tps == pytest.approx(second.metrics.throughput_tps)
    assert first.metrics.protocol_latency_ms == pytest.approx(second.metrics.protocol_latency_ms)
    assert first.metrics.end_to_end_latency_ms == pytest.approx(second.metrics.end_to_end_latency_ms)
    assert first.metrics.cpu_utilization_percent == pytest.approx(second.metrics.cpu_utilization_percent)
    assert first.metrics.normalized_energy == pytest.approx(second.metrics.normalized_energy)
    assert first.calibration_hash == second.calibration_hash

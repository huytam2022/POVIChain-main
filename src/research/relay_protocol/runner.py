import hashlib
import os
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

from povichain.core.errors import ManifestError
from povichain.ingestion.calibration_loader import (
    hash_calibration_artifact,
    load_processed_calibration,
)
from povichain.simulation.network import load_network_preset
from povichain.simulation.workload import WorkloadGenerator, load_workload_profile

from .destination_chain import RelayDestinationChain
from .light_client import RelayLightClient
from .manifest import RelayManifest, load_relay_manifest
from .merkle_verifier import RelayMerkleVerifier
from .metrics_collector import RelayMetricsCollector, IbcMetricsSnapshot
from .packet import RelayPacket
from .packet_lifecycle import RelayPacketLifecycle, PacketLifecycleOutcome
from .protocol_profile import build_replays, load_relay_protocol_profile
from .relayer import RelayAgent
from .source_chain import RelaySourceChain


@dataclass
class RelayRunResult:
    experiment_id: str
    baseline: str
    mode: str
    metrics: IbcMetricsSnapshot
    outcomes: Tuple[PacketLifecycleOutcome, ...]
    protocol_profile_name: str
    network_preset: str
    replay_mode: str
    calibration_hash: Optional[str]
    provenance: Dict[str, str] = field(default_factory=dict)


def _packet_commit_digest(
    sequence: int, channel: str, sender: int, payload_bytes: int, submitted_at_ms: float
) -> bytes:
    h = hashlib.sha256()
    h.update(b"IBC_PACKET_DIGEST|")
    h.update(sequence.to_bytes(8, "big", signed=False))
    h.update(b"|")
    h.update(channel.encode("utf-8"))
    h.update(b"|")
    h.update(str(sender).encode("utf-8"))
    h.update(b"|")
    h.update(str(payload_bytes).encode("utf-8"))
    h.update(b"|")
    h.update(str(int(submitted_at_ms * 1000.0)).encode("utf-8"))
    return h.digest()


def _resolve_profile_path(configs_root: str, name: str) -> str:
    profiles_dir = os.path.join(configs_root, "profiles")
    candidate = os.path.join(profiles_dir, name + ".yaml")
    if os.path.isfile(candidate):
        return profiles_dir
    candidate = os.path.join(profiles_dir, name + ".json")
    if os.path.isfile(candidate):
        return profiles_dir
    defaults_dir = os.path.join(configs_root, "defaults")
    candidate = os.path.join(defaults_dir, name + ".yaml")
    if os.path.isfile(candidate):
        return defaults_dir
    candidate = os.path.join(defaults_dir, name + ".json")
    if os.path.isfile(candidate):
        return defaults_dir
    raise ManifestError("relay_protocol_profile_not_found:" + name)


def _resolve_device_profile_path(data_root: str, name: str) -> str:
    candidate = os.path.join(data_root, "processed", name + ".processed.yaml")
    if os.path.isfile(candidate):
        return candidate
    candidate = os.path.join(data_root, "processed", name + ".yaml")
    if os.path.isfile(candidate):
        return candidate
    raise ManifestError("relay_protocol_device_profile_not_found:" + name)


@dataclass
class RelayRunner:
    configs_root: str
    schemas_root: str
    data_root: str

    def run_manifest(self, manifest_path: str) -> RelayRunResult:
        manifest = load_relay_manifest(manifest_path)
        return self.run(manifest)

    def run(self, manifest: RelayManifest) -> RelayRunResult:
        protocol_dir = _resolve_profile_path(self.configs_root, manifest.protocol_profile)
        network_dir = _resolve_profile_path(self.configs_root, manifest.network_profile)
        workload_dir = _resolve_profile_path(self.configs_root, manifest.workload_profile)
        profile = load_relay_protocol_profile(protocol_dir, manifest.protocol_profile)
        if profile.replay_mode != manifest.replay_mode:
            raise ManifestError("relay_protocol_replay_mode_mismatch_between_manifest_and_profile")
        replays = build_replays(profile)
        network = load_network_preset(
            network_dir, manifest.network_profile, manifest.replay_mode
        )
        device_profile_path = _resolve_device_profile_path(self.data_root, manifest.device_profile)
        calibration = load_processed_calibration(
            device_profile_path,
            os.path.join(self.schemas_root, "processed_calibration.schema.json"),
        )
        if calibration.calibration_policy.replay_mode != manifest.replay_mode:
            raise ManifestError("relay_protocol_calibration_replay_mode_mismatch")
        calibration_hash = hash_calibration_artifact(device_profile_path)
        workload_profile = load_workload_profile(workload_dir, manifest.workload_profile)
        zones = tuple(z for z, _ in workload_profile.zone_weights)
        workload = WorkloadGenerator(workload_profile, zones)
        metrics = RelayMetricsCollector()
        source_chain = RelaySourceChain(chain_id=profile.source_chain_id)
        light_client = RelayLightClient(
            counterparty_chain_id=profile.source_chain_id,
            storage_footprint_per_header_kb=profile.light_client.storage_per_header_kb,
            retention_headers=profile.light_client.retention_headers,
        )
        verifier = RelayMerkleVerifier(light_client=light_client)
        destination_chain = RelayDestinationChain(
            chain_id=profile.destination_chain_id,
            verifier=verifier,
        )
        relayer = RelayAgent(
            relayer_id="relayer_0",
            concurrent_packets=profile.relayer.concurrent_packets,
            rpc_rtt_replay=replays.relayer_rpc_rtt,
            processing_ms_per_packet_replay=replays.relayer_processing,
            header_verify_ms_replay=replays.light_client_header_verify,
            ack_return_ms_replay=replays.relayer_ack_return,
        )
        lifecycle = RelayPacketLifecycle(
            source_chain=source_chain,
            destination_chain=destination_chain,
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
        total_tx = manifest.tx_per_block * manifest.blocks_to_run
        txs = workload.next_batch(total_tx)
        tx_cursor = 0
        simulation_start_ms = 0.0
        source_clock_ms = 0.0
        destination_ready_ms = 0.0
        max_packets = profile.source.max_packets_per_block

        def submit_arrivals(upto_ms: float) -> None:
            nonlocal tx_cursor
            while tx_cursor < len(txs) and txs[tx_cursor].submitted_at_ms <= upto_ms:
                tx = txs[tx_cursor]
                seq = source_chain.next_sequence()
                digest = _packet_commit_digest(
                    sequence=seq,
                    channel=tx.zone_id,
                    sender=tx.sender,
                    payload_bytes=tx.payload_bytes,
                    submitted_at_ms=tx.submitted_at_ms,
                )
                packet = RelayPacket(
                    sequence=seq,
                    source_channel=tx.zone_id,
                    destination_channel=tx.zone_id + ".counterparty",
                    source_port="transfer",
                    destination_port="transfer",
                    sender=tx.sender,
                    payload_bytes=tx.payload_bytes,
                    submitted_at_ms=tx.submitted_at_ms,
                    commit_digest=digest,
                )
                lifecycle.submit_packet(packet)
                tx_cursor += 1

        for block_no in range(manifest.blocks_to_run):
            block_interval_ms = float(replays.source_block_interval.next_value())
            commit_packet_ms = float(replays.source_commit_packet.next_value())
            proposed_at_ms = source_clock_ms + block_interval_ms
            submit_arrivals(proposed_at_ms)
            if source_chain.pending_packet_count() == 0 and tx_cursor >= len(txs):
                source_clock_ms = proposed_at_ms
                break
            if source_chain.pending_packet_count() == 0:
                source_clock_ms = proposed_at_ms
                continue
            packets_in_block = min(max_packets, source_chain.pending_packet_count())
            commit_duration_ms = commit_packet_ms * float(packets_in_block)
            committed_at_ms = proposed_at_ms + commit_duration_ms
            lifecycle.commit_source_block(
                max_packets_per_block=max_packets,
                proposed_at_ms=proposed_at_ms,
                committed_at_ms=committed_at_ms,
            )
            source_clock_ms = committed_at_ms
            dispatch_interval_ms = float(replays.relayer_dispatch_interval.next_value())
            net_delay_ms = float(network.next_delay_ms())
            dispatch_at_ms = committed_at_ms + dispatch_interval_ms + net_delay_ms
            while relayer.backlog() > 0:
                batch = lifecycle.relay_and_deliver(dispatch_at_ms=dispatch_at_ms)
                receive_start_ms = max(batch.delivered_at_ms, destination_ready_ms)
                outcomes = lifecycle.receive_batch(batch, receive_start_ms=receive_start_ms)
                if outcomes:
                    last_ack = max(o.ack_committed_at_ms for o in outcomes)
                    destination_ready_ms = max(destination_ready_ms, last_ack)
                dispatch_at_ms = max(
                    batch.delivered_at_ms + float(replays.relayer_dispatch_interval.next_value()),
                    committed_at_ms + dispatch_interval_ms,
                )
        simulation_end_ms = max(source_clock_ms, destination_ready_ms)
        metrics.set_simulation_window(simulation_start_ms, simulation_end_ms)
        snap = metrics.snapshot()
        provenance = {
            "manifest_id": manifest.experiment_id,
            "baseline": manifest.baseline,
            "protocol_profile": profile.name,
            "network_preset": network.preset_name(),
            "workload_profile": workload_profile.name,
            "device_profile": manifest.device_profile,
            "calibration_sha256": calibration_hash,
            "replay_mode": manifest.replay_mode,
            "validators": str(manifest.validators),
            "tx_per_block": str(manifest.tx_per_block),
            "blocks_to_run": str(manifest.blocks_to_run),
            "source_chain_id": profile.source_chain_id,
            "destination_chain_id": profile.destination_chain_id,
        }
        return RelayRunResult(
            experiment_id=manifest.experiment_id,
            baseline=manifest.baseline,
            mode=manifest.mode,
            metrics=snap,
            outcomes=lifecycle.outcomes(),
            protocol_profile_name=profile.name,
            network_preset=network.preset_name(),
            replay_mode=manifest.replay_mode,
            calibration_hash=calibration_hash,
            provenance=provenance,
        )

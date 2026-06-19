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

from .channel_state import OracleChannelState
from .dvn import OracleVerifierNetwork, OracleVerifier
from .endpoint import OracleDestinationEndpoint, OracleEndpoint, OracleSourceEndpoint
from .executor import OracleExecutor
from .lifecycle import L0LifecycleOutcome, OraclePacketLifecycle
from .manifest import OracleManifest, load_oracle_manifest
from .message_lib import OracleMessageLib
from .metrics_collector import OracleMetricsCollector, L0MetricsSnapshot
from .nonce_manager import OracleNonceManager
from .protocol_profile import (
    L0ProtocolProfile,
    build_verifier_replays,
    build_replays,
    load_oracle_protocol_profile,
)


@dataclass
class OracleRunResult:
    experiment_id: str
    baseline: str
    mode: str
    metrics: L0MetricsSnapshot
    outcomes: Tuple[L0LifecycleOutcome, ...]
    protocol_profile_name: str
    network_preset: str
    replay_mode: str
    calibration_hash: Optional[str]
    dvn_quorum: Dict[str, int]
    provenance: Dict[str, str] = field(default_factory=dict)


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
    raise ManifestError("oracle_protocol_profile_not_found:" + name)


def _resolve_device_profile_path(data_root: str, name: str) -> str:
    candidate = os.path.join(data_root, "processed", name + ".processed.yaml")
    if os.path.isfile(candidate):
        return candidate
    candidate = os.path.join(data_root, "processed", name + ".yaml")
    if os.path.isfile(candidate):
        return candidate
    raise ManifestError("oracle_protocol_device_profile_not_found:" + name)


@dataclass
class OracleRunner:
    configs_root: str
    schemas_root: str
    data_root: str

    def run_manifest(self, manifest_path: str) -> OracleRunResult:
        manifest = load_oracle_manifest(manifest_path)
        return self.run(manifest)

    def run(self, manifest: OracleManifest) -> OracleRunResult:
        protocol_dir = _resolve_profile_path(self.configs_root, manifest.protocol_profile)
        network_dir = _resolve_profile_path(self.configs_root, manifest.network_profile)
        workload_dir = _resolve_profile_path(self.configs_root, manifest.workload_profile)
        profile = load_oracle_protocol_profile(protocol_dir, manifest.protocol_profile)
        if profile.replay_mode != manifest.replay_mode:
            raise ManifestError("oracle_protocol_replay_mode_mismatch_between_manifest_and_profile")
        total_verifiers = profile.dvn.total_verifiers
        required_quorum = profile.dvn.required_quorum
        if manifest.dvn_quorum_override is not None:
            total_verifiers = int(manifest.dvn_quorum_override.total_verifiers)
            required_quorum = int(manifest.dvn_quorum_override.required)
            if total_verifiers != len(profile.dvn.verifiers):
                raise ManifestError("oracle_protocol_manifest_total_verifiers_must_match_profile")
            if required_quorum > total_verifiers:
                raise ManifestError("oracle_protocol_manifest_required_exceeds_total")
        replays = build_replays(profile)
        verifier_replays = build_verifier_replays(profile)
        network = load_network_preset(network_dir, manifest.network_profile, manifest.replay_mode)
        device_profile_path = _resolve_device_profile_path(self.data_root, manifest.device_profile)
        calibration = load_processed_calibration(
            device_profile_path,
            os.path.join(self.schemas_root, "processed_calibration.schema.json"),
        )
        if calibration.calibration_policy.replay_mode != manifest.replay_mode:
            raise ManifestError("oracle_protocol_calibration_replay_mode_mismatch")
        calibration_hash = hash_calibration_artifact(device_profile_path)
        workload_profile = load_workload_profile(workload_dir, manifest.workload_profile)
        zones = tuple(z for z, _ in workload_profile.zone_weights)
        workload = WorkloadGenerator(workload_profile, zones)

        channel_state = OracleChannelState()
        nonce_manager = OracleNonceManager()
        message_lib = OracleMessageLib(
            packet_header_bytes=profile.message_lib.packet_header_bytes,
            format_latency_replay=replays.packet_format_latency,
            commit_verification_latency_replay=replays.commit_verification_latency,
        )
        verifiers = tuple(
            OracleVerifier(
                verifier_id=r.verifier_id,
                verify_latency_replay=r.verify_latency,
                network_rtt_replay=r.network_rtt,
            )
            for r in verifier_replays
        )
        dvn = OracleVerifierNetwork(
            verifiers=verifiers,
            required_quorum=required_quorum,
            total_verifiers=total_verifiers,
        )
        executor = OracleExecutor(
            execute_latency_replay=replays.lz_receive_execute,
            channel_state=channel_state,
        )
        source_endpoint_core = OracleEndpoint(
            chain_id=profile.source_chain_id, oapp_identifier=profile.source_oapp
        )
        dest_endpoint_core = OracleEndpoint(
            chain_id=profile.destination_chain_id, oapp_identifier=profile.destination_oapp
        )
        source_endpoint = OracleSourceEndpoint(
            endpoint=source_endpoint_core,
            message_lib=message_lib,
            nonce_manager=nonce_manager,
            channel_state=channel_state,
        )
        destination_endpoint = OracleDestinationEndpoint(
            endpoint=dest_endpoint_core,
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
            source_cpu_replay=replays.source_send_cpu,
            dvn_cpu_replay=replays.dvn_cpu,
            destination_cpu_replay=replays.destination_execute_cpu,
            k_cpu_nj_per_1k_cycles=profile.energy.k_cpu_nj_per_1k_cycles,
            k_net_uj_per_kb=profile.energy.k_net_uj_per_kb,
            k_dvn_verify_mj_per_vote=profile.energy.k_dvn_verify_mj_per_vote,
            k_commit_verification_mj=profile.energy.k_commit_verification_mj,
            dvn_verification_payload_bytes=profile.dvn.verification_payload_bytes,
        )

        total_tx = manifest.tx_per_block * manifest.blocks_to_run
        txs = workload.next_batch(total_tx)
        if not txs:
            raise ManifestError("oracle_protocol_workload_produced_no_transactions")
        batch_size = profile.source_endpoint.max_messages_per_batch

        simulation_start_ms = 0.0
        simulation_end_ms = 0.0
        idx = 0
        while idx < len(txs):
            batch_end = min(idx + batch_size, len(txs))
            last_submitted_at_ms = 0.0
            for ti in range(idx, batch_end):
                tx = txs[ti]
                lifecycle.submit_message(
                    counterparty_chain=profile.destination_chain_id,
                    counterparty_oapp=profile.destination_oapp,
                    sender=tx.sender,
                    payload_bytes=tx.payload_bytes,
                    submitted_at_ms=tx.submitted_at_ms,
                )
                if tx.submitted_at_ms > last_submitted_at_ms:
                    last_submitted_at_ms = tx.submitted_at_ms
            net_delay_ms = float(network.next_delay_ms())
            dispatched_at_ms = last_submitted_at_ms + net_delay_ms
            lifecycle.dispatch_verification(dispatched_at_ms=dispatched_at_ms)
            executed = lifecycle.drain_execution()
            if executed:
                latest_exec = max(o.executed_at_ms for o in executed)
                if latest_exec > simulation_end_ms:
                    simulation_end_ms = latest_exec
            idx = batch_end

        extra = lifecycle.drain_execution()
        if extra:
            latest_exec = max(o.executed_at_ms for o in extra)
            if latest_exec > simulation_end_ms:
                simulation_end_ms = latest_exec

        if simulation_end_ms <= simulation_start_ms:
            simulation_end_ms = simulation_start_ms + 1.0
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
            "dvn_total_verifiers": str(total_verifiers),
            "dvn_required_quorum": str(required_quorum),
            "source_chain_id": profile.source_chain_id,
            "destination_chain_id": profile.destination_chain_id,
        }
        return OracleRunResult(
            experiment_id=manifest.experiment_id,
            baseline=manifest.baseline,
            mode=manifest.mode,
            metrics=snap,
            outcomes=lifecycle.outcomes(),
            protocol_profile_name=profile.name,
            network_preset=network.preset_name(),
            replay_mode=manifest.replay_mode,
            calibration_hash=calibration_hash,
            dvn_quorum={
                "total_verifiers": total_verifiers,
                "required": required_quorum,
            },
            provenance=provenance,
        )

import json
import os
from dataclasses import dataclass
from typing import Tuple

from povichain.core.errors import ManifestError
from povichain.ingestion.trace_loader import TraceReplay, make_replay


def _read_yaml_or_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if path.endswith(".json"):
        return json.loads(text)
    try:
        import yaml
    except Exception as exc:
        raise ManifestError("pyyaml_required_for_ibc_profile") from exc
    return yaml.safe_load(text)


def _series(doc: dict, key: str) -> Tuple[float, ...]:
    node = doc.get(key)
    if not isinstance(node, dict):
        raise ManifestError("ibc_protocol_field_missing:" + key)
    ds = node.get("deterministic_series")
    if not isinstance(ds, list) or not ds:
        raise ManifestError("ibc_protocol_series_missing:" + key)
    return tuple(float(x) for x in ds)


@dataclass(frozen=True)
class IbcSourceChainProfile:
    block_interval_ms: Tuple[float, ...]
    commit_packet_ms: Tuple[float, ...]
    cpu_percent: Tuple[float, ...]
    max_packets_per_block: int


@dataclass(frozen=True)
class IbcDestinationChainProfile:
    block_interval_ms: Tuple[float, ...]
    receive_execute_ms: Tuple[float, ...]
    ack_commit_ms: Tuple[float, ...]
    cpu_percent: Tuple[float, ...]


@dataclass(frozen=True)
class IbcLightClientProfile:
    header_verify_ms: Tuple[float, ...]
    storage_per_header_kb: float
    retention_headers: int


@dataclass(frozen=True)
class IbcMerkleProfile:
    proof_verify_ms: Tuple[float, ...]


@dataclass(frozen=True)
class IbcRelayerProfile:
    concurrent_packets: int
    rpc_rtt_ms: Tuple[float, ...]
    relay_processing_ms_per_packet: Tuple[float, ...]
    cpu_percent: Tuple[float, ...]
    ack_return_ms: Tuple[float, ...]
    dispatch_interval_ms: Tuple[float, ...]


@dataclass(frozen=True)
class IbcEnergyCoefficients:
    k_cpu_nj_per_1k_cycles: float
    k_net_uj_per_kb: float
    k_header_mj_per_update: float
    k_verify_mj_per_proof: float


@dataclass(frozen=True)
class IbcProtocolProfile:
    name: str
    replay_mode: str
    source: IbcSourceChainProfile
    destination: IbcDestinationChainProfile
    light_client: IbcLightClientProfile
    merkle: IbcMerkleProfile
    relayer: IbcRelayerProfile
    energy: IbcEnergyCoefficients
    source_chain_id: str
    destination_chain_id: str


@dataclass
class IbcProtocolReplays:
    source_block_interval: TraceReplay
    source_commit_packet: TraceReplay
    source_cpu: TraceReplay
    destination_block_interval: TraceReplay
    destination_receive_execute: TraceReplay
    destination_ack_commit: TraceReplay
    destination_cpu: TraceReplay
    light_client_header_verify: TraceReplay
    merkle_proof_verify: TraceReplay
    relayer_rpc_rtt: TraceReplay
    relayer_processing: TraceReplay
    relayer_cpu: TraceReplay
    relayer_ack_return: TraceReplay
    relayer_dispatch_interval: TraceReplay


def load_relay_protocol_profile(configs_root: str, name: str) -> IbcProtocolProfile:
    candidate = os.path.join(configs_root, name + ".yaml")
    if not os.path.isfile(candidate):
        candidate = os.path.join(configs_root, name + ".json")
    if not os.path.isfile(candidate):
        raise ManifestError("ibc_protocol_profile_not_found:" + name)
    doc = _read_yaml_or_json(candidate)
    if not isinstance(doc, dict):
        raise ManifestError("ibc_protocol_profile_root_must_be_mapping")
    replay_mode = str(doc.get("replay_mode", "exact_cycle"))
    src = doc.get("source_chain")
    if not isinstance(src, dict):
        raise ManifestError("ibc_protocol_source_chain_missing")
    dst = doc.get("destination_chain")
    if not isinstance(dst, dict):
        raise ManifestError("ibc_protocol_destination_chain_missing")
    lc = doc.get("light_client")
    if not isinstance(lc, dict):
        raise ManifestError("ibc_protocol_light_client_missing")
    mk = doc.get("merkle_verifier")
    if not isinstance(mk, dict):
        raise ManifestError("ibc_protocol_merkle_verifier_missing")
    rl = doc.get("relayer")
    if not isinstance(rl, dict):
        raise ManifestError("ibc_protocol_relayer_missing")
    en = doc.get("energy")
    if not isinstance(en, dict):
        raise ManifestError("ibc_protocol_energy_missing")
    source = IbcSourceChainProfile(
        block_interval_ms=_series(src, "block_interval_ms"),
        commit_packet_ms=_series(src, "commit_packet_ms"),
        cpu_percent=_series(src, "cpu_percent"),
        max_packets_per_block=int(src.get("max_packets_per_block", 256)),
    )
    destination = IbcDestinationChainProfile(
        block_interval_ms=_series(dst, "block_interval_ms"),
        receive_execute_ms=_series(dst, "receive_execute_ms"),
        ack_commit_ms=_series(dst, "ack_commit_ms"),
        cpu_percent=_series(dst, "cpu_percent"),
    )
    light_client = IbcLightClientProfile(
        header_verify_ms=_series(lc, "header_verify_ms"),
        storage_per_header_kb=float(lc.get("storage_per_header_kb", 2.0)),
        retention_headers=int(lc.get("retention_headers", 128)),
    )
    merkle = IbcMerkleProfile(proof_verify_ms=_series(mk, "proof_verify_ms"))
    relayer = IbcRelayerProfile(
        concurrent_packets=int(rl.get("concurrent_packets", 128)),
        rpc_rtt_ms=_series(rl, "rpc_rtt_ms"),
        relay_processing_ms_per_packet=_series(rl, "relay_processing_ms_per_packet"),
        cpu_percent=_series(rl, "cpu_percent"),
        ack_return_ms=_series(rl, "ack_return_ms"),
        dispatch_interval_ms=_series(rl, "dispatch_interval_ms"),
    )
    energy = IbcEnergyCoefficients(
        k_cpu_nj_per_1k_cycles=float(en["k_cpu_nj_per_1k_cycles"]),
        k_net_uj_per_kb=float(en["k_net_uj_per_kb"]),
        k_header_mj_per_update=float(en.get("k_header_mj_per_update", 0.0)),
        k_verify_mj_per_proof=float(en.get("k_verify_mj_per_proof", 0.0)),
    )
    return IbcProtocolProfile(
        name=str(doc.get("name", name)),
        replay_mode=replay_mode,
        source=source,
        destination=destination,
        light_client=light_client,
        merkle=merkle,
        relayer=relayer,
        energy=energy,
        source_chain_id=str(doc.get("source_chain_id", "chain_a")),
        destination_chain_id=str(doc.get("destination_chain_id", "chain_b")),
    )


def build_replays(profile: IbcProtocolProfile) -> IbcProtocolReplays:
    mode = profile.replay_mode
    return IbcProtocolReplays(
        source_block_interval=make_replay(mode, profile.source.block_interval_ms),
        source_commit_packet=make_replay(mode, profile.source.commit_packet_ms),
        source_cpu=make_replay(mode, profile.source.cpu_percent),
        destination_block_interval=make_replay(mode, profile.destination.block_interval_ms),
        destination_receive_execute=make_replay(mode, profile.destination.receive_execute_ms),
        destination_ack_commit=make_replay(mode, profile.destination.ack_commit_ms),
        destination_cpu=make_replay(mode, profile.destination.cpu_percent),
        light_client_header_verify=make_replay(mode, profile.light_client.header_verify_ms),
        merkle_proof_verify=make_replay(mode, profile.merkle.proof_verify_ms),
        relayer_rpc_rtt=make_replay(mode, profile.relayer.rpc_rtt_ms),
        relayer_processing=make_replay(mode, profile.relayer.relay_processing_ms_per_packet),
        relayer_cpu=make_replay(mode, profile.relayer.cpu_percent),
        relayer_ack_return=make_replay(mode, profile.relayer.ack_return_ms),
        relayer_dispatch_interval=make_replay(mode, profile.relayer.dispatch_interval_ms),
    )

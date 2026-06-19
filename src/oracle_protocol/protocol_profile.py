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
        raise ManifestError("pyyaml_required_for_l0_profile") from exc
    return yaml.safe_load(text)


def _series(doc: dict, key: str) -> Tuple[float, ...]:
    node = doc.get(key)
    if not isinstance(node, dict):
        raise ManifestError("l0_protocol_field_missing:" + key)
    ds = node.get("deterministic_series")
    if not isinstance(ds, list) or not ds:
        raise ManifestError("l0_protocol_series_missing:" + key)
    return tuple(float(x) for x in ds)


@dataclass(frozen=True)
class L0SourceEndpointProfile:
    packet_format_latency_ms: Tuple[float, ...]
    source_send_cpu_percent: Tuple[float, ...]
    max_messages_per_batch: int


@dataclass(frozen=True)
class L0DestinationEndpointProfile:
    lz_receive_execute_ms: Tuple[float, ...]
    destination_execute_cpu_percent: Tuple[float, ...]


@dataclass(frozen=True)
class L0MessageLibProfile:
    packet_header_bytes: int
    commit_verification_latency_ms: Tuple[float, ...]


@dataclass(frozen=True)
class L0DvnVerifierSpec:
    verifier_id: str
    verify_latency_ms: Tuple[float, ...]
    network_rtt_ms: Tuple[float, ...]


@dataclass(frozen=True)
class L0DvnProfile:
    total_verifiers: int
    required_quorum: int
    verifiers: Tuple[L0DvnVerifierSpec, ...]
    dvn_cpu_percent: Tuple[float, ...]
    verification_payload_bytes: int


@dataclass(frozen=True)
class L0EnergyCoefficients:
    k_cpu_nj_per_1k_cycles: float
    k_net_uj_per_kb: float
    k_dvn_verify_mj_per_vote: float
    k_commit_verification_mj: float


@dataclass(frozen=True)
class L0ProtocolProfile:
    name: str
    replay_mode: str
    source_chain_id: str
    destination_chain_id: str
    source_oapp: str
    destination_oapp: str
    source_endpoint: L0SourceEndpointProfile
    destination_endpoint: L0DestinationEndpointProfile
    message_lib: L0MessageLibProfile
    dvn: L0DvnProfile
    energy: L0EnergyCoefficients


@dataclass
class L0ProtocolReplays:
    packet_format_latency: TraceReplay
    source_send_cpu: TraceReplay
    lz_receive_execute: TraceReplay
    destination_execute_cpu: TraceReplay
    commit_verification_latency: TraceReplay
    dvn_cpu: TraceReplay


@dataclass
class L0DvnVerifierReplays:
    verifier_id: str
    verify_latency: TraceReplay
    network_rtt: TraceReplay


def load_oracle_protocol_profile(configs_root: str, name: str) -> L0ProtocolProfile:
    candidate = os.path.join(configs_root, name + ".yaml")
    if not os.path.isfile(candidate):
        candidate = os.path.join(configs_root, name + ".json")
    if not os.path.isfile(candidate):
        raise ManifestError("l0_protocol_profile_not_found:" + name)
    doc = _read_yaml_or_json(candidate)
    if not isinstance(doc, dict):
        raise ManifestError("l0_protocol_profile_root_must_be_mapping")
    replay_mode = str(doc.get("replay_mode", "exact_cycle"))
    src_ep = doc.get("source_endpoint")
    if not isinstance(src_ep, dict):
        raise ManifestError("l0_protocol_source_endpoint_missing")
    dst_ep = doc.get("destination_endpoint")
    if not isinstance(dst_ep, dict):
        raise ManifestError("l0_protocol_destination_endpoint_missing")
    mlib = doc.get("message_lib")
    if not isinstance(mlib, dict):
        raise ManifestError("l0_protocol_message_lib_missing")
    dvn_node = doc.get("dvn")
    if not isinstance(dvn_node, dict):
        raise ManifestError("l0_protocol_dvn_missing")
    en = doc.get("energy")
    if not isinstance(en, dict):
        raise ManifestError("l0_protocol_energy_missing")
    source = L0SourceEndpointProfile(
        packet_format_latency_ms=_series(src_ep, "packet_format_latency_ms"),
        source_send_cpu_percent=_series(src_ep, "source_send_cpu_percent"),
        max_messages_per_batch=int(src_ep.get("max_messages_per_batch", 32)),
    )
    destination = L0DestinationEndpointProfile(
        lz_receive_execute_ms=_series(dst_ep, "lz_receive_execute_ms"),
        destination_execute_cpu_percent=_series(dst_ep, "destination_execute_cpu_percent"),
    )
    message_lib = L0MessageLibProfile(
        packet_header_bytes=int(mlib.get("packet_header_bytes", 96)),
        commit_verification_latency_ms=_series(mlib, "commit_verification_latency_ms"),
    )
    verifiers_node = dvn_node.get("verifiers")
    if not isinstance(verifiers_node, list) or not verifiers_node:
        raise ManifestError("l0_protocol_dvn_verifiers_missing")
    verifier_specs = []
    for v in verifiers_node:
        if not isinstance(v, dict):
            raise ManifestError("l0_protocol_dvn_verifier_entry_invalid")
        verifier_specs.append(
            L0DvnVerifierSpec(
                verifier_id=str(v["verifier_id"]),
                verify_latency_ms=_series(v, "verify_latency_ms"),
                network_rtt_ms=_series(v, "network_rtt_ms"),
            )
        )
    dvn_profile = L0DvnProfile(
        total_verifiers=int(dvn_node.get("total_verifiers", len(verifier_specs))),
        required_quorum=int(dvn_node.get("required_quorum", max(1, len(verifier_specs) - 1))),
        verifiers=tuple(verifier_specs),
        dvn_cpu_percent=_series(dvn_node, "dvn_cpu_percent"),
        verification_payload_bytes=int(dvn_node.get("verification_payload_bytes", 512)),
    )
    if dvn_profile.total_verifiers != len(verifier_specs):
        raise ManifestError("l0_protocol_dvn_total_verifiers_mismatch")
    if dvn_profile.required_quorum > dvn_profile.total_verifiers:
        raise ManifestError("l0_protocol_dvn_required_exceeds_total")
    if dvn_profile.required_quorum <= 0:
        raise ManifestError("l0_protocol_dvn_required_must_be_positive")
    energy = L0EnergyCoefficients(
        k_cpu_nj_per_1k_cycles=float(en["k_cpu_nj_per_1k_cycles"]),
        k_net_uj_per_kb=float(en["k_net_uj_per_kb"]),
        k_dvn_verify_mj_per_vote=float(en.get("k_dvn_verify_mj_per_vote", 0.0)),
        k_commit_verification_mj=float(en.get("k_commit_verification_mj", 0.0)),
    )
    return L0ProtocolProfile(
        name=str(doc.get("name", name)),
        replay_mode=replay_mode,
        source_chain_id=str(doc.get("source_chain_id", "chain_a")),
        destination_chain_id=str(doc.get("destination_chain_id", "chain_b")),
        source_oapp=str(doc.get("source_oapp", "oapp_a")),
        destination_oapp=str(doc.get("destination_oapp", "oapp_b")),
        source_endpoint=source,
        destination_endpoint=destination,
        message_lib=message_lib,
        dvn=dvn_profile,
        energy=energy,
    )


def build_replays(profile: L0ProtocolProfile) -> L0ProtocolReplays:
    mode = profile.replay_mode
    return L0ProtocolReplays(
        packet_format_latency=make_replay(mode, profile.source_endpoint.packet_format_latency_ms),
        source_send_cpu=make_replay(mode, profile.source_endpoint.source_send_cpu_percent),
        lz_receive_execute=make_replay(mode, profile.destination_endpoint.lz_receive_execute_ms),
        destination_execute_cpu=make_replay(
            mode, profile.destination_endpoint.destination_execute_cpu_percent
        ),
        commit_verification_latency=make_replay(
            mode, profile.message_lib.commit_verification_latency_ms
        ),
        dvn_cpu=make_replay(mode, profile.dvn.dvn_cpu_percent),
    )


def build_verifier_replays(profile: L0ProtocolProfile) -> Tuple[L0DvnVerifierReplays, ...]:
    mode = profile.replay_mode
    out = []
    for v in profile.dvn.verifiers:
        out.append(
            L0DvnVerifierReplays(
                verifier_id=v.verifier_id,
                verify_latency=make_replay(mode, v.verify_latency_ms),
                network_rtt=make_replay(mode, v.network_rtt_ms),
            )
        )
    return tuple(out)

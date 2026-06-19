import json
import os
from dataclasses import dataclass
from typing import Any, Dict

from povichain.core.errors import ManifestError


@dataclass(frozen=True)
class OracleQuorumOverride:
    total_verifiers: int
    required: int


@dataclass(frozen=True)
class OracleManifest:
    experiment_id: str
    baseline: str
    validators: int
    tx_per_block: int
    mode: str
    network_profile: str
    device_profile: str
    workload_profile: str
    protocol_profile: str
    blocks_to_run: int
    replay_mode: str
    dvn_quorum_override: Any
    raw_document: Dict[str, Any]


def _read_yaml_or_json(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise ManifestError("oracle_protocol_manifest_missing:" + path)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if path.endswith(".json"):
        return json.loads(text)
    try:
        import yaml
    except Exception as exc:
        raise ManifestError("pyyaml_required_for_oracle_protocol_manifest") from exc
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict):
        raise ManifestError("oracle_protocol_manifest_root_must_be_mapping")
    return doc


def _parse_dvn_quorum(doc: Dict[str, Any]):
    q = doc.get("dvn_quorum")
    if q is None:
        return None
    if not isinstance(q, dict):
        raise ManifestError("oracle_protocol_manifest_dvn_quorum_must_be_mapping")
    total = int(q.get("total_verifiers"))
    required = int(q.get("required"))
    if total <= 0:
        raise ManifestError("oracle_protocol_manifest_dvn_total_verifiers_invalid")
    if required <= 0 or required > total:
        raise ManifestError("oracle_protocol_manifest_dvn_required_invalid")
    return OracleQuorumOverride(total_verifiers=total, required=required)


def load_oracle_manifest(path: str) -> OracleManifest:
    doc = _read_yaml_or_json(path)
    if str(doc.get("baseline", "")).lower() != "oracle_protocol":
        raise ManifestError("oracle_protocol_manifest_baseline_mismatch")
    replay_mode = "exact_cycle"
    required = [
        "experiment_id",
        "validators",
        "tx_per_block",
        "mode",
        "network_profile",
        "device_profile",
        "workload_profile",
        "protocol_profile",
    ]
    for key in required:
        if key not in doc:
            raise ManifestError("oracle_protocol_manifest_field_missing:" + key)
    return OracleManifest(
        experiment_id=str(doc["experiment_id"]),
        baseline=str(doc["baseline"]),
        validators=int(doc["validators"]),
        tx_per_block=int(doc["tx_per_block"]),
        mode=str(doc["mode"]),
        network_profile=str(doc["network_profile"]),
        device_profile=str(doc["device_profile"]),
        workload_profile=str(doc["workload_profile"]),
        protocol_profile=str(doc["protocol_profile"]),
        blocks_to_run=int(doc.get("blocks_to_run", 32)),
        replay_mode=replay_mode,
        dvn_quorum_override=_parse_dvn_quorum(doc),
        raw_document=doc,
    )

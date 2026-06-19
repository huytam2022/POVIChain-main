import json
import os
from dataclasses import dataclass
from typing import Any, Dict

from povichain.core.errors import ManifestError


@dataclass(frozen=True)
class RelayManifest:
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
    raw_document: Dict[str, Any]


def _read_yaml_or_json(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise ManifestError("relay_protocol_manifest_missing:" + path)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if path.endswith(".json"):
        return json.loads(text)
    try:
        import yaml
    except Exception as exc:
        raise ManifestError("pyyaml_required_for_relay_protocol_manifest") from exc
    doc = yaml.safe_load(text)
    if not isinstance(doc, dict):
        raise ManifestError("relay_protocol_manifest_root_must_be_mapping")
    return doc


def load_relay_manifest(path: str) -> RelayManifest:
    doc = _read_yaml_or_json(path)
    if str(doc.get("baseline", "")).lower() != "relay_protocol":
        raise ManifestError("relay_protocol_manifest_baseline_mismatch")
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
            raise ManifestError("relay_protocol_manifest_field_missing:" + key)
    return RelayManifest(
        experiment_id=str(doc["experiment_id"]),
        baseline=str(doc["baseline"]),
        validators=int(doc["validators"]),
        tx_per_block=int(doc["tx_per_block"]),
        mode=str(doc["mode"]),
        network_profile=str(doc["network_profile"]),
        device_profile=str(doc["device_profile"]),
        workload_profile=str(doc["workload_profile"]),
        protocol_profile=str(doc["protocol_profile"]),
        blocks_to_run=int(doc.get("blocks_to_run", 6)),
        replay_mode=replay_mode,
        raw_document=doc,
    )

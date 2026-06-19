import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict

from ..core.errors import ManifestError
from .validators import load_schema, validate_json_against_schema


@dataclass(frozen=True)
class ReputationWeights:
    alpha: float
    beta: float
    gamma: float
    lambd: float
    delta: float
    eta: float
    mu: float
    r_min: float


@dataclass(frozen=True)
class ExperimentManifest:
    experiment_id: str
    mode: str
    validator_count: int
    tx_per_block: int
    proof_backend: str
    committee_threshold_theta: float
    reputation_weights: ReputationWeights
    network_profile: str
    device_profile_file: str
    routing_profile: str
    energy_profile: str
    workload_profile: str
    malicious_fraction: float
    blocks_to_run: int
    replay_mode: str
    raw_document: Dict[str, Any] = field(default_factory=dict)


def _read_yaml_or_json(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise ManifestError("manifest_file_missing:" + path)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if path.endswith(".json"):
        return json.loads(text)
    try:
        import yaml
    except Exception as exc:
        raise ManifestError("pyyaml_required_for_yaml_manifest") from exc
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ManifestError("manifest_root_must_be_mapping")
    return data


def load_manifest(path: str, schema_path: str) -> ExperimentManifest:
    schema = load_schema(schema_path)
    doc = _read_yaml_or_json(path)
    errs = validate_json_against_schema(doc, schema)
    if errs:
        raise ManifestError("manifest_invalid:" + ";".join(errs))
    rw = doc["reputation_weights"]
    return ExperimentManifest(
        experiment_id=str(doc["experiment_id"]),
        mode=str(doc["mode"]),
        validator_count=int(doc["validator_count"]),
        tx_per_block=int(doc["tx_per_block"]),
        proof_backend=str(doc["proof_backend"]),
        committee_threshold_theta=float(doc["committee_threshold_theta"]),
        reputation_weights=ReputationWeights(
            alpha=float(rw["alpha"]),
            beta=float(rw["beta"]),
            gamma=float(rw["gamma"]),
            lambd=float(rw["lambda"]),
            delta=float(rw["delta"]),
            eta=float(rw.get("eta", 0.02)),
            mu=float(rw.get("mu", 0.0)),
            r_min=float(rw.get("r_min", 0.0)),
        ),
        network_profile=str(doc["network_profile"]),
        device_profile_file=str(doc["device_profile_file"]),
        routing_profile=str(doc["routing_profile"]),
        energy_profile=str(doc["energy_profile"]),
        workload_profile=str(doc["workload_profile"]),
        malicious_fraction=float(doc.get("malicious_fraction", 0.0)),
        blocks_to_run=int(doc.get("blocks_to_run", 20)),
        replay_mode="exact_cycle",
        raw_document=doc,
    )

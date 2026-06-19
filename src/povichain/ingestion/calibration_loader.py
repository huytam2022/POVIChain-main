import hashlib
import json
import os
from typing import Any, Dict, Optional

from ..core.errors import CalibrationError
from .processed_schema import (
    CalibrationPolicy,
    EnergyCoefficientsSchema,
    EspBlock,
    EspRamProfile,
    ProcessedCalibration,
    ProofStack,
    ProverBlock,
    SeriesStats,
)
from .validators import load_schema, validate_json_against_schema


def _read_yaml_or_json(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise CalibrationError("calibration_file_missing:" + path)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if path.endswith(".json"):
        return json.loads(text)
    try:
        import yaml
    except Exception as exc:
        raise CalibrationError("pyyaml_required_for_yaml_calibration") from exc
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise CalibrationError("calibration_root_must_be_mapping")
    return data


def _series_from(d: Optional[Dict[str, Any]]) -> Optional[SeriesStats]:
    if d is None:
        return None
    ds = d.get("deterministic_series")
    if not isinstance(ds, list) or not ds:
        raise CalibrationError("deterministic_series_missing_or_empty")
    return SeriesStats(
        deterministic_series=tuple(float(x) for x in ds),
        median=float(d["median"]) if "median" in d else None,
        ci95_low=float(d["ci95_low"]) if "ci95_low" in d else None,
        ci95_high=float(d["ci95_high"]) if "ci95_high" in d else None,
    )


def _prover_from(d: Optional[Dict[str, Any]]) -> Optional[ProverBlock]:
    if d is None:
        return None
    pl = _series_from(d.get("proving_latency_seconds"))
    cpu = _series_from(d.get("cpu_utilization_percent"))
    mem = _series_from(d.get("resident_memory_mb"))
    if pl is None or cpu is None or mem is None:
        raise CalibrationError("prover_block_incomplete")
    return ProverBlock(
        proving_latency_seconds=pl,
        cpu_utilization_percent=cpu,
        resident_memory_mb=mem,
    )


def _esp_from(d: Optional[Dict[str, Any]]) -> Optional[EspBlock]:
    if d is None:
        return None
    merkle = _series_from(d.get("merkle_verify_latency_ms"))
    if merkle is None:
        raise CalibrationError("esp_merkle_series_missing")
    ram = d.get("ram_profile_kb")
    if not isinstance(ram, dict):
        raise CalibrationError("esp_ram_profile_missing")
    return EspBlock(
        merkle_verify_latency_ms=merkle,
        ram_profile_kb=EspRamProfile(
            resident_baseline=float(ram["resident_baseline"]),
            proof_reception_peak=float(ram["proof_reception_peak"]),
            verification_peak=float(ram["verification_peak"]),
            post_update_return=float(ram["post_update_return"]),
        ),
    )


def load_processed_calibration(path: str, schema_path: str) -> ProcessedCalibration:
    schema = load_schema(schema_path)
    doc = _read_yaml_or_json(path)
    errs = validate_json_against_schema(doc, schema)
    if errs:
        raise CalibrationError("processed_calibration_invalid:" + ";".join(errs))
    source = doc["source_manifest"]
    devices = doc.get("device_profiles", {})
    pi4 = devices.get("raspberry_pi_4", {})
    esp = devices.get("esp32_s3")
    policy = doc["calibration_policy"]
    proof_stack = doc.get("proof_stack")
    ec = doc.get("energy_coefficients")
    return ProcessedCalibration(
        version=int(doc["version"]),
        generated_at=str(source["generated_at"]),
        generated_by=str(source["generated_by"]),
        raw_files=tuple(str(rf["path"]) for rf in source.get("raw_files", [])),
        pi4_groth16=_prover_from(pi4.get("groth16")),
        pi4_stark=_prover_from(pi4.get("stark")),
        esp32=_esp_from(esp) if isinstance(esp, dict) else None,
        calibration_policy=CalibrationPolicy(
            replay_mode=policy["replay_mode"],
            interpolation=policy["interpolation"],
        ),
        energy_coefficients=(
            EnergyCoefficientsSchema(
                k_cpu_nj_per_1k_cycles=float(ec["k_cpu_nj_per_1k_cycles"]),
                k_net_uj_per_kb=float(ec["k_net_uj_per_kb"]),
            )
            if isinstance(ec, dict)
            else None
        ),
        proof_stack=(
            ProofStack(
                curve=str(proof_stack["curve"]),
                hash=str(proof_stack["hash"]),
                r1cs_constraints=int(proof_stack["r1cs_constraints"]),
                stack=str(proof_stack["stack"]),
            )
            if isinstance(proof_stack, dict)
            else None
        ),
        raw_document=doc,
    )


def hash_calibration_artifact(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

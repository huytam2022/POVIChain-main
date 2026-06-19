import json
import os
from dataclasses import dataclass
from typing import List

from ..core.errors import SchemaError
from .validators import load_schema, validate_json_against_schema


@dataclass(frozen=True)
class RawMeasurement:
    device_class: str
    measurement_type: str
    proof_backend: str
    circuit_family: str
    r1cs_constraints: int
    transcript: str
    run_id: str
    warmup_index: int
    sample_index: int
    value: float
    unit: str
    timestamp_utc: str
    firmware_or_os: str
    notes: str = ""


def _record_from_dict(d: dict) -> RawMeasurement:
    c = d["circuit_profile"]
    return RawMeasurement(
        device_class=d["device_class"],
        measurement_type=d["measurement_type"],
        proof_backend=d["proof_backend"],
        circuit_family=c["family"],
        r1cs_constraints=int(c["r1cs_constraints"]),
        transcript=c["transcript"],
        run_id=d["run_id"],
        warmup_index=int(d["warmup_index"]),
        sample_index=int(d["sample_index"]),
        value=float(d["value"]),
        unit=d["unit"],
        timestamp_utc=d["timestamp_utc"],
        firmware_or_os=d["firmware_or_os"],
        notes=d.get("notes", ""),
    )


def load_raw_measurements(path: str, schema_path: str) -> List[RawMeasurement]:
    if not os.path.isfile(path):
        raise SchemaError("raw_file_missing:" + path)
    schema = load_schema(schema_path)
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, list):
        raise SchemaError("raw_payload_must_be_array")
    out: List[RawMeasurement] = []
    for idx, entry in enumerate(payload):
        errs = validate_json_against_schema(entry, schema)
        if errs:
            raise SchemaError("raw_record_invalid:index=" + str(idx) + ":" + ";".join(errs))
        out.append(_record_from_dict(entry))
    return out

import json
import os
from dataclasses import dataclass
from typing import Dict, Iterator, List, Tuple

from ..core.errors import ManifestError
from ..core.types import Transaction, ZoneId


@dataclass(frozen=True)
class WorkloadProfile:
    name: str
    zone_weights: Tuple[Tuple[ZoneId, int], ...]
    payload_sizes_bytes: Tuple[int, ...]
    tx_arrival_interval_us: float
    senders: int


def _read_yaml_or_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if path.endswith(".json"):
        return json.loads(text)
    try:
        import yaml
    except Exception as exc:
        raise ManifestError("pyyaml_required_for_workload_profile") from exc
    return yaml.safe_load(text)


def load_workload_profile(configs_root: str, name: str) -> WorkloadProfile:
    candidate = os.path.join(configs_root, name + ".yaml")
    if not os.path.isfile(candidate):
        candidate = os.path.join(configs_root, name + ".json")
    if not os.path.isfile(candidate):
        raise ManifestError("workload_profile_not_found:" + name)
    doc = _read_yaml_or_json(candidate)
    zone_weights = tuple(
        (str(z["zone_id"]), int(z["weight"])) for z in doc["zone_weights"]
    )
    payload_sizes = tuple(int(x) for x in doc["payload_sizes_bytes"])
    if not payload_sizes:
        raise ManifestError("workload_payload_sizes_empty")
    if not zone_weights:
        raise ManifestError("workload_zone_weights_empty")
    return WorkloadProfile(
        name=str(doc.get("name", name)),
        zone_weights=zone_weights,
        payload_sizes_bytes=payload_sizes,
        tx_arrival_interval_us=float(doc.get("tx_arrival_interval_us", 1000.0)),
        senders=int(doc.get("senders", 128)),
    )


def _expand_zones(weights: Tuple[Tuple[ZoneId, int], ...]) -> Tuple[ZoneId, ...]:
    out: List[ZoneId] = []
    for zid, w in weights:
        for _ in range(max(0, int(w))):
            out.append(zid)
    if not out:
        raise ManifestError("workload_expanded_zones_empty")
    return tuple(out)


class WorkloadGenerator:
    def __init__(self, profile: WorkloadProfile, allowed_zones: Tuple[ZoneId, ...]) -> None:
        expanded = _expand_zones(profile.zone_weights)
        for z in expanded:
            if z not in allowed_zones:
                raise ManifestError("workload_zone_not_in_registry:" + z)
        self._expanded = expanded
        self._profile = profile
        self._tx_counter = 0
        self._start_ms = 0.0

    def reset(self, start_ms: float = 0.0) -> None:
        self._tx_counter = 0
        self._start_ms = start_ms

    def next_batch(self, count: int) -> Tuple[Transaction, ...]:
        out: List[Transaction] = []
        for _ in range(count):
            idx = self._tx_counter
            zone = self._expanded[idx % len(self._expanded)]
            payload = self._profile.payload_sizes_bytes[idx % len(self._profile.payload_sizes_bytes)]
            sender = idx % max(1, self._profile.senders)
            submitted_at = self._start_ms + (idx * self._profile.tx_arrival_interval_us) / 1000.0
            out.append(
                Transaction(
                    tx_id=idx,
                    sender=sender,
                    zone_id=zone,
                    payload_bytes=int(payload),
                    submitted_at_ms=float(submitted_at),
                    nonce=idx // max(1, self._profile.senders),
                )
            )
            self._tx_counter += 1
        return tuple(out)

    def zone_distribution(self) -> Dict[ZoneId, int]:
        counts: Dict[ZoneId, int] = {}
        for z in self._expanded:
            counts[z] = counts.get(z, 0) + 1
        return counts

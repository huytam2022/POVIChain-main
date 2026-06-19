import json
import os
from dataclasses import dataclass
from typing import Tuple

from ..core.errors import ManifestError
from ..ingestion.trace_loader import TraceReplay, make_replay


@dataclass(frozen=True)
class NetworkPreset:
    name: str
    delay_series_ms: Tuple[float, ...]
    replay_mode: str
    bandwidth_mbps: float
    description: str


@dataclass
class NetworkModel:
    preset: NetworkPreset
    _replay: TraceReplay

    def next_delay_ms(self) -> float:
        return float(self._replay.next_value())

    def preset_name(self) -> str:
        return self.preset.name


def _read_yaml_or_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if path.endswith(".json"):
        return json.loads(text)
    try:
        import yaml
    except Exception as exc:
        raise ManifestError("pyyaml_required_for_network_preset") from exc
    return yaml.safe_load(text)


def load_network_preset(configs_root: str, name: str, replay_mode: str) -> NetworkModel:
    candidate = os.path.join(configs_root, name + ".yaml")
    if not os.path.isfile(candidate):
        candidate = os.path.join(configs_root, name + ".json")
    if not os.path.isfile(candidate):
        raise ManifestError("network_preset_not_found:" + name)
    data = _read_yaml_or_json(candidate)
    series = tuple(float(x) for x in data["delay_series_ms"])
    preset = NetworkPreset(
        name=str(data["name"]),
        delay_series_ms=series,
        replay_mode=str(data.get("replay_mode", replay_mode)),
        bandwidth_mbps=float(data.get("bandwidth_mbps", 100.0)),
        description=str(data.get("description", "")),
    )
    replay = make_replay(preset.replay_mode, series)
    return NetworkModel(preset=preset, _replay=replay)

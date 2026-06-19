from typing import Protocol, Tuple

from ..core.errors import InsufficientCalibrationLength


class TraceReplay(Protocol):
    def next_value(self) -> float: ...

    def peek_mode(self) -> str: ...

    def reset(self) -> None: ...


def _require_series(series: Tuple[float, ...]) -> None:
    if not series:
        raise InsufficientCalibrationLength("empty_series")


class ExactCycleReplay:
    def __init__(self, series: Tuple[float, ...]) -> None:
        _require_series(series)
        self._series = tuple(series)
        self._idx = 0

    def next_value(self) -> float:
        v = self._series[self._idx % len(self._series)]
        self._idx += 1
        return float(v)

    def peek_mode(self) -> str:
        return "exact_cycle"

    def reset(self) -> None:
        self._idx = 0


class ExactOnceReplay:
    def __init__(self, series: Tuple[float, ...]) -> None:
        _require_series(series)
        self._series = tuple(series)
        self._idx = 0

    def next_value(self) -> float:
        if self._idx >= len(self._series):
            raise InsufficientCalibrationLength("exact_once_exhausted")
        v = self._series[self._idx]
        self._idx += 1
        return float(v)

    def peek_mode(self) -> str:
        return "exact_once"

    def reset(self) -> None:
        self._idx = 0


def _median_sorted(series: Tuple[float, ...]) -> float:
    xs = sorted(series)
    n = len(xs)
    mid = n // 2
    if n % 2 == 1:
        return float(xs[mid])
    return float((xs[mid - 1] + xs[mid]) / 2.0)


class MedianFixedReplay:
    def __init__(self, series: Tuple[float, ...], median_override: float = None) -> None:
        _require_series(series)
        self._value = float(median_override) if median_override is not None else _median_sorted(series)

    def next_value(self) -> float:
        return self._value

    def peek_mode(self) -> str:
        return "median_fixed"

    def reset(self) -> None:
        return None


class EnvelopeFixedReplay:
    def __init__(self, series: Tuple[float, ...], band: str) -> None:
        _require_series(series)
        xs = sorted(series)
        if band == "low":
            v = xs[0]
        elif band == "median":
            v = _median_sorted(series)
        elif band == "high":
            v = xs[-1]
        else:
            raise ValueError("envelope_band_unknown:" + band)
        self._value = float(v)
        self._band = band

    def next_value(self) -> float:
        return self._value

    def peek_mode(self) -> str:
        return "envelope_fixed:" + self._band

    def reset(self) -> None:
        return None


def make_replay(mode: str, series: Tuple[float, ...], envelope_band: str = "median", median_override: float = None) -> TraceReplay:
    if mode == "exact_cycle":
        return ExactCycleReplay(series)
    if mode == "exact_once":
        return ExactOnceReplay(series)
    if mode == "median_fixed":
        return MedianFixedReplay(series, median_override=median_override)
    if mode == "envelope_fixed":
        return EnvelopeFixedReplay(series, band=envelope_band)
    raise ValueError("unknown_replay_mode:" + mode)

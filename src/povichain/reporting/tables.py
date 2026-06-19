from typing import Dict, Iterable, List, Tuple


def _format_row(cells: Iterable[str], widths: Tuple[int, ...]) -> str:
    parts = []
    for cell, width in zip(cells, widths):
        parts.append(str(cell).ljust(width))
    return " | ".join(parts)


def _table(header: Tuple[str, ...], rows: Tuple[Tuple[str, ...], ...]) -> str:
    widths = tuple(max(len(str(h)), *(len(str(r[i])) for r in rows)) if rows else len(h) for i, h in enumerate(header))
    lines: List[str] = []
    lines.append(_format_row(header, widths))
    lines.append("-+-".join("-" * w for w in widths))
    for r in rows:
        lines.append(_format_row(r, widths))
    return "\n".join(lines)


def render_metric_table(summary: Dict[str, float]) -> str:
    header = ("metric", "value")
    rows = tuple((k, f"{v:.6f}") for k, v in summary.items())
    return _table(header, rows)


def render_per_zone_table(per_zone: Dict[str, float]) -> str:
    header = ("zone", "tps")
    rows = tuple((z, f"{v:.4f}") for z, v in sorted(per_zone.items()))
    return _table(header, rows)


def render_device_table(cpu: float, mem_mb: float, resident_kb: float, peak_kb: float) -> str:
    header = ("device_metric", "value")
    rows = (
        ("gateway_cpu_percent", f"{cpu:.3f}"),
        ("gateway_memory_mb", f"{mem_mb:.3f}"),
        ("esp32_resident_kb", f"{resident_kb:.3f}"),
        ("esp32_peak_kb", f"{peak_kb:.3f}"),
    )
    return _table(header, rows)

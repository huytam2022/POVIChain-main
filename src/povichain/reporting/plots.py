from typing import Dict


def render_text_bars(series: Dict[str, float], width: int = 40) -> str:
    if not series:
        return ""
    peak = max(max(series.values()), 1e-9)
    lines = []
    label_w = max(len(k) for k in series)
    for key, value in series.items():
        bar_len = int(round((value / peak) * width))
        lines.append(key.ljust(label_w) + " | " + ("#" * max(0, bar_len)) + f" {value:.4f}")
    return "\n".join(lines)

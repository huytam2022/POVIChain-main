# -*- coding: utf-8 -*-
"""Quét ablation ĐO THẬT qua nhiều cấu hình (N, tỉ lệ nút xấu) để lấy dải min-max.

Mỗi cấu hình chạy lại run_ablation (measure.py) -> đọc % suy giảm đo được,
rồi tổng hợp min-max trên toàn bộ cấu hình. Dải báo cáo trong khóa luận lấy từ
đây nên luôn nhất quán với số repo sinh ra.
"""
import io
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))
if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import yaml
from research.ablation.measure import measure

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(_ROOT, "configs", "experiments", "rq4_ablation_base.yaml")

# Các cấu hình quét: thay đổi số validator, tỉ lệ nút xấu, tải/khối và số khối.
CONFIGS = [
    {"validator_count": 100, "malicious_fraction": 0.10, "tx_per_block": 2048, "blocks_to_run": 16},
    {"validator_count": 100, "malicious_fraction": 0.25, "tx_per_block": 8192, "blocks_to_run": 32},
    {"validator_count": 300, "malicious_fraction": 0.25, "tx_per_block": 8192, "blocks_to_run": 32},
    {"validator_count": 300, "malicious_fraction": 0.33, "tx_per_block": 16384, "blocks_to_run": 48},
    {"validator_count": 500, "malicious_fraction": 0.25, "tx_per_block": 8192, "blocks_to_run": 32},
    {"validator_count": 500, "malicious_fraction": 0.33, "tx_per_block": 8192, "blocks_to_run": 32},
    {"validator_count": 500, "malicious_fraction": 0.33, "tx_per_block": 16384, "blocks_to_run": 48},
]

METRICS = ["thr_degradation_pct", "lat_degradation_pct", "energy_degradation_pct"]


def main():
    with open(BASE, "r", encoding="utf-8") as f:
        base_doc = yaml.safe_load(f)

    # ablation_name -> metric -> list of values
    agg = {}
    for cfg in CONFIGS:
        doc = dict(base_doc)
        doc.update(cfg)
        doc["experiment_id"] = "rq4_abl_N%d_m%02d" % (
            cfg["validator_count"], int(cfg["malicious_fraction"] * 100))
        work = tempfile.mkdtemp(prefix="ablsweep_")
        base_path = os.path.join(work, "base.yaml")
        with open(base_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(doc, f, allow_unicode=True, sort_keys=False)
        out = os.path.join(work, "out")
        print("\n### Cấu hình N=%d, mal=%.0f%%" % (
            cfg["validator_count"], cfg["malicious_fraction"] * 100))
        summary = measure(base_path, out)
        for row in summary["ablations"]:
            name = row["ablation"]
            d = agg.setdefault(name, {m: [] for m in METRICS})
            d["thr_degradation_pct"].append(row["thr_degradation_pct"])
            d["lat_degradation_pct"].append(row["lat_degradation_pct"])
            d["energy_degradation_pct"].append(row["energy_degradation_pct"])

    print("\n\n================ DẢI MIN-MAX ĐO ĐƯỢC (qua %d cấu hình) ================" % len(CONFIGS))
    print("| Ablation | Thr ↓ | Lat ↑ | Energy ↑ |")
    print("|---|---|---|---|")
    for name, d in agg.items():
        def rng(vals):
            return "%.1f–%.1f%%" % (min(vals), max(vals))
        print("| %s | %s | %s | %s |" % (
            name, rng(d["thr_degradation_pct"]),
            rng(d["lat_degradation_pct"]), rng(d["energy_degradation_pct"])))


if __name__ == "__main__":
    main()

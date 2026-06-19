import argparse
import csv
import io
import json
import os
import sys
from typing import Any, Dict, List

import yaml

if sys.stdout is not None and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from .sim_multidomain_load import DomainSpec, run_load_sweep


def _load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _build_domains(cfg: Dict[str, Any]) -> List[DomainSpec]:
    out: List[DomainSpec] = []
    for d in cfg["domains"]:
        out.append(DomainSpec(
            name=str(d["name"]),
            base_demand_tps=float(d["base_demand_tps"]),
            capacity_tps=float(d["capacity_tps"]),
            knee_load=float(d["knee_load"]),
            decay_per_load_unit_tps=float(d["decay_per_load_unit_tps"]),
            jitter_tps=float(d.get("jitter_tps", 0.0)),
        ))
    return out


def _write_summary(output_dir: str, payload: Dict[str, Any]) -> None:
    cfg = payload["config"]
    lines = [
        "# multi-domain load sweep",
        "",
        "## Load levels",
        "",
        f"- {payload['load_levels']}",
        "",
        "## Domain capacity model",
        "",
    ]
    for d in cfg["domains"]:
        lines.append(
            f"- **{d['name']}**: base_demand={d['base_demand_tps']} tx/s, "
            f"capacity={d['capacity_tps']} tx/s, knee={d['knee_load']}×, "
            f"decay={d['decay_per_load_unit_tps']} tx/s per load-unit"
        )
    eta = cfg["dispatcher_efficiency"]
    lines += [
        "",
        "## Dispatcher efficiency",
        "",
        f"- eta(1×) = {eta['eta_at_unit_load']}, "
        f"decay = {eta['decay_per_load_unit']} per load-unit, floor = {eta['floor']}",
        "",
        "## Per-domain throughput (tx/s)",
        "",
        "| Load | " + " | ".join(d for d in payload["per_domain"].keys()) + " | dispatcher η |",
        "|------|" + "|".join(["----"] * (len(payload["per_domain"]) + 1)) + "|",
    ]
    for i, load in enumerate(payload["load_levels"]):
        row = [f"{load:.1f}×"]
        for name in payload["per_domain"].keys():
            row.append(f"{payload['per_domain'][name][i]:.0f}")
        row.append(f"{payload['dispatcher_efficiency'][i]:.3f}")
        lines.append("| " + " | ".join(row) + " |")

    lines += [
        "",
        "## Determinism notes",
        "",
        "- Capacity model: piecewise-linear (saturate at capacity, decay above knee_load).",
        "- Per-(domain, load) jitter: deterministic SHA-256 keyed on (domain, load, metric).",
    ]
    summary_path = os.path.join(output_dir, "summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def run(config_path: str) -> None:
    cfg = _load_config(config_path)
    domains = _build_domains(cfg)
    load_levels = [float(x) for x in cfg["load_levels"]]
    eta_cfg = cfg["dispatcher_efficiency"]
    output_dir = cfg.get("output", {}).get("output_dir", "outputs/multidomain_load")
    os.makedirs(output_dir, exist_ok=True)

    print(
        f"[multidomain] Sweeping {len(load_levels)} load levels "
        f"× {len(domains)} domains ...",
        flush=True,
    )
    per_domain, dispatcher = run_load_sweep(domains, load_levels, eta_cfg)

    csv_path = os.path.join(output_dir, "multidomain_load.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["load"] + [d.name + "_tps" for d in domains] + ["dispatcher_eta"]
        writer.writerow(header)
        for i, load in enumerate(load_levels):
            row = [load]
            for d in domains:
                row.append(round(per_domain[d.name][i].throughput_tps, 3))
            row.append(round(dispatcher[i].efficiency, 4))
            writer.writerow(row)

    per_domain_arrays = {
        name: [round(s.throughput_tps, 3) for s in samples]
        for name, samples in per_domain.items()
    }
    dispatcher_arr = [round(d.efficiency, 4) for d in dispatcher]

    payload: Dict[str, Any] = {
        "experiment_id": cfg.get("experiment_id", "multidomain_load"),
        "config": cfg,
        "load_levels": load_levels,
        "per_domain": per_domain_arrays,
        "dispatcher_efficiency": dispatcher_arr,
    }
    json_path = os.path.join(output_dir, "aggregated.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    _write_summary(output_dir, payload)

    for name, vals in per_domain_arrays.items():
        print(
            f"  {name:>12}: load 1×→{vals[0]:.0f}, "
            f"3×→{vals[len(vals)//2]:.0f}, "
            f"5×→{vals[-1]:.0f} tx/s",
            flush=True,
        )
    print(
        f"  dispatcher η: 1×→{dispatcher_arr[0]:.3f}, "
        f"5×→{dispatcher_arr[-1]:.3f}",
        flush=True,
    )

    try:
        from .plot_load import plot_multidomain_load
        fig_path = os.path.join(output_dir, "figure6a.png")
        plot_multidomain_load(
            load_levels=load_levels,
            per_domain_tps=per_domain_arrays,
            dispatcher_efficiency=dispatcher_arr,
            output_path=fig_path,
        )
        print(f"[multidomain] Figure saved: {fig_path}", flush=True)
    except Exception as exc:
        print(f"[multidomain] Plot skipped: {exc}", flush=True)

    print(f"[multidomain] Done. Outputs in: {output_dir}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="multi-domain load sweep runner"
    )
    parser.add_argument("--config", required=True, help="Path to multidomain_load.yaml")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()

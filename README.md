# PoVIChain — Lightweight Verifiable Cross-Chain Interoperability for Heterogeneous Edge Networks

A research prototype for **lightweight, verifiable cross-chain interoperability**
targeting IoT services in smart cities. The system combines a protocol core
(Proof-of-Verified-Interaction consensus, Smart Zone dispatching, hybrid
MCU/gateway verification), a deterministic trace-driven simulator for fair
protocol comparison, and a multi-role demonstration dashboard.

Evaluation uses **trace-driven simulation with hardware-calibrated emulation**:
cryptographic latencies are measured on real hardware (Raspberry Pi 4 and
ESP32-S3) and injected into the simulator. The simulation is fully
**deterministic** — re-running yields identical results.

> Associated publication: T.-D. Tran, T. Truong Ha Huy, V.-H. Pham,
> *"PoVIChain: Lightweight and verifiable cross-chain interoperability for
> heterogeneous edge networks,"* **Internet of Things** (Elsevier), vol. 37,
> art. 101917, 2026. DOI: 10.1016/j.iot.2026.101917.

## Code organization

The `src/` tree is split into three clear layers:

- **`src/povichain/`** — the protocol core library (PoVI consensus, cryptography,
  routing, devices, simulation, reporting). Everything else depends on it.
- **`src/research/`** — research/experiment code: the two baselines
  (relay / oracle) and the evaluation runners for the four research questions
  (RQ1–RQ4) plus the fidelity check.
- **`src/demo/`** — demonstration code (a multi-role Streamlit dashboard).

The project runs by placing `src/` on the import path (no package installation
required). The root entry points (`run*.py`, `run_dashboard.*`) add `src/` to
`sys.path` automatically; when invoking modules directly with `python -m`, set
`PYTHONPATH=src`.

## Requirements

- Python 3.10+
- `pyyaml` for the simulation core (manifest/config parsing)
- Demo only: `pip install -r requirements_dashboard.txt`

## Running an experiment

Each experiment is described by a YAML manifest under `configs/experiments/`.
Run it through the command-line entry point:

```bash
python run.py --config configs/experiments/main_comparison_mode_b.yaml
```

Results are written to `outputs/<experiment_id>/` (`*_summary.json`,
`aggregated_metrics.json`, `raw_metrics.json`). Override the destination with
`--output-dir`.

Use it directly from Python (requires `src/` on the path, e.g. `PYTHONPATH=src`):

```python
from povichain.simulation.runner import Runner

runner = Runner(configs_root="configs", schemas_root="schemas", data_root="data")
result = runner.run_manifest("configs/experiments/main_comparison_mode_b.yaml")
```

Selected manifests map to the four research questions:

- `rq1_sybil_collusion.yaml`, `rq1_network_partitions.yaml` — adversarial robustness
- `rq2_multidomain_load.yaml`, `rq2_stress_epochs.yaml` — multi-domain scalability
- `rq3_end_device.yaml`, `rq3_gateway_profile.yaml` — efficiency on IoT devices
- `main_comparison_mode_b.yaml` — comparison against IBC-like / LayerZero-like baselines

Run the two baselines for comparison:

```bash
python run_relay_protocol.py --config configs/experiments/relay_protocol_comparison.yaml
PYTHONPATH=src python -m research.oracle_protocol --config configs/experiments/oracle_protocol_comparison.yaml
```

## Ablation (directly measured)

Quantify the contribution of each architectural pillar by **disabling one at a
time** and **directly measuring** throughput / latency / energy from the
simulator (not applying estimated factors):

```bash
python run_ablation.py
```

Four variants: no reputation weighting, network-wide consensus (no VRF
committee), Full-ZKP consensus (no hybrid verification), and no Smart Zone
dispatching. Results are written to
`outputs/rq4_ablations/measured_{ablations.csv, summary.json, summary.md}`.

## Simulation vs. hardware fidelity check

An internal consistency check: it confirms the simulator faithfully reproduces
the calibrated benchmark values measured on Raspberry Pi 4 and ESP32-S3
(proof-generation / verification latency, CPU, memory) — every value falls
within the 95% confidence interval of the measurement. This is a sanity check
of the deterministic replay mechanism, not an independent model validation
against a new testbed.

```bash
python run_validation.py
```

Results are written to `outputs/validation/fidelity_table.{csv,md}` (maximum
relative deviation ~1.6%).

## Tests

```bash
pytest -q
```

## Demo

```bash
pip install -r requirements_dashboard.txt
python -m streamlit run src/demo/dashboard/streamlit_app.py
```

Or use the launch scripts: `run_dashboard.bat` (Windows) /
`bash run_dashboard.sh` (Linux/macOS). The demo presents three roles: a citizen
(EV charging station, water bill, solar metering), an administrator (epoch
monitoring, validator dashboard, network health), and an inspector
(zero-knowledge identity verification across five credential types).

## Directory structure

```
src/
  povichain/          Protocol core: consensus, crypto, routing, devices, simulation, reporting
  research/           Research/experiment code (baselines + RQ1–RQ4 evaluation)
    relay_protocol/   IBC-like relay baseline simulator
    oracle_protocol/  LayerZero-like oracle baseline simulator
    resilience/       Runner + plots for robustness experiments (RQ1)
    performance/      Runner + plots for performance experiments (RQ2)
    resource_usage/   Runner + plots for device resource usage (RQ3)
    ablation/         Directly-measured ablation (measure.py) + plots (RQ4)
    security_analysis/ Security-economics analysis (ECoC, centralization)
    validation/       Simulator fidelity check (run_validation.py)
  demo/               Demonstration code
    dashboard/        Streamlit interface (kiosk, roles, trace viewer)

configs/
  defaults/           Network, device, energy, and workload profiles
  experiments/        Experiment manifests (Mode A / B and scenarios)
  profiles/           Aggregated protocol profiles

data/                 Input measurement series and schema-compliant bootstrap artifacts
schemas/              JSON Schemas for manifests and calibration data
outputs/              Experiment results
tests/                pytest suite
```

## Reproducibility notes

Protocol logic is decoupled from device measurement data: cryptographic
latencies and resource usage are calibrated offline and injected into the
simulator through schema-standardized injection points. Per-transaction energy
is a protocol-level calibrated value (see
`configs/experiments/end_device.yaml`), consistent across experiments. Thanks to
this separation, results are reproducible once a schema-compliant device
calibration file is provided.

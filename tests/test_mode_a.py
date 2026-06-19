import os
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PLACEHOLDER = os.path.join(
    ROOT, "data", "placeholders", "processed", "device_profiles.placeholder.yaml"
)


def _build_manifest(tmp_path, mode):
    try:
        import yaml
    except Exception:
        pytest.skip("pyyaml_missing")
    manifest = {
        "experiment_id": "test_" + mode,
        "mode": mode,
        "validator_count": 16,
        "tx_per_block": 32,
        "proof_backend": "groth16" if mode == "B" else "none",
        "committee_threshold_theta": 0.2,
        "reputation_weights": {
            "alpha": 0.7,
            "beta": 0.15,
            "gamma": 0.10,
            "lambda": 0.05,
            "delta": 0.25,
            "eta": 0.02,
            "mu": 0.10,
            "r_min": 0.05,
        },
        "network_profile": "network_delay_standard",
        "device_profile_file": PLACEHOLDER,
        "routing_profile": "smart_zones_default",
        "energy_profile": "protocol_energy_default",
        "workload_profile": "multidomain_default",
        "malicious_fraction": 0.0,
        "blocks_to_run": 4,
    }
    path = tmp_path / (mode + ".yaml")
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f)
    return str(path)


def test_mode_a_does_not_inject_proving_latency(tmp_path):
    from povichain.simulation.runner import Runner

    runner = Runner(
        configs_root=os.path.join(ROOT, "configs"),
        schemas_root=os.path.join(ROOT, "schemas"),
        data_root=os.path.join(ROOT, "data"),
    )
    result = runner.run_manifest(_build_manifest(tmp_path, "A"))
    assert result.metrics.proofs_built >= 1
    assert result.mode == "A"
    assert all(sample == 0.0 for sample in result.proving_latency_samples_ms)
    assert all(sample == 0.0 for sample in result.gateway_cpu_samples)

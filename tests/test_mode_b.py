import os
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PLACEHOLDER = os.path.join(
    ROOT, "data", "placeholders", "processed", "device_profiles.placeholder.yaml"
)


def test_mode_b_injects_proving_latency(tmp_path):
    try:
        import yaml
    except Exception:
        pytest.skip("pyyaml_missing")
    from povichain.simulation.runner import Runner

    manifest = {
        "experiment_id": "test_b",
        "mode": "B",
        "validator_count": 16,
        "tx_per_block": 32,
        "proof_backend": "groth16",
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
    path = tmp_path / "b.yaml"
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(manifest, f)
    runner = Runner(
        configs_root=os.path.join(ROOT, "configs"),
        schemas_root=os.path.join(ROOT, "schemas"),
        data_root=os.path.join(ROOT, "data"),
    )
    result = runner.run_manifest(str(path))
    assert result.mode == "B"
    assert any(sample > 0.0 for sample in result.proving_latency_samples_ms)
    assert any(sample > 0.0 for sample in result.gateway_cpu_samples)

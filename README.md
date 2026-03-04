# PoVIChain: Proof-of-Verified-Interaction Chain

**PoVIChain** is a modular cross-chain interoperability architecture for heterogeneous IoT/edge networks, implementing the Proof-of-Verified-Interaction (PoVI) consensus mechanism.

## Overview

This repository contains a Python implementation of the PoVIChain protocol as described in the published paper. The implementation includes:

- **Hybrid three-tier architecture**: MCU-class verifiers, gateway validators, and Smart Zone dispatchers
- **PoVI Consensus**: Reputation-based consensus with VRF committee selection
- **Smart Zone Dispatcher**: Execution zoning for Single-Point-of-Value mitigation
- **ZKP Integration**: Groth16 and STARK proof generation/verification
- **Hardware-calibrated simulation**: Timing based on Raspberry Pi 4 and ESP32 measurements

## Quick Start

### Requirements
- Python 3.10+
- PyYAML
- Node.js (for real ZKP with snarkjs)

### Installation

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install pyyaml

# Install Node.js dependencies (for ZKP)
npm install
```

### Running Experiments

Generate all experimental results (RQ1-RQ4):

```bash
python run.py
```

This will create `output_results.txt` with all scenario results.

### ZKP Demonstration

Run the ZKP demo to see proof generation and verification:

```bash
python demo_zkp.py
```

Test ZKP module:

```bash
python test_zkp.py
```

## Architecture

```
povichain/
├── core/                    # Core protocol logic
│   ├── config.py           # Configuration management
│   ├── consensus.py        # PoVI consensus engine
│   ├── merkle.py          # Merkle tree operations
│   ├── reputation.py      # Reputation tracking
│   ├── types.py           # Data structures
│   └── vrf.py             # VRF implementation
├── zones/                  # Smart Zone dispatcher
│   └── dispatcher.py      # Zone routing logic
├── zkp/                    # ZKP implementation
│   ├── groth16_prover.py  # Groth16/STARK provers
│   └── __init__.py
├── verification/           # Verification (wraps ZKP)
│   └── stub_prover.py
├── experiments/            # RQ1-RQ4 experiments
│   ├── calibrated_runner.py
│   └── runner.py
├── simulator.py           # Main simulation engine
├── formatter.py           # Output formatting
└── run.py                 # Main entry point
```

## ZKP (Zero-Knowledge Proof) System

### Supported Systems

1. **Groth16**: Fast proving (~15s on RPi4), small proofs
2. **STARKs**: Post-quantum, larger proofs (~50s on RPi4)

### Usage

```python
from povichain.zkp import ZKPFactory

# Create prover
prover = ZKPFactory.create_prover("groth16", use_stub=True)

# Generate proof
private_inputs = {'secret': 'hidden_data'}
public_inputs = {'zone_id': 1, 'tx_id': 'abc123'}

proof = prover.generate_proof(private_inputs, public_inputs)
# Returns: {'proof': '...', 'proving_time_ms': 15000, ...}

# Verify proof
is_valid = prover.verify_proof(proof, public_inputs)
```

### Integration with Consensus

ZKP proofs are embedded in `ProofBundle` and verified during consensus:

```python
from povichain.core.types import ProofBundle, ZKProof

# Create proof bundle
bundle = ProofBundle(
    zk_proof=ZKProof(
        system='groth16',
        public_inputs={'zone_id': 2},
        proving_time_ms=15000,
        verification_time_ms=50,
        proof_data=b'...'
    ),
    block_header=header,
    tx_index=0
)

# Verify
bundle.verify_full()      # Full ZKP verification (validators)
bundle.verify_light(root) # Light verification (MCU)
```

## Implementation Notes

### ZKP Backend

The ZKP implementation uses **snarkjs** via Node.js for real Groth16 proofs. Python stub mode is available for testing without Node.js:

```python
# Real ZKP (requires snarkjs)
prover = ZKPFactory.create_prover("groth16", use_stub=False)

# Stub mode (deterministic, fast)
prover = ZKPFactory.create_prover("groth16", use_stub=True)
```

### PoVI Consensus

The consensus implements:
1. **VRF-based committee selection** (Algorithm 1)
2. **Reputation update rules** (Algorithm 2)
3. **Smart Zone dispatch** (Algorithm 3)

Reputation formula:
```
R'ₜ(i) = δ·log(1+S(i)) + (1-δ)·Rₜ(i)
```

## Research Questions (RQs)

### RQ1: Security
- **RQ1.1**: Sybil and collusion attacks with varying malicious fractions
- **RQ1.2**: Network partition recovery

### RQ2: Scalability  
- **RQ2.1**: Multi-domain load testing
- **RQ2.2**: Partition recovery backlog
- **RQ2.3**: Long-horizon throughput stability

### RQ3: IoT Efficiency
- **RQ3.1**: Device calibration traces (CPU/Memory)
- **RQ3.2**: ZKP choice comparison (Groth16 vs STARKs)
- **RQ3.3**: MCU-grade verification profile

### RQ4: Ablation Studies
Impact of removing: Reputation, VRF, Smart Zones; using Full-ZKP

## Configuration

Edit `config.yaml` to adjust simulation parameters:

```yaml
network:
  num_validators: 100
  num_malicious: 10
  
reputation:
  eta: 0.05      # Decay factor
  alpha: 0.70    # Participation weight
  beta: 0.15     # Verification accuracy weight
  delta: 0.25    # Stake vs behavior balance

zkp:
  system: "groth16"  # or "stark"
  groth16_proving_time_ms: 15000
  stark_proving_time_ms: 50000
```

## License

This implementation is provided for academic and research purposes.

## Citation

If you use this code, please cite the original PoVIChain paper.

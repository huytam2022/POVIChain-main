"""Configuration loader for PoVIChain."""
import yaml
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class NetworkConfig:
    num_validators: int
    num_malicious: int
    network_delay_ms: List[int]
    packet_loss_rate: float
    partition_duration: int


@dataclass
class VRFConfig:
    threshold: float
    min_reputation: float


@dataclass
class ReputationConfig:
    eta: float
    alpha: float
    beta: float
    gamma: float
    lambda_penalty: float
    delta: float


@dataclass
class ConsensusConfig:
    epoch_duration_ms: int
    block_size: int
    warmup_epochs: int
    total_epochs: int


@dataclass
class ZKPConfig:
    system: str
    groth16_proving_time_ms: int
    stark_proving_time_ms: int
    verification_time_ms: int


@dataclass
class ExperimentConfig:
    mode: str
    load_factor: float


class Config:
    """Main configuration class."""
    
    def __init__(self, config_path: str = "config.yaml"):
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        
        self.network = NetworkConfig(**data['network'])
        self.vrf = VRFConfig(**data['vrf'])
        self.reputation = ReputationConfig(**data['reputation'])
        self.consensus = ConsensusConfig(**data['consensus'])
        self.zkp = ZKPConfig(**data['zkp'])
        self.experiment = ExperimentConfig(**data['experiment'])
        self.zones = data['zones']
        self.output = data['output']
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'network': self.network.__dict__,
            'vrf': self.vrf.__dict__,
            'reputation': self.reputation.__dict__,
            'consensus': self.consensus.__dict__,
            'zkp': self.zkp.__dict__,
            'experiment': self.experiment.__dict__,
        }

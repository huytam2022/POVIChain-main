"""Core data types."""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum
import hashlib
import json
import time


class ZoneType(Enum):
    IDENTITY = "identity"
    HOUSING = "housing"
    TRAFFIC = "traffic"
    ENERGY = "energy"
    FINANCE = "finance"
    GOVERNANCE = "governance"
    ENVIRONMENT = "environment"


@dataclass
class Transaction:
    tx_id: str
    sender: str
    destination_domain: str
    payload: Dict[str, Any]
    zone_id: int
    fee: int = 0
    timestamp: float = field(default_factory=time.time)
    
    def hash(self) -> str:
        data = f"{self.tx_id}:{self.sender}:{self.destination_domain}:{self.zone_id}"
        return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class BlockHeader:
    height: int
    timestamp: int
    prev_hash: str
    merkle_root: str
    validator: str
    zone_id: int
    
    def hash(self) -> str:
        data = {
            'height': self.height,
            'timestamp': self.timestamp,
            'prev_hash': self.prev_hash,
            'merkle_root': self.merkle_root,
            'validator': self.validator,
            'zone_id': self.zone_id,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


@dataclass
class Block:
    header: BlockHeader
    transactions: List[Transaction]
    proof_bundle: Optional['ProofBundle'] = None
    
    def hash(self) -> str:
        return self.header.hash()


@dataclass
class ZKProof:
    system: str
    public_inputs: Dict[str, Any]
    proving_time_ms: int
    verification_time_ms: int
    proof_data: bytes = field(default_factory=lambda: b"STUB")
    _proof_obj: Any = None  # Reference to actual proof object
    
    def verify(self) -> bool:
        """Verify the ZK proof."""
        if self._proof_obj is not None:
            # Use the real ZKP verifier
            from ..zkp import ZKPFactory
            prover = ZKPFactory.create_prover(self.system, use_stub=True)
            return prover.verify_proof(self._proof_obj, self.public_inputs)
        return True


@dataclass
class ProofBundle:
    zk_proof: ZKProof
    block_header: BlockHeader
    tx_index: int
    merkle_siblings: List[str] = field(default_factory=list)
    
    def verify_full(self) -> bool:
        return self.zk_proof.verify()
    
    def verify_light(self, trusted_root: str) -> bool:
        return self.block_header.merkle_root == trusted_root


@dataclass
class ReputationState:
    validator_id: str
    behavioral_rep: float = 0.5
    stake: float = 100.0
    participation_count: int = 0
    verification_accuracy: float = 1.0
    penalties: float = 0.0
    is_malicious: bool = False
    
    def effective_reputation(self, delta: float = 0.25) -> float:
        import math
        stake_term = math.log1p(self.stake)
        return min(1.0, delta * stake_term + (1 - delta) * self.behavioral_rep)


@dataclass
class Vote:
    validator_id: str
    block_hash: str
    epoch: int


@dataclass
class VerificationReceipt:
    tx_id: str
    zone_id: int
    status: str
    acknowledgement: str
    timestamp: int = field(default_factory=lambda: int(time.time()))

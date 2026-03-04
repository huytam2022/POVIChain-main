"""Reputation engine."""
from typing import Dict, List
from dataclasses import dataclass, field
from .types import ReputationState


@dataclass
class ReputationEngine:
    eta: float = 0.05
    alpha: float = 0.70
    beta: float = 0.15
    gamma: float = 0.10
    lambda_penalty: float = 0.05
    delta: float = 0.25
    
    reputations: Dict[str, ReputationState] = field(default_factory=dict)
    
    def register(self, validator_id: str, stake: float = 100.0, 
                 is_malicious: bool = False):
        self.reputations[validator_id] = ReputationState(
            validator_id=validator_id,
            stake=stake,
            is_malicious=is_malicious
        )
    
    def update(self, validator_id: str,
               participated: bool,
               verified_correctly: bool,
               penalty: float = 0.0):
        if validator_id not in self.reputations:
            return
        
        rep = self.reputations[validator_id]
        delta_a = 1.0 if participated else 0.0
        delta_v = 1.0 if verified_correctly else 0.0
        
        new_rep = (
            (1 - self.eta) * rep.behavioral_rep +
            self.alpha * delta_a +
            self.beta * delta_v -
            self.lambda_penalty * penalty
        )
        
        rep.behavioral_rep = min(1.0, max(0.0, new_rep))
        rep.participation_count += 1 if participated else 0
    
    def get_effective_reputation(self, validator_id: str) -> float:
        if validator_id not in self.reputations:
            return 0.0
        return self.reputations[validator_id].effective_reputation(self.delta)
    
    def get_all_effective_reputations(self) -> Dict[str, float]:
        return {
            vid: rep.effective_reputation(self.delta)
            for vid, rep in self.reputations.items()
        }
    
    def get_total_effective_reputation(self) -> float:
        return sum(self.get_all_effective_reputations().values())
    
    def penalize(self, validator_id: str, amount: float):
        if validator_id in self.reputations:
            rep = self.reputations[validator_id]
            rep.penalties += amount
            rep.behavioral_rep = max(0.0, rep.behavioral_rep - amount)

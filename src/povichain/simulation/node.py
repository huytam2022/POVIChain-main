from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple

from ..core.types import ValidatorId, Vote


class NodeRole(str, Enum):
    VALIDATOR_PROVER = "validator_prover"
    MCU_VERIFIER = "mcu_verifier"


@dataclass
class Node:
    node_id: int
    role: NodeRole
    validator_id: ValidatorId
    stake: float
    malicious: bool
    public_key: bytes
    votes_cast: List[Vote] = field(default_factory=list)
    blocks_proposed: int = 0

    def record_vote(self, vote: Vote) -> None:
        self.votes_cast.append(vote)

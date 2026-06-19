from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from ..core.types import CommitteeRecord, ValidatorId
from .finalization import FinalizationDecision
from .voting import VoteTally


@dataclass
class ConsensusReceipts:
    committees: List[CommitteeRecord] = field(default_factory=list)
    tallies: List[VoteTally] = field(default_factory=list)
    decisions: List[FinalizationDecision] = field(default_factory=list)
    invalid_accepts: int = 0
    committee_stats: Dict[int, int] = field(default_factory=dict)

    def record_committee(self, rec: CommitteeRecord) -> None:
        self.committees.append(rec)
        self.committee_stats[rec.epoch] = len(rec.members)

    def record_tally(self, tally: VoteTally) -> None:
        self.tallies.append(tally)

    def record_decision(self, decision: FinalizationDecision, malicious_ids: Tuple[ValidatorId, ...] = ()) -> None:
        self.decisions.append(decision)
        if decision.finalized and malicious_ids:
            for tally in self.tallies:
                if tally.block_id == decision.block_id:
                    for mid in malicious_ids:
                        if mid in tally.accepted_ids:
                            self.invalid_accepts += 1
                            break
                    break

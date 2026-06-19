from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class EventKind(str, Enum):
    TX_SUBMIT = "tx_submit"
    TX_DISPATCH = "tx_dispatch"
    BLOCK_PROPOSE = "block_propose"
    PROOF_REQUEST = "proof_request"
    PROOF_READY = "proof_ready"
    VERIFY_REQUEST = "verify_request"
    VERIFY_DONE = "verify_done"
    VOTE_CAST = "vote_cast"
    VOTE_AGGREGATE = "vote_aggregate"
    FINALIZE = "finalize"
    HLC_RECEIVE = "hlc_receive"
    EPOCH_ADVANCE = "epoch_advance"
    FEE_SPLIT = "fee_split"


@dataclass(order=True)
class Event:
    time_ms: float
    priority: int
    sequence: int
    kind: EventKind = field(compare=False)
    payload: Dict[str, Any] = field(default_factory=dict, compare=False)

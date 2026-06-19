import hashlib
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class StateCommitment:
    root: bytes
    tx_count: int
    block_id: int


def commit_state(prev_root: bytes, tx_digests: Tuple[bytes, ...], block_id: int) -> StateCommitment:
    h = hashlib.sha256()
    h.update(b"STATE|")
    h.update(prev_root)
    h.update(b"|")
    h.update(str(block_id).encode("utf-8"))
    for d in tx_digests:
        h.update(b"|")
        h.update(d)
    return StateCommitment(root=h.digest(), tx_count=len(tx_digests), block_id=block_id)

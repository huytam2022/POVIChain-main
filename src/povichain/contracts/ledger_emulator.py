import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from ..core.types import BlockHeader, ProofBackend, Transaction
from ..crypto.merkle import merkle_root
from ..crypto.proof_bundle import build_proof_digest
from .receipt import FinalizationReceipt, Receipt
from .state_commitment import commit_state


def tx_leaf_bytes(tx: Transaction) -> bytes:
    return (
        b"TX|"
        + str(tx.tx_id).encode("utf-8")
        + b"|"
        + tx.zone_id.encode("utf-8")
        + b"|"
        + str(tx.sender).encode("utf-8")
        + b"|"
        + str(tx.nonce).encode("utf-8")
        + b"|"
        + str(tx.payload_bytes).encode("utf-8")
    )


def _tx_digest(tx: Transaction) -> bytes:
    return hashlib.sha256(tx_leaf_bytes(tx)).digest()


@dataclass
class BlockSubmission:
    block_id: int
    zone_id: str
    proposer: int
    epoch: int
    proposed_at_ms: float
    transactions: Tuple[Transaction, ...]
    merkle_root: bytes
    state_root: bytes
    parent_id: Optional[int]


@dataclass
class LedgerEmulator:
    proof_backend: ProofBackend
    r1cs_constraints: int
    curve: str
    hash_primitive: str
    _chain_heads: Dict[str, Optional[int]] = field(default_factory=dict)
    _state_roots: Dict[str, bytes] = field(default_factory=dict)
    _finalized: List[FinalizationReceipt] = field(default_factory=list)
    _receipts: List[Receipt] = field(default_factory=list)

    def propose_block(
        self,
        block_id: int,
        zone_id: str,
        proposer: int,
        epoch: int,
        proposed_at_ms: float,
        transactions: Tuple[Transaction, ...],
    ) -> BlockSubmission:
        raw_leaves = tuple(tx_leaf_bytes(tx) for tx in transactions)
        tx_digests = tuple(_tx_digest(tx) for tx in transactions)
        root = merkle_root(raw_leaves) if raw_leaves else hashlib.sha256(b"EMPTY").digest()
        prev_root = self._state_roots.get(zone_id, hashlib.sha256(b"GENESIS|" + zone_id.encode("utf-8")).digest())
        state = commit_state(prev_root, tx_digests, block_id)
        parent = self._chain_heads.get(zone_id)
        return BlockSubmission(
            block_id=block_id,
            zone_id=zone_id,
            proposer=proposer,
            epoch=epoch,
            proposed_at_ms=proposed_at_ms,
            transactions=transactions,
            merkle_root=root,
            state_root=state.root,
            parent_id=parent,
        )

    def finalize(self, submission: BlockSubmission, finalized_at_ms: float) -> FinalizationReceipt:
        receipt = FinalizationReceipt(
            block_id=submission.block_id,
            zone_id=submission.zone_id,
            finalized_at_ms=finalized_at_ms,
            tx_ids=tuple(tx.tx_id for tx in submission.transactions),
            state_root=submission.state_root,
            merkle_root=submission.merkle_root,
        )
        self._finalized.append(receipt)
        self._chain_heads[submission.zone_id] = submission.block_id
        self._state_roots[submission.zone_id] = submission.state_root
        for tx in submission.transactions:
            self._receipts.append(
                Receipt(
                    tx_id=tx.tx_id,
                    block_id=submission.block_id,
                    zone_id=submission.zone_id,
                    success=True,
                    submitted_at_ms=tx.submitted_at_ms,
                    finalized_at_ms=finalized_at_ms,
                )
            )
        return receipt

    def proof_digest_for(self, submission: BlockSubmission) -> bytes:
        return build_proof_digest(
            submission.block_id,
            submission.zone_id,
            submission.merkle_root,
            submission.state_root,
            self.proof_backend,
            self.r1cs_constraints,
            self.curve,
            self.hash_primitive,
        )

    def header_for(self, submission: BlockSubmission) -> BlockHeader:
        return BlockHeader(
            block_id=submission.block_id,
            parent_id=submission.parent_id,
            zone_id=submission.zone_id,
            merkle_root=submission.merkle_root,
            state_root=submission.state_root,
            tx_count=len(submission.transactions),
            proposer=submission.proposer,
            epoch=submission.epoch,
            proposed_at_ms=submission.proposed_at_ms,
        )

    def finalized(self) -> Tuple[FinalizationReceipt, ...]:
        return tuple(self._finalized)

    def receipts(self) -> Tuple[Receipt, ...]:
        return tuple(self._receipts)

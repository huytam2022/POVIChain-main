from typing import Tuple

from ..core.types import ProofBundle
from .merkle import verify_inclusion
from .proof_bundle import build_proof_digest


def verify_proof_bundle(bundle: ProofBundle) -> bool:
    expected = build_proof_digest(
        bundle.block_id,
        bundle.zone_id,
        bundle.merkle_root,
        bundle.state_root,
        bundle.backend,
        bundle.circuit_r1cs,
        bundle.curve,
        bundle.hash_primitive,
    )
    return expected == bundle.proof_digest


def verify_merkle_only(leaf: bytes, path: Tuple[Tuple[bytes, bool], ...], root: bytes) -> bool:
    return verify_inclusion(leaf, path, root)

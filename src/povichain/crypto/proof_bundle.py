import hashlib
from typing import Iterable

from ..core.types import ProofBundle, ProofBackend


def build_proof_digest(
    block_id: int,
    zone_id: str,
    merkle_root: bytes,
    state_root: bytes,
    backend: ProofBackend,
    r1cs: int,
    curve: str,
    hash_primitive: str,
) -> bytes:
    h = hashlib.sha256()
    h.update(b"PROOF|")
    h.update(str(block_id).encode("utf-8"))
    h.update(b"|")
    h.update(zone_id.encode("utf-8"))
    h.update(b"|")
    h.update(merkle_root)
    h.update(b"|")
    h.update(state_root)
    h.update(b"|")
    h.update(backend.value.encode("utf-8"))
    h.update(b"|")
    h.update(str(r1cs).encode("utf-8"))
    h.update(b"|")
    h.update(curve.encode("utf-8"))
    h.update(b"|")
    h.update(hash_primitive.encode("utf-8"))
    return h.digest()


def serialize_bundle(bundle: ProofBundle) -> bytes:
    h = hashlib.sha256()
    h.update(b"BUNDLE|")
    h.update(str(bundle.block_id).encode("utf-8"))
    h.update(b"|")
    h.update(bundle.zone_id.encode("utf-8"))
    h.update(b"|")
    h.update(bundle.backend.value.encode("utf-8"))
    h.update(b"|")
    h.update(bundle.proof_digest)
    h.update(b"|")
    h.update(bundle.state_root)
    h.update(b"|")
    h.update(bundle.merkle_root)
    h.update(b"|")
    h.update(str(bundle.circuit_r1cs).encode("utf-8"))
    h.update(b"|")
    h.update(bundle.curve.encode("utf-8"))
    h.update(b"|")
    h.update(bundle.hash_primitive.encode("utf-8"))
    return h.digest()


def digest_of_leaves(leaves: Iterable[bytes]) -> bytes:
    h = hashlib.sha256()
    for x in leaves:
        h.update(x)
    return h.digest()

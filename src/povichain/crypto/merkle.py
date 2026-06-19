import hashlib
from dataclasses import dataclass
from typing import List, Tuple


def _h(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _leaf(data: bytes) -> bytes:
    return _h(b"\x00" + data)


def _inner(left: bytes, right: bytes) -> bytes:
    return _h(b"\x01" + left + right)


@dataclass
class MerkleTree:
    leaves: Tuple[bytes, ...]
    levels: Tuple[Tuple[bytes, ...], ...]

    def root(self) -> bytes:
        if not self.levels:
            return _h(b"")
        return self.levels[-1][0]

    def inclusion_path(self, index: int) -> Tuple[Tuple[bytes, bool], ...]:
        if index < 0 or index >= len(self.leaves):
            raise IndexError("leaf_index_out_of_range")
        path: List[Tuple[bytes, bool]] = []
        idx = index
        for level in self.levels[:-1]:
            sibling_is_right = (idx % 2 == 0)
            sibling_idx = idx + 1 if sibling_is_right else idx - 1
            if sibling_idx >= len(level):
                sibling = level[idx]
            else:
                sibling = level[sibling_idx]
            path.append((sibling, sibling_is_right))
            idx //= 2
        return tuple(path)


def _build_levels(leaf_hashes: Tuple[bytes, ...]) -> Tuple[Tuple[bytes, ...], ...]:
    if not leaf_hashes:
        return tuple()
    levels: List[Tuple[bytes, ...]] = [tuple(leaf_hashes)]
    cur = list(leaf_hashes)
    while len(cur) > 1:
        nxt: List[bytes] = []
        for i in range(0, len(cur), 2):
            left = cur[i]
            right = cur[i + 1] if i + 1 < len(cur) else cur[i]
            nxt.append(_inner(left, right))
        levels.append(tuple(nxt))
        cur = nxt
    return tuple(levels)


def merkle_root(leaves: Tuple[bytes, ...]) -> bytes:
    hashed = tuple(_leaf(x) for x in leaves)
    levels = _build_levels(hashed)
    if not levels:
        return _h(b"")
    return levels[-1][0]


def build_merkle_tree(leaves: Tuple[bytes, ...]) -> MerkleTree:
    hashed = tuple(_leaf(x) for x in leaves)
    levels = _build_levels(hashed)
    return MerkleTree(leaves=hashed, levels=levels)


def verify_inclusion(leaf: bytes, path: Tuple[Tuple[bytes, bool], ...], root: bytes) -> bool:
    cur = _leaf(leaf)
    for sibling, sibling_is_right in path:
        if sibling_is_right:
            cur = _inner(cur, sibling)
        else:
            cur = _inner(sibling, cur)
    return cur == root

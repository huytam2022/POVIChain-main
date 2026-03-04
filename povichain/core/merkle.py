"""Merkle tree for state verification."""
import hashlib
from typing import List, Optional, Tuple


def hash_data(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def hash_pair(a: bytes, b: bytes) -> bytes:
    if a < b:
        return hash_data(a + b)
    return hash_data(b + a)


class MerkleTree:
    def __init__(self, leaves: List[bytes] = None):
        self.leaves: List[bytes] = leaves or []
        self.layers: List[List[bytes]] = []
        self.root: Optional[bytes] = None
        if self.leaves:
            self._build()
    
    def _build(self):
        self.layers = [self.leaves[:]]
        while len(self.layers[-1]) > 1:
            current = self.layers[-1]
            next_layer = []
            for i in range(0, len(current), 2):
                left = current[i]
                right = current[i + 1] if i + 1 < len(current) else left
                next_layer.append(hash_pair(left, right))
            self.layers.append(next_layer)
        self.root = self.layers[-1][0] if self.layers else None
    
    def add_leaf(self, data: bytes):
        self.leaves.append(hash_data(data))
        self._build()
    
    def get_proof(self, index: int) -> List[Tuple[bytes, str]]:
        if index < 0 or index >= len(self.leaves):
            return []
        proof = []
        for layer in self.layers[:-1]:
            sibling_index = index + 1 if index % 2 == 0 else index - 1
            if sibling_index < len(layer):
                direction = 'right' if index % 2 == 0 else 'left'
                proof.append((layer[sibling_index], direction))
            index //= 2
        return proof
    
    @staticmethod
    def verify_proof(root: bytes, leaf_hash: bytes, 
                     proof: List[Tuple[bytes, str]]) -> bool:
        current = leaf_hash
        for sibling, direction in proof:
            if direction == 'left':
                current = hash_pair(sibling, current)
            else:
                current = hash_pair(current, sibling)
        return current == root

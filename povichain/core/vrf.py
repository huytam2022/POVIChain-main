"""VRF for committee selection."""
import hashlib
import hmac
import secrets
from typing import Tuple


class VRF:
    def __init__(self, secret_key: str = None):
        self._secret_key = secret_key or secrets.token_hex(32)
        self._public_key = hashlib.sha256(self._secret_key.encode()).hexdigest()
    
    @property
    def public_key(self) -> str:
        return self._public_key
    
    def prove(self, seed: str) -> Tuple[int, str]:
        proof = hmac.new(
            self._secret_key.encode(),
            seed.encode(),
            hashlib.sha256
        ).hexdigest()
        output = int(proof[:16], 16)
        return output, proof
    
    def verify(self, seed: str, output: int, proof: str) -> bool:
        expected = hmac.new(
            self._secret_key.encode(),
            seed.encode(),
            hashlib.sha256
        ).hexdigest()
        return proof == expected
    
    @staticmethod
    def output_to_float(output: int, total_range: int = 2**64) -> float:
        return output / total_range


def derive_seed(prev_block_hash: str, random_beacon: str) -> str:
    combined = f"{prev_block_hash}:{random_beacon}"
    return hashlib.sha256(combined.encode()).hexdigest()

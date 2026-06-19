import hashlib
import hmac


def vrf_seed(prev_block_id: bytes, randao: bytes) -> bytes:
    h = hashlib.sha256()
    h.update(b"VRFSEED|")
    h.update(prev_block_id)
    h.update(b"|")
    h.update(randao)
    return h.digest()


def vrf_output(seed: bytes, validator_public_key: bytes) -> bytes:
    return hmac.new(seed, validator_public_key, hashlib.sha256).digest()


def expand_uniform_int(seed: bytes, l_bits: int) -> int:
    if l_bits <= 0:
        raise ValueError("l_bits_must_be_positive")
    digest = hashlib.sha256(b"EXPAND|" + seed).digest()
    n = int.from_bytes(digest, "big")
    mask = (1 << l_bits) - 1
    return n & mask


def vrf_fraction(seed: bytes, validator_public_key: bytes, l_bits: int = 256) -> float:
    y = vrf_output(seed, validator_public_key)
    n = int.from_bytes(y, "big")
    denom = float(1 << l_bits)
    return float(n) / denom

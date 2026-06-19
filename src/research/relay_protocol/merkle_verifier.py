from dataclasses import dataclass

from povichain.crypto.merkle import verify_inclusion

from .light_client import RelayLightClient
from .packet import PacketProofBundle


@dataclass
class RelayMerkleVerifier:
    light_client: RelayLightClient
    _verifications: int = 0
    _failures: int = 0

    def verify(self, bundle: PacketProofBundle) -> bool:
        self._verifications += 1
        header = self.light_client.trusted_header(bundle.source_block_id)
        if header is None:
            self._failures += 1
            return False
        if header.merkle_root != bundle.source_merkle_root:
            self._failures += 1
            return False
        if header.state_root != bundle.source_state_root:
            self._failures += 1
            return False
        ok = verify_inclusion(bundle.commit_leaf, bundle.inclusion_path, header.merkle_root)
        if not ok:
            self._failures += 1
        return ok

    def verifications(self) -> int:
        return self._verifications

    def failures(self) -> int:
        return self._failures

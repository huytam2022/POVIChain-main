from dataclasses import dataclass, field
from typing import Dict, Tuple


ChannelKey = Tuple[str, str, str, str]


@dataclass
class OracleNonceManager:
    _outbound_next: Dict[ChannelKey, int] = field(default_factory=dict)
    _inbound_expected: Dict[ChannelKey, int] = field(default_factory=dict)

    def assign_outbound(
        self,
        src_chain: str,
        dst_chain: str,
        src_oapp: str,
        dst_oapp: str,
    ) -> int:
        key = (src_chain, dst_chain, src_oapp, dst_oapp)
        current = self._outbound_next.get(key, 0)
        nxt = current + 1
        self._outbound_next[key] = nxt
        return nxt

    def peek_outbound(
        self,
        src_chain: str,
        dst_chain: str,
        src_oapp: str,
        dst_oapp: str,
    ) -> int:
        key = (src_chain, dst_chain, src_oapp, dst_oapp)
        return self._outbound_next.get(key, 0)

    def expected_inbound(
        self,
        src_chain: str,
        dst_chain: str,
        src_oapp: str,
        dst_oapp: str,
    ) -> int:
        key = (src_chain, dst_chain, src_oapp, dst_oapp)
        return self._inbound_expected.get(key, 0) + 1

    def is_next_inbound(
        self,
        src_chain: str,
        dst_chain: str,
        src_oapp: str,
        dst_oapp: str,
        nonce: int,
    ) -> bool:
        return int(nonce) == self.expected_inbound(src_chain, dst_chain, src_oapp, dst_oapp)

    def advance_inbound(
        self,
        src_chain: str,
        dst_chain: str,
        src_oapp: str,
        dst_oapp: str,
        nonce: int,
    ) -> None:
        key = (src_chain, dst_chain, src_oapp, dst_oapp)
        expected = self._inbound_expected.get(key, 0) + 1
        if int(nonce) != expected:
            raise ValueError("oracle_nonce_advance_out_of_order")
        self._inbound_expected[key] = int(nonce)

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .message import OracleMessage, OracleAttestation


PathKey = Tuple[str, str, str, str]


@dataclass
class L0ChannelPath:
    src_chain_id: str
    dst_chain_id: str
    src_oapp: str
    dst_oapp: str
    outbound_nonces: List[int] = field(default_factory=list)
    committed_inbound: Dict[int, OracleAttestation] = field(default_factory=dict)
    executed_inbound: List[int] = field(default_factory=list)

    def key(self) -> PathKey:
        return (self.src_chain_id, self.dst_chain_id, self.src_oapp, self.dst_oapp)


@dataclass
class OracleChannelState:
    _paths: Dict[PathKey, L0ChannelPath] = field(default_factory=dict)
    _messages: Dict[bytes, OracleMessage] = field(default_factory=dict)

    def ensure_path(
        self,
        src_chain_id: str,
        dst_chain_id: str,
        src_oapp: str,
        dst_oapp: str,
    ) -> L0ChannelPath:
        key: PathKey = (src_chain_id, dst_chain_id, src_oapp, dst_oapp)
        if key not in self._paths:
            self._paths[key] = L0ChannelPath(
                src_chain_id=src_chain_id,
                dst_chain_id=dst_chain_id,
                src_oapp=src_oapp,
                dst_oapp=dst_oapp,
            )
        return self._paths[key]

    def register_outbound(self, message: OracleMessage) -> L0ChannelPath:
        path = self.ensure_path(
            message.src_chain_id,
            message.dst_chain_id,
            message.src_oapp,
            message.dst_oapp,
        )
        if message.nonce in path.outbound_nonces:
            raise ValueError("l0_channel_duplicate_outbound_nonce")
        if path.outbound_nonces:
            expected = path.outbound_nonces[-1] + 1
            if message.nonce != expected:
                raise ValueError("l0_channel_outbound_nonce_gap")
        else:
            if message.nonce != 1:
                raise ValueError("l0_channel_outbound_nonce_must_start_at_one")
        path.outbound_nonces.append(int(message.nonce))
        self._messages[message.guid] = message
        return path

    def record_commit_verification(
        self,
        message: OracleMessage,
        attestation: OracleAttestation,
    ) -> L0ChannelPath:
        path = self.ensure_path(
            message.src_chain_id,
            message.dst_chain_id,
            message.src_oapp,
            message.dst_oapp,
        )
        if message.nonce in path.committed_inbound:
            raise ValueError("l0_channel_duplicate_commit_verification")
        path.committed_inbound[int(message.nonce)] = attestation
        return path

    def has_committed_verification(self, message: OracleMessage) -> bool:
        path = self.ensure_path(
            message.src_chain_id,
            message.dst_chain_id,
            message.src_oapp,
            message.dst_oapp,
        )
        return int(message.nonce) in path.committed_inbound

    def next_expected_inbound(
        self,
        src_chain_id: str,
        dst_chain_id: str,
        src_oapp: str,
        dst_oapp: str,
    ) -> int:
        path = self.ensure_path(src_chain_id, dst_chain_id, src_oapp, dst_oapp)
        if not path.executed_inbound:
            return 1
        return path.executed_inbound[-1] + 1

    def record_executed(self, message: OracleMessage) -> L0ChannelPath:
        path = self.ensure_path(
            message.src_chain_id,
            message.dst_chain_id,
            message.src_oapp,
            message.dst_oapp,
        )
        expected = 1 if not path.executed_inbound else path.executed_inbound[-1] + 1
        if int(message.nonce) != expected:
            raise ValueError("l0_channel_execute_out_of_order")
        path.executed_inbound.append(int(message.nonce))
        return path

    def paths(self) -> Tuple[L0ChannelPath, ...]:
        return tuple(self._paths.values())

    def message_for(self, guid: bytes) -> OracleMessage:
        return self._messages[guid]

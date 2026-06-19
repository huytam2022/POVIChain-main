import pytest

from povichain.core.errors import DeterminismError
from povichain.crypto.merkle import build_merkle_tree
from povichain.devices.hlc import HLCState, HybridLightClient
from povichain.ingestion.trace_loader import ExactCycleReplay


def _hlc():
    state = HLCState(
        device_id=0,
        resident_kb=100.0,
        peak_kb=250.0,
        reception_peak_kb=130.0,
        verification_peak_kb=250.0,
        post_update_return_kb=110.0,
        ram_now_kb=100.0,
    )
    return HybridLightClient(state=state, latency_replay=ExactCycleReplay((125.0, 150.0)))


def test_hlc_forbids_full_zkp_verification():
    hlc = _hlc()
    with pytest.raises(DeterminismError):
        hlc.verify_zkp_forbidden()


def test_hlc_verifies_merkle_inclusion_only():
    hlc = _hlc()
    leaves = (b"a", b"b", b"c", b"d")
    tree = build_merkle_tree(leaves)
    path = tree.inclusion_path(1)
    from povichain.core.types import BlockHeader

    header = BlockHeader(
        block_id=1,
        parent_id=None,
        zone_id="identity",
        merkle_root=tree.root(),
        state_root=b"\x00" * 32,
        tx_count=4,
        proposer=0,
        epoch=0,
        proposed_at_ms=0.0,
    )
    hlc.attach_header(header)
    ok, latency = hlc.verify_merkle(b"b", path, "identity")
    assert ok is True
    assert latency > 0.0


def test_hlc_ram_lifecycle_transitions():
    hlc = _hlc()
    assert hlc.state.ram_now_kb == 100.0
    hlc.receive_proof()
    assert hlc.state.ram_now_kb == 130.0
    from povichain.core.types import BlockHeader

    header = BlockHeader(
        block_id=2,
        parent_id=None,
        zone_id="traffic",
        merkle_root=build_merkle_tree((b"x",)).root(),
        state_root=b"\x00" * 32,
        tx_count=1,
        proposer=0,
        epoch=0,
        proposed_at_ms=0.0,
    )
    hlc.attach_header(header)
    _ok, _ = hlc.verify_merkle(b"x", tuple(), header.merkle_root) if False else hlc.verify_merkle(b"x", tuple(), "traffic")
    assert hlc.state.ram_now_kb == 110.0
    assert hlc.state.peak_observed_kb >= 250.0

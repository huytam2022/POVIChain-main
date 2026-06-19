import pytest

from povichain.core.errors import DispatcherError
from povichain.core.types import Transaction
from povichain.routing.dispatcher import Dispatcher
from povichain.routing.fee_split import FeeSplitPolicy, apply_fee_split
from povichain.routing.smart_zone import SmartZoneRegistry


def _tx(i, zone):
    return Transaction(
        tx_id=i,
        sender=i % 16,
        zone_id=zone,
        payload_bytes=256,
        submitted_at_ms=float(i),
        nonce=i // 16,
    )


def test_dispatch_queues_by_zone_id():
    dispatcher = Dispatcher(registry=SmartZoneRegistry())
    dispatcher.dispatch(_tx(0, "identity"))
    dispatcher.dispatch(_tx(1, "finance"))
    assert dispatcher.pending("identity") == 1
    assert dispatcher.pending("finance") == 1


def test_dispatch_rejects_unknown_zone():
    dispatcher = Dispatcher(registry=SmartZoneRegistry())
    with pytest.raises(DispatcherError):
        dispatcher.dispatch(_tx(7, "nowhere"))


def test_ex_post_reroute_is_forbidden():
    dispatcher = Dispatcher(registry=SmartZoneRegistry())
    dispatcher.dispatch(_tx(9, "identity"))
    with pytest.raises(DispatcherError):
        dispatcher.dispatch(_tx(9, "finance"))


def test_zone_id_decides_route_and_does_not_change_under_drain():
    dispatcher = Dispatcher(registry=SmartZoneRegistry())
    for i in range(10):
        dispatcher.dispatch(_tx(i, "traffic"))
    drained = dispatcher.drain_batch("traffic", 5)
    assert all(t.zone_id == "traffic" for t in drained)
    assert dispatcher.pending("traffic") == 5


def test_fee_split_conserves_gross_amount_and_respects_shares():
    registry = SmartZoneRegistry()
    zone = registry.get("finance")
    fees = apply_fee_split(zone, 100.0, FeeSplitPolicy())
    assert abs(fees.validator + fees.protocol + fees.treasury - 100.0) < 1e-9
    assert abs(fees.validator - zone.validator_share * 100.0) < 1e-9

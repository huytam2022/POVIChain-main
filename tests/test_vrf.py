from povichain.consensus.committee import CommitteeSelector
from povichain.crypto.vrf import vrf_fraction, vrf_output, vrf_seed


def _eff(n: int) -> dict:
    return {i: 1.0 + (i % 13) * 0.1 for i in range(n)}


def test_vrf_seed_is_deterministic():
    s1 = vrf_seed(b"\x00" * 8, b"randao-1")
    s2 = vrf_seed(b"\x00" * 8, b"randao-1")
    assert s1 == s2


def test_vrf_fraction_in_unit_interval():
    seed = vrf_seed(b"\x01" * 8, b"randao-2")
    frac = vrf_fraction(seed, b"pk|42")
    assert 0.0 <= frac < 1.0


def test_committee_is_deterministic_for_same_seed_and_reps():
    selector = CommitteeSelector(theta=0.25, r_min=0.05)
    reps = _eff(128)
    r1 = selector.select(epoch=7, prev_block_id=1234, randao=b"same", effective_reputations=reps)
    r2 = selector.select(epoch=7, prev_block_id=1234, randao=b"same", effective_reputations=reps)
    assert r1.members == r2.members


def test_committee_changes_with_different_randao():
    selector = CommitteeSelector(theta=0.25, r_min=0.05)
    reps = _eff(128)
    r1 = selector.select(epoch=7, prev_block_id=1234, randao=b"a", effective_reputations=reps)
    r2 = selector.select(epoch=7, prev_block_id=1234, randao=b"b", effective_reputations=reps)
    assert r1.members != r2.members or r1.seed != r2.seed


def test_r_min_excludes_validators():
    selector = CommitteeSelector(theta=1.0, r_min=100.0)
    reps = _eff(32)
    r = selector.select(epoch=1, prev_block_id=0, randao=b"x", effective_reputations=reps)
    assert r.members == ()

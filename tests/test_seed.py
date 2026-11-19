import numpy as np

from screener import SEED, make_rng


def test_seed_is_a_fixed_int():
    assert isinstance(SEED, int)


def test_make_rng_is_reproducible():
    a = make_rng().random(5)
    b = make_rng().random(5)
    assert np.array_equal(a, b)


def test_make_rng_streams_are_independent_but_reproducible():
    s0 = make_rng(0).random(5)
    s1 = make_rng(1).random(5)
    assert not np.array_equal(s0, s1)
    assert np.array_equal(s1, make_rng(1).random(5))

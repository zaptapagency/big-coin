"""Tests for Milestone 9 — Security Analysis (attacker success probability).

Reference values are taken directly from the Bitcoin whitepaper
(Nakamoto 2008, section 11).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calc import (  # noqa: E402
    attacker_success_probability,
    recommend_confirmations,
)


def test_z_zero_is_certain():
    # With zero confirmations the attacker is already even; P = 1.
    assert attacker_success_probability(0.1, 0) == 1.0


def test_whitepaper_q01_z5():
    assert attacker_success_probability(0.1, 5) == pytest.approx(0.0009137, abs=1e-6)


def test_whitepaper_q01_z10():
    assert attacker_success_probability(0.1, 10) == pytest.approx(0.0000012, abs=1e-7)


def test_whitepaper_q03_z5():
    assert attacker_success_probability(0.3, 5) == pytest.approx(0.1773523, abs=1e-6)


def test_monotonic_decreasing_in_z():
    probs = [attacker_success_probability(0.1, z) for z in range(1, 11)]
    for earlier, later in zip(probs, probs[1:]):
        assert later < earlier


def test_higher_q_needs_more_confirmations():
    assert recommend_confirmations(0.1) < recommend_confirmations(0.3)


def test_recommend_q01_is_5():
    assert recommend_confirmations(0.1) == 5


def test_recommend_q03_is_24():
    assert recommend_confirmations(0.3) == 24


@pytest.mark.parametrize(
    "q, expected_z",
    [
        (0.10, 5),
        (0.15, 8),
        (0.20, 11),
        (0.25, 15),
        (0.30, 24),
        (0.35, 41),
        (0.40, 89),
        (0.45, 340),
    ],
)
def test_whitepaper_solving_table(q, expected_z):
    assert recommend_confirmations(q, 0.001) == expected_z


def test_majority_raises():
    with pytest.raises(ValueError):
        recommend_confirmations(0.5)

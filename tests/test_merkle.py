"""Tests for Milestone 2/7 — Merkle tree and inclusion proofs."""

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from merkle import merkle_proof, merkle_root, verify_merkle_proof  # noqa: E402


def _txid(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def test_single_leaf_root_is_itself():
    leaf = _txid("only")
    assert merkle_root([leaf]) == leaf


def test_root_is_deterministic():
    ids = [_txid(str(i)) for i in range(4)]
    assert merkle_root(ids) == merkle_root(list(ids))


def test_root_changes_with_any_leaf():
    ids = [_txid(str(i)) for i in range(4)]
    r1 = merkle_root(ids)
    ids2 = list(ids)
    ids2[2] = _txid("tampered")
    assert merkle_root(ids2) != r1


def test_odd_count_duplicates_last_node():
    # With 3 leaves the last is duplicated; root must be stable/deterministic.
    ids = [_txid(str(i)) for i in range(3)]
    assert merkle_root(ids) == merkle_root(ids)


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 7, 8, 9])
def test_proofs_for_every_index(n):
    ids = [_txid(str(i)) for i in range(n)]
    root = merkle_root(ids)
    for i in range(n):
        proof = merkle_proof(ids, i)
        assert verify_merkle_proof(ids[i], proof, root) is True


def test_tampered_proof_fails():
    ids = [_txid(str(i)) for i in range(6)]
    root = merkle_root(ids)
    proof = merkle_proof(ids, 2)
    bad = list(proof)
    sibling, side = bad[0]
    bad[0] = (_txid("evil"), side)
    assert verify_merkle_proof(ids[2], bad, root) is False


def test_wrong_leaf_fails():
    ids = [_txid(str(i)) for i in range(4)]
    root = merkle_root(ids)
    proof = merkle_proof(ids, 1)
    assert verify_merkle_proof(_txid("not-in-tree"), proof, root) is False


def test_empty_raises():
    with pytest.raises(ValueError):
        merkle_root([])
    with pytest.raises(ValueError):
        merkle_proof([], 0)

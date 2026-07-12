"""Tests for Milestone 2 — Block structure, header hashing, genesis."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from block import (  # noqa: E402
    Block,
    build_block,
    coinbase_height,
    create_coinbase,
    genesis_block,
)
from transaction import pubkey_hash, generate_keypair  # noqa: E402


def _pkh():
    _, pub = generate_keypair()
    return pubkey_hash(pub)


def test_genesis_is_deterministic():
    assert genesis_block().hash == genesis_block().hash


def test_header_hash_changes_with_nonce():
    g = genesis_block()
    h0 = g.hash
    g.header.nonce += 1
    assert g.hash != h0


def test_merkle_root_matches_transactions():
    txs = [create_coinbase(1, _pkh())]
    block = build_block(prev_hash="00" * 32, transactions=txs, bits=8, timestamp=1)
    assert block.has_valid_merkle_root()
    block.transactions[0].outputs[0].amount += 1  # mutate after building
    assert not block.has_valid_merkle_root()


def test_coinbase_uniqueness_by_height_and_nonce():
    pkh = _pkh()
    c1 = create_coinbase(1, pkh)
    c2 = create_coinbase(2, pkh)
    c3 = create_coinbase(1, pkh, extra_nonce="x")
    assert c1.txid != c2.txid  # different height
    assert c1.txid != c3.txid  # different extra-nonce
    assert coinbase_height(c1) == 1 and coinbase_height(c2) == 2


def test_block_serialization_round_trip():
    txs = [create_coinbase(1, _pkh())]
    block = build_block(prev_hash="00" * 32, transactions=txs, bits=8, timestamp=1)
    restored = Block.from_dict(block.to_dict())
    assert restored.hash == block.hash
    assert restored.has_valid_merkle_root()

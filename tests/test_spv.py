"""Tests for Milestone 7: the SPV light client."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from block import BlockHeader, build_block, genesis_block
from merkle import merkle_root
from spv import MerkleProofBundle, SPVClient, build_proof_bundle
from transaction import (
    Transaction,
    TxInput,
    TxOutput,
    generate_keypair,
    pubkey_hash,
)


# --------------------------------------------------------------------------- #
# Helpers: cheap, well-formed transactions (they need not verify — SPV only
# checks Merkle inclusion, not signatures).
# --------------------------------------------------------------------------- #
def make_tx(seed: int) -> Transaction:
    """A distinct, well-formed transaction keyed by `seed` (unique txid)."""
    _sk, pub = generate_keypair()
    return Transaction(
        inputs=[TxInput(prev_txid=f"{seed:064x}", output_index=seed)],
        outputs=[TxOutput(amount=1000 + seed, pubkey_hash=pubkey_hash(pub))],
    )


def make_block(prev_hash: str, n_txs: int, bits: int = 16, timestamp: int = 1):
    """Build a block carrying `n_txs` distinct transactions."""
    txs = [make_tx(i) for i in range(n_txs)]
    return build_block(prev_hash, txs, bits, timestamp)


# --------------------------------------------------------------------------- #
# Inclusion proofs across block sizes (odd/even -> duplicate-last-node rule)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("n_txs", [1, 2, 3, 4, 5])
def test_verify_payment_true_for_included_tx(n_txs):
    genesis = genesis_block()
    block = make_block(genesis.hash, n_txs)

    client = SPVClient()
    assert client.add_header(block.header)

    for tx in block.transactions:
        bundle = build_proof_bundle(block, tx.txid)
        assert client.verify_payment(bundle) is True


def test_bundle_roundtrip_preserves_verification():
    genesis = genesis_block()
    block = make_block(genesis.hash, 3)
    client = SPVClient()
    client.add_header(block.header)

    bundle = build_proof_bundle(block, block.transactions[1].txid)
    restored = MerkleProofBundle.from_dict(bundle.to_dict())

    assert restored.txid == bundle.txid
    assert restored.block_hash == bundle.block_hash
    assert restored.proof == bundle.proof
    assert client.verify_payment(restored) is True


# --------------------------------------------------------------------------- #
# Negative cases
# --------------------------------------------------------------------------- #
def test_verify_payment_false_for_tampered_proof():
    genesis = genesis_block()
    block = make_block(genesis.hash, 4)
    client = SPVClient()
    client.add_header(block.header)

    bundle = build_proof_bundle(block, block.transactions[0].txid)
    # Flip a hash in the branch -> root no longer recomputes.
    sibling, side = bundle.proof[0]
    flipped = ("f" + sibling[1:]) if sibling[0] != "f" else ("0" + sibling[1:])
    bundle.proof[0] = (flipped, side)

    assert client.verify_payment(bundle) is False


def test_verify_payment_false_for_wrong_block():
    genesis = genesis_block()
    block_a = make_block(genesis.hash, 3)
    client = SPVClient()
    client.add_header(block_a.header)

    # Build a valid bundle, then point it at a block the client does not know.
    bundle = build_proof_bundle(block_a, block_a.transactions[0].txid)
    bundle.block_hash = "a" * 64
    assert client.verify_payment(bundle) is False


def test_verify_payment_false_when_txid_not_in_claimed_block():
    genesis = genesis_block()
    block_a = make_block(genesis.hash, 3)
    block_b = build_block(block_a.hash, [make_tx(99), make_tx(100)], 16, 2)

    client = SPVClient()
    client.add_header(block_a.header)
    client.add_header(block_b.header)

    # Proof built against block_a, but claimed to be in block_b.
    bundle = build_proof_bundle(block_a, block_a.transactions[0].txid)
    bundle.block_hash = block_b.hash
    assert client.verify_payment(bundle) is False


def test_build_proof_bundle_raises_for_unknown_txid():
    genesis = genesis_block()
    block = make_block(genesis.hash, 3)
    with pytest.raises(ValueError):
        build_proof_bundle(block, "d" * 64)


# --------------------------------------------------------------------------- #
# Header chain: height & confirmations
# --------------------------------------------------------------------------- #
def test_client_seeded_with_genesis():
    client = SPVClient()
    assert client.height == 0
    assert client.tip_hash == genesis_block().hash
    assert client.header_by_hash(genesis_block().hash) is not None


def test_height_and_confirmations_grow_with_chain():
    genesis = genesis_block()
    client = SPVClient()

    prev = genesis.hash
    blocks = []
    for i in range(5):
        blk = make_block(prev, n_txs=2, timestamp=10 + i)
        assert client.add_header(blk.header)
        blocks.append(blk)
        prev = blk.hash

    assert client.height == 5  # genesis + 5

    # The first added block is now 5 deep (itself + 4 on top).
    assert client.confirmations(blocks[0].hash) == 5
    # The tip has exactly 1 confirmation.
    assert client.confirmations(blocks[-1].hash) == 1
    # Unknown block -> 0.
    assert client.confirmations("b" * 64) == 0


def test_block_with_tx_reports_n_confirmations():
    """A block with the payment, plus N-1 headers on top, reports N confs."""
    genesis = genesis_block()
    client = SPVClient()

    payment_block = make_block(genesis.hash, n_txs=3, timestamp=100)
    assert client.add_header(payment_block.header)

    # Add 3 more headers on top -> total depth 4.
    prev = payment_block.hash
    for i in range(3):
        blk = make_block(prev, n_txs=1, timestamp=200 + i)
        assert client.add_header(blk.header)
        prev = blk.hash

    assert client.confirmations(payment_block.hash) == 4

    bundle = build_proof_bundle(payment_block, payment_block.transactions[0].txid)
    assert client.verify_payment(bundle) is True


def test_add_header_rejects_disconnected_header():
    client = SPVClient()
    orphan = BlockHeader(
        prev_hash="c" * 64,  # does not match tip (genesis)
        merkle_root=merkle_root([make_tx(0).txid]),
        timestamp=5,
        bits=16,
        nonce=0,
    )
    assert client.add_header(orphan) is False
    assert client.height == 0  # chain unchanged


# --------------------------------------------------------------------------- #
# Confirmation threshold enforcement
# --------------------------------------------------------------------------- #
def test_verify_payment_with_confirmations_enforces_minimum():
    genesis = genesis_block()
    client = SPVClient()

    payment_block = make_block(genesis.hash, n_txs=2, timestamp=50)
    client.add_header(payment_block.header)  # 1 confirmation

    bundle = build_proof_bundle(payment_block, payment_block.transactions[0].txid)

    assert client.verify_payment_with_confirmations(bundle, 1) is True
    assert client.verify_payment_with_confirmations(bundle, 2) is False

    # Bury it deeper, then the higher threshold passes.
    prev = payment_block.hash
    for i in range(2):
        blk = make_block(prev, n_txs=1, timestamp=60 + i)
        client.add_header(blk.header)
        prev = blk.hash

    assert client.confirmations(payment_block.hash) == 3
    assert client.verify_payment_with_confirmations(bundle, 3) is True
    assert client.verify_payment_with_confirmations(bundle, 4) is False


def test_verify_payment_with_confirmations_false_for_unknown_block():
    client = SPVClient()
    bundle = MerkleProofBundle(txid="e" * 64, block_hash="f" * 64, proof=[])
    assert client.verify_payment_with_confirmations(bundle, 1) is False


# --------------------------------------------------------------------------- #
# SPV stores ONLY headers
# --------------------------------------------------------------------------- #
def test_spv_client_stores_only_headers():
    genesis = genesis_block()
    client = SPVClient()
    block = make_block(genesis.hash, n_txs=4)
    client.add_header(block.header)

    # Every stored object must be a BlockHeader; no Block / Transaction retained.
    stored = client._headers
    assert all(isinstance(h, BlockHeader) for h in stored)
    assert not any(hasattr(h, "transactions") for h in stored)

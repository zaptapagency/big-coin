"""Tests for Milestones 3-5: PoW, blockchain, node, and the 3-node network."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pow as powmod  # noqa: E402
from block import CENTS_PER_COIN, block_subsidy  # noqa: E402
from network import Network  # noqa: E402
from node import ACCEPTED_REORG, ORPHAN, Node  # noqa: E402
from transaction import Transaction, TxInput, TxOutput  # noqa: E402
from transaction import generate_keypair, pubkey_hash  # noqa: E402


def _wallet():
    sk, pub = generate_keypair()
    return sk, pub, pubkey_hash(pub)


# --------------------------------------------------------------------------- #
# Proof-of-work
# --------------------------------------------------------------------------- #
def test_mined_block_meets_target():
    node = Node("solo")
    _, _, pkh = _wallet()
    block = node.mine_block(pkh)
    assert block is not None
    assert powmod.block_meets_target(block)
    assert int(block.hash, 16) < powmod.bits_to_target(block.header.bits)


def test_subsidy_halving():
    assert block_subsidy(0) == 50 * CENTS_PER_COIN
    assert block_subsidy(210_000) == 25 * CENTS_PER_COIN
    assert block_subsidy(420_000) == 12 * CENTS_PER_COIN + 50_000_000  # 12.5 coins
    assert block_subsidy(210_000 * 64) == 0


def test_difficulty_retarget_directions():
    # Too fast -> harder (more bits); too slow -> easier (fewer bits).
    assert powmod.calculate_next_bits(16, actual_timespan=1, expected_timespan=1000) == 17
    assert powmod.calculate_next_bits(16, actual_timespan=10_000, expected_timespan=1000) == 15
    assert powmod.calculate_next_bits(16, actual_timespan=1000, expected_timespan=1000) == 16


# --------------------------------------------------------------------------- #
# Single-node chain growth and coinbase spending
# --------------------------------------------------------------------------- #
def test_mining_extends_chain():
    node = Node("solo")
    _, _, pkh = _wallet()
    assert node.chain.height == 0
    node.mine_block(pkh)
    node.mine_block(pkh)
    assert node.chain.height == 2


def test_spend_a_coinbase_output():
    node = Node("solo", coinbase_maturity=0)
    a_sk, _, a_pkh = _wallet()
    _, _, b_pkh = _wallet()

    block = node.mine_block(a_pkh)  # coinbase pays Alice
    coinbase = block.transactions[0]
    assert node.chain.utxo.contains(coinbase.txid, 0)

    subsidy = block_subsidy(1)
    spend = Transaction(
        inputs=[TxInput(coinbase.txid, 0)],
        outputs=[TxOutput(subsidy - 1000, b_pkh)],  # leave 1000 as fee
    )
    spend.sign_input(0, a_sk)
    assert node.chain.add_to_mempool(spend) is True

    node.mine_block(a_pkh)  # confirm the spend; miner also collects the fee
    assert node.chain.utxo.contains(spend.txid, 0)
    assert not node.chain.utxo.contains(coinbase.txid, 0)  # coinbase now spent


# --------------------------------------------------------------------------- #
# 3-node network: propagation
# --------------------------------------------------------------------------- #
def test_block_propagates_to_three_nodes():
    net = Network()
    n1, n2, n3 = Node("n1"), Node("n2"), Node("n3")
    for n in (n1, n2, n3):
        net.connect(n)

    _, _, pkh = _wallet()
    n1.mine_block(pkh)
    assert n1.chain.tip == n2.chain.tip == n3.chain.tip
    assert n2.chain.height == 1 and n3.chain.height == 1


def test_transaction_propagates_and_is_mined():
    net = Network()
    n1, n2, n3 = (
        Node("n1", coinbase_maturity=0),
        Node("n2", coinbase_maturity=0),
        Node("n3", coinbase_maturity=0),
    )
    for n in (n1, n2, n3):
        net.connect(n)

    a_sk, _, a_pkh = _wallet()
    _, _, b_pkh = _wallet()

    block = n1.mine_block(a_pkh)  # everyone now has Alice's coinbase
    coinbase = block.transactions[0]
    spend = Transaction(
        inputs=[TxInput(coinbase.txid, 0)],
        outputs=[TxOutput(block_subsidy(1), b_pkh)],
    )
    spend.sign_input(0, a_sk)

    n1.submit_transaction(spend)
    # Gossiped to all mempools.
    assert spend.txid in n2.chain.mempool
    assert spend.txid in n3.chain.mempool

    n2.mine_block(a_pkh)  # n2 mines the payment
    for n in (n1, n2, n3):
        assert n.chain.utxo.contains(spend.txid, 0)
        assert spend.txid not in n.chain.mempool


# --------------------------------------------------------------------------- #
# Forks and reorg
# --------------------------------------------------------------------------- #
def test_reorg_to_heavier_chain():
    _, _, pkh = _wallet()

    # Node A builds a 2-block chain in isolation.
    a = Node("a")
    a.mine_block(pkh)
    a.mine_block(pkh)
    assert a.chain.height == 2

    # Node B builds a 3-block chain in isolation (more cumulative work).
    b = Node("b")
    b_blocks = [b.mine_block(pkh) for _ in range(3)]
    assert b.chain.height == 3

    # Feed B's heavier chain to A: A must reorg onto it.
    results = [a.chain.add_block(blk) for blk in b_blocks]
    assert ACCEPTED_REORG in results
    assert a.chain.tip == b.chain.tip
    assert a.chain.height == 3


def test_gap_triggers_parent_request():
    # B mines two blocks alone; A only receives the second (the first was
    # "dropped"). A should detect the gap and pull the parent from a peer.
    _, _, pkh = _wallet()
    b = Node("b")
    blk1 = b.mine_block(pkh)
    blk2 = b.mine_block(pkh)

    net = Network()
    a = Node("a")
    net.connect(a)
    net.connect(b)

    result = a.receive_block(blk2)  # arrives before its parent blk1
    assert a.chain.height == 2
    assert a.has_block(blk1.hash) and a.has_block(blk2.hash)
    assert result != ORPHAN  # resolved after requesting the parent


def test_dropped_messages_reconciled_by_sync():
    # A very lossy network still converges once we run a reconciliation sync.
    net = Network(drop_rate=0.8, seed=1)
    n1, n2, n3 = Node("n1"), Node("n2"), Node("n3")
    for n in (n1, n2, n3):
        net.connect(n)

    _, _, pkh = _wallet()
    for _ in range(4):
        n1.mine_block(pkh)

    net.sync()
    assert n2.chain.tip == n1.chain.tip
    assert n3.chain.tip == n1.chain.tip

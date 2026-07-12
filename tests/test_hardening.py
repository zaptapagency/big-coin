"""Production-hardening tests: consensus rules added on top of Milestones 1-6.

Covers coinbase maturity, the timestamp rules (max-future-time and
median-time-past), the block-size ceiling, and the max-money invariant. These
are the rules that stop a hostile peer from minting value, gaming difficulty, or
exhausting a node's resources.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import params  # noqa: E402
import pow as powmod  # noqa: E402
from block import block_subsidy, build_block, create_coinbase  # noqa: E402
from node import INVALID, Node  # noqa: E402
from transaction import (  # noqa: E402
    MAX_MONEY,
    Transaction,
    TxInput,
    TxOutput,
    generate_keypair,
    pubkey_hash,
)


def _wallet():
    sk, pub = generate_keypair()
    return sk, pub, pubkey_hash(pub)


# --------------------------------------------------------------------------- #
# Coinbase maturity
# --------------------------------------------------------------------------- #
def test_production_default_maturity_is_100():
    """A regression guard: the shipped default must match the whitepaper-scale
    parameter, not the 0 that many tests use for convenience."""
    assert params.COINBASE_MATURITY == 100
    assert Node("solo").chain.coinbase_maturity == 100


def test_immature_coinbase_cannot_be_spent():
    node = Node("solo", coinbase_maturity=5)
    a_sk, _, a_pkh = _wallet()
    _, _, b_pkh = _wallet()

    block = node.mine_block(a_pkh)  # coinbase pays Alice at height 1
    coinbase = block.transactions[0]

    spend = Transaction(
        inputs=[TxInput(coinbase.txid, 0)],
        outputs=[TxOutput(block_subsidy(1) - 1000, b_pkh)],
    )
    spend.sign_input(0, a_sk)
    # Only 1 block deep (< maturity of 5): the mempool must reject it.
    assert node.chain.add_to_mempool(spend) is False


def test_coinbase_spendable_once_mature():
    node = Node("solo", coinbase_maturity=3)
    a_sk, _, a_pkh = _wallet()
    _, _, b_pkh = _wallet()

    block = node.mine_block(a_pkh)  # height 1
    coinbase = block.transactions[0]
    # Age it: mine to a neutral key until the coinbase is >= 3 deep.
    _, _, m_pkh = _wallet()
    for _ in range(3):
        node.mine_block(m_pkh)

    spend = Transaction(
        inputs=[TxInput(coinbase.txid, 0)],
        outputs=[TxOutput(block_subsidy(1) - 1000, b_pkh)],
    )
    spend.sign_input(0, a_sk)
    assert node.chain.add_to_mempool(spend) is True


# --------------------------------------------------------------------------- #
# Timestamp rules
# --------------------------------------------------------------------------- #
def test_block_too_far_in_future_rejected():
    node = Node("solo")
    _, _, pkh = _wallet()
    coinbase = create_coinbase(1, pkh)
    future = int(time.time()) + params.MAX_FUTURE_TIME + 3600
    block = build_block(
        prev_hash=node.chain.tip,
        transactions=[coinbase],
        bits=node.chain.next_bits(),
        timestamp=future,
    )
    powmod.mine(block)
    assert node.chain.add_block(block) == INVALID
    assert node.chain.height == 0


def test_timestamp_not_after_median_time_past_rejected():
    node = Node("solo")
    _, _, pkh = _wallet()
    coinbase = create_coinbase(1, pkh)
    # Genesis timestamp is the median for the first block; equal is not "after".
    stale = node.chain.median_time_past(node.chain.tip)
    block = build_block(
        prev_hash=node.chain.tip,
        transactions=[coinbase],
        bits=node.chain.next_bits(),
        timestamp=stale,
    )
    powmod.mine(block)
    assert node.chain.add_block(block) == INVALID
    assert node.chain.height == 0


# --------------------------------------------------------------------------- #
# Block-size ceiling
# --------------------------------------------------------------------------- #
def test_oversized_block_rejected():
    node = Node("solo", coinbase_maturity=0)
    _, _, pkh = _wallet()
    # A coinbase whose extra-nonce is padded past the 1 MB serialized limit.
    coinbase = create_coinbase(1, pkh, extra_nonce="x" * (params.MAX_BLOCK_BYTES + 1000))
    block = build_block(
        prev_hash=node.chain.tip,
        transactions=[coinbase],
        bits=node.chain.next_bits(),
        timestamp=node.chain.median_time_past(node.chain.tip) + 1,
    )
    powmod.mine(block)
    assert block.serialized_size() > params.MAX_BLOCK_BYTES
    assert node.chain.add_block(block) == INVALID


# --------------------------------------------------------------------------- #
# Max-money invariant
# --------------------------------------------------------------------------- #
def test_output_exceeding_max_money_is_unverifiable():
    a_sk, a_pub, a_pkh = _wallet()
    _, _, b_pkh = _wallet()
    funding = TxOutput(MAX_MONEY, a_pkh)

    def resolver(txid, index):
        return funding if (txid, index) == ("f" * 64, 0) else None

    tx = Transaction(
        inputs=[TxInput("f" * 64, 0)],
        outputs=[TxOutput(MAX_MONEY + 1, b_pkh)],  # value-overflow forgery
    )
    tx.sign_input(0, a_sk)
    assert tx.verify(resolver) is False


def test_zero_value_output_is_unverifiable():
    a_sk, a_pub, a_pkh = _wallet()
    _, _, b_pkh = _wallet()
    funding = TxOutput(10_000, a_pkh)

    def resolver(txid, index):
        return funding if (txid, index) == ("f" * 64, 0) else None

    tx = Transaction(
        inputs=[TxInput("f" * 64, 0)],
        outputs=[TxOutput(0, b_pkh)],  # dust/zero output not allowed
    )
    tx.sign_input(0, a_sk)
    assert tx.verify(resolver) is False

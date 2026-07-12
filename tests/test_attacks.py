"""Milestone 9 — Attack tests against the local network.

Exercises the consensus rules from the attacker's side: a double-spend attempt,
an invalid block, and a 51%-style reorg that rewrites a confirmed transaction on
a local 3-node network. These demonstrate what the honest rules prevent and what
raw hash-power majority can still do (motivating the confirmation math in
calc.py).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pow as powmod  # noqa: E402
from block import block_subsidy, build_block, create_coinbase  # noqa: E402
from network import Network  # noqa: E402
from node import INVALID, Node  # noqa: E402
from transaction import (  # noqa: E402
    Transaction,
    TxInput,
    TxOutput,
    generate_keypair,
    pubkey_hash,
)


def _wallet():
    sk, pub = generate_keypair()
    return sk, pub, pubkey_hash(pub)


def test_double_spend_within_mempool_rejected():
    node = Node("solo", coinbase_maturity=0)
    a_sk, _, a_pkh = _wallet()
    _, _, b_pkh = _wallet()
    _, _, c_pkh = _wallet()

    block = node.mine_block(a_pkh)
    coinbase = block.transactions[0]
    amount = block_subsidy(1)

    spend1 = Transaction([TxInput(coinbase.txid, 0)], [TxOutput(amount, b_pkh)])
    spend1.sign_input(0, a_sk)
    spend2 = Transaction([TxInput(coinbase.txid, 0)], [TxOutput(amount, c_pkh)])
    spend2.sign_input(0, a_sk)

    assert node.chain.add_to_mempool(spend1) is True
    # The output is still unspent in the UTXO set (mempool doesn't consume it),
    # but once spend1 is mined, spend2 must fail against the UTXO set.
    node.mine_block(a_pkh)
    assert node.chain.utxo.contains(spend1.txid, 0)
    assert node.chain.add_to_mempool(spend2) is False  # UTXO already gone


def test_invalid_block_forged_pow_rejected():
    node = Node("solo")
    _, _, pkh = _wallet()
    # Build a block but never actually mine it (nonce won't meet target).
    coinbase = create_coinbase(1, pkh)
    forged = build_block(
        prev_hash=node.chain.tip, transactions=[coinbase], bits=node.chain.next_bits()
    )
    assert not powmod.block_meets_target(forged)
    assert node.chain.add_block(forged) == INVALID
    assert node.chain.height == 0  # chain unchanged


def test_invalid_block_overclaimed_subsidy_rejected():
    node = Node("solo")
    _, _, pkh = _wallet()
    # Coinbase claims more than the allowed subsidy (no fees available).
    greedy = create_coinbase(1, pkh, fees=block_subsidy(1))  # double the subsidy
    block = build_block(
        prev_hash=node.chain.tip, transactions=[greedy], bits=node.chain.next_bits()
    )
    powmod.mine(block)
    assert node.chain.add_block(block) == INVALID


def test_51_percent_reorg_rewrites_confirmed_payment():
    """A majority attacker mines a longer secret chain that omits a payment the
    honest network had already confirmed, then releases it to force a reorg."""
    net = Network()
    honest1, honest2 = Node("h1", coinbase_maturity=0), Node("h2", coinbase_maturity=0)
    net.connect(honest1)
    net.connect(honest2)

    a_sk, _, a_pkh = _wallet()
    _, _, merchant_pkh = _wallet()

    # Honest chain: Alice gets a coinbase, then pays the merchant; it confirms.
    block1 = honest1.mine_block(a_pkh)
    coinbase = block1.transactions[0]
    pay = Transaction(
        [TxInput(coinbase.txid, 0)], [TxOutput(block_subsidy(1), merchant_pkh)]
    )
    pay.sign_input(0, a_sk)
    honest1.submit_transaction(pay)
    honest1.mine_block(a_pkh)  # payment confirmed on the honest chain
    assert honest1.chain.utxo.contains(pay.txid, 0)
    honest_height = honest1.chain.height

    # Attacker builds a heavier chain in secret from the same block1, but never
    # includes `pay` (Alice keeps her coin). It must be longer to win.
    attacker = Node("attacker", coinbase_maturity=0)
    attacker.chain.add_block(block1)  # shares history up to the payment's parent
    for _ in range(honest_height + 1):  # outrun the honest chain
        attacker.mine_block(a_pkh)
    assert attacker.chain.chainwork[attacker.chain.tip] > honest1.chain.chainwork[
        honest1.chain.tip
    ]

    # Release the secret chain to the honest nodes -> reorg.
    for h in attacker.chain.active_chain():
        honest1.receive_block(attacker.chain.blocks[h])

    assert honest1.chain.tip == attacker.chain.tip
    # The confirmed payment has been erased: the merchant's output is gone and
    # Alice's coin is spendable again on the winning chain.
    assert not honest1.chain.utxo.contains(pay.txid, 0)
    assert honest1.chain.utxo.contains(coinbase.txid, 0)

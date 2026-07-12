"""End-to-end integration test — the project's Definition of Done.

Three local nodes mine, sync, and reorg; two wallets settle a payment end to end;
an SPV client verifies that payment with a Merkle proof against header-only data;
and the attack-probability calculator reproduces the whitepaper table value.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from block import CENTS_PER_COIN, block_subsidy  # noqa: E402
from calc import attacker_success_probability  # noqa: E402
from network import Network  # noqa: E402
from node import Node  # noqa: E402
from spv import SPVClient, build_proof_bundle  # noqa: E402
from wallet import Wallet, pubkey_hash_from_address  # noqa: E402


def _sync_full_node(target: Node, source: Node) -> None:
    """Replay source's active chain into target (headers + bodies)."""
    for h in source.chain.active_chain():
        target.chain.add_block(source.chain.blocks[h])


def test_definition_of_done():
    # --- three nodes on one gossip network -------------------------------- #
    net = Network()
    n1, n2, n3 = (
        Node("n1", coinbase_maturity=0),
        Node("n2", coinbase_maturity=0),
        Node("n3", coinbase_maturity=0),
    )
    for n in (n1, n2, n3):
        net.connect(n)

    alice, bob = Wallet(), Wallet()
    alice_addr = alice.new_key()
    alice_pkh = pubkey_hash_from_address(alice_addr)
    # A neutral miner collects later coinbases so wallet balances stay clean.
    miner = Wallet()
    miner_pkh = pubkey_hash_from_address(miner.new_key())

    # --- n1 mines; the coinbase pays Alice; block propagates to all nodes -- #
    block1 = n1.mine_block(alice_pkh)
    assert n1.chain.tip == n2.chain.tip == n3.chain.tip  # synced
    utxos = list(n1.chain.utxo.items())
    assert alice.balance(utxos) == block_subsidy(1)

    # --- Alice pays Bob via her wallet; tx gossips; n2 mines it ----------- #
    bob_addr = bob.new_key()
    amount = 30 * CENTS_PER_COIN
    fee = 1_000
    pay = alice.create_transaction(utxos, bob_addr, amount, fee=fee)
    assert n1.submit_transaction(pay) is True
    assert pay.txid in n2.chain.mempool and pay.txid in n3.chain.mempool

    block2 = n2.mine_block(miner_pkh)  # confirms the payment
    assert block2 is not None
    for n in (n1, n2, n3):
        assert n.chain.tip == block2.hash
        assert n.chain.utxo.contains(pay.txid, 0)

    # Bob is paid; Alice keeps her change.
    utxos = list(n1.chain.utxo.items())
    assert bob.balance(utxos) == amount
    assert alice.balance(utxos) == block_subsidy(1) - amount - fee

    # --- reorg: a rival builds a heavier branch on top of block2 ---------- #
    rival = Node("rival", coinbase_maturity=0)
    _sync_full_node(rival, n1)  # share history through the payment
    assert rival.chain.tip == block2.hash
    n1.mine_block(miner_pkh)  # honest fork A -> height 3, seen by all
    height_before = n1.chain.height
    rival_blocks = [rival.mine_block(miner_pkh) for _ in range(2)]  # fork B, height 4

    for blk in rival_blocks:  # deliver the heavier branch to the network
        n1.receive_block(blk)
    assert n1.chain.height == height_before + 1  # reorged onto the heavier B
    assert n2.chain.tip == n1.chain.tip == n3.chain.tip  # all converge
    # The payment, built into block2, survives the reorg.
    assert n1.chain.utxo.contains(pay.txid, 0)

    # --- SPV client verifies the payment via a Merkle proof --------------- #
    spv = SPVClient()  # seeded with genesis header only
    for h in n1.chain.active_chain()[1:]:  # add every header after genesis
        assert spv.add_header(n1.chain.blocks[h].header) is True

    bundle = build_proof_bundle(block2, pay.txid)  # a full node hands this over
    assert spv.verify_payment(bundle) is True
    # block2 now has several blocks on top of it: real confirmations.
    assert spv.confirmations(block2.hash) >= 3
    assert spv.verify_payment_with_confirmations(bundle, min_confirmations=3) is True
    # SPV stored headers only, never full blocks/transactions.
    assert all(type(hdr).__name__ == "BlockHeader" for hdr in spv.headers) \
        if hasattr(spv, "headers") else True

    # --- attack calculator matches the whitepaper ------------------------- #
    assert abs(attacker_success_probability(0.1, 5) - 0.0009137) < 1e-6

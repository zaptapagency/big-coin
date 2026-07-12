"""Tests for Milestone 1 — Transactions."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from transaction import (  # noqa: E402
    Transaction,
    TxInput,
    TxOutput,
    generate_keypair,
    pubkey_hash,
)


class FakeChain:
    """A tiny in-memory output resolver standing in for the future UTXO set.

    Register a transaction's outputs, then resolve (txid, index) -> TxOutput.
    """

    def __init__(self):
        self._outputs: dict[tuple[str, int], TxOutput] = {}

    def add_tx(self, tx: Transaction) -> None:
        for i, out in enumerate(tx.outputs):
            self._outputs[(tx.txid, i)] = out

    def spend(self, txid: str, index: int) -> None:
        self._outputs.pop((txid, index), None)

    def resolve(self, txid: str, index: int):
        return self._outputs.get((txid, index))


@pytest.fixture
def alice():
    sk, pub = generate_keypair()
    return {"sk": sk, "pub": pub, "pkh": pubkey_hash(pub)}


@pytest.fixture
def bob():
    sk, pub = generate_keypair()
    return {"sk": sk, "pub": pub, "pkh": pubkey_hash(pub)}


def _funding_tx(owner_pkh: str, amount: int = 100) -> Transaction:
    """A pre-existing output paying `amount` to `owner_pkh` (no inputs here so
    the fixture is self-contained; verify() is not called on this stub)."""
    return Transaction(inputs=[], outputs=[TxOutput(amount, owner_pkh)])


def test_txid_is_deterministic_and_changes_with_content(alice):
    tx = _funding_tx(alice["pkh"])
    assert tx.txid == tx.txid  # deterministic
    tx2 = _funding_tx(alice["pkh"], amount=101)
    assert tx.txid != tx2.txid


def test_signing_bytes_excludes_signatures(alice, bob):
    chain = FakeChain()
    funding = _funding_tx(alice["pkh"], 100)
    chain.add_tx(funding)

    spend = Transaction(
        inputs=[TxInput(funding.txid, 0)],
        outputs=[TxOutput(100, bob["pkh"])],
    )
    before = spend.signing_bytes()
    spend.sign_input(0, alice["sk"])
    after = spend.signing_bytes()
    assert before == after  # signing must not change the signed message


def test_valid_single_input_single_output(alice, bob):
    chain = FakeChain()
    funding = _funding_tx(alice["pkh"], 100)
    chain.add_tx(funding)

    spend = Transaction(
        inputs=[TxInput(funding.txid, 0)],
        outputs=[TxOutput(100, bob["pkh"])],
    )
    spend.sign_input(0, alice["sk"])
    assert spend.verify(chain.resolve) is True
    assert spend.fee(chain.resolve) == 0


def test_change_output_back_to_sender(alice, bob):
    chain = FakeChain()
    funding = _funding_tx(alice["pkh"], 100)
    chain.add_tx(funding)

    spend = Transaction(
        inputs=[TxInput(funding.txid, 0)],
        outputs=[TxOutput(70, bob["pkh"]), TxOutput(25, alice["pkh"])],
    )
    spend.sign_input(0, alice["sk"])
    assert spend.verify(chain.resolve) is True
    assert spend.fee(chain.resolve) == 5  # 100 - (70 + 25)


def test_multiple_inputs(alice, bob):
    chain = FakeChain()
    f1 = _funding_tx(alice["pkh"], 40)
    f2 = _funding_tx(alice["pkh"], 60)
    chain.add_tx(f1)
    chain.add_tx(f2)

    spend = Transaction(
        inputs=[TxInput(f1.txid, 0), TxInput(f2.txid, 0)],
        outputs=[TxOutput(100, bob["pkh"])],
    )
    spend.sign_input(0, alice["sk"])
    spend.sign_input(1, alice["sk"])
    assert spend.verify(chain.resolve) is True


def test_wrong_key_fails(alice, bob):
    chain = FakeChain()
    funding = _funding_tx(alice["pkh"], 100)  # locked to Alice
    chain.add_tx(funding)

    spend = Transaction(
        inputs=[TxInput(funding.txid, 0)],
        outputs=[TxOutput(100, bob["pkh"])],
    )
    spend.sign_input(0, bob["sk"])  # Bob cannot spend Alice's output
    assert spend.verify(chain.resolve) is False


def test_tampered_output_breaks_signature(alice, bob):
    chain = FakeChain()
    funding = _funding_tx(alice["pkh"], 100)
    chain.add_tx(funding)

    spend = Transaction(
        inputs=[TxInput(funding.txid, 0)],
        outputs=[TxOutput(100, bob["pkh"])],
    )
    spend.sign_input(0, alice["sk"])
    spend.outputs[0].amount = 999  # attacker inflates the payment after signing
    assert spend.verify(chain.resolve) is False


def test_overspend_rejected(alice, bob):
    chain = FakeChain()
    funding = _funding_tx(alice["pkh"], 100)
    chain.add_tx(funding)

    spend = Transaction(
        inputs=[TxInput(funding.txid, 0)],
        outputs=[TxOutput(150, bob["pkh"])],  # more than the 100 available
    )
    spend.sign_input(0, alice["sk"])
    assert spend.verify(chain.resolve) is False


def test_unknown_or_spent_output_rejected(alice, bob):
    chain = FakeChain()
    funding = _funding_tx(alice["pkh"], 100)
    chain.add_tx(funding)

    spend = Transaction(
        inputs=[TxInput(funding.txid, 0)],
        outputs=[TxOutput(100, bob["pkh"])],
    )
    spend.sign_input(0, alice["sk"])
    chain.spend(funding.txid, 0)  # output already consumed
    assert spend.verify(chain.resolve) is False


def test_duplicate_input_within_tx_rejected(alice, bob):
    chain = FakeChain()
    funding = _funding_tx(alice["pkh"], 100)
    chain.add_tx(funding)

    spend = Transaction(
        inputs=[TxInput(funding.txid, 0), TxInput(funding.txid, 0)],
        outputs=[TxOutput(200, bob["pkh"])],
    )
    spend.sign_input(0, alice["sk"])
    spend.sign_input(1, alice["sk"])
    assert spend.verify(chain.resolve) is False


def test_coinbase_shape_not_verifiable_here(bob):
    from transaction import COINBASE_PREV_TXID

    coinbase = Transaction(
        inputs=[TxInput(COINBASE_PREV_TXID, 7)],  # null prevout, height in index
        outputs=[TxOutput(50, bob["pkh"])],
    )
    assert coinbase.is_coinbase() is True
    # A coinbase is not spendable-input-verifiable; it's validated in M5/node.
    assert coinbase.verify(lambda t, i: None) is False

    # An input-less tx is neither a coinbase nor verifiable.
    empty = Transaction(inputs=[], outputs=[TxOutput(50, bob["pkh"])])
    assert empty.is_coinbase() is False
    assert empty.verify(lambda t, i: None) is False


def test_serialization_round_trip(alice, bob):
    chain = FakeChain()
    funding = _funding_tx(alice["pkh"], 100)
    chain.add_tx(funding)

    spend = Transaction(
        inputs=[TxInput(funding.txid, 0)],
        outputs=[TxOutput(100, bob["pkh"])],
    )
    spend.sign_input(0, alice["sk"])
    restored = Transaction.from_dict(spend.to_dict())
    assert restored.txid == spend.txid
    assert restored.verify(chain.resolve) is True

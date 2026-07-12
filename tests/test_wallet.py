"""Tests for MyCoin Milestone 8: Wallet & Privacy."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import os

import pytest

from transaction import Transaction, TxInput, TxOutput
from wallet import (
    Wallet,
    address_from_pubkey_hash,
    base58_decode,
    base58_encode,
    is_valid_address,
    pubkey_hash_from_address,
)


# --------------------------------------------------------------------------- #
# In-memory UTXO helpers
# --------------------------------------------------------------------------- #
def make_utxos_paying(pkh_to_amount, prefix="fund"):
    """Create a funding Transaction paying each (pkh, amount) and return its
    UTXOs as a list of (txid, index, TxOutput)."""
    outputs = [TxOutput(amount, pkh) for pkh, amount in pkh_to_amount]
    tx = Transaction(inputs=[], outputs=outputs)
    txid = tx.txid
    return [(txid, i, out) for i, out in enumerate(outputs)]


def make_resolver(utxos):
    """Build a resolver mapping (txid, index) -> TxOutput for Transaction.verify."""
    lookup = {(txid, idx): out for txid, idx, out in utxos}

    def resolver(txid, index):
        return lookup.get((txid, index))

    return resolver


# --------------------------------------------------------------------------- #
# Base58Check
# --------------------------------------------------------------------------- #
def test_base58check_round_trip():
    for _ in range(20):
        pkh = os.urandom(32).hex()
        addr = address_from_pubkey_hash(pkh)
        assert is_valid_address(addr)
        assert pubkey_hash_from_address(addr) == pkh


def test_corrupted_address_fails_checksum():
    pkh = os.urandom(32).hex()
    addr = address_from_pubkey_hash(pkh)

    # Flip one character to a different valid base58 char.
    i = len(addr) // 2
    original = addr[i]
    replacement = "A" if original != "A" else "B"
    corrupted = addr[:i] + replacement + addr[i + 1 :]
    assert corrupted != addr

    assert is_valid_address(corrupted) is False
    with pytest.raises(ValueError):
        pubkey_hash_from_address(corrupted)


def test_leading_zero_round_trip():
    # A pubkey hash whose leading bytes are zero must still round-trip.
    pkh = "00" * 4 + os.urandom(28).hex()
    addr = address_from_pubkey_hash(pkh)
    assert pubkey_hash_from_address(addr) == pkh


def test_base58_leading_zero_bytes():
    data = b"\x00\x00\x01\x02\x03"
    assert base58_decode(base58_encode(data)) == data


# --------------------------------------------------------------------------- #
# Wallet key management
# --------------------------------------------------------------------------- #
def test_new_key_returns_valid_addresses_and_grows():
    w = Wallet()
    assert w.addresses == []
    a1 = w.new_key()
    assert is_valid_address(a1)
    assert w.addresses == [a1]
    a2 = w.new_key()
    assert is_valid_address(a2)
    assert w.addresses == [a1, a2]


def test_new_key_addresses_differ():
    w = Wallet()
    a1 = w.new_key()
    a2 = w.new_key()
    assert a1 != a2


def test_balance_sums_only_owned():
    w = Wallet()
    owned_addr = w.new_key()
    owned_pkh = pubkey_hash_from_address(owned_addr)

    # An address the wallet does NOT own.
    other = Wallet()
    other_pkh = pubkey_hash_from_address(other.new_key())

    utxos = make_utxos_paying(
        [(owned_pkh, 500), (other_pkh, 999), (owned_pkh, 250)]
    )
    assert w.balance(utxos) == 750


# --------------------------------------------------------------------------- #
# create_transaction
# --------------------------------------------------------------------------- #
def test_create_transaction_with_change():
    w = Wallet()
    src_addr = w.new_key()
    src_pkh = pubkey_hash_from_address(src_addr)

    recipient = Wallet()
    to_addr = recipient.new_key()

    utxos = make_utxos_paying([(src_pkh, 1000)])
    before = set(w.addresses)

    tx = w.create_transaction(utxos, to_addr, amount=600, fee=50)
    resolver = make_resolver(utxos)

    assert tx.verify(resolver) is True
    assert tx.fee(resolver) == 50

    # Recipient output.
    to_pkh = pubkey_hash_from_address(to_addr)
    assert tx.outputs[0].amount == 600
    assert tx.outputs[0].pubkey_hash == to_pkh

    # Change output: 1000 - 600 - 50 = 350 back to a newly generated address.
    assert len(tx.outputs) == 2
    assert tx.outputs[1].amount == 350
    change_pkh = tx.outputs[1].pubkey_hash
    assert w.owns(change_pkh)

    new_addrs = set(w.addresses) - before
    assert len(new_addrs) == 1
    change_addr = new_addrs.pop()
    assert pubkey_hash_from_address(change_addr) == change_pkh

    # History recorded.
    assert w.history[-1]["amount"] == 600
    assert w.history[-1]["to"] == to_addr
    assert w.history[-1]["txid"] == tx.txid


def test_create_transaction_exact_amount_no_change():
    w = Wallet()
    src_addr = w.new_key()
    src_pkh = pubkey_hash_from_address(src_addr)

    to_addr = Wallet().new_key()

    utxos = make_utxos_paying([(src_pkh, 700)])
    before = set(w.addresses)

    tx = w.create_transaction(utxos, to_addr, amount=650, fee=50)
    resolver = make_resolver(utxos)

    assert tx.verify(resolver) is True
    assert tx.fee(resolver) == 50
    assert len(tx.outputs) == 1  # no change output
    assert tx.outputs[0].amount == 650
    # No new change key was generated (exact spend).
    assert set(w.addresses) == before


def test_create_transaction_insufficient_funds():
    w = Wallet()
    src_pkh = pubkey_hash_from_address(w.new_key())
    to_addr = Wallet().new_key()

    utxos = make_utxos_paying([(src_pkh, 100)])
    with pytest.raises(ValueError):
        w.create_transaction(utxos, to_addr, amount=200, fee=10)


def test_create_transaction_multiple_inputs():
    w = Wallet()
    pkh1 = pubkey_hash_from_address(w.new_key())
    pkh2 = pubkey_hash_from_address(w.new_key())
    to_addr = Wallet().new_key()

    utxos = make_utxos_paying([(pkh1, 400), (pkh2, 400)])
    tx = w.create_transaction(utxos, to_addr, amount=700, fee=10)
    resolver = make_resolver(utxos)

    assert len(tx.inputs) == 2
    assert tx.verify(resolver) is True
    assert tx.fee(resolver) == 10

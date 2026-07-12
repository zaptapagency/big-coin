"""MyCoin — Milestone 1: Transactions (Bitcoin whitepaper sections 2 and 9).

A coin is modeled as a chain of digital signatures. Each transaction spends the
outputs of earlier transactions by signing over a commitment to what is being
spent and to the next owners, then creates new outputs locked to recipient
public-key hashes.

Trade-offs vs. real Bitcoin (the "~10% difference"):
  * Serialization is canonical JSON (sorted keys), not a compact binary format.
    Human-readable and easy to debug, but larger and slower on the wire.
  * There is no Script language. An output is locked to a single pubkey hash and
    can be spent by exactly one signature (pay-to-pubkey-hash only).
  * `pubkey_hash` here is a single SHA-256 of the public key. Bitcoin uses
    RIPEMD-160(SHA-256(pubkey)); we avoid RIPEMD-160 because it is missing from
    some OpenSSL 3 builds. This is fine for an educational network with no value.
  * The signing message is SIGHASH_ALL only (every input commits to all inputs
    and all outputs). Bitcoin supports several sighash modes.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Callable, Optional

from ecdsa import SECP256k1, BadSignatureError, SigningKey, VerifyingKey

from params import MAX_MONEY


# --------------------------------------------------------------------------- #
# Crypto helpers
# --------------------------------------------------------------------------- #
def sha256d(data: bytes) -> bytes:
    """Double SHA-256, as used throughout Bitcoin for hashing/identifiers."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def pubkey_hash(pubkey_hex: str) -> str:
    """Address material: hash of a public key. See module trade-off note."""
    return hashlib.sha256(bytes.fromhex(pubkey_hex)).hexdigest()


def generate_keypair() -> tuple[SigningKey, str]:
    """Convenience for tests/wallet prototyping: (signing_key, pubkey_hex)."""
    sk = SigningKey.generate(curve=SECP256k1)
    pubkey_hex = sk.get_verifying_key().to_string().hex()
    return sk, pubkey_hex


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #
@dataclass
class TxOutput:
    """A spendable output: an `amount` locked to a recipient `pubkey_hash`."""

    amount: int
    pubkey_hash: str

    def to_dict(self) -> dict:
        return {"amount": self.amount, "pubkey_hash": self.pubkey_hash}

    @staticmethod
    def from_dict(d: dict) -> "TxOutput":
        return TxOutput(amount=d["amount"], pubkey_hash=d["pubkey_hash"])


@dataclass
class TxInput:
    """A reference to a previous output, plus the authorization to spend it.

    `pubkey` and `signature` are empty in the "signing form" of a transaction
    and are filled in by `Transaction.sign_input`.
    """

    prev_txid: str
    output_index: int
    pubkey: str = ""
    signature: str = ""

    def outpoint(self) -> tuple[str, int]:
        """The (txid, index) pair uniquely identifying the output being spent."""
        return (self.prev_txid, self.output_index)

    def to_dict(self, *, include_sig: bool = True) -> dict:
        d = {"prev_txid": self.prev_txid, "output_index": self.output_index}
        if include_sig:
            d["pubkey"] = self.pubkey
            d["signature"] = self.signature
        return d

    @staticmethod
    def from_dict(d: dict) -> "TxInput":
        return TxInput(
            prev_txid=d["prev_txid"],
            output_index=d["output_index"],
            pubkey=d.get("pubkey", ""),
            signature=d.get("signature", ""),
        )


# A resolver maps an outpoint to the TxOutput it refers to (or None if unknown /
# already spent). In later milestones this is backed by the UTXO set.
OutputResolver = Callable[[str, int], Optional[TxOutput]]

# A coinbase transaction (Milestone 5) has a single input with this "null"
# previous txid. The input's `output_index` carries the block height and its
# `pubkey` field carries an arbitrary extra-nonce, which together keep every
# coinbase txid unique. Mirrors Bitcoin's null-prevout coinbase input.
COINBASE_PREV_TXID = "0" * 64


@dataclass
class Transaction:
    inputs: list[TxInput] = field(default_factory=list)
    outputs: list[TxOutput] = field(default_factory=list)

    # ----- serialization -------------------------------------------------- #
    def to_dict(self, *, include_sigs: bool = True) -> dict:
        return {
            "inputs": [i.to_dict(include_sig=include_sigs) for i in self.inputs],
            "outputs": [o.to_dict() for o in self.outputs],
        }

    @staticmethod
    def from_dict(d: dict) -> "Transaction":
        return Transaction(
            inputs=[TxInput.from_dict(i) for i in d["inputs"]],
            outputs=[TxOutput.from_dict(o) for o in d["outputs"]],
        )

    def _serialize(self, *, include_sigs: bool) -> bytes:
        return json.dumps(
            self.to_dict(include_sigs=include_sigs),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()

    # ----- identity & signing --------------------------------------------- #
    def signing_bytes(self) -> bytes:
        """The message every input signs (SIGHASH_ALL): the tx with all input
        signatures/pubkeys stripped. Commits to which outputs are spent and to
        all next owners, so signatures cannot be replayed on a different tx."""
        return self._serialize(include_sigs=False)

    @property
    def txid(self) -> str:
        """Hex identifier: double-SHA-256 of the fully-signed serialization."""
        return sha256d(self._serialize(include_sigs=True)).hex()

    def sign_input(self, index: int, signing_key: SigningKey) -> None:
        """Sign input `index`, recording the signer's pubkey and signature."""
        vk: VerifyingKey = signing_key.get_verifying_key()
        self.inputs[index].pubkey = vk.to_string().hex()
        self.inputs[index].signature = signing_key.sign(self.signing_bytes()).hex()

    def is_coinbase(self) -> bool:
        """A coinbase (Milestone 5) mints coins via a single null-prevout input."""
        return len(self.inputs) == 1 and self.inputs[0].prev_txid == COINBASE_PREV_TXID

    # ----- verification --------------------------------------------------- #
    def verify(self, resolver: OutputResolver) -> bool:
        """Validate this (non-coinbase) transaction against referenced outputs.

        Checks: at least one input and output; no duplicate outpoints; each
        referenced output exists; the spender's pubkey hashes to that output's
        pubkey_hash; the signature is valid; and total in >= total out.
        """
        if self.is_coinbase():
            return False
        if not self.inputs or not self.outputs:
            return False
        # Every output must carry a positive value within the money supply, and
        # the total must not exceed it (guards against value-overflow forgery).
        if any(o.amount <= 0 or o.amount > MAX_MONEY for o in self.outputs):
            return False
        if sum(o.amount for o in self.outputs) > MAX_MONEY:
            return False

        seen: set[tuple[str, int]] = set()
        total_in = 0
        message = self.signing_bytes()

        for txin in self.inputs:
            outpoint = txin.outpoint()
            if outpoint in seen:  # double-spend within a single tx
                return False
            seen.add(outpoint)

            prev = resolver(txin.prev_txid, txin.output_index)
            if prev is None:  # unknown or already-spent output
                return False

            if pubkey_hash(txin.pubkey) != prev.pubkey_hash:
                return False  # not authorized to spend this output

            try:
                vk = VerifyingKey.from_string(
                    bytes.fromhex(txin.pubkey), curve=SECP256k1
                )
                vk.verify(bytes.fromhex(txin.signature), message)
            except (BadSignatureError, ValueError):
                return False

            total_in += prev.amount

        total_out = sum(o.amount for o in self.outputs)
        return total_in >= total_out

    def fee(self, resolver: OutputResolver) -> int:
        """inputs - outputs. Assumes the tx has already passed `verify`."""
        total_in = sum(
            resolver(i.prev_txid, i.output_index).amount for i in self.inputs
        )
        return total_in - sum(o.amount for o in self.outputs)

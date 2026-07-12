"""MyCoin — Milestone 2 & 5: Blocks, timestamp chain, and incentives.

A block chains to its predecessor by hash and commits to its transactions via a
Merkle root, forming the timestamp server of whitepaper section 3. The first
transaction is a coinbase that mints the block subsidy plus fees for the miner
(section 6, incentives).

Consensus parameters (my own numbers; see README):
  * Target block time: 10 minutes.
  * Retarget interval: 2016 blocks (handled in pow.py).
  * Max supply: 42,000,000 coins, expressed in the smallest unit "cent" where
    1 coin = 100_000_000 cents (like Bitcoin's satoshi).
  * Initial subsidy: 50 coins, halving every 210,000 blocks.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field

from merkle import merkle_root
from params import (
    CENTS_PER_COIN,
    GENESIS_BITS,
    GENESIS_MINER_PKH,
    GENESIS_TIMESTAMP,
    HALVING_INTERVAL,
    INITIAL_SUBSIDY,
    MAX_SUPPLY,
)
from transaction import COINBASE_PREV_TXID, Transaction, TxInput, TxOutput


def block_subsidy(height: int) -> int:
    """Coins minted by the coinbase at `height`, in cents, before fees.

    Halves every HALVING_INTERVAL blocks; returns 0 once fully decayed.
    """
    halvings = height // HALVING_INTERVAL
    if halvings >= 64:  # right-shifting past the width would zero it anyway
        return 0
    return INITIAL_SUBSIDY >> halvings


def create_coinbase(
    height: int, miner_pubkey_hash: str, fees: int = 0, extra_nonce: str = ""
) -> Transaction:
    """Build the block's first transaction, paying subsidy+fees to the miner.

    The single input has a null previous txid (marking it as a coinbase); its
    `output_index` carries the block height and its `pubkey` field carries an
    arbitrary `extra_nonce`. Together these keep every coinbase txid unique, so
    two coinbases at different heights (or with the same miner key) never
    collide in the UTXO set.
    """
    marker = TxInput(
        prev_txid=COINBASE_PREV_TXID,
        output_index=height,
        pubkey=extra_nonce,
    )
    return Transaction(
        inputs=[marker],
        outputs=[TxOutput(block_subsidy(height) + fees, miner_pubkey_hash)],
    )


def coinbase_height(tx: Transaction) -> int:
    """Extract the height a coinbase commits to (its input's output_index)."""
    return tx.inputs[0].output_index


@dataclass
class BlockHeader:
    prev_hash: str
    merkle_root: str
    timestamp: int
    bits: int  # difficulty as required number of leading zero bits (see pow.py)
    nonce: int = 0

    def serialize(self) -> bytes:
        return json.dumps(
            {
                "prev_hash": self.prev_hash,
                "merkle_root": self.merkle_root,
                "timestamp": self.timestamp,
                "bits": self.bits,
                "nonce": self.nonce,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()

    def hash(self) -> str:
        """Block hash = double-SHA-256 of the serialized header (hex)."""
        return hashlib.sha256(hashlib.sha256(self.serialize()).digest()).digest().hex()

    def to_dict(self) -> dict:
        return {
            "prev_hash": self.prev_hash,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp,
            "bits": self.bits,
            "nonce": self.nonce,
        }

    @staticmethod
    def from_dict(d: dict) -> "BlockHeader":
        return BlockHeader(
            prev_hash=d["prev_hash"],
            merkle_root=d["merkle_root"],
            timestamp=d["timestamp"],
            bits=d["bits"],
            nonce=d["nonce"],
        )


@dataclass
class Block:
    header: BlockHeader
    transactions: list[Transaction] = field(default_factory=list)

    @property
    def hash(self) -> str:
        return self.header.hash()

    def compute_merkle_root(self) -> str:
        return merkle_root([tx.txid for tx in self.transactions])

    def has_valid_merkle_root(self) -> bool:
        return self.header.merkle_root == self.compute_merkle_root()

    def to_dict(self) -> dict:
        return {
            "header": self.header.to_dict(),
            "transactions": [tx.to_dict() for tx in self.transactions],
        }

    def serialized_size(self) -> int:
        """Size in bytes of the canonical serialization (for the block limit)."""
        return len(
            json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode()
        )

    @staticmethod
    def from_dict(d: dict) -> "Block":
        return Block(
            header=BlockHeader.from_dict(d["header"]),
            transactions=[Transaction.from_dict(t) for t in d["transactions"]],
        )


def build_block(
    prev_hash: str,
    transactions: list[Transaction],
    bits: int,
    timestamp: int | None = None,
) -> Block:
    """Assemble a block (unmined: nonce still needs solving in pow.py)."""
    txids = [tx.txid for tx in transactions]
    header = BlockHeader(
        prev_hash=prev_hash,
        merkle_root=merkle_root(txids),
        timestamp=timestamp if timestamp is not None else int(time.time()),
        bits=bits,
        nonce=0,
    )
    return Block(header=header, transactions=transactions)


# --- Genesis --------------------------------------------------------------- #
# GENESIS_BITS / GENESIS_TIMESTAMP / GENESIS_MINER_PKH come from params.py.


def genesis_block() -> Block:
    """Deterministic, hardcoded first block shared by every node."""
    coinbase = create_coinbase(0, GENESIS_MINER_PKH, fees=0)
    header = BlockHeader(
        prev_hash="0" * 64,
        merkle_root=merkle_root([coinbase.txid]),
        timestamp=GENESIS_TIMESTAMP,
        bits=GENESIS_BITS,
        nonce=0,
    )
    # The genesis block is accepted by rule, so its nonce need not meet target.
    return Block(header=header, transactions=[coinbase])

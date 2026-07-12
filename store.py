"""MyCoin — persistence layer: a SQLite-backed block store.

Blocks are the durable state of the chain; everything else (the UTXO set,
heights, chainwork) is derivable by replaying them from genesis. This module
persists the raw blocks to a SQLite database and reconstructs a `Blockchain`
from them on load.

Design note: reloading replays each stored block through `Blockchain.add_block`,
which re-runs full consensus validation (proof-of-work, Merkle root, timestamps,
transaction/UTXO checks). A persisted chain that is invalid under the current
rules is therefore rejected on load — that is intended: the database is a cache
of blocks, not a bypass of consensus.
"""

from __future__ import annotations

import json
import sqlite3

import node
from block import Block, genesis_block


class BlockStore:
    """A durable, SQLite-backed store of blocks keyed by hash."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        # `check_same_thread=False` keeps the store usable if a caller hands it
        # to another thread; access here is otherwise single-threaded.
        self._conn = sqlite3.connect(db_path)
        # WAL mode improves durability/concurrency for the write-then-read
        # patterns this store sees (persist a chain, then reload it).
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blocks (
                hash      TEXT PRIMARY KEY,
                prev_hash TEXT,
                height    INTEGER,
                body      TEXT
            )
            """
        )
        self._conn.commit()

    # ----- context manager ------------------------------------------------- #
    def __enter__(self) -> "BlockStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ----- writes ---------------------------------------------------------- #
    def save_block(self, block: Block, height: int) -> None:
        """Upsert a block. INSERT OR REPLACE makes re-saving idempotent."""
        body = json.dumps(block.to_dict())
        self._conn.execute(
            "INSERT OR REPLACE INTO blocks (hash, prev_hash, height, body) "
            "VALUES (?, ?, ?, ?)",
            (block.hash, block.header.prev_hash, height, body),
        )
        self._conn.commit()

    # ----- reads ----------------------------------------------------------- #
    def has_block(self, block_hash: str) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM blocks WHERE hash = ? LIMIT 1", (block_hash,)
        )
        return cur.fetchone() is not None

    def get_block(self, block_hash: str) -> Block | None:
        cur = self._conn.execute(
            "SELECT body FROM blocks WHERE hash = ?", (block_hash,)
        )
        row = cur.fetchone()
        if row is None:
            return None
        return Block.from_dict(json.loads(row[0]))

    def load_blocks_in_height_order(self) -> list[Block]:
        """All stored blocks ordered by height ascending, so a parent always
        precedes its children (required for a clean replay)."""
        cur = self._conn.execute(
            "SELECT body FROM blocks ORDER BY height ASC, hash ASC"
        )
        return [Block.from_dict(json.loads(row[0])) for row in cur.fetchall()]

    def count(self) -> int:
        cur = self._conn.execute("SELECT COUNT(*) FROM blocks")
        return int(cur.fetchone()[0])

    def close(self) -> None:
        self._conn.close()


def save_chain(chain, store: BlockStore) -> int:
    """Persist every block known to `chain` (including side branches).

    Iterates `chain.blocks` alongside `chain.heights`. Returns the count saved.
    """
    saved = 0
    for block_hash, block in chain.blocks.items():
        store.save_block(block, chain.heights[block_hash])
        saved += 1
    return saved


def load_chain(store: BlockStore, coinbase_maturity: int = 100):
    """Rebuild a `Blockchain` by replaying stored blocks through `add_block`.

    A fresh chain already contains genesis, so the stored genesis hash is
    skipped. Every other block is re-validated as it is connected.
    """
    chain = node.Blockchain(coinbase_maturity=coinbase_maturity)
    genesis_hash = genesis_block().hash
    for block in store.load_blocks_in_height_order():
        if block.hash == genesis_hash:
            continue
        chain.add_block(block)
    return chain

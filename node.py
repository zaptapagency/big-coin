"""MyCoin — Milestone 4 & 5: Blockchain consensus and the node.

`Blockchain` stores every block it has seen (including side branches), tracks
cumulative proof-of-work, and keeps the active chain on the most-work tip
(whitepaper section 5, step 5-6, and the longest/most-work chain rule of
section 4). It validates blocks against the UTXO set, handles forks, and reorgs
onto a heavier competing branch.

`Node` wires a blockchain to a network and performs the six steps of section 5:
  1. new transactions are broadcast to all nodes,
  2. each node collects them into a candidate block (the mempool),
  3. each node works on proof-of-work for its block,
  4. when solved, the block is broadcast,
  5. nodes accept the block only if all its transactions are valid & unspent,
  6. nodes express acceptance by building the next block on its hash.

Trade-off vs Bitcoin: to keep the code readable, block validation for a fork
replays the UTXO set from genesis along the branch rather than keeping per-block
undo data. Correct, but O(chain length) per validated block.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from block import (
    Block,
    build_block,
    coinbase_height,
    create_coinbase,
    genesis_block,
)
from pow import (
    RETARGET_INTERVAL,
    TARGET_BLOCK_TIME,
    block_meets_target,
    calculate_next_bits,
    mine,
)
from params import (
    COINBASE_MATURITY,
    MAX_BLOCK_BYTES,
    MAX_FUTURE_TIME,
    MEDIAN_TIME_SPAN,
)
from transaction import Transaction
from utxo import UTXOSet, validate_coinbase

# add_block result codes
ACCEPTED_EXTEND = "extended"  # extended the active tip
ACCEPTED_SIDE = "sidebranch"  # valid, stored, but not the active chain
ACCEPTED_REORG = "reorg"  # became active by outweighing the old tip
DUPLICATE = "duplicate"
ORPHAN = "orphan"  # parent unknown; caller should request it
INVALID = "invalid"


def _work(bits: int) -> int:
    """Approximate work of a block: proportional to the target difficulty."""
    return 1 << bits


class Blockchain:
    def __init__(self, coinbase_maturity: int = COINBASE_MATURITY) -> None:
        # coinbase_maturity is configurable so tests can use a small value; the
        # production default is params.COINBASE_MATURITY (100 blocks).
        self.coinbase_maturity = coinbase_maturity
        genesis = genesis_block()
        gh = genesis.hash
        self.blocks: dict[str, Block] = {gh: genesis}
        self.heights: dict[str, int] = {gh: 0}
        self.chainwork: dict[str, int] = {gh: _work(genesis.header.bits)}
        self.genesis_hash = gh
        self.tip = gh
        self.utxo = UTXOSet()
        self.utxo.apply_block(genesis, 0)
        self.mempool: dict[str, Transaction] = {}
        self.orphans: dict[str, Block] = {}  # hash -> block with unknown parent

    # ----- queries -------------------------------------------------------- #
    @property
    def height(self) -> int:
        return self.heights[self.tip]

    def tip_block(self) -> Block:
        return self.blocks[self.tip]

    def active_chain(self) -> list[str]:
        """Hashes from genesis to the active tip, inclusive."""
        return self._ancestry(self.tip)

    def _ancestry(self, block_hash: str) -> list[str]:
        chain: list[str] = []
        h = block_hash
        while True:
            chain.append(h)
            if h == self.genesis_hash:
                break
            h = self.blocks[h].header.prev_hash
        chain.reverse()
        return chain

    # ----- difficulty ----------------------------------------------------- #
    def _expected_bits(self, prev_hash: str, height: int) -> int:
        prev = self.blocks[prev_hash]
        if height % RETARGET_INTERVAL != 0:
            return prev.header.bits
        # Retarget: compare the last interval's actual timespan to the ideal.
        first_hash = self._ancestry(prev_hash)[-RETARGET_INTERVAL]
        first = self.blocks[first_hash]
        actual = prev.header.timestamp - first.header.timestamp
        return calculate_next_bits(prev.header.bits, actual)

    def next_bits(self) -> int:
        return self._expected_bits(self.tip, self.height + 1)

    def median_time_past(self, block_hash: str) -> int:
        """Median timestamp of the last MEDIAN_TIME_SPAN blocks up to and
        including `block_hash`. A new block's timestamp must exceed this, which
        stops miners from rolling timestamps backward to game difficulty."""
        stamps: list[int] = []
        h = block_hash
        for _ in range(MEDIAN_TIME_SPAN):
            b = self.blocks[h]
            stamps.append(b.header.timestamp)
            if h == self.genesis_hash:
                break
            h = b.header.prev_hash
        stamps.sort()
        return stamps[len(stamps) // 2]

    # ----- UTXO replay for a branch --------------------------------------- #
    def _utxo_for_branch(self, tip_hash: str) -> UTXOSet:
        """Build the UTXO set as of `tip_hash` by replaying its ancestry."""
        u = UTXOSet()
        for height, h in enumerate(self._ancestry(tip_hash)):
            u.apply_block(self.blocks[h], height)
        return u

    # ----- block validation ----------------------------------------------- #
    def _validate_block(self, block: Block, prev_hash: str, height: int) -> bool:
        if not block.transactions:
            return False
        # Resource limit: reject oversized blocks (DoS / bandwidth protection).
        if block.serialized_size() > MAX_BLOCK_BYTES:
            return False
        # Proof-of-work and the committed transaction set.
        if not block_meets_target(block):
            return False
        if not block.has_valid_merkle_root():
            return False
        if block.header.bits != self._expected_bits(prev_hash, height):
            return False
        # Timestamp rules: not too far in the future, and strictly greater than
        # the median time of the preceding window.
        if block.header.timestamp > int(time.time()) + MAX_FUTURE_TIME:
            return False
        if block.header.timestamp <= self.median_time_past(prev_hash):
            return False

        # Validate transactions against the UTXO state as of the parent,
        # applying each in order so a tx may spend an earlier tx in the block.
        working = self._utxo_for_branch(prev_hash)
        fees = 0
        for i, tx in enumerate(block.transactions):
            if tx.is_coinbase():
                if i != 0:
                    return False  # only the first tx may be a coinbase
                continue
            if not working.validate_transaction(
                tx, spend_height=height, maturity=self.coinbase_maturity
            ):
                return False
            fees += tx.fee(working.resolve)
            working.apply_transaction(tx, height)

        from block import block_subsidy

        return validate_coinbase(block, height, block_subsidy(height), fees)

    # ----- add a block ---------------------------------------------------- #
    def add_block(self, block: Block) -> str:
        h = block.hash
        if h in self.blocks:
            return DUPLICATE
        prev_hash = block.header.prev_hash
        if prev_hash not in self.blocks:
            self.orphans[h] = block
            return ORPHAN

        height = self.heights[prev_hash] + 1
        if not self._validate_block(block, prev_hash, height):
            return INVALID

        # Store the block.
        self.blocks[h] = block
        self.heights[h] = height
        self.chainwork[h] = self.chainwork[prev_hash] + _work(block.header.bits)

        result: str
        if prev_hash == self.tip:
            # Fast path: extends the active chain.
            self.utxo.apply_block(block, height)
            self.tip = h
            self._remove_block_txs_from_mempool(block)
            result = ACCEPTED_EXTEND
        elif self.chainwork[h] > self.chainwork[self.tip]:
            # A competing branch now has more work: reorganize.
            self._reorg_to(h)
            result = ACCEPTED_REORG
        else:
            result = ACCEPTED_SIDE

        self._try_connect_orphans(h)
        return result

    def _reorg_to(self, new_tip: str) -> None:
        """Switch the active chain to `new_tip`, rebuilding UTXO and mempool."""
        old_txs = {
            tx.txid: tx
            for h in self.active_chain()
            for tx in self.blocks[h].transactions
            if not tx.is_coinbase()
        }
        self.utxo = self._utxo_for_branch(new_tip)
        new_txs = {
            tx.txid
            for h in self._ancestry(new_tip)
            for tx in self.blocks[h].transactions
        }
        self.tip = new_tip
        next_height = self.heights[new_tip] + 1
        # Transactions that were confirmed only on the abandoned branch return
        # to the mempool if they are still valid against the new UTXO set.
        for txid, tx in old_txs.items():
            if txid not in new_txs and self.utxo.validate_transaction(
                tx, spend_height=next_height, maturity=self.coinbase_maturity
            ):
                self.mempool[txid] = tx
        # Drop mempool txs that the new chain already confirmed or invalidated.
        for txid in list(self.mempool):
            if txid in new_txs or not self.utxo.validate_transaction(
                self.mempool[txid],
                spend_height=next_height,
                maturity=self.coinbase_maturity,
            ):
                self.mempool.pop(txid, None)

    def _remove_block_txs_from_mempool(self, block: Block) -> None:
        for tx in block.transactions:
            self.mempool.pop(tx.txid, None)

    def _try_connect_orphans(self, new_parent: str) -> None:
        """Once a parent arrives, retry any orphan blocks that referenced it."""
        connected = [
            oh
            for oh, ob in self.orphans.items()
            if ob.header.prev_hash == new_parent
        ]
        for oh in connected:
            ob = self.orphans.pop(oh)
            self.add_block(ob)

    # ----- mempool -------------------------------------------------------- #
    def add_to_mempool(self, tx: Transaction) -> bool:
        if tx.txid in self.mempool:
            return False
        # Validate as if it were mined into the next block (for maturity).
        if not self.utxo.validate_transaction(
            tx, spend_height=self.height + 1, maturity=self.coinbase_maturity
        ):
            return False
        self.mempool[tx.txid] = tx
        return True

    def gather_block_transactions(self, max_txs: int = 1000) -> tuple[list[Transaction], int]:
        """Pick a set of mutually-consistent mempool txs and their total fee."""
        working = self.utxo.copy()
        next_height = self.height + 1
        chosen: list[Transaction] = []
        fees = 0
        for tx in list(self.mempool.values())[:max_txs]:
            if working.validate_transaction(
                tx, spend_height=next_height, maturity=self.coinbase_maturity
            ):
                fees += tx.fee(working.resolve)
                working.apply_transaction(tx, next_height)
                chosen.append(tx)
        return chosen, fees


class Node:
    def __init__(
        self,
        node_id: str,
        network: Optional["object"] = None,
        coinbase_maturity: int = COINBASE_MATURITY,
    ) -> None:
        self.node_id = node_id
        self.chain = Blockchain(coinbase_maturity=coinbase_maturity)
        self.network = network  # set by Network.connect

    # ----- step 1 & 2: receive/broadcast transactions --------------------- #
    def submit_transaction(self, tx: Transaction) -> bool:
        """Local origination of a tx (e.g. from a wallet): add + broadcast."""
        if self.chain.add_to_mempool(tx):
            if self.network:
                self.network.broadcast_tx(self.node_id, tx)
            return True
        return False

    def receive_transaction(self, tx: Transaction) -> None:
        # Add to mempool and relay onward (flood fill) only if newly accepted.
        if self.chain.add_to_mempool(tx):
            if self.network:
                self.network.broadcast_tx(self.node_id, tx)

    # ----- step 3 & 4: mine and broadcast a block ------------------------- #
    def mine_block(self, miner_pubkey_hash: str, extra_nonce: str = "") -> Optional[Block]:
        height = self.chain.height + 1
        bits = self.chain.next_bits()
        txs, fees = self.chain.gather_block_transactions()
        coinbase = create_coinbase(
            height, miner_pubkey_hash, fees=fees, extra_nonce=extra_nonce or self.node_id
        )
        # Timestamp must exceed the median-time-past; clamp up so blocks mined in
        # the same wall-clock second still satisfy the strictly-increasing rule.
        timestamp = max(int(time.time()), self.chain.median_time_past(self.chain.tip) + 1)
        block = build_block(
            prev_hash=self.chain.tip,
            transactions=[coinbase, *txs],
            bits=bits,
            timestamp=timestamp,
        )
        if not mine(block):
            return None
        if self.chain.add_block(block) in (ACCEPTED_EXTEND, ACCEPTED_REORG):
            if self.network:
                self.network.broadcast_block(self.node_id, block)
            return block
        return None

    # ----- step 5 & 6: receive/validate blocks ---------------------------- #
    def receive_block(self, block: Block) -> str:
        result = self.chain.add_block(block)
        if result == ORPHAN and self.network:
            # Gap detected: request the missing parent (tolerates dropped msgs).
            parent = self.network.request_block(self.node_id, block.header.prev_hash)
            if parent is not None:
                self.chain.add_block(parent)
                result = self.chain.add_block(block)
        if result in (ACCEPTED_EXTEND, ACCEPTED_REORG) and self.network:
            self.network.broadcast_block(self.node_id, block)
        return result

    def has_block(self, block_hash: str) -> bool:
        return block_hash in self.chain.blocks

    def get_block(self, block_hash: str) -> Optional[Block]:
        return self.chain.blocks.get(block_hash)

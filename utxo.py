"""MyCoin — Milestone 6: UTXO set & disk space (Bitcoin whitepaper section 7).

The UTXO (unspent transaction output) set is an index of every output that can
still be spent, keyed by outpoint (txid, index). It gives O(1) double-spend
checks: an input is only valid if its referenced outpoint is still present.

Section 7 also describes reclaiming disk space: once a transaction's outputs are
all spent, its body can be discarded because the block's Merkle root still
commits to it via interior hashes. `pruned_leaf_count` / `merkle_pruning_demo`
illustrate that a proof needs only ~log2(n) hashes, not the whole block.

Trade-off vs Bitcoin: real nodes persist the UTXO set to LevelDB and store undo
data for reorgs. Here it lives in memory and reorgs rebuild it from the active
chain (see node.py), which is simpler but O(chain length) per reorg.
"""

from __future__ import annotations

import math
from typing import Iterator, Optional

from block import Block, coinbase_height
from transaction import Transaction, TxOutput


class UTXOSet:
    def __init__(self) -> None:
        # (txid, index) -> TxOutput
        self._utxos: dict[tuple[str, int], TxOutput] = {}
        # (txid, index) -> (is_coinbase, creation_height); used for maturity.
        self._meta: dict[tuple[str, int], tuple[bool, int]] = {}

    # ----- basic index operations ----------------------------------------- #
    def get(self, txid: str, index: int) -> Optional[TxOutput]:
        """Resolver form used by Transaction.verify."""
        return self._utxos.get((txid, index))

    resolve = get  # alias matching the OutputResolver signature

    def contains(self, txid: str, index: int) -> bool:
        return (txid, index) in self._utxos

    def meta(self, txid: str, index: int) -> Optional[tuple[bool, int]]:
        """Return (is_coinbase, creation_height) for an unspent output."""
        return self._meta.get((txid, index))

    def add(
        self,
        txid: str,
        index: int,
        output: TxOutput,
        *,
        is_coinbase: bool = False,
        height: int = 0,
    ) -> None:
        self._utxos[(txid, index)] = output
        self._meta[(txid, index)] = (is_coinbase, height)

    def spend(self, txid: str, index: int) -> None:
        self._utxos.pop((txid, index), None)
        self._meta.pop((txid, index), None)

    def __len__(self) -> int:
        return len(self._utxos)

    def items(self) -> Iterator[tuple[str, int, TxOutput]]:
        for (txid, index), out in self._utxos.items():
            yield txid, index, out

    def total_value(self) -> int:
        return sum(out.amount for out in self._utxos.values())

    def copy(self) -> "UTXOSet":
        clone = UTXOSet()
        clone._utxos = dict(self._utxos)
        clone._meta = dict(self._meta)
        return clone

    # ----- validation & application --------------------------------------- #
    def validate_transaction(
        self,
        tx: Transaction,
        *,
        spend_height: Optional[int] = None,
        maturity: int = 0,
    ) -> bool:
        """Full validity of a non-coinbase tx against the current set.

        Delegates signature/authorization/no-overspend checks to Transaction
        .verify (which uses this set as its resolver), and additionally ensures
        every referenced outpoint is currently unspent. When `spend_height` and
        `maturity` are supplied, a coinbase output may only be spent once it is
        at least `maturity` blocks deep (the coinbase-maturity rule).
        """
        if tx.is_coinbase():
            return False
        for txin in tx.inputs:
            if not self.contains(txin.prev_txid, txin.output_index):
                return False
            if maturity and spend_height is not None:
                m = self._meta.get((txin.prev_txid, txin.output_index))
                if m is not None and m[0] and spend_height - m[1] < maturity:
                    return False  # coinbase not yet mature
        return tx.verify(self.resolve)

    def apply_transaction(self, tx: Transaction, height: int = 0) -> None:
        """Consume a tx's inputs and register its outputs. Assumes validity
        (coinbases skip input consumption since their input is the null marker)."""
        is_cb = tx.is_coinbase()
        if not is_cb:
            for txin in tx.inputs:
                self.spend(txin.prev_txid, txin.output_index)
        txid = tx.txid
        for i, out in enumerate(tx.outputs):
            self.add(txid, i, out, is_coinbase=is_cb, height=height)

    def apply_block(self, block: Block, height: int = 0) -> None:
        for tx in block.transactions:
            self.apply_transaction(tx, height)

    def total_fees(self, block: Block) -> int:
        """Sum of (inputs - outputs) across the block's non-coinbase txs.

        Must be called against the set as it stood BEFORE the block was applied.
        """
        fees = 0
        for tx in block.transactions:
            if tx.is_coinbase():
                continue
            fees += tx.fee(self.resolve)
        return fees


def validate_coinbase(block: Block, height: int, expected_subsidy: int, fees: int) -> bool:
    """A block's first tx must be a coinbase for `height` paying no more than
    subsidy + fees (miners may under-claim; over-claiming is invalid)."""
    if not block.transactions:
        return False
    cb = block.transactions[0]
    if not cb.is_coinbase():
        return False
    if coinbase_height(cb) != height:
        return False
    if any(other.is_coinbase() for other in block.transactions[1:]):
        return False
    claimed = sum(o.amount for o in cb.outputs)
    return claimed <= expected_subsidy + fees


# --------------------------------------------------------------------------- #
# Section 7 pruning demonstration
# --------------------------------------------------------------------------- #
def merkle_pruning_demo(num_transactions: int) -> dict:
    """Show the disk-space argument: to prove one tx is in a block of N txs, an
    SPV proof keeps only ceil(log2(N)) interior hashes; the other spent tx
    bodies can be discarded while the header's Merkle root stays valid."""
    if num_transactions < 1:
        raise ValueError("need at least one transaction")
    branch_hashes = max(1, math.ceil(math.log2(num_transactions)))
    return {
        "transactions": num_transactions,
        "hashes_needed_for_proof": branch_hashes,
        "bodies_prunable": num_transactions - 1,
    }

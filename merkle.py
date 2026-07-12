"""MyCoin — Milestone 2/7: Merkle tree (Bitcoin whitepaper section 7, section 8).

Transactions in a block are committed to by a single Merkle root in the block
header. This lets a lightweight (SPV) client verify that a transaction is
included in a block using only a small branch of hashes, without downloading
the whole block (section 8), and lets full nodes prune spent transaction data
while keeping the interior hashes that preserve the root (section 7).

Construction rule (matching Bitcoin): hash leaves pairwise with double-SHA-256;
if a level has an odd number of nodes, duplicate the last node before pairing.

Trade-off note: Bitcoin hashes the natural byte encodings of transactions. Here
a "leaf" is a transaction id (hex string), hashed as its raw bytes, which keeps
the code readable and consistent with `Transaction.txid`.
"""

from __future__ import annotations

import hashlib


def _h(data: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def _hash_pair(left: str, right: str) -> str:
    """Combine two child hashes (hex) into a parent hash (hex)."""
    return _h(bytes.fromhex(left) + bytes.fromhex(right)).hex()


def merkle_root(txids: list[str]) -> str:
    """Compute the Merkle root (hex) of a list of transaction ids (hex).

    An empty list has no root; callers should ensure at least the coinbase tx.
    """
    if not txids:
        raise ValueError("merkle_root requires at least one txid")

    level = list(txids)
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])  # duplicate last node on odd count
        level = [_hash_pair(level[i], level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]


def merkle_proof(txids: list[str], index: int) -> list[tuple[str, str]]:
    """Return the authentication branch for the txid at `index`.

    The branch is a list of (sibling_hash, side) pairs walking leaf -> root,
    where `side` is "left" or "right" describing where the sibling sits. An SPV
    client combines these with its own txid to recompute the root.
    """
    if not txids:
        raise ValueError("merkle_proof requires at least one txid")
    if not 0 <= index < len(txids):
        raise IndexError("index out of range")

    proof: list[tuple[str, str]] = []
    level = list(txids)
    idx = index
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        if idx % 2 == 0:  # node is a left child, sibling is on the right
            proof.append((level[idx + 1], "right"))
        else:  # node is a right child, sibling is on the left
            proof.append((level[idx - 1], "left"))
        idx //= 2
        level = [_hash_pair(level[i], level[i + 1]) for i in range(0, len(level), 2)]
    return proof


def verify_merkle_proof(txid: str, proof: list[tuple[str, str]], root: str) -> bool:
    """Recompute the root from a txid and its branch; compare to `root`."""
    acc = txid
    for sibling, side in proof:
        if side == "right":
            acc = _hash_pair(acc, sibling)
        elif side == "left":
            acc = _hash_pair(sibling, acc)
        else:
            return False
    return acc == root

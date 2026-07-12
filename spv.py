"""MyCoin — Milestone 7: Simplified Payment Verification (whitepaper section 8).

An SPV (Simplified Payment Verification) client is a *light* node. Rather than
downloading and validating every transaction in every block, it keeps only the
block *headers* — the most-work chain of proof-of-work commitments. To confirm
that a specific payment happened, it asks a full node for a Merkle *branch*
linking that transaction's id to the `merkle_root` recorded in a block header
(section 8). If the branch recomputes to the header's root, the transaction is
provably included in that block, and the number of headers chained on top of it
(confirmations) measures how much work would have to be redone to reverse it.

How the pieces fit together:
  * `merkle.verify_merkle_proof` checks inclusion of one txid under one root.
  * The header chain (`SPVClient`) supplies the trusted root for a block hash and
    the confirmation depth.
  * A full node uses `build_proof_bundle` to package (txid, block_hash, branch)
    for the client; the client never sees the other transactions.

Trade-off vs. a full node:
  An SPV client trusts that the most-work header chain was produced by an honest
  majority of hashing power. It *cannot* independently detect an invalid block
  (e.g. one that mints coins out of thin air or contains a double-spend) because
  it never validates the transactions inside blocks — it only checks Merkle
  inclusion and proof-of-work depth. As the whitepaper notes, this verification
  is reliable "as long as honest nodes control the network," but can be fooled by
  an attacker who can sustain more proof-of-work than the honest network. To
  mitigate this, real SPV clients rely on the honest majority and on network
  *alerts* from full nodes that detect an invalid block, prompting the light
  client to download the full block and confirm the inconsistency. That safety
  net, and the inability to self-validate, is the price paid for storing only
  headers instead of the whole chain.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from block import BlockHeader, Block, genesis_block
from merkle import merkle_proof, verify_merkle_proof


@dataclass
class MerkleProofBundle:
    """What a full node hands an SPV client to prove a single payment.

    Contains just enough to check one transaction's inclusion in one block:
    the transaction id, the hash of the block it claims membership in, and the
    Merkle branch (list of (sibling_hash_hex, side) pairs) linking the txid to
    that block's Merkle root.
    """

    txid: str
    block_hash: str
    proof: list[tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "txid": self.txid,
            "block_hash": self.block_hash,
            # tuples are serialized as 2-element lists for JSON transport
            "proof": [[sibling, side] for sibling, side in self.proof],
        }

    @staticmethod
    def from_dict(d: dict) -> "MerkleProofBundle":
        return MerkleProofBundle(
            txid=d["txid"],
            block_hash=d["block_hash"],
            proof=[(sibling, side) for sibling, side in d["proof"]],
        )


class SPVClient:
    """A light client that stores only block headers (whitepaper section 8).

    The chain is seeded with the genesis header and grown by `add_header`, which
    accepts a header only if it links to the current tip. Payments are checked
    against the header's Merkle root; confirmation depth is read off the chain.
    """

    def __init__(self) -> None:
        # Headers only — never full blocks or transactions.
        self._headers: list[BlockHeader] = [genesis_block().header]
        # hash -> index, for O(1) lookup by block hash.
        self._index_by_hash: dict[str, int] = {self._headers[0].hash(): 0}

    def add_header(self, header: BlockHeader) -> bool:
        """Append `header` iff it links to the current tip; return success.

        SPV clients follow the most-work header chain. For this milestone a
        simple linear append suffices, but a header whose `prev_hash` does not
        match the tip is rejected so the stored chain stays connected.
        """
        if header.prev_hash != self.tip_hash:
            return False
        self._headers.append(header)
        self._index_by_hash[header.hash()] = len(self._headers) - 1
        return True

    @property
    def height(self) -> int:
        """Tip height; the genesis header is height 0."""
        return len(self._headers) - 1

    @property
    def tip_hash(self) -> str:
        return self._headers[-1].hash()

    def header_by_hash(self, h: str) -> BlockHeader | None:
        idx = self._index_by_hash.get(h)
        return None if idx is None else self._headers[idx]

    def confirmations(self, block_hash: str) -> int:
        """Headers from `block_hash` to the tip inclusive (tip itself = 1).

        Returns 0 if the block hash is not on the stored chain.
        """
        idx = self._index_by_hash.get(block_hash)
        if idx is None:
            return 0
        return len(self._headers) - idx

    def verify_payment(self, bundle: MerkleProofBundle) -> bool:
        """Confirm the bundle's txid is included in its claimed block.

        Looks up the trusted header for `bundle.block_hash`; if the client has
        never seen that block, verification fails. Otherwise the Merkle branch
        must recompute to the header's committed Merkle root.
        """
        header = self.header_by_hash(bundle.block_hash)
        if header is None:
            return False
        return verify_merkle_proof(bundle.txid, bundle.proof, header.merkle_root)

    def verify_payment_with_confirmations(
        self, bundle: MerkleProofBundle, min_confirmations: int
    ) -> bool:
        """Inclusion proof AND at least `min_confirmations` headers deep."""
        if not self.verify_payment(bundle):
            return False
        return self.confirmations(bundle.block_hash) >= min_confirmations


def build_proof_bundle(block: Block, txid: str) -> MerkleProofBundle:
    """Full-node helper: package the Merkle branch proving `txid` is in `block`.

    Raises ValueError if `txid` is not one of the block's transactions.
    """
    txids = [tx.txid for tx in block.transactions]
    try:
        index = txids.index(txid)
    except ValueError:
        raise ValueError(f"txid {txid} is not in block {block.hash}")
    proof = merkle_proof(txids, index)
    return MerkleProofBundle(txid=txid, block_hash=block.hash, proof=proof)

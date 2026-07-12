"""MyCoin — Milestone 4: Peer-to-peer network (whitepaper section 5).

An in-process simulation of a gossip network so we can run several `Node`s in
one program and exercise transaction/block propagation, forks, reorgs, and the
"nodes always consider the longest chain to be correct" rule. It also models
dropped messages: broadcasts can be randomly lost, and a node that receives a
block whose parent it is missing (a gap) can pull the parent on demand via
`request_block`, satisfying section 5's "if a node does not receive a block, it
will request it when it realizes it missed one."

Trade-off vs Bitcoin: real nodes speak a binary TCP protocol with inventory
(inv/getdata) negotiation and DoS protection. Here delivery is synchronous
function calls between in-memory peers, which is enough to demonstrate the
consensus behavior end-to-end.
"""

from __future__ import annotations

import random
from typing import Optional

from block import Block
from node import Node
from transaction import Transaction


class Network:
    def __init__(self, drop_rate: float = 0.0, seed: Optional[int] = None) -> None:
        self.nodes: dict[str, Node] = {}
        self.drop_rate = drop_rate
        self._rng = random.Random(seed)

    # ----- membership ----------------------------------------------------- #
    def connect(self, node: Node) -> None:
        node.network = self
        self.nodes[node.node_id] = node

    def peers_of(self, node_id: str) -> list[Node]:
        return [n for nid, n in self.nodes.items() if nid != node_id]

    def _dropped(self) -> bool:
        return self.drop_rate > 0 and self._rng.random() < self.drop_rate

    # ----- gossip --------------------------------------------------------- #
    def broadcast_tx(self, sender_id: str, tx: Transaction) -> None:
        for peer in self.peers_of(sender_id):
            if self._dropped():
                continue  # message lost; peer may still learn the tx later
            peer.receive_transaction(tx)

    def broadcast_block(self, sender_id: str, block: Block) -> None:
        for peer in self.peers_of(sender_id):
            if self._dropped():
                continue  # dropped: peer will request it when it sees a child
            peer.receive_block(block)

    def request_block(self, requester_id: str, block_hash: str) -> Optional[Block]:
        """Pull a specific block from any peer that has it (getdata)."""
        for peer in self.peers_of(requester_id):
            block = peer.get_block(block_hash)
            if block is not None:
                return block
        return None

    # ----- convenience for tests ------------------------------------------ #
    def sync(self) -> None:
        """Bring every node to the best-known tip by pushing each node's active
        chain to all peers. Useful after lossy periods to reconcile state."""
        best = max(
            self.nodes.values(),
            key=lambda n: n.chain.chainwork[n.chain.tip],
        )
        for h in best.chain.active_chain():
            block = best.chain.blocks[h]
            for peer in self.peers_of(best.node_id):
                peer.receive_block(block)

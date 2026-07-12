"""BigCoin Full Node - Combines P2P network with local blockchain.

This is what users run to participate in the decentralized network.
Each full node:
- Maintains complete blockchain copy
- Validates blocks and transactions
- Mines new blocks
- Broadcasts to peers
- Syncs state with network
"""

import os
import time
import json
import logging
import threading
from typing import Optional

from node import Node
from p2p_network import P2PNode, BootstrapServer
from transaction import generate_keypair, pubkey_hash, Transaction
from wallet import Wallet, address_from_pubkey_hash, pubkey_hash_from_address

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BigCoinFullNode(P2PNode):
    """Full node that runs blockchain + P2P network."""

    def __init__(self, node_id: str, host: str = "127.0.0.1", port: int = 9000,
                 coinbase_maturity: int = 100):
        """Initialize full node.

        Args:
            node_id: Unique identifier (e.g., "alice", "bob")
            host: Bind address
            port: Bind port
            coinbase_maturity: Blocks a coinbase must age before it is spendable
        """
        super().__init__(node_id, host, port)

        # Initialize local blockchain
        self.blockchain = Node(node_id, coinbase_maturity=coinbase_maturity)
        logger.info(f"[{node_id}] Blockchain initialized - Height: {self.blockchain.chain.height}")

        # Wallet: holds the signing keys for addresses this node owns, so it can
        # both receive mined coins and sign outgoing transactions. Keys are
        # persisted to disk so addresses/coins survive a restart.
        self.wallet = Wallet()
        self.wallet_file = os.path.join("walletdata", f"{node_id}.json")
        self._wallet_lock = threading.Lock()
        self._load_wallet()

        # Mining state
        self.mining_enabled = False
        self.mining_address: Optional[str] = None
        self.mining_thread: Optional[threading.Thread] = None

        # Serializes all chain mutations (local mining + peer blocks)
        self.chain_lock = threading.RLock()

        # Sync state
        self.syncing = False
        self.last_sync_time = time.time()

        # Disk persistence: restore any previously-saved chain
        self.chain_file = os.path.join("chaindata", f"{node_id}.jsonl")
        self._persist_lock = threading.Lock()
        self._load_chain()

    def _load_chain(self):
        """Restore non-genesis blocks from disk (if any) so we resume at saved height."""
        from block import Block

        if not os.path.exists(self.chain_file):
            return

        restored = 0
        with open(self.chain_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    block = Block.from_dict(json.loads(line))
                except Exception as e:
                    logger.warning(f"[{self.node_id}] Skipping bad persisted block: {e}")
                    continue
                with self.chain_lock:
                    result = self.blockchain.chain.add_block(block)
                if result in ("extended", "reorg"):
                    restored += 1

        if restored:
            logger.info(
                f"[{self.node_id}] Restored {restored} block(s) from disk"
                f" - Height: {self.blockchain.chain.height}"
            )

    def _persist_block(self, block):
        """Append an accepted non-genesis block to the on-disk chain file."""
        try:
            with self._persist_lock:
                os.makedirs(os.path.dirname(self.chain_file), exist_ok=True)
                with open(self.chain_file, "a") as f:
                    f.write(json.dumps(block.to_dict()) + "\n")
        except Exception as e:
            logger.warning(f"[{self.node_id}] Failed to persist block: {e}")

    def _load_wallet(self):
        """Restore this node's wallet keys from disk (if any)."""
        if not os.path.exists(self.wallet_file):
            return
        try:
            with open(self.wallet_file) as f:
                privkeys = json.load(f)
            for pk in privkeys:
                self.wallet.load_privkey(pk)
            logger.info(f"[{self.node_id}] Restored {len(privkeys)} wallet key(s) from disk")
        except Exception as e:
            logger.warning(f"[{self.node_id}] Failed to load wallet: {e}")

    def _save_wallet(self):
        """Persist all wallet signing keys to disk (plaintext, local demo use)."""
        try:
            with self._wallet_lock:
                os.makedirs(os.path.dirname(self.wallet_file), exist_ok=True)
                with open(self.wallet_file, "w") as f:
                    json.dump(self.wallet.export_privkeys(), f)
        except Exception as e:
            logger.warning(f"[{self.node_id}] Failed to save wallet: {e}")

    def start_server(self):
        """Start P2P server, then background tasks (self.running is now True)."""
        super().start_server()
        self.start_background_tasks()

    def start_background_tasks(self):
        """Start background sync and keep-alive tasks."""
        # Periodic sync
        threading.Thread(daemon=True, target=self._sync_loop).start()

        # Periodic keep-alive (ping)
        threading.Thread(daemon=True, target=self._keepalive_loop).start()

        # Process pending blocks
        threading.Thread(daemon=True, target=self._process_pending_blocks).start()

        # Process pending transactions received from peers
        threading.Thread(daemon=True, target=self._process_pending_txs).start()

    def _sync_loop(self):
        """Periodically catch up to any peer that is ahead.

        Live block gossip is best-effort and can drop messages; this loop
        guarantees eventual convergence by pulling missing blocks by height
        over each peer's (reliable) HTTP RPC interface.
        """
        while self.running:
            try:
                if self.get_peer_count() > 0:
                    self._sync_with_peers()
            except Exception as e:
                logger.debug(f"[{self.node_id}] Sync error: {e}")
            time.sleep(5)

    @staticmethod
    def _peer_rpc_port(p2p_port: int) -> int:
        """RPC port convention used by the launchers: rpc = p2p - 1000."""
        return p2p_port - 1000

    def _sync_with_peers(self):
        """Ask each peer its height (over HTTP) and download any missing blocks."""
        import requests

        for peer in self.get_connected_peers():
            rpc_port = self._peer_rpc_port(peer.port)
            try:
                info = requests.get(
                    f"http://{peer.host}:{rpc_port}/api/blockchain/info", timeout=3
                ).json()
                peer_height = info.get('height', 0)
            except Exception:
                continue

            if peer_height > self.blockchain.chain.height:
                self._download_blocks(
                    peer.host, rpc_port,
                    self.blockchain.chain.height + 1, peer_height
                )
        self.last_sync_time = time.time()

    def _download_blocks(self, host: str, rpc_port: int, start: int, end: int):
        """Fetch blocks [start, end] by height from a peer and add them in order."""
        import requests
        from block import Block

        for height in range(start, end + 1):
            try:
                resp = requests.get(f"http://{host}:{rpc_port}/api/block/{height}", timeout=3)
                if resp.status_code != 200:
                    break
                block = Block.from_dict(resp.json()['block'])
            except Exception:
                break

            with self.chain_lock:
                result = self.blockchain.chain.add_block(block)

            if result in ("extended", "reorg"):
                self._persist_block(block)
            elif result not in ("duplicate",):
                logger.debug(f"[{self.node_id}] Sync halted at height {height}: {result}")
                break

        logger.info(f"[{self.node_id}] Synced -> Height: {self.blockchain.chain.height}")

    def _keepalive_loop(self):
        """Periodically send ping to peers."""
        while self.running:
            try:
                self.send_ping_to_all()
                self.cleanup_dead_peers()
                time.sleep(30)  # Keep-alive every 30 seconds
            except Exception as e:
                logger.debug(f"[{self.node_id}] Keep-alive error: {e}")

    def _process_pending_blocks(self):
        """Process blocks received from peers."""
        while self.running:
            try:
                if self.pending_blocks:
                    block_data = self.pending_blocks.pop(0)
                    self._validate_and_add_block(block_data)
                time.sleep(0.1)
            except Exception as e:
                logger.debug(f"[{self.node_id}] Block processing error: {e}")

    def _process_pending_txs(self):
        """Drain transactions gossiped by peers into the local mempool."""
        while self.running:
            try:
                if self.pending_transactions:
                    _tx_hash, tx_json = self.pending_transactions.pop()
                    self._accept_peer_transaction(tx_json)
                time.sleep(0.1)
            except KeyError:
                time.sleep(0.1)
            except Exception as e:
                logger.debug(f"[{self.node_id}] Tx processing error: {e}")

    def _accept_peer_transaction(self, tx_json: str):
        """Validate a peer transaction, add to mempool, and relay if newly seen."""
        try:
            tx_data = json.loads(tx_json)
            tx = Transaction.from_dict(tx_data)
        except Exception as e:
            logger.warning(f"[{self.node_id}] Malformed tx from peer: {e}")
            return

        with self.chain_lock:
            added = self.blockchain.chain.add_to_mempool(tx)

        if added:
            self.broadcast({'type': 'new_transaction', 'transaction': tx_data})

    def _validate_and_add_block(self, block_data: dict):
        """Validate and add block from peer, then relay if newly accepted."""
        from block import Block

        try:
            block = Block.from_dict(block_data)
        except Exception as e:
            logger.warning(f"[{self.node_id}] Malformed block from peer: {e}")
            return

        with self.chain_lock:
            result = self.blockchain.chain.add_block(block)

        if result in ("extended", "reorg"):
            self._persist_block(block)
            logger.info(
                f"[{self.node_id}] Accepted peer block ({result})"
                f" - Height: {self.blockchain.chain.height}"
            )
            # Flood-fill to other peers; duplicates stop the cascade naturally.
            self.broadcast({
                'type': 'new_block',
                'block': block_data,
                'node_id': self.node_id
            })
        elif result == "orphan":
            logger.debug(f"[{self.node_id}] Orphan block from peer (missing parent)")
        elif result == "invalid":
            logger.warning(f"[{self.node_id}] Rejected invalid block from peer")

    # ========================================================================= #
    # MINING
    # ========================================================================= #

    def start_mining(self, address: str):
        """Start mining with given address.

        Coinbase outputs are locked to the pubkey_hash decoded from the Base58
        address, so a wallet that generated that address actually owns (and can
        spend) the mined coins. If `address` is already a raw pubkey_hash, it is
        used as-is.
        """
        self.mining_address = address
        try:
            self.mining_pkh = pubkey_hash_from_address(address)
        except Exception:
            self.mining_pkh = address
        self.mining_enabled = True

        self.mining_thread = threading.Thread(
            daemon=True,
            target=self._mining_loop
        )
        self.mining_thread.start()

        logger.info(f"[{self.node_id}] Mining started for {address[:20]}...")
        return {"status": "mining_started"}

    def stop_mining(self):
        """Stop mining."""
        self.mining_enabled = False
        logger.info(f"[{self.node_id}] Mining stopped")

    def _mining_loop(self):
        """Main mining loop."""
        while self.mining_enabled:
            try:
                # Mine one block
                with self.chain_lock:
                    block = self.blockchain.mine_block(self.mining_pkh)

                if block:
                    self._persist_block(block)
                    logger.info(f"[{self.node_id}] Mined block #{self.blockchain.chain.height}")

                    # Broadcast to peers
                    announcement = {
                        'type': 'new_block',
                        'block': block.to_dict(),
                        'node_id': self.node_id
                    }
                    self.broadcast(announcement)

                    # Small delay between blocks
                    time.sleep(0.5)

            except Exception as e:
                logger.error(f"[{self.node_id}] Mining error: {e}")

    # ========================================================================= #
    # WALLET / ADDRESS MANAGEMENT
    # ========================================================================= #

    def generate_new_address(self) -> dict:
        """Generate a new address in this node's wallet and persist the key."""
        addr = self.wallet.new_key()
        pkh = pubkey_hash_from_address(addr)
        self._save_wallet()

        return {
            'address': addr,
            'pubkey_hash': pkh
            # NOTE: Private key NOT included in response (serialize safely)
        }

    def _wallet_utxos(self):
        """UTXOs on the active chain that this node's wallet can spend."""
        return [
            (txid, index, out)
            for txid, index, out in self.blockchain.chain.utxo.items()
            if self.wallet.owns(out.pubkey_hash)
        ]

    def send_to_address(self, to_address: str, amount_cents: int, fee: int = 0) -> dict:
        """Build, sign, submit, and broadcast a payment from the node's wallet."""
        try:
            with self.chain_lock:
                utxos = self._wallet_utxos()
                tx = self.wallet.create_transaction(utxos, to_address, amount_cents, fee=fee)
                added = self.blockchain.chain.add_to_mempool(tx)

            if not added:
                return {'status': 'error', 'message': 'transaction rejected by mempool'}

            # create_transaction may have minted a fresh change key — persist it.
            self._save_wallet()
            self.broadcast({'type': 'new_transaction', 'transaction': tx.to_dict()})
            return {'status': 'success', 'txid': tx.txid, 'message': 'transaction submitted'}
        except ValueError as e:
            return {'status': 'error', 'message': str(e)}
        except Exception as e:
            logger.error(f"[{self.node_id}] send_to_address error: {e}")
            return {'status': 'error', 'message': str(e)}

    def get_mempool(self) -> dict:
        """Summarize the pending (unconfirmed) transactions in the mempool."""
        mempool = self.blockchain.chain.mempool
        txs = [
            {
                'txid': txid,
                'inputs': len(tx.inputs),
                'outputs': len(tx.outputs),
                'total_out_cents': sum(o.amount for o in tx.outputs),
            }
            for txid, tx in mempool.items()
        ]
        return {'count': len(txs), 'transactions': txs}

    def get_balance(self) -> dict:
        """Get wallet balance."""
        total_cents = self.blockchain.chain.utxo.total_value()
        return {
            'balance_cents': total_cents,
            'balance_coins': total_cents / 100_000_000
        }

    def get_block_by_height(self, height: int) -> Optional[dict]:
        """Return the active-chain block at `height` as a dict, or None."""
        chain = self.blockchain.chain
        active = chain.active_chain()  # genesis..tip hashes, index == height
        if 0 <= height < len(active):
            return chain.blocks[active[height]].to_dict()
        return None

    def get_blockchain_info(self) -> dict:
        """Get blockchain information."""
        return {
            'height': self.blockchain.chain.height,
            'tip_hash': self.blockchain.chain.tip,
            'total_money_cents': self.blockchain.chain.utxo.total_value(),
            'total_money_coins': self.blockchain.chain.utxo.total_value() / 100_000_000,
            'tx_count': sum(
                len(block.transactions) for block in self.blockchain.chain.blocks.values()
            ),
            'node_id': self.node_id,
            'connected_peers': self.get_peer_count(),
            'version': self.version
        }

    # ========================================================================= #
    # JSON-RPC API
    # ========================================================================= #

    def process_rpc_request(self, request: dict) -> dict:
        """Process JSON-RPC request."""
        method = request.get('method')
        params = request.get('params', {})

        try:
            if method == 'new_address':
                return self.generate_new_address()

            elif method == 'get_balance':
                return self.get_balance()

            elif method == 'blockchain_info':
                return self.get_blockchain_info()

            elif method == 'start_mining':
                address = params.get('address')
                if not address:
                    return {'error': 'No address provided'}
                self.start_mining(address)
                return {'status': 'mining_started'}

            elif method == 'stop_mining':
                self.stop_mining()
                return {'status': 'mining_stopped'}

            elif method == 'send_transaction':
                to_address = params.get('to_address')
                amount_cents = params.get('amount_cents')
                if not to_address or amount_cents is None:
                    return {'error': 'to_address and amount_cents required'}
                return self.send_to_address(
                    to_address, int(amount_cents), fee=int(params.get('fee', 0))
                )

            elif method == 'get_mempool':
                return self.get_mempool()

            elif method == 'connect_peer':
                host = params.get('host', '127.0.0.1')
                port = params.get('port')
                if not port:
                    return {'error': 'No port provided'}
                success = self.connect_to_peer(host, int(port))
                return {
                    'status': 'connected' if success else 'failed',
                    'host': host,
                    'port': port
                }

            elif method == 'mining_status':
                return {
                    'is_mining': self.mining_enabled,
                    'mining_address': self.mining_address,
                    'height': self.blockchain.chain.height
                }

            elif method == 'peer_info':
                peers = self.get_connected_peers()
                return {
                    'connected_peers': len(peers),
                    'peers': [p.to_dict() for p in peers]
                }

            elif method == 'node_stats':
                return self.get_stats()

            else:
                return {'error': f'Unknown method: {method}'}

        except Exception as e:
            return {'error': str(e)}


def main():
    """Run a full node (for testing)."""
    import sys

    node_id = sys.argv[1] if len(sys.argv) > 1 else "node1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9000

    # Create node
    node = BigCoinFullNode(node_id, host="127.0.0.1", port=port)

    # Start server
    node.start_server()

    try:
        while True:
            time.sleep(1)
            if node.get_peer_count() > 0:
                print(
                    f"[{node_id}] Peers: {node.get_peer_count()}, "
                    f"Height: {node.blockchain.chain.height}"
                )

    except KeyboardInterrupt:
        print(f"\n[{node_id}] Shutting down...")
        node.stop_server()


if __name__ == "__main__":
    main()

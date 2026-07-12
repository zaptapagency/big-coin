"""MyCoin P2P Network - Decentralized blockchain synchronization.

This module handles:
- Peer discovery and connection
- Blockchain synchronization
- Transaction broadcasting
- Block propagation
- Network resilience
"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Optional, List, Set, Dict, Callable
import hashlib
import threading

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PeerInfo:
    """Information about a peer node."""
    node_id: str
    host: str
    port: int
    version: str = "1.0.0"
    last_seen: float = None

    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = time.time()

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def is_alive(self, timeout=300) -> bool:
        """Check if peer is still responsive (5 min timeout)."""
        return time.time() - self.last_seen < timeout

    def to_address(self) -> tuple:
        return (self.host, self.port)


class P2PNode:
    """Main P2P node that participates in the network."""

    def __init__(self, node_id: str, host: str = "127.0.0.1", port: int = 9000):
        """Initialize a P2P node.

        Args:
            node_id: Unique identifier for this node (e.g., "alice", "bob")
            host: IP address to bind to
            port: Port to listen on
        """
        self.node_id = node_id
        self.host = host
        self.port = port
        self.version = "1.0.0"

        # Peer management
        self.peers: dict[str, PeerInfo] = {}  # peer_id -> PeerInfo
        self.peer_sockets: dict[str, socket.socket] = {}  # peer_id -> socket
        self.peer_lock = threading.RLock()

        # Blockchain sync
        self.blockchain = None  # Will be set by caller
        self.pending_blocks: list = []
        self.pending_transactions: set = set()

        # Message handlers
        self.handlers: dict[str, Callable] = {}
        self.register_default_handlers()

        # Network stats
        self.messages_sent = 0
        self.messages_received = 0
        self.bytes_sent = 0
        self.bytes_received = 0

        # Server socket
        self.server_socket: Optional[socket.socket] = None
        self.running = False

        logger.info(f"[{self.node_id}] P2P Node initialized on {host}:{port}")

    def register_handler(self, message_type: str, handler: Callable):
        """Register a handler for a message type."""
        self.handlers[message_type] = handler

    def register_default_handlers(self):
        """Register default message handlers."""
        self.handlers['ping'] = self.handle_ping
        self.handlers['pong'] = self.handle_pong
        self.handlers['peer_list'] = self.handle_peer_list
        self.handlers['get_blocks'] = self.handle_get_blocks
        self.handlers['get_block'] = self.handle_get_block
        self.handlers['new_block'] = self.handle_new_block
        self.handlers['new_transaction'] = self.handle_new_transaction
        self.handlers['sync_request'] = self.handle_sync_request

    # ========================================================================= #
    # SERVER - Listen for incoming connections
    # ========================================================================= #

    def start_server(self):
        """Start listening for incoming peer connections."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)

            logger.info(f"[{self.node_id}] P2P Server listening on {self.host}:{self.port}")
            self.running = True

            # Start accepting connections in background thread
            threading.Thread(daemon=True, target=self._accept_connections).start()

        except Exception as e:
            logger.error(f"[{self.node_id}] Failed to start server: {e}")
            raise

    def stop_server(self):
        """Stop the P2P server."""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        logger.info(f"[{self.node_id}] P2P Server stopped")

    def _accept_connections(self):
        """Accept incoming peer connections (runs in background thread)."""
        while self.running:
            try:
                peer_socket, peer_addr = self.server_socket.accept()
                peer_socket.settimeout(30)

                # Handle peer in background thread
                threading.Thread(
                    daemon=True,
                    target=self._handle_peer_connection,
                    args=(peer_socket, peer_addr)
                ).start()

            except Exception as e:
                if self.running:
                    logger.debug(f"[{self.node_id}] Accept error: {e}")

    @staticmethod
    def _encode(message: dict) -> bytes:
        """Frame a message as newline-delimited JSON for stream transport."""
        return (json.dumps(message) + "\n").encode()

    def _handle_peer_connection(self, peer_socket: socket.socket, peer_addr: tuple):
        """Handle incoming connection from a peer."""
        try:
            # Read exactly one framed handshake line (buffer until newline).
            buffer = ""
            while "\n" not in buffer:
                data = peer_socket.recv(4096)
                if not data:
                    return
                buffer += data.decode(errors="ignore")

            line, buffer = buffer.split("\n", 1)
            message = json.loads(line)

            if message.get('type') == 'handshake':
                # Process handshake and get peer info
                peer_info = self._process_handshake(message, peer_addr, peer_socket)

                if peer_info:
                    logger.info(f"[{self.node_id}] Connected to peer: {peer_info.node_id}")

                    # Keep connection alive; pass leftover bytes into the loop.
                    self._peer_message_loop(peer_socket, peer_info, initial_buffer=buffer)

        except Exception as e:
            logger.debug(f"[{self.node_id}] Peer connection error: {e}")
        finally:
            try:
                peer_socket.close()
            except Exception:
                pass

    def _process_handshake(
        self, message: dict, peer_addr: tuple, peer_socket: socket.socket
    ) -> Optional[PeerInfo]:
        """Process handshake message from incoming peer."""
        try:
            peer_info = PeerInfo(
                node_id=message.get('node_id'),
                host=message.get('host', peer_addr[0]),
                port=message.get('port', peer_addr[1]),
                version=message.get('version', '1.0.0')
            )

            # Add peer
            with self.peer_lock:
                self.peers[peer_info.node_id] = peer_info
                self.peer_sockets[peer_info.node_id] = peer_socket

            # Send handshake response
            response = {
                'type': 'handshake',
                'node_id': self.node_id,
                'host': self.host,
                'port': self.port,
                'version': self.version,
                'blockchain_height': self.blockchain.chain.height if self.blockchain else 0
            }
            peer_socket.sendall(self._encode(response))

            return peer_info

        except Exception as e:
            logger.error(f"[{self.node_id}] Handshake error: {e}")
            return None

    def _peer_message_loop(
        self, peer_socket: socket.socket, peer_info: PeerInfo, initial_buffer: str = ""
    ):
        """Receive and process newline-framed messages from a peer."""
        buffer = initial_buffer
        while self.running:
            # Drain any complete messages already buffered.
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue
                try:
                    message = json.loads(line)
                except Exception:
                    continue  # skip malformed frame, keep the stream alive

                peer_info.last_seen = time.time()
                self.messages_received += 1
                message_type = message.get('type')
                if message_type in self.handlers:
                    self.handlers[message_type](peer_info, message)

            try:
                data = peer_socket.recv(4096)
                if not data:
                    break
                buffer += data.decode(errors="ignore")
                self.bytes_received += len(data)
            except TimeoutError:
                continue
            except Exception as e:
                logger.debug(f"[{self.node_id}] Message loop error: {e}")
                break

        # Cleanup
        with self.peer_lock:
            if peer_info.node_id in self.peer_sockets:
                del self.peer_sockets[peer_info.node_id]

    # ========================================================================= #
    # CLIENT - Connect to other peers
    # ========================================================================= #

    def connect_to_peer(self, peer_host: str, peer_port: int, peer_id: str = None) -> bool:
        """Connect to another peer node.

        Args:
            peer_host: IP address of peer
            peer_port: Port of peer
            peer_id: Optional ID of peer (will discover if not provided)

        Returns:
            True if connection successful
        """
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.settimeout(10)
            peer_socket.connect((peer_host, peer_port))

            # Send handshake
            handshake = {
                'type': 'handshake',
                'node_id': self.node_id,
                'host': self.host,
                'port': self.port,
                'version': self.version,
                'blockchain_height': self.blockchain.chain.height if self.blockchain else 0
            }
            peer_socket.sendall(self._encode(handshake))

            # Receive framed handshake response (buffer until newline).
            buffer = ""
            while "\n" not in buffer:
                data = peer_socket.recv(4096)
                if not data:
                    return False
                buffer += data.decode(errors="ignore")
            line, buffer = buffer.split("\n", 1)
            response = json.loads(line)

            # Create peer info
            peer_info = PeerInfo(
                node_id=response.get('node_id', peer_id or f"peer_{peer_host}_{peer_port}"),
                host=response.get('host', peer_host),
                port=response.get('port', peer_port),
                version=response.get('version', '1.0.0')
            )

            # Add to peers
            with self.peer_lock:
                self.peers[peer_info.node_id] = peer_info
                self.peer_sockets[peer_info.node_id] = peer_socket

            logger.info(
                f"[{self.node_id}] Connected to peer: {peer_info.node_id} "
                f"at {peer_host}:{peer_port}"
            )

            # Start receiving messages from this peer (pass leftover bytes).
            threading.Thread(
                daemon=True,
                target=self._peer_message_loop,
                args=(peer_socket, peer_info, buffer)
            ).start()

            return True

        except Exception as e:
            logger.warning(f"[{self.node_id}] Failed to connect to {peer_host}:{peer_port}: {e}")
            return False

    # ========================================================================= #
    # MESSAGING - Send and receive messages
    # ========================================================================= #

    def broadcast(self, message: dict, exclude_peer: str = None):
        """Broadcast a message to all connected peers.

        Args:
            message: Message dict to send
            exclude_peer: Peer ID to exclude from broadcast
        """
        with self.peer_lock:
            for peer_id, peer_socket in list(self.peer_sockets.items()):
                if exclude_peer and peer_id == exclude_peer:
                    continue

                try:
                    framed = self._encode(message)
                    peer_socket.sendall(framed)
                    self.messages_sent += 1
                    self.bytes_sent += len(framed)
                except Exception as e:
                    logger.debug(f"[{self.node_id}] Failed to send to {peer_id}: {e}")

    def send_to_peer(self, peer_id: str, message: dict) -> bool:
        """Send a message to a specific peer.

        Args:
            peer_id: ID of peer to send to
            message: Message dict to send

        Returns:
            True if successful
        """
        with self.peer_lock:
            if peer_id not in self.peer_sockets:
                return False

            try:
                peer_socket = self.peer_sockets[peer_id]
                framed = self._encode(message)
                peer_socket.sendall(framed)
                self.messages_sent += 1
                self.bytes_sent += len(framed)
                return True
            except Exception as e:
                logger.debug(f"[{self.node_id}] Failed to send to {peer_id}: {e}")
                return False

    # ========================================================================= #
    # HANDLERS - Process incoming messages
    # ========================================================================= #

    def handle_ping(self, peer: PeerInfo, message: dict):
        """Handle ping message."""
        pong = {
            'type': 'pong',
            'node_id': self.node_id,
            'timestamp': time.time()
        }
        self.send_to_peer(peer.node_id, pong)

    def handle_pong(self, peer: PeerInfo, message: dict):
        """Handle pong message."""
        peer.last_seen = time.time()

    def handle_peer_list(self, peer: PeerInfo, message: dict):
        """Handle peer list request/response."""
        if message.get('request'):
            # Send our peer list
            response = {
                'type': 'peer_list',
                'peers': [p.to_dict() for p in self.peers.values()]
            }
            self.send_to_peer(peer.node_id, response)
        else:
            # Receive peer list and connect to new peers
            new_peers = message.get('peers', [])
            for peer_data in new_peers:
                peer_info = PeerInfo.from_dict(peer_data)
                if peer_info.node_id != self.node_id:  # Don't add ourselves
                    if peer_info.node_id not in self.peers:
                        logger.info(f"[{self.node_id}] Discovered new peer: {peer_info.node_id}")
                        self.connect_to_peer(peer_info.host, peer_info.port, peer_info.node_id)

    def handle_get_blocks(self, peer: PeerInfo, message: dict):
        """Handle block range request."""
        if not self.blockchain:
            return

        start_height = message.get('start_height', 0)
        end_height = message.get('end_height', self.blockchain.height)

        blocks = []
        for height in range(start_height, min(end_height + 1, self.blockchain.height + 1)):
            block_hash = self.blockchain.get_block_hash_by_height(height)
            if block_hash:
                block = self.blockchain.get_block(block_hash)
                if block:
                    blocks.append(block.to_dict())

        response = {
            'type': 'blocks',
            'blocks': blocks
        }
        self.send_to_peer(peer.node_id, response)

    def handle_get_block(self, peer: PeerInfo, message: dict):
        """Handle single block request."""
        if not self.blockchain:
            return

        block_hash = message.get('hash')
        block = self.blockchain.get_block(block_hash)

        response = {
            'type': 'block',
            'block': block.to_dict() if block else None
        }
        self.send_to_peer(peer.node_id, response)

    def handle_new_block(self, peer: PeerInfo, message: dict):
        """Handle new block announcement."""
        block_data = message.get('block')
        if block_data:
            self.pending_blocks.append(block_data)

    def handle_new_transaction(self, peer: PeerInfo, message: dict):
        """Handle new transaction announcement."""
        tx_data = message.get('transaction')
        if tx_data:
            tx_json = json.dumps(tx_data, sort_keys=True)
            tx_hash = hashlib.sha256(tx_json.encode()).hexdigest()
            # Store the serialized form: a (str, str) tuple is hashable, so it
            # can live in the set (a raw dict would raise TypeError) and gives
            # natural de-duplication of identical transactions.
            self.pending_transactions.add((tx_hash, tx_json))

    def handle_sync_request(self, peer: PeerInfo, message: dict):
        """Handle sync request."""
        if not self.blockchain:
            return

        response = {
            'type': 'sync_info',
            'height': self.blockchain.height,
            'tip': self.blockchain.tip,
            'node_id': self.node_id
        }
        self.send_to_peer(peer.node_id, response)

    # ========================================================================= #
    # PEER MANAGEMENT
    # ========================================================================= #

    def get_connected_peers(self) -> list[PeerInfo]:
        """Get list of currently connected peers."""
        with self.peer_lock:
            return [p for p in self.peers.values() if p.is_alive()]

    def get_peer_count(self) -> int:
        """Get number of connected peers."""
        return len(self.get_connected_peers())

    def disconnect_peer(self, peer_id: str):
        """Disconnect from a peer."""
        with self.peer_lock:
            if peer_id in self.peer_sockets:
                try:
                    self.peer_sockets[peer_id].close()
                except Exception:
                    pass
                del self.peer_sockets[peer_id]
            if peer_id in self.peers:
                del self.peers[peer_id]
        logger.info(f"[{self.node_id}] Disconnected from {peer_id}")

    def cleanup_dead_peers(self):
        """Remove peers that haven't responded in a while."""
        with self.peer_lock:
            dead_peers = [p.node_id for p in self.peers.values() if not p.is_alive()]
            for peer_id in dead_peers:
                self.disconnect_peer(peer_id)

        if dead_peers:
            logger.info(f"[{self.node_id}] Removed {len(dead_peers)} dead peers")

    def send_ping_to_all(self):
        """Send ping to all peers (keep-alive)."""
        ping = {'type': 'ping', 'node_id': self.node_id, 'timestamp': time.time()}
        self.broadcast(ping)

    # ========================================================================= #
    # STATISTICS
    # ========================================================================= #

    def get_stats(self) -> dict:
        """Get network statistics."""
        return {
            'node_id': self.node_id,
            'connected_peers': self.get_peer_count(),
            'messages_sent': self.messages_sent,
            'messages_received': self.messages_received,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'pending_blocks': len(self.pending_blocks),
            'pending_transactions': len(self.pending_transactions),
            'uptime_seconds': time.time()
        }


class BootstrapServer:
    """Bootstrap server for peer discovery (centralized DHT alternative)."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8999):
        self.host = host
        self.port = port
        self.known_peers: dict[str, PeerInfo] = {}
        self.peer_lock = threading.RLock()
        self.running = False
        self.server_socket = None

    def start(self):
        """Start bootstrap server."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)

            logger.info(f"[Bootstrap] Server listening on {self.host}:{self.port}")
            self.running = True

            threading.Thread(daemon=True, target=self._accept_connections).start()

        except Exception as e:
            logger.error(f"[Bootstrap] Failed to start: {e}")
            raise

    def stop(self):
        """Stop bootstrap server."""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception:
                pass
        logger.info("[Bootstrap] Server stopped")

    def _accept_connections(self):
        """Accept connections from peers."""
        while self.running:
            try:
                client_socket, client_addr = self.server_socket.accept()
                client_socket.settimeout(10)

                threading.Thread(
                    daemon=True,
                    target=self._handle_client,
                    args=(client_socket, client_addr)
                ).start()

            except Exception as e:
                if self.running:
                    logger.debug(f"[Bootstrap] Accept error: {e}")

    def _handle_client(self, client_socket: socket.socket, client_addr: tuple):
        """Handle client connection."""
        try:
            # Receive peer info
            data = client_socket.recv(4096)
            if not data:
                return

            message = json.loads(data.decode())
            msg_type = message.get('type')

            if msg_type == 'register':
                # Register new peer
                peer_info = PeerInfo(
                    node_id=message.get('node_id'),
                    host=message.get('host'),
                    port=message.get('port'),
                    version=message.get('version', '1.0.0')
                )

                with self.peer_lock:
                    self.known_peers[peer_info.node_id] = peer_info

                logger.info(f"[Bootstrap] Registered peer: {peer_info.node_id}")

                # Send back known peers
                response = {
                    'type': 'peer_list',
                    'peers': [p.to_dict() for p in list(self.known_peers.values())[:20]]
                }
                client_socket.sendall(json.dumps(response).encode())

            elif msg_type == 'discover':
                # Send known peers
                with self.peer_lock:
                    peers = list(self.known_peers.values())[:20]

                response = {
                    'type': 'peer_list',
                    'peers': [p.to_dict() for p in peers]
                }
                client_socket.sendall(json.dumps(response).encode())

        except Exception as e:
            logger.debug(f"[Bootstrap] Client error: {e}")
        finally:
            try:
                client_socket.close()
            except Exception:
                pass


if __name__ == "__main__":
    # Test bootstrap server
    bootstrap = BootstrapServer()
    bootstrap.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bootstrap.stop()

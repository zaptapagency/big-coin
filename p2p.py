"""MyCoin — real TCP peer-to-peer transport (whitepaper section 5, for real).

The in-process `network.Network` gossips by calling peer methods directly. This
module replaces that with an actual asyncio TCP layer so `Node`s can run as
separate processes talking over sockets, using a Bitcoin-flavoured message
protocol: a `version`/`verack` handshake, then `inv`/`getdata`/`block`/`tx`
inventory negotiation.

Wire format
-----------
Every message is a length-prefixed JSON frame:

    +----------------------+-----------------------------+
    | 4-byte BE uint length | length bytes of UTF-8 JSON |
    +----------------------+-----------------------------+

The JSON is an envelope ``{"type": <str>, "payload": <obj>}``. Frames larger
than ``MAX_FRAME_BYTES`` are rejected to bound memory (basic DoS protection).

Design notes / trade-offs vs Bitcoin:
  * JSON envelope instead of a compact binary protocol — readable and easy to
    debug, matching the rest of MyCoin.
  * No peer discovery, addr gossip, or ping/pong keepalive; peers are wired up
    explicitly via `connect`.
  * `Node` instances used here should be constructed with ``network=None`` so
    the P2P layer is solely responsible for relay (avoiding double-broadcast).
"""

from __future__ import annotations

import asyncio
import json
import struct
from typing import Optional

from block import Block
from node import Node
from transaction import Transaction

# --------------------------------------------------------------------------- #
# Wire protocol
# --------------------------------------------------------------------------- #
HEADER_LEN = 4  # 4-byte big-endian unsigned length prefix
MAX_FRAME_BYTES = 8 * 1024 * 1024  # 8 MiB ceiling on a single frame

# Message types.
MSG_VERSION = "version"
MSG_VERACK = "verack"
MSG_INV = "inv"
MSG_GETDATA = "getdata"
MSG_BLOCK = "block"
MSG_TX = "tx"


class FrameError(Exception):
    """Raised when a peer sends a malformed or oversized frame."""


async def read_message(reader: asyncio.StreamReader) -> Optional[dict]:
    """Read one length-prefixed JSON frame.

    Returns the decoded envelope dict, or ``None`` on a clean EOF (the peer
    closed the connection at a frame boundary). Raises `FrameError` if the
    frame is oversized or not valid UTF-8 JSON.
    """
    try:
        header = await reader.readexactly(HEADER_LEN)
    except asyncio.IncompleteReadError:
        return None  # clean EOF: nothing (or a partial nothing) left to read

    (length,) = struct.unpack(">I", header)
    if length > MAX_FRAME_BYTES:
        raise FrameError(f"frame too large: {length} > {MAX_FRAME_BYTES}")

    try:
        body = await reader.readexactly(length)
    except asyncio.IncompleteReadError as exc:
        # Header promised bytes that never fully arrived: treat as malformed.
        raise FrameError("truncated frame body") from exc

    try:
        msg = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FrameError("frame is not valid UTF-8 JSON") from exc

    if not isinstance(msg, dict) or "type" not in msg:
        raise FrameError("frame is not a message envelope")
    return msg


async def write_message(writer: asyncio.StreamWriter, msg: dict) -> None:
    """Encode ``msg`` as a length-prefixed JSON frame and flush it."""
    body = json.dumps(msg, separators=(",", ":")).encode("utf-8")
    if len(body) > MAX_FRAME_BYTES:
        raise FrameError(f"outgoing frame too large: {len(body)}")
    writer.write(struct.pack(">I", len(body)) + body)
    await writer.drain()


def _envelope(msg_type: str, payload) -> dict:
    return {"type": msg_type, "payload": payload}


# --------------------------------------------------------------------------- #
# Peer connection
# --------------------------------------------------------------------------- #
class Peer:
    """A single connected peer: its stream pair and remote handshake info."""

    def __init__(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.node_id: Optional[str] = None
        self.height: int = 0
        self.handshaked = False

    async def send(self, msg: dict) -> None:
        await write_message(self.writer, msg)

    async def close(self) -> None:
        try:
            self.writer.close()
            await self.writer.wait_closed()
        except (OSError, ConnectionError):
            pass


# --------------------------------------------------------------------------- #
# P2P node
# --------------------------------------------------------------------------- #
class P2PNode:
    """Wraps a `Node` with an asyncio TCP server and outbound connections."""

    def __init__(self, node: Node, host: str = "127.0.0.1", port: int = 0) -> None:
        self.node = node
        self.host = host
        self.port = port
        self._server: Optional[asyncio.AbstractServer] = None
        self.peers: set[Peer] = set()
        # Tasks driving each peer's read loop, so stop() can cancel them.
        self._peer_tasks: set[asyncio.Task] = set()

    # ----- lifecycle ------------------------------------------------------ #
    async def start(self) -> None:
        """Start listening. If port was 0, capture the OS-assigned port."""
        self._server = await asyncio.start_server(
            self._on_inbound, self.host, self.port
        )
        # Reflect the actual bound port back onto self.port for port=0 callers.
        sock = self._server.sockets[0]
        self.port = sock.getsockname()[1]

    async def stop(self) -> None:
        """Close the server and every peer connection; cancel read loops.

        Peer writers are closed *before* awaiting ``Server.wait_closed()``:
        on Python 3.12+ the server waits for its inbound-connection callbacks
        to finish, so those connections must be torn down first or the wait
        would hang forever.
        """
        # Stop accepting new connections (but do not yet wait for callbacks).
        if self._server is not None:
            self._server.close()

        # Close every peer writer; this makes any pending readexactly in a read
        # loop raise, so both outbound loops and inbound server callbacks exit.
        peers = list(self.peers)
        self.peers.clear()
        for peer in peers:
            try:
                peer.writer.close()
            except (OSError, ConnectionError):
                pass

        # Cancel outstanding (outbound) peer read loops and await them.
        tasks = list(self._peer_tasks)
        self._peer_tasks.clear()
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except BaseException:
                pass

        # Wait for the writers to fully close.
        for peer in peers:
            try:
                await peer.writer.wait_closed()
            except (OSError, ConnectionError):
                pass

        # Now that all connections are gone, the server can finish closing.
        if self._server is not None:
            try:
                await self._server.wait_closed()
            except (OSError, ConnectionError):
                pass
            self._server = None

    # ----- connection handling -------------------------------------------- #
    async def _on_inbound(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Accept an inbound peer: complete the handshake, then serve it."""
        peer = Peer(reader, writer)
        self.peers.add(peer)
        try:
            await self._handshake(peer, initiator=False)
            # Announce our chain so the freshly-connected peer can pull blocks
            # it is missing from us (both sides advertise after the handshake).
            await self._send_inv(peer)
            await self._read_loop(peer)
        except (FrameError, ConnectionError, OSError, asyncio.IncompleteReadError):
            pass
        finally:
            await self._drop_peer(peer)

    async def connect(self, host: str, port: int) -> Peer:
        """Dial a peer, handshake, then send an `inv` of our active chain.

        The `inv` lets the remote pull anything it is missing from us during
        the initial sync.
        """
        reader, writer = await asyncio.open_connection(host, port)
        peer = Peer(reader, writer)
        self.peers.add(peer)
        await self._handshake(peer, initiator=True)

        # Kick off the read loop for this outbound peer.
        task = asyncio.ensure_future(self._serve_peer(peer))
        self._peer_tasks.add(task)
        task.add_done_callback(self._peer_tasks.discard)

        # Announce what we have so the peer can request missing blocks.
        await self._send_inv(peer)
        return peer

    async def _serve_peer(self, peer: Peer) -> None:
        try:
            await self._read_loop(peer)
        except (FrameError, ConnectionError, OSError, asyncio.IncompleteReadError):
            pass
        finally:
            await self._drop_peer(peer)

    async def _handshake(self, peer: Peer, initiator: bool) -> None:
        """Exchange version/verack. Both sides send version and reply verack."""
        await peer.send(
            _envelope(
                MSG_VERSION,
                {"node_id": self.node.node_id, "height": self.node.chain.height},
            )
        )
        # Read messages until we've both received the peer's version and its
        # verack (order-independent to tolerate interleaving on both ends).
        got_version = False
        got_verack = False
        while not (got_version and got_verack):
            msg = await read_message(peer.reader)
            if msg is None:
                raise ConnectionError("peer closed during handshake")
            mtype = msg.get("type")
            payload = msg.get("payload") or {}
            if mtype == MSG_VERSION:
                peer.node_id = payload.get("node_id")
                peer.height = payload.get("height", 0)
                got_version = True
                await peer.send(_envelope(MSG_VERACK, {}))
            elif mtype == MSG_VERACK:
                got_verack = True
            # Ignore any other message type until the handshake completes.
        peer.handshaked = True

    async def _read_loop(self, peer: Peer) -> None:
        """Serve post-handshake messages from a single peer until it closes."""
        while True:
            msg = await read_message(peer.reader)
            if msg is None:
                break  # clean EOF
            await self._handle_message(peer, msg)

    async def _drop_peer(self, peer: Peer) -> None:
        self.peers.discard(peer)
        await peer.close()

    # ----- message handling ----------------------------------------------- #
    async def _handle_message(self, peer: Peer, msg: dict) -> None:
        mtype = msg.get("type")
        payload = msg.get("payload")

        if mtype == MSG_INV:
            await self._handle_inv(peer, payload)
        elif mtype == MSG_GETDATA:
            await self._handle_getdata(peer, payload)
        elif mtype == MSG_BLOCK:
            await self._handle_block(peer, payload)
        elif mtype == MSG_TX:
            await self._handle_tx(peer, payload)
        elif mtype in (MSG_VERSION, MSG_VERACK):
            # Stray handshake messages after the handshake: ignore.
            pass
        # Unknown types are silently ignored (forward compatibility).

    async def _handle_inv(self, peer: Peer, payload) -> None:
        """Peer announced block hashes; request the ones we don't have."""
        if not isinstance(payload, list):
            return
        unknown = [h for h in payload if isinstance(h, str) and not self.node.has_block(h)]
        if unknown:
            await peer.send(_envelope(MSG_GETDATA, unknown))

    async def _handle_getdata(self, peer: Peer, payload) -> None:
        """Peer requested full blocks by hash; send each one we have."""
        if not isinstance(payload, list):
            return
        for h in payload:
            block = self.node.get_block(h) if isinstance(h, str) else None
            if block is not None:
                await peer.send(_envelope(MSG_BLOCK, block.to_dict()))

    async def _handle_block(self, peer: Peer, payload) -> None:
        """Receive a full block, add it, and relay inv on new acceptance."""
        try:
            block = Block.from_dict(payload)
        except (KeyError, TypeError, ValueError):
            return
        status = self.node.receive_block(block)
        if status in ("extended", "reorg"):
            # New tip: tell our other peers so it propagates down the line.
            await self._relay_inv([block.hash], exclude=peer)

    async def _handle_tx(self, peer: Peer, payload) -> None:
        try:
            tx = Transaction.from_dict(payload)
        except (KeyError, TypeError, ValueError):
            return
        self.node.receive_transaction(tx)

    # ----- sending helpers ------------------------------------------------ #
    async def _send_inv(self, peer: Peer) -> None:
        """Send our full active chain as an inv to a single peer."""
        hashes = self.node.chain.active_chain()
        await peer.send(_envelope(MSG_INV, hashes))

    async def _relay_inv(self, hashes: list[str], exclude: Optional[Peer] = None) -> None:
        for peer in list(self.peers):
            if peer is exclude:
                continue
            try:
                await peer.send(_envelope(MSG_INV, hashes))
            except (ConnectionError, OSError, FrameError):
                await self._drop_peer(peer)

    async def broadcast_block(self, block: Block) -> None:
        """Announce a block to all connected peers via inv."""
        await self._relay_inv([block.hash])

    async def broadcast_tx(self, tx: Transaction) -> None:
        """Send a transaction to all connected peers."""
        msg = _envelope(MSG_TX, tx.to_dict())
        for peer in list(self.peers):
            try:
                await peer.send(msg)
            except (ConnectionError, OSError, FrameError):
                await self._drop_peer(peer)

"""Tests for the real TCP peer-to-peer transport (p2p.py)."""

import asyncio
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from node import Node  # noqa: E402
from transaction import generate_keypair, pubkey_hash  # noqa: E402
from p2p import (  # noqa: E402
    HEADER_LEN,
    MAX_FRAME_BYTES,
    P2PNode,
    read_message,
    write_message,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _pkh():
    _, pub = generate_keypair()
    return pubkey_hash(pub)


def _make_node(node_id):
    # coinbase_maturity=0 so freshly-mined coinbases are immediately mature;
    # network=None so the P2P layer is the sole relay mechanism.
    return Node(node_id, network=None, coinbase_maturity=0)


async def _wait_for_tip(node, expected_tip, timeout=5):
    """Poll node.chain.tip until it matches expected_tip or timeout fires."""

    async def _poll():
        while node.chain.tip != expected_tip:
            await asyncio.sleep(0.01)

    await asyncio.wait_for(_poll(), timeout=timeout)


# --------------------------------------------------------------------------- #
# Framing
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_framing_round_trip():
    """write_message then read_message returns the same dict."""
    # An in-process echo server bounces frames straight back.
    async def echo(reader, writer):
        try:
            while True:
                msg = await read_message(reader)
                if msg is None:
                    break
                await write_message(writer, msg)
        except Exception:
            pass
        finally:
            writer.close()

    server = await asyncio.start_server(echo, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", port)
        try:
            original = {"type": "version", "payload": {"node_id": "A", "height": 7}}
            await write_message(writer, original)
            echoed = await asyncio.wait_for(read_message(reader), timeout=5)
            assert echoed == original
        finally:
            writer.close()
            await writer.wait_closed()
    finally:
        server.close()
        await server.wait_closed()


# --------------------------------------------------------------------------- #
# Two nodes: initial inv/getdata sync
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_initial_sync_on_connect():
    """A mines a block; B connects and reaches A's tip via inv/getdata."""
    a = P2PNode(_make_node("A"))
    b = P2PNode(_make_node("B"))
    try:
        await a.start()
        await b.start()

        block = a.node.mine_block(_pkh())
        assert block is not None
        assert a.node.chain.tip == block.hash

        await b.connect(a.host, a.port)
        await _wait_for_tip(b.node, a.node.chain.tip)
        assert b.node.chain.tip == a.node.chain.tip
    finally:
        await a.stop()
        await b.stop()


# --------------------------------------------------------------------------- #
# Live broadcast
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_live_broadcast():
    """With A and B connected, A mines and broadcasts; B converges."""
    a = P2PNode(_make_node("A"))
    b = P2PNode(_make_node("B"))
    try:
        await a.start()
        await b.start()
        await b.connect(a.host, a.port)

        block = a.node.mine_block(_pkh())
        assert block is not None
        await a.broadcast_block(block)

        await _wait_for_tip(b.node, a.node.chain.tip)
        assert b.node.chain.tip == block.hash
    finally:
        await a.stop()
        await b.stop()


# --------------------------------------------------------------------------- #
# Three nodes in a line: relay via inv
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_three_node_relay():
    """A<-B<-C connections: a block mined at A propagates to C via relay."""
    a = P2PNode(_make_node("A"))
    b = P2PNode(_make_node("B"))
    c = P2PNode(_make_node("C"))
    try:
        await a.start()
        await b.start()
        await c.start()

        # B dials A, C dials B, forming a line A <- B <- C.
        await b.connect(a.host, a.port)
        await c.connect(b.host, b.port)

        block = a.node.mine_block(_pkh())
        assert block is not None
        await a.broadcast_block(block)

        # B learns it from A, then relays inv to C, which pulls it.
        await _wait_for_tip(c.node, block.hash)
        assert c.node.chain.tip == block.hash
    finally:
        await a.stop()
        await b.stop()
        await c.stop()


# --------------------------------------------------------------------------- #
# Robustness: a bad peer must not take down the server
# --------------------------------------------------------------------------- #
@pytest.mark.asyncio
async def test_malformed_frame_isolated():
    """An oversized frame disconnects only that peer; server keeps serving."""
    a = P2PNode(_make_node("A"))
    good = P2PNode(_make_node("good"))
    try:
        await a.start()
        block = a.node.mine_block(_pkh())
        assert block is not None

        # Misbehaving raw client: send a header claiming a frame far larger
        # than the ceiling, which the server must reject and disconnect.
        reader, writer = await asyncio.open_connection(a.host, a.port)
        try:
            writer.write(struct.pack(">I", MAX_FRAME_BYTES + 1))
            writer.write(b"\x00" * 16)  # a little garbage body
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()

        # Give the server a moment to process and drop the bad peer.
        await asyncio.sleep(0.05)

        # A well-behaved node can still connect and sync afterward.
        await good.connect(a.host, a.port)
        await _wait_for_tip(good.node, a.node.chain.tip)
        assert good.node.chain.tip == a.node.chain.tip
    finally:
        await a.stop()
        await good.stop()

"""MyCoin Shared State Server — IPC for synchronized blockchain state.

Both web_app.py and gui.py connect to this server to share a single Node instance.
This ensures the same blockchain, addresses, and mining state across all UIs.

Run this FIRST before starting web_app.py or gui.py:
  python shared_state.py
"""

from __future__ import annotations

import json
import socket
import threading
import time
from typing import Optional

from node import Node
from transaction import generate_keypair, pubkey_hash
from wallet import address_from_pubkey_hash

# Global shared state
shared_node: Optional[Node] = None
generated_addresses: dict = {}  # pubkey_hash -> {"address": str, "pubkey": str}
mining_state = {
    "is_mining": False,
    "blocks_to_mine": 0,
    "blocks_mined": 0,
    "current_height": 0,
    "mining_address": None,
}
state_lock = threading.Lock()


def get_node() -> Node:
    """Get or create the global shared node."""
    global shared_node
    if shared_node is None:
        shared_node = Node("shared", coinbase_maturity=0)
    return shared_node


def handle_client(client_socket: socket.socket, addr: tuple) -> None:
    """Handle a client connection with JSON RPC-like protocol."""
    try:
        while True:
            # Read message (with timeout to prevent hanging)
            client_socket.settimeout(30.0)  # 30-second timeout
            try:
                data = client_socket.recv(4096)
            except TimeoutError:
                break

            if not data:
                break

            try:
                request = json.loads(data.decode())
                # Process request (mining happens in separate thread, doesn't block here)
                response = process_request(request)
                client_socket.sendall(json.dumps(response).encode())
            except json.JSONDecodeError:
                client_socket.sendall(
                    json.dumps({"error": "Invalid JSON"}).encode()
                )
            except Exception as e:
                client_socket.sendall(json.dumps({"error": str(e)}).encode())
    finally:
        try:
            client_socket.close()
        except Exception:
            pass


def process_request(request: dict) -> dict:
    """Process a JSON request and return response."""
    global shared_node, generated_addresses, mining_state

    cmd = request.get("cmd")

    if cmd == "new_key":
        sk, pubkey_hex = generate_keypair()
        pkh = pubkey_hash(pubkey_hex)
        addr = address_from_pubkey_hash(pkh)
        with state_lock:
            generated_addresses[pkh] = {"address": addr, "pubkey": pubkey_hex}
        return {"address": addr, "pubkey_hash": pkh}

    elif cmd == "get_balance":
        node = get_node()
        with state_lock:
            total = node.chain.utxo.total_value()
        return {"balance_cents": total, "balance_coins": total / 100_000_000}

    elif cmd == "blockchain_info":
        node = get_node()
        with state_lock:
            info = {
                "height": node.chain.height,
                "tip_hash": node.chain.tip,
                "total_money_cents": node.chain.utxo.total_value(),
                "total_money_coins": node.chain.utxo.total_value() / 100_000_000,
                "tx_count": sum(
                    len(block.transactions) for block in node.chain.blocks.values()
                ),
            }
        return info

    elif cmd == "start_mining":
        blocks = request.get("blocks", 1)
        address = request.get("address", "")

        if not address:
            return {"error": "No address provided"}

        # Find the pubkey_hash for this address
        node = get_node()
        pkh = None
        for stored_pkh, stored_data in generated_addresses.items():
            if stored_data["address"] == address:
                pkh = stored_pkh
                break

        if not pkh:
            return {"error": f"Address '{address}' not found. Generate a new address first."}

        with state_lock:
            if mining_state["is_mining"]:
                return {"error": "Already mining"}
            mining_state["is_mining"] = True
            mining_state["blocks_to_mine"] = blocks
            mining_state["blocks_mined"] = 0
            mining_state["mining_address"] = address

        # Mine in background thread
        def mine_worker():
            try:
                for i in range(blocks):
                    block = node.mine_block(pkh)
                    with state_lock:
                        mining_state["blocks_mined"] = i + 1
                        mining_state["current_height"] = node.chain.height
                    if not block:
                        break
            finally:
                with state_lock:
                    mining_state["is_mining"] = False

        threading.Thread(daemon=True, target=mine_worker).start()
        return {"status": "mining started"}

    elif cmd == "mining_status":
        with state_lock:
            return {
                "is_mining": mining_state["is_mining"],
                "blocks_mined": mining_state["blocks_mined"],
                "blocks_to_mine": mining_state["blocks_to_mine"],
                "current_height": mining_state["current_height"],
            }

    elif cmd == "stop_mining":
        with state_lock:
            mining_state["is_mining"] = False
        return {"status": "mining stopped"}

    elif cmd == "get_addresses":
        with state_lock:
            addrs = [
                {"address": v["address"], "pubkey_hash": k}
                for k, v in generated_addresses.items()
            ]
        return {"addresses": addrs}

    else:
        return {"error": f"Unknown command: {cmd}"}


def run_server(host: str = "127.0.0.1", port: int = 9999) -> None:
    """Run the shared state server."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(5)

    print(f"[Shared State Server] Listening on {host}:{port}")
    print("[Shared State Server] Web & GUI apps should connect here")

    try:
        while True:
            client_socket, addr = server_socket.accept()
            print(f"[Shared State Server] Client connected from {addr}")
            threading.Thread(
                daemon=True, target=handle_client, args=(client_socket, addr)
            ).start()
    except KeyboardInterrupt:
        print("\n[Shared State Server] Shutting down...")
    finally:
        server_socket.close()


if __name__ == "__main__":
    # Initialize node on startup
    get_node()
    print("[Shared State Server] Node initialized (genesis block created)")
    run_server()

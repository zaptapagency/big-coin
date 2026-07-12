"""Client for shared state server — used by web_app.py and gui.py."""

from __future__ import annotations

import json
import socket
from typing import Any, Optional


class SharedStateClient:
    """Connect to shared_state.py server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9999):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None

    def connect(self) -> None:
        """Connect to the shared state server."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host, self.port))

    def send_request(self, request: dict) -> dict:
        """Send a JSON request and get response."""
        # Create a fresh socket for each request to avoid concurrency issues
        sock = None
        max_retries = 2
        for attempt in range(max_retries):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((self.host, self.port))

                # Send request
                request_data = json.dumps(request).encode()
                sock.sendall(request_data)

                # Receive response with buffering
                response_data = b''
                while True:
                    try:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        response_data += chunk
                        # Try to parse - if complete JSON, break
                        json.loads(response_data.decode())
                        break
                    except json.JSONDecodeError:
                        # Incomplete JSON, continue reading
                        continue

                if not response_data:
                    raise Exception("Empty response from server")

                return json.loads(response_data.decode())

            except (ConnectionRefusedError, ConnectionResetError, BrokenPipeError) as e:
                if attempt < max_retries - 1:
                    continue  # Retry
                raise Exception(f"Server connection error: {e}")
            except TimeoutError:
                if attempt < max_retries - 1:
                    continue
                raise Exception("Connection timeout")
            except json.JSONDecodeError as e:
                raise Exception(f"Invalid JSON response: {e}")
            finally:
                if sock:
                    try:
                        sock.close()
                    except Exception:
                        pass

    def new_key(self) -> dict:
        """Generate new keypair. Returns {"address": str, "pubkey_hash": str}"""
        return self.send_request({"cmd": "new_key"})

    def get_balance(self) -> dict:
        """Get balance. Returns {"balance_coins": float, "balance_cents": int}"""
        return self.send_request({"cmd": "get_balance"})

    def blockchain_info(self) -> dict:
        """Get blockchain info."""
        return self.send_request({"cmd": "blockchain_info"})

    def start_mining(self, blocks: int, address: str) -> dict:
        """Start mining."""
        return self.send_request(
            {"cmd": "start_mining", "blocks": blocks, "address": address}
        )

    def mining_status(self) -> dict:
        """Get mining status."""
        return self.send_request({"cmd": "mining_status"})

    def stop_mining(self) -> dict:
        """Stop mining."""
        return self.send_request({"cmd": "stop_mining"})

    def get_addresses(self) -> dict:
        """Get all generated addresses."""
        return self.send_request({"cmd": "get_addresses"})

"""Connect nodes in P2P network - Peer discovery and connection."""

import requests
import json
import sys
import time


def connect_nodes(node_configs):
    """Connect all nodes to form a network.

    Args:
        node_configs: List of (node_id, rpc_port) tuples
    """
    print("\n" + "=" * 60)
    print("BigCoin P2P Network - Node Connection")
    print("=" * 60 + "\n")

    for node_id, rpc_port in node_configs:
        print(f"Connecting {node_id}...")

        # Connect this node to all other nodes
        for other_id, other_port in node_configs:
            if node_id != other_id:
                other_p2p_port = 9000 + node_configs.index((other_id, other_port)) + 1
                connect_peers(rpc_port, "127.0.0.1", other_p2p_port)
                time.sleep(0.5)

    print("\nNetwork connection complete!")
    print_network_status(node_configs)


def connect_peers(rpc_port, peer_host, peer_p2p_port):
    """Tell a node to connect to another peer. Returns True on success."""
    try:
        response = requests.post(
            f"http://127.0.0.1:{rpc_port}/rpc",
            json={"method": "connect_peer", "params": {"host": peer_host, "port": peer_p2p_port}},
            timeout=5
        )
        if response.status_code != 200:
            return False
        return response.json().get("status") == "connected"
    except Exception:
        return False


def print_network_status(node_configs):
    """Print status of all nodes."""
    print("\n" + "=" * 60)
    print("Network Status")
    print("=" * 60 + "\n")

    for node_id, rpc_port in node_configs:
        try:
            # Get blockchain info
            response = requests.get(f"http://127.0.0.1:{rpc_port}/api/blockchain/info", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"{node_id}:")
                print(f"  RPC Port: {rpc_port}")
                print(f"  P2P Port: {9000 + node_configs.index((node_id, rpc_port)) + 1}")
                print(f"  Height: {data.get('height', 'N/A')}")
                print(f"  Connected Peers: {data.get('connected_peers', 0)}")
                print()
        except Exception as e:
            print(f"{node_id}: ERROR - {e}\n")


if __name__ == "__main__":
    # Node configuration: (node_id, rpc_port)
    nodes = [
        ("alice", 8001),
        ("bob", 8002),
        ("charlie", 8003),
    ]

    print("Waiting for nodes to start...")
    time.sleep(5)

    connect_nodes(nodes)

    # Print status
    print("\nMonitoring network (Ctrl+C to exit)...\n")
    try:
        while True:
            print_network_status(nodes)
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n\nExiting...")

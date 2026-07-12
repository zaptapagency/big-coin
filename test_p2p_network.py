"""Test P2P Network functionality.

This script tests:
- Node startup
- Peer connections
- Block synchronization
- Mining and broadcasting
"""

import requests
import json
import time
import sys
from typing import List, Tuple

# Configuration
NODES = [
    ("alice", 8001),
    ("bob", 8002),
    ("charlie", 8003),
]

BASE_URL = "http://127.0.0.1"


class NetworkTester:
    """Test suite for P2P network."""

    def __init__(self, nodes: list[tuple[str, int]]):
        self.nodes = nodes
        self.test_results = []

    def run_all_tests(self):
        """Run all tests."""
        print("\n" + "=" * 70)
        print("BigCoin P2P Network - Test Suite")
        print("=" * 70 + "\n")

        self.test_node_availability()
        self.test_peer_connectivity()
        self.test_blockchain_sync()
        self.test_mining_broadcast()
        self.test_network_stats()

        self.print_results()

    # ========================================================================= #
    # TEST 1: Node Availability
    # ========================================================================= #

    def test_node_availability(self):
        """Test that all nodes are running."""
        print("TEST 1: Node Availability")
        print("-" * 70)

        for node_id, rpc_port in self.nodes:
            try:
                url = f"{BASE_URL}:{rpc_port}/api/blockchain/info"
                response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✓ {node_id} ({rpc_port}): RUNNING")
                    print(f"    - Height: {data.get('height', 'N/A')}")
                    print(f"    - Peers: {data.get('connected_peers', 0)}")
                    self.test_results.append(("availability", node_id, True))
                else:
                    print(f"  ✗ {node_id} ({rpc_port}): HTTP {response.status_code}")
                    self.test_results.append(("availability", node_id, False))

            except requests.exceptions.ConnectionError:
                print(f"  ✗ {node_id} ({rpc_port}): CONNECTION REFUSED")
                print(
                    f"    → Make sure node is running: "
                    f"python node_rpc_server.py {node_id} ... {rpc_port}"
                )
                self.test_results.append(("availability", node_id, False))
            except Exception as e:
                print(f"  ✗ {node_id} ({rpc_port}): ERROR - {e}")
                self.test_results.append(("availability", node_id, False))

        print()

    # ========================================================================= #
    # TEST 2: Peer Connectivity
    # ========================================================================= #

    def test_peer_connectivity(self):
        """Test that nodes are connected to each other."""
        print("TEST 2: Peer Connectivity")
        print("-" * 70)

        for node_id, rpc_port in self.nodes:
            try:
                url = f"{BASE_URL}:{rpc_port}/api/node/peers"
                response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    peer_count = data.get("peer_count", 0)

                    if peer_count > 0:
                        print(f"  ✓ {node_id}: Connected to {peer_count} peers")
                        for peer in data.get("peers", []):
                            print(
                                f"    - {peer.get('node_id')} "
                                f"({peer.get('host')}:{peer.get('port')})"
                            )
                        self.test_results.append(("connectivity", node_id, True))
                    else:
                        print(f"  ✗ {node_id}: NO CONNECTED PEERS")
                        print("    → Run: python connect_nodes.py")
                        self.test_results.append(("connectivity", node_id, False))

            except Exception as e:
                print(f"  ✗ {node_id}: ERROR - {e}")
                self.test_results.append(("connectivity", node_id, False))

        print()

    # ========================================================================= #
    # TEST 3: Blockchain Synchronization
    # ========================================================================= #

    def test_blockchain_sync(self):
        """Test blockchain synchronization across nodes."""
        print("TEST 3: Blockchain Synchronization")
        print("-" * 70)

        heights = {}
        for node_id, rpc_port in self.nodes:
            try:
                url = f"{BASE_URL}:{rpc_port}/api/blockchain/info"
                response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    data = response.json()
                    height = data.get("height", 0)
                    heights[node_id] = height
                    print(f"  {node_id}: Height {height}")

            except Exception as e:
                print(f"  {node_id}: ERROR - {e}")

        if heights:
            max_height = max(heights.values())
            min_height = min(heights.values())
            diff = max_height - min_height

            if diff == 0:
                print(f"\n  ✓ All nodes synchronized at height {max_height}")
                self.test_results.append(("sync", "all", True))
            elif diff <= 1:
                print(f"\n  ✓ Nodes nearly synchronized (diff: {diff})")
                print("    → Wait 30 seconds for full sync")
                self.test_results.append(("sync", "all", True))
            else:
                print(f"\n  ✗ Nodes OUT OF SYNC (diff: {diff})")
                print("    → Possible causes:")
                print("    - Nodes not connected")
                print("    - Sync in progress")
                self.test_results.append(("sync", "all", False))

        print()

    # ========================================================================= #
    # TEST 4: Mining and Broadcasting
    # ========================================================================= #

    def test_mining_broadcast(self):
        """Test mining and block broadcasting."""
        print("TEST 4: Mining and Broadcasting")
        print("-" * 70)

        try:
            # Get Alice's info
            alice_port = self.nodes[0][1]
            alice_url = f"{BASE_URL}:{alice_port}"

            # Generate address
            print("  Generating address on Alice...")
            addr_response = requests.get(f"{alice_url}/api/wallet/new", timeout=5)
            if addr_response.status_code != 200:
                print("  ✗ Failed to generate address")
                self.test_results.append(("mining", "broadcast", False))
                return

            address = addr_response.json().get("address")
            print(f"  ✓ Generated address: {address[:20]}...")

            # Get initial height
            info_response = requests.get(f"{alice_url}/api/blockchain/info", timeout=5)
            initial_height = info_response.json().get("height", 0)
            print(f"  Initial height: {initial_height}")

            # Start mining
            print("  Starting mining (1 block)...")
            mining_response = requests.post(
                f"{alice_url}/api/mining/start",
                json={"address": address},
                timeout=5
            )

            if mining_response.status_code != 200:
                print("  ✗ Mining failed to start")
                self.test_results.append(("mining", "broadcast", False))
                return

            # Wait for block
            print("  Waiting for block (max 30 seconds)...")
            for i in range(30):
                time.sleep(1)

                # Check height
                check_response = requests.get(f"{alice_url}/api/blockchain/info", timeout=5)
                current_height = check_response.json().get("height", 0)

                if current_height > initial_height:
                    print(f"  ✓ Block mined! Height increased: {initial_height} → {current_height}")

                    # Check peers also increased
                    time.sleep(2)  # Wait for broadcast
                    for other_id, other_port in self.nodes[1:]:
                        other_response = requests.get(
                            f"{BASE_URL}:{other_port}/api/blockchain/info", timeout=5
                        )
                        other_height = other_response.json().get("height", 0)
                        print(f"  ✓ {other_id} received block: Height {other_height}")

                    self.test_results.append(("mining", "broadcast", True))
                    return

                if i % 5 == 0:
                    print(f"    ... {30-i} seconds remaining")

            print("  ✗ Block not mined after 30 seconds")
            self.test_results.append(("mining", "broadcast", False))

        except Exception as e:
            print(f"  ✗ Mining test error: {e}")
            self.test_results.append(("mining", "broadcast", False))

        print()

    # ========================================================================= #
    # TEST 5: Network Statistics
    # ========================================================================= #

    def test_network_stats(self):
        """Test network statistics."""
        print("TEST 5: Network Statistics")
        print("-" * 70)

        total_peers = 0
        for node_id, rpc_port in self.nodes:
            try:
                url = f"{BASE_URL}:{rpc_port}/api/node/stats"
                response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    stats = response.json()
                    print(f"  {node_id}:")
                    print(f"    - Messages Sent: {stats.get('messages_sent', 0)}")
                    print(f"    - Messages Received: {stats.get('messages_received', 0)}")
                    print(f"    - Bytes Sent: {stats.get('bytes_sent', 0)} B")
                    print(f"    - Bytes Received: {stats.get('bytes_received', 0)} B")
                    print(f"    - Pending Blocks: {stats.get('pending_blocks', 0)}")
                    print(f"    - Pending Transactions: {stats.get('pending_transactions', 0)}")

                    total_peers += stats.get('connected_peers', 0)

            except Exception as e:
                print(f"  {node_id}: ERROR - {e}")

        print(f"\n  Total peer connections: {total_peers}")
        print()

    # ========================================================================= #
    # RESULTS
    # ========================================================================= #

    def print_results(self):
        """Print test results summary."""
        print("=" * 70)
        print("Test Results Summary")
        print("=" * 70 + "\n")

        passed = sum(1 for _, _, result in self.test_results if result)
        total = len(self.test_results)

        print(f"Tests Passed: {passed}/{total}\n")

        # Group by test type
        by_type = {}
        for test_type, name, result in self.test_results:
            if test_type not in by_type:
                by_type[test_type] = []
            by_type[test_type].append((name, result))

        for test_type in sorted(by_type.keys()):
            results = by_type[test_type]
            type_passed = sum(1 for _, r in results if r)
            type_total = len(results)
            status = "✓ PASS" if type_passed == type_total else "✗ FAIL"

            print(f"{test_type.upper()}: {status} ({type_passed}/{type_total})")

        print("\n" + "=" * 70)

        if passed == total:
            print("✓ All tests passed! Network is working correctly.")
            print("\nNext steps:")
            print("  1. Open browser: http://localhost:8001")
            print("  2. Generate addresses and mine blocks")
            print("  3. Check peer blockchains - they should synchronize!")
        else:
            print("✗ Some tests failed. Check above for details.")
            print("\nCommon issues:")
            print("  - Nodes not running: Run START_NODE_NETWORK.bat")
            print("  - Nodes not connected: Run python connect_nodes.py")
            print("  - Mining slow: Mining takes time, wait 30+ seconds")

        print("=" * 70 + "\n")


def main():
    """Run test suite."""
    tester = NetworkTester(NODES)

    try:
        tester.run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")


if __name__ == "__main__":
    main()

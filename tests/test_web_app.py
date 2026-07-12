"""MyCoin Web App Tests — Flask application test suite.

Tests for the Flask web dashboard including:
  - Wallet API endpoints (new address generation, balance checking)
  - Blockchain info endpoints (height, tip hash, transaction count)
  - Mining endpoints (start, stop, status)
  - Transaction listing
  - Error handling
"""

import pytest
import json
from web_app import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
    # Reset global state between tests
    app.mining_state = {
        "is_mining": False,
        "blocks_to_mine": 0,
        "blocks_mined": 0,
        "current_block_height": 0,
        "mining_address": None,
        "mining_thread": None,
    }
    app.node = None
    app.generated_addresses = {}
    with app.test_client() as client:
        yield client


# ============================================================================= #
# Page Rendering Tests
# ============================================================================= #


class TestPageRendering:
    """Test that HTML pages render correctly."""

    def test_index_page(self, client):
        """Test GET / returns dashboard page."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"MyCoin" in response.data
        assert b"Dashboard" in response.data

    def test_wallet_page(self, client):
        """Test GET /wallet returns wallet page."""
        response = client.get("/wallet")
        assert response.status_code == 200
        assert b"Wallet" in response.data
        assert b"Generate New Address" in response.data

    def test_mining_page(self, client):
        """Test GET /mining returns mining page."""
        response = client.get("/mining")
        assert response.status_code == 200
        assert b"Mining" in response.data
        assert b"Number of Blocks to Mine" in response.data


# ============================================================================= #
# Wallet API Tests
# ============================================================================= #


class TestWalletAPI:
    """Test wallet-related API endpoints."""

    def test_wallet_new_success(self, client):
        """Test GET /api/wallet/new generates a valid address."""
        response = client.get("/api/wallet/new")
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "success"
        assert "address" in data
        assert "pubkey_hash" in data
        assert "pubkey" in data

        # Address should be a non-empty string
        address = data["address"]
        assert isinstance(address, str)
        assert len(address) > 10
        # Base58Check addresses start with specific characters for version 0x00
        assert address[0] in "13"  # Typical starting chars for version 0

    def test_wallet_new_multiple_calls(self, client):
        """Test multiple address generations produce different addresses."""
        response1 = client.get("/api/wallet/new")
        response2 = client.get("/api/wallet/new")

        data1 = response1.get_json()
        data2 = response2.get_json()

        # Addresses should be different (with very high probability)
        assert data1["address"] != data2["address"]
        assert data1["pubkey_hash"] != data2["pubkey_hash"]

    def test_wallet_balance_initial(self, client):
        """Test GET /api/wallet/balance returns initial balance structure."""
        response = client.get("/api/wallet/balance")
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "success"
        assert "balance_satoshis" in data
        assert "balance_coins" in data
        assert "balance_cents" in data
        assert "utxo_count" in data

        # Initially no addresses, so balance should be 0
        assert isinstance(data["balance_satoshis"], int)
        assert isinstance(data["balance_coins"], int)
        assert isinstance(data["balance_cents"], int)
        assert isinstance(data["utxo_count"], int)

    def test_wallet_balance_after_mining(self, client):
        """Test that balance increases after mining a block."""
        # Generate an address
        addr_response = client.get("/api/wallet/new")
        address = addr_response.get_json()["address"]

        # Check initial balance
        balance_before = client.get("/api/wallet/balance").get_json()
        initial_satoshis = balance_before["balance_satoshis"]

        # Mine a block to that address
        mine_response = client.post(
            "/api/mining/start",
            data=json.dumps({"blocks": 1, "address": address}),
            content_type="application/json",
        )
        assert mine_response.status_code == 200

        # Wait for mining to complete by polling status
        import time
        for _ in range(60):  # Up to 30 seconds
            status = client.get("/api/mining/status").get_json()
            if status["status"] != "mining":
                break
            time.sleep(0.5)

        # Check balance after mining
        balance_after = client.get("/api/wallet/balance").get_json()
        final_satoshis = balance_after["balance_satoshis"]

        # Balance should have increased (coinbase reward received)
        assert final_satoshis > initial_satoshis


# ============================================================================= #
# Blockchain API Tests
# ============================================================================= #


class TestBlockchainAPI:
    """Test blockchain info endpoints."""

    def test_blockchain_info_structure(self, client):
        """Test GET /api/blockchain/info returns expected structure."""
        response = client.get("/api/blockchain/info")
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "success"
        assert "height" in data
        assert "tip_hash" in data
        assert "total_money_satoshis" in data
        assert "total_money_coins" in data
        assert "tx_count" in data
        assert "mempool_size" in data

    def test_blockchain_info_genesis_state(self, client):
        """Test blockchain info reflects genesis state initially."""
        response = client.get("/api/blockchain/info")
        data = response.get_json()

        # Genesis block is height 0
        assert data["height"] == 0
        # Tip hash should be a valid hex string
        assert isinstance(data["tip_hash"], str)
        assert len(data["tip_hash"]) == 64  # SHA256 hex digest length

    def test_blockchain_info_after_mining(self, client):
        """Test blockchain info updates after mining a block."""
        # Get initial height
        initial_info = client.get("/api/blockchain/info").get_json()
        initial_height = initial_info["height"]

        # Generate an address and mine
        addr_response = client.get("/api/wallet/new")
        address = addr_response.get_json()["address"]

        mine_response = client.post(
            "/api/mining/start",
            data=json.dumps({"blocks": 1, "address": address}),
            content_type="application/json",
        )

        # Wait for mining to complete
        import time
        for _ in range(60):
            status = client.get("/api/mining/status").get_json()
            if status["status"] != "mining":
                break
            time.sleep(0.5)

        # Get updated info
        updated_info = client.get("/api/blockchain/info").get_json()
        updated_height = updated_info["height"]

        # Height should have increased
        assert updated_height > initial_height
        # Tip hash should have changed
        assert updated_info["tip_hash"] != initial_info["tip_hash"]


# ============================================================================= #
# Mining API Tests
# ============================================================================= #


class TestMiningAPI:
    """Test mining-related API endpoints."""

    def test_mining_start_valid(self, client):
        """Test POST /api/mining/start with valid parameters."""
        # Generate an address first
        addr_response = client.get("/api/wallet/new")
        address = addr_response.get_json()["address"]

        # Start mining
        response = client.post(
            "/api/mining/start",
            data=json.dumps({"blocks": 1, "address": address}),
            content_type="application/json",
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "mining"
        assert data["blocks_to_mine"] == 1

    def test_mining_start_missing_address(self, client):
        """Test POST /api/mining/start with missing address returns 400."""
        response = client.post(
            "/api/mining/start",
            data=json.dumps({"blocks": 1}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["status"] == "error"

    def test_mining_start_invalid_address(self, client):
        """Test POST /api/mining/start with invalid address returns 400."""
        response = client.post(
            "/api/mining/start",
            data=json.dumps({"blocks": 1, "address": "invalid_address"}),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["status"] == "error"
        assert "Invalid address" in data["message"]

    def test_mining_start_invalid_blocks(self, client):
        """Test POST /api/mining/start with invalid blocks count returns 400."""
        # Generate an address
        addr_response = client.get("/api/wallet/new")
        address = addr_response.get_json()["address"]

        # Try to mine 0 blocks
        response = client.post(
            "/api/mining/start",
            data=json.dumps({"blocks": 0, "address": address}),
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_mining_status_idle(self, client):
        """Test GET /api/mining/status when not mining."""
        response = client.get("/api/mining/status")
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "idle"
        assert "blocks_mined" in data
        assert "total_blocks" in data
        assert "current_height" in data

    def test_mining_status_during_mining(self, client):
        """Test GET /api/mining/status while mining is active."""
        # Generate an address
        addr_response = client.get("/api/wallet/new")
        address = addr_response.get_json()["address"]

        # Start mining
        client.post(
            "/api/mining/start",
            data=json.dumps({"blocks": 1, "address": address}),
            content_type="application/json",
        )

        # Check status immediately
        status_response = client.get("/api/mining/status")
        assert status_response.status_code == 200
        data = status_response.get_json()

        # Should be mining or idle (depending on timing)
        assert data["status"] in ("mining", "idle")
        assert "current_height" in data

    def test_mining_stop(self, client):
        """Test GET /api/mining/stop stops mining."""
        # Generate an address
        addr_response = client.get("/api/wallet/new")
        address = addr_response.get_json()["address"]

        # Start mining
        client.post(
            "/api/mining/start",
            data=json.dumps({"blocks": 5, "address": address}),
            content_type="application/json",
        )

        # Stop mining
        response = client.get("/api/mining/stop")
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "stopped"


# ============================================================================= #
# Transaction API Tests
# ============================================================================= #


class TestTransactionAPI:
    """Test transaction-related API endpoints."""

    def test_transactions_list_empty(self, client):
        """Test GET /api/transactions returns list structure."""
        response = client.get("/api/transactions")
        assert response.status_code == 200

        data = response.get_json()
        assert data["status"] == "success"
        assert "transactions" in data
        assert isinstance(data["transactions"], list)

    def test_transactions_after_mining(self, client):
        """Test transactions list updates after mining."""
        # Generate an address
        addr_response = client.get("/api/wallet/new")
        address = addr_response.get_json()["address"]

        # Mine a block
        client.post(
            "/api/mining/start",
            data=json.dumps({"blocks": 1, "address": address}),
            content_type="application/json",
        )

        # Wait for mining to complete
        import time
        for _ in range(60):
            status = client.get("/api/mining/status").get_json()
            if status["status"] != "mining":
                break
            time.sleep(0.5)

        # Get transactions
        response = client.get("/api/transactions")
        data = response.get_json()

        assert data["status"] == "success"
        # Should have at least the coinbase transaction from the mined block
        assert len(data["transactions"]) > 0


# ============================================================================= #
# Error Handling Tests
# ============================================================================= #


class TestErrorHandling:
    """Test error handling."""

    def test_404_not_found(self, client):
        """Test 404 error for invalid routes."""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404
        data = response.get_json()
        assert data["status"] == "error"

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present."""
        response = client.get("/api/blockchain/info")
        assert "Access-Control-Allow-Origin" in response.headers
        assert response.headers["Access-Control-Allow-Origin"] == "*"

    def test_json_content_type(self, client):
        """Test that API responses have correct content type."""
        response = client.get("/api/blockchain/info")
        assert "application/json" in response.content_type


# ============================================================================= #
# Integration Tests
# ============================================================================= #


class TestIntegration:
    """Integration tests combining multiple features."""

    def test_full_mining_flow(self, client):
        """Test complete mining flow: generate address, mine, check balance."""
        # Step 1: Generate an address
        addr_response = client.get("/api/wallet/new")
        assert addr_response.status_code == 200
        address = addr_response.get_json()["address"]

        # Step 2: Mine a block
        mine_response = client.post(
            "/api/mining/start",
            data=json.dumps({"blocks": 1, "address": address}),
            content_type="application/json",
        )
        assert mine_response.status_code == 200

        # Step 3: Wait for mining to complete
        import time
        for _ in range(60):
            status = client.get("/api/mining/status").get_json()
            if status["status"] != "mining":
                break
            time.sleep(0.5)

        # Step 4: Check balance
        balance_response = client.get("/api/wallet/balance")
        assert balance_response.status_code == 200
        balance = balance_response.get_json()
        assert balance["balance_satoshis"] > 0

        # Step 5: Verify blockchain height increased
        info_response = client.get("/api/blockchain/info")
        info = info_response.get_json()
        assert info["height"] >= 1

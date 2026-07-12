"""MyCoin Web Dashboard — Flask application for blockchain visualization and interaction.

This module provides a RESTful API and web interface for MyCoin, allowing users to:
  - Generate new wallet addresses
  - Check wallet balances
  - View blockchain information
  - Mine blocks with configurable parameters
  - Monitor mining progress in real-time

Educational use only — never holds real funds.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Optional

from flask import Flask, jsonify, render_template, request
from node import Node
from transaction import generate_keypair, pubkey_hash
from wallet import address_from_pubkey_hash

app = Flask(__name__, template_folder="templates", static_folder="static")

# Global state for mining operations
app.mining_state = {
    "is_mining": False,
    "blocks_to_mine": 0,
    "blocks_mined": 0,
    "current_block_height": 0,
    "mining_address": None,
    "mining_thread": None,
}

# Global node instance (initialized once per app instance)
app.node: Optional[Node] = None

# Generated addresses for wallet operations (in-memory storage for demo)
app.generated_addresses = {}  # pubkey_hash -> {"address": ..., "pubkey": ...}

# Lock for thread-safe mining operations
app.mining_lock = threading.Lock()


def get_node() -> Node:
    """Get or create the global node instance."""
    if app.node is None:
        app.node = Node("web-app", coinbase_maturity=0)
    return app.node


def mining_worker(blocks_to_mine: int, miner_address: str) -> None:
    """Background worker thread for mining blocks."""
    node = get_node()
    app.mining_state["blocks_mined"] = 0
    app.mining_state["current_block_height"] = node.chain.height

    for i in range(blocks_to_mine):
        if not app.mining_state["is_mining"]:
            break

        try:
            block = node.mine_block(miner_address)
            if block is not None:
                app.mining_state["blocks_mined"] = i + 1
                app.mining_state["current_block_height"] = node.chain.height
            else:
                break
        except Exception as e:
            print(f"Mining error: {e}")
            break

    app.mining_state["is_mining"] = False


# ============================================================================= #
# Routes
# ============================================================================= #


@app.route("/")
def index():
    """Render the main dashboard."""
    return render_template("index.html")


@app.route("/wallet")
def wallet_page():
    """Render the wallet page."""
    return render_template("wallet.html")


@app.route("/mining")
def mining_page():
    """Render the mining page."""
    return render_template("mining.html")


# ============================================================================= #
# API Routes — Wallet
# ============================================================================= #


@app.route("/api/wallet/new", methods=["GET"])
def api_wallet_new():
    """Generate a new keypair and return address + pubkey_hash."""
    try:
        sk, pubkey_hex = generate_keypair()
        pkh = pubkey_hash(pubkey_hex)
        address = address_from_pubkey_hash(pkh)

        # Store for potential balance checking
        app.generated_addresses[pkh] = {
            "address": address,
            "pubkey": pubkey_hex,
            "pubkey_hash": pkh,
        }

        return jsonify(
            {
                "status": "success",
                "address": address,
                "pubkey_hash": pkh,
                "pubkey": pubkey_hex,
            }
        ), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/wallet/balance", methods=["GET"])
def api_wallet_balance():
    """Get balance for all generated addresses in this session."""
    try:
        node = get_node()
        total_balance = 0
        utxo_count = 0

        # Check all generated addresses
        for pkh in app.generated_addresses.keys():
            # Iterate through all UTXOs and find those matching this pubkey_hash
            for _txid, _idx, out in node.chain.utxo.items():
                if out.pubkey_hash == pkh:
                    total_balance += out.amount
                    utxo_count += 1

        # Convert satoshis to coins (assuming 100 satoshis = 1 coin)
        # In real Bitcoin: 100,000,000 satoshis = 1 BTC
        # For MyCoin: using simpler 100 satoshis = 1 coin for demo
        balance_coins = total_balance // 100
        balance_cents = (total_balance % 100)

        return jsonify(
            {
                "status": "success",
                "balance_satoshis": total_balance,
                "balance_coins": balance_coins,
                "balance_cents": balance_cents,
                "utxo_count": utxo_count,
            }
        ), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================================= #
# API Routes — Blockchain Info
# ============================================================================= #


@app.route("/api/blockchain/info", methods=["GET"])
def api_blockchain_info():
    """Get blockchain state: height, tip hash, total money, tx count."""
    try:
        node = get_node()
        chain = node.chain

        # Count total transactions in the active chain
        tx_count = sum(
            len(block.transactions)
            for block_hash in chain.active_chain()
            for block in [chain.blocks[block_hash]]
        )

        # Calculate total money (sum of coinbase outputs)
        # In a real system, this would be tracked more efficiently
        total_money_satoshis = sum(
            output.amount
            for block_hash in chain.active_chain()
            for block in [chain.blocks[block_hash]]
            for tx in block.transactions
            for output in tx.outputs
        )
        total_money_coins = total_money_satoshis // 100

        return jsonify(
            {
                "status": "success",
                "height": chain.height,
                "tip_hash": chain.tip,
                "total_money_satoshis": total_money_satoshis,
                "total_money_coins": total_money_coins,
                "tx_count": tx_count,
                "mempool_size": len(chain.mempool),
            }
        ), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================================= #
# API Routes — Mining
# ============================================================================= #


@app.route("/api/mining/start", methods=["POST"])
def api_mining_start():
    """Start mining blocks. Expects JSON: {"blocks": N, "address": "..."}"""
    with app.mining_lock:
        if app.mining_state["is_mining"]:
            return jsonify(
                {
                    "status": "error",
                    "message": "Mining already in progress",
                }
            ), 400

        try:
            data = request.get_json()
            blocks_to_mine = data.get("blocks", 1)
            miner_address = data.get("address")

            if not miner_address or blocks_to_mine <= 0:
                return jsonify(
                    {
                        "status": "error",
                        "message": "Invalid blocks or address",
                    }
                ), 400

            # Validate and convert address to pubkey_hash
            try:
                from wallet import pubkey_hash_from_address
                miner_pubkey_hash = pubkey_hash_from_address(miner_address)
            except Exception as e:
                return jsonify(
                    {
                        "status": "error",
                        "message": f"Invalid address format: {str(e)}",
                    }
                ), 400

            app.mining_state["is_mining"] = True
            app.mining_state["blocks_to_mine"] = blocks_to_mine
            app.mining_state["blocks_mined"] = 0
            app.mining_state["mining_address"] = miner_address

            # Start mining in a background thread (pass pubkey_hash, not address)
            thread = threading.Thread(
                target=mining_worker, args=(blocks_to_mine, miner_pubkey_hash), daemon=True
            )
            app.mining_state["mining_thread"] = thread
            thread.start()

            return jsonify(
                {
                    "status": "mining",
                    "blocks_to_mine": blocks_to_mine,
                }
            ), 200

        except Exception as e:
            app.mining_state["is_mining"] = False
            return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/mining/status", methods=["GET"])
def api_mining_status():
    """Get current mining status."""
    try:
        node = get_node()
        return jsonify(
            {
                "status": "mining" if app.mining_state["is_mining"] else "idle",
                "blocks_mined": app.mining_state["blocks_mined"],
                "total_blocks": app.mining_state["blocks_to_mine"],
                "current_height": node.chain.height,
                "tip_hash": node.chain.tip,
            }
        ), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/mining/stop", methods=["GET"])
def api_mining_stop():
    """Stop the current mining operation."""
    try:
        app.mining_state["is_mining"] = False
        return jsonify({"status": "stopped"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================================= #
# API Routes — Transactions
# ============================================================================= #


@app.route("/api/transactions", methods=["GET"])
def api_transactions():
    """Get recent transactions from mempool and recent blocks."""
    try:
        node = get_node()
        transactions = []

        # Get mempool transactions (pending)
        for txid, tx in list(node.chain.mempool.items())[:10]:
            transactions.append(
                {
                    "txid": txid,
                    "status": "pending",
                    "inputs": len(tx.inputs),
                    "outputs": len(tx.outputs),
                }
            )

        # Get transactions from the last 5 blocks
        chain = node.chain
        for block_hash in chain.active_chain()[-5:]:
            block = chain.blocks[block_hash]
            for tx in block.transactions:
                transactions.append(
                    {
                        "txid": tx.txid,
                        "status": "confirmed",
                        "inputs": len(tx.inputs),
                        "outputs": len(tx.outputs),
                    }
                )

        return jsonify(
            {
                "status": "success",
                "transactions": transactions[:20],  # Limit to 20 most recent
            }
        ), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================================= #
# Error Handlers
# ============================================================================= #


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"status": "error", "message": "Not found"}), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors."""
    return jsonify({"status": "error", "message": "Internal server error"}), 500


# ============================================================================= #
# CORS Headers (educational use — allow all origins)
# ============================================================================= #


@app.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


# ============================================================================= #
# App Initialization
# ============================================================================= #


if __name__ == "__main__":
    # Initialize the node on startup
    get_node()
    print("MyCoin Dashboard starting on http://localhost:5000")
    app.run(debug=True, host="localhost", port=5000)

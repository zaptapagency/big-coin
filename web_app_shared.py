"""MyCoin Web Dashboard — Using Shared State Server.

This version connects to shared_state.py instead of creating its own Node.
Run shared_state.py FIRST, then this app.
"""

from __future__ import annotations

import logging
from flask import Flask, jsonify, render_template, request
from shared_client import SharedStateClient

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['JSON_SORT_KEYS'] = False

# Connect to shared state server
shared_client = SharedStateClient("127.0.0.1", 9999)
logger.info("SharedStateClient created")


# ============================================================================= #
# Routes — Pages
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
    """Generate a new keypair."""
    try:
        result = shared_client.new_key()
        return jsonify(
            {
                "status": "success",
                "address": result["address"],
                "pubkey_hash": result["pubkey_hash"],
            }
        ), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/wallet/addresses", methods=["GET"])
def api_wallet_addresses():
    """Get all generated addresses from shared state."""
    try:
        logger.debug("Getting addresses from shared state...")
        result = shared_client.get_addresses()
        logger.debug(f"Got {len(result.get('addresses', []))} addresses")
        return jsonify(
            {
                "status": "success",
                "addresses": result.get("addresses", []),
            }
        ), 200
    except Exception as e:
        logger.error(f"Error in api_wallet_addresses: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/wallet/balance", methods=["GET"])
def api_wallet_balance():
    """Get total balance."""
    try:
        result = shared_client.get_balance()
        return jsonify(
            {
                "status": "success",
                "balance_coins": result["balance_coins"],
                "balance_cents": result["balance_cents"],
                "utxo_count": 0,  # Could add to shared_client if needed
            }
        ), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================================= #
# API Routes — Blockchain
# ============================================================================= #


@app.route("/api/blockchain/info", methods=["GET"])
def api_blockchain_info():
    """Get blockchain information."""
    try:
        result = shared_client.blockchain_info()
        return jsonify(
            {
                "status": "success",
                "height": result["height"],
                "tip_hash": result["tip_hash"],
                "total_money_coins": result["total_money_coins"],
                "total_money_cents": result["total_money_cents"],
                "tx_count": result["tx_count"],
            }
        ), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================================= #
# API Routes — Mining
# ============================================================================= #


@app.route("/api/mining/start", methods=["POST"])
def api_mining_start():
    """Start mining."""
    try:
        data = request.json
        blocks = data.get("blocks", 1)
        address = data.get("address", "")

        if not address:
            return jsonify({"status": "error", "message": "No address provided"}), 400

        result = shared_client.start_mining(blocks, address)

        if "error" in result:
            return jsonify({"status": "error", "message": result["error"]}), 400

        return jsonify({"status": "success", "message": "Mining started"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/mining/status", methods=["GET"])
def api_mining_status():
    """Get mining status."""
    try:
        result = shared_client.mining_status()
        return jsonify(
            {
                "status": "success",
                "is_mining": result["is_mining"],
                "blocks_mined": result["blocks_mined"],
                "blocks_to_mine": result["blocks_to_mine"],
                "current_height": result["current_height"],
            }
        ), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/mining/stop", methods=["GET"])
def api_mining_stop():
    """Stop mining."""
    try:
        shared_client.stop_mining()
        return jsonify({"status": "success", "message": "Mining stopped"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ============================================================================= #
# Run
# ============================================================================= #


if __name__ == "__main__":
    print("=" * 70)
    print("MyCoin Web Dashboard (using Shared State)")
    print("=" * 70)
    print("Make sure shared_state.py is running on 127.0.0.1:9999")
    print("Starting Flask on http://localhost:5000")
    print("=" * 70)
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=False, use_reloader=False)

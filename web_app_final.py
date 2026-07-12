"""MyCoin Web Dashboard - FINAL WORKING VERSION"""
from flask import Flask, jsonify, render_template, request
from shared_client import SharedStateClient

app = Flask(__name__, template_folder="templates", static_folder="static")
client = SharedStateClient("127.0.0.1", 9999)

# ============================================================================= #
# PAGES
# ============================================================================= #

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/wallet")
def wallet_page():
    return render_template("wallet.html")

@app.route("/mining")
def mining_page():
    return render_template("mining.html")

# ============================================================================= #
# API WALLET
# ============================================================================= #

@app.route("/api/wallet/new", methods=["GET"])
def api_wallet_new():
    try:
        result = client.new_key()
        return jsonify({
            "status": "success",
            "address": result["address"],
            "pubkey_hash": result["pubkey_hash"],
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/wallet/addresses", methods=["GET"])
def api_wallet_addresses():
    try:
        result = client.get_addresses()
        return jsonify({"status": "success", "addresses": result.get("addresses", [])})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/wallet/balance", methods=["GET"])
def api_wallet_balance():
    try:
        result = client.get_balance()
        return jsonify({
            "status": "success",
            "balance_coins": result["balance_coins"],
            "balance_cents": result["balance_cents"],
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============================================================================= #
# API BLOCKCHAIN
# ============================================================================= #

@app.route("/api/blockchain/info", methods=["GET"])
def api_blockchain_info():
    try:
        result = client.blockchain_info()
        return jsonify({
            "status": "success",
            "height": result["height"],
            "tip_hash": result["tip_hash"],
            "total_money_coins": result["total_money_coins"],
            "total_money_cents": result["total_money_cents"],
            "tx_count": result["tx_count"],
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ============================================================================= #
# API MINING
# ============================================================================= #

@app.route("/api/mining/start", methods=["POST"])
def api_mining_start():
    try:
        data = request.json or {}
        blocks = data.get("blocks", 1)
        address = data.get("address", "")
        if not address:
            return jsonify({"status": "error", "message": "No address"}), 400
        result = client.start_mining(blocks, address)
        if "error" in result:
            return jsonify({"status": "error", "message": result["error"]}), 400
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/mining/status", methods=["GET"])
def api_mining_status():
    try:
        result = client.mining_status()
        return jsonify({
            "status": "success",
            "is_mining": result["is_mining"],
            "blocks_mined": result["blocks_mined"],
            "blocks_to_mine": result["blocks_to_mine"],
            "current_height": result["current_height"],
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/mining/stop", methods=["GET"])
def api_mining_stop():
    try:
        client.stop_mining()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    print("MyCoin Web Dashboard")
    print("Running on http://localhost:5000")
    app.run(host="127.0.0.1", port=5002, debug=False, threaded=False)

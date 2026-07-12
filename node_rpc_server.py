"""JSON-RPC API Server for Full Node.

Clients (wallets, miners, dashboards) connect here via HTTP/WebSocket
to interact with the local full node.
"""

from flask import Flask, jsonify, request, render_template
from full_node import BigCoinFullNode
import logging
import json
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NodeRPCServer:
    """Wraps a full node with JSON-RPC HTTP API."""

    def __init__(self, node: BigCoinFullNode, rpc_host: str = "127.0.0.1", rpc_port: int = 8000):
        self.node = node
        self.rpc_host = rpc_host
        self.rpc_port = rpc_port

        # Create Flask app
        self.app = Flask(__name__, template_folder="templates", static_folder="static")
        self.setup_routes()

    def setup_routes(self):
        """Setup HTTP routes."""

        @self.app.route("/", methods=["GET"])
        def index():
            """Dashboard home page."""
            return render_template("index.html")

        @self.app.route("/wallet", methods=["GET"])
        def wallet_page():
            return render_template("wallet.html")

        @self.app.route("/mining", methods=["GET"])
        def mining_page():
            return render_template("mining.html")

        # ===================================================================== #
        # JSON-RPC ENDPOINTS
        # ===================================================================== #

        @self.app.route("/rpc", methods=["POST"])
        def rpc():
            """JSON-RPC endpoint."""
            try:
                request_data = request.json
                result = self.node.process_rpc_request(request_data)
                return jsonify(result)
            except Exception as e:
                logger.error(f"RPC error: {e}")
                return jsonify({"error": str(e)}), 500

        # ===================================================================== #
        # REST API (for convenience)
        # ===================================================================== #

        @self.app.route("/api/wallet/new", methods=["GET"])
        def api_wallet_new():
            """Generate new address."""
            try:
                result = self.node.generate_new_address()
                return jsonify({"status": "success", **result})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/wallet/balance", methods=["GET"])
        def api_wallet_balance():
            """Get balance."""
            try:
                result = self.node.get_balance()
                return jsonify({"status": "success", **result})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/wallet/send", methods=["POST"])
        def api_wallet_send():
            try:
                data = request.json or {}
                to_address = data.get("to_address")
                amount = data.get("amount")  # amount in COINS (float), from the UI
                if not to_address or amount is None:
                    return jsonify(
                        {"status": "error", "message": "to_address and amount required"}
                    ), 400
                try:
                    amount_cents = int(round(float(amount) * 100_000_000))
                except (TypeError, ValueError):
                    return jsonify({"status": "error", "message": "invalid amount"}), 400
                if amount_cents <= 0:
                    return jsonify({"status": "error", "message": "amount must be positive"}), 400
                result = self.node.send_to_address(to_address, amount_cents)
                code = 200 if result.get("status") == "success" else 400
                return jsonify(result), code
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/mempool", methods=["GET"])
        def api_mempool():
            try:
                result = self.node.get_mempool()
                return jsonify({"status": "success", **result})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/blockchain/info", methods=["GET"])
        def api_blockchain_info():
            """Get blockchain info."""
            try:
                result = self.node.get_blockchain_info()
                return jsonify({"status": "success", **result})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/block/<int:height>", methods=["GET"])
        def api_get_block(height):
            """Return the active-chain block at a given height (used for sync)."""
            try:
                block = self.node.get_block_by_height(height)
                if block is None:
                    return jsonify({"status": "error", "message": "not found"}), 404
                return jsonify({"status": "success", "block": block})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/mining/start", methods=["POST"])
        def api_mining_start():
            """Start mining."""
            try:
                data = request.json or {}
                address = data.get("address")
                if not address:
                    return jsonify({"status": "error", "message": "No address"}), 400

                try:
                    self.node.start_mining(address)
                    return jsonify({"status": "success", "message": "Mining started"})
                except Exception as e:
                    logger.error(f"Mining start error: {e}", exc_info=True)
                    return jsonify({"status": "error", "message": str(e)}), 400
            except Exception as e:
                logger.error(f"Mining API error: {e}", exc_info=True)
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/mining/status", methods=["GET"])
        def api_mining_status():
            """Get mining status."""
            try:
                status = self.node.process_rpc_request({"method": "mining_status"})
                return jsonify({"status": "success", **status})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/mining/stop", methods=["GET"])
        def api_mining_stop():
            """Stop mining."""
            try:
                self.node.stop_mining()
                return jsonify({"status": "success", "message": "Mining stopped"})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/node/peers", methods=["GET"])
        def api_node_peers():
            """Get connected peers."""
            try:
                peers = self.node.get_connected_peers()
                return jsonify({
                    "status": "success",
                    "peer_count": len(peers),
                    "peers": [p.to_dict() for p in peers]
                })
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/api/node/stats", methods=["GET"])
        def api_node_stats():
            """Get node statistics."""
            try:
                stats = self.node.get_stats()
                return jsonify({"status": "success", **stats})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

    def run(self, debug=False):
        """Run the RPC server.

        In normal operation the app is served via `wsgi_server.serve` (waitress,
        which handles high concurrent request load far better than Flask's dev
        server). `debug=True` keeps the Flask dev server for local debugging.
        """
        logger.info(f"Starting RPC server on {self.rpc_host}:{self.rpc_port}")
        if debug:
            self.app.run(
                host=self.rpc_host,
                port=self.rpc_port,
                debug=True,
                threaded=True,
                use_reloader=False
            )
        else:
            from wsgi_server import serve
            serve(self.app, host=self.rpc_host, port=self.rpc_port)


def main():
    """Run RPC server for a full node."""
    import sys
    import os

    node_id = sys.argv[1] if len(sys.argv) > 1 else "node1"
    p2p_port = int(sys.argv[2]) if len(sys.argv) > 2 else 9000
    rpc_port = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
    # Coinbase maturity is 100 by default (Bitcoin-like); override for demos.
    maturity = int(os.environ.get("COINBASE_MATURITY", "100"))

    # Create full node
    node = BigCoinFullNode(node_id, host="127.0.0.1", port=p2p_port,
                           coinbase_maturity=maturity)
    node.start_server()

    # Start RPC server
    rpc_server = NodeRPCServer(node, rpc_host="127.0.0.1", rpc_port=rpc_port)
    rpc_server.run(debug=False)


if __name__ == "__main__":
    main()

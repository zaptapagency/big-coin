"""Minimal test of SharedStateClient in Flask"""
from flask import Flask, jsonify
from shared_client import SharedStateClient

app = Flask(__name__)

# Global client
client = SharedStateClient("127.0.0.1", 9999)

@app.route("/test/direct")
def test_direct():
    """Direct call - no client"""
    return jsonify({"status": "ok"})

@app.route("/test/client")
def test_client():
    """Call shared client"""
    try:
        result = client.blockchain_info()
        return jsonify({"status": "ok", "height": result["height"]})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    print("Starting test app...")
    app.run(host="127.0.0.1", port=5001, debug=True, threaded=False, use_reloader=False)

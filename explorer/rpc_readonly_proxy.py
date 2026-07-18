#!/usr/bin/env python3
"""Read-only JSON-RPC proxy for a wallet-loaded litecoind/bigcoind node.

Sits between a PUBLIC caller (e.g. the Railway explorer, reached via a
Cloudflare Tunnel) and a node whose RPC is bound to loopback. It:

  * authenticates the caller with its OWN Basic-auth credentials
    (so the real node password never leaves this host),
  * allows ONLY a whitelist of read-only methods (block/tx/chain queries),
    rejecting every wallet/spend/admin method with a JSON-RPC error,
  * forwards permitted calls to the node using the real node credentials.

All configuration comes from environment variables — no secrets in this file:

  PROXY_BIND            interface to listen on            (default 127.0.0.1)
  PROXY_PORT            port to listen on                 (default 9350)
  PROXY_USER            username the caller must present   (required)
  PROXY_PASSWORD        password the caller must present   (required)
  NODE_RPC_URL          upstream node RPC URL      (default http://127.0.0.1:9332/)
  NODE_RPC_USER         node rpcuser                       (required)
  NODE_RPC_PASSWORD     node rpcpassword                   (required)
  PROXY_TIMEOUT         upstream timeout seconds           (default 15)
"""
import base64
import hmac
import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# The only methods the explorer needs. Everything else is refused.
# All are read-only: block/tx/chain queries plus the address-page helpers
# (scantxoutset for UTXO lookup, validateaddress, estimatesmartfee,
# decoderawtransaction). Wallet, spend, mining and admin methods are NOT here,
# so sendrawtransaction / generatetoaddress / getbalance etc. are rejected.
ALLOWED_METHODS = frozenset({
    "getblockcount",
    "getblockhash",
    "getblock",
    "getblockheader",
    "getrawtransaction",
    "getblockchaininfo",
    "getmempoolinfo",
    "getrawmempool",
    "getnetworkinfo",
    "getbestblockhash",
    "uptime",
    "scantxoutset",
    "validateaddress",
    "estimatesmartfee",
    "decoderawtransaction",
})

PROXY_BIND = os.environ.get("PROXY_BIND", "127.0.0.1")
PROXY_PORT = int(os.environ.get("PROXY_PORT", "9350"))
PROXY_USER = os.environ.get("PROXY_USER", "")
PROXY_PASSWORD = os.environ.get("PROXY_PASSWORD", "")
NODE_RPC_URL = os.environ.get("NODE_RPC_URL", "http://127.0.0.1:9332/")
NODE_RPC_USER = os.environ.get("NODE_RPC_USER", "")
NODE_RPC_PASSWORD = os.environ.get("NODE_RPC_PASSWORD", "")
PROXY_TIMEOUT = float(os.environ.get("PROXY_TIMEOUT", "15"))

_NODE_AUTH = "Basic " + base64.b64encode(
    f"{NODE_RPC_USER}:{NODE_RPC_PASSWORD}".encode()
).decode()
_EXPECTED_CALLER_AUTH = "Basic " + base64.b64encode(
    f"{PROXY_USER}:{PROXY_PASSWORD}".encode()
).decode()


def _rpc_error(id_, message, code=-32601):
    return json.dumps({"jsonrpc": "1.0", "id": id_,
                       "result": None,
                       "error": {"code": code, "message": message}}).encode()


class Handler(BaseHTTPRequestHandler):
    server_version = "roproxy/1.0"

    def _send(self, status, body, ctype="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _unauthorized(self):
        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="rpc"')
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        # Tiny health endpoint for the tunnel/monitoring (no auth, no node call).
        if self.path in ("/health", "/healthz"):
            self._send(200, b'{"status":"ok"}')
        else:
            self._send(404, b'{"error":"not found"}')

    def do_POST(self):
        # 1) Authenticate the caller against the PROXY credentials.
        provided = self.headers.get("Authorization", "")
        if not hmac.compare_digest(provided, _EXPECTED_CALLER_AUTH):
            self._unauthorized()
            return

        # 2) Read + parse the JSON-RPC body.
        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b""
            req = json.loads(raw.decode("utf-8"))
        except (ValueError, TypeError):
            self._send(400, _rpc_error(None, "invalid JSON body", -32700))
            return

        # Support single or batch requests; enforce whitelist on each.
        items = req if isinstance(req, list) else [req]
        for it in items:
            method = it.get("method") if isinstance(it, dict) else None
            if method not in ALLOWED_METHODS:
                self._send(403, _rpc_error(
                    (it.get("id") if isinstance(it, dict) else None),
                    f"method '{method}' not permitted by read-only proxy",
                    -32601))
                return

        # 3) Forward to the node with the REAL credentials.
        try:
            upstream = urllib.request.Request(NODE_RPC_URL, data=raw)
            upstream.add_header("Content-Type", "application/json")
            upstream.add_header("Authorization", _NODE_AUTH)
            with urllib.request.urlopen(upstream, timeout=PROXY_TIMEOUT) as resp:
                body = resp.read()
                self._send(resp.status, body)
        except urllib.error.HTTPError as exc:
            # Pass through the node's JSON-RPC error body verbatim.
            body = exc.read() or _rpc_error(None, f"node HTTP {exc.code}")
            self._send(exc.code, body)
        except Exception as exc:  # noqa: BLE001 - report upstream failure cleanly
            self._send(502, _rpc_error(None, f"upstream unreachable: {exc}", -32603))

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def main():
    missing = [n for n, v in (
        ("PROXY_USER", PROXY_USER), ("PROXY_PASSWORD", PROXY_PASSWORD),
        ("NODE_RPC_USER", NODE_RPC_USER), ("NODE_RPC_PASSWORD", NODE_RPC_PASSWORD),
    ) if not v]
    if missing:
        sys.stderr.write("FATAL: missing env vars: %s\n" % ", ".join(missing))
        sys.exit(1)

    srv = ThreadingHTTPServer((PROXY_BIND, PROXY_PORT), Handler)
    sys.stderr.write(
        f"read-only RPC proxy on {PROXY_BIND}:{PROXY_PORT} -> {NODE_RPC_URL} "
        f"(allowed: {len(ALLOWED_METHODS)} methods)\n")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()

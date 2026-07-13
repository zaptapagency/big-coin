"""A small Bitcoin/Litecoin-Core-style JSON-RPC client for bigcoind.

Uses the standard library (urllib) so no third-party dependency is strictly
required. If DEMO_MODE is enabled -- either explicitly via env, or implicitly
because the node is unreachable -- calls fall back to bundled sample data.
"""
import base64
import json
import socket
import urllib.error
import urllib.request

import config
import demo_data


class RPCError(Exception):
    """Raised when the node returns a JSON-RPC error object."""

    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code
        self.message = message


class RPCConnectionError(Exception):
    """Raised when the node cannot be reached / did not answer."""


# Methods that we know how to serve from demo_data.
_DEMO_METHODS = {
    "getblockcount",
    "getblockhash",
    "getblock",
    "getrawtransaction",
    "getblockchaininfo",
    "getmempoolinfo",
    "getrawmempool",
    "getnetworkinfo",
}


class RpcClient:
    """Thin JSON-RPC client with automatic DEMO_MODE fallback.

    Attributes:
        demo: True when the client is currently serving sample data.
        demo_reason: human-readable reason demo mode is active (or None).
    """

    def __init__(self):
        self.demo = config.DEMO_MODE
        self.demo_reason = "DEMO_MODE explicitly enabled" if config.DEMO_MODE else None
        self._id = 0

    # -- public helpers ---------------------------------------------------

    def is_demo(self) -> bool:
        return self.demo

    def call(self, method, *params):
        """Invoke an RPC method. Falls back to demo data on connection
        failure when demo mode is allowed."""
        if self.demo:
            return self._demo_call(method, params)

        try:
            return self._http_call(method, list(params))
        except RPCConnectionError as exc:
            # Node unreachable: enable demo mode unless the user has
            # explicitly disabled it (DEMO_MODE=0).
            if config.DEMO_MODE_EXPLICIT and not config.DEMO_MODE:
                # User said DEMO_MODE=0 -> do not silently fake data.
                raise
            self.demo = True
            self.demo_reason = f"BigCoin node unreachable ({exc}); serving demo data"
            return self._demo_call(method, params)

    # -- HTTP transport ---------------------------------------------------

    def _http_call(self, method, params):
        self._id += 1
        payload = json.dumps(
            {"jsonrpc": "1.0", "id": self._id, "method": method, "params": params}
        ).encode("utf-8")

        req = urllib.request.Request(config.rpc_url(), data=payload)
        req.add_header("Content-Type", "application/json")
        if config.RPC_USER or config.RPC_PASSWORD:
            token = base64.b64encode(
                f"{config.RPC_USER}:{config.RPC_PASSWORD}".encode()
            ).decode()
            req.add_header("Authorization", f"Basic {token}")

        try:
            with urllib.request.urlopen(req, timeout=config.RPC_TIMEOUT) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            # Bitcoin Core returns 500 with a JSON-RPC error body for bad calls.
            try:
                body = exc.read().decode("utf-8")
                data = json.loads(body)
                err = data.get("error")
                if err:
                    raise RPCError(err.get("message", str(err)), err.get("code"))
            except (ValueError, AttributeError):
                pass
            if exc.code in (401, 403):
                raise RPCConnectionError(f"authentication failed (HTTP {exc.code})")
            raise RPCConnectionError(f"HTTP error {exc.code}")
        except (TimeoutError, urllib.error.URLError, ConnectionError, OSError) as exc:
            raise RPCConnectionError(str(getattr(exc, "reason", exc)))

        try:
            data = json.loads(body)
        except ValueError:
            raise RPCConnectionError("invalid JSON response from node")

        if data.get("error"):
            err = data["error"]
            raise RPCError(err.get("message", str(err)), err.get("code"))
        return data.get("result")

    # -- demo transport ---------------------------------------------------

    def _demo_call(self, method, params):
        if method not in _DEMO_METHODS:
            raise RPCError(f"method '{method}' not supported in demo mode")
        fn = getattr(demo_data, method)
        try:
            return fn(*params)
        except KeyError as exc:
            raise RPCError(str(exc))

    # -- convenience wrappers --------------------------------------------

    def getblockchaininfo(self):
        return self.call("getblockchaininfo")

    def getmempoolinfo(self):
        return self.call("getmempoolinfo")

    def getnetworkinfo(self):
        try:
            return self.call("getnetworkinfo")
        except RPCError:
            return {}

    def getblockcount(self):
        return self.call("getblockcount")

    def getblockhash(self, height):
        return self.call("getblockhash", int(height))

    def getblock(self, block_hash, verbosity=1):
        return self.call("getblock", block_hash, verbosity)

    def getrawtransaction(self, txid, verbose=True):
        # Bitcoin Core accepts verbose as bool or int.
        return self.call("getrawtransaction", txid, True if verbose else False)

    def getrawmempool(self, verbose=False):
        return self.call("getrawmempool", verbose)

    # -- wallet-support wrappers (require a live node; not in demo) --------

    def scantxoutset(self, action, scanobjects):
        """Scan the UTXO set. `scanobjects` is a list of descriptor dicts,
        e.g. [{"desc": "addr(<address>)"}]. Works on a stock node without an
        address index. Not available in demo mode."""
        return self.call("scantxoutset", action, scanobjects)

    def sendrawtransaction(self, hexstring):
        return self.call("sendrawtransaction", hexstring)

    def estimatesmartfee(self, conf_target):
        return self.call("estimatesmartfee", int(conf_target))

    def decoderawtransaction(self, hexstring):
        return self.call("decoderawtransaction", hexstring)

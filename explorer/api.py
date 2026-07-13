"""JSON API for the Big Coin mobile wallet.

These endpoints give a non-custodial wallet everything it needs to operate
against a real bigcoind without any address index:

    GET  /api/status                    chain tip + mempool + node info
    GET  /api/address/<addr>/utxos      spendable outputs for an address
    GET  /api/address/<addr>/balance    confirmed / unconfirmed / total
    GET  /api/fee                        suggested fee rate (BIG/kB)
    POST /api/tx/broadcast               relay a signed raw transaction
    GET  /api/tx/<txid>                   decoded transaction

UTXO lookup uses `scantxoutset`, so it works on a stock node (no -addrindex).
When the explorer is in DEMO_MODE there is no live UTXO set, so read endpoints
return empty/zero results with `"demo": true`, and broadcast returns 503.

The wallet builds and signs transactions ON DEVICE; the server only relays the
finished hex and reports chain state. No keys ever reach this server.
"""
import re
import threading
import time

from flask import Blueprint, jsonify, request

from rpc import RpcClient, RPCConnectionError, RPCError

api = Blueprint("api", __name__, url_prefix="/api")

# Addresses are base58check or bech32: strictly alphanumeric, no separators.
# Anchoring to this charset + length blocks descriptor-string injection into
# scantxoutset's `addr(...)` argument and rejects obviously malformed input
# before it ever reaches the node.
_ADDRESS_RE = re.compile(r"^[a-zA-Z0-9]{8,100}$")

# 64-hex-char transaction id.
_TXID_RE = re.compile(r"^[0-9a-fA-F]{64}$")

# scantxoutset scans the entire UTXO set and holds cs_main, so it is expensive
# and must not run concurrently for every request. Results are cached briefly
# and scans are serialized under a single lock (also throttles abuse).
_CACHE_TTL = 15.0  # seconds
_scan_cache = {}  # address -> (expires_at, (utxos, scan_height))
_scan_lock = threading.Lock()


def _client():
    return RpcClient()


def _err(message, status):
    resp = jsonify({"error": message})
    resp.status_code = status
    return resp


def _valid_address(address):
    return bool(_ADDRESS_RE.match(address))


@api.route("/status")
def status():
    client = _client()
    try:
        info = client.getblockchaininfo()
        mempool = client.getmempoolinfo()
        net = client.getnetworkinfo()
        height = client.getblockcount()
    except RPCConnectionError as exc:
        return _err(str(exc), 503)
    except RPCError as exc:
        return _err(str(exc), 502)

    return jsonify({
        "chain": info.get("chain", "?"),
        "blocks": info.get("blocks", height),
        "headers": info.get("headers", info.get("blocks", height)),
        "bestblockhash": info.get("bestblockhash", ""),
        "difficulty": info.get("difficulty", 0),
        "verificationprogress": info.get("verificationprogress", 1.0),
        "mempool_txs": mempool.get("size", 0),
        "mempool_bytes": mempool.get("bytes", 0),
        "connections": net.get("connections", 0),
        "subversion": net.get("subversion", ""),
        "demo": client.is_demo(),
    })


def _scan_utxos(client, address):
    """Returns (utxos, scan_height). Raises RPCError/RPCConnectionError.

    In demo mode there is no UTXO set, so returns ([], None)."""
    if client.is_demo():
        return [], None
    result = client.scantxoutset("start", [{"desc": f"addr({address})"}])
    if not result or not result.get("success", False):
        return [], result.get("height") if result else None
    scan_height = result.get("height")
    utxos = []
    for u in result.get("unspents", []):
        u_height = u.get("height")
        confirmations = 0
        if scan_height is not None and u_height is not None:
            confirmations = max(0, scan_height - u_height + 1)
        utxos.append({
            "txid": u.get("txid"),
            "vout": u.get("vout"),
            "amount": float(u.get("amount", 0)),
            "scriptPubKey": u.get("scriptPubKey"),
            "height": u_height,
            "confirmations": confirmations,
        })
    return utxos, scan_height


def _cached_scan(client, address):
    """Cached + serialized wrapper around _scan_utxos.

    Reuses a recent scan (within _CACHE_TTL) for the same address, and holds
    _scan_lock so at most one scantxoutset runs at a time. Demo mode is not
    cached (it's already a cheap no-op)."""
    if client.is_demo():
        return _scan_utxos(client, address)

    now = time.monotonic()
    cached = _scan_cache.get(address)
    if cached and cached[0] > now:
        return cached[1]

    with _scan_lock:
        # Re-check under the lock: another request may have just scanned.
        cached = _scan_cache.get(address)
        now = time.monotonic()
        if cached and cached[0] > now:
            return cached[1]
        result = _scan_utxos(client, address)
        _scan_cache[address] = (now + _CACHE_TTL, result)
        return result


@api.route("/address/<address>/utxos")
def address_utxos(address):
    client = _client()
    address = address.strip()
    if not _valid_address(address):
        return _err("invalid address", 400)
    try:
        utxos, scan_height = _cached_scan(client, address)
    except RPCConnectionError as exc:
        return _err(str(exc), 503)
    except RPCError as exc:
        return _err(str(exc), 502)

    return jsonify({
        "address": address,
        "utxos": utxos,
        "scan_height": scan_height,
        "demo": client.is_demo(),
    })


@api.route("/address/<address>/balance")
def address_balance(address):
    client = _client()
    address = address.strip()
    if not _valid_address(address):
        return _err("invalid address", 400)
    try:
        utxos, _ = _cached_scan(client, address)
    except RPCConnectionError as exc:
        return _err(str(exc), 503)
    except RPCError as exc:
        return _err(str(exc), 502)

    confirmed = sum(u["amount"] for u in utxos if u["confirmations"] > 0)
    unconfirmed = sum(u["amount"] for u in utxos if u["confirmations"] == 0)
    return jsonify({
        "address": address,
        "confirmed": confirmed,
        "unconfirmed": unconfirmed,
        "total": confirmed + unconfirmed,
        "utxo_count": len(utxos),
        "demo": client.is_demo(),
    })


@api.route("/fee")
def fee():
    client = _client()
    # A conservative floor matching Core's default min relay fee (0.00001/kB).
    fallback = 0.00001
    if client.is_demo():
        return jsonify({"feerate": fallback, "blocks": None, "source": "default", "demo": True})
    try:
        est = client.estimatesmartfee(6)
        rate = est.get("feerate") if isinstance(est, dict) else None
        if rate and rate > 0:
            return jsonify({"feerate": float(rate), "blocks": est.get("blocks"), "source": "estimatesmartfee", "demo": False})
    except (RPCError, RPCConnectionError):
        pass
    return jsonify({"feerate": fallback, "blocks": None, "source": "default", "demo": client.is_demo()})


@api.route("/tx/broadcast", methods=["POST"])
def broadcast():
    client = _client()
    if client.is_demo():
        return _err("no live node available (explorer is in demo mode)", 503)

    data = request.get_json(silent=True) or {}
    rawtx = (data.get("rawtx") or data.get("hex") or "").strip()
    if not rawtx:
        return _err("missing 'rawtx' hex in request body", 400)

    try:
        txid = client.sendrawtransaction(rawtx)
    except RPCConnectionError as exc:
        return _err(str(exc), 503)
    except RPCError as exc:
        return _err(str(exc), 400)

    return jsonify({"txid": txid})


@api.route("/tx/<txid>")
def tx_json(txid):
    client = _client()
    txid = txid.strip()
    if not _TXID_RE.match(txid):
        return _err("invalid txid", 400)
    try:
        transaction = client.getrawtransaction(txid, True)
    except RPCConnectionError as exc:
        return _err(str(exc), 503)
    except RPCError as exc:
        return _err(str(exc), 404)
    return jsonify(transaction)

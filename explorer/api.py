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
import hmac

from flask import Blueprint, jsonify, request

import config
import webhooks
from rpc import RpcClient, RPCConnectionError, RPCError

api = Blueprint("api", __name__, url_prefix="/api")


def _client():
    return RpcClient()


def _err(message, status):
    resp = jsonify({"error": message})
    resp.status_code = status
    return resp


def _allowed_origin(origin):
    """Return the value to echo in Access-Control-Allow-Origin, or None."""
    allow = [o.strip() for o in config.MINING_CORS_ORIGINS.split(",") if o.strip()]
    if "*" in allow:
        return "*"
    if origin and origin in allow:
        return origin
    return None


@api.after_request
def _cors(resp):
    """Permit the browser miner (served from the website origin) to call the
    JSON API cross-origin. Only origins in MINING_CORS_ORIGINS are echoed."""
    origin = request.headers.get("Origin")
    allowed = _allowed_origin(origin)
    if allowed:
        resp.headers["Access-Control-Allow-Origin"] = allowed
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


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


@api.route("/address/<address>/utxos")
def address_utxos(address):
    client = _client()
    address = address.strip()
    try:
        utxos, scan_height = _scan_utxos(client, address)
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
    try:
        utxos, _ = _scan_utxos(client, address)
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


@api.route("/mine", methods=["POST", "OPTIONS"])
def mine():
    """Trigger real mining of one block to `address`. The NODE performs the
    proof-of-work (generatetoaddress); this endpoint just relays the request so
    a browser/phone can mine the live chain. Disabled unless MINING_ENABLED."""
    if request.method == "OPTIONS":
        return ("", 204)

    if not config.MINING_ENABLED:
        return _err("mining endpoint is disabled (set MINING_ENABLED=1 on the explorer)", 403)

    client = _client()
    if client.is_demo():
        return _err("no live node available (explorer is in demo mode)", 503)

    data = request.get_json(silent=True) or {}
    address = (data.get("address") or "").strip()
    if not address:
        return _err("missing 'address' in request body", 400)

    # Validate the address on the node before mining to it.
    try:
        info = client.validateaddress(address)
        if not info.get("isvalid"):
            return _err("invalid MoonBite address", 400)
    except RPCConnectionError as exc:
        return _err(str(exc), 503)
    except RPCError as exc:
        return _err(str(exc), 502)

    try:
        before = client.getblockcount()
        hashes = client.generatetoaddress(1, address, config.MINING_MAXTRIES)
    except RPCConnectionError as exc:
        return _err(str(exc), 503)
    except RPCError as exc:
        return _err(str(exc), 502)

    hashes = hashes or []
    return jsonify({
        "mined": len(hashes),
        "hashes": hashes,
        "height": before + len(hashes),
        "address": address,
        # False when the PoW budget was exhausted this call without a block --
        # the client should simply call again.
        "found": bool(hashes),
    })


@api.route("/tx/<txid>")
def tx_json(txid):
    client = _client()
    txid = txid.strip()
    try:
        transaction = client.getrawtransaction(txid, True)
    except RPCConnectionError as exc:
        return _err(str(exc), 503)
    except RPCError as exc:
        return _err(str(exc), 404)
    return jsonify(transaction)


# ------------------------------------------------------------------------- #
# Block explorer JSON (browse blocks / fetch a block / resolve a search).
# Read-only and demo-safe: every RPC used here is backed by demo_data, so
# these keep working on the public instance even when the node is down.
# ------------------------------------------------------------------------- #


def _block_summary(block: dict) -> dict:
    """Compact, stable summary of a getblock (verbosity>=1) result."""
    txids = block.get("tx") or []
    # verbosity 2 returns tx objects; normalise to a count either way.
    tx_count = block.get("nTx")
    if tx_count is None:
        tx_count = len(txids)
    return {
        "height": block.get("height"),
        "hash": block.get("hash"),
        "time": block.get("time"),
        "tx_count": tx_count,
        "size": block.get("size"),
        "difficulty": block.get("difficulty"),
        "nonce": block.get("nonce"),
        "bits": block.get("bits"),
        "merkleroot": block.get("merkleroot"),
        "previousblockhash": block.get("previousblockhash"),
        "nextblockhash": block.get("nextblockhash"),
    }


@api.route("/blocks")
def blocks():
    """Paginated list of block summaries, newest first.

    Query params: limit (1..50, default 15), offset (>=0, default 0)."""
    client = _client()
    try:
        limit = int(request.args.get("limit", 15))
    except (TypeError, ValueError):
        limit = 15
    try:
        offset = int(request.args.get("offset", 0))
    except (TypeError, ValueError):
        offset = 0
    limit = max(1, min(limit, 50))
    offset = max(0, offset)

    try:
        tip = client.getblockcount()
        top = tip - offset
        summaries = []
        for h in range(top, max(-1, top - limit), -1):
            block_hash = client.getblockhash(h)
            block = client.getblock(block_hash, 1)
            summaries.append(_block_summary(block))
    except RPCConnectionError as exc:
        return _err(str(exc), 503)
    except RPCError as exc:
        return _err(str(exc), 502)

    return jsonify({
        "blocks": summaries,
        "tip": tip,
        "total": tip + 1,
        "offset": offset,
        "limit": limit,
        "demo": client.is_demo(),
    })


@api.route("/block/<identifier>")
def block_json(identifier):
    """A single block (by height or hash) including its txids."""
    client = _client()
    key = identifier.strip()
    try:
        block_hash = client.getblockhash(int(key)) if key.isdigit() else key
        block = client.getblock(block_hash, 1)
    except RPCConnectionError as exc:
        return _err(str(exc), 503)
    except RPCError as exc:
        return _err("block not found", 404)

    summary = _block_summary(block)
    summary["tx"] = block.get("tx") or []
    summary["confirmations"] = block.get("confirmations")
    summary["demo"] = client.is_demo()
    return jsonify(summary)


@api.route("/search")
def search_json():
    """Resolve a query to a block or transaction. Returns {kind, id}."""
    client = _client()
    q = (request.args.get("q") or "").strip()
    if not q:
        return _err("empty search query", 400)

    # Integer -> block height.
    if q.isdigit():
        try:
            client.getblockhash(int(q))
            return jsonify({"kind": "block", "id": q, "demo": client.is_demo()})
        except (RPCError, RPCConnectionError):
            return _err("no block at that height", 404)

    # 64-char hex -> tx first, then block.
    if len(q) == 64 and all(c in "0123456789abcdefABCDEF" for c in q):
        ql = q.lower()
        try:
            client.getrawtransaction(ql, True)
            return jsonify({"kind": "tx", "id": ql, "demo": client.is_demo()})
        except (RPCError, RPCConnectionError):
            pass
        try:
            client.getblock(ql, 1)
            return jsonify({"kind": "block", "id": ql, "demo": client.is_demo()})
        except (RPCError, RPCConnectionError):
            pass

    return _err("no block or transaction matches that query", 404)


# ------------------------------------------------------------------------- #
# Webhooks. Registration is gated behind an API key so a public explorer is
# never turned into an open relay. Deletion requires the per-hook secret.
# ------------------------------------------------------------------------- #


def _require_api_key():
    """Return an error response if the request lacks a valid API key, else None."""
    if not config.WEBHOOKS_ENABLED:
        return _err("webhooks are disabled", 503)
    if not config.WEBHOOK_API_KEY:
        return _err("webhook registration is not configured", 503)
    provided = request.headers.get("X-API-Key", "")
    if not hmac.compare_digest(provided, config.WEBHOOK_API_KEY):
        return _err("missing or invalid API key", 401)
    return None


@api.route("/webhooks", methods=["POST"])
def webhooks_register():
    denied = _require_api_key()
    if denied is not None:
        return denied
    data = request.get_json(silent=True) or {}
    try:
        created = webhooks.register(
            url=data.get("url"),
            event=data.get("event"),
            address=data.get("address"),
        )
    except webhooks.WebhookError as exc:
        return _err(exc.message, exc.status)
    return jsonify(created), 201


@api.route("/webhooks/<hook_id>", methods=["GET"])
def webhooks_get(hook_id):
    hook = webhooks.get(hook_id.strip())
    if hook is None:
        return _err("webhook not found", 404)
    return jsonify(hook)


@api.route("/webhooks/<hook_id>", methods=["DELETE"])
def webhooks_delete(hook_id):
    # The secret authorises deletion; accept it via header or JSON body.
    secret = request.headers.get("X-Webhook-Secret", "")
    if not secret:
        data = request.get_json(silent=True) or {}
        secret = data.get("secret", "")
    try:
        ok = webhooks.delete(hook_id.strip(), secret)
    except webhooks.WebhookError as exc:
        return _err(exc.message, exc.status)
    if not ok:
        return _err("webhook not found", 404)
    return jsonify({"deleted": hook_id})

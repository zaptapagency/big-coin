"""BigCoin (BIG) block explorer -- Flask web app.

Talks to a Bitcoin/Litecoin-Core-style JSON-RPC daemon (bigcoind). Supports a
DEMO_MODE that serves realistic sample data so the explorer can be run and
demoed without a live chain.
"""
import datetime

from flask import Flask, abort, redirect, render_template, request, url_for

import config
from api import api as api_blueprint
from rpc import RpcClient, RPCConnectionError, RPCError

app = Flask(__name__)
app.register_blueprint(api_blueprint)


# --- Jinja filters -------------------------------------------------------

@app.template_filter("ts")
def fmt_timestamp(value):
    """Unix timestamp -> human readable UTC string."""
    if value in (None, ""):
        return "-"
    try:
        dt = datetime.datetime.utcfromtimestamp(int(value))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except (ValueError, OSError, OverflowError):
        return str(value)


@app.template_filter("since")
def fmt_since(value):
    """Unix timestamp -> '3 minutes ago' style relative string."""
    if value in (None, ""):
        return ""
    try:
        secs = int(datetime.datetime.utcnow().timestamp()) - int(value)
    except (ValueError, OSError, OverflowError):
        return ""
    if secs < 0:
        secs = 0
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if secs >= size:
            return f"{secs // size}{unit} ago"
    return f"{secs}s ago"


@app.template_filter("coin")
def fmt_coin(value):
    """Format a coin amount (already in BIG) with thousands separators."""
    try:
        return f"{float(value):,.8f}"
    except (ValueError, TypeError):
        return str(value)


@app.template_filter("short")
def fmt_short(value, head=10, tail=10):
    """Shorten a long hash for compact display."""
    if not value:
        return "-"
    s = str(value)
    if len(s) <= head + tail + 3:
        return s
    return f"{s[:head]}...{s[-tail:]}"


@app.template_filter("bytes")
def fmt_bytes(value):
    try:
        n = float(value)
    except (ValueError, TypeError):
        return str(value)
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1024


# --- Context ------------------------------------------------------------

@app.context_processor
def inject_globals():
    return {
        "COIN_NAME": config.COIN_NAME,
        "COIN_TICKER": config.COIN_TICKER,
    }


def new_client():
    return RpcClient()


# --- Helpers ------------------------------------------------------------

def tx_value_out(tx):
    """Sum of all output values in a transaction."""
    total = 0.0
    for vout in tx.get("vout", []):
        try:
            total += float(vout.get("value", 0))
        except (ValueError, TypeError):
            pass
    return total


def vout_address(vout):
    spk = vout.get("scriptPubKey", {}) or {}
    if spk.get("address"):
        return spk["address"]
    addrs = spk.get("addresses")
    if addrs:
        return ", ".join(addrs)
    return spk.get("type", "unknown")


def vin_address_value(vin):
    """Best-effort extract of (address, value) for an input using the
    'prevout' hint some nodes/indexes provide."""
    if "coinbase" in vin:
        return ("coinbase (newly generated coins)", None)
    prevout = vin.get("prevout") or {}
    val = prevout.get("value")
    spk = prevout.get("scriptPubKey", {}) or {}
    addr = None
    if spk.get("address"):
        addr = spk["address"]
    elif spk.get("addresses"):
        addr = ", ".join(spk["addresses"])
    if addr is None and vin.get("txid"):
        addr = f"{vin['txid'][:16]}...:{vin.get('vout')}"
    return (addr or "unknown", val)


# --- Routes -------------------------------------------------------------

@app.route("/")
def index():
    client = new_client()
    try:
        chaininfo = client.getblockchaininfo()
        mempool = client.getmempoolinfo()
        netinfo = client.getnetworkinfo()
        height = client.getblockcount()
    except RPCConnectionError as exc:
        return render_template("error.html", message=str(exc)), 503
    except RPCError as exc:
        return render_template("error.html", message=str(exc)), 502

    latest = []
    count = config.LATEST_BLOCKS
    for h in range(height, max(-1, height - count), -1):
        try:
            bh = client.getblockhash(h)
            blk = client.getblock(bh, 1)
            latest.append(blk)
        except (RPCError, RPCConnectionError):
            break

    summary = {
        "chain": chaininfo.get("chain", "?"),
        "blocks": chaininfo.get("blocks", height),
        "bestblockhash": chaininfo.get("bestblockhash", ""),
        "difficulty": chaininfo.get("difficulty", 0),
        "mempool_size": mempool.get("size", 0),
        "mempool_bytes": mempool.get("bytes", 0),
        "connections": netinfo.get("connections", "?"),
        "subversion": netinfo.get("subversion", ""),
        "verificationprogress": chaininfo.get("verificationprogress", 1.0),
    }
    return render_template(
        "index.html",
        summary=summary,
        blocks=latest,
        demo=client.is_demo(),
        demo_reason=client.demo_reason,
    )


@app.route("/block/<hash_or_height>")
def block(hash_or_height):
    client = new_client()
    key = hash_or_height.strip()
    try:
        if key.isdigit():
            block_hash = client.getblockhash(int(key))
        else:
            block_hash = key
        blk = client.getblock(block_hash, 1)
    except RPCConnectionError as exc:
        return render_template("error.html", message=str(exc)), 503
    except RPCError as exc:
        return render_template("notfound.html", query=key, kind="block", message=str(exc)), 404

    # Compute total output value across the block (best effort, may hit node).
    return render_template(
        "block.html",
        block=blk,
        demo=client.is_demo(),
        demo_reason=client.demo_reason,
    )


@app.route("/tx/<txid>")
def tx(txid):
    client = new_client()
    txid = txid.strip()
    try:
        transaction = client.getrawtransaction(txid, True)
    except RPCConnectionError as exc:
        return render_template("error.html", message=str(exc)), 503
    except RPCError as exc:
        return render_template(
            "notfound.html", query=txid, kind="transaction", message=str(exc)
        ), 404

    inputs = []
    total_in = 0.0
    have_all_inputs = True
    for vin in transaction.get("vin", []):
        addr, val = vin_address_value(vin)
        is_coinbase = "coinbase" in vin
        if val is not None:
            total_in += float(val)
        elif not is_coinbase:
            have_all_inputs = False
        inputs.append({"address": addr, "value": val, "coinbase": is_coinbase})

    outputs = []
    total_out = 0.0
    for vout in transaction.get("vout", []):
        addr = vout_address(vout)
        val = float(vout.get("value", 0) or 0)
        total_out += val
        outputs.append({"address": addr, "value": val, "n": vout.get("n")})

    fee = None
    if have_all_inputs and inputs and not any(i["coinbase"] for i in inputs):
        fee = max(0.0, total_in - total_out)

    return render_template(
        "tx.html",
        tx=transaction,
        inputs=inputs,
        outputs=outputs,
        total_in=total_in if have_all_inputs else None,
        total_out=total_out,
        fee=fee,
        demo=client.is_demo(),
        demo_reason=client.demo_reason,
    )


@app.route("/search")
def search():
    q = (request.args.get("q") or "").strip()
    if not q:
        return redirect(url_for("index"))

    client = new_client()

    # Integer -> block by height.
    if q.isdigit():
        return redirect(url_for("block", hash_or_height=q))

    # 64-char hex -> try tx first, then block.
    is_hex64 = len(q) == 64 and all(c in "0123456789abcdefABCDEF" for c in q)
    if is_hex64:
        ql = q.lower()
        try:
            client.getrawtransaction(ql, True)
            return redirect(url_for("tx", txid=ql))
        except (RPCError, RPCConnectionError):
            pass
        try:
            client.getblock(ql, 1)
            return redirect(url_for("block", hash_or_height=ql))
        except (RPCError, RPCConnectionError):
            pass

    return render_template("notfound.html", query=q, kind="anything", message=None), 404


@app.errorhandler(404)
def handle_404(_e):
    return render_template("notfound.html", query=request.path, kind="page", message=None), 404


if __name__ == "__main__":
    print(f"Starting {config.COIN_NAME} explorer on http://127.0.0.1:{config.EXPLORER_PORT}/")
    if config.DEMO_MODE:
        print("DEMO_MODE is ON (serving sample data).")
    else:
        print(f"Connecting to RPC at {config.rpc_url()} (falls back to DEMO_MODE if unreachable).")
    app.run(host="127.0.0.1", port=config.EXPLORER_PORT, debug=False)

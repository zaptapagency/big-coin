"""Webhook subscriptions + delivery for the MoonBite explorer.

A single background poller watches the chain tip and delivers signed HTTP
callbacks to subscribers:

  * event="new_block"  -> fired once per new block with a block summary.
  * event="address"    -> fired when a new block contains a tx that pays to
                          (or spends from) the subscribed address.

Design notes
------------
* Storage is stdlib ``sqlite3`` (no extra dependency). The DB path is
  ephemeral on Railway by default, which is fine for v1.
* Delivery is signed: each POST carries
  ``X-MoonBite-Signature: sha256=<hmac-sha256(secret, body)>`` so the receiver
  can verify authenticity. Failures back off and the hook auto-disables after
  ``WEBHOOK_MAX_FAILURES`` consecutive strikes.
* SSRF guard: callback URLs must be https and must not resolve to a private /
  loopback / link-local address unless ``WEBHOOK_ALLOW_PRIVATE`` is set.
* Single poller: gunicorn runs multiple workers, so the poller claims a lock
  row in SQLite (with a heartbeat) and only the holder polls. If the holder
  dies, another worker takes over once the lock goes stale.

This module never touches keys or signs coin transactions; it only reads chain
state over RPC and POSTs notifications.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
import sqlite3
import threading
import time
import urllib.error
import urllib.request
import uuid
from urllib.parse import urlparse

import config
from rpc import RpcClient, RPCConnectionError, RPCError

_VALID_EVENTS = ("new_block", "address")
_LOCK_STALE_SECONDS = 45  # a heartbeat older than this means the holder died.


# ------------------------------------------------------------------------- #
# Storage
# ------------------------------------------------------------------------- #

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.WEBHOOK_DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = _connect()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS webhooks (
                id            TEXT PRIMARY KEY,
                url           TEXT NOT NULL,
                event         TEXT NOT NULL,
                address       TEXT,
                secret        TEXT NOT NULL,
                active        INTEGER NOT NULL DEFAULT 1,
                failures      INTEGER NOT NULL DEFAULT 0,
                created       INTEGER NOT NULL,
                last_delivery INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS state (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS poller_lock (
                id        INTEGER PRIMARY KEY CHECK (id = 1),
                owner     TEXT,
                heartbeat INTEGER
            )
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO poller_lock (id, owner, heartbeat) VALUES (1, NULL, 0)"
        )
        conn.commit()
    finally:
        conn.close()


def _get_state(conn, key):
    row = conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def _set_state(conn, key, value):
    conn.execute(
        "INSERT INTO state (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )


# ------------------------------------------------------------------------- #
# Registration / management (called from the API layer)
# ------------------------------------------------------------------------- #

class WebhookError(Exception):
    """Registration/validation failure; carries an HTTP status."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def _validate_callback_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise WebhookError("callback url must be http or https")
    if not config.WEBHOOK_ALLOW_PRIVATE and parsed.scheme != "https":
        raise WebhookError("callback url must use https")
    host = parsed.hostname
    if not host:
        raise WebhookError("callback url has no host")
    if config.WEBHOOK_ALLOW_PRIVATE:
        return
    # Resolve every address the host maps to and reject anything non-public.
    try:
        infos = socket.getaddrinfo(host, parsed.port or None, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise WebhookError("callback host does not resolve")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            raise WebhookError("callback url must be a public address")


def register(url: str, event: str, address: str | None) -> dict:
    """Create a subscription. Returns {id, secret, ...}. Raises WebhookError."""
    url = (url or "").strip()
    event = (event or "").strip()
    address = (address or "").strip() or None

    if event not in _VALID_EVENTS:
        raise WebhookError(f"event must be one of {list(_VALID_EVENTS)}")
    if event == "address" and not address:
        raise WebhookError("event 'address' requires an 'address'")
    if not url:
        raise WebhookError("missing 'url'")
    _validate_callback_url(url)

    # Confirm the address is well-formed on the node (skipped in demo mode).
    if event == "address":
        client = RpcClient()
        if not client.is_demo():
            try:
                info = client.validateaddress(address)
                if not info.get("isvalid"):
                    raise WebhookError("invalid MoonBite address")
            except RPCConnectionError as exc:
                raise WebhookError(f"node unreachable: {exc}", 503)
            except RPCError as exc:
                raise WebhookError(str(exc), 502)

    conn = _connect()
    try:
        total = conn.execute("SELECT COUNT(*) AS c FROM webhooks").fetchone()["c"]
        if total >= config.WEBHOOK_MAX:
            raise WebhookError("webhook limit reached", 429)
        hook_id = uuid.uuid4().hex
        secret = secrets.token_hex(24)
        conn.execute(
            "INSERT INTO webhooks (id, url, event, address, secret, created) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (hook_id, url, event, address, secret, int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()

    return {"id": hook_id, "secret": secret, "url": url,
            "event": event, "address": address}


def get(hook_id: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id, url, event, address, active, failures, created, last_delivery "
            "FROM webhooks WHERE id = ?",
            (hook_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    d = dict(row)
    d["active"] = bool(d["active"])
    return d


def delete(hook_id: str, secret: str) -> bool:
    """Delete a subscription. Requires the secret issued at creation."""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT secret FROM webhooks WHERE id = ?", (hook_id,)
        ).fetchone()
        if not row:
            return False
        if not hmac.compare_digest(row["secret"], secret or ""):
            raise WebhookError("invalid secret", 403)
        conn.execute("DELETE FROM webhooks WHERE id = ?", (hook_id,))
        conn.commit()
    finally:
        conn.close()
    return True


# ------------------------------------------------------------------------- #
# Delivery
# ------------------------------------------------------------------------- #

def _deliver(hook: sqlite3.Row, payload: dict) -> bool:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = hmac.new(hook["secret"].encode(), body, hashlib.sha256).hexdigest()
    req = urllib.request.Request(hook["url"], data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "MoonBite-Webhooks/1.0")
    req.add_header("X-MoonBite-Event", payload.get("event", ""))
    req.add_header("X-MoonBite-Delivery", uuid.uuid4().hex)
    req.add_header("X-MoonBite-Signature", f"sha256={sig}")
    try:
        with urllib.request.urlopen(req, timeout=config.WEBHOOK_TIMEOUT) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as exc:
        return 200 <= exc.code < 300
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
        return False


def _record_result(conn, hook_id: str, ok: bool) -> None:
    if ok:
        conn.execute(
            "UPDATE webhooks SET failures = 0, last_delivery = ? WHERE id = ?",
            (int(time.time()), hook_id),
        )
    else:
        conn.execute(
            "UPDATE webhooks SET failures = failures + 1, "
            "active = CASE WHEN failures + 1 >= ? THEN 0 ELSE active END "
            "WHERE id = ?",
            (config.WEBHOOK_MAX_FAILURES, hook_id),
        )
    conn.commit()


def _fanout(conn, event: str, address: str | None, payload: dict) -> None:
    if address is None:
        rows = conn.execute(
            "SELECT * FROM webhooks WHERE active = 1 AND event = ?", (event,)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM webhooks WHERE active = 1 AND event = 'address' "
            "AND address = ?",
            (address,),
        ).fetchall()
    for hook in rows:
        ok = _deliver(hook, payload)
        _record_result(conn, hook["id"], ok)


# ------------------------------------------------------------------------- #
# Chain scanning
# ------------------------------------------------------------------------- #

def _block_summary(block: dict) -> dict:
    txids = block.get("tx") or []
    tx_count = block.get("nTx")
    if tx_count is None:
        tx_count = len(txids)
    return {
        "height": block.get("height"),
        "hash": block.get("hash"),
        "time": block.get("time"),
        "tx_count": tx_count,
        "size": block.get("size"),
        "previousblockhash": block.get("previousblockhash"),
    }


def _vout_addresses(vout: dict):
    spk = vout.get("scriptPubKey", {}) or {}
    if spk.get("address"):
        return [spk["address"]]
    return list(spk.get("addresses") or [])


def _vin_addresses(vin: dict):
    prevout = vin.get("prevout") or {}
    spk = prevout.get("scriptPubKey", {}) or {}
    if spk.get("address"):
        return [spk["address"]]
    return list(spk.get("addresses") or [])


def _process_block(conn, client: RpcClient, height: int) -> None:
    block_hash = client.getblockhash(height)
    # verbosity 2 embeds full tx data so we can scan without extra RPC calls.
    block = client.getblock(block_hash, 2)
    summary = _block_summary(block)

    _fanout(conn, "new_block", None, {
        "event": "new_block",
        "block": summary,
        "time": int(time.time()),
    })

    # Which addresses does *any* active subscription care about?
    watched = {
        row["address"]
        for row in conn.execute(
            "SELECT DISTINCT address FROM webhooks "
            "WHERE active = 1 AND event = 'address' AND address IS NOT NULL"
        ).fetchall()
    }
    if not watched:
        return

    txs = block.get("tx") or []
    for tx in txs:
        if not isinstance(tx, dict):
            continue  # verbosity<2 fell back to txids; skip address scan.
        received = {}
        for vout in tx.get("vout", []):
            val = float(vout.get("value", 0) or 0)
            for addr in _vout_addresses(vout):
                if addr in watched:
                    received[addr] = received.get(addr, 0.0) + val
        spent = set()
        for vin in tx.get("vin", []):
            for addr in _vin_addresses(vin):
                if addr in watched:
                    spent.add(addr)

        for addr in watched:
            got = received.get(addr)
            gave = addr in spent
            if got is None and not gave:
                continue
            direction = "both" if (got is not None and gave) else (
                "receive" if got is not None else "send")
            _fanout(conn, "address", addr, {
                "event": "address",
                "address": addr,
                "txid": tx.get("txid"),
                "direction": direction,
                "value": got,
                "block": {"height": summary["height"], "hash": summary["hash"],
                          "time": summary["time"]},
            })


# ------------------------------------------------------------------------- #
# Poller (single instance across workers via a SQLite lock)
# ------------------------------------------------------------------------- #

def _acquire_lock(conn, owner: str) -> bool:
    now = int(time.time())
    row = conn.execute(
        "SELECT owner, heartbeat FROM poller_lock WHERE id = 1"
    ).fetchone()
    holder, beat = row["owner"], row["heartbeat"] or 0
    if holder in (None, "", owner) or (now - beat) > _LOCK_STALE_SECONDS:
        # Claim only if the row still looks the way we just read it (optimistic).
        cur = conn.execute(
            "UPDATE poller_lock SET owner = ?, heartbeat = ? "
            "WHERE id = 1 AND (owner IS ? OR owner = ? OR heartbeat = ?)",
            (owner, now, holder, holder if holder else "", beat),
        )
        conn.commit()
        return cur.rowcount == 1
    return False


def _heartbeat(conn, owner: str) -> bool:
    now = int(time.time())
    cur = conn.execute(
        "UPDATE poller_lock SET heartbeat = ? WHERE id = 1 AND owner = ?",
        (now, owner),
    )
    conn.commit()
    return cur.rowcount == 1


def _poll_once(conn, client: RpcClient, owner: str) -> None:
    if not _heartbeat(conn, owner):
        # Lost the lock (another worker took over); try to reclaim next tick.
        if not _acquire_lock(conn, owner):
            return

    tip = client.getblockcount()
    last = _get_state(conn, "last_height")
    if last is None:
        # First run: start from the tip so we don't replay all of history.
        _set_state(conn, "last_height", tip)
        conn.commit()
        return
    last = int(last)
    if tip <= last:
        return

    start = last + 1
    if tip - last > config.WEBHOOK_MAX_CATCHUP:
        # Bound catch-up after a long outage; skip the older gap.
        start = tip - config.WEBHOOK_MAX_CATCHUP + 1
    for height in range(start, tip + 1):
        _process_block(conn, client, height)
        _set_state(conn, "last_height", height)
        conn.commit()


def _poller_loop() -> None:
    owner = uuid.uuid4().hex
    interval = max(2.0, config.WEBHOOK_POLL_INTERVAL)
    conn = _connect()
    try:
        _acquire_lock(conn, owner)
        while True:
            try:
                client = RpcClient()
                if client.is_demo():
                    # No live chain to watch; idle but keep the lock warm.
                    _heartbeat(conn, owner)
                else:
                    _poll_once(conn, client, owner)
            except (RPCError, RPCConnectionError):
                pass
            except Exception:
                # Never let the poller thread die on an unexpected error.
                pass
            time.sleep(interval)
    finally:
        conn.close()


_started = False
_start_lock = threading.Lock()


def start_poller() -> None:
    """Start the background poller once per process."""
    global _started
    if not config.WEBHOOKS_ENABLED:
        return
    with _start_lock:
        if _started:
            return
        init_db()
        thread = threading.Thread(target=_poller_loop, name="webhook-poller",
                                  daemon=True)
        thread.start()
        _started = True

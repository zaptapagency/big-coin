"""Configuration for the BigCoin block explorer.

All settings are read from environment variables so the explorer can be
pointed at any bigcoind instance without editing code.
"""
import os


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


# --- RPC connection settings (Bitcoin/Litecoin-Core style JSON-RPC) ---
RPC_HOST = os.environ.get("BIGCOIN_RPC_HOST", "127.0.0.1")
RPC_PORT = int(os.environ.get("BIGCOIN_RPC_PORT", "9445"))
RPC_USER = os.environ.get("BIGCOIN_RPC_USER", "")
RPC_PASSWORD = os.environ.get("BIGCOIN_RPC_PASSWORD", "")

# Full RPC URL override. When set (e.g. an HTTPS Cloudflare-tunnel host that
# fronts the read-only proxy), it takes precedence over HOST/PORT so the
# explorer can reach a remote node over https without editing code.
RPC_URL = os.environ.get("BIGCOIN_RPC_URL", "")

# Timeout (seconds) for RPC HTTP calls.
RPC_TIMEOUT = float(os.environ.get("BIGCOIN_RPC_TIMEOUT", "8"))

# --- Explorer / display settings ---
COIN_NAME = os.environ.get("BIGCOIN_NAME", "BigCoin")
COIN_TICKER = os.environ.get("BIGCOIN_TICKER", "BIG")

# Explorer web server port (chosen to avoid common collisions).
EXPLORER_PORT = int(os.environ.get("EXPLORER_PORT", "5055"))

# How many recent blocks to show on the home page.
LATEST_BLOCKS = int(os.environ.get("EXPLORER_LATEST_BLOCKS", "15"))

# --- Demo mode ---
# When DEMO_MODE=1 the explorer serves realistic fake sample data and never
# needs a running chain. When DEMO_MODE is unset, it defaults to ON only if
# the RPC node cannot be reached (handled in rpc.py).
DEMO_MODE = _env_bool("DEMO_MODE", default=False)

# Whether DEMO_MODE was explicitly requested by the user.
DEMO_MODE_EXPLICIT = os.environ.get("DEMO_MODE") is not None

# --- Browser-miner endpoint (POST /api/mine) ---
# Lets the Spark web page trigger real mining on the node (the node does the
# proof-of-work via generatetoaddress). Off unless MINING_ENABLED is truthy so a
# public explorer never mines unless the operator opts in.
MINING_ENABLED = _env_bool("MINING_ENABLED", default=False)
# PoW attempts the node makes per /api/mine call before returning (keep modest so
# the HTTP request returns promptly whether or not a block is found).
MINING_MAXTRIES = int(os.environ.get("MINING_MAXTRIES", "500000"))
# Cross-origin allow-list for the browser miner (the site is a different origin
# from the explorer). Comma-separated; "*" allows any origin.
MINING_CORS_ORIGINS = os.environ.get(
    "MINING_CORS_ORIGINS", "https://zaptapagency.github.io"
)


# --- Webhooks (POST /api/webhooks) ---
# A background poller watches the chain tip and delivers signed callbacks for
# 'new_block' and per-'address' activity. Registration requires an API key so a
# public explorer is never turned into an open relay; leave WEBHOOK_API_KEY
# unset to disable registration entirely.
WEBHOOKS_ENABLED = _env_bool("WEBHOOKS_ENABLED", default=True)
WEBHOOK_API_KEY = os.environ.get("WEBHOOK_API_KEY", "")
# Where the SQLite store lives (ephemeral on Railway's dyno disk by default).
WEBHOOK_DB_PATH = os.environ.get("WEBHOOK_DB_PATH", "webhooks.db")
# Seconds between chain-tip polls.
WEBHOOK_POLL_INTERVAL = float(os.environ.get("WEBHOOK_POLL_INTERVAL", "10"))
# Safety caps.
WEBHOOK_MAX = int(os.environ.get("WEBHOOK_MAX", "200"))
WEBHOOK_MAX_FAILURES = int(os.environ.get("WEBHOOK_MAX_FAILURES", "10"))
WEBHOOK_TIMEOUT = float(os.environ.get("WEBHOOK_TIMEOUT", "8"))
# Most blocks to walk forward in a single poll (bounds catch-up work after a
# long outage; older gaps are skipped rather than replayed).
WEBHOOK_MAX_CATCHUP = int(os.environ.get("WEBHOOK_MAX_CATCHUP", "50"))
# SSRF guard. By default callback URLs must be https and must not resolve to a
# private/loopback/link-local address. Set WEBHOOK_ALLOW_PRIVATE=1 for local
# testing (permits http + private IPs).
WEBHOOK_ALLOW_PRIVATE = _env_bool("WEBHOOK_ALLOW_PRIVATE", default=False)


def rpc_url() -> str:
    return RPC_URL if RPC_URL else f"http://{RPC_HOST}:{RPC_PORT}/"

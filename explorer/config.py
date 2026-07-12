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


def rpc_url() -> str:
    return f"http://{RPC_HOST}:{RPC_PORT}/"

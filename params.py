"""MyCoin — central consensus parameters.

Collecting every consensus-critical constant in one module keeps them from
drifting apart across files and makes the network's rules auditable at a glance.
Changing any value here is a hard fork: nodes on different values will reject
each other's blocks.
"""

from __future__ import annotations

# --- monetary policy ------------------------------------------------------- #
CENTS_PER_COIN = 100_000_000          # smallest unit; 1 coin = 100,000,000 cents
INITIAL_SUBSIDY = 50 * CENTS_PER_COIN  # block reward at height 0
HALVING_INTERVAL = 210_000            # halve the subsidy every N blocks
MAX_SUPPLY = 42_000_000 * CENTS_PER_COIN
MAX_MONEY = MAX_SUPPLY                 # no single value may exceed the cap

# --- proof-of-work / timing ------------------------------------------------ #
TARGET_BLOCK_TIME = 600               # seconds between blocks (10 minutes)
RETARGET_INTERVAL = 2016              # recompute difficulty every N blocks
MIN_BITS = 1
MAX_BITS = 240                        # keep below 256 so a target always exists

# --- block / consensus limits ---------------------------------------------- #
MAX_BLOCK_BYTES = 1_000_000           # serialized block size ceiling (~1 MB)
MAX_FUTURE_TIME = 2 * 60 * 60         # reject headers >2h ahead of local clock
MEDIAN_TIME_SPAN = 11                 # window for median-time-past lower bound
COINBASE_MATURITY = 100               # blocks a coinbase must age before spending

# --- genesis --------------------------------------------------------------- #
GENESIS_BITS = 16                     # easy difficulty for a local network
GENESIS_TIMESTAMP = 1_700_000_000
GENESIS_MINER_PKH = "0" * 64          # unspendable placeholder recipient

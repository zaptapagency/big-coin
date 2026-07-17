#!/usr/bin/env bash
# Entrypoint for the MoonBite seed node on Railway.
#
# Data lives on a Railway Volume mounted at /data (set the Volume mount path
# to /data in the service settings so the chain survives restarts/redeploys).
#
# RPC credentials come from Railway service Variables:
#   MOONBITE_RPC_USER, MOONBITE_RPC_PASSWORD   (required)
#   MINE=1                                    (optional: mine blocks on this node)
#   MINE_ADDRESS=<moonbite address>           (optional: where mined coins go)
set -euo pipefail

DATADIR=/data
mkdir -p "$DATADIR"

: "${MOONBITE_RPC_USER:?set MOONBITE_RPC_USER in Railway Variables}"
: "${MOONBITE_RPC_PASSWORD:?set MOONBITE_RPC_PASSWORD in Railway Variables}"

# P2P is public (via Railway TCP Proxy on 9444).
# RPC (9445) is bound so the internal explorer service can reach it over
# Railway's private network. Keep 9444 as the ONLY public domain/proxy;
# never attach a public domain to 9445.
ARGS=(
  -datadir="$DATADIR"
  -server=1
  -txindex=1
  -listen=1
  -bind=0.0.0.0:9444
  -rpcbind=0.0.0.0
  -rpcbind=::
  -rpcallowip=0.0.0.0/0
  -rpcallowip=::/0
  -rpcport=9445
  -rpcuser="$MOONBITE_RPC_USER"
  -rpcpassword="$MOONBITE_RPC_PASSWORD"
  -printtoconsole
)

# Optional: advertise the public P2P address so peers can dial back in.
if [[ -n "${EXTERNAL_IP:-}" ]]; then
  ARGS+=( -externalip="$EXTERNAL_IP" -discover=0 )
fi

echo "Starting moonbited (MoonBite seed node) ..."
moonbited "${ARGS[@]}" &
NODE_PID=$!

# Optional built-in miner so the fresh chain actually produces blocks.
# A brand-new chain with zero miners stays at height 0 forever.
if [[ "${MINE:-0}" == "1" ]]; then
  echo "MINE=1 -> will mine to ${MINE_ADDRESS:-<new wallet address>}"
  (
    # Wait for RPC to come up.
    until moonbite-cli -datadir="$DATADIR" -rpcport=9445 \
        -rpcuser="$MOONBITE_RPC_USER" -rpcpassword="$MOONBITE_RPC_PASSWORD" \
        getblockchaininfo >/dev/null 2>&1; do
      sleep 2
    done

    mcli() {
      moonbite-cli -datadir="$DATADIR" -rpcport=9445 \
        -rpcuser="$MOONBITE_RPC_USER" -rpcpassword="$MOONBITE_RPC_PASSWORD" "$@"
    }

    ADDR="${MINE_ADDRESS:-}"
    if [[ -z "$ADDR" ]]; then
      # First boot: create the "miner" wallet. On every later restart the wallet
      # already exists on the /data volume but Core does NOT auto-load it, so
      # createwallet fails and we must loadwallet instead. Try both (ignoring the
      # "already exists / already loaded" errors) so the wallet is loaded in all
      # three states: absent, present-unloaded, present-loaded.
      mcli createwallet miner >/dev/null 2>&1 || true
      mcli loadwallet miner   >/dev/null 2>&1 || true

      # Do not start mining until we actually hold an address; a blank ADDR makes
      # every generatetoaddress call fail silently and the chain never advances.
      for _ in $(seq 1 15); do
        ADDR=$(mcli getnewaddress 2>/dev/null || true)
        [[ -n "$ADDR" ]] && break
        mcli loadwallet miner >/dev/null 2>&1 || true
        sleep 2
      done
      echo "Mining to new wallet address: ${ADDR:-<none: wallet load failed>}"
    fi

    if [[ -z "$ADDR" ]]; then
      echo "Mining disabled: could not obtain a wallet address. Node stays up."
      exit 0
    fi

    # Auto-stop after MINE_BLOCKS blocks (default 20) so a test run cannot
    # drain Railway credit. Set MINE_BLOCKS=0 to mine indefinitely.
    TARGET="${MINE_BLOCKS:-20}"
    HEIGHT=$(moonbite-cli -datadir="$DATADIR" -rpcport=9445 \
      -rpcuser="$MOONBITE_RPC_USER" -rpcpassword="$MOONBITE_RPC_PASSWORD" \
      getblockcount 2>/dev/null || echo 0)
    STOP_AT=$(( HEIGHT + TARGET ))
    echo "Mining test: current height $HEIGHT, will mine to $STOP_AT then stop."

    # Slow, steady mining loop (1 block attempt every few seconds) so we don't
    # peg the container CPU. RandomX is CPU-heavy; keep the batch small.
    while kill -0 "$NODE_PID" 2>/dev/null; do
      moonbite-cli -datadir="$DATADIR" -rpcport=9445 \
        -rpcuser="$MOONBITE_RPC_USER" -rpcpassword="$MOONBITE_RPC_PASSWORD" \
        generatetoaddress 1 "$ADDR" >/dev/null 2>&1 || true

      if [[ "$TARGET" != "0" ]]; then
        HEIGHT=$(moonbite-cli -datadir="$DATADIR" -rpcport=9445 \
          -rpcuser="$MOONBITE_RPC_USER" -rpcpassword="$MOONBITE_RPC_PASSWORD" \
          getblockcount 2>/dev/null || echo "$HEIGHT")
        if (( HEIGHT >= STOP_AT )); then
          echo "=========================================================="
          echo " TEST COMPLETE: mined $TARGET blocks, height is now $HEIGHT."
          echo " Mining stopped to save credit. Node still running (idle)."
          echo " Pause this Railway service now to stop all spending."
          echo "=========================================================="
          break
        fi
      fi
      sleep 5
    done
  ) &
fi

wait "$NODE_PID"

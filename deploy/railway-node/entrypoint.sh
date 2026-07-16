#!/usr/bin/env bash
# Entrypoint for the MoonBite seed node on Railway.
#
# Data lives on a Railway Volume mounted at /data (set the Volume mount path
# to /data in the service settings so the chain survives restarts/redeploys).
#
# RPC credentials come from Railway service Variables:
#   BIGCOIN_RPC_USER, BIGCOIN_RPC_PASSWORD   (required)
#   MINE=1                                    (optional: mine blocks on this node)
#   MINE_ADDRESS=<moonbite address>           (optional: where mined coins go)
set -euo pipefail

DATADIR=/data
mkdir -p "$DATADIR"

: "${BIGCOIN_RPC_USER:?set BIGCOIN_RPC_USER in Railway Variables}"
: "${BIGCOIN_RPC_PASSWORD:?set BIGCOIN_RPC_PASSWORD in Railway Variables}"

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
  -rpcuser="$BIGCOIN_RPC_USER"
  -rpcpassword="$BIGCOIN_RPC_PASSWORD"
  -printtoconsole
)

# Optional: advertise the public P2P address so peers can dial back in.
if [[ -n "${EXTERNAL_IP:-}" ]]; then
  ARGS+=( -externalip="$EXTERNAL_IP" -discover=0 )
fi

echo "Starting bigcoind (MoonBite seed node) ..."
bigcoind "${ARGS[@]}" &
NODE_PID=$!

# Optional built-in miner so the fresh chain actually produces blocks.
# A brand-new chain with zero miners stays at height 0 forever.
if [[ "${MINE:-0}" == "1" ]]; then
  echo "MINE=1 -> will mine to ${MINE_ADDRESS:-<new wallet address>}"
  (
    # Wait for RPC to come up.
    until bigcoin-cli -datadir="$DATADIR" -rpcport=9445 \
        -rpcuser="$BIGCOIN_RPC_USER" -rpcpassword="$BIGCOIN_RPC_PASSWORD" \
        getblockchaininfo >/dev/null 2>&1; do
      sleep 2
    done

    ADDR="${MINE_ADDRESS:-}"
    if [[ -z "$ADDR" ]]; then
      bigcoin-cli -datadir="$DATADIR" -rpcport=9445 \
        -rpcuser="$BIGCOIN_RPC_USER" -rpcpassword="$BIGCOIN_RPC_PASSWORD" \
        createwallet miner >/dev/null 2>&1 || true
      ADDR=$(bigcoin-cli -datadir="$DATADIR" -rpcport=9445 \
        -rpcuser="$BIGCOIN_RPC_USER" -rpcpassword="$BIGCOIN_RPC_PASSWORD" \
        getnewaddress)
      echo "Mining to new wallet address: $ADDR"
    fi

    # Auto-stop after MINE_BLOCKS blocks (default 20) so a test run cannot
    # drain Railway credit. Set MINE_BLOCKS=0 to mine indefinitely.
    TARGET="${MINE_BLOCKS:-20}"
    HEIGHT=$(bigcoin-cli -datadir="$DATADIR" -rpcport=9445 \
      -rpcuser="$BIGCOIN_RPC_USER" -rpcpassword="$BIGCOIN_RPC_PASSWORD" \
      getblockcount 2>/dev/null || echo 0)
    STOP_AT=$(( HEIGHT + TARGET ))
    echo "Mining test: current height $HEIGHT, will mine to $STOP_AT then stop."

    # Slow, steady mining loop (1 block attempt every few seconds) so we don't
    # peg the container CPU. RandomX is CPU-heavy; keep the batch small.
    while kill -0 "$NODE_PID" 2>/dev/null; do
      bigcoin-cli -datadir="$DATADIR" -rpcport=9445 \
        -rpcuser="$BIGCOIN_RPC_USER" -rpcpassword="$BIGCOIN_RPC_PASSWORD" \
        generatetoaddress 1 "$ADDR" >/dev/null 2>&1 || true

      if [[ "$TARGET" != "0" ]]; then
        HEIGHT=$(bigcoin-cli -datadir="$DATADIR" -rpcport=9445 \
          -rpcuser="$BIGCOIN_RPC_USER" -rpcpassword="$BIGCOIN_RPC_PASSWORD" \
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

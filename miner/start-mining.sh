#!/usr/bin/env bash
# MoonBite one-click CPU miner (Linux / macOS / WSL).
# Prompts for your reward address + node RPC details, then mines.
set -euo pipefail

echo "================================================================"
echo "  MoonBite CPU Miner"
echo "================================================================"
echo

if [[ -z "${MINE_ADDRESS:-}" ]]; then
  read -rp "Your MoonBite reward address (moon1... or M...): " MINE_ADDRESS
fi
if [[ -z "${MINE_ADDRESS:-}" ]]; then
  echo "No address entered. Exiting."
  exit 1
fi

if [[ -z "${BIGCOIN_RPC_HOST:-}" ]]; then
  read -rp "Node RPC host [127.0.0.1]: " BIGCOIN_RPC_HOST
  BIGCOIN_RPC_HOST="${BIGCOIN_RPC_HOST:-127.0.0.1}"
fi
if [[ -z "${BIGCOIN_RPC_PORT:-}" ]]; then
  read -rp "Node RPC port [9445]: " BIGCOIN_RPC_PORT
  BIGCOIN_RPC_PORT="${BIGCOIN_RPC_PORT:-9445}"
fi
if [[ -z "${BIGCOIN_RPC_USER:-}" ]]; then
  read -rp "RPC username: " BIGCOIN_RPC_USER
fi
if [[ -z "${BIGCOIN_RPC_PASSWORD:-}" ]]; then
  read -rsp "RPC password: " BIGCOIN_RPC_PASSWORD
  echo
fi

export MINE_ADDRESS BIGCOIN_RPC_HOST BIGCOIN_RPC_PORT BIGCOIN_RPC_USER BIGCOIN_RPC_PASSWORD

echo
echo "Starting miner -> ${BIGCOIN_RPC_HOST}:${BIGCOIN_RPC_PORT}  reward ${MINE_ADDRESS}"
echo "Press Ctrl+C to stop."
echo

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python
exec "$PY" "$(dirname "$0")/moonbite_miner.py" --address "$MINE_ADDRESS"

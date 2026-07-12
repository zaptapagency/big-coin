#!/usr/bin/env bash
# ============================================================================
# BigCoin seed-node provisioner for a fresh Ubuntu 22.04 VPS.
# Run as root:   sudo bash setup-seednode.sh /path/to/bigcoind /path/to/bigcoin-cli
# Installs binaries, creates a dedicated user, config, systemd service, firewall.
# ============================================================================
set -euo pipefail

BIGCOIND_SRC="${1:-./bigcoind}"
BIGCOINCLI_SRC="${2:-./bigcoin-cli}"

echo "==> [1/7] Sanity checks"
[ "$(id -u)" -eq 0 ] || { echo "Run as root (sudo)."; exit 1; }
[ -f "$BIGCOIND_SRC" ] || { echo "bigcoind not found at $BIGCOIND_SRC"; exit 1; }
[ -f "$BIGCOINCLI_SRC" ] || { echo "bigcoin-cli not found at $BIGCOINCLI_SRC"; exit 1; }

echo "==> [2/7] Install runtime deps"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq libboost-system1.74.0 libboost-filesystem1.74.0 \
    libboost-thread1.74.0 libevent-2.1-7 libevent-pthreads-2.1-7 \
    libdb5.3++ libminiupnpc17 libnatpmp1 libzmq5 libfmt8 ufw >/dev/null 2>&1 || true

echo "==> [3/7] Install binaries to /usr/local/bin"
install -m 0755 "$BIGCOIND_SRC"   /usr/local/bin/bigcoind
install -m 0755 "$BIGCOINCLI_SRC" /usr/local/bin/bigcoin-cli

echo "==> [4/7] Create bigcoin user + directories"
id -u bigcoin >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin bigcoin
install -d -o bigcoin -g bigcoin -m 0750 /var/lib/bigcoin
install -d -m 0755 /etc/bigcoin

echo "==> [5/7] Install config (generates random RPC credentials)"
RPCUSER="big_$(head -c6 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9')"
RPCPASS="$(head -c48 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9')"
if [ ! -f /etc/bigcoin/bigcoin.conf ]; then
  sed -e "s/CHANGE_ME_user/${RPCUSER}/" \
      -e "s/CHANGE_ME_LONG_RANDOM_64_CHARS/${RPCPASS}/" \
      "$(dirname "$0")/bigcoin.conf" > /etc/bigcoin/bigcoin.conf
  chown root:bigcoin /etc/bigcoin/bigcoin.conf
  chmod 0640 /etc/bigcoin/bigcoin.conf
  echo "    Generated RPC user: ${RPCUSER}  (password stored in /etc/bigcoin/bigcoin.conf)"
else
  echo "    /etc/bigcoin/bigcoin.conf already exists — left untouched."
fi

echo "==> [6/7] Install systemd service"
install -m 0644 "$(dirname "$0")/bigcoind.service" /etc/systemd/system/bigcoind.service
systemctl daemon-reload
systemctl enable bigcoind
systemctl restart bigcoind

echo "==> [7/7] Firewall: open P2P 9444, keep RPC private"
ufw allow 9444/tcp comment "BigCoin P2P" >/dev/null 2>&1 || true
ufw --force enable >/dev/null 2>&1 || true

echo
echo "Done. Check status with:  systemctl status bigcoind"
echo "Tail logs with:           journalctl -u bigcoind -f"
echo "Query the node with:      bigcoin-cli -conf=/etc/bigcoin/bigcoin.conf getpeerinfo"
echo
echo "Report this host's PUBLIC IP to the other seed operators, and add it to"
echo "chainparams.cpp vSeeds / vFixedSeeds before mainnet launch."

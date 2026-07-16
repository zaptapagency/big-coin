#!/usr/bin/env bash
# ============================================================
#  MoonBite instant miner (macOS / Linux one-click)
#  Run this, paste your address, and mine the live MoonBite
#  chain. Needs Python 3 and moonbite-miner.py in the same
#  folder.
#
#  First time on macOS/Linux, make it runnable:
#     chmod +x mine-moonbite.sh
#  Then:
#     ./mine-moonbite.sh
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo
  echo " Python 3 is not installed."
  echo " macOS:  brew install python   (or install from python.org)"
  echo " Linux:  sudo apt install python3   (Debian/Ubuntu)"
  echo
  exit 1
fi

if [ ! -f "moonbite-miner.py" ]; then
  echo
  echo " moonbite-miner.py was not found next to this launcher."
  echo " Keep both files in the same folder."
  echo
  exit 1
fi

echo "============================================================"
echo "  MoonBite instant miner"
echo "============================================================"
echo
read -r -p "Paste your MoonBite reward address (moon1... or M...): " ADDR
if [ -z "${ADDR}" ]; then
  echo " No address entered. Exiting."
  exit 1
fi

echo
echo " Starting miner. Press Ctrl+C to stop."
echo
exec python3 moonbite-miner.py --address "${ADDR}"

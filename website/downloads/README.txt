MoonBite miners — quick start
=============================

Three ways to mine the live MoonBite (MBITE) chain. All of them mine to an
address you choose; the node does the real proof-of-work.

1) BROWSER MINER (nothing to install)
   Open:  https://zaptapagency.github.io/big-coin/spark.html
   Paste your address, click "Mine a block". Done.

2) INSTANT MINER (one-click desktop)
   - Windows:      double-click  Mine-MoonBite.bat
   - macOS/Linux:  run           ./mine-moonbite.sh   (chmod +x it first)
   Paste your address when asked. Keep moonbite-miner.py in the same folder.

3) DESKTOP MINER (command line, full control)
   python moonbite-miner.py --address YOUR_ADDRESS
   Options:
     --address   MoonBite address to receive rewards (required)
     --explorer  explorer URL (defaults to the live chain)
     --rounds    stop after N blocks (default 0 = forever)
     --sleep     seconds between rounds (default 0)

Requirements: Python 3 for options 2 and 3. Nothing for the browser miner.

Notes
-----
- You need a MoonBite address (moon1... or M...). Create one with your wallet
  or a node:  moonbite-cli getnewaddress
- The mining endpoint must be enabled on the explorer (operator sets
  MINING_ENABLED=1). If you see "mining endpoint is disabled", the operator
  has not turned it on yet.
- No coins have market value pre-mainnet. This is for testing the network.

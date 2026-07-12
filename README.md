# Big Coin (BIG)

**A fast, open, mineable Scrypt proof-of-work cryptocurrency** — forked from battle-tested Litecoin / Bitcoin Core. 2.5-minute blocks, an 84,000,000 hard-cap supply, and a fair launch. Mine it with a CPU or GPU; hold it in a non-custodial wallet.

> ⚠️ **Experimental software.** Big Coin is a community/experimental cryptocurrency, not an investment or a security. It has not had a production security audit. Verify all software before use and only participate with what you can afford to lose.

---

## Network parameters

| Parameter | Value |
| --- | --- |
| Ticker | **BIG** |
| Algorithm | **Scrypt** `scrypt(1024, 1, 1)` (Proof-of-Work) |
| Max supply | **84,000,000 BIG** |
| Initial block reward | 50 BIG |
| Halving interval | every 840,000 blocks (~4 years) |
| Target block time | 2.5 minutes (150 s) |
| Difficulty retarget | every 2,016 blocks (~3.5 days) |
| Address format | bech32 `big1…` (mainnet) / `tbig1…` (testnet) |
| Mainnet P2P port | 9444 |
| RPC port | 9445 |

Because Big Coin uses **Scrypt** (like Litecoin/Dogecoin), it **cannot** be mined with Bitcoin's SHA-256 ASICs — use a Scrypt-capable miner.

---

## What's in this repository

Big Coin's production chain is a **Litecoin Core v0.21.5.5 C++ fork** (the daemon/wallet binaries are published under [`release/`](release/)). This repo also holds the full supporting ecosystem:

| Folder | What it is |
| --- | --- |
| [`explorer/`](explorer/) | **Block explorer** — a Flask web app (JSON-RPC to `bigcoind`, with a demo mode). Railway-ready. |
| [`website/`](website/) | Marketing website (static HTML/CSS/JS). Deploys to GitHub Pages. |
| [`mobile/`](mobile/) | Flutter wallet app. |
| [`docs/`](docs/) | Guides: [Mining](docs/MINING.md), [Wallet](docs/WALLET.md), [Node setup](docs/NODE_SETUP.md), [Exchange listing](docs/EXCHANGE_LISTING.md). |
| [`deploy/`](deploy/) | Seed-node kit: `systemd` unit, `bigcoin.conf`, and `setup-seednode.sh`. |
| [`release/`](release/) | Packaged binaries manifest + `SHA256SUMS` + sample config. |

In addition, the repository root contains a **from-scratch Python reference implementation** of a Bitcoin-style coin (`block.py`, `transaction.py`, `pow.py`, `node.py`, `wallet.py`, `utxo.py`, `spv.py`, …) with a full test suite — the educational origin of the project.

---

## Quick start

### Mine on testnet
See [`docs/MINING.md`](docs/MINING.md). In short: run `bigcoind`, point a Scrypt miner (cpuminer / ccminer / sgminer) at a stratum bridge or pool, and mine to a Big Coin address.

### Run the block explorer locally
```bash
cd explorer
pip install -r requirements.txt
DEMO_MODE=1 python app.py        # serves sample data at http://127.0.0.1:5055
```
To point it at a real node, unset `DEMO_MODE` and set `BIGCOIN_RPC_HOST/PORT/USER/PASSWORD`. Deployment config for **Railway** (`Procfile`, `railway.json`, `runtime.txt`) is included.

### Run the Python reference implementation
```bash
pip install -r requirements.txt
python -m pytest -q
```

---

## Disclaimer

Big Coin is experimental, open-source software provided with **no warranties**. Nothing in this repository is financial advice. Cryptocurrency involves risk. Always verify checksums and signatures before running any binary.

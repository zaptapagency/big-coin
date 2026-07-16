# MoonBite Miners

Three ways to mine MoonBite (MBITE). Pick the one that fits you.

| Miner | What it is | Real PoW? | Where |
|---|---|---|---|
| **Instant** | Regtest — blocks appear immediately, for testing | node-side, trivial difficulty | `deploy/railway-node/entrypoint.sh` (`MINE=1`) |
| **Normal (CPU)** | Solo mine a real chain from your PC | ✅ yes, node does the work | this folder |
| **Browser (Spark)** | Mine from a web page / phone | ✅ yes — see note | `website/spark.html` |

---

## Normal CPU miner (this folder)

Real solo mining against a MoonBite node. The node does the proof-of-work via
`generatetoaddress`, so blocks you find are real and the reward goes to your
address. On a new / low-difficulty network this finds blocks quickly.

### Requirements
- Python 3 (no extra packages)
- A reachable MoonBite node RPC (your own local `bigcoind`, or any node whose
  RPC you can reach). **The public Railway node keeps RPC private**, so for the
  CPU miner run your own node locally (WSL) or point at one you control.

### Run it

**Windows:** double-click `START_MINING.bat`, answer the prompts.

**Linux / macOS / WSL:**
```bash
chmod +x start-mining.sh
./start-mining.sh
```

**Or directly:**
```bash
python moonbite_miner.py \
  --address moon1youraddresshere \
  --rpc-host 127.0.0.1 --rpc-port 9445 \
  --rpc-user moonrpc --rpc-pass yourpassword
```

Get a reward address from your wallet, or:
```bash
bigcoin-cli getnewaddress
```

Stop any time with **Ctrl+C**.

### Options
| Flag | Default | Meaning |
|---|---|---|
| `--address` | — (required) | address that receives block rewards |
| `--rpc-host` | `127.0.0.1` | node RPC host (env `BIGCOIN_RPC_HOST`) |
| `--rpc-port` | `9445` | node RPC port (env `BIGCOIN_RPC_PORT`) |
| `--rpc-user` / `--rpc-pass` | — | RPC auth (env `BIGCOIN_RPC_USER` / `_PASSWORD`) |
| `--maxtries` | `1000000` | PoW attempts per round |
| `--blocks` | `0` | stop after N blocks (0 = forever) |

> `generatetoaddress` mines single-threaded inside the node. For heavy
> multi-core mining on a high-difficulty chain you'd use an external miner via
> `getblocktemplate`; for launching/testing a fresh network this simple path is
> real and sufficient.

---

## Browser miner (Spark)

`website/spark.html` has two modes:

1. **Local rehearsal** (always available, no node) — an honest CPU throughput
   probe so you can see exactly what runs before it runs. Earns nothing.
2. **Mine the live chain** — enter your MoonBite address and the page asks the
   **explorer** to mine a block to you. The explorer reaches the node's private
   RPC over Railway's internal network and calls `generatetoaddress`, so a real
   block is produced and credited to your address.

> **Honest note:** in "mine the live chain" mode the heavy proof-of-work runs on
> the **node** (server-side), triggered from your browser. A full in-browser
> WASM RandomX hasher is a separate, larger piece of work; this gives you real,
> credited blocks today without pretending your phone did the RandomX math.

To enable live mode, the Spark page needs your explorer's URL — paste it into
the field on the page (it's remembered in your browser), or append
`?api=https://your-explorer.up.railway.app` to the Spark URL.

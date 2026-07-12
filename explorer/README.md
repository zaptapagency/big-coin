# BigCoin (BIG) Block Explorer

A lightweight, dark-themed web block explorer for **BigCoin** — a
Litecoin/Bitcoin-Core fork. It talks to a `bigcoind` daemon over the standard
Bitcoin-style JSON-RPC interface (the same methods as Bitcoin/Litecoin Core:
`getblockchaininfo`, `getblockcount`, `getblockhash`, `getblock`,
`getrawtransaction`, `getmempoolinfo`, `getrawmempool`, `getnetworkinfo`).

Built with Flask. The RPC client uses only the Python standard library
(`urllib`), so the only dependency is Flask itself.

## Features

- **Home** — node/chain summary (chain, height, best block hash, difficulty,
  mempool size, connections) plus the latest ~15 blocks.
- **Block page** (`/block/<hashOrHeight>`) — full block details and a linked
  list of transaction IDs.
- **Transaction page** (`/tx/<txid>`) — decoded inputs and outputs (address +
  value), size, confirmations, and computed fee where possible.
- **Search box** — routes an integer to a block height, a 64-hex string to a
  transaction (then a block), otherwise shows a friendly "not found" page.
- **DEMO_MODE** — serves realistic sample data so the explorer renders and can
  be demoed with no running chain.
- Responsive dark UI, monospace hashes, human-readable timestamps and BIG
  amounts.

## Requirements

- Python 3.8+
- Flask (`pip install -r requirements.txt`)

## Configuration (environment variables)

| Variable                | Default     | Purpose                              |
|-------------------------|-------------|--------------------------------------|
| `BIGCOIN_RPC_HOST`      | `127.0.0.1` | bigcoind RPC host                    |
| `BIGCOIN_RPC_PORT`      | `9445`      | bigcoind RPC port                    |
| `BIGCOIN_RPC_USER`      | *(empty)*   | RPC username (`rpcuser`)             |
| `BIGCOIN_RPC_PASSWORD`  | *(empty)*   | RPC password (`rpcpassword`)         |
| `BIGCOIN_RPC_TIMEOUT`   | `8`         | RPC HTTP timeout (seconds)           |
| `DEMO_MODE`             | *(auto)*    | `1` forces sample data; unset = auto |
| `EXPLORER_PORT`         | `5055`      | Web server port                      |
| `EXPLORER_LATEST_BLOCKS`| `15`        | Blocks shown on the home page        |

## Running against a live node

```bash
pip install -r requirements.txt

export BIGCOIN_RPC_HOST=127.0.0.1
export BIGCOIN_RPC_PORT=9445
export BIGCOIN_RPC_USER=yourrpcuser
export BIGCOIN_RPC_PASSWORD=yourrpcpassword

python app.py
```

Then open <http://127.0.0.1:5055/>.

Your `bigcoin.conf` should enable the RPC server, e.g.:

```
server=1
rpcuser=yourrpcuser
rpcpassword=yourrpcpassword
rpcport=9445
rpcallowip=127.0.0.1
```

## DEMO_MODE

The explorer ships with a small, realistic in-memory sample chain (a dozen
blocks plus coinbase and payment transactions, and a couple of mempool
transactions) shaped exactly like real JSON-RPC output.

- **Force it on:** `DEMO_MODE=1 python app.py` — never contacts a node.
- **Automatic fallback:** if `DEMO_MODE` is *unset* and the node is
  unreachable, the explorer automatically switches to demo data so it still
  renders (a banner explains why).
- **Disable fallback:** `DEMO_MODE=0` — if the node is unreachable you get a
  friendly "cannot reach BigCoin node" page instead of fake data.

Quick demo:

```bash
DEMO_MODE=1 python app.py
# then visit http://127.0.0.1:5055/
```

## Project layout

```
explorer/
├── app.py            # Flask app + routes + template filters
├── rpc.py            # JSON-RPC client (urllib) with DEMO_MODE fallback
├── config.py         # env-driven configuration
├── demo_data.py      # sample blockchain for DEMO_MODE
├── requirements.txt
├── templates/        # base, index, block, tx, notfound, error
└── static/style.css  # dark explorer theme
```

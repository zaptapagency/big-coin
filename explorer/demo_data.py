"""Realistic fake sample data for DEMO_MODE.

Provides a small in-memory blockchain (a handful of blocks + transactions)
shaped exactly like the JSON that bigcoind's JSON-RPC returns, so every
explorer page renders without a live chain.
"""
import time

# A fixed base time so timestamps look sensible and stable.
_BASE_TIME = 1_752_000_000  # ~ mid 2025


def _h(n: int) -> str:
    """Deterministic 64-hex 'hash' derived from an integer seed."""
    import hashlib

    return hashlib.sha256(f"bigcoin-demo-{n}".encode()).hexdigest()


# --- Transactions --------------------------------------------------------
# Each tx is shaped like getrawtransaction verbose=true output.

def _coinbase_tx(height: int, reward: float, block_hash: str, confirmations: int):
    txid = _h(1000 + height)
    return {
        "txid": txid,
        "hash": txid,
        "version": 2,
        "size": 190,
        "vsize": 163,
        "weight": 652,
        "locktime": 0,
        "vin": [
            {
                "coinbase": f"03{height:06x}0442414c4c",
                "sequence": 4294967295,
            }
        ],
        "vout": [
            {
                "value": reward,
                "n": 0,
                "scriptPubKey": {
                    "asm": "OP_DUP OP_HASH160 ... OP_EQUALVERIFY OP_CHECKSIG",
                    "hex": "76a914" + _h(height)[:40] + "88ac",
                    "reqSigs": 1,
                    "type": "pubkeyhash",
                    "addresses": [f"Big{_h(height)[:30]}"],
                },
            }
        ],
        "blockhash": block_hash,
        "confirmations": confirmations,
        "time": _BASE_TIME + height * 150,
        "blocktime": _BASE_TIME + height * 150,
    }


def _payment_tx(seed: int, block_hash: str, height: int, confirmations: int,
                inputs, outputs):
    txid = _h(seed)
    vin = []
    for i, (prev_txid, vout_n, val) in enumerate(inputs):
        vin.append(
            {
                "txid": prev_txid,
                "vout": vout_n,
                "scriptSig": {"asm": "3045...[sig]", "hex": "483045" + _h(seed + i)[:20]},
                "sequence": 4294967295,
                # Convenience field some explorers surface (prevout value/addr).
                "prevout": {
                    "value": val,
                    "scriptPubKey": {
                        "addresses": [f"Big{_h(seed + 500 + i)[:30]}"],
                        "type": "pubkeyhash",
                    },
                },
            }
        )
    vout = []
    for n, (val, addr) in enumerate(outputs):
        vout.append(
            {
                "value": val,
                "n": n,
                "scriptPubKey": {
                    "asm": "OP_DUP OP_HASH160 ... OP_EQUALVERIFY OP_CHECKSIG",
                    "hex": "76a914" + _h(seed + 900 + n)[:40] + "88ac",
                    "reqSigs": 1,
                    "type": "pubkeyhash",
                    "addresses": [addr],
                },
            }
        )
    return {
        "txid": txid,
        "hash": txid,
        "version": 2,
        "size": 226,
        "vsize": 226,
        "weight": 904,
        "locktime": 0,
        "vin": vin,
        "vout": vout,
        "blockhash": block_hash,
        "confirmations": confirmations,
        "time": _BASE_TIME + height * 150 + 30,
        "blocktime": _BASE_TIME + height * 150 + 30,
    }


def _build():
    """Construct the demo chain. Returns (blocks_by_hash, blocks_by_height,
    height_of_hash, txs_by_id, tip_height, mempool_txids)."""
    num_blocks = 12
    tip_height = num_blocks - 1

    blocks_by_hash = {}
    blocks_by_height = {}
    txs_by_id = {}
    height_of_hash = {}

    prev_hash = "0" * 64
    reward = 50.0

    for height in range(num_blocks):
        block_hash = _h(height)
        confirmations = tip_height - height + 1

        cb = _coinbase_tx(height, reward, block_hash, confirmations)
        txs_by_id[cb["txid"]] = cb
        tx_list = [cb]

        # Add a couple of payment txs to non-genesis blocks.
        if height > 0:
            p1 = _payment_tx(
                seed=height * 10 + 1,
                block_hash=block_hash,
                height=height,
                confirmations=confirmations,
                inputs=[(_h(1000 + height - 1), 0, 50.0)],
                outputs=[
                    (12.5, f"Big{_h(height * 3 + 1)[:30]}"),
                    (37.49, f"Big{_h(height * 3 + 2)[:30]}"),
                ],
            )
            txs_by_id[p1["txid"]] = p1
            tx_list.append(p1)

        if height > 1:
            p2 = _payment_tx(
                seed=height * 10 + 2,
                block_hash=block_hash,
                height=height,
                confirmations=confirmations,
                inputs=[
                    (_h(1000 + height - 2), 0, 50.0),
                    (_h((height - 1) * 10 + 1), 1, 37.49),
                ],
                outputs=[
                    (80.0, f"Big{_h(height * 5 + 7)[:30]}"),
                    (7.485, f"Big{_h(height * 5 + 8)[:30]}"),
                ],
            )
            txs_by_id[p2["txid"]] = p2
            tx_list.append(p2)

        txids = [t["txid"] for t in tx_list]
        size = 285 + sum(t["size"] for t in tx_list)
        block = {
            "hash": block_hash,
            "confirmations": confirmations,
            "height": height,
            "version": 536870912,
            "versionHex": "20000000",
            "merkleroot": _h(9000 + height),
            "time": _BASE_TIME + height * 150,
            "mediantime": _BASE_TIME + height * 150 - 75,
            "nonce": 305419896 + height,
            "bits": "1d00ffff",
            "difficulty": 1.0 + height * 0.0003,
            "chainwork": f"{'0' * 56}{(height + 1) * 65536:08x}",
            "nTx": len(txids),
            "previousblockhash": prev_hash if height > 0 else None,
            "nextblockhash": _h(height + 1) if height < tip_height else None,
            "strippedsize": size - 40,
            "size": size,
            "weight": size * 4,
            "tx": txids,
        }
        if height == 0:
            block.pop("previousblockhash")

        blocks_by_hash[block_hash] = block
        blocks_by_height[height] = block
        height_of_hash[block_hash] = height
        prev_hash = block_hash

    # A couple of unconfirmed mempool transactions.
    mempool_txids = []
    for k in range(2):
        mtx = _payment_tx(
            seed=99000 + k,
            block_hash="",
            height=tip_height + 1,
            confirmations=0,
            inputs=[(_h(1000 + tip_height), 0, 50.0)],
            outputs=[
                (10.0 + k, f"Big{_h(88000 + k)[:30]}"),
                (39.9 - k, f"Big{_h(77000 + k)[:30]}"),
            ],
        )
        mtx["blockhash"] = ""
        mtx["confirmations"] = 0
        mtx.pop("blocktime", None)
        txs_by_id[mtx["txid"]] = mtx
        mempool_txids.append(mtx["txid"])

    return {
        "blocks_by_hash": blocks_by_hash,
        "blocks_by_height": blocks_by_height,
        "height_of_hash": height_of_hash,
        "txs_by_id": txs_by_id,
        "tip_height": tip_height,
        "mempool_txids": mempool_txids,
    }


_DATA = _build()


# --- RPC-shaped accessors ------------------------------------------------

def getblockcount():
    return _DATA["tip_height"]


def getblockhash(height):
    height = int(height)
    blk = _DATA["blocks_by_height"].get(height)
    if blk is None:
        raise KeyError(f"Block height out of range: {height}")
    return blk["hash"]


def getblock(hash_or_height, verbosity=1):
    key = hash_or_height
    blk = _DATA["blocks_by_hash"].get(key)
    if blk is None:
        # Maybe a height was passed.
        try:
            blk = _DATA["blocks_by_height"].get(int(key))
        except (ValueError, TypeError):
            blk = None
    if blk is None:
        raise KeyError(f"Block not found: {hash_or_height}")
    return dict(blk)


def getrawtransaction(txid, verbose=True):
    tx = _DATA["txs_by_id"].get(txid)
    if tx is None:
        raise KeyError(f"No such transaction: {txid}")
    return dict(tx)


def getblockchaininfo():
    tip = _DATA["tip_height"]
    tip_block = _DATA["blocks_by_height"][tip]
    return {
        "chain": "main",
        "blocks": tip,
        "headers": tip,
        "bestblockhash": tip_block["hash"],
        "difficulty": tip_block["difficulty"],
        "mediantime": tip_block["mediantime"],
        "verificationprogress": 1.0,
        "initialblockdownload": False,
        "chainwork": tip_block["chainwork"],
        "size_on_disk": 1_234_567,
        "pruned": False,
    }


def getmempoolinfo():
    return {
        "loaded": True,
        "size": len(_DATA["mempool_txids"]),
        "bytes": 452 * len(_DATA["mempool_txids"]),
        "usage": 900 * len(_DATA["mempool_txids"]),
        "maxmempool": 300_000_000,
        "mempoolminfee": 0.00001000,
        "minrelaytxfee": 0.00001000,
    }


def getrawmempool(verbose=False):
    if verbose:
        return {t: {"size": 226, "time": int(time.time())} for t in _DATA["mempool_txids"]}
    return list(_DATA["mempool_txids"])


def getnetworkinfo():
    return {
        "version": 250000,
        "subversion": "/BigCoin:2.5.0/",
        "protocolversion": 70015,
        "connections": 8,
        "connections_in": 3,
        "connections_out": 5,
        "networkactive": True,
        "relayfee": 0.00001000,
        "warnings": "",
    }

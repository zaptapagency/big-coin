#!/usr/bin/env python3
"""MoonBite one-click CPU solo miner.

Real solo mining against a MoonBite (bigcoind) node. The node performs the
proof-of-work via the `generatetoaddress` RPC, so this is genuine mining -- on a
new / low-difficulty network it will find blocks; the reward goes to the address
you provide.

No third-party packages required (standard library only).

Usage:
    python moonbite_miner.py --address moon1... [options]

Common options (all also read from env / config file):
    --address    MoonBite address that receives the block rewards (required)
    --rpc-host   node RPC host           (default 127.0.0.1, env BIGCOIN_RPC_HOST)
    --rpc-port   node RPC port           (default 9445,      env BIGCOIN_RPC_PORT)
    --rpc-user   RPC username            (env BIGCOIN_RPC_USER)
    --rpc-pass   RPC password            (env BIGCOIN_RPC_PASSWORD)
    --maxtries   PoW attempts per round  (default 1000000)
    --blocks     stop after N blocks     (default 0 = run forever)

Note: `generatetoaddress` mines single-threaded inside the node. For heavy
multi-core mining on a high-difficulty chain you would use an external miner via
getblocktemplate; for launching / testing a fresh MoonBite network this is the
simple, honest path.
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request


class RpcError(Exception):
    pass


class RpcConn:
    def __init__(self, host, port, user, password, timeout=30):
        self.url = f"http://{host}:{port}/"
        self.user = user
        self.password = password
        self.timeout = timeout
        self._id = 0

    def call(self, method, *params):
        self._id += 1
        payload = json.dumps(
            {"jsonrpc": "1.0", "id": self._id, "method": method, "params": list(params)}
        ).encode("utf-8")
        req = urllib.request.Request(self.url, data=payload)
        req.add_header("Content-Type", "application/json")
        if self.user or self.password:
            token = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
            req.add_header("Authorization", f"Basic {token}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            try:
                data = json.loads(exc.read().decode("utf-8"))
                err = data.get("error")
                if err:
                    raise RpcError(err.get("message", str(err)))
            except (ValueError, AttributeError):
                pass
            if exc.code in (401, 403):
                raise RpcError(f"authentication failed (HTTP {exc.code}) -- check --rpc-user/--rpc-pass")
            raise RpcError(f"HTTP error {exc.code}")
        except (TimeoutError, urllib.error.URLError, ConnectionError, OSError) as exc:
            raise RpcError(f"cannot reach node at {self.url} ({getattr(exc, 'reason', exc)})")
        data = json.loads(body)
        if data.get("error"):
            raise RpcError(data["error"].get("message", str(data["error"])))
        return data.get("result")


def human_rate(blocks, seconds):
    if seconds <= 0:
        return "0/min"
    per_min = blocks / seconds * 60
    return f"{per_min:.2f} blocks/min"


def main(argv=None):
    p = argparse.ArgumentParser(description="MoonBite one-click CPU solo miner")
    p.add_argument("--address", default=os.environ.get("MINE_ADDRESS", ""),
                   help="MoonBite address to receive rewards (required)")
    p.add_argument("--rpc-host", default=os.environ.get("BIGCOIN_RPC_HOST", "127.0.0.1"))
    p.add_argument("--rpc-port", type=int, default=int(os.environ.get("BIGCOIN_RPC_PORT", "9445")))
    p.add_argument("--rpc-user", default=os.environ.get("BIGCOIN_RPC_USER", ""))
    p.add_argument("--rpc-pass", default=os.environ.get("BIGCOIN_RPC_PASSWORD", ""))
    p.add_argument("--maxtries", type=int, default=1000000,
                   help="PoW attempts per round before returning (default 1000000)")
    p.add_argument("--blocks", type=int, default=0,
                   help="stop after N blocks (default 0 = forever)")
    args = p.parse_args(argv)

    if not args.address:
        p.error("--address is required (or set MINE_ADDRESS). "
                "Get one from your wallet or `bigcoin-cli getnewaddress`.")

    conn = RpcConn(args.rpc_host, args.rpc_port, args.rpc_user, args.rpc_pass)

    print("=" * 60)
    print(" MoonBite CPU solo miner")
    print("=" * 60)
    print(f" Node    : http://{args.rpc_host}:{args.rpc_port}/")
    print(f" Reward  : {args.address}")
    print(f" Target  : {'forever' if args.blocks == 0 else str(args.blocks) + ' blocks'}")
    print("-" * 60)

    # Sanity-check the connection + report starting height.
    try:
        info = conn.call("getblockchaininfo")
        start_height = info.get("blocks", 0)
        print(f" Connected. Chain '{info.get('chain','?')}' at height {start_height}.")
        print(f" Difficulty {info.get('difficulty', 0)}.")
    except RpcError as exc:
        print(f" ERROR: {exc}", file=sys.stderr)
        return 1
    print("-" * 60)
    print(" Mining... (Ctrl+C to stop)\n")

    mined = 0
    started = time.time()
    try:
        while args.blocks == 0 or mined < args.blocks:
            try:
                hashes = conn.call("generatetoaddress", 1, args.address, args.maxtries)
            except RpcError as exc:
                # Invalid address / node error -> stop, it won't fix itself.
                print(f" ERROR: {exc}", file=sys.stderr)
                return 1
            if hashes:
                mined += len(hashes)
                height = start_height + mined
                elapsed = time.time() - started
                for h in hashes:
                    print(f" [+] block #{height} mined  hash={h}")
                print(f"     total this session: {mined}  ({human_rate(mined, elapsed)})\n")
            # else: no block found in this maxtries round -> loop and retry.
    except KeyboardInterrupt:
        print("\n Stopped by user.")

    elapsed = time.time() - started
    print("-" * 60)
    print(f" Session done: {mined} block(s) in {elapsed:.0f}s ({human_rate(mined, elapsed)}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

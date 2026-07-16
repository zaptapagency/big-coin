#!/usr/bin/env python3
"""MoonBite desktop miner (public, one-file, no dependencies).

This mines the LIVE MoonBite chain by asking the public explorer to mine a
block to your address. The node does the real proof-of-work (RandomX/Scrypt)
server-side, so no RPC credentials are needed -- you only supply the address
that should receive the block reward.

Requires nothing but Python 3 (standard library only).

Usage:
    python moonbite-miner.py --address moon1youraddress...

Options:
    --address    MoonBite address to receive rewards   (required)
    --explorer   Explorer base URL                      (default: live chain)
    --rounds     Stop after N successful blocks         (default 0 = forever)
    --sleep      Seconds to wait between rounds          (default 0)
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

DEFAULT_EXPLORER = "https://moonbite-production.up.railway.app"


def mine_once(explorer, address, timeout=60):
    """Ask the explorer to mine one block to `address`.
    Returns the parsed JSON body. Raises RuntimeError on transport failure."""
    url = explorer.rstrip("/") + "/api/mine"
    payload = json.dumps({"address": address}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except (ValueError, AttributeError):
            body = {}
        msg = body.get("error", f"HTTP {exc.code}")
        raise RuntimeError(msg)
    except (TimeoutError, urllib.error.URLError, ConnectionError, OSError) as exc:
        raise RuntimeError(f"cannot reach explorer at {explorer} ({getattr(exc, 'reason', exc)})")


def main(argv=None):
    p = argparse.ArgumentParser(description="MoonBite desktop miner (mines the live chain via the explorer)")
    p.add_argument("--address", default=os.environ.get("MINE_ADDRESS", ""),
                   help="MoonBite address to receive rewards (required)")
    p.add_argument("--explorer", default=os.environ.get("MOONBITE_EXPLORER", DEFAULT_EXPLORER),
                   help=f"explorer base URL (default {DEFAULT_EXPLORER})")
    p.add_argument("--rounds", type=int, default=0,
                   help="stop after N blocks (default 0 = forever)")
    p.add_argument("--sleep", type=float, default=0.0,
                   help="seconds between rounds (default 0)")
    args = p.parse_args(argv)

    if not args.address:
        p.error("--address is required. Use your MoonBite wallet address (moon1... or M...).")

    explorer = args.explorer.rstrip("/")

    print("=" * 60)
    print(" MoonBite desktop miner")
    print("=" * 60)
    print(f" Explorer : {explorer}")
    print(f" Reward   : {args.address}")
    print(f" Target   : {'forever' if args.rounds == 0 else str(args.rounds) + ' block(s)'}")
    print("-" * 60)
    print(" Mining... (Ctrl+C to stop)\n")

    mined = 0
    started = time.time()
    try:
        while args.rounds == 0 or mined < args.rounds:
            try:
                res = mine_once(explorer, args.address)
            except RuntimeError as exc:
                print(f" ERROR: {exc}", file=sys.stderr)
                # A disabled/demo explorer or a bad address will not fix itself.
                low = str(exc).lower()
                if "disabled" in low or "invalid" in low or "demo" in low:
                    return 1
                time.sleep(max(1.0, args.sleep))
                continue

            if res.get("found"):
                mined += 1
                height = res.get("height", "?")
                h = (res.get("hashes") or ["?"])[0]
                elapsed = time.time() - started
                rate = mined / elapsed * 60 if elapsed > 0 else 0
                print(f" [+] block #{height} mined to you   {h}")
                print(f"     session: {mined} block(s)  ({rate:.2f} blocks/min)\n")
            else:
                # No block this round -- keep trying.
                print(" ... no block this round, retrying")
            if args.sleep > 0:
                time.sleep(args.sleep)
    except KeyboardInterrupt:
        print("\n Stopped by user.")

    elapsed = time.time() - started
    print("-" * 60)
    print(f" Session done: {mined} block(s) in {elapsed:.0f}s.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

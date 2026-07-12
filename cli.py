"""MyCoin — command-line interface.

A thin, human-friendly wrapper over the existing modules (transaction, block,
node, wallet, params). It creates fresh in-memory state per invocation; there is
no persistence and this network never holds real funds.

Subcommands:
  newkey             generate a keypair and print its address
  mine [--count N]   mine N blocks to an address, printing each block
  subsidy --height H print the block subsidy at height H
  info               print genesis hash, height, and total money in the UTXO set
"""

from __future__ import annotations

import argparse
from typing import Optional

from block import block_subsidy, genesis_block
from node import Node
from params import CENTS_PER_COIN
from transaction import generate_keypair, pubkey_hash
from wallet import address_from_pubkey_hash, is_valid_address


def _fresh_address() -> str:
    """Generate a keypair and return its Base58Check address."""
    _sk, pubkey_hex = generate_keypair()
    return address_from_pubkey_hash(pubkey_hash(pubkey_hex))


def _address_to_pkh(address: str) -> str:
    """Recover the pubkey-hash (hex) that a coinbase output locks to."""
    from wallet import pubkey_hash_from_address

    return pubkey_hash_from_address(address)


def _format_amount(cents: int) -> str:
    """Render an integer cent amount as 'C coins (K cents)'."""
    coins = cents / CENTS_PER_COIN
    return f"{coins:g} coins ({cents} cents)"


# --------------------------------------------------------------------------- #
# Subcommand handlers
# --------------------------------------------------------------------------- #
def cmd_newkey(args: argparse.Namespace) -> int:
    print(_fresh_address())
    return 0


def cmd_mine(args: argparse.Namespace) -> int:
    if args.count < 1:
        print("error: --count must be at least 1")
        return 1

    address = args.address or _fresh_address()
    if not is_valid_address(address):
        print(f"error: invalid address {address!r}")
        return 1

    miner_pkh = _address_to_pkh(address)
    # coinbase_maturity=0 so the CLI can mine freely without maturity gating.
    node = Node("cli-miner", coinbase_maturity=0)

    print(f"mining {args.count} block(s) to {address}")
    for _ in range(args.count):
        block = node.mine_block(miner_pkh)
        if block is None:
            print("error: failed to mine a block")
            return 1
        total = node.chain.utxo.total_value()
        print(
            f"height={node.chain.height} hash={block.hash} "
            f"total_utxo={_format_amount(total)}"
        )
    return 0


def cmd_subsidy(args: argparse.Namespace) -> int:
    if args.height < 0:
        print("error: --height must be non-negative")
        return 1
    cents = block_subsidy(args.height)
    coins = cents // CENTS_PER_COIN
    print(f"height {args.height}: subsidy = {coins} coins ({cents} cents)")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    node = Node("cli-info")
    chain = node.chain
    print(f"genesis_hash: {chain.genesis_hash}")
    print(f"height:       {chain.height}")
    print(f"total_money:  {_format_amount(chain.utxo.total_value())}")
    return 0


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mycoin",
        description="MyCoin command-line interface (educational; no real funds).",
    )
    sub = parser.add_subparsers(dest="command", metavar="command")

    p_newkey = sub.add_parser("newkey", help="generate a keypair and print its address")
    p_newkey.set_defaults(func=cmd_newkey)

    p_mine = sub.add_parser("mine", help="mine blocks to an address")
    p_mine.add_argument("--count", type=int, default=1, help="number of blocks to mine")
    p_mine.add_argument(
        "--address", default=None, help="destination address (default: a fresh key)"
    )
    p_mine.set_defaults(func=cmd_mine)

    p_subsidy = sub.add_parser("subsidy", help="print the block subsidy at a height")
    p_subsidy.add_argument("--height", type=int, required=True, help="block height")
    p_subsidy.set_defaults(func=cmd_subsidy)

    p_info = sub.add_parser("info", help="print fresh-chain info")
    p_info.set_defaults(func=cmd_info)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

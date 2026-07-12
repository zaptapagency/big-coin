"""MyCoin — Milestone 3: Proof-of-Work (Bitcoin whitepaper section 4).

Mining searches for a header nonce whose double-SHA-256 hash is below a target,
i.e. begins with a required number of leading zero bits. This is "one CPU, one
vote": producing a block costs proportional work, and the chain with the most
cumulative work wins (longest-most-work chain rule, enforced in node.py).

Design of `bits`: we represent difficulty as an integer number of required
leading zero bits. The target is `2**(256 - bits)` and a hash is valid when its
integer value is strictly below the target.

Trade-off vs Bitcoin: Bitcoin encodes a full 256-bit target in a compact "bits"
field and retargets continuously toward a 2-week timespan. Here difficulty is
quantized to whole leading-zero bits, so retargeting moves in coarse ~2x steps.
This keeps local mining fast and the arithmetic easy to follow.
"""

from __future__ import annotations

from block import Block

# Consensus timing (my own parameters).
TARGET_BLOCK_TIME = 600  # seconds (10 minutes)
RETARGET_INTERVAL = 2016  # blocks
MIN_BITS = 1
MAX_BITS = 240  # keep well under 256 so a target always exists


def bits_to_target(bits: int) -> int:
    """The largest hash value (exclusive) that satisfies `bits`."""
    return 1 << (256 - bits)


def hash_meets_target(hash_hex: str, bits: int) -> bool:
    """True if `hash_hex` has at least `bits` leading zero bits."""
    return int(hash_hex, 16) < bits_to_target(bits)


def block_meets_target(block: Block) -> bool:
    return hash_meets_target(block.hash, block.header.bits)


def mine(block: Block, max_nonce: int = 1 << 32) -> bool:
    """Increment the block's nonce until its hash meets the target.

    Returns True and leaves the winning nonce in the header on success; returns
    False if the nonce space is exhausted (caller should change something, e.g.
    the coinbase extra-nonce or timestamp, and retry).
    """
    for nonce in range(max_nonce):
        block.header.nonce = nonce
        if hash_meets_target(block.hash, block.header.bits):
            return True
    return False


def calculate_next_bits(
    current_bits: int, actual_timespan: int, expected_timespan: int | None = None
) -> int:
    """Coarse difficulty retarget once per RETARGET_INTERVAL blocks.

    `actual_timespan` is the wall-clock time the last interval actually took.
    If blocks came more than 2x too fast, require one more zero bit (harder);
    more than 2x too slow, require one fewer (easier). Clamped to [MIN, MAX].
    """
    if expected_timespan is None:
        expected_timespan = TARGET_BLOCK_TIME * RETARGET_INTERVAL

    if actual_timespan < expected_timespan // 2:
        next_bits = current_bits + 1  # too fast -> harder
    elif actual_timespan > expected_timespan * 2:
        next_bits = current_bits - 1  # too slow -> easier
    else:
        next_bits = current_bits

    return max(MIN_BITS, min(MAX_BITS, next_bits))

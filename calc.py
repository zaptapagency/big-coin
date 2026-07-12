"""Milestone 9 — Security Analysis: attacker double-spend probability.

This module ports the "AttackerSuccessProbability" function from the Bitcoin
whitepaper (Nakamoto 2008, section 11, "Calculations") to Python.

The math in plain English
-------------------------
An attacker who controls a fraction ``q`` of the network's hash power wants to
double-spend: they secretly build their own private chain while the honest
network extends the public chain. A merchant waits for ``z`` confirmations
before releasing goods. We want the probability that the attacker's private
chain ever catches up to and overtakes the honest chain after starting ``z``
blocks behind.

Two ideas combine:

1. Poisson term — By the time the honest chain has produced ``z`` blocks, the
   attacker will have produced some number ``k`` of blocks. Because block
   discovery is a memoryless (Poisson) process, the number of blocks the
   attacker found while the honest chain found ``z`` is Poisson-distributed with
   mean ``lambda = z * (q / p)`` where ``p = 1 - q`` is the honest fraction.

2. Gambler's-ruin term — Given the attacker is ``z - k`` blocks behind, the
   probability they ever catch up is the classic gambler's-ruin result
   ``(q / p) ** (z - k)`` when the attacker is the underdog (``q < p``); once
   ``k >= z`` the attacker is already even or ahead, so catch-up is certain
   (probability 1).

We sum, over every possible ``k``, the probability of that Poisson outcome times
the probability of NOT catching up from it, then subtract from 1 to get the
probability of catching up. This mirrors the whitepaper's C loop exactly.

Only the Python standard library is used.
"""

import math


def attacker_success_probability(q: float, z: int) -> float:
    """Probability the attacker ever catches up from ``z`` blocks behind.

    Faithful port of the whitepaper's C ``AttackerSuccessProbability``.

    Args:
        q: Fraction of total hash power controlled by the attacker (0 <= q < 1).
        z: Number of confirmations (blocks) the merchant waits for.

    Returns:
        Probability in [0, 1] that the attacker succeeds in the double-spend.

    Note:
        For ``q >= 0.5`` the attacker is not the underdog and the gambler's-ruin
        term ``(q / p) ** (z - k)`` no longer represents a probability < 1; the
        attacker catches up with probability 1. This function follows the
        whitepaper formula literally and does not special-case that regime; use
        :func:`recommend_confirmations` for safe policy decisions.
    """
    p = 1.0 - q
    # Mean number of attacker blocks found while honest chain finds z blocks.
    lambda_ = z * (q / p)
    total = 1.0
    for k in range(0, z + 1):
        # Poisson term: probability the attacker found exactly k blocks,
        # poisson = exp(-lambda) * lambda**k / k!, built up iteratively.
        poisson = math.exp(-lambda_)
        for i in range(1, k + 1):
            poisson *= lambda_ / i
        # Gambler's-ruin term: (q/p)**(z-k) is the probability of catching up
        # from (z-k) blocks behind. Subtract the probability of NOT catching up.
        total -= poisson * (1 - pow(q / p, z - k))
    return total


def recommend_confirmations(q: float, max_probability: float = 0.001) -> int:
    """Smallest number of confirmations ``z`` making the attack unlikely.

    Returns the smallest ``z`` such that
    ``attacker_success_probability(q, z) < max_probability``.

    Args:
        q: Fraction of hash power controlled by the attacker.
        max_probability: Acceptable upper bound on attacker success (default
            0.001, i.e. 0.1%, matching the whitepaper's table).

    Returns:
        The smallest safe ``z`` (>= 0).

    Raises:
        ValueError: If ``q >= 0.5``. With a majority of hash power the attacker
            catches up with probability 1 no matter how many confirmations are
            required, so no finite ``z`` is safe.
    """
    if q >= 0.5:
        raise ValueError(
            "q >= 0.5: attacker controls a majority and succeeds with "
            "probability 1; no number of confirmations is safe."
        )
    z = 0
    while attacker_success_probability(q, z) >= max_probability:
        z += 1
    return z


if __name__ == "__main__":
    # Whitepaper table 1: q = 0.1, P for z = 0..10.
    print("q = 0.1")
    for z in range(0, 11):
        print(f"z={z:<3d} P={attacker_success_probability(0.1, z):.7f}")

    # Whitepaper table 2: solving for P < 0.1%, q from 0.10 to 0.45 step 0.05.
    print("\nSolving for P less than 0.1%")
    q = 0.10
    while q < 0.45 + 1e-9:
        print(f"q={q:.2f} z={recommend_confirmations(q, 0.001)}")
        q += 0.05

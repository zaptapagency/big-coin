# Security Policy & Threat Model — MyCoin

> **MyCoin is an educational / portfolio project. It must never be used to hold
> real funds.** The engineering here is "production-grade" in the sense of
> software quality (tests, persistence, real networking, packaging, CI). It is
> **not** production-grade money: it has had no independent security audit, no
> cryptographic review, and no legal/regulatory review. Do not deploy it as a
> real currency.

## Scope of hardening delivered

The consensus and validation rules below are implemented and tested
(`tests/test_hardening.py`, `tests/test_attacks.py`):

| Rule | Purpose | Where |
| --- | --- | --- |
| Coinbase maturity (100 blocks) | Newly minted coins can't be spent until buried, limiting reorg profit | `utxo.py`, `node.py` |
| Median-time-past lower bound | Stops miners rolling timestamps backward to game difficulty | `node.py:median_time_past` |
| Max-future-time (2h) | Rejects blocks dated far ahead of local clock | `node.py:_validate_block` |
| Block-size ceiling (~1 MB) | Bandwidth / DoS protection | `params.MAX_BLOCK_BYTES` |
| Max-money invariant | Rejects value-overflow forgeries; per-output and per-tx caps | `transaction.py:verify` |
| Most-work chain rule + reorg | Follows heaviest valid branch, revalidating UTXO on switch | `node.py:add_block/_reorg_to` |
| Full signature + UTXO validation | ECDSA secp256k1, no double-spend, in ≥ out | `transaction.py`, `utxo.py` |

## Threat model

**In scope (defended against):**
- Double-spend within a block, within the mempool, and across a reorg.
- Value forgery (over-claimed coinbase subsidy, outputs exceeding the supply cap).
- Forged / insufficient proof-of-work blocks.
- Timestamp manipulation to distort difficulty retargeting.
- Oversized-block resource exhaustion.
- Spending immature coinbase outputs.

**Explicitly out of scope (NOT defended against — do not rely on this code):**
- **Real-money safety.** No audit; assume exploitable bugs exist.
- **Network-layer attacks:** eclipse/Sybil attacks, peer authentication, DoS on
  the P2P layer, transaction/-block flooding beyond the size check.
- **Cryptographic side channels & key management.** `pubkey_hash` is a single
  SHA-256 (not RIPEMD-160(SHA-256)); keys live unencrypted in memory. No HD
  wallets, no secure key storage.
- **51% / majority-hashrate attacks.** These succeed by design (see
  `tests/test_attacks.py::test_51_percent_reorg_rewrites_confirmed_payment` and
  `calc.py` for the whitepaper attacker-success probabilities). Choose
  confirmation depth via `calc.recommend_confirmations`.
- **Serialization hardening.** Canonical JSON is used for readability; it is not
  a hardened binary format and parsing untrusted input has not been fuzzed.
- **Consensus edge cases** at scale (real retarget windows, deep reorgs,
  memory/disk exhaustion over long chains).

## Known trade-offs vs. Bitcoin

- Reorgs replay the UTXO set from genesis along the branch (O(chain length))
  rather than keeping per-block undo data.
- UTXO set is in-memory; SQLite persistence (`store.py`) is additive, not the
  source of consensus truth during a run.
- No Script language: outputs are pay-to-pubkey-hash only, one signature each.
- SIGHASH_ALL is the only sighash mode.

## Reporting

This is a learning repository with no production deployment. If you find a bug,
open an issue describing the behavior and the affected module/test. Do not
report it as a security vulnerability of a live system — there is none.

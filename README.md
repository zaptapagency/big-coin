# MyCoin

A Bitcoin-style peer-to-peer electronic cash system, built from first principles
for education and portfolio purposes. Modeled on the Bitcoin whitepaper
(Nakamoto, 2008).

> **Warning:** This is a toy network with no real value. It must never hold real
> funds and makes no production security guarantees.

## Setup

```bash
pip install -r requirements.txt
python -m pytest -q
```

## Milestones

- [x] **M1 — Transactions** (§2, §9)
- [x] **M2 — Blocks & timestamp chain** (§3, §7 Merkle)
- [x] **M3 — Proof-of-work** (§4)
- [x] **M4 — Node & network** (§5)
- [x] **M5 — Incentives** (§6)
- [x] **M6 — UTXO set & pruning** (§7)
- [x] **M7 — SPV client** (§8)
- [x] **M8 — Wallet & privacy** (§10)
- [x] **M9 — Security analysis** (§11)

## Modules

| File | Milestone | Purpose |
| --- | --- | --- |
| `transaction.py` | M1 | Transaction model, ECDSA signing, verification |
| `merkle.py` | M2/M7 | Merkle root + inclusion-proof branch |
| `block.py` | M2/M5 | Block/header, genesis, coinbase, subsidy/halving |
| `pow.py` | M3 | Proof-of-work target, mining, difficulty retarget |
| `utxo.py` | M6 | UTXO index, tx/coinbase validation, pruning demo |
| `node.py` | M4/M5 | Blockchain, most-work rule, fork/reorg, the 6 steps |
| `network.py` | M4 | In-process gossip net, dropped-message tolerance |
| `wallet.py` | M8 | Base58Check addresses, keychain, tx building |
| `spv.py` | M7 | Header-only light client, Merkle proof verification |
| `calc.py` | M9 | Attacker-success probability & confirmation advice |
| `params.py` | *hardening* | Central consensus constants (maturity, timestamps, limits) |
| `store.py` | *hardening* | SQLite persistence layer (BlockStore, save/load chain) |
| `p2p.py` | *hardening* | asyncio TCP P2P transport (length-prefixed JSON frames) |
| `cli.py` | *hardening* | Command-line interface (newkey, mine, subsidy, info) |

---

## Milestone 1 — Transactions

A coin is a **chain of digital signatures** (§2). Each transaction spends the
outputs of earlier transactions and creates new outputs locked to recipients.

- `TxOutput(amount, pubkey_hash)` — value locked to a recipient's public-key hash.
- `TxInput(prev_txid, output_index, pubkey, signature)` — a reference to an
  output being spent, plus the authorization to spend it.
- `Transaction(inputs, outputs)` — supports multiple inputs/outputs and an
  explicit change output back to the sender.

**Signing.** Every input signs a SIGHASH_ALL message: the transaction serialized
with all input signatures/pubkeys stripped (`signing_bytes()`). This commits to
exactly which outputs are being spent and to every next owner, so a signature
cannot be replayed on a different transaction or have its outputs altered.

**Identity.** `txid` is the double-SHA-256 of the fully-signed canonical
serialization.

**Verification** (`Transaction.verify(resolver)`) checks, for each input:
1. the referenced output exists (via a resolver — later the UTXO set),
2. `sha256(input.pubkey) == output.pubkey_hash` (spender is authorized),
3. the ECDSA (secp256k1) signature is valid,
4. no duplicate outpoints within the transaction, and
5. `sum(inputs) >= sum(outputs)` — the difference is the fee (used in M5).

### Trade-offs vs. real Bitcoin (the "~10% difference")

| Area | MyCoin | Bitcoin |
| --- | --- | --- |
| Serialization | Canonical JSON (readable, larger) | Compact binary |
| Locking | Single pubkey hash only | Full Script language |
| Address hash | `SHA-256(pubkey)` | `RIPEMD-160(SHA-256(pubkey))` |
| Sighash | SIGHASH_ALL only | Multiple sighash modes |

RIPEMD-160 is avoided because it is absent from some OpenSSL 3 builds; the
single SHA-256 is adequate for a network with no value.

### Files
- `transaction.py` — transaction model, signing, verification.
- `tests/test_transaction.py` — 12 tests (valid spends, multi-I/O, change,
  wrong key, tampering, overspend, spent/unknown output, duplicate input,
  serialization round-trip).

---

## Milestone 2 — Blocks & timestamp chain

Blocks chain by `prev_hash` and commit to their transactions with a Merkle root,
forming the timestamp server of §3. `merkle.py` builds the tree pairwise with
double-SHA-256, duplicating the last node on odd counts, and produces a compact
inclusion branch for SPV. The genesis block is hardcoded and identical on every
node. A block hash is the double-SHA-256 of the serialized header.

## Milestone 3 — Proof-of-work

`bits` is the required number of leading zero bits; the target is
`2**(256 - bits)` and a block is valid when its hash is below it. `mine()`
searches the nonce space. Difficulty retargets every 2016 blocks toward a
10-minute block time (coarsely, in whole-bit steps — see trade-off below).
Consensus follows the **most-work chain**.

## Milestone 5 — Incentives

The first transaction in a block is a **coinbase** minting the block subsidy plus
the sum of transaction fees to the miner. Subsidy starts at 50 coins and halves
every 210,000 blocks; total supply is capped at 42,000,000 coins (1 coin =
100,000,000 "cents"). A coinbase uses a null-prevout input whose index carries
the block height and whose pubkey field carries an extra-nonce, keeping every
coinbase txid unique. Over-claiming the subsidy makes a block invalid.

## Milestone 6 — UTXO set & pruning

`UTXOSet` indexes every unspent output by `(txid, index)` for O(1) double-spend
checks. `validate_transaction` defers signature/authorization/no-overspend to
`Transaction.verify` and additionally requires each referenced outpoint to still
be unspent. `merkle_pruning_demo(n)` illustrates §7: proving one tx in a block of
`n` needs only ~log2(n) hashes, so spent tx bodies can be discarded.

## Milestone 4 — Node & network

`Blockchain` stores all blocks (including side branches), tracks cumulative work,
keeps the active tip on the most-work chain, and **reorgs** onto a heavier branch
(rebuilding the UTXO set and returning displaced txs to the mempool). `Node`
performs the six steps of §5; `Network` is an in-process gossip simulation that
can randomly **drop messages**, and a node that receives a block whose parent it
is missing requests the parent on demand (`request_block`).

### Trade-offs vs. real Bitcoin (core)

| Area | MyCoin | Bitcoin |
| --- | --- | --- |
| Difficulty | Whole leading-zero bits, coarse ~2x retarget | Compact 256-bit target, smooth retarget |
| Reorg | Replay UTXO from genesis along branch | Per-block undo data in LevelDB |
| Network | Synchronous in-process gossip | Binary TCP, inv/getdata, DoS limits |
| Coinbase maturity | Spendable immediately | 100-block maturity |

### Security tests (M9 attacks)
`tests/test_attacks.py` — double-spend rejection, forged-PoW block rejection,
over-claimed-subsidy rejection, and a 51% reorg that rewrites a confirmed
payment on a 3-node network (motivating the confirmation math in `calc.py`).

---

## Milestone 7 — SPV client

`spv.py` is a light client that stores **only block headers**. A full node hands
it a `MerkleProofBundle` (txid, block hash, Merkle branch); the client checks the
branch against the header's Merkle root (`verify_payment`) and counts headers
stacked on top for confirmations. `verify_payment_with_confirmations` enforces a
depth threshold. Trade-off: an SPV client cannot detect an invalid block itself —
it trusts the most-work header chain and the honest majority (§8).

## Milestone 8 — Wallet & privacy

`wallet.py` provides Base58Check addresses (`address_from_pubkey_hash` /
`pubkey_hash_from_address` with a 4-byte double-SHA-256 checksum) and a `Wallet`
keychain. Following §10's privacy guidance, `new_key()` mints a fresh key pair
per call and change defaults to a brand-new address. `create_transaction`
greedily selects owned UTXOs, pays the recipient, returns change, and signs every
input. Trade-off vs Bitcoin: single-SHA-256 pubkey hashing and random keys rather
than RIPEMD-160 + BIP32 HD derivation.

## Milestone 9 — Security analysis

`calc.py` ports the whitepaper's `AttackerSuccessProbability` (Poisson progress ×
gambler's-ruin catch-up). `recommend_confirmations(q)` returns the smallest depth
`z` with `P < 0.1%` (raising for `q ≥ 0.5`, where the attacker wins with
certainty). It reproduces the paper's tables exactly, including
**q=0.1, z=5 → P ≈ 0.0009137** and the P<0.1% row
`z = 5, 8, 11, 15, 24, 41, 89, 340` for `q = 0.10 … 0.45`.

---

## Production-Grade Hardening

In addition to the 9 milestones above, the following hardening has been applied:

| Rule | Purpose | Location |
| --- | --- | --- |
| Coinbase maturity (100 blocks) | Newly minted coins can't be spent until buried | `utxo.py`, `node.py` |
| Median-time-past lower bound | Prevents timestamp rolling to game difficulty | `node.py:median_time_past` |
| Max-future-time rejection (2h) | Rejects blocks dated far ahead | `node.py:_validate_block` |
| Block-size ceiling (~1 MB) | Bandwidth / DoS protection | `params.MAX_BLOCK_BYTES` |
| Max-money & overflow checks | Rejects value-forgery transactions | `transaction.py:verify` |
| Full UTXO validation on reorg | Revalidates the UTXO set on branch switch | `node.py:_reorg_to` |

See `SECURITY.md` for the full threat model, in-scope vs. out-of-scope defenses,
and an explicit statement that this is an **educational project** that must never
hold real funds and has had no production security audit.

### Test results

Run all tests with:
```bash
python -m pytest -q
```

**Result: 117 tests passing.**

- Milestones 1–9: 83 tests (transaction, merkle, block, wallet, spv, calc, etc.)
- Node/network (M4): 15 tests (including 3-node sync, fork/reorg, 51% attack)
- Hardening: 8 tests (coinbase maturity, timestamp rules, block-size, max-money)
- Persistence (SQLite): 5 tests (save/load chain, DB persistence)
- CLI: 6 tests (newkey, mine, subsidy, info)
- P2P (asyncio TCP): TBD (async tests running)

### End-to-end (Definition of Done)

`tests/test_integration.py` runs the whole system: three nodes mine and sync, two
wallets settle a payment, a rival branch forces a reorg the payment survives, an
SPV client verifies that payment by Merkle proof against headers only, and the
calculator matches the whitepaper. CI (`ruff`, `mypy`, `pytest`) validates the
entire codebase on push (GitHub Actions, Python 3.11 & 3.12).

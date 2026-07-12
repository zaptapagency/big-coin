# Exchange Listing & Integration Checklist for BigCoin (BIG)

This document describes, honestly, what it takes to get BIG integrated by an
exchange and what exchanges typically require. It is an integration/readiness
checklist, not a promise that any exchange will list BIG.

> **Reality check:** Getting listed on a **Tier-1 centralized exchange** (Binance,
> Coinbase, Kraken, etc.) is **very hard** for a new coin — it involves
> significant fees, legal review, liquidity, security audits, and demonstrable
> demand. New coins almost always start on **DEXs** (decentralized exchanges) or
> **small/mid-tier CEXs**, then work up. Plan accordingly.

---

## 1. Technical readiness

### Stable mainnet with finality

- A **live, stable mainnet** that has run without consensus-breaking issues for a
  meaningful period.
- Exchanges credit deposits only after **N confirmations** for probabilistic
  finality. With a 2.5-minute block time:

  | Confirmations | Approx. wall-clock time |
  |---------------|-------------------------|
  | 6             | ~15 minutes             |
  | 12            | ~30 minutes             |
  | 20            | ~50 minutes             |

  **Recommended deposit confirmations: at least 12** for BIG (adjust upward if
  the network has low total hash power and is thus cheaper to reorg — see
  section on reorgs below). Many exchanges pick a value targeting ~30-60 minutes
  of finality.

### Public block explorer

- A working, public **block explorer** (e.g. an Iquidus/BlockBook-style explorer)
  so anyone can verify blocks, transactions, addresses, and supply. Exchanges and
  users treat "no explorer" as a red flag.

### Published, reproducible binaries with checksums

- Official `bigcoind`, `bigcoin-cli`, and `bigcoin-qt` binaries for the platforms
  the exchange runs (typically Linux x86-64).
- **SHA-256 checksums** published alongside downloads, and ideally
  **GPG-signed** checksum files.
- **Reproducible builds** (Guix, as Bitcoin/Litecoin Core use) so a third party
  can rebuild bit-for-bit and verify the binaries match source.

```
# example checksum publication
sha256sum bigcoind-1.0.0-x86_64-linux-gnu.tar.gz
# -> <hash>  bigcoind-1.0.0-x86_64-linux-gnu.tar.gz
```

### JSON-RPC compatibility

BigCoin exposes the standard Bitcoin/Litecoin Core JSON-RPC interface, which is
what most exchange integration tooling already speaks. The RPC methods exchanges
rely on include:

| Method            | Used for                                             |
|-------------------|------------------------------------------------------|
| `getnewaddress`   | generate a unique deposit address per user           |
| `getbalance`      | hot-wallet balance checks                            |
| `sendtoaddress`   | process withdrawals                                  |
| `gettransaction`  | look up a specific wallet tx (confirmations, amount) |
| `listtransactions`| poll recent wallet activity for deposit detection    |
| `getblockcount`   | track chain height / confirmation counting           |
| `validateaddress` | validate withdrawal addresses before sending         |

Additional commonly used methods: `getblockchaininfo`, `getnetworkinfo`,
`getrawtransaction`, `estimatesmartfee`, `walletpassphrase` (for encrypted hot
wallets), and `getblock`.

- Provide a **`txindex=1`** node so any transaction can be looked up.
- Confirm behavior matches upstream (address formats, fee estimation, RBF, SegWit
  handling) since exchange code assumes Bitcoin/Litecoin Core semantics.

### Replay and reorg considerations

- **Replay protection:** If BIG ever forked from another chain sharing history,
  demonstrate replay protection so transactions can't be replayed across chains.
  A clean-genesis fork (its own genesis block) avoids cross-chain replay by
  construction — state this explicitly.
- **Reorg resistance:** A low-hash-power chain is cheap to 51%-attack and deep
  reorgs. Exchanges will (and should) demand **higher confirmation counts** for a
  young/low-difficulty chain. Be transparent about current network hash rate.
- **Deposit crediting logic:** Credits should only be final after the required
  confirmations, and integration should handle reorgs by re-checking
  confirmations via `gettransaction` rather than crediting on first-seen.

---

## 2. Coin information sheet

Provide a single authoritative info sheet. Fill in the bracketed launch values.

| Field               | Value                                             |
|---------------------|---------------------------------------------------|
| Name                | BigCoin                                           |
| Ticker              | BIG                                               |
| Algorithm           | Scrypt (PoW)                                       |
| Block time          | 2.5 minutes                                        |
| Initial reward      | 50 BIG                                             |
| Halving             | every 840,000 blocks                              |
| Max supply          | 84,000,000 BIG                                     |
| Address prefix      | `B` (base58) / `big1...` (bech32)                 |
| P2P port            | 9444 (mainnet) / 19555 (testnet)                  |
| RPC port            | 9445                                              |
| Genesis block       | `<genesis hash / date>` (to be filled at launch)  |
| Deposit confirmations (recommended) | 12+                              |
| Block explorer URL  | `<https://explorer.bigcoin.example>`              |
| Website             | `<https://bigcoin.example>`                        |
| Source (GitHub)     | `<https://github.com/<org>/bigcoin>`              |
| Node binaries       | `<downloads URL + checksums>`                     |

---

## 3. Business & legal realities

These are non-technical but usually the **actual** gating factors:

- **Listing fees.** Many CEXs charge listing/marketing fees that range from
  modest (small exchanges) to very large (top-tier). Some are "free" but require
  liquidity, volume, or community-vote campaigns.
- **KYC/AML & compliance.** Exchanges must satisfy their own regulatory
  obligations. They will scrutinize the project team, token distribution, and
  whether the asset can be used for money laundering.
- **Legal opinion / not-a-security.** Reputable exchanges typically want a
  **legal opinion** (from qualified counsel in the relevant jurisdictions)
  stating the token is **not a security** under applicable law, plus clarity on
  how BIG was distributed (fair-launch mining vs. premine/ICO matters a lot).
- **Liquidity & market making.** Exchanges want assurance of two-sided liquidity.
  Expect to arrange a market maker or seed liquidity yourself, especially on DEXs
  and small CEXs.
- **Security posture.** Audited code, disclosed premine (if any), multisig
  treasury, incident response, and responsiveness to the exchange's integration
  team.

---

## 4. Realistic path to being tradable

1. **DEX first.** If a wrapped/bridged or EVM-compatible representation is viable,
   list on a DEX where anyone can create a market. For a native L1 like BIG this
   usually means a bridge, an atomic-swap market, or an exchange that supports
   the coin natively.
2. **Small / mid-tier CEX.** Cheaper, faster, more willing to integrate new
   Bitcoin/Litecoin-family coins. Have your explorer, binaries, checksums, and RPC
   integration docs ready.
3. **Build volume, liquidity, and track record.**
4. **Then approach larger exchanges** with a proven, stable network and real
   trading history.

Be honest with your community: a new coin being "listable" is mostly about doing
the unglamorous work in sections 1-3, and even then, listing is at each
exchange's sole discretion.

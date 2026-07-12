# BigCoin — Production Launch Plan (Mineable L1, Wallet, Exchange-Listable)

> Honest scope note: The Python code in this repo is an **educational reference**. It is
> NOT the production chain and will never be listed. The production coin is a **fork of a
> proven Bitcoin-family chain (C++ Bitcoin Core / Litecoin Core)**. The Python repo stays as
> a learning artifact / the basis for a paid "build-your-own-Bitcoin" course (a separate, legal, low-risk income stream).

---

## 1. Chain parameters (DECIDED — sensible defaults, change before genesis)

| Parameter            | Value                          | Why |
|----------------------|--------------------------------|-----|
| Name / Ticker        | BigCoin / **BIG**              | Reuse existing brand |
| Base to fork         | **Litecoin Core** (Bitcoin fork, Scrypt) | Most exchange-integrated, simplest PoW change |
| PoW algorithm        | **Scrypt** (or RandomX for CPU-friendly) | Scrypt = proven & GPU-mineable; RandomX = "mine on any PC" |
| Max supply           | 84,000,000 BIG                 | Litecoin-like scarcity |
| Block time           | 2.5 minutes                    | Fast confirmations, proven |
| Initial block reward | 50 BIG                         | Familiar economics |
| Halving interval     | 840,000 blocks (~4 yrs)        | Predictable issuance |
| Premine              | **≤ 1%** (or 0)                | Large premines look like scams → exchanges reject |
| Address prefix       | custom (e.g. "B..." / bech32 `big1`) | Brand identity |
| P2P / RPC ports      | custom (avoid 8333/9333)       | Network separation |
| Genesis block        | freshly mined, new magic bytes | Unique network |

## 2. Technical build phases

- [ ] **Phase 0 — Toolchain**: Linux/WSL build env, C++ toolchain, clone Litecoin Core source.
- [ ] **Phase 1 — Rebrand & params**: edit `chainparams.cpp` (magic bytes, ports, prefixes,
      supply, reward, halving), mine a new **genesis block**, set checkpoints, add DNS seeds.
- [ ] **Phase 2 — Build**: compile `bigcoind` (daemon) + `bigcoin-qt` (**desktop wallet — free from the fork**).
- [ ] **Phase 3 — Testnet**: launch 3–5 seed nodes on cloud VPS, test mining, sends, reorgs, sync.
- [ ] **Phase 4 — Security audit**: professional review before mainnet ($10k–$50k). Non-negotiable if it holds value.
- [ ] **Phase 5 — Block explorer**: deploy open-source explorer (e.g. BTC RPC Explorer / Iquidus).
- [ ] **Phase 6 — Mainnet launch**: publish binaries, seed nodes, genesis, mining pool config.
- [ ] **Phase 7 — Mining accessibility**: publish `getblocktemplate` config; set up/stratum pool so "people can mine."
- [ ] **Phase 8 — Wallets**: desktop (done via Qt), + optional mobile (fork an open-source wallet).

## 3. Getting listed on exchanges (the hard, expensive part)

**DEX first (realistic, fast):** wrap BIG or bridge to Ethereum/BSC → list on Uniswap/PancakeSwap
by adding liquidity. Instant, permissionless, no listing fee. This is where new coins get their first market price.

**CEX (hard, costly):**
- Small/mid CEX: often **$5k–$100k+ listing fees**, needs volume, community, legal opinion.
- Tier-1 (Binance/Coinbase): effectively unattainable for a brand-new solo coin; needs huge
  traction and passes strict legal/security review.
- Exchanges require: working chain + explorer + wallet, deposit/withdrawal integration (they run
  your node), liquidity, an active community, and usually a **legal opinion the token isn't a security.**

## 4. Legal & compliance (READ THIS — it makes or breaks you)

- **Securities law (Howey test):** if BIG is marketed/sold as an investment, it may be a security.
  Getting this wrong is **criminal**, not just a fine. Get a crypto lawyer's opinion letter.
- **Money transmission / MSB:** issuing/exchanging may require FinCEN registration + state licenses (US), plus **KYC/AML**.
- **Jurisdiction:** many founders incorporate in crypto-clearer jurisdictions with proper counsel.
- **No misrepresentation:** never promise returns or imply guaranteed value → that's how "rug pulls" get prosecuted.
- **Tax:** issuance, premine, and sales have tax consequences. Talk to an accountant.

## 5. Realistic cost & time

- Technical fork + testnet: **days–weeks** (I can do most of this with you).
- Credible mainnet (audit, seed infra, explorer, wallets, liquidity): **months + real money** ($20k–$100k+ typical).
- CEX listing: additional fees + legal + traction. Budget accordingly.

## 6. What I (Claude) can build with you right now

- ✅ Rebranded fork config: chainparams, genesis miner script, seed setup.
- ✅ Block explorer deployment + a polished public website / landing page.
- ✅ Mining pool + miner setup docs so "people can mine."
- ✅ Wallet UI/UX polish; scripts to package desktop wallet builds.
- ❌ I can't: compile Bitcoin Core in this sandbox, register a company, pay exchange fees, or give legal advice.

## 7. Recommended first move

Start **Phase 0–1 on your machine (WSL/Linux)**: I'll generate the exact rebrand + genesis
scripts and walk the Litecoin Core fork step-by-step, producing a running `bigcoind` testnet.
That gets you a *real, mineable coin with a real wallet* to build everything else on.

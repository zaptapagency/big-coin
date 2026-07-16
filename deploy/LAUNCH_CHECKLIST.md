# MoonBite Launch Checklist

Living launch tracker. Update the status boxes as work lands. Companion docs:
`RUNBOOK.md` (VPS route), `railway-node/DEPLOY.md` (Railway route).

_Last updated: 2026-07-16_

---

## Launch readiness (RAG)

| Workstream | Status | Notes |
|---|---|---|
| Website (GitHub Pages) | 🟢 Live | `zaptapagency.github.io/big-coin` verified |
| Deploy tooling (Railway kit) | 🟢 Done | `deploy/railway-node/` on `main` |
| Qt / client rebrand | 🟡 Amber | Committed in source; not yet in shipped binaries |
| Live seed node | 🔴 Red | No node exists yet |
| Chain liveness | 🔴 Red | Height 0 until a miner runs |

> **Perception risk:** the website is live, so visitors will assume the network
> is live. Closing the node/liveness gap is the critical path.

---

## Definition of Done — "MoonBite is live"

- [ ] Node reachable on public P2P 9444, block height increasing
- [ ] A second machine syncs from the seed (`bigcoin-cli addnode <ip>:9444 onetry`)
- [ ] Explorer serves real chain data (no demo banner)
- [ ] Website links to the live explorer

---

## Critical path (risk-first sequence)

Highest-uncertainty item is scheduled first: the node blocks everything else and
is the least-proven piece.

### 1. Node spike (timeboxed) — 🔴 not started
- [ ] Deploy `moonbite-node` on Railway (Root `/`, Dockerfile `deploy/railway-node/Dockerfile`)
- [ ] Attach Volume mounted at `/data`
- [ ] Set `BIGCOIN_RPC_USER`, `BIGCOIN_RPC_PASSWORD`, `MINE=1`
- [ ] Enable TCP Proxy on **9444 only**
- [ ] **Success gate:** deploy logs show height rising
- [ ] **Fail gate:** if RandomX/CPU can't sustain it → pivot to VPS (`RUNBOOK.md`)

### 2. Explorer wiring — 🔴 blocked on #1
- [ ] Deploy `moonbite-explorer` (Root `explorer`)
- [ ] Vars: `BIGCOIN_RPC_HOST=moonbite-node.railway.internal`, port 9445, same creds
- [ ] Vars: `BIGCOIN_NAME=MoonBite`, `BIGCOIN_TICKER=MBITE`
- [ ] Generate public domain
- [ ] **Success gate:** real block/tx/search data, no demo banner

### 3. Network durability — 🔴 blocked on #1
- [ ] Stand up a **second** seed node (removes single point of failure)
- [ ] Confirm cross-node sync

### 4. Finalize (fast-follow, NOT critical path) — ⚪ deferred
- [ ] Bake seed(s) into `vSeeds`/`vFixedSeeds` (`src/chainparams.cpp`)
- [ ] Rebuild `moon1` binaries; refresh `release/SHA256SUMS`
- [ ] Add live explorer link to the website

---

## Risk register

| # | Risk | Prob | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R1 | Railway node can't sustain P2P / RandomX CPU | High | High | VPS is real home; Railway = bootstrap only | You |
| R2 | Volume not mounted → chain wiped on redeploy | Med | High | `/data` volume is step 1, not optional | You |
| R3 | RPC 9445 exposed publicly | Low | Critical | Only 9444 gets the TCP proxy | You |
| R4 | `big1` binary shows old address prefixes | High | Low | Cosmetic; rebuild `moon1` in step 4 | You |
| R5 | Single seed = single point of failure | High | Med | Add 2nd seed before public promotion (step 3) | You |

---

## Scope guardrail

Do **not** pull the `moon1` binary rebuild (step 4) into the launch critical
path. It is cosmetic (address-prefix display only) and network-compatible with
the shipped `big1` build. Bundling it in just delays a reachable network for no
functional gain — ship it as a fast-follow.

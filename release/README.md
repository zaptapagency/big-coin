# MoonBite Core — Release Binaries

MoonBite (**MBITE**) is a proof-of-work Layer-1 coin, forked from Litecoin Core v0.21.5.5.
These are Linux x86-64 binaries built on Ubuntu 22.04 (glibc 2.35).

## Chain parameters

| Parameter        | Value                        |
|------------------|------------------------------|
| Ticker           | MBITE                          |
| PoW algorithm    | Scrypt                       |
| Max supply       | 84,000,000 MBITE               |
| Block time       | 2.5 minutes                  |
| Initial reward   | 50 MBITE                       |
| Halving interval | 840,000 blocks (~4 years)    |
| Address prefix   | bech32 `big1…`               |
| P2P port         | 9444 (mainnet) / 19555 (testnet) |
| RPC port         | 9445 (mainnet) / 19555 (testnet) |

### Genesis blocks (baked in)
- **mainnet** `4deaa9d06e7a01728cbe3816a8176ea452ccf3e446cee5d02f56e8e5be46d662` (nonce 531891)
- **testnet** `6cd25461e9837bb87af4a1f775b67580f8be6762c5f988f4b95ae2ab365895ef` (nonce 210032)
- **regtest** `66c4bfe925b1af8ea1ae34cd1b1570737de340cab162b1d2fbedfb53ed92074c` (nonce 1)

## Contents (`bin/`)
- `moonbited` — full node daemon
- `moonbite-cli` — RPC command-line client
- `moonbite-qt` — **desktop GUI wallet** (Qt5)
- `moonbite-tx` — raw transaction utility
- `moonbite-wallet` — offline wallet tool

Verify downloads against `SHA256SUMS.txt`.

## Desktop wallet
Launch the GUI wallet with `./bin/moonbite-qt` (mainnet) or `./bin/moonbite-qt -testnet`.
It runs an integrated node and reports client name `MoonBiteCore` on the network.

## Quick start (regtest — instant local mining)
```bash
./bin/moonbited -regtest -rpcuser=big -rpcpassword=big -daemon
CLI="./bin/moonbite-cli -regtest -rpcuser=big -rpcpassword=big"
$CLI createwallet "wallet"
ADDR=$($CLI getnewaddress)
$CLI generatetoaddress 101 "$ADDR"   # mine 101 blocks (coinbase matures at 100)
$CLI getbalance                      # -> 50.00000000
$CLI sendtoaddress <dest_addr> 12.5  # send MBITE
$CLI stop
```

## Mainnet / testnet
1. Copy `moonbite.conf.example` → data dir as `moonbite.conf`, set a strong `rpcpassword`.
2. `./bin/moonbited` (mainnet) or `./bin/moonbited -testnet`.
3. See the repo `docs/` for mining, wallet, node-setup, and exchange-listing guides.

## Verified working
- **Mining:** Scrypt PoW, regtest mined 101 blocks → 50 MBITE coinbase matured.
- **Transactions:** send/receive confirmed (12.5 MBITE between two wallets, mempool → block).
- **P2P networking:** two nodes connect and sync a 10-block chain (identical tips).
- **Wallet security:** AES-256 encryption, passphrase-locked spending, HD seed, backup — all verified.
- **Block explorer:** wired to a live node, serves real block/tx data (no demo mode).
- **Branding:** `--version` reports **MoonBite Core**; window title / About dialog say
  "MoonBite Core"; network client name `MoonBiteCore` (`/MoonBiteCore:0.21.5.5/`);
  default data directory is `.moonbite` (Linux) / `MoonBite` (Windows/macOS).

## Status / known remaining polish
- Mainnet has no DNS seeds yet (removed Litecoin's); use `deploy/` to stand up seed
  nodes on VPS hosts, then bake their IPs into chainparams before public launch.
- A few deep-menu Qt labels may still read "Litecoin" (cosmetic); core identity,
  version banner, About dialog, and data dir are all MoonBite.
- macOS/Windows native builds require cross-compiling (these are Linux x86-64).

Forked chain — **not** affiliated with or compatible with the Litecoin network
(distinct magic bytes, ports, genesis, and address prefixes).

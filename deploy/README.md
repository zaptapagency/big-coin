# BigCoin Seed-Node Deployment Kit

This is what turns "BigCoin runs on my machine" into "a public network anyone on the
internet can join." A **seed node** is a permanently-online full node with a stable
public IP that new nodes contact first to discover the rest of the peer network.

You need **at least 2–3 seed nodes on separate VPS hosts** (different providers/regions
is best) before a credible mainnet launch.

## Files
| File | Purpose |
|------|---------|
| `setup-seednode.sh` | One-shot provisioner for a fresh Ubuntu 22.04 VPS |
| `bigcoind.service`  | systemd unit (auto-start, restart-on-failure, hardened) |
| `bigcoin.conf`      | Seed-node config (public P2P, private RPC) |

## Quick deploy (per VPS)
```bash
# 1. Copy the release binaries + this deploy/ folder to the VPS, then:
sudo bash setup-seednode.sh ./bigcoind ./bigcoin-cli

# 2. Confirm it's running and reachable
systemctl status bigcoind
bigcoin-cli -conf=/etc/bigcoin/bigcoin.conf getnetworkinfo
```

The script installs binaries to `/usr/local/bin`, creates an unprivileged `bigcoin`
system user, generates **random RPC credentials**, installs the systemd service,
and opens **only** the P2P port (9444) in the firewall — RPC stays on localhost.

## Wiring the seeds together
1. Deploy the script on each VPS. Note each host's **public IP**.
2. On every node, uncomment the `addnode=` lines in `/etc/bigcoin/bigcoin.conf`
   and fill in the *other* seeds' IPs, then `systemctl restart bigcoind`.
3. Verify mesh connectivity:
   ```bash
   bigcoin-cli -conf=/etc/bigcoin/bigcoin.conf getpeerinfo | grep addr
   ```

## Baking seeds into the client (before public release)
So that *end users* auto-discover the network without manual `addnode`, add your seed
IPs to `src/chainparams.cpp` in `CMainParams`:
- `vSeeds.emplace_back("seed1.bigcoin.org");`  (if you run a DNS seeder), and/or
- hard-coded IPs via `vFixedSeeds` (see `contrib/seeds/` upstream tooling).
Then rebuild and re-release binaries.

## Security notes
- **Never expose RPC (9445) to the internet.** The config binds it to 127.0.0.1 only.
- Prefer `rpcauth=` (hashed) over a plaintext `rpcpassword=` — generate with
  `share/rpcauth/rpcauth.py` from the source tree.
- Keep the OS patched; the systemd unit already applies `NoNewPrivileges`,
  `ProtectSystem`, `ProtectHome`, and `PrivateTmp`.
- Seed nodes hold **no wallet** — they route blocks/transactions only, so a
  compromise cannot steal coins, but keep them patched to protect the network.

## Cost reality
A small VPS (1–2 GB RAM) per seed is enough at launch (~$5–10/mo each). Budget for
3 seeds + 1 explorer host. This is infrastructure you must keep running indefinitely —
if all seeds go down, new users can't find the network.

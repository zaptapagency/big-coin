"""Scaled crash-recovery test: launch N nodes, converge, crash half, restart, verify.

This stress-tests the same crash-recovery + disk-persistence path validated on
3 nodes, but at N nodes to observe how the architecture behaves as it grows.
"""

import os
import sys
import csv
import time
import subprocess
import requests

N = int(sys.argv[1]) if len(sys.argv) > 1 else 10
P2P_BASE = 9100          # node i -> p2p 9100+i+1, rpc (p2p-1000)
MINE_ADDR = "1huQf7Cq55ch8nA3banGNPFfm17pkLW2gWxANNEtqrYU34RuNY"
RAM_ABORT_MB = 28000     # abort if total python RSS crosses this (stay under ~28 GB)


def total_python_rss_mb():
    """Sum RSS of all python.exe processes (Windows tasklist)."""
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq python.exe", "/FO", "CSV"], text=True)
    except Exception:
        return 0.0
    total = 0
    for r in csv.reader(out.splitlines()[1:]):
        if len(r) >= 5:
            total += int(r[4].replace(",", "").replace(" K", ""))
    return total / 1024


def ram_guard():
    used = total_python_rss_mb()
    if used > RAM_ABORT_MB:
        print(f"!! RAM guard tripped: {used:.0f} MB > {RAM_ABORT_MB} MB — aborting test")
        return False, used
    return True, used


def p2p_port(i): return P2P_BASE + i + 1
def rpc_port(i): return p2p_port(i) - 1000
def node_id(i):  return f"n{i}"


def launch(i):
    logf = open(f"scale_{node_id(i)}.log", "w")
    return subprocess.Popen(
        [sys.executable, "node_rpc_server.py", node_id(i), str(p2p_port(i)), str(rpc_port(i))],
        stdout=logf, stderr=subprocess.STDOUT,
    )


def height(i):
    try:
        resp = requests.get(
            f"http://127.0.0.1:{rpc_port(i)}/api/blockchain/info", timeout=3
        )
        return resp.json().get("height")
    except Exception:
        return None


def connect(i, j):
    try:
        requests.post(
            f"http://127.0.0.1:{rpc_port(i)}/rpc",
            json={
                "method": "connect_peer",
                "params": {"host": "127.0.0.1", "port": p2p_port(j)},
            },
            timeout=3,
        )
    except Exception:
        pass


def peers_of(i):
    """Bounded-degree hub+ring: node connects to hub(0) and its ring neighbor.

    Keeps total connections ~2N (linear) instead of N^2, so RAM is the real
    limit. Hub node 0 is the guaranteed sync source and is never crashed.
    """
    links = set()
    if i != 0:
        links.add(0)          # everyone -> hub
        links.add(i - 1)      # ring back-link
    return links


def wait_converge(indices, timeout=60):
    """Wait until all given nodes report the same (non-None) height."""
    start = time.time()
    while time.time() - start < timeout:
        hs = [height(i) for i in indices]
        if all(h is not None for h in hs) and len(set(hs)) == 1:
            return hs[0]
        time.sleep(2)
    return {i: height(i) for i in indices}


def main():
    # fresh chaindata for the test node ids
    for i in range(N):
        f = os.path.join("chaindata", f"{node_id(i)}.jsonl")
        if os.path.exists(f):
            os.remove(f)

    print(f"=== Launching {N} nodes (hub+ring topology) ===")
    procs = []
    BATCH = 25
    for i in range(N):
        procs.append(launch(i))
        if (i + 1) % BATCH == 0:
            time.sleep(1.5)  # let the batch's servers bind before the next wave
            ok, used = ram_guard()
            if not ok:
                for p in procs:
                    p.terminate()
                return 1
    time.sleep(N * 0.05 + 8)
    ok, used = ram_guard()
    print(f"    RAM after launch: {used:.0f} MB")
    if not ok:
        for p in procs:
            p.terminate()
        return 1

    print("=== Connecting bounded-degree topology ===")
    t0 = time.time()
    edges = 0
    for i in range(N):
        for j in peers_of(i):
            connect(i, j)
            edges += 1
    print(f"    {edges} directed connects in {time.time()-t0:.1f}s (~{edges/N:.1f}/node)")
    time.sleep(3)

    print("=== Mining on n0 up to height 15 ===")
    requests.post(
        f"http://127.0.0.1:{rpc_port(0)}/api/mining/start",
        json={"address": MINE_ADDR},
        timeout=5,
    )
    while (height(0) or 0) < 15:
        time.sleep(1)
    requests.get(f"http://127.0.0.1:{rpc_port(0)}/api/mining/stop", timeout=5)

    h = wait_converge(range(N), timeout=180)
    print(f"    all {N} nodes converged at height: {h}")

    # crash every other node (except hub 0) so survivors keep the ring + hub alive
    crash = [i for i in range(1, N) if i % 2 == 1]
    print(f"=== Crashing {len(crash)} nodes (odd indices, hub survives) ===")
    for i in crash:
        procs[i].terminate()
    time.sleep(3)

    print("=== Mining 5 more blocks on n0 while they are down ===")
    target = (height(0) or 0) + 5
    requests.post(
        f"http://127.0.0.1:{rpc_port(0)}/api/mining/start",
        json={"address": MINE_ADDR},
        timeout=5,
    )
    while (height(0) or 0) < target:
        time.sleep(1)
    requests.get(f"http://127.0.0.1:{rpc_port(0)}/api/mining/stop", timeout=5)
    print(f"    survivors advanced to height {height(0)}")

    print("=== Restarting crashed nodes (should restore from disk, then sync) ===")
    for i in crash:
        procs[i] = launch(i)
    time.sleep(N * 0.15 + 8)
    for i in crash:
        for j in peers_of(i):
            connect(i, j)

    final = wait_converge(range(N), timeout=300)
    print(f"=== FINAL convergence height: {final} ===")
    _, used = ram_guard()
    print(f"    peak RAM (python total): {used:.0f} MB")

    # report restore-from-disk evidence
    print("=== Restore-from-disk log lines ===")
    for i in crash:
        try:
            with open(f"scale_{node_id(i)}.log") as fh:
                for line in fh:
                    if "Restored" in line:
                        print("   ", line.strip())
        except Exception:
            pass

    ok = isinstance(final, int)
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'} - {N} nodes, {len(crash)} crashed+recovered")

    print("=== Tearing down ===")
    for p in procs:
        try:
            p.terminate()
        except Exception:
            pass
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

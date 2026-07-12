# MyCoin Shared State Setup

## Problem
Web Dashboard and Desktop GUI each create their own `Node` instance, so they don't share the same blockchain, addresses, or mining state.

## Solution: Use Shared State Server

### Setup (3 terminals)

#### **Terminal 1: Start Shared State Server** (Do this FIRST)
```bash
python shared_state.py
# Output: [Shared State Server] Listening on 127.0.0.1:9999
```

#### **Terminal 2: Start Web Dashboard** (connects to shared state)
```bash
# Modify web_app.py line 38 from:
#   app.node: Optional[Node] = None
# to:
#   from shared_client import SharedStateClient
#   shared_client = SharedStateClient()

python web_app.py
# Now http://localhost:5000 uses shared blockchain
```

#### **Terminal 3: Start Desktop GUI** (connects to shared state)
```bash
# Modify gui.py line 30 from:
#   self.node = Node("gui-app", coinbase_maturity=0)
# to:
#   from shared_client import SharedStateClient
#   self.shared_client = SharedStateClient()

python gui.py
# Now PyQt6 window uses shared blockchain
```

---

## What This Does

- **Shared State Server** (`shared_state.py`, port 9999):
  - Holds the single `Node` instance
  - Tracks all generated addresses
  - Handles mining operations (thread-safe)
  - Returns state via JSON RPC

- **Web Dashboard** (`web_app.py`):
  - Calls `SharedStateClient` instead of `Node` directly
  - Same address generation → same addresses
  - Same mining → same blockchain

- **Desktop GUI** (`gui.py`):
  - Calls `SharedStateClient` instead of `Node` directly
  - Same addresses as web app
  - Same blockchain state

---

## API (SharedStateClient)

```python
client = SharedStateClient("127.0.0.1", 9999)

# Generate new address
result = client.new_key()
# {"address": "1ABC...", "pubkey_hash": "def456..."}

# Get balance
result = client.get_balance()
# {"balance_coins": 150.0, "balance_cents": 15000000000}

# Start mining
result = client.start_mining(blocks=5, address="1ABC...")
# {"status": "mining started"}

# Check mining progress
result = client.mining_status()
# {"is_mining": true, "blocks_mined": 2, "blocks_to_mine": 5, ...}

# Get blockchain info
result = client.blockchain_info()
# {"height": 5, "tip_hash": "0000abc...", "total_money_coins": 250.0, ...}
```

---

## Benefits

✅ **Same blockchain** — all UIs see the same state
✅ **Same addresses** — generate on web, mine on desktop, see balance on mobile
✅ **Thread-safe** — mining is atomic across UIs
✅ **Real-time sync** — all UIs query the same source of truth

---

## Files Created

- `shared_state.py` — Shared state server (JSON RPC over TCP)
- `shared_client.py` — Client library for web_app & gui.py

## Next Steps

1. Edit `web_app.py` to use `SharedStateClient` (replace `get_node()`)
2. Edit `gui.py` to use `SharedStateClient` (replace direct `Node()`)
3. Run: `python shared_state.py` (Terminal 1)
4. Run: `python web_app.py` (Terminal 2)
5. Run: `python gui.py` (Terminal 3)
6. Generate address on Web → Mine on Desktop → Check balance on Mobile ✓

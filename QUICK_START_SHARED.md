# MyCoin — Shared State Quick Start

## Problem Solved ✓

**Desktop GUI and Web Dashboard now share the same blockchain, addresses, and mining state!**

---

## How It Works

```
┌─────────────────────────────────┐
│  Shared State Server (port 9999)│  ← Holds single Node instance
│  shared_state.py                │  ← All address/mining data here
└─────────────────────────────────┘
         ▲                   ▲
         │                   │
    JSON RPC             JSON RPC
      over TCP             over TCP
         │                   │
    ┌────┴────┐         ┌────┴────┐
    │  Web    │         │ Desktop │
    │Dashboard│         │  GUI    │
    │ (browser)│        │(PyQt6)  │
    └─────────┘         └─────────┘
   localhost:5000      Native window
```

All 3 apps now use the same blockchain! ✓

---

## Setup (3 Terminals)

### Terminal 1: Start Shared State Server (port 9999)
```bash
cd C:\Users\usman\Desktop\BigCoinBB
python shared_state.py
```
**Output:** `[Shared State Server] Listening on 127.0.0.1:9999`

### Terminal 2: Start Web Dashboard (port 5000)
```bash
python web_app_shared.py
```
**Output:** `Running on http://localhost:5000`

### Terminal 3: Start Desktop GUI
```bash
python gui_shared.py
```
**Output:** PyQt6 window opens (connects to shared state)

---

## Test It Works! ✓

1. **On Web Dashboard** (localhost:5000):
   - Click "Wallet" tab
   - Click "Generate New Address"
   - Copy the address

2. **On Desktop GUI**:
   - Address field **automatically shows the same address**
   - Tab to "Mining"
   - Paste the address (or it's already filled)
   - Click "Start Mining" → Blocks mine on Desktop GUI

3. **Back to Web Dashboard**:
   - Refresh page
   - Click "Blockchain" tab
   - Height **increased** (same blocks mined on Desktop show up here)
   - Total money **increased**

**Result:** Both UIs show the exact same blockchain! 🎉

---

## Files

| File | Purpose |
|------|---------|
| `shared_state.py` | Shared state server (holds Node, handles all requests) |
| `shared_client.py` | Client library (used by web & desktop apps) |
| `web_app_shared.py` | Web dashboard (uses shared state) |
| `gui_shared.py` | Desktop GUI (uses shared state) |
| `web_app.py` | Old web dashboard (standalone, can still use) |
| `gui.py` | Old desktop GUI (standalone, can still use) |

---

## API (What Shared State Provides)

```python
from shared_client import SharedStateClient
client = SharedStateClient("127.0.0.1", 9999)

# Generate address
result = client.new_key()
# {"address": "1ABC...", "pubkey_hash": "def..."}

# Get balance
result = client.get_balance()
# {"balance_coins": 150.0, "balance_cents": 15000000000}

# Start mining
result = client.start_mining(blocks=5, address="1ABC...")
# {"status": "mining started"}

# Check mining progress
result = client.mining_status()
# {"is_mining": true, "blocks_mined": 2, ...}

# Blockchain info
result = client.blockchain_info()
# {"height": 5, "tip_hash": "0000...", ...}
```

---

## Workflow Example

```bash
# Terminal 1
$ python shared_state.py
[Shared State Server] Listening on 127.0.0.1:9999
[Shared State Server] Node initialized (genesis block created)

# Terminal 2
$ python web_app_shared.py
 * Running on http://127.0.0.1:5000

# Terminal 3
$ python gui_shared.py
[Connected to Shared State Server]
```

**Now:**
- 🌐 Open **http://localhost:5000** in browser (Web Dashboard)
- 🖥️ PyQt6 window shows Desktop GUI
- 💰 Generate address on Web → Mine on Desktop → See updated balance on Web
- 📊 All 3 UIs show the same blockchain state

---

## Benefits vs Original

| Feature | Original | Shared State |
|---------|----------|--------------|
| Same addresses? | ❌ No | ✅ Yes |
| Same blockchain? | ❌ No | ✅ Yes |
| Same mining? | ❌ No | ✅ Yes |
| Synchronized state? | ❌ No | ✅ Yes |
| Easy to use? | ✅ Yes | ✅ Yes (3 terminals) |

---

## Troubleshooting

**Web Dashboard says "Connection refused"?**
- Make sure `shared_state.py` is running first
- Check port 9999 is not blocked

**Desktop GUI crashes on startup?**
- Run `shared_state.py` first
- Check error message for port/connection issues

**Addresses don't match?**
- Make sure you're using `*_shared.py` versions, not originals
- Restart all 3 servers

---

## Back to Standalone Mode

If you want the original independent apps:
```bash
# Original Web Dashboard (separate blockchain)
python web_app.py

# Original Desktop GUI (separate blockchain)
python gui.py
```

But they won't share state. Use shared versions for synchronized UIs!

---

## Mobile App

Mobile app (`flutter`) still connects to the web backend API:
```bash
cd mobile
flutter pub get
flutter run
```

Mobile → connects to http://localhost:5000 → which connects to shared_state.py ✓

---

**Now all your UIs are in sync!** 🚀

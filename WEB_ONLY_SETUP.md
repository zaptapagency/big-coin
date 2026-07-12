# MyCoin — Web-Only Setup (No Desktop GUI)

If the Desktop GUI (PyQt6) is not working, you can use **Web Dashboard only**.

## Quick Setup (2 Terminals)

### Terminal 1: Start Shared State Server
```bash
cd C:\Users\usman\Desktop\BigCoinBB
python shared_state.py
```

Output should show:
```
[Shared State Server] Listening on 127.0.0.1:9999
[Shared State Server] Node initialized (genesis block created)
```

### Terminal 2: Start Web Dashboard
```bash
cd C:\Users\usman\Desktop\BigCoinBB
python web_app_shared.py
```

Output should show:
```
Running on http://127.0.0.1:5000
```

### Browser: Open Dashboard
```
http://localhost:5000
```

You should see:
- Dashboard with blockchain info
- Wallet tab (generate addresses)
- Mining tab (mine blocks)
- Blockchain tab (view chain)

---

## Features (Web Only)

✓ Generate wallet addresses
✓ Check balance
✓ Mine blocks with progress tracking
✓ View blockchain info (height, tip hash, total money)
✓ Real-time updates (3-second refresh)
✓ Dark mode toggle
✓ Fully responsive (works on mobile too!)

---

## Usage

1. **Generate Address:**
   - Click "Wallet" tab
   - Click "Generate New Address"
   - Copy the address

2. **Mine Blocks:**
   - Click "Mining" tab
   - Paste address in "Miner Address" field
   - Enter number of blocks (default 1)
   - Click "Start Mining"
   - Watch progress bar

3. **View Blockchain:**
   - Click "Blockchain" tab
   - See: Height, Tip Hash, Total Money, Tx Count
   - Click "Refresh" for latest data

---

## Why Use Web-Only?

**Advantages:**
- No GUI framework needed (no PyQt6)
- Works on any device with a browser
- Easy to use (point & click)
- Real-time updates
- No extra window to manage

**Disadvantages:**
- Browser-based (slower than native GUI)
- Requires refresh to see updates
- No offline mode

---

## If Desktop GUI Doesn't Open

**Option 1: Use Web Dashboard (This Guide)**
- Just 2 terminals + browser
- Simpler setup
- Works everywhere

**Option 2: Test GUI**
```bash
python gui_test.py
```
This opens a simple test window. If it works, the GUI framework is OK.

**Option 3: Use CLI**
```bash
python cli.py newkey                    # Generate address
python cli.py mine --count 5            # Mine 5 blocks
python cli.py info                      # Check chain info
python cli.py subsidy --height 210000   # Check block reward
```

---

## API Endpoints (For Developers)

If you want to integrate with the web API:

```bash
# Generate new address
curl http://localhost:5000/api/wallet/new

# Get balance
curl http://localhost:5000/api/wallet/balance

# Get blockchain info
curl http://localhost:5000/api/blockchain/info

# Start mining
curl -X POST http://localhost:5000/api/mining/start \
  -H "Content-Type: application/json" \
  -d '{"blocks": 5, "address": "1ABC123..."}'

# Check mining status
curl http://localhost:5000/api/mining/status

# Stop mining
curl http://localhost:5000/api/mining/stop
```

---

## Recommended: Use Both!

If Desktop GUI works, use it alongside Web:
- **Desktop GUI** for serious mining (no UI freeze)
- **Web Dashboard** for monitoring from other devices
- **Same blockchain** (both connect to shared_state.py)

But if Desktop GUI doesn't work, **Web-Only is fully functional!** ✓

---

## Summary

**2-Terminal Web-Only Setup:**
```bash
Terminal 1: python shared_state.py
Terminal 2: python web_app_shared.py
Browser: http://localhost:5000
```

That's it! No Desktop GUI needed. 🌐

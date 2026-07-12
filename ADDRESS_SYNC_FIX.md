# MyCoin — Address Sync Fix

## Problem

Addresses appear different on Web and Desktop GUI after clicking "Generate New Key"

## Root Cause

Each time you click "Generate New Key", a **new address is created** (this is correct behavior - each keypair is unique).

The issue is:
1. You generate an address on **Web Dashboard** → shows Address A
2. You generate a **different** address on **Desktop GUI** → shows Address B (different because it's a new keypair!)
3. They don't match because they're supposed to be different

## Solution: Use Same Address

### Method 1: Generate Once on Web, Use on Desktop (BEST)

```
1. Web Dashboard (localhost:5000)
   - Click "Wallet" tab
   - Click "Generate New Address"
   - COPY the address (e.g., 1ABC123...)

2. Desktop GUI
   - Click "Wallet" tab
   - See the address field (read-only or auto-filled)
   - IF not auto-filled, it means shared state isn't connected

3. On Desktop Mining tab
   - Paste the copied address
   - Click "Start Mining"

Result: Both apps mine to THE SAME address!
```

### Method 2: Check Shared State Connection

If addresses still don't match, the shared state server might not be connected:

```bash
# Terminal 1 - Is shared_state.py running?
python shared_state.py
# Should show: [Shared State Server] Listening on 127.0.0.1:9999

# Terminal 2 - Is web_app_shared.py running?
python web_app_shared.py
# Should connect WITHOUT errors

# Terminal 3 - Is gui_shared.py running?
python gui_shared.py
# Should show: [Connected to Shared State Server]
```

### Method 3: Share Addresses via API

Web Dashboard has an API endpoint to list all generated addresses:

```bash
curl http://localhost:5000/api/wallet/get-addresses
```

This shows all addresses generated through the shared state server.

## How Shared State Should Work

```
shared_state.py (port 9999)
  └─ Stores: generated_addresses = {}
             (persists all addresses ever created)

Web Dashboard (port 5000)
  └─ Click "Generate New Address"
  └─ Calls: shared_client.new_key()
  └─ Which calls: shared_state.py
  └─ Returns: newly generated address
  └─ Stores in: generated_addresses dict

Desktop GUI
  └─ Can call: shared_client.get_addresses()
  └─ Gets ALL addresses from shared_state.py
  └─ Shows them in dropdown (if we add that feature)
```

## Why This Happens

Each time you call `generate_keypair()`, it creates a **brand new keypair**:

```python
from transaction import generate_keypair
sk1, pub1 = generate_keypair()  # Unique keypair #1
sk2, pub2 = generate_keypair()  # Unique keypair #2 (different!)
```

This is **correct behavior** for a wallet. You're supposed to have multiple addresses.

## Quick Fix

1. **Make sure all 3 processes are running:**
   ```bash
   Terminal 1: python shared_state.py
   Terminal 2: python web_app_shared.py
   Terminal 3: python gui_shared.py
   ```

2. **Generate address ONCE on Web:**
   ```
   Web Dashboard → Wallet → "Generate New Address"
   Copy the address
   ```

3. **Use SAME address on Desktop:**
   ```
   Desktop GUI → Mining → Paste address
   Click "Start Mining"
   ```

4. **Both apps now mine to SAME address** ✓

## Testing

To verify they're synced:

```bash
# Web Dashboard
1. Go to http://localhost:5000
2. Wallet tab → Generate New Address → copy it

# Desktop GUI
3. Check the address field → should show SAME address
   (if shared state is working)

# Mining
4. Desktop → Mining tab → Mine 5 blocks
5. Web → Blockchain tab → Refresh
6. See height increased (same blockchain!)
7. Web → Wallet tab → Balance increased (same mining!)
```

If all 3 show the same values, **addresses and mining are synced!** ✓

## If Still Not Working

**Make sure:**
- [ ] shared_state.py is running on port 9999
- [ ] web_app_shared.py is running on port 5000
- [ ] gui_shared.py is running and shows "Connected"
- [ ] No firewall blocking port 9999
- [ ] Using web_app_SHARED.py (not web_app.py)
- [ ] Using gui_SHARED.py (not gui.py)

If all above are correct and still not syncing:
```bash
# Restart everything (fresh state)
# Kill all 3 processes
# Start again in order: shared_state → web_app_shared → gui_shared
```

---

**TL;DR:** Generate address ONCE on Web, use SAME address on Desktop = addresses sync! ✓

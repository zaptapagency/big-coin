# BigCoin P2P Network Setup Guide

## What is P2P Network?

Instead of one central `shared_state.py` server, each user runs their own **Full Node** that:
- Stores complete blockchain copy
- Validates blocks independently
- Mines blocks locally
- Connects to peers for synchronization
- Broadcasts transactions/blocks

**Architecture:**
```
User 1 (Alice)       User 2 (Bob)        User 3 (Charlie)
    Node 1  ←————→    Node 2  ←————→      Node 3
      ↓               ↓                     ↓
  Blockchain      Blockchain           Blockchain
  Mining          Mining               Mining
  Wallet          Wallet               Wallet
```

---

## Quick Start (3 Minutes)

### Step 1: Start Three Nodes

```bash
# Double-click this file:
START_NODE_NETWORK.bat
```

This will open 3 command windows:
- **Alice** (Port 9001 P2P, 8001 RPC)
- **Bob** (Port 9002 P2P, 8002 RPC)
- **Charlie** (Port 9003 P2P, 8003 RPC)

Wait for each to show:
```
[node_id] P2P Server listening on 127.0.0.1:PORT
```

### Step 2: Connect the Nodes

In a new command prompt, run:
```bash
python connect_nodes.py
```

You should see:
```
Alice:
  RPC Port: 8001
  P2P Port: 9001
  Height: 1
  Connected Peers: 2
```

### Step 3: Test Mining

Open your browser and go to:
```
http://localhost:8001
```

Now you can:
- ✓ Generate addresses
- ✓ Mine blocks (they sync to peers!)
- ✓ Check blockchain info
- ✓ See connected peers

---

## How It Works

### Node Startup (`node_rpc_server.py`)

```python
# 1. Create full node
node = BigCoinFullNode("alice", host="127.0.0.1", port=9001)

# 2. Start P2P network server (listens for peer connections)
node.start_server()

# 3. Start RPC server (clients connect here via HTTP)
rpc_server = NodeRPCServer(node, rpc_host="127.0.0.1", rpc_port=8001)
rpc_server.run()
```

### Peer Connection

**Alice connects to Bob:**

```
Alice sends:
  {
    "type": "handshake",
    "node_id": "alice",
    "host": "127.0.0.1",
    "port": 9001,
    "version": "1.0.0"
  }

Bob receives and sends back:
  {
    "type": "handshake",
    "node_id": "bob",
    "host": "127.0.0.1",
    "port": 9002,
    "version": "1.0.0",
    "blockchain_height": 1
  }

✓ Connection established!
```

### Block Broadcasting

**Alice mines a block:**

```python
1. Alice mines block #2
2. Alice broadcasts to peers:
   {
     "type": "new_block",
     "block": { ... block data ... },
     "node_id": "alice"
   }

3. Bob receives and validates
4. Bob adds to his blockchain
5. Bob broadcasts to Charlie
6. Network synchronized!
```

### Blockchain Sync

**Periodic synchronization (every 10 seconds):**

```python
if peer.height > my.height:
    request_blocks(start=my.height+1, end=peer.height)
```

---

## Network Architecture

### P2P Network Layer (`p2p_network.py`)

```
P2PNode
├── Server Socket (listen for peers)
├── Peer Connections (maintain connections)
├── Message Handlers
│   ├── handshake
│   ├── ping/pong
│   ├── new_block
│   ├── new_transaction
│   ├── sync_request
│   └── peer_list
└── Broadcasting
    └── Send to all peers
```

### Full Node (`full_node.py`)

```
BigCoinFullNode(P2PNode)
├── Local Blockchain (Node)
├── Mining Loop
├── Wallet/Address Management
├── Background Tasks
│   ├── Sync Loop (every 10s)
│   ├── Keep-alive Loop (every 30s)
│   └── Block Processing Loop
└── JSON-RPC Interface
```

### RPC Server (`node_rpc_server.py`)

```
NodeRPCServer
├── Flask HTTP Server
├── REST API Endpoints
│   ├── /api/wallet/*
│   ├── /api/blockchain/*
│   ├── /api/mining/*
│   ├── /api/node/*
│   └── /api/node/peers
└── JSON-RPC Endpoint
    └── /rpc (for custom clients)
```

---

## Configuration

### Ports

Each node uses 2 ports:

| Node | P2P Port | RPC Port | Access |
|------|----------|----------|--------|
| Alice | 9001 | 8001 | http://localhost:8001 |
| Bob | 9002 | 8002 | http://localhost:8002 |
| Charlie | 9003 | 8003 | http://localhost:8003 |

### Adding More Nodes

To add a 4th node (David):

```bash
python node_rpc_server.py david 9004 8004
```

Then connect:
```python
# In connect_nodes.py, add:
nodes = [
    ("alice", 8001),
    ("bob", 8002),
    ("charlie", 8003),
    ("david", 8004),  # NEW
]
```

### Custom Configuration

```bash
# Start node with custom port
python node_rpc_server.py mynode 9999 8999

# Access at:
# P2P: localhost:9999
# RPC: http://localhost:8999
```

---

## API Endpoints

### REST API

**Generate Address:**
```bash
curl http://localhost:8001/api/wallet/new
```

Response:
```json
{
  "status": "success",
  "address": "1sat2erwKtRkUvuLuiwUo6aZ3WBFkMgMQbAJECMdu...",
  "pubkey_hash": "72db82dc391b24063e59eaac72a717e1603d5fab69ad55f2f5a41b9a78556abe"
}
```

**Get Balance:**
```bash
curl http://localhost:8001/api/wallet/balance
```

**Blockchain Info:**
```bash
curl http://localhost:8001/api/blockchain/info
```

**Start Mining:**
```bash
curl -X POST http://localhost:8001/api/mining/start \
  -H "Content-Type: application/json" \
  -d '{"address": "1sat2erwKtRkUvuLuiwUo6aZ3WBFkMgMQbAJECMdu..."}'
```

**Get Connected Peers:**
```bash
curl http://localhost:8001/api/node/peers
```

**Node Statistics:**
```bash
curl http://localhost:8001/api/node/stats
```

---

## Monitoring Network

### Real-time Monitoring

```bash
python connect_nodes.py
```

Shows every 10 seconds:
```
Alice:
  RPC Port: 8001
  P2P Port: 9001
  Height: 5
  Connected Peers: 2

Bob:
  RPC Port: 8002
  P2P Port: 9002
  Height: 5
  Connected Peers: 2

Charlie:
  RPC Port: 8003
  P2P Port: 9003
  Height: 5
  Connected Peers: 2
```

### Check Network in Browser

http://localhost:8001 → Shows:
- Connected peers
- Blockchain height
- Network statistics
- Mining status

---

## Testing Scenarios

### Test 1: Mining with Sync

1. Start 3 nodes
2. Connect nodes
3. Mine on Alice: `http://localhost:8001`
4. Check Bob's blockchain: `http://localhost:8002`
   - Height should increase!
   - Blocks should synchronize!

### Test 2: Peer Discovery

1. Start Alice
2. Start Bob (alone)
3. Bob connects to Alice
4. Start Charlie (alone)
5. Charlie connects to Alice or Bob
6. All three should see each other

### Test 3: Mining Distribution

1. Generate addresses on Alice, Bob, Charlie
2. Each mines 1 block to their own address
3. Check total money: should be 150 coins (3 blocks × 50 coins)

### Test 4: Network Resilience

1. Start 3 nodes
2. Disconnect Bob (close terminal)
3. Alice & Charlie should sync
4. Restart Bob
5. Bob should catch up to height of A & C

---

## Troubleshooting

### Ports Already in Use

```
Error: Address already in use
```

**Solution:**
```bash
# Kill existing processes
taskkill /F /IM python.exe

# Or use different ports
python node_rpc_server.py alice 9100 8100
```

### Nodes Won't Connect

Make sure:
- [ ] All nodes are started
- [ ] All nodes show "P2P Server listening"
- [ ] No firewall blocking ports
- [ ] Run `python connect_nodes.py`

### Blockchain Heights Differ

This is **normal**! Nodes sync every 10 seconds. Wait 30 seconds for full synchronization.

### Blocks Not Syncing

Check in browser:
```
http://localhost:8001/api/node/peers
```

If `"connected_peers": 0`, nodes aren't connected. Run:
```
python connect_nodes.py
```

---

## What's Next?

### Phase 2: Exchange Listing

1. Deploy to cloud (AWS, DigitalOcean)
2. Run 10+ nodes (decentralized)
3. Create exchange APIs
4. List on DEX (Uniswap)

### Phase 3: Optimization

1. Better sync algorithm
2. Transaction mempool
3. Block validation caching
4. Peer scoring system

### Phase 4: Production

1. Security audit
2. Consensus hardening
3. Full test suite
4. Monitoring tools

---

## Architecture Summary

```
┌─────────────────────────────────────┐
│        User Client (Browser)        │
│  http://localhost:8001              │
└──────────────┬──────────────────────┘
               │ HTTP
               ▼
┌─────────────────────────────────────┐
│      NodeRPCServer (Flask)          │
│  REST API + JSON-RPC Endpoints      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      BigCoinFullNode                │
│ ┌──────────────────────────────────┐│
│ │  P2PNode (Network)               ││
│ │ - Peer connections               ││
│ │ - Message routing                ││
│ │ - Block broadcasting             ││
│ └──────────────────────────────────┘│
│ ┌──────────────────────────────────┐│
│ │  Node (Blockchain)               ││
│ │ - Validate blocks                ││
│ │ - Maintain chain                 ││
│ │ - Mining                         ││
│ └──────────────────────────────────┘│
└─────────────┬──────────────────────┘
              │ TCP P2P
   ┌──────────┼──────────┐
   ▼          ▼          ▼
 Alice       Bob       Charlie
```

---

## Summary

✓ **Decentralized**: Each user runs their own node
✓ **Synchronized**: Blocks sync across network
✓ **Independent**: Can mine without central server
✓ **Scalable**: Add more nodes anytime
✓ **Resilient**: Network survives node failures

You now have a true P2P blockchain network! 🚀

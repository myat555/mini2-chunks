# Testing on a Single Computer

## ✅ Yes, you can test everything on a single computer!

You don't need to change IP addresses if you use `localhost` or `127.0.0.1`. I've updated the code and created configuration files for single-machine testing.

---

## Quick Answer

**For single-machine testing:**
- ✅ Use `localhost` or `127.0.0.1` instead of IP addresses
- ✅ Use different ports for different nodes (50051, 50052, etc.)
- ✅ Run multiple terminals/windows on the same computer

**You DON'T need to:**
- ❌ Find your computer's IP address
- ❌ Set up network connections
- ❌ Use multiple computers

---

## Part 1: Testing Ping-Pong Example (Single Machine)

### Step 1: Generate gRPC Code
```bash
chmod +x build_proto.sh
./build_proto.sh
```

### Step 2: Start the Server (Terminal 1)
```bash
python server.py
```
You should see: `Server started on port 50051`

### Step 3: Run the Client (Terminal 2)
```bash
python client.py
```
The client is already configured to use `localhost`, so it will connect to the server on the same machine!

**Expected Output:**
```
Received response: Pong from server: Hello from client!
```

---

## Part 2: Testing Overlay Network (Single Machine)

You can run multiple nodes on the same computer using different ports!

### Step 1: Generate gRPC Code
```bash
cd chunks
chmod +x build_proto_chunks.sh
./build_proto_chunks.sh
```

### Step 2: Start Node 1 (Terminal 1)
```bash
cd chunks
python node.py node_config_localhost1.json
```
You should see: `Node node-1 listening on port 50051 with neighbors: [{'host': 'localhost', 'port': 50052}]`

### Step 3: Start Node 2 (Terminal 2)
```bash
cd chunks
python node.py node_config_localhost2.json
```
You should see: `Node node-2 listening on port 50052 with neighbors: [{'host': 'localhost', 'port': 50051}]`

### Step 4: Run the Client (Terminal 3)
```bash
cd chunks
python client_chunks.py localhost 50051
```

**Expected Output:**
```
Got aggregated result: node-1|node-2 hops: ['node-1', 'node-2']
```

---

## Understanding IP Addresses vs Localhost

### Network Testing (Multiple Computers)
- **IP Address**: `192.168.1.2`, `192.168.1.100`, etc.
  - Used when server and client are on different computers
  - You need to know the server's actual IP address
  - Both computers must be on the same network

### Single Machine Testing
- **localhost** or **127.0.0.1**: Always refers to "this computer"
  - No network needed - everything runs locally
  - Perfect for development and testing
  - Faster (no network latency)

---

## Configuration Files Explained

### For Network Testing (Original Files)
- `node_config_mac.json`: Uses IP `192.168.1.2` (for Mac connecting to Windows)
- `node_config_win.json`: Uses IP `192.168.1.1` (for Windows connecting to Mac)

### For Single Machine Testing (New Files)
- `node_config_localhost1.json`: Uses `localhost` - Node 1 on port 50051
- `node_config_localhost2.json`: Uses `localhost` - Node 2 on port 50052

**Key Difference:**
```json
// Network version
{ "host": "192.168.1.2", "port": 50052 }

// Single machine version
{ "host": "localhost", "port": 50052 }
```

---

## Troubleshooting

### "Address already in use" Error
**Problem:** Port is already taken by another process

**Solution:**
1. Find what's using the port:
   ```bash
   # Mac/Linux
   lsof -i :50051
   
   # Windows
   netstat -ano | findstr :50051
   ```
2. Kill that process or use a different port

### "Connection refused" Error
**Problem:** Server isn't running or wrong address

**Solution:**
1. Make sure server is running first
2. Check you're using `localhost` (not an IP address) for single-machine testing
3. Verify the port number matches

### Multiple Nodes on Same Machine
**Important:** Each node must use a **different port**:
- Node 1: Port 50051
- Node 2: Port 50052
- Node 3: Port 50053 (if you add more)

---

## Testing with More Nodes (Single Machine)

You can create a network with 3+ nodes on one computer:

**Create `node_config_localhost3.json`:**
```json
{
  "id": "node-3",
  "listen_port": 50053,
  "neighbors": [
    { "host": "localhost", "port": 50051 }
  ]
}
```

**Update `node_config_localhost1.json` to include node-3:**
```json
{
  "id": "node-1",
  "listen_port": 50051,
  "neighbors": [
    { "host": "localhost", "port": 50052 },
    { "host": "localhost", "port": 50053 }
  ]
}
```

Then run all three nodes in separate terminals!

---

## Summary

✅ **Single Machine Testing:**
- Use `localhost` or `127.0.0.1`
- Use different ports for each node
- No IP address changes needed
- Perfect for development

✅ **Network Testing:**
- Use actual IP addresses (like `192.168.1.2`)
- Requires multiple computers on same network
- Need to know each computer's IP address

The code is now ready for single-machine testing! Just use the `node_config_localhost*.json` files instead of the `node_config_mac.json` and `node_config_win.json` files.


# Beginner's Guide to This gRPC Project

## 📚 Table of Contents
1. [What is This Project?](#what-is-this-project)
2. [Project Structure Overview](#project-structure-overview)
3. [Part 1: Simple Ping-Pong Example](#part-1-simple-ping-pong-example)
4. [Part 2: Overlay Network System](#part-2-overlay-network-system)
5. [How to Run Everything](#how-to-run-everything)

---

## What is This Project?

This project demonstrates **gRPC (gRPC Remote Procedure Calls)**, a modern framework for building distributed systems. Think of it like this:
- **Traditional approach**: You send HTTP requests and get responses
- **gRPC approach**: You call functions on remote computers as if they were local functions

The project has **two parts**:
1. **Simple Example**: A basic client-server ping-pong system
2. **Advanced Example**: A distributed overlay network where nodes forward messages to each other

---

## Project Structure Overview

```
mini2-chunks/
├── README.md                    # Setup instructions
├── requirements.txt             # Python dependencies
├── build_proto.sh              # Script to generate gRPC code
│
├── test.proto                  # Protocol definition for ping-pong
├── test_pb2.py                 # Generated Python code (messages)
├── test_pb2_grpc.py            # Generated Python code (services)
├── server.py                   # Ping-pong server
├── client.py                   # Ping-pong client
│
└── chunks/                     # Overlay network system
    ├── overlay.proto           # Protocol definition for overlay
    ├── overlay_pb2.py          # Generated Python code (messages)
    ├── overlay_pb2_grpc.py     # Generated Python code (services)
    ├── node.py                 # Overlay network node (server)
    ├── client_chunks.py        # Client to start overlay requests
    ├── node_config_mac.json    # Configuration for Mac node
    ├── node_config_win.json    # Configuration for Windows node
    └── build_proto_chunks.sh   # Script to generate gRPC code
```

---

## Part 1: Simple Ping-Pong Example

This is the **simplest possible gRPC example** - perfect for learning!

### Step 1: Define the Protocol (`test.proto`)

**What is a `.proto` file?**
- It's like a **contract** that defines what messages can be sent and what functions are available
- Both client and server must use the same `.proto` file

```protobuf
syntax = "proto3";              // Use Protocol Buffers version 3
package test;                    // Namespace for our code

service PingService {            // Define a service (like a class with methods)
  rpc Ping(PingMessage) returns (PongMessage) {}  // One method: Ping
}

message PingMessage {            // Input message structure
  string text = 1;               // A text field (number 1 is the field ID)
}

message PongMessage {            // Output message structure
  string text = 1;               // A text field
}
```

**Key Concepts:**
- **Service**: A collection of remote procedures (functions you can call remotely)
- **RPC**: Remote Procedure Call - a function you can call on a remote server
- **Message**: A data structure (like a class in Python)

### Step 2: Generate Python Code (`build_proto.sh`)

**Why do we need this?**
- The `.proto` file is just a definition - we need actual Python code to use it
- The `protoc` compiler converts `.proto` → Python code

```bash
#!/bin/bash
# This script finds all .proto files and generates Python code

for proto in *.proto; do
    python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. $proto
done
```

**What this does:**
- `--python_out=.` → Generates `test_pb2.py` (message classes)
- `--grpc_python_out=.` → Generates `test_pb2_grpc.py` (service classes)

**Generated Files:**
- `test_pb2.py`: Contains `PingMessage` and `PongMessage` classes
- `test_pb2_grpc.py`: Contains `PingServiceStub` (client) and `PingServiceServicer` (server base class)

### Step 3: Implement the Server (`server.py`)

**What does a server do?**
- Listens for incoming requests
- Processes them and sends back responses

```python
import grpc
from concurrent import futures
import time
import test_pb2
import test_pb2_grpc

# Step 1: Create a class that implements the service
class PingServiceServicer(test_pb2_grpc.PingServiceServicer):
    def Ping(self, request, context):
        # This method is called when a client sends a Ping request
        print(f"Received Ping: {request.text}")
        # Create and return a PongMessage response
        return test_pb2.PongMessage(text=f"Pong from server: {request.text}")

def serve():
    # Step 2: Create a gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    
    # Step 3: Register our service implementation
    test_pb2_grpc.add_PingServiceServicer_to_server(PingServiceServicer(), server)
    
    # Step 4: Tell server which port to listen on
    # [::] means "listen on all network interfaces"
    server.add_insecure_port('[::]:50051')
    
    # Step 5: Start the server
    server.start()
    print("Server started on port 50051")
    
    # Step 6: Keep server running (wait for requests)
    try:
        while True:
            time.sleep(60*60*24)  # Sleep for 24 hours
    except KeyboardInterrupt:
        server.stop(0)
        print("Server stopped")

if __name__ == '__main__':
    serve()
```

**Key Concepts:**
- **Servicer**: A class that implements the actual logic for each RPC method
- **ThreadPoolExecutor**: Allows server to handle multiple requests simultaneously
- **Insecure port**: For development only (no encryption)

### Step 4: Implement the Client (`client.py`)

**What does a client do?**
- Connects to a server
- Sends requests and receives responses

```python
import grpc
import test_pb2
import test_pb2_grpc

def run():
    # Step 1: Create a connection (channel) to the server
    server_ip = "192.168.1.2"  # Replace with actual server IP
    channel = grpc.insecure_channel(f"{server_ip}:50051")
    
    # Step 2: Create a "stub" - this is like a proxy object
    # It has all the methods defined in the service
    stub = test_pb2_grpc.PingServiceStub(channel)
    
    # Step 3: Call the remote method as if it were local!
    # Create a PingMessage
    request = test_pb2.PingMessage(text="Hello from client!")
    
    # Call Ping() - this actually sends a network request
    response = stub.Ping(request)
    
    # Step 4: Use the response
    print("Received response:", response.text)

if __name__ == '__main__':
    run()
```

**Key Concepts:**
- **Channel**: The connection to the server
- **Stub**: A client-side proxy that makes remote calls look like local function calls
- **Blocking call**: `stub.Ping()` waits for the response before continuing

---

## Part 2: Overlay Network System

This is a **more advanced example** showing a distributed network where nodes forward messages to each other.

### Step 1: Define the Overlay Protocol (`chunks/overlay.proto`)

```protobuf
syntax = "proto3";
package overlay;

service OverlayNode {
  // A node can forward requests to its neighbors
  rpc Forward(Request) returns (Response);
}

message Request {
  string payload = 1;              // The actual data being sent
  repeated string hops = 2;        // List of nodes this request has visited
}

message Response {
  string result = 1;               // Aggregated result from all nodes
  repeated string hops = 2;        // List of nodes that processed this request
}
```

**Key Concepts:**
- **repeated**: Means it's a list/array (can have multiple values)
- **hops**: Used to prevent infinite loops - tracks which nodes have already seen this request

### Step 2: Implement a Network Node (`chunks/node.py`)

**What is a node?**
- A server that can receive requests and forward them to neighboring nodes
- Like a router in a network

```python
import grpc
import json
from concurrent import futures
import overlay_pb2
import overlay_pb2_grpc
import sys

class OverlayServicer(overlay_pb2_grpc.OverlayNodeServicer):
    def __init__(self, config):
        self.config = config
        self.neighbors = config["neighbors"]  # List of connected nodes
        self.id = config["id"]                # This node's unique ID

    def Forward(self, request, context):
        # Step 1: Log that we received a request
        print(f"{self.id} got request with hops: {request.hops}")
        
        # Step 2: Add ourselves to the hops list (prevent loops)
        new_hops = list(request.hops)
        new_hops.append(self.id)
        
        # Step 3: If we have neighbors, forward to them
        if len(self.neighbors) > 0:
            responses = []
            for neighbor in self.neighbors:
                # Only forward to neighbors we haven't visited yet
                if neighbor['host'] not in request.hops:
                    # Forward the request to this neighbor
                    resp = forward_to_neighbor(
                        neighbor["host"], 
                        neighbor["port"], 
                        request.payload, 
                        new_hops
                    )
                    responses.append(resp)
            
            # Step 4: Aggregate all responses
            agg = ";".join(r.result for r in responses)
            return overlay_pb2.Response(
                result=f"{self.id}|{agg}", 
                hops=new_hops
            )
        else:
            # Step 5: If no neighbors, we're a leaf node - just return our ID
            return overlay_pb2.Response(result=self.id, hops=new_hops)

def forward_to_neighbor(host, port, payload, hops):
    """Helper function to forward a request to another node"""
    with grpc.insecure_channel(f"{host}:{port}") as channel:
        stub = overlay_pb2_grpc.OverlayNodeStub(channel)
        req = overlay_pb2.Request(payload=payload, hops=hops)
        resp = stub.Forward(req)  # Make the remote call
        return resp

def serve(config_path):
    # Step 1: Load configuration from JSON file
    with open(config_path) as f:
        config = json.load(f)
    
    # Step 2: Create and start the server (similar to ping-pong example)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    servicer = OverlayServicer(config)
    overlay_pb2_grpc.add_OverlayNodeServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{config['listen_port']}")
    server.start()
    
    print(f"Node {config['id']} listening on port {config['listen_port']} with neighbors: {config['neighbors']}")
    server.wait_for_termination()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python node.py node_config.json")
        sys.exit(1)
    serve(sys.argv[1])
```

**How it works:**
1. Node receives a request
2. Adds itself to the "hops" list
3. Forwards to all neighbors (that haven't been visited)
4. Collects responses and aggregates them
5. Returns the aggregated result

**Loop Prevention:**
- The `hops` list tracks visited nodes
- Before forwarding, we check: `if neighbor['host'] not in request.hops`
- This prevents infinite loops in the network

### Step 3: Node Configuration Files

**Why do we need config files?**
- Each node needs to know:
  - Its own ID
  - Which port to listen on
  - Who its neighbors are

**`node_config_mac.json`:**
```json
{
  "id": "mac-node",           // Unique identifier
  "listen_port": 50051,       // Port this node listens on
  "neighbors": [              // List of connected nodes
    { "host": "192.168.1.2", "port": 50052 }
  ]
}
```

**`node_config_win.json`:**
```json
{
  "id": "windows-node",
  "listen_port": 50052,
  "neighbors": [
    { "host": "192.168.1.1", "port": 50051 }  // Points back to Mac node
  ]
}
```

**Network Topology:**
```
Client → Mac Node (50051) ←→ Windows Node (50052)
```

### Step 4: Client for Overlay Network (`chunks/client_chunks.py`)

```python
import grpc
import overlay_pb2
import overlay_pb2_grpc
import sys

def main(server_host, server_port):
    # Step 1: Connect to the first node
    channel = grpc.insecure_channel(f"{server_host}:{server_port}")
    stub = overlay_pb2_grpc.OverlayNodeStub(channel)
    
    # Step 2: Create a request with empty hops (starting point)
    req = overlay_pb2.Request(payload="start", hops=[])
    
    # Step 3: Send the request - it will propagate through the network
    resp = stub.Forward(req)
    
    # Step 4: Print the aggregated result from all nodes
    print("Got aggregated result:", resp.result, "hops:", resp.hops)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python client.py <host> <port>")
        sys.exit(1)
    main(sys.argv[1], int(sys.argv[2]))
```

**What happens:**
1. Client sends request to first node
2. First node forwards to its neighbors
3. Neighbors forward to their neighbors (if any)
4. Responses bubble back up
5. Client receives aggregated result from entire network

---

## How to Run Everything

### Setup (One-time)

1. **Create virtual environment:**
   ```bash
   python -m venv .venv
   ```

2. **Activate virtual environment:**
   - Mac/Linux: `source .venv/bin/activate`
   - Windows: `.venv\Scripts\activate`

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Running the Ping-Pong Example

1. **Generate gRPC code:**
   ```bash
   chmod +x build_proto.sh
   ./build_proto.sh
   ```

2. **Start the server** (in one terminal):
   ```bash
   python server.py
   ```

3. **Run the client** (in another terminal):
   ```bash
   # Edit client.py first to set the correct server IP
   python client.py
   ```

### Running the Overlay Network

1. **Generate gRPC code:**
   ```bash
   cd chunks
   chmod +x build_proto_chunks.sh
   ./build_proto_chunks.sh
   ```

2. **Start Node 1** (Mac, in one terminal):
   ```bash
   cd chunks
   python node.py node_config_mac.json
   ```

3. **Start Node 2** (Windows, in another terminal):
   ```bash
   cd chunks
   python node.py node_config_win.json
   ```

4. **Run the client** (in a third terminal):
   ```bash
   cd chunks
   python client_chunks.py 192.168.1.1 50051
   ```

---

## Key Concepts Summary

### gRPC Basics
- **Protocol Buffers (protobuf)**: Language-neutral way to define data structures
- **Service**: Collection of remote procedures
- **RPC**: Remote Procedure Call - calling a function on another machine
- **Stub**: Client-side proxy that makes remote calls look local
- **Servicer**: Server-side implementation of the service

### Network Concepts
- **Port**: A number that identifies a specific service on a computer (like an apartment number)
- **IP Address**: Unique identifier for a computer on a network
- **Channel**: The connection between client and server
- **Thread Pool**: Allows server to handle multiple requests simultaneously

### Distributed Systems
- **Node**: A server in a distributed network
- **Neighbor**: A directly connected node
- **Forwarding**: Passing a request to another node
- **Aggregation**: Combining results from multiple nodes
- **Loop Prevention**: Using "hops" to avoid infinite forwarding loops

---

## Common Issues & Solutions

1. **"Module not found" errors:**
   - Make sure you've run the build script to generate `*_pb2.py` files
   - Make sure virtual environment is activated

2. **Connection refused:**
   - Check that server is running
   - Verify IP address and port are correct
   - Check firewall settings

3. **Port already in use:**
   - Another process is using that port
   - Change the port number in config or kill the other process

---

## Next Steps for Learning

1. **Modify the ping-pong example:**
   - Add more fields to messages
   - Add more RPC methods
   - Add error handling

2. **Experiment with overlay network:**
   - Add more nodes
   - Create different network topologies
   - Add data processing at each node

3. **Learn more about:**
   - gRPC streaming (sending multiple messages)
   - Authentication and security
   - Error handling and retries
   - Load balancing

---

Happy coding! 🚀


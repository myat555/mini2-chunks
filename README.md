# 2-Host Distributed Leader-Queue System

A distributed overlay network system built with gRPC that implements a leader-queue architecture across two hosts (Windows and macOS). This system demonstrates distributed request processing with team-based routing and queue management.

## System Architecture

### Host Configuration

- **Windows Host**: `192.168.1.2`
- **macOS Host**: `192.168.1.1`

### Process Roles and Distribution

| Process | Role | Team | Host | Port |
|---------|------|------|------|------|
| A | Leader | Green | Windows (192.168.1.2) | 50051 |
| B | Team Leader | Green | Windows (192.168.1.2) | 50052 |
| C | Worker | Green | macOS (192.168.1.1) | 50053 |
| D | Worker | Pink | Windows (192.168.1.2) | 50054 |
| E | Team Leader | Pink | macOS (192.168.1.1) | 50055 |
| F | Worker | Pink | macOS (192.168.1.1) | 50056 |

### Network Topology

```
Windows Host (192.168.1.2)           macOS Host (192.168.1.1)
┌─────────────────┐                  ┌─────────────────┐
│   Process A     │◄── Leader ────►│   Process E     │
│   (Leader)      │                  │ (Team Leader)   │
│   Port: 50051   │                  │   Port: 50055   │
└─────────────────┘                  └─────────────────┘
         │                                      │
         │                                      │
┌─────────────────┐                  ┌─────────────────┐
│   Process B     │                  │   Process C     │
│ (Team Leader)   │                  │    (Worker)     │
│   Port: 50052   │                  │   Port: 50053   │
└─────────────────┘                  └─────────────────┘
         │                                      │
         │                                      │
┌─────────────────┐                  ┌─────────────────┐
│   Process D     │                  │   Process F     │
│    (Worker)     │                  │    (Worker)     │
│   Port: 50054   │                  │   Port: 50056   │
└─────────────────┘                  └─────────────────┘
```

## Prerequisites

- Python 3.7+
- pip package manager
- Network connectivity between hosts

## Quick Start

### 1. Setup Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate

# On macOS/Linux:
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Generate gRPC Code

```bash
# Make build script executable (macOS/Linux)
chmod +x build_proto.sh

# Generate proto files
./build_proto.sh
```

## Running the System

### Start Windows Processes

Run the following command on the Windows host (192.168.1.2):

```bash
cd scripts
start_windows.bat
```

This starts:
- Process A (Leader) on port 50051
- Process B (Team Leader) on port 50052
- Process D (Worker) on port 50054

### Start macOS Processes

Run the following command on the macOS host (192.168.1.1):

```bash
cd scripts
chmod +x start_macos.sh
./start_macos.sh
```

This starts:
- Process C (Worker) on port 50053
- Process E (Team Leader) on port 50055
- Process F (Worker) on port 50056

## Testing the System

### Basic Client Test

Test a single request through the leader:

```bash
python client.py 192.168.1.2 50051
```

### Check Queue Status

Monitor the leader's queue status:

```bash
python client.py 192.168.1.2 50051 check
```

### Comprehensive System Test

Run the full test suite:

```bash
python test_system.py 192.168.1.2 50051
```

This performs:
- Single request test
- Queue status monitoring
- Concurrent request handling (10 requests)

## Manual Process Management

### Starting Individual Processes

```bash
# Start specific process
python node.py two_hosts_config.json A  # Leader
python node.py two_hosts_config.json B  # Team Leader
python node.py two_hosts_config.json C  # Worker
python node.py two_hosts_config.json D  # Worker
python node.py two_hosts_config.json E  # Team Leader
python node.py two_hosts_config.json F  # Worker
```

### Stopping Processes

Stop all processes:

```bash
# macOS/Linux
./scripts/stop_all.sh

# Windows - Use Ctrl+C in the batch script window or manually kill processes
```

## Configuration

The system configuration is defined in [`two_hosts_config.json`](two_hosts_config.json):

```json
{
  "processes": {
    "A": {
      "id": "A",
      "role": "leader",
      "team": "green",
      "host": "192.168.1.2",
      "port": 50051,
      "neighbors": ["B", "E"]
    },
    ...
  }
}
```

## Protocol Buffer Definition

The gRPC service is defined in [`overlay.proto`](overlay.proto):

- [`Forward`](overlay.proto:4) - Routes requests through the overlay network
- [`GetMetrics`](overlay.proto:5) - Retrieves queue and system metrics

## Troubleshooting

### Common Issues

1. **Process fails to start**
   - Verify Python and dependencies are installed
   - Check if ports are available
   - Ensure proto files are generated
   - Run startup scripts from the `scripts/` directory

2. **Network connectivity issues**
   - Verify hosts can ping each other
   - Check firewall settings on both hosts
   - Ensure IP addresses match configuration (Windows: 192.168.1.2, macOS: 192.168.1.1)
   - Verify server binds to 0.0.0.0 for proper network accessibility

3. **gRPC connection errors**
   - Verify all processes are running on correct hosts
   - Check port numbers match configuration
   - Ensure network connectivity between hosts
   - Confirm configuration file matches startup script process assignments

### Recent Fixes

**Configuration and Connectivity Updates:**
- Fixed host IP assignments to match startup scripts (Windows: 192.168.1.2, macOS: 192.168.1.1)
- Changed server binding from [::] to 0.0.0.0 in node.py for proper IPv4 network connectivity
- Corrected file path references in startup scripts to use relative paths from scripts/ directory

### Log Files

Process logs are stored in the `logs/` directory:
- `process_a.log` - Leader process logs
- `process_b.log` - Team leader logs
- `process_c.log` - Worker process logs
- etc.

## File Structure

```
.
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── two_hosts_config.json    # System configuration
├── overlay.proto            # gRPC service definition
├── build_proto.sh          # Proto file generation script
├── node.py                 # Process implementation
├── client.py               # Client for testing
├── test_system.py          # Comprehensive test suite
└── scripts/
    ├── start_windows.bat   # Windows process starter
    ├── start_macos.sh      # macOS process starter
    └── stop_all.sh         # Process cleanup script
```

## Development

### Regenerating Proto Files

If you modify the protocol buffer definition:

```bash
./build_proto.sh
```

This generates:
- `overlay_pb2.py` - Protocol buffer classes
- `overlay_pb2_grpc.py` - gRPC service stubs

### Adding New Processes

1. Update [`two_hosts_config.json`](two_hosts_config.json) with new process configuration
2. Add startup commands to appropriate script files
3. Update neighbor relationships in existing processes

## Network Requirements

- TCP ports 50051-50056 must be open between hosts
- Hosts must be on the same subnet or have routing configured
- Network latency should be < 100ms for optimal performance

## Performance Characteristics

- Leader queue capacity: 200 requests
- Maximum concurrent requests per process: 100
- Automatic loop prevention with hop tracking
- Team-based routing for efficient request distribution
# Distributed Overlay Network System

A gRPC-based distributed system implementing a leader-queue architecture with team-based routing and data partitioning.

## Architecture

### Process Roles

| Process | Role | Team | Host | Port |
|---------|------|------|------|------|
| A | Leader | Green | Windows (192.168.1.2) | 60051 |
| B | Team Leader | Green | Windows (192.168.1.2) | 60052 |
| C | Worker | Green | macOS (192.168.1.1) | 60053 |
| D | Worker | Pink | Windows (192.168.1.2) | 60054 |
| E | Team Leader | Pink | macOS (192.168.1.1) | 60055 |
| F | Worker | Pink | macOS (192.168.1.1) | 60056 |

### Data Distribution

- **Leader (A)**: Coordinator only, no data storage
- **Team Leaders (B, E)**: Load their team's data partition and coordinate workers
- **Workers (C, D, F)**: Load their team's data partition
- **Partitions**: Team Green (20200810-20200820), Team Pink (20200821-20200924)

### Query Flow

1. Client sends query to Leader
2. Leader forwards to Team Leaders
3. Team Leaders query local data and forward to Workers
4. Results aggregated and returned in chunks

## Prerequisites

- Python 3.7+
- Virtual environment (recommended)
- Network connectivity between hosts (for two-host setup)

## Setup

```bash
# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Generate gRPC code
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. overlay.proto
```

## Running the System

### Single-Host (All processes on one machine)

**Windows:**
```bash
cd scripts
start_single_host_windows.bat
```

**macOS/Linux:**
```bash
cd scripts
chmod +x start_single_host_macos.sh
./start_single_host_macos.sh
```

Press Ctrl+C to stop all processes.

### Two-Host Setup

Start servers on both machines:

**Windows (192.168.1.2):**
```bash
cd scripts
start_two_hosts_windows.bat
```
Starts: A (Leader), B (Team Leader), D (Worker)

**macOS (192.168.1.1):**
```bash
cd scripts
chmod +x start_two_hosts_macos.sh
./start_two_hosts_macos.sh
```
Starts: C (Worker), E (Team Leader), F (Worker)

## Testing

### Verify Data Loading
```bash
python verify_data_loading.py one_host_config.json
```

### Basic Query Test
```bash
python client.py 192.168.1.2 60051 query PM2.5 5 35
```

### System Test
```bash
python test_system.py 192.168.1.2 60051
```

### Metrics
```bash
python client.py 192.168.1.2 60051 metrics
```

## Benchmarking

### Single-Host Benchmark

Automatically starts servers, runs benchmark, stops servers:

**Windows:**
```bash
cd scripts
benchmark_single_host_windows.bat [requests] [concurrency]
```

**macOS/Linux:**
```bash
cd scripts
chmod +x benchmark_single_host_macos.sh
./benchmark_single_host_macos.sh [requests] [concurrency]
```

Default: 200 requests, 20 concurrency
Results saved to: `benchmark_results.json`

### Two-Host Benchmark

Requires servers to be running on both hosts:

**Windows:**
```bash
cd scripts
benchmark_two_hosts.bat [host] [port] [requests] [concurrency]
```

**macOS/Linux:**
```bash
cd scripts
chmod +x benchmark_two_hosts.sh
./benchmark_two_hosts.sh [host] [port] [requests] [concurrency]
```

Default: host=192.168.1.2, port=60051, requests=200, concurrency=20
Results saved to: `benchmark_results_two_hosts.json`

## Configuration

Configuration files:
- `one_host_config.json` - Single-host setup (all processes on 127.0.0.1)
- `two_hosts_config.json` - Two-host setup (Windows + macOS)

Each process requires:
- `id`: Process identifier (A-F)
- `role`: leader, team_leader, or worker
- `team`: green or pink
- `host`: IP address or hostname
- `port`: Listening port
- `neighbors`: List of neighbor process IDs

## gRPC API

Defined in `overlay.proto`:

- `Query` - Submit query with filters, returns query UID and chunk metadata
- `GetChunk` - Retrieve data chunks by UID and chunk index
- `GetMetrics` - Get process metrics (queue size, active requests, etc.)
- `Shutdown` - Graceful shutdown (optional)

## Implementation

Core modules in `overlay_core/`:

- `OverlayFacade` - Main facade coordinating queries, caching, and routing
- `ProxyRegistry` - Manages proxies for remote neighbor communication
- `DataStore` - Team-specific data loading and filtering
- `ResultCache` - TTL-based chunk caching
- `RequestAdmissionController` - Capacity management and fairness
- `MetricsTracker` - Performance metrics collection

## Troubleshooting

**Process fails to start:**
- Check Python version and dependencies
- Verify ports are available
- Ensure proto files are generated
- Check configuration file exists and is valid

**Network connectivity issues:**
- Verify hosts can reach each other
- Check firewall allows ports 60051-60056
- Confirm IP addresses match configuration
- Ensure servers bind to 0.0.0.0 (not localhost)

**gRPC connection errors:**
- Verify all processes are running
- Check port numbers match configuration
- Confirm processes can reach each other
- Review process logs in separate windows

## Network Requirements

- TCP ports 60051-60056 must be open between hosts
- Hosts should be on the same subnet or have routing configured
- Network latency < 100ms recommended for optimal performance

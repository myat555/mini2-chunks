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

## Project Structure

```
mini2-chunks/
├── datasets/                          # Dataset folder (ignored by git)
│   └── 2020-fire/
│       ├── airnow-output-desc.pdf
│       └── data/                      # CSV data files organized by date
│           ├── 20200810/              # Team Green: 20200810-20200820
│           │   ├── 20200810-01.csv
│           │   ├── 20200810-03.csv
│           │   └── ... (hourly files)
│           ├── 20200811/
│           ├── ... (through 20200820)
│           ├── 20200821/              # Team Pink: 20200821-20200924
│           ├── ... (through 20200924)
│
│
├── logs/                              # Benchmark logs and results
│   ├── windows/                       # Single-host Windows logs
│   │   ├── node_a.log                 # Process A (Leader) logs
│   │   ├── node_b.log                 # Process B (Team Leader) logs
│   │   ├── node_c.log                 # Process C (Worker) logs
│   │   ├── node_d.log                 # Process D (Worker) logs
│   │   ├── node_e.log                 # Process E (Team Leader) logs
│   │   ├── node_f.log                 # Process F (Worker) logs
│   │   └── benchmark_results.json     # Single-host benchmark results
│   ├── macos/                         # Single-host macOS logs
│   │   ├── node_a.log
│   │   ├── node_b.log
│   │   ├── ... (same structure as windows/)
│   │   └── benchmark_results.json
│   └── two_hosts/                     # Two-host setup logs (filtered by IP and platform)
│       ├── windows_192.168.1.2_node_a.log    # Windows host, Process A (Leader)
│       ├── windows_192.168.1.2_node_b.log    # Windows host, Process B (Team Leader)
│       ├── windows_192.168.1.2_node_d.log    # Windows host, Process D (Worker)
│       ├── macos_192.168.1.1_node_c.log      # macOS host, Process C (Worker)
│       ├── macos_192.168.1.1_node_e.log      # macOS host, Process E (Team Leader)
│       ├── macos_192.168.1.1_node_f.log      # macOS host, Process F (Worker)
│       └── benchmark_results_two_hosts.json  # Two-host benchmark results
│
├── overlay_core/                      # Core implementation modules
│   ├── __init__.py
│   ├── config.py                      # Configuration parsing
│   ├── data_store.py                  # Dataset loading and querying
│   ├── facade.py                      # Main facade orchestrating queries
│   ├── metrics.py                     # Performance metrics tracking
│   ├── proxies.py                     # Remote node proxy management
│   ├── request_controller.py          # Request admission and fairness
│   └── result_cache.py                # Chunked result caching
│
├── scripts/                           # Automation scripts
│   ├── benchmark_single_host_macos.sh    # Single-host benchmark (macOS)
│   ├── benchmark_single_host_windows.bat # Single-host benchmark (Windows)
│   ├── benchmark_two_hosts.bat        # Two-host benchmark (Windows)
│   ├── benchmark_two_hosts.py         # Two-host benchmark (Python)
│   ├── benchmark_two_hosts.sh         # Two-host benchmark (macOS)
│   ├── start_single_host_macos.sh     # Start single-host servers (macOS)
│   ├── start_single_host_windows.bat  # Start single-host servers (Windows)
│   ├── start_two_hosts_macos.sh       # Start two-host servers (macOS)
│   ├── start_two_hosts_windows.bat    # Start two-host servers (Windows)
│   └── wait_for_leader.py             # Leader readiness check utility
│
├── .gitignore                         # Git ignore patterns
├── .venv/                             # Virtual environment (ignored by git)
├── benchmark.py                       # Benchmark implementation
├── build_proto.sh                     # Protocol buffer generation script
├── client.py                          # Client for testing queries
├── node.py                            # Process node implementation
├── one_host_config.json               # Single-host configuration
├── overlay.proto                      # gRPC service definition
├── overlay_pb2.py                     # Generated protocol buffer classes
├── overlay_pb2_grpc.py                # Generated gRPC service stubs
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── test_system.py                     # System test suite
├── two_hosts_config.json              # Two-host configuration
└── verify_data_loading.py             # Data loading verification script
```

**Important Notes:**
- `datasets/` folder is required but ignored by git - you must provide the dataset files
- `logs/` folder is created automatically during benchmarks
- `.venv/` is the virtual environment (ignored by git)
- Generated files: `overlay_pb2.py`, `overlay_pb2_grpc.py` (created by `build_proto.sh`)

## Prerequisites

- Python 3.7+
- Virtual environment (recommended)
- Network connectivity between hosts (for two-host setup)
- **Dataset files**: The `datasets/2020-fire/data/` folder must contain CSV files

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

# Ensure dataset folder structure exists
# datasets/2020-fire/data/ should contain date folders (20200810, 20200811, etc.)
# Each date folder should contain hourly CSV files (20200810-01.csv, 20200810-03.csv, etc.)
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
Results saved to: `logs/windows/benchmark_results.json` or `logs/macos/benchmark_results.json`

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
Results saved to: `logs/two_hosts/benchmark_results_two_hosts.json`
Process logs saved to: `logs/two_hosts/` with filenames indicating platform and IP (e.g., `windows_192.168.1.2_node_a.log`, `macos_192.168.1.1_node_c.log`)

**View logs from both hosts:**
- **Windows**: `scripts\view_two_hosts_logs.bat` - Shows logs from both Windows and macOS (if accessible)
- **macOS**: `scripts/view_two_hosts_logs.sh` - Shows logs from both macOS and Windows (if accessible)

**Note**: macOS logs are on the macOS machine. To view complete logs from both platforms:
1. Run `view_two_hosts_logs.sh` on the macOS machine to see macOS logs
2. Run `view_two_hosts_logs.bat` on the Windows machine to see Windows logs
3. Or access logs via network share if configured

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

## Network Requirements

- TCP ports 60051-60056 must be open between hosts
- Hosts should be on the same subnet or have routing configured
- Network latency < 100ms recommended for optimal performance

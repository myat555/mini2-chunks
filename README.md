# Distributed Overlay Network System

A gRPC-based distributed system implementing a leader-queue architecture with team-based routing, data partitioning, and configurable strategies for forwarding, chunking, and fairness. Features real-time benchmarking with visual monitoring of data distribution across multiple hosts.

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

- **Leader (A)**: Coordinator only; splits every client limit across team leaders
- **Team Leaders (B, E)**: Stateless routers. They never load data and immediately
  forward proportional sub-requests to their workers.
- **Workers (C, D, F)**: Own the actual dataset slices. The loader automatically
  splits each team's date range across its workers to avoid manual box-by-box
  configuration.
- **Partitions**: Team Green handles dates `20200810-20200820`, Team Pink handles
  `20200821-20200924`. No cross-team replication.

### Query Flow

1. Client sends query to Leader (A)
2. Leader forwards to Team Leaders (B, E) - can use parallel or sequential forwarding
3. Team Leaders query local data and forward to Workers (C, D, F)
4. Results aggregated and returned in chunks
5. Chunks retrieved by client on-demand

## Project Structure

```
mini2-chunks/
├── datasets/                          # Dataset folder
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
├── logs/                              # Benchmark logs and results
│   ├── windows/                       # Single-host Windows logs
│   │   ├── node_a.log                 # Process A (Leader) logs
│   │   ├── node_b.log                 # Process B (Team Leader) logs
│   │   ├── node_c.log                 # Process C (Worker) logs
│   │   ├── node_d.log                 # Process D (Worker) logs
│   │   ├── node_e.log                 # Process E (Team Leader) logs
│   │   ├── node_f.log                 # Process F (Worker) logs
│   │   └── benchmark_<strategy>.txt   # Single-host benchmark results (full console output)
│   ├── macos/                         # Single-host macOS logs
│   │   ├── node_a.log
│   │   ├── node_b.log
│   │   ├── ... (same structure as windows/)
│   │   └── benchmark_<strategy>.txt
│   └── two_hosts/                     # Two-host setup logs (filtered by IP and platform)
│       ├── windows_192.168.1.2_node_a.log    # Windows host, Process A (Leader)
│       ├── windows_192.168.1.2_node_b.log    # Windows host, Process B (Team Leader)
│       ├── windows_192.168.1.2_node_d.log    # Windows host, Process D (Worker)
│       ├── macos_192.168.1.1_node_c.log      # macOS host, Process C (Worker)
│       ├── macos_192.168.1.1_node_e.log      # macOS host, Process E (Team Leader)
│       ├── macos_192.168.1.1_node_f.log      # macOS host, Process F (Worker)
│       └── benchmark_<strategy>.txt          # Two-host benchmark results (full console output)
│
├── overlay_core/                      # Core implementation modules
│   ├── __init__.py
│   ├── config.py                      # Configuration parsing
│   ├── data_store.py                  # Dataset loading and querying
│   ├── facade.py                      # Main facade orchestrating queries
│   ├── metrics.py                     # Performance metrics tracking
│   ├── proxies.py                     # Remote node proxy management
│   ├── request_controller.py          # Request admission and fairness
│   ├── result_cache.py                # Chunked result caching
│   └── strategies.py                  # Strategy pattern implementations
│
├── scripts/                           # Automation scripts
│   ├── benchmark_single_host.bat      # Single-host benchmark (Windows)
│   ├── benchmark_single_host.sh       # Single-host benchmark (macOS/Linux)
│   ├── benchmark_two_hosts.bat        # Two-host benchmark (Windows)
│   ├── benchmark_two_hosts.sh         # Two-host benchmark (macOS/Linux)
│   ├── start_single_host_macos.sh     # Start single-host servers (macOS)
│   ├── start_single_host_windows.bat  # Start single-host servers (Windows)
│   ├── start_two_hosts_macos.sh       # Start two-host servers (macOS)
│   └── start_two_hosts_windows.bat    # Start two-host servers (Windows)
│
├── benchmark_unified.py               # Unified benchmark tool with real-time visualization
├── .gitignore                         # Git ignore patterns
├── .venv/                             # Virtual environment (ignored by git)
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
└── two_hosts_config.json              # Two-host configuration
```

**Important Notes:**
- `datasets/` folder is required but ignored by git
- `logs/` folder is created automatically during benchmarks
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
```

## Running the System

### Single-Host (All processes on one machine)

**Windows:**
```bash
scripts\start_single_host_windows.bat
```

**macOS/Linux:**
```bash
chmod +x scripts/start_single_host_macos.sh
./scripts/start_single_host_macos.sh
```

This starts all processes (A-F) on localhost (127.0.0.1) with ports 60051-60056.

Press Ctrl+C to stop all processes.

### Two-Host Setup

Start servers on both machines:

**Windows (192.168.1.2):**
```bash
scripts\start_two_hosts_windows.bat
```
Starts: A (Leader), B (Team Leader), D (Worker)

**macOS (192.168.1.1):**
```bash
chmod +x scripts/start_two_hosts_macos.sh
./scripts/start_two_hosts_macos.sh
```
Starts: C (Worker), E (Team Leader), F (Worker)

> **Networking tip:** the hosts must be able to reach each other both ways.
> Make sure Windows firewall allows inbound TCP 60051-60056 (and optionally
> ICMP) so macOS workers can call the Windows nodes.

## Workload Simulation & Benchmarks

- The `datasets/2020-fire/data` bundle contains **214,636 green** records and
  **952,889 pink** records (1,167,525 total). Sharding happens automatically:
  team leaders stay stateless and workers load their share.
- Use the unified benchmark from either host:

  ```bash
  # Windows
  scripts\benchmark_two_hosts.bat

  # macOS
  ./scripts/benchmark_two_hosts.sh
  ```

  By default the scripts run a heavy scenario (`--num-requests 400
  --concurrency 20`) so that both workers and leaders stay busy. Override flags
  as needed, e.g. `scripts\benchmark_two_hosts.bat --num-requests 200
  --concurrency 10`.

- Single-host benchmarks use the same entrypoints (`benchmark_single_host.*`).

- Under the hood these scripts call `benchmark_unified.py`, which renders the
  live dashboard and saves full logs to `logs/<platform>/benchmark_*.txt`.

## Testing

### Basic Query Test
```bash
python client.py 127.0.0.1 60051 query PM2.5 5 35
```

### System Test
```bash
python test_system.py 127.0.0.1 60051
```

### Metrics
```bash
python client.py 127.0.0.1 60051 metrics
```

## Relationship to `leader-adv` lab

The original `leader-adv` OpenMP lab lives in `docs/leader-adv/` for reference.
This project keeps the same design ideas (leaders delegating to workers, queue
admission, centralized vs. decentralized execution) but applies them across two
physical hosts over gRPC instead of in-memory threads.

## Strategy Configuration

The system implements a strategy pattern for configurable behavior in forwarding, chunking, and fairness. This allows testing different approaches to coordination and request control as required by mini2-chunks.md.

**Global Strategy Configuration**: All processes (across macOS and Windows) use the same strategies as defined in the JSON configuration files (`one_host_config.json` or `two_hosts_config.json`). This ensures consistent behavior across all processes in a deployment. Strategies can still be overridden per-process via command-line arguments if needed.

### Forwarding Strategies

Controls how queries are forwarded to neighbors:

- **`round_robin`** (default): Sequential round-robin forwarding
  - Processes neighbors one by one in round-robin order
  - Can be used with async flag for parallel execution while maintaining order
- **`parallel`**: Parallel forwarding to all neighbors simultaneously
  - Uses custom threading implementation (not gRPC async APIs)
  - All neighbors queried in parallel for maximum throughput
- **`capacity`**: Capacity-based forwarding (least-loaded first)
  - Sorts neighbors by load (active/capacity ratio)
  - Routes to least-loaded neighbors first

### Chunking Strategies

Controls how results are chunked:

- **`fixed`** (default): Fixed chunk size (configurable via `--chunk-size`)
- **`adaptive`**: Adaptive chunk size based on result size
  - Small results (< 100 records): 50 records per chunk
  - Medium results (< 500 records): base size
  - Large results (< 2000 records): 2x base size
  - Very large (> 2000 records): max size (1000)
- **`query_based`**: Chunk size based on query limit
  - Uses 10% of query limit as chunk size
  - Minimum: base size, Maximum: 500

### Fairness Strategies

Controls request admission and fairness between teams:

- **`strict`** (default): Strict per-team limits
  - Each team has a hard limit (default: 60 concurrent requests)
  - No flexibility when one team is overloaded
- **`weighted`**: Weighted fairness based on team load
  - Allows slight over-limit if other teams are underutilized
  - Better overall system utilization
- **`hybrid`**: Hybrid approach
  - Strict when system load > 80%
  - Weighted when system load < 80%
  - Balances fairness and performance

### Async vs Blocking Forwarding

The system supports both blocking and async forwarding modes:

- **Blocking mode** (default): Sequential forwarding, one neighbor at a time
- **Async mode** (`--async-forwarding` flag): Parallel forwarding using custom threading
  - Uses Python `threading` module (not gRPC async APIs as per requirements)
  - Leader forwards to team leaders in parallel
  - Team leaders forward to workers in parallel
  - Local data queries remain blocking

### Configuration

Strategies are configured globally in the JSON config files:

```json
{
  "strategies": {
    "forwarding_strategy": "round_robin",
    "async_forwarding": false,
    "chunking_strategy": "fixed",
    "fairness_strategy": "strict",
    "chunk_size": 200
  },
  "processes": {
    ...
  }
}
```

All processes started with that config file will automatically use these strategies. This ensures consistent behavior across all processes in a deployment, including across macOS and Windows in two-host setups.

### Predefined Strategy Profiles

To simplify testing and comparison, the project includes three predefined strategy profiles. Instead of manually editing config files, you can use these profiles by passing a profile name to the startup and benchmark scripts.

**Available Profiles:**

1. **`baseline`** (default): Conservative, predictable configuration
   - Forwarding: `round_robin` (sequential)
   - Async: `false` (blocking)
   - Chunking: `fixed` (200 records per chunk)
   - Fairness: `strict` (hard per-team limits)

2. **`parallel`**: Optimized for throughput with parallel execution
   - Forwarding: `parallel` (all neighbors simultaneously)
   - Async: `true` (custom threading-based async)
   - Chunking: `adaptive` (adjusts based on result size)
   - Fairness: `strict` (maintains fairness guarantees)

3. **`balanced`**: Smart routing with flexible fairness
   - Forwarding: `capacity` (least-loaded first)
   - Async: `true` (custom threading-based async)
   - Chunking: `query_based` (adjusts based on query limit)
   - Fairness: `weighted` (allows load balancing between teams)

**Using Profiles:**

All startup and benchmark scripts accept an optional profile parameter:

```bash
# Single-host: Start servers with baseline profile (default)
scripts\start_single_host_windows.bat
# or explicitly:
scripts\start_single_host_windows.bat baseline

# Start with parallel profile
scripts\start_single_host_windows.bat parallel

# Run benchmark with the same profile
scripts\benchmark_single_host.bat parallel
```

**Two-host setup:**
```bash
# Windows side (must use same profile on both hosts)
scripts\start_two_hosts_windows.bat balanced

# macOS side (must use same profile)
./scripts/start_two_hosts_macos.sh balanced

# Run benchmark (from either machine)
scripts\benchmark_two_hosts.bat balanced
```

**Important:** When using two-host setup, both Windows and macOS must use the **same profile** to ensure consistent behavior across all processes.

**Profile Config Files:**

Each profile has dedicated config files:
- `one_host_config_baseline.json`, `one_host_config_parallel.json`, `one_host_config_balanced.json`
- `two_hosts_config_baseline.json`, `two_hosts_config_parallel.json`, `two_hosts_config_balanced.json`

These files contain the same process topology but with different strategy configurations. You can still manually edit these files if you need custom configurations.

### Overriding Strategies

Strategies can be overridden per-process via command-line arguments:

```bash
# Example: Override forwarding strategy for one process
python node.py config.json A --forwarding-strategy parallel --async-forwarding

# Example: Use default strategies from config file (recommended)
python node.py config.json A
```


## Benchmarking

### Unified Benchmark Tool

The unified benchmark tool (`benchmark_unified.py`) provides real-time visualization showing:
- Server output from all processes across all hosts in real-time
- Process metrics (active requests, queue size, processing time)
- Benchmark statistics (latency, throughput, success rate)
- Strategy configuration from config file
- Recent log output from each process

The benchmark tests only the strategy configuration specified in the config file. Results are saved to a text file named with the strategy (e.g., `benchmark_round_robin_blocking_fixed_strict.txt`).

### Single-Host Benchmark

**Windows:**
```bash
# Use baseline profile (default)
scripts\benchmark_single_host.bat

# Use specific profile
scripts\benchmark_single_host.bat parallel
scripts\benchmark_single_host.bat balanced
```

**macOS/Linux:**
```bash
# Use baseline profile (default)
./scripts/benchmark_single_host.sh

# Use specific profile
./scripts/benchmark_single_host.sh parallel
./scripts/benchmark_single_host.sh balanced
```

**With options:**
```bash
scripts\benchmark_single_host.bat parallel --num-requests 200 --concurrency 20 --update-interval 0.5
```

Results saved to: `logs/windows/benchmark_<strategy>.txt` or `logs/macos/benchmark_<strategy>.txt`
Example: `benchmark_round_robin_blocking_fixed_strict.txt`

### Two-Host Benchmark

**Windows (from Windows machine):**
```bash
# Use baseline profile (default)
scripts\benchmark_two_hosts.bat

# Use specific profile (must match profile used when starting servers)
scripts\benchmark_two_hosts.bat parallel
scripts\benchmark_two_hosts.bat balanced
```

**macOS (from macOS machine):**
```bash
./scripts/benchmark_two_hosts.sh
```

**With options:**
```bash
scripts\benchmark_two_hosts.bat --num-requests 200 --concurrency 20
```

Results saved to: `logs/two_hosts/benchmark_<strategy>.txt`
Example: `benchmark_round_robin_blocking_fixed_strict.txt`

### Benchmark Options

All benchmark scripts support these options:
- `--num-requests N`: Number of requests (default: 100)
- `--concurrency N`: Concurrency level (default: 10)
- `--update-interval N`: Dashboard update interval in seconds (default: 1.0)
- `--output-dir DIR`: Output directory for results (default: logs/windows or logs/two_hosts)

### Real-Time Dashboard

The benchmark tool displays a real-time dashboard that updates every second (configurable), showing:

**Process Status:**
- Process ID, role, team for each process
- Online/offline status
- Active requests count
- Queue size
- Average processing time
- Data files loaded
- Processing state (Processing, Ready, No Data)

**Server Output:**
- Recent log lines from each process
- Query execution logs
- Data processing logs

**Benchmark Statistics:**
- Total requests, successful, failed
- Success rate percentage
- Average, P95, P99 latency
- Throughput (requests per second)
- Total records returned

**Data Distribution:**
- Files loaded per host
- Active requests per host
- Queue sizes per host
- Online process count per host

The dashboard clearly shows:
- Whether data is being distributed between macOS and Windows
- Whether benchmarking is working correctly
- Which processes are processing queries
- Real-time performance metrics

## Configuration

Configuration files:
- `one_host_config.json` - Single-host setup (all processes on 127.0.0.1)
- `two_hosts_config.json` - Two-host setup (Windows 192.168.1.2 + macOS 192.168.1.1)

Each process requires:
- `id`: Process identifier (A-F)
- `role`: leader, team_leader, or worker
- `team`: green or pink
- `host`: IP address or hostname
- `port`: Listening port (60051-60056)
- `neighbors`: List of neighbor process IDs (defines overlay topology)

## gRPC API

Defined in `overlay.proto`:

- **`Query`** - Submit query with filters, returns query UID and chunk metadata
  - Returns: `uid`, `total_chunks`, `total_records`, `hops`, `status`
- **`GetChunk`** - Retrieve data chunks by UID and chunk index
  - Returns: `uid`, `chunk_index`, `total_chunks`, `data` (JSON), `is_last`, `status`
- **`GetMetrics`** - Get process metrics (queue size, active requests, etc.)
  - Returns: `process_id`, `role`, `team`, `active_requests`, `queue_size`, `avg_processing_time_ms`, `data_files_loaded`, `is_healthy`
- **`Shutdown`** - Graceful shutdown (optional)

## Implementation

### Core Modules (`overlay_core/`)

- **`QueryOrchestrator`** - Orchestrates query execution across the overlay network
  - Coordinates between all subsystems (caching, fairness, routing)
  - Handles query execution, forwarding, and result aggregation
  - Manages strategy selection and execution
  
- **`NeighborRegistry`** - Manages connections to neighbor nodes in the overlay
  - Lazy client creation per neighbor
  - Handles gRPC channel management
  - Provides `RemoteNodeClient` instances for neighbor communication
  
- **`DataStore`** - Team-specific data loading and filtering
  - Loads CSV files for assigned date ranges
  - Enforces team-specific data partitioning
  - Provides query filtering capabilities
  
- **`ResultCache`** - TTL-based chunk caching
  - Stores `ChunkedResult` objects with expiration
  - Thread-safe cache with automatic eviction
  
- **`RequestAdmissionController`** - Capacity management and fairness
  - Admits/rejects requests based on capacity limits
  - Implements fairness strategies (strict, weighted, hybrid)
  - Tracks active requests per team
  
- **`MetricsTracker`** - Performance metrics collection
  - Tracks processing times
  - Provides snapshot of current metrics
  
- **`strategies.py`** - Strategy pattern implementations
  - Forwarding strategies (RoundRobin, Parallel, CapacityBased)
  - Chunking strategies (Fixed, Adaptive, QueryBased)
  - Fairness strategies (StrictPerTeam, Weighted, Hybrid)
  - Custom async implementation using threading (not gRPC async)

### Design Patterns

- **Facade Pattern**: `QueryOrchestrator` provides unified interface to complex subsystem
- **Proxy Pattern**: `NeighborRegistry` and `RemoteNodeClient` hide remote gRPC complexity
- **Strategy Pattern**: Configurable forwarding, chunking, and fairness algorithms
- **Template Method**: Strategy base classes define common interface

### Async Implementation

- **Custom async implementation** using Python `threading` module
- **NOT using gRPC async APIs** (as specified in requirements)
- Parallel forwarding implemented via threads, not asyncio
- Blocking operations remain for local data access and cache retrieval

## Network Requirements

- TCP ports 60051-60056 must be open between hosts
- Hosts should be on the same subnet or have routing configured
- Network latency < 100ms recommended for optimal performance
- For two-host setup: Windows should be on 192.168.1.2, macOS on 192.168.1.1


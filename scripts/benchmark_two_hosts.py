#!/usr/bin/env python3
"""
Benchmark script for two-host configuration.
Assumes servers are already running on both hosts.
"""

import argparse
import grpc
import json
import sys
import time

sys.path.append(sys.path[0] + '/..')
import overlay_pb2
import overlay_pb2_grpc


def wait_for_leader(address, timeout=60):
    """Wait for leader to be ready."""
    start_time = time.time()
    print(f"Waiting for leader at {address} to be ready...", end="", flush=True)
    
    while time.time() - start_time < timeout:
        try:
            channel = grpc.insecure_channel(address)
            stub = overlay_pb2_grpc.OverlayNodeStub(channel)
            metrics = stub.GetMetrics(overlay_pb2.MetricsRequest(), timeout=2)
            channel.close()
            
            if metrics.process_id and metrics.role == "leader":
                print(f" Ready! (Leader: {metrics.process_id})")
                time.sleep(2)
                return True
        except Exception:
            pass
        
        time.sleep(1)
        print(".", end="", flush=True)
    
    print(f"\nTimeout waiting for leader at {address}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Benchmark two-host configuration")
    parser.add_argument("--host", default="192.168.1.2", help="Leader host (default: 192.168.1.2)")
    parser.add_argument("--port", type=int, default=60051, help="Leader port (default: 60051)")
    parser.add_argument("--requests", type=int, default=200, help="Number of requests (default: 200)")
    parser.add_argument("--concurrency", type=int, default=20, help="Concurrency level (default: 20)")
    args = parser.parse_args()
    
    print("=" * 80)
    print("TWO-HOST BENCHMARK")
    print("=" * 80)
    print(f"Target: {args.host}:{args.port}")
    print(f"Requests: {args.requests}, Concurrency: {args.concurrency}")
    print()
    print("NOTE: Make sure servers are running on both hosts:")
    print("  - Windows (192.168.1.2): Run scripts/start_two_hosts_windows.bat")
    print("  - macOS (192.168.1.1): Run scripts/start_two_hosts_macos.sh")
    print()
    
    if not wait_for_leader(f"{args.host}:{args.port}"):
        print("ERROR: Could not connect to leader. Make sure servers are running.")
        sys.exit(1)
    
    print()
    print("Running benchmark...")
    print()
    
    # Import and run benchmark
    from benchmark import Benchmark
    
    # Use logs directory for Windows
    import os
    output_dir = "logs" if os.name == 'nt' else "."
    os.makedirs(output_dir, exist_ok=True)
    
    benchmark = Benchmark(args.host, args.port)
    stats = benchmark.run_benchmark(args.requests, args.concurrency, output_dir)
    
    # Save results with specific filename for two-host
    output_file = os.path.join(output_dir, "benchmark_results_two_hosts.json")
    with open(output_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print()
    print(f"Results saved to {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()


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


def show_log_summary(log_dir):
    """Show summary of recent log entries from both hosts."""
    import os
    from pathlib import Path
    
    log_path = Path(log_dir)
    if not log_path.exists():
        print(f"Log directory not found: {log_dir}")
        return
    
    # Windows logs
    print("\n--- Windows Host (192.168.1.2) ---")
    windows_logs = {
        "A (Leader)": log_path / "windows_192.168.1.2_node_a.log",
        "B (Team Leader)": log_path / "windows_192.168.1.2_node_b.log",
        "D (Worker)": log_path / "windows_192.168.1.2_node_d.log",
    }
    
    for process_name, log_file in windows_logs.items():
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # Get last 3-5 meaningful lines (skip empty lines)
                    recent = [l for l in lines[-10:] if l.strip()][-3:]
                    if recent:
                        print(f"\n  {process_name} ({log_file.name}):")
                        for line in recent:
                            print(f"    {line.rstrip()}")
            except Exception as e:
                print(f"  {process_name}: Error reading log: {e}")
        else:
            print(f"  {process_name}: Log file not found")
    
    # macOS logs
    print("\n--- macOS Host (192.168.1.1) ---")
    macos_logs = {
        "C (Worker)": log_path / "macos_192.168.1.1_node_c.log",
        "E (Team Leader)": log_path / "macos_192.168.1.1_node_e.log",
        "F (Worker)": log_path / "macos_192.168.1.1_node_f.log",
    }
    
    for process_name, log_file in macos_logs.items():
        if log_file.exists():
            try:
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # Get last 3-5 meaningful lines (skip empty lines)
                    recent = [l for l in lines[-10:] if l.strip()][-3:]
                    if recent:
                        print(f"\n  {process_name} ({log_file.name}):")
                        for line in recent:
                            print(f"    {line.rstrip()}")
            except Exception as e:
                print(f"  {process_name}: Error reading log: {e}")
        else:
            print(f"  {process_name}: Log file not found (check macOS machine: 192.168.1.1)")

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
        print("\n" + "=" * 80)
        print("ERROR: Could not connect to leader.")
        print("=" * 80)
        print("\nMake sure servers are running on both hosts:")
        print("\n1. On Windows (192.168.1.2):")
        print("   cd scripts")
        print("   start_two_hosts_windows.bat")
        print("   - This starts: A (Leader), B (Team Leader), D (Worker)")
        print("\n2. On macOS (192.168.1.1):")
        print("   cd scripts")
        print("   chmod +x start_two_hosts_macos.sh")
        print("   ./start_two_hosts_macos.sh")
        print("   - This starts: C (Worker), E (Team Leader), F (Worker)")
        print("\n3. Check process logs in logs/two_hosts/ for errors:")
        print("   - Windows: windows_192.168.1.2_node_*.log")
        print("   - macOS: macos_192.168.1.1_node_*.log")
        print("\n4. Verify connectivity:")
        print(f"   - Can ping {args.host}?")
        print(f"   - Is firewall allowing port {args.port}?")
        print("=" * 80)
        sys.exit(1)
    
    print()
    print("Running benchmark...")
    print()
    
    # Import and run benchmark
    from benchmark import Benchmark
    import os
    import platform
    
    # Use two_hosts logs directory
    output_dir = "logs/two_hosts"
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
    
    # Show log summary if available
    print()
    print("PROCESS LOGS SUMMARY")
    print("=" * 80)
    show_log_summary(output_dir)
    
    print()
    print("=" * 80)
    print("PROCESS LOGS")
    print("=" * 80)
    print()
    print("Logs are saved to logs/two_hosts/ with filenames indicating platform and IP:")
    print()
    print("Windows (192.168.1.2):")
    print("  - windows_192.168.1.2_node_a.log (Leader)")
    print("  - windows_192.168.1.2_node_b.log (Team Leader)")
    print("  - windows_192.168.1.2_node_d.log (Worker)")
    print()
    print("macOS (192.168.1.1):")
    print("  - macos_192.168.1.1_node_c.log (Worker)")
    print("  - macos_192.168.1.1_node_e.log (Team Leader)")
    print("  - macos_192.168.1.1_node_f.log (Worker)")
    print()
    print("View logs:")
    print("  Windows: scripts\\view_two_hosts_logs.bat")
    print("  macOS:   scripts/view_two_hosts_logs.sh")
    print("=" * 80)


if __name__ == "__main__":
    main()


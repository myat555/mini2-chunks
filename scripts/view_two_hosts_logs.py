#!/usr/bin/env python3
"""
View logs from both Windows and macOS processes in two-host setup.
"""

import os
import sys
import glob
from pathlib import Path

def get_log_dir():
    """Get the two_hosts log directory."""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    return project_root / "logs" / "two_hosts"

def get_recent_logs(log_file, lines=20):
    """Get recent lines from a log file."""
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            return all_lines[-lines:] if len(all_lines) > lines else all_lines
    except FileNotFoundError:
        return [f"Log file not found: {log_file}\n"]
    except Exception as e:
        return [f"Error reading log: {e}\n"]

def print_log_section(title, log_files, lines=20):
    """Print a section of logs."""
    print("\n" + "=" * 80)
    print(f"{title}")
    print("=" * 80)
    
    found_any = False
    for log_file in log_files:
        if log_file.exists():
            found_any = True
            print(f"\n--- {log_file.name} ---")
            recent = get_recent_logs(log_file, lines)
            print("".join(recent))
        else:
            print(f"\n--- {log_file.name} ---")
            print("Log file not found (process may not have run yet)")
    
    if not found_any:
        print("\nNo log files found in this section.")

def main():
    log_dir = get_log_dir()
    
    if not log_dir.exists():
        print(f"Log directory not found: {log_dir}")
        print("\nMake sure servers have been started and logs were generated.")
        sys.exit(1)
    
    print("=" * 80)
    print("TWO-HOST PROCESS LOGS")
    print("=" * 80)
    print(f"Log directory: {log_dir}")
    
    # Windows logs (192.168.1.2)
    windows_logs = [
        log_dir / "windows_192.168.1.2_node_a.log",  # Leader
        log_dir / "windows_192.168.1.2_node_b.log",  # Team Leader
        log_dir / "windows_192.168.1.2_node_d.log",  # Worker
    ]
    
    # macOS logs (192.168.1.1)
    macos_logs = [
        log_dir / "macos_192.168.1.1_node_c.log",  # Worker
        log_dir / "macos_192.168.1.1_node_e.log",  # Team Leader
        log_dir / "macos_192.168.1.1_node_f.log",  # Worker
    ]
    
    # Show Windows logs
    print_log_section("WINDOWS HOST (192.168.1.2)", windows_logs, lines=30)
    
    # Show macOS logs
    print_log_section("macOS HOST (192.168.1.1)", macos_logs, lines=30)
    
    # Show benchmark results if available
    benchmark_file = log_dir / "benchmark_results_two_hosts.json"
    if benchmark_file.exists():
        print("\n" + "=" * 80)
        print("BENCHMARK RESULTS")
        print("=" * 80)
        print(f"Results file: {benchmark_file}")
        try:
            import json
            with open(benchmark_file, 'r') as f:
                results = json.load(f)
                print(f"\nTotal Requests: {results.get('total_requests', 0)}")
                print(f"Successful: {results.get('successful_requests', 0)}")
                print(f"Failed: {results.get('failed_requests', 0)}")
                print(f"Throughput: {results.get('throughput_rps', 0):.2f} req/s")
                print(f"Avg Latency: {results.get('avg_latency_ms', 0):.2f} ms")
                print(f"Total Records: {results.get('total_records_returned', 0)}")
        except Exception as e:
            print(f"Error reading benchmark results: {e}")
    
    print("\n" + "=" * 80)
    print("NOTE: macOS logs are only available if running from macOS host.")
    print("For complete logs, check logs/two_hosts/ on both machines.")
    print("=" * 80)

if __name__ == "__main__":
    main()


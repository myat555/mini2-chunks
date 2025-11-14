#!/usr/bin/env python3
"""Run benchmark with real-time monitoring of both hosts."""

import argparse
import json
import os
import sys
import subprocess
import threading
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from benchmark import Benchmark

# Import monitor - handle both direct and script directory execution
import sys
import os
if os.path.dirname(__file__) not in sys.path:
    sys.path.insert(0, os.path.dirname(__file__))
from monitor_two_hosts import TwoHostMonitor


class BenchmarkWithMonitoring:
    """Run benchmark while monitoring both hosts."""

    def __init__(
        self,
        leader_host: str,
        leader_port: int,
        config_path: str,
        output_dir: str,
        monitor_interval: float = 2.0,
    ):
        self.leader_host = leader_host
        self.leader_port = leader_port
        self.config_path = config_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.monitor_interval = monitor_interval
        self.monitoring = False
        self.monitor_thread = None
        self.snapshots = []

    def start_monitoring(self):
        """Start monitoring in a separate thread."""
        self.monitoring = True
        monitor = TwoHostMonitor(self.config_path, self.monitor_interval)
        
        def monitor_loop():
            while self.monitoring:
                snapshot = monitor.snapshot()
                self.snapshots.append(snapshot)
                time.sleep(self.monitor_interval)
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)

    def run_benchmark_with_monitoring(
        self,
        num_requests: int = 100,
        concurrency: int = 10,
    ) -> dict:
        """Run benchmark while monitoring."""
        print("=" * 60)
        print("BENCHMARK WITH REAL-TIME MONITORING")
        print("=" * 60)
        
        # Start monitoring
        print("Starting monitoring...")
        self.start_monitoring()
        time.sleep(2)  # Let monitoring start
        
        # Take pre-benchmark snapshot
        monitor = TwoHostMonitor(self.config_path, self.monitor_interval)
        pre_snapshot = monitor.snapshot()
        
        print("\nRunning benchmark...")
        benchmark = Benchmark(self.leader_host, self.leader_port)
        benchmark_results = benchmark.run_benchmark_internal(
            num_requests=num_requests,
            concurrency=concurrency,
            query_type="simple",
        )
        
        # Wait a bit for metrics to stabilize
        time.sleep(2)
        
        # Take post-benchmark snapshot
        post_snapshot = monitor.snapshot()
        
        # Stop monitoring
        self.stop_monitoring()
        
        # Collect all metrics from processes
        all_metrics = monitor.collect_all_metrics()
        
        # Combine results
        combined_results = {
            "benchmark": benchmark_results,
            "pre_benchmark_snapshot": pre_snapshot,
            "post_benchmark_snapshot": post_snapshot,
            "process_metrics": all_metrics,
            "monitoring_snapshots": self.snapshots,
            "timestamp": time.time(),
        }
        
        # Save results
        output_file = self.output_dir / "benchmark_with_monitoring.json"
        with open(output_file, "w") as f:
            json.dump(combined_results, f, indent=2, default=str)
        
        # Also save a human-readable summary
        summary_file = self.output_dir / "benchmark_summary.txt"
        self._write_summary(combined_results, summary_file)
        
        print(f"\nResults saved to: {output_file}")
        print(f"Summary saved to: {summary_file}")
        
        return combined_results

    def _write_summary(self, results: dict, output_file: Path):
        """Write human-readable summary."""
        with open(output_file, "w") as f:
            f.write("=" * 80 + "\n")
            f.write("BENCHMARK SUMMARY WITH MONITORING\n")
            f.write("=" * 80 + "\n\n")
            
            # Benchmark results
            benchmark = results.get("benchmark", {})
            stats = benchmark.get("statistics", {})
            
            f.write("BENCHMARK RESULTS:\n")
            f.write("-" * 80 + "\n")
            f.write(f"Total Requests: {benchmark.get('total_requests', 0)}\n")
            f.write(f"Successful: {benchmark.get('successful_requests', 0)}\n")
            f.write(f"Failed: {benchmark.get('failed_requests', 0)}\n")
            f.write(f"Success Rate: {stats.get('success_rate', 0):.1f}%\n")
            f.write(f"Avg Latency: {stats.get('avg_latency_ms', 0):.2f} ms\n")
            f.write(f"P95 Latency: {stats.get('p95_latency_ms', 0):.2f} ms\n")
            f.write(f"P99 Latency: {stats.get('p99_latency_ms', 0):.2f} ms\n")
            f.write(f"Throughput: {stats.get('throughput_req_per_sec', 0):.2f} req/s\n")
            f.write(f"Total Records: {stats.get('total_records_returned', 0)}\n")
            f.write("\n")
            
            # Pre-benchmark snapshot
            pre = results.get("pre_benchmark_snapshot", {})
            pre_summary = pre.get("summary", {})
            f.write("PRE-BENCHMARK STATE:\n")
            f.write("-" * 80 + "\n")
            f.write(f"Online Processes: {pre_summary.get('online_processes', 0)}/{pre_summary.get('total_processes', 0)}\n")
            f.write(f"Active Requests: {pre_summary.get('total_active_requests', 0)}\n")
            f.write(f"Queue Size: {pre_summary.get('total_queue_size', 0)}\n")
            f.write("\n")
            
            # Post-benchmark snapshot
            post = results.get("post_benchmark_snapshot", {})
            post_summary = post.get("summary", {})
            f.write("POST-BENCHMARK STATE:\n")
            f.write("-" * 80 + "\n")
            f.write(f"Online Processes: {post_summary.get('online_processes', 0)}/{post_summary.get('total_processes', 0)}\n")
            f.write(f"Active Requests: {post_summary.get('total_active_requests', 0)}\n")
            f.write(f"Queue Size: {post_summary.get('total_queue_size', 0)}\n")
            f.write(f"Avg Processing Time: {post_summary.get('avg_processing_time_ms', 0):.2f} ms\n")
            f.write("\n")
            
            # Process metrics
            f.write("PROCESS METRICS:\n")
            f.write("-" * 80 + "\n")
            processes = results.get("process_metrics", {})
            for process_id, proc in sorted(processes.items()):
                f.write(f"\n{process_id} ({proc.get('role', 'N/A')}/{proc.get('team', 'N/A')}) on {proc.get('host', 'N/A')}:\n")
                f.write(f"  Status: {proc.get('status', 'unknown')}\n")
                if proc.get("status") == "online":
                    f.write(f"  Active Requests: {proc.get('active_requests', 0)}\n")
                    f.write(f"  Queue Size: {proc.get('queue_size', 0)}\n")
                    f.write(f"  Avg Processing: {proc.get('avg_processing_time_ms', 0):.2f} ms\n")
                    f.write(f"  Data Files: {proc.get('data_files_loaded', 0)}\n")


def main():
    parser = argparse.ArgumentParser(description="Run benchmark with real-time monitoring.")
    parser.add_argument(
        "--leader-host",
        default="192.168.1.2",
        help="Leader host address.",
    )
    parser.add_argument(
        "--leader-port",
        type=int,
        default=60051,
        help="Leader port.",
    )
    parser.add_argument(
        "--config",
        default="two_hosts_config.json",
        help="Overlay configuration file.",
    )
    parser.add_argument(
        "--output-dir",
        default="logs/two_hosts",
        help="Output directory for results.",
    )
    parser.add_argument(
        "--num-requests",
        type=int,
        default=100,
        help="Number of requests.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Concurrency level.",
    )
    parser.add_argument(
        "--monitor-interval",
        type=float,
        default=2.0,
        help="Monitoring update interval in seconds.",
    )

    args = parser.parse_args()

    runner = BenchmarkWithMonitoring(
        args.leader_host,
        args.leader_port,
        args.config,
        args.output_dir,
        args.monitor_interval,
    )
    
    results = runner.run_benchmark_with_monitoring(
        args.num_requests,
        args.concurrency,
    )
    
    print("\nBenchmark with monitoring completed!")


if __name__ == "__main__":
    main()


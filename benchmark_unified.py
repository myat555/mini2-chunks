#!/usr/bin/env python3
"""Unified benchmarking tool with real-time visualization of server output and strategy comparison."""

import argparse
import json
import os
import sys
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict

import overlay_pb2
import overlay_pb2_grpc
import grpc


class UnifiedBenchmark:
    """Unified benchmark with real-time visualization."""

    def __init__(
        self,
        leader_host: str,
        leader_port: int,
        config_path: str,
        output_dir: str = "logs",
    ):
        self.leader_host = leader_host
        self.leader_port = leader_port
        self.config_path = config_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._load_config()
        self.monitoring = False
        self.process_metrics_history = defaultdict(list)
        self.server_outputs = defaultdict(list)

    def _load_config(self):
        """Load overlay configuration."""
        with open(self.config_path, "r") as f:
            self.config = json.load(f)

    def clear_screen(self):
        """Clear terminal screen."""
        os.system("cls" if os.name == "nt" else "clear")

    def collect_process_metrics(self) -> Dict[str, Dict]:
        """Collect metrics from all processes."""
        metrics = {}
        processes = self.config.get("processes", {})
        
        for process_id, process_info in processes.items():
            try:
                address = f"{process_info['host']}:{process_info['port']}"
                with grpc.insecure_channel(address, options=[("grpc.keepalive_timeout_ms", 1000)]) as channel:
                    stub = overlay_pb2_grpc.OverlayNodeStub(channel)
                    try:
                        m = stub.GetMetrics(overlay_pb2.MetricsRequest(), timeout=1)
                        # Try to get strategy fields, with fallback for older proto versions
                        try:
                            forwarding_strat = m.forwarding_strategy if m.forwarding_strategy else "unknown"
                            async_fwd = m.async_forwarding
                            chunking_strat = m.chunking_strategy if m.chunking_strategy else "unknown"
                            fairness_strat = m.fairness_strategy if m.fairness_strategy else "unknown"
                        except AttributeError:
                            # Fallback for older proto versions
                            forwarding_strat = "unknown"
                            async_fwd = False
                            chunking_strat = "unknown"
                            fairness_strat = "unknown"
                        
                        metrics[process_id] = {
                            "process_id": m.process_id,
                            "role": m.role,
                            "team": m.team,
                            "host": process_info["host"],
                            "port": process_info["port"],
                            "active_requests": m.active_requests,
                            "queue_size": m.queue_size,
                            "avg_processing_time_ms": round(m.avg_processing_time_ms, 2),
                            "data_files_loaded": m.data_files_loaded,
                            "is_healthy": m.is_healthy,
                            "status": "online",
                            "forwarding_strategy": forwarding_strat,
                            "async_forwarding": async_fwd,
                            "chunking_strategy": chunking_strat,
                            "fairness_strategy": fairness_strat,
                            "timestamp": time.time(),
                        }
                    except grpc.RpcError:
                        metrics[process_id] = {
                            "process_id": process_id,
                            "host": process_info["host"],
                            "status": "offline",
                        }
            except Exception:
                metrics[process_id] = {
                    "process_id": process_id,
                    "status": "offline",
                }
        
        return metrics

    def read_server_logs(self, log_dir: Path, lines: int = 3) -> Dict[str, List[str]]:
        """Read recent server log output."""
        logs = {}
        
        if not log_dir.exists():
            return logs
        
        # Try to find log files for each process
        for process_id in self.config.get("processes", {}).keys():
            patterns = [
                f"*{process_id.lower()}*.log",
                f"*node_{process_id.lower()}.log",
                f"*{process_id}*.log",
            ]
            
            for pattern in patterns:
                log_files = list(log_dir.glob(pattern))
                if log_files:
                    try:
                        with open(log_files[0], "r", encoding="utf-8", errors="ignore") as f:
                            all_lines = f.readlines()
                            recent = [line.strip() for line in all_lines[-lines:] if line.strip()]
                            if recent:
                                logs[process_id] = recent
                            break
                    except:
                        pass
        
        return logs

    def display_dashboard(self, metrics: Dict, logs: Dict, benchmark_stats: Optional[Dict] = None):
        """Display real-time dashboard."""
        self.clear_screen()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print("=" * 120)
        print(f"UNIFIED BENCHMARK DASHBOARD - {current_time}")
        print("=" * 120)
        
        # Group by host
        hosts = defaultdict(list)
        for process_id, proc in metrics.items():
            host = proc.get("host", "unknown")
            hosts[host].append((process_id, proc))
        
        # Display metrics by host
        for host, host_processes in sorted(hosts.items()):
            print(f"\n{'─' * 120}")
            print(f"HOST: {host}")
            print(f"{'─' * 120}")
            print(f"{'ID':<4} {'Role':<12} {'Team':<6} {'Status':<8} {'Active':<8} {'Queue':<8} {'Avg(ms)':<10} {'Files':<8} {'Processing':<12}")
            print(f"{'─' * 120}")
            
            # Track strategies for this host
            host_strategies = {}
            
            for process_id, proc in sorted(host_processes):
                pid = proc.get("process_id", "N/A")
                role = proc.get("role", "N/A")
                team = proc.get("team", "N/A")
                status = proc.get("status", "unknown")
                active = proc.get("active_requests", 0)
                queue = proc.get("queue_size", 0)
                avg_ms = proc.get("avg_processing_time_ms", 0)
                files = proc.get("data_files_loaded", 0)
                
                # Check if data is being processed
                data_indicator = "✓ Loaded" if files > 0 else "✗ No Data"
                if active > 0:
                    data_indicator = f"→ {active} req"  # Processing
                elif files > 0 and active == 0:
                    data_indicator = "✓ Ready"
                
                status_icon = "✓" if status == "online" else "✗"
                
                print(
                    f"{pid:<4} {role:<12} {team:<6} {status_icon} {status:<7} "
                    f"{active:<8} {queue:<8} {avg_ms:<10.2f} {files:<8} {data_indicator:<12}"
                )
                
                # Store strategy info
                if status == "online":
                    host_strategies[process_id] = {
                        "forwarding": proc.get("forwarding_strategy", "unknown"),
                        "async": proc.get("async_forwarding", False),
                        "chunking": proc.get("chunking_strategy", "unknown"),
                        "fairness": proc.get("fairness_strategy", "unknown"),
                    }
            
            # Show strategies in use on this host
            if host_strategies:
                print(f"\n{'─' * 120}")
                print(f"STRATEGIES IN USE ({host}):")
                print(f"{'─' * 120}")
                for proc_id, strat in sorted(host_strategies.items()):
                    async_str = "async" if strat["async"] else "blocking"
                    print(f"  {proc_id}: Forward={strat['forwarding']}({async_str}), Chunk={strat['chunking']}, Fair={strat['fairness']}")
            
            # Show recent server output for this host
            print(f"\n{'─' * 120}")
            print(f"RECENT SERVER OUTPUT ({host}):")
            print(f"{'─' * 120}")
            for process_id, proc in sorted(host_processes):
                if process_id in logs:
                    for log_line in logs[process_id][-2:]:  # Last 2 lines
                        # Truncate long lines
                        if len(log_line) > 110:
                            log_line = log_line[:107] + "..."
                        print(f"  {process_id}: {log_line}")
        
        # Benchmark statistics
        if benchmark_stats:
            print(f"\n{'─' * 120}")
            print("BENCHMARK STATISTICS:")
            print(f"{'─' * 120}")
            stats = benchmark_stats.get("statistics", {})
            print(f"Total Requests: {benchmark_stats.get('total_requests', 0)}")
            print(f"Successful: {benchmark_stats.get('successful_requests', 0)}")
            print(f"Failed: {benchmark_stats.get('failed_requests', 0)}")
            print(f"Success Rate: {stats.get('success_rate', 0):.1f}%")
            print(f"Avg Latency: {stats.get('avg_latency_ms', 0):.2f} ms")
            print(f"Throughput: {stats.get('throughput_req_per_sec', 0):.2f} req/s")
            print(f"Total Records: {stats.get('total_records_returned', 0)}")
            
            # Show data distribution across hosts
            print(f"\n{'─' * 120}")
            print("DATA DISTRIBUTION ACROSS HOSTS:")
            print(f"{'─' * 120}")
            for host, host_processes in sorted(hosts.items()):
                total_files = sum(p[1].get("data_files_loaded", 0) for p in host_processes)
                active_total = sum(p[1].get("active_requests", 0) for p in host_processes)
                queue_total = sum(p[1].get("queue_size", 0) for p in host_processes)
                online_count = sum(1 for p in host_processes if p[1].get("status") == "online")
                print(f"{host}: {online_count}/{len(host_processes)} online, {total_files} files, {active_total} active, {queue_total} queued")
            
            # Strategy comparison summary
            if benchmark_stats:
                print(f"\n{'─' * 120}")
                print("STRATEGY COMPARISON:")
                print(f"{'─' * 120}")
                
                # Collect all strategies in use across all hosts
                all_strategies = {}
                for host, host_processes in sorted(hosts.items()):
                    for process_id, proc in host_processes:
                        if proc.get("status") == "online":
                            key = (
                                proc.get("forwarding_strategy", "unknown"),
                                proc.get("async_forwarding", False),
                                proc.get("chunking_strategy", "unknown"),
                                proc.get("fairness_strategy", "unknown"),
                            )
                            if key not in all_strategies:
                                all_strategies[key] = []
                            all_strategies[key].append(process_id)
                
                if all_strategies:
                    print("Strategies currently in use:")
                    for (fwd, async_flag, chunk, fair), procs in sorted(all_strategies.items()):
                        async_str = "async" if async_flag else "blocking"
                        print(f"  {', '.join(sorted(procs))}: {fwd}({async_str}), {chunk}, {fair}")
                
                print("\nTo compare different strategies:")
                print("  1. Run servers with one strategy configuration (e.g., round_robin blocking)")
                print("  2. Run benchmark and note performance metrics (latency, throughput)")
                print("  3. Restart servers with different configuration (e.g., parallel async)")
                print("  4. Run benchmark again and compare results")
                print("\nExpected performance characteristics:")
                print("  - Parallel + async: Higher throughput, lower latency for concurrent queries")
                print("  - Round-robin: More balanced load, predictable order")
                print("  - Adaptive chunking: Better memory usage for varying result sizes")
                print("  - Weighted fairness: Better system utilization under mixed loads")
        
        print(f"\n{'─' * 120}")
        print("Press Ctrl+C to stop")
        print(f"{'─' * 120}\n")

    def send_query_request(self, query_params: Dict) -> Dict:
        """Send a query request and collect results."""
        try:
            address = f"{self.leader_host}:{self.leader_port}"
            with grpc.insecure_channel(address) as channel:
                stub = overlay_pb2_grpc.OverlayNodeStub(channel)
                
                request = overlay_pb2.QueryRequest(
                    query_type="filter",
                    query_params=json.dumps(query_params),
                    hops=[],
                    client_id="benchmark",
                )
                
                start = time.time()
                response = stub.Query(request)
                latency = (time.time() - start) * 1000
                
                if response.status != "ready" or not response.uid:
                    return {
                        "success": False,
                        "latency": latency,
                        "records": 0,
                        "hops": len(response.hops),
                    }
                
                # Collect all chunks
                total_records = 0
                for chunk_idx in range(response.total_chunks):
                    chunk_resp = stub.GetChunk(
                        overlay_pb2.ChunkRequest(uid=response.uid, chunk_index=chunk_idx)
                    )
                    if chunk_resp.status == "success":
                        try:
                            data = json.loads(chunk_resp.data)
                            total_records += len(data)
                        except:
                            pass
                    if chunk_resp.is_last:
                        break
                
                return {
                    "success": True,
                    "latency": latency,
                    "records": total_records,
                    "hops": len(response.hops),
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "latency": 0,
                "records": 0,
            }

    def run_benchmark(
        self,
        num_requests: int = 100,
        concurrency: int = 10,
        update_interval: float = 1.0,
        log_dir: Optional[str] = None,
    ) -> Dict:
        """Run benchmark with real-time monitoring."""
        print("=" * 120)
        print("UNIFIED BENCHMARK WITH REAL-TIME MONITORING")
        print("=" * 120)
        print(f"Requests: {num_requests}, Concurrency: {concurrency}")
        print("=" * 120)
        
        log_path = Path(log_dir) if log_dir else None
        results = []
        errors = 0
        lock = threading.Lock()
        monitoring = [True]
        
        # Start monitoring thread
        def monitor_loop():
            iteration = 0
            while monitoring[0]:
                iteration += 1
                metrics = self.collect_process_metrics()
                logs = self.read_server_logs(log_path, lines=3) if log_path else {}
                
                # Compute benchmark stats so far
                with lock:
                    current_results = list(results)
                    current_errors = errors
                
                benchmark_stats = None
                if current_results:
                    latencies = [r["latency"] for r in current_results if r.get("success")]
                    total_records = sum(r.get("records", 0) for r in current_results)
                    successful = sum(1 for r in current_results if r.get("success"))
                    failed = current_errors + len(current_results) - successful
                    
                    if latencies:
                        sorted_latencies = sorted(latencies)
                        benchmark_stats = {
                            "total_requests": len(current_results),
                            "successful_requests": successful,
                            "failed_requests": failed,
                            "statistics": {
                                "success_rate": (successful / len(current_results) * 100) if current_results else 0,
                                "avg_latency_ms": sum(latencies) / len(latencies),
                                "p95_latency_ms": sorted_latencies[int(len(sorted_latencies) * 0.95)] if len(sorted_latencies) > 0 else 0,
                                "p99_latency_ms": sorted_latencies[int(len(sorted_latencies) * 0.99)] if len(sorted_latencies) > 0 else 0,
                                "throughput_req_per_sec": len(current_results) / (time.time() - start_time) if time.time() > start_time else 0,
                                "total_records_returned": total_records,
                            },
                        }
                
                self.display_dashboard(metrics, logs, benchmark_stats)
                time.sleep(update_interval)
        
        start_time = time.time()
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        time.sleep(1)  # Let monitoring start
        
        # Run benchmark
        query_params = {
            "parameter": "PM2.5",
            "min_value": 10.0,
            "max_value": 50.0,
            "limit": 100,
        }
        
        def worker(worker_id: int, num_per_worker: int):
            nonlocal errors
            local_results = []
            for i in range(num_per_worker):
                result = self.send_query_request(query_params)
                local_results.append(result)
                if not result.get("success"):
                    with lock:
                        errors += 1
                time.sleep(0.01)
            
            with lock:
                results.extend(local_results)
        
        # Start workers
        workers = []
        requests_per_worker = num_requests // concurrency
        for i in range(concurrency):
            worker_id = i
            num_reqs = requests_per_worker + (1 if i < num_requests % concurrency else 0)
            thread = threading.Thread(target=worker, args=(worker_id, num_reqs))
            thread.start()
            workers.append(thread)
        
        # Wait for workers
        for thread in workers:
            thread.join()
        
        # Stop monitoring
        monitoring[0] = False
        time.sleep(update_interval + 0.5)
        
        # Final metrics
        final_metrics = self.collect_process_metrics()
        final_logs = self.read_server_logs(log_path, lines=5) if log_path else {}
        
        # Compute final statistics
        latencies = [r["latency"] for r in results if r.get("success")]
        total_records = sum(r.get("records", 0) for r in results)
        successful = sum(1 for r in results if r.get("success"))
        failed = errors
        duration = time.time() - start_time
        
        if latencies:
            sorted_latencies = sorted(latencies)
            statistics = {
                "success_rate": (successful / len(results) * 100) if results else 0,
                "avg_latency_ms": sum(latencies) / len(latencies),
                "min_latency_ms": min(latencies),
                "max_latency_ms": max(latencies),
                "p95_latency_ms": sorted_latencies[int(len(sorted_latencies) * 0.95)] if len(sorted_latencies) > 0 else 0,
                "p99_latency_ms": sorted_latencies[int(len(sorted_latencies) * 0.99)] if len(sorted_latencies) > 0 else 0,
                "throughput_req_per_sec": len(results) / duration if duration > 0 else 0,
                "total_records_returned": total_records,
                "avg_records_per_query": total_records / successful if successful > 0 else 0,
            }
        else:
            statistics = {}
        
        benchmark_results = {
            "total_requests": len(results),
            "successful_requests": successful,
            "failed_requests": failed,
            "duration_seconds": duration,
            "statistics": statistics,
            "final_metrics": final_metrics,
            "timestamp": time.time(),
        }
        
        # Final display
        self.display_dashboard(final_metrics, final_logs, benchmark_results)
        
        # Save results
        output_file = self.output_dir / "benchmark_results.json"
        with open(output_file, "w") as f:
            json.dump(benchmark_results, f, indent=2, default=str)
        
        print(f"\nResults saved to: {output_file}")
        
        return benchmark_results


def main():
    parser = argparse.ArgumentParser(description="Unified benchmark with real-time visualization.")
    parser.add_argument(
        "--leader-host",
        default="127.0.0.1",
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
        default="one_host_config.json",
        help="Overlay configuration file.",
    )
    parser.add_argument(
        "--output-dir",
        default="logs",
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
        "--update-interval",
        type=float,
        default=1.0,
        help="Dashboard update interval in seconds.",
    )
    parser.add_argument(
        "--log-dir",
        help="Directory containing server log files.",
    )

    args = parser.parse_args()

    benchmark = UnifiedBenchmark(
        args.leader_host,
        args.leader_port,
        args.config,
        args.output_dir,
    )
    
    benchmark.run_benchmark(
        args.num_requests,
        args.concurrency,
        args.update_interval,
        args.log_dir,
    )


if __name__ == "__main__":
    main()


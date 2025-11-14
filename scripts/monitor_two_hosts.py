#!/usr/bin/env python3
"""Real-time monitoring tool for two-host setup."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import overlay_pb2
import overlay_pb2_grpc
import grpc


class TwoHostMonitor:
    """Monitor processes on both Windows and macOS hosts."""

    def __init__(self, config_path: str, update_interval: float = 2.0):
        self.config_path = config_path
        self.update_interval = update_interval
        self._load_config()

    def _load_config(self):
        """Load overlay configuration."""
        with open(self.config_path, "r") as f:
            self.config = json.load(f)

    def collect_process_metrics(self, process_id: str, process_info: Dict) -> Dict:
        """Collect metrics from a single process."""
        try:
            address = f"{process_info['host']}:{process_info['port']}"
            with grpc.insecure_channel(address, options=[("grpc.keepalive_timeout_ms", 2000)]) as channel:
                stub = overlay_pb2_grpc.OverlayNodeStub(channel)
                try:
                    metrics = stub.GetMetrics(overlay_pb2.MetricsRequest(), timeout=2)
                    return {
                        "process_id": metrics.process_id,
                        "role": metrics.role,
                        "team": metrics.team,
                        "host": process_info["host"],
                        "port": process_info["port"],
                        "active_requests": metrics.active_requests,
                        "max_capacity": metrics.max_capacity,
                        "queue_size": metrics.queue_size,
                        "avg_processing_time_ms": round(metrics.avg_processing_time_ms, 2),
                        "data_files_loaded": metrics.data_files_loaded,
                        "is_healthy": metrics.is_healthy,
                        "status": "online",
                        "timestamp": time.time(),
                    }
                except grpc.RpcError as e:
                    return {
                        "process_id": process_id,
                        "host": process_info["host"],
                        "port": process_info["port"],
                        "status": "error",
                        "error": str(e.code()),
                        "timestamp": time.time(),
                    }
        except Exception as e:
            return {
                "process_id": process_id,
                "host": process_info.get("host", "unknown"),
                "port": process_info.get("port", 0),
                "status": "offline",
                "error": str(e),
                "timestamp": time.time(),
            }

    def collect_all_metrics(self) -> Dict:
        """Collect metrics from all processes."""
        all_metrics = {}
        processes = self.config.get("processes", {})
        
        for process_id, process_info in processes.items():
            all_metrics[process_id] = self.collect_process_metrics(process_id, process_info)
        
        return all_metrics

    def group_by_host(self, metrics: Dict) -> Dict[str, List[Dict]]:
        """Group metrics by host."""
        hosts = {}
        for process_id, process_metrics in metrics.items():
            host = process_metrics.get("host", "unknown")
            if host not in hosts:
                hosts[host] = []
            hosts[host].append(process_metrics)
        return hosts

    def display_metrics(self, metrics: Dict, clear_screen: bool = True):
        """Display metrics in a formatted way."""
        if clear_screen:
            os.system("cls" if os.name == "nt" else "clear")
        
        hosts = self.group_by_host(metrics)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print("=" * 100)
        print(f"TWO-HOST MONITORING - {current_time}")
        print("=" * 100)
        
        for host, host_processes in hosts.items():
            print(f"\n{'─' * 100}")
            print(f"HOST: {host}")
            print(f"{'─' * 100}")
            print(f"{'ID':<4} {'Role':<12} {'Team':<6} {'Status':<10} {'Active':<8} {'Queue':<8} {'Avg(ms)':<10} {'Files':<8}")
            print(f"{'─' * 100}")
            
            for proc in sorted(host_processes, key=lambda x: x.get("process_id", "")):
                pid = proc.get("process_id", "N/A")
                role = proc.get("role", "N/A")
                team = proc.get("team", "N/A")
                status = proc.get("status", "unknown")
                active = proc.get("active_requests", 0)
                queue = proc.get("queue_size", 0)
                avg_ms = proc.get("avg_processing_time_ms", 0)
                files = proc.get("data_files_loaded", 0)
                
                status_icon = "✓" if status == "online" else "✗" if status == "offline" else "⚠"
                
                print(
                    f"{pid:<4} {role:<12} {team:<6} {status_icon} {status:<8} "
                    f"{active:<8} {queue:<8} {avg_ms:<10.2f} {files:<8}"
                )
        
        print(f"\n{'─' * 100}")
        print("Press Ctrl+C to stop monitoring")
        print(f"{'─' * 100}\n")

    def get_recent_logs(self, log_dir: Path, process_id: str, lines: int = 5) -> List[str]:
        """Get recent log lines for a process."""
        # Try to find log file
        log_patterns = [
            f"*{process_id.lower()}*.log",
            f"*node_{process_id.lower()}.log",
            f"*{process_id}*.log",
        ]
        
        for pattern in log_patterns:
            log_files = list(log_dir.glob(pattern))
            if log_files:
                try:
                    with open(log_files[0], "r", encoding="utf-8", errors="ignore") as f:
                        all_lines = f.readlines()
                        return [line.strip() for line in all_lines[-lines:] if line.strip()]
                except:
                    pass
        
        return []

    def monitor_loop(self, show_logs: bool = False, log_dir: Optional[str] = None):
        """Main monitoring loop."""
        log_path = Path(log_dir) if log_dir else None
        
        try:
            while True:
                metrics = self.collect_all_metrics()
                self.display_metrics(metrics)
                
                if show_logs and log_path:
                    print("\nRecent Log Activity:")
                    print("─" * 100)
                    for process_id in sorted(metrics.keys()):
                        proc = metrics[process_id]
                        if proc.get("status") == "online":
                            logs = self.get_recent_logs(log_path, process_id, lines=2)
                            if logs:
                                print(f"{process_id}: {logs[-1][:90]}")
                    print()
                
                time.sleep(self.update_interval)
        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")

    def snapshot(self, output_file: Optional[str] = None) -> Dict:
        """Take a snapshot of current metrics."""
        metrics = self.collect_all_metrics()
        hosts = self.group_by_host(metrics)
        
        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "hosts": hosts,
            "summary": self._compute_summary(metrics),
        }
        
        if output_file:
            with open(output_file, "w") as f:
                json.dump(snapshot, f, indent=2)
            print(f"Snapshot saved to: {output_file}")
        
        return snapshot

    def _compute_summary(self, metrics: Dict) -> Dict:
        """Compute summary statistics."""
        online_count = sum(1 for m in metrics.values() if m.get("status") == "online")
        total_active = sum(m.get("active_requests", 0) for m in metrics.values())
        total_queue = sum(m.get("queue_size", 0) for m in metrics.values())
        avg_processing = sum(m.get("avg_processing_time_ms", 0) for m in metrics.values() if m.get("status") == "online")
        online_processes = [m for m in metrics.values() if m.get("status") == "online"]
        avg_processing = avg_processing / len(online_processes) if online_processes else 0
        
        return {
            "total_processes": len(metrics),
            "online_processes": online_count,
            "offline_processes": len(metrics) - online_count,
            "total_active_requests": total_active,
            "total_queue_size": total_queue,
            "avg_processing_time_ms": round(avg_processing, 2),
        }


def main():
    parser = argparse.ArgumentParser(description="Monitor two-host overlay setup.")
    parser.add_argument(
        "--config",
        default="two_hosts_config.json",
        help="Overlay configuration file.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=2.0,
        help="Update interval in seconds.",
    )
    parser.add_argument(
        "--log-dir",
        help="Directory containing log files (optional).",
    )
    parser.add_argument(
        "--show-logs",
        action="store_true",
        help="Show recent log entries.",
    )
    parser.add_argument(
        "--snapshot",
        help="Take a snapshot and save to file (exits after snapshot).",
    )

    args = parser.parse_args()

    monitor = TwoHostMonitor(args.config, args.interval)

    if args.snapshot:
        monitor.snapshot(args.snapshot)
    else:
        monitor.monitor_loop(show_logs=args.show_logs, log_dir=args.log_dir)


if __name__ == "__main__":
    main()


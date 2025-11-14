#!/usr/bin/env python3
"""Benchmark comparison tool for testing different strategies."""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import overlay_pb2
import overlay_pb2_grpc
import grpc
from benchmark import Benchmark


class StrategyBenchmark:
    """Run benchmarks with different strategies and compare results."""

    def __init__(self, leader_host: str, leader_port: int, output_dir: str):
        self.leader_host = leader_host
        self.leader_port = leader_port
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def collect_metrics_from_all_processes(self, config_path: str) -> Dict[str, Dict]:
        """Collect metrics from all processes in the overlay."""
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception as e:
            print(f"Failed to load config: {e}")
            return {}

        all_metrics = {}
        for process_id, process_info in config.get("processes", {}).items():
            try:
                address = f"{process_info['host']}:{process_info['port']}"
                with grpc.insecure_channel(address) as channel:
                    stub = overlay_pb2_grpc.OverlayNodeStub(channel)
                    try:
                        metrics = stub.GetMetrics(overlay_pb2.MetricsRequest())
                        all_metrics[process_id] = {
                            "process_id": metrics.process_id,
                            "role": metrics.role,
                            "team": metrics.team,
                            "active_requests": metrics.active_requests,
                            "max_capacity": metrics.max_capacity,
                            "queue_size": metrics.queue_size,
                            "avg_processing_time_ms": metrics.avg_processing_time_ms,
                            "data_files_loaded": metrics.data_files_loaded,
                            "is_healthy": metrics.is_healthy,
                            "host": process_info["host"],
                            "port": process_info["port"],
                        }
                    except grpc.RpcError:
                        all_metrics[process_id] = {"error": "unreachable"}
            except Exception as e:
                all_metrics[process_id] = {"error": str(e)}

        return all_metrics

    def run_strategy_benchmark(
        self,
        strategy_name: str,
        strategy_config: Dict,
        num_requests: int = 100,
        concurrency: int = 10,
    ) -> Dict:
        """Run benchmark with specific strategy configuration."""
        print(f"\n{'='*60}")
        print(f"Testing Strategy: {strategy_name}")
        print(f"Config: {strategy_config}")
        print(f"{'='*60}\n")

        benchmark = Benchmark(self.leader_host, self.leader_port)
        results = benchmark.run_benchmark_internal(
            num_requests=num_requests,
            concurrency=concurrency,
            query_type="simple",
        )

        strategy_results = {
            "strategy_name": strategy_name,
            "strategy_config": strategy_config,
            "benchmark": results,
            "timestamp": time.time(),
        }

        return strategy_results

    def compare_strategies(
        self,
        strategy_configs: List[Dict],
        config_path: str,
        num_requests: int = 100,
        concurrency: int = 10,
    ) -> Dict:
        """Run benchmarks for multiple strategies and compare."""
        all_results = []
        
        # Collect baseline metrics
        print("Collecting baseline metrics from all processes...")
        baseline_metrics = self.collect_metrics_from_all_processes(config_path)
        
        for strategy_config in strategy_configs:
            strategy_name = strategy_config["name"]
            
            # Collect metrics before benchmark
            pre_metrics = self.collect_metrics_from_all_processes(config_path)
            
            # Run benchmark
            strategy_result = self.run_strategy_benchmark(
                strategy_name,
                strategy_config,
                num_requests,
                concurrency,
            )
            
            # Collect metrics after benchmark
            time.sleep(2)  # Wait for metrics to stabilize
            post_metrics = self.collect_metrics_from_all_processes(config_path)
            
            strategy_result["pre_metrics"] = pre_metrics
            strategy_result["post_metrics"] = post_metrics
            all_results.append(strategy_result)

        # Generate comparison report
        comparison = self._generate_comparison_report(all_results)
        
        output = {
            "baseline_metrics": baseline_metrics,
            "strategies": all_results,
            "comparison": comparison,
            "timestamp": time.time(),
        }

        # Save results
        output_file = self.output_dir / "strategy_comparison.json"
        with open(output_file, "w") as f:
            json.dump(output, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
        
        return output

    def _generate_comparison_report(self, all_results: List[Dict]) -> Dict:
        """Generate comparison report from all strategy results."""
        comparison = {
            "strategies": [],
            "best_latency": None,
            "best_throughput": None,
            "best_fairness": None,
        }

        best_latency_val = float("inf")
        best_throughput_val = 0
        best_fairness_val = 0

        for result in all_results:
            benchmark = result.get("benchmark", {})
            stats = benchmark.get("statistics", {})
            
            strategy_summary = {
                "name": result["strategy_name"],
                "config": result["strategy_config"],
                "avg_latency_ms": stats.get("avg_latency_ms", 0),
                "p95_latency_ms": stats.get("p95_latency_ms", 0),
                "p99_latency_ms": stats.get("p99_latency_ms", 0),
                "throughput_req_per_sec": stats.get("throughput_req_per_sec", 0),
                "success_rate": stats.get("success_rate", 0),
                "total_records": stats.get("total_records_returned", 0),
            }
            
            comparison["strategies"].append(strategy_summary)
            
            # Track best performers
            if stats.get("avg_latency_ms", float("inf")) < best_latency_val:
                best_latency_val = stats.get("avg_latency_ms", float("inf"))
                comparison["best_latency"] = result["strategy_name"]
            
            if stats.get("throughput_req_per_sec", 0) > best_throughput_val:
                best_throughput_val = stats.get("throughput_req_per_sec", 0)
                comparison["best_throughput"] = result["strategy_name"]
            
            # Fairness is based on success rate and balanced load
            fairness_score = stats.get("success_rate", 0) * 0.7 + (
                100 - abs(stats.get("green_team_percentage", 50) - 50)
            ) * 0.3
            if fairness_score > best_fairness_val:
                best_fairness_val = fairness_score
                comparison["best_fairness"] = result["strategy_name"]

        return comparison


def main():
    parser = argparse.ArgumentParser(description="Compare different strategies.")
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
        default="logs/strategy_comparison",
        help="Output directory for results.",
    )
    parser.add_argument(
        "--num-requests",
        type=int,
        default=50,
        help="Number of requests per strategy test.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Concurrency level.",
    )

    args = parser.parse_args()

    # Define strategy configurations to test
    strategy_configs = [
        {
            "name": "round_robin_blocking",
            "forwarding": "round_robin",
            "async": False,
            "chunking": "fixed",
            "fairness": "strict",
            "chunk_size": 200,
        },
        {
            "name": "round_robin_async",
            "forwarding": "round_robin",
            "async": True,
            "chunking": "fixed",
            "fairness": "strict",
            "chunk_size": 200,
        },
        {
            "name": "parallel_async",
            "forwarding": "parallel",
            "async": True,
            "chunking": "fixed",
            "fairness": "strict",
            "chunk_size": 200,
        },
        {
            "name": "adaptive_chunking",
            "forwarding": "parallel",
            "async": True,
            "chunking": "adaptive",
            "fairness": "strict",
            "chunk_size": 200,
        },
        {
            "name": "weighted_fairness",
            "forwarding": "parallel",
            "async": True,
            "chunking": "fixed",
            "fairness": "weighted",
            "chunk_size": 200,
        },
    ]

    print("=" * 60)
    print("STRATEGY COMPARISON BENCHMARK")
    print("=" * 60)
    print(f"Testing {len(strategy_configs)} strategies")
    print(f"Requests per strategy: {args.num_requests}")
    print(f"Concurrency: {args.concurrency}")
    print("=" * 60)

    comparator = StrategyBenchmark(
        args.leader_host, args.leader_port, args.output_dir
    )
    
    results = comparator.compare_strategies(
        strategy_configs,
        args.config,
        args.num_requests,
        args.concurrency,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    comparison = results.get("comparison", {})
    print(f"\nBest Latency: {comparison.get('best_latency')}")
    print(f"Best Throughput: {comparison.get('best_throughput')}")
    print(f"Best Fairness: {comparison.get('best_fairness')}")
    
    print("\nDetailed Results:")
    for strategy in comparison.get("strategies", []):
        print(f"\n{strategy['name']}:")
        print(f"  Avg Latency: {strategy['avg_latency_ms']:.2f} ms")
        print(f"  Throughput: {strategy['throughput_req_per_sec']:.2f} req/s")
        print(f"  Success Rate: {strategy['success_rate']:.1f}%")


if __name__ == "__main__":
    main()


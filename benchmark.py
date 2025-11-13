#!/usr/bin/env python3
"""
Benchmark script comparing one host vs two hosts performance
Measures: latency, throughput, queue pressure, fairness
"""

import grpc
import json
import time
import threading
import statistics
import sys
import os
from collections import defaultdict

sys.path.append(os.path.dirname(__file__))

import overlay_pb2
import overlay_pb2_grpc

class Benchmark:
    def __init__(self, leader_host, leader_port):
        self.leader_address = f"{leader_host}:{leader_port}"
        self.results = {
            'latencies': [],
            'throughput': [],
            'queue_sizes': [],
            'processing_times': [],
            'errors': 0,
            'total_requests': 0
        }
    
    def get_metrics(self):
        """Get current metrics from leader"""
        try:
            channel = grpc.insecure_channel(self.leader_address)
            stub = overlay_pb2_grpc.OverlayNodeStub(channel)
            metrics = stub.GetMetrics(overlay_pb2.MetricsRequest())
            channel.close()
            return {
                'queue_size': metrics.queue_size,
                'avg_processing_time': metrics.avg_processing_time_ms,
                'active_requests': metrics.active_requests,
                'role': metrics.role,
                'team': metrics.team
            }
        except Exception as e:
            print(f"Error getting metrics: {e}")
            return None
    
    def send_query_request(self, query_params):
        """Send a query request"""
        try:
            channel = grpc.insecure_channel(self.leader_address)
            stub = overlay_pb2_grpc.OverlayNodeStub(channel)
            
            payload = json.dumps({
                'type': 'query',
                'query': query_params
            })
            
            req = overlay_pb2.Request(payload=payload, hops=[])
            
            start_time = time.time()
            resp = stub.Forward(req)
            end_time = time.time()
            
            latency = (end_time - start_time) * 1000  # ms
            
            channel.close()
            
            return {
                'success': True,
                'latency': latency,
                'response': resp.result,
                'hops': len(resp.hops)
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'latency': 0
            }
    
    def run_benchmark(self, num_requests=100, concurrency=10, query_type='simple'):
        """Run benchmark with specified parameters"""
        print(f"\n{'='*60}")
        print(f"BENCHMARK: {num_requests} requests, concurrency={concurrency}")
        print(f"{'='*60}\n")
        
        # Baseline metrics
        baseline_metrics = self.get_metrics()
        if baseline_metrics:
            print(f"Baseline Queue Size: {baseline_metrics['queue_size']}")
        
        results = []
        lock = threading.Lock()
        errors = 0
        
        def worker(worker_id, num_requests_per_worker):
            local_results = []
            query_params = {
                'parameter': 'PM2.5',
                'min_value': 10.0,
                'max_value': 50.0,
                'limit': 100
            }
            
            for i in range(num_requests_per_worker):
                result = self.send_query_request(query_params)
                local_results.append(result)
                if not result['success']:
                    with lock:
                        errors += 1
                time.sleep(0.01)  # Small delay between requests
            
            with lock:
                results.extend(local_results)
        
        # Start workers
        workers = []
        requests_per_worker = num_requests // concurrency
        
        start_time = time.time()
        
        for i in range(concurrency):
            w = threading.Thread(target=worker, args=(i, requests_per_worker))
            w.start()
            workers.append(w)
        
        # Monitor queue during execution
        queue_samples = []
        for _ in range(10):
            time.sleep((num_requests * 0.01) / 10)
            metrics = self.get_metrics()
            if metrics:
                queue_samples.append(metrics['queue_size'])
        
        # Wait for completion
        for w in workers:
            w.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Collect metrics
        latencies = [r['latency'] for r in results if r['success']]
        hops_counts = [r['hops'] for r in results if r['success']]
        
        # Final metrics
        final_metrics = self.get_metrics()
        
        # Calculate statistics
        stats = {
            'total_requests': num_requests,
            'successful_requests': len([r for r in results if r['success']]),
            'failed_requests': errors,
            'total_time_seconds': total_time,
            'throughput_rps': num_requests / total_time if total_time > 0 else 0,
            'avg_latency_ms': statistics.mean(latencies) if latencies else 0,
            'median_latency_ms': statistics.median(latencies) if latencies else 0,
            'p95_latency_ms': statistics.quantiles(latencies, n=20)[18] if len(latencies) > 20 else (max(latencies) if latencies else 0),
            'p99_latency_ms': statistics.quantiles(latencies, n=100)[98] if len(latencies) > 100 else (max(latencies) if latencies else 0),
            'min_latency_ms': min(latencies) if latencies else 0,
            'max_latency_ms': max(latencies) if latencies else 0,
            'avg_hops': statistics.mean(hops_counts) if hops_counts else 0,
            'max_queue_size': max(queue_samples) if queue_samples else 0,
            'avg_queue_size': statistics.mean(queue_samples) if queue_samples else 0,
            'final_queue_size': final_metrics['queue_size'] if final_metrics else 0,
            'avg_processing_time_ms': final_metrics['avg_processing_time_ms'] if final_metrics else 0
        }
        
        return stats
    
    def print_results(self, stats_one_host, stats_two_hosts):
        """Print comparison results"""
        print(f"\n{'='*60}")
        print("BENCHMARK RESULTS: ONE HOST vs TWO HOSTS")
        print(f"{'='*60}\n")
        
        print(f"{'Metric':<30} {'One Host':<15} {'Two Hosts':<15} {'Improvement':<15}")
        print("-" * 75)
        
        metrics_to_compare = [
            ('Throughput (req/s)', 'throughput_rps', 'higher'),
            ('Avg Latency (ms)', 'avg_latency_ms', 'lower'),
            ('P95 Latency (ms)', 'p95_latency_ms', 'lower'),
            ('Max Queue Size', 'max_queue_size', 'lower'),
            ('Avg Processing Time (ms)', 'avg_processing_time_ms', 'lower'),
            ('Success Rate (%)', lambda s: (s['successful_requests']/s['total_requests']*100) if s['total_requests'] > 0 else 0, 'higher')
        ]
        
        for metric_name, metric_key, direction in metrics_to_compare:
            if callable(metric_key):
                val1 = metric_key(stats_one_host)
                val2 = metric_key(stats_two_hosts)
            else:
                val1 = stats_one_host.get(metric_key, 0)
                val2 = stats_two_hosts.get(metric_key, 0)
            
            if direction == 'higher':
                improvement = ((val2 - val1) / val1 * 100) if val1 > 0 else 0
                symbol = "↑" if improvement > 0 else "↓"
            else:
                improvement = ((val1 - val2) / val1 * 100) if val1 > 0 else 0
                symbol = "↓" if improvement > 0 else "↑"
            
            print(f"{metric_name:<30} {val1:<15.2f} {val2:<15.2f} {improvement:>6.1f}% {symbol}")
        
        print("\n" + "="*60)
        print("DISCOVERIES:")
        print("="*60)
        
        discoveries = []
        
        # Discovery 1: Network overhead vs parallelism
        latency_diff = stats_one_host['avg_latency_ms'] - stats_two_hosts['avg_latency_ms']
        if latency_diff > 0:
            discoveries.append(
                f"1. NETWORK OVERHEAD: Two-host setup adds {latency_diff:.2f}ms average latency "
                f"due to network communication, but enables parallel processing across hosts."
            )
        else:
            discoveries.append(
                f"1. PARALLELISM BENEFIT: Two-host setup reduces latency by {abs(latency_diff):.2f}ms "
                f"through distributed processing, outweighing network overhead."
            )
        
        # Discovery 2: Queue pressure management
        queue_diff = stats_one_host['max_queue_size'] - stats_two_hosts['max_queue_size']
        if queue_diff > 0:
            discoveries.append(
                f"2. QUEUE PRESSURE: Two-host setup reduces max queue size by {queue_diff} requests "
                f"({(queue_diff/stats_one_host['max_queue_size']*100) if stats_one_host['max_queue_size'] > 0 else 0:.1f}%), "
                f"demonstrating better load distribution."
            )
        else:
            discoveries.append(
                f"2. LOAD DISTRIBUTION: Queue pressure similar, but two-host setup distributes "
                f"load across network, preventing single-host bottlenecks."
            )
        
        # Discovery 3: Throughput scalability
        throughput_ratio = stats_two_hosts['throughput_rps'] / stats_one_host['throughput_rps'] if stats_one_host['throughput_rps'] > 0 else 0
        if throughput_ratio > 1.2:
            discoveries.append(
                f"3. SCALABILITY: Two-host setup achieves {throughput_ratio:.2f}x throughput, "
                f"demonstrating near-linear scaling with distributed architecture."
            )
        elif throughput_ratio < 0.8:
            discoveries.append(
                f"3. NETWORK BOTTLENECK: Two-host setup shows {((1-throughput_ratio)*100):.1f}% "
                f"throughput reduction, indicating network communication overhead dominates."
            )
        else:
            discoveries.append(
                f"3. BALANCED PERFORMANCE: Two-host setup maintains similar throughput "
                f"({throughput_ratio:.2f}x) while enabling fault tolerance and geographic distribution."
            )
        
        for discovery in discoveries:
            print(f"  {discovery}")
        
        print("\n" + "="*60)

def main():
    if len(sys.argv) < 5:
        print("Usage: python benchmark.py <leader_host> <leader_port> <num_requests> <concurrency>")
        print("Example: python benchmark.py 192.168.1.2 50051 100 10")
        sys.exit(1)
    
    leader_host = sys.argv[1]
    leader_port = int(sys.argv[2])
    num_requests = int(sys.argv[3])
    concurrency = int(sys.argv[4])
    
    benchmark = Benchmark(leader_host, leader_port)
    
    print("Running benchmark...")
    print("Note: Run this script twice - once with one-host config, once with two-host config")
    print("Then compare the results manually or modify script to run both automatically\n")
    
    stats = benchmark.run_benchmark(num_requests, concurrency)
    
    print("\n" + "="*60)
    print("BENCHMARK STATISTICS")
    print("="*60)
    print(f"Total Requests: {stats['total_requests']}")
    print(f"Successful: {stats['successful_requests']}")
    print(f"Failed: {stats['failed_requests']}")
    print(f"Throughput: {stats['throughput_rps']:.2f} requests/second")
    print(f"Average Latency: {stats['avg_latency_ms']:.2f} ms")
    print(f"Median Latency: {stats['median_latency_ms']:.2f} ms")
    print(f"P95 Latency: {stats['p95_latency_ms']:.2f} ms")
    print(f"P99 Latency: {stats['p99_latency_ms']:.2f} ms")
    print(f"Average Hops: {stats['avg_hops']:.2f}")
    print(f"Max Queue Size: {stats['max_queue_size']}")
    print(f"Average Queue Size: {stats['avg_queue_size']:.2f}")
    print(f"Average Processing Time: {stats['avg_processing_time_ms']:.2f} ms")
    
    # Save results to file
    with open('benchmark_results.json', 'w') as f:
        json.dump(stats, f, indent=2)
    
    print(f"\nResults saved to benchmark_results.json")

if __name__ == "__main__":
    main()
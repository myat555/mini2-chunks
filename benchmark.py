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
                'avg_processing_time_ms': metrics.avg_processing_time_ms,
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

            req = overlay_pb2.QueryRequest(
                query_type='filter',
                query_params=json.dumps(query_params),
                hops=[],
                client_id='benchmark'
            )

            start_time = time.time()
            resp = stub.Query(req)
            latency = (time.time() - start_time) * 1000

            if resp.status != 'ready':
                channel.close()
                return {
                    'success': False,
                    'error': resp.status,
                    'latency': latency,
                    'hops': len(resp.hops)
                }

            chunk = stub.GetChunk(overlay_pb2.ChunkRequest(uid=resp.uid, chunk_index=0))
            channel.close()

            if chunk.status != 'success':
                return {
                    'success': False,
                    'error': f"chunk:{chunk.status}",
                    'latency': latency,
                    'hops': len(resp.hops)
                }

            rows = json.loads(chunk.data) if chunk.data else []
            
            # Verify we got actual data records
            sample_record = None
            if rows:
                sample_record = rows[0]
                # Validate record structure
                if not isinstance(sample_record, dict) or 'parameter' not in sample_record:
                    print(f"Warning: Unexpected record format: {sample_record}")
            
            return {
                'success': True,
                'latency': latency,
                'records': len(rows),
                'hops': len(resp.hops),
                'sample_parameter': sample_record.get('parameter') if sample_record else None,
                'sample_value': sample_record.get('value') if sample_record else None
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'latency': 0
            }
    
    def run_benchmark_internal(self, num_requests=100, concurrency=10, query_type='simple'):
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
            nonlocal errors
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
        record_counts = [r.get('records', 0) for r in results if r['success']]
        
        # Show data verification info
        successful_results = [r for r in results if r['success']]
        if successful_results:
            first_success = successful_results[0]
            print(f"\nData Verification:")
            print(f"  Records returned: {first_success.get('records', 0)}")
            if first_success.get('sample_parameter'):
                print(f"  Sample parameter: {first_success.get('sample_parameter')}")
                print(f"  Sample value: {first_success.get('sample_value')}")
            print(f"  Average records per query: {sum(record_counts) / len(record_counts):.1f}" if record_counts else "  No records returned")
        
        # Final metrics
        final_metrics = self.get_metrics()
        
        # Calculate statistics
        total_records = sum(record_counts) if record_counts else 0
        avg_records_per_query = statistics.mean(record_counts) if record_counts else 0
        max_records = max(record_counts) if record_counts else 0
        min_records = min(record_counts) if record_counts else 0
        
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
            'avg_processing_time_ms': final_metrics['avg_processing_time_ms'] if final_metrics else 0,
            'total_records_returned': total_records,
            'avg_records_per_query': avg_records_per_query,
            'max_records_per_query': max_records,
            'min_records_per_query': min_records
        }
        
        return stats
    
    def run_benchmark(self, num_requests: int, concurrency: int, output_dir: str = "."):
        """Run benchmark and return stats."""
        stats = self.run_benchmark_internal(num_requests, concurrency)
        
        # Save results to output directory
        import os
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'benchmark_results.json')
        
        with open(output_file, 'w') as f:
            json.dump(stats, f, indent=2)
        
        print(f"\nResults saved to {output_file}")
        
        return stats

def main():
    if len(sys.argv) < 5:
        print("Usage: python benchmark.py <leader_host> <leader_port> <num_requests> <concurrency> [output_dir]")
        print("Example: python benchmark.py 192.168.1.2 60051 100 10 logs")
        sys.exit(1)
    
    leader_host = sys.argv[1]
    leader_port = int(sys.argv[2])
    num_requests = int(sys.argv[3])
    concurrency = int(sys.argv[4])
    output_dir = sys.argv[5] if len(sys.argv) > 5 else "."
    
    benchmark = Benchmark(leader_host, leader_port)
    
    print("Running benchmark...")
    print("Tip: use run_benchmark_comparison.py or scripts/benchmark_windows.bat to automate single-host vs two-host comparisons.\n")
    
    stats = benchmark.run_benchmark(num_requests, concurrency, output_dir)
    
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
    print(f"\nData Processing:")
    print(f"Total Records Returned: {stats['total_records_returned']}")
    print(f"Average Records per Query: {stats['avg_records_per_query']:.1f}")
    print(f"Max Records per Query: {stats['max_records_per_query']}")
    print(f"Min Records per Query: {stats['min_records_per_query']}")

if __name__ == "__main__":
    main()
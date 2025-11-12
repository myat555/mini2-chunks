#!/usr/bin/env python3
"""
Load testing client - simulates multiple requests and collects performance metrics
"""

import grpc
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import overlay_pb2
import overlay_pb2_grpc
import sys
import json

class LoadTestClient:
    def __init__(self, server_address, num_requests=100, concurrent=True):
        self.server_address = server_address
        self.num_requests = num_requests
        self.concurrent = concurrent
        self.results = []
        self.lock = threading.Lock()
    
    def send_single_request(self, request_id):
        """Send one request and measure time"""
        start_time = time.time()
        
        try:
            channel = grpc.insecure_channel(self.server_address)
            stub = overlay_pb2_grpc.OverlayNodeStub(channel)
            
            # Create request
            request = overlay_pb2.Request(
                payload=f"test-request-{request_id}",
                hops=[]
            )
            
            # Send request
            response = stub.Forward(request)
            
            end_time = time.time()
            latency = (end_time - start_time) * 1000  # Convert to milliseconds
            
            result = {
                'request_id': request_id,
                'success': True,
                'latency_ms': latency,
                'timestamp': start_time,
                'error': None,
                'result': response.result
            }
            
            channel.close()
            
        except Exception as e:
            end_time = time.time()
            latency = (end_time - start_time) * 1000
            
            result = {
                'request_id': request_id,
                'success': False,
                'latency_ms': latency,
                'timestamp': start_time,
                'error': str(e),
                'result': None
            }
        
        with self.lock:
            self.results.append(result)
        
        return result
    
    def run_concurrent_test(self):
        """Send all requests concurrently"""
        print(f"Sending {self.num_requests} concurrent requests to {self.server_address}...")
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.num_requests) as executor:
            futures = [executor.submit(self.send_single_request, i) 
                      for i in range(self.num_requests)]
            
            # Wait for all to complete
            completed = 0
            for future in as_completed(futures):
                future.result()
                completed += 1
                if completed % 10 == 0:
                    print(f"  Completed: {completed}/{self.num_requests}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        return self.calculate_metrics(total_time)
    
    def run_sequential_test(self):
        """Send requests one after another"""
        print(f"Sending {self.num_requests} sequential requests to {self.server_address}...")
        start_time = time.time()
        
        for i in range(self.num_requests):
            self.send_single_request(i)
            if (i + 1) % 10 == 0:
                print(f"  Completed: {i + 1}/{self.num_requests}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        return self.calculate_metrics(total_time)
    
    def calculate_metrics(self, total_time):
        """Calculate performance metrics"""
        successful = [r for r in self.results if r['success']]
        failed = [r for r in self.results if not r['success']]
        
        latencies = [r['latency_ms'] for r in successful]
        
        metrics = {
            'total_requests': self.num_requests,
            'successful_requests': len(successful),
            'failed_requests': len(failed),
            'success_rate': (len(successful) / self.num_requests) * 100 if self.num_requests > 0 else 0,
            'total_time_seconds': total_time,
            'throughput_rps': self.num_requests / total_time if total_time > 0 else 0,
            'avg_latency_ms': statistics.mean(latencies) if latencies else 0,
            'min_latency_ms': min(latencies) if latencies else 0,
            'max_latency_ms': max(latencies) if latencies else 0,
            'median_latency_ms': statistics.median(latencies) if latencies else 0,
            'p95_latency_ms': self.percentile(latencies, 95) if latencies else 0,
            'p99_latency_ms': self.percentile(latencies, 99) if latencies else 0,
            'errors': [r['error'] for r in failed if r['error']]
        }
        
        return metrics
    
    def percentile(self, data, percentile):
        """Calculate percentile"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def print_report(self, metrics):
        """Print performance report"""
        print("\n" + "="*60)
        print("PERFORMANCE TEST REPORT")
        print("="*60)
        print(f"Total Requests: {metrics['total_requests']}")
        print(f"Successful: {metrics['successful_requests']}")
        print(f"Failed: {metrics['failed_requests']}")
        print(f"Success Rate: {metrics['success_rate']:.2f}%")
        print(f"\nTiming:")
        print(f"  Total Time: {metrics['total_time_seconds']:.2f} seconds")
        print(f"  Throughput: {metrics['throughput_rps']:.2f} requests/second")
        print(f"\nLatency (milliseconds):")
        print(f"  Average: {metrics['avg_latency_ms']:.2f} ms")
        print(f"  Median: {metrics['median_latency_ms']:.2f} ms")
        print(f"  Min: {metrics['min_latency_ms']:.2f} ms")
        print(f"  Max: {metrics['max_latency_ms']:.2f} ms")
        print(f"  95th Percentile: {metrics['p95_latency_ms']:.2f} ms")
        print(f"  99th Percentile: {metrics['p99_latency_ms']:.2f} ms")
        
        if metrics['errors']:
            print(f"\nErrors ({len(metrics['errors'])}):")
            error_counts = {}
            for error in metrics['errors']:
                error_counts[error] = error_counts.get(error, 0) + 1
            for error, count in error_counts.items():
                print(f"  {error}: {count}")
        
        print("="*60 + "\n")

def main():
    if len(sys.argv) < 2:
        print("Usage: python load_test_client.py <server_address> [num_requests] [concurrent|sequential]")
        print("Example: python load_test_client.py localhost:50051 100 concurrent")
        sys.exit(1)
    
    server_address = sys.argv[1]
    num_requests = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    concurrent = sys.argv[3].lower() == 'concurrent' if len(sys.argv) > 3 else True
    
    print("="*60)
    print("LOAD TEST CLIENT")
    print("="*60)
    print(f"Server: {server_address}")
    print(f"Requests: {num_requests}")
    print(f"Mode: {'Concurrent' if concurrent else 'Sequential'}")
    print("="*60)
    
    client = LoadTestClient(server_address, num_requests, concurrent)
    
    if concurrent:
        metrics = client.run_concurrent_test()
    else:
        metrics = client.run_sequential_test()
    
    client.print_report(metrics)
    
    # Save to file
    with open('performance_results.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    print("Results saved to performance_results.json")

if __name__ == '__main__':
    main()


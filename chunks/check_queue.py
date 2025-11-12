#!/usr/bin/env python3
"""
Queue Status Checker - Check queue status via GetMetrics RPC
"""

import grpc
import overlay_pb2
import overlay_pb2_grpc
import sys

def check_queue(server_address):
    """Check queue status for a process"""
    channel = grpc.insecure_channel(server_address)
    stub = overlay_pb2_grpc.OverlayNodeStub(channel)
    
    try:
        metrics = stub.GetMetrics(overlay_pb2.MetricsRequest())
        
        print(f"\n{'='*50}")
        print(f"Queue Status for {metrics.process_id}")
        print(f"{'='*50}")
        print(f"Role:              {metrics.role}")
        print(f"Team:              {metrics.team}")
        print(f"Queue Size:        {metrics.queue_size}")
        print(f"Active Requests:   {metrics.active_requests}")
        print(f"Max Capacity:      {metrics.max_capacity}")
        print(f"Is Healthy:        {metrics.is_healthy}")
        print(f"Avg Processing:    {metrics.avg_processing_time_ms:.2f} ms")
        print(f"{'='*50}\n")
        
    except grpc.RpcError as e:
        print(f"Error connecting to {server_address}: {e.code()} - {e.details()}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        channel.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_queue.py <server_address>")
        print("Example: python check_queue.py localhost:50051")
        print("\nCheck queue status for all processes:")
        print("  python check_queue.py localhost:50051  # Leader (A)")
        print("  python check_queue.py localhost:50052  # Team Leader (B)")
        print("  python check_queue.py localhost:50053  # Worker (C)")
        sys.exit(1)
    
    server_address = sys.argv[1]
    check_queue(server_address)


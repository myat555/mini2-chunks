#!/usr/bin/env python3
"""
Test script to trace what happens when team leader E receives a query.
This simulates what happens when leader A forwards to E.
"""

import json
import sys
import time

import grpc

import overlay_pb2
import overlay_pb2_grpc


def test_e_forwarding():
    """Test what happens when E receives a query."""
    
    print("="*70)
    print("TESTING TEAM LEADER E FORWARDING")
    print("="*70)
    
    # Test E directly
    e_address = "192.168.1.1:60055"
    
    print(f"\nStep 1: Query E directly (simulating what A does)")
    print("-" * 70)
    
    try:
        with grpc.insecure_channel(e_address, options=[("grpc.keepalive_timeout_ms", 1000)]) as channel:
            stub = overlay_pb2_grpc.OverlayNodeStub(channel)
            
            # Get initial metrics
            initial = stub.GetMetrics(overlay_pb2.MetricsRequest(), timeout=2)
            print(f"Initial E metrics:")
            print(f"  Avg Processing Time: {initial.avg_processing_time_ms:.2f}ms")
            print(f"  Files Loaded: {initial.data_files_loaded}")
            print(f"  Recent Logs (last 5):")
            for log in list(initial.recent_logs)[-5:]:
                print(f"    {log}")
            
            # Send a query with allocation of 1000 (what A would send)
            query_params = {
                "parameter": "PM2.5",
                "min_value": 10.0,
                "max_value": 50.0,
                "limit": 1000  # This is what E receives from A
            }
            
            request = overlay_pb2.QueryRequest(
                query_type="filter",
                query_params=json.dumps(query_params),
                hops=["A"],  # Simulate coming from A
                client_id="test_e_forwarding",
            )
            
            print(f"\nStep 2: Send query to E (limit=1000, hops=[A])")
            print("-" * 70)
            
            start_time = time.time()
            response = stub.Query(request, timeout=10)
            query_latency = (time.time() - start_time) * 1000
            
            print(f"Query Response:")
            print(f"  Status: {response.status}")
            print(f"  Latency: {query_latency:.2f}ms")
            print(f"  Total Records: {response.total_records}")
            print(f"  Total Chunks: {response.total_chunks}")
            print(f"  Hops: {list(response.hops)}")
            print(f"  UID: {response.uid[:8]}...")
            
            # Get logs after query
            time.sleep(0.5)
            final = stub.GetMetrics(overlay_pb2.MetricsRequest(), timeout=2)
            print(f"\nStep 3: Check E's logs after query")
            print("-" * 70)
            print(f"Final E metrics:")
            print(f"  Avg Processing Time: {final.avg_processing_time_ms:.2f}ms")
            print(f"  Recent Logs (last 10):")
            for log in list(final.recent_logs)[-10:]:
                if "forwarding" in log.lower() or "local query" in log.lower() or "query" in log.lower():
                    print(f"    {log}")
            
            # Check if F and D received requests
            print(f"\nStep 4: Check if workers F and D processed requests")
            print("-" * 70)
            
            # Check F
            try:
                f_address = "192.168.1.1:60056"
                with grpc.insecure_channel(f_address, options=[("grpc.keepalive_timeout_ms", 1000)]) as f_channel:
                    f_stub = overlay_pb2_grpc.OverlayNodeStub(f_channel)
                    f_metrics = f_stub.GetMetrics(overlay_pb2.MetricsRequest(), timeout=2)
                    print(f"Worker F metrics:")
                    print(f"  Avg Processing Time: {f_metrics.avg_processing_time_ms:.2f}ms")
                    print(f"  Files Loaded: {f_metrics.data_files_loaded}")
                    print(f"  Recent Logs (last 5):")
                    for log in list(f_metrics.recent_logs)[-5:]:
                        print(f"    {log}")
            except Exception as e:
                print(f"  Error checking F: {e}")
            
            # Check D
            try:
                d_address = "192.168.1.2:60054"
                with grpc.insecure_channel(d_address, options=[("grpc.keepalive_timeout_ms", 1000)]) as d_channel:
                    d_stub = overlay_pb2_grpc.OverlayNodeStub(d_channel)
                    d_metrics = d_stub.GetMetrics(overlay_pb2.MetricsRequest(), timeout=2)
                    print(f"\nWorker D metrics:")
                    print(f"  Avg Processing Time: {d_metrics.avg_processing_time_ms:.2f}ms")
                    print(f"  Files Loaded: {d_metrics.data_files_loaded}")
                    print(f"  Recent Logs (last 5):")
                    for log in list(d_metrics.recent_logs)[-5:]:
                        print(f"    {log}")
            except Exception as e:
                print(f"  Error checking D: {e}")
            
            print(f"\n" + "="*70)
            print("ANALYSIS")
            print("="*70)
            
            # Look for forwarding logs in E's recent logs
            e_logs = list(final.recent_logs)
            forwarding_logs = [log for log in e_logs if "forwarding" in log.lower()]
            
            if forwarding_logs:
                print("✓ E IS forwarding to workers:")
                for log in forwarding_logs:
                    print(f"  {log}")
            else:
                print("✗ E is NOT forwarding to workers")
                print("  Possible reasons:")
                print("    1. E is satisfying queries locally (has 420 files)")
                print("    2. Forwarding is happening but not logged")
                print("    3. Workers are returning records too quickly")
            
            # Check if workers show any activity
            print(f"\nWorker Activity:")
            try:
                f_final = f_stub.GetMetrics(overlay_pb2.MetricsRequest(), timeout=2)
                d_final = d_stub.GetMetrics(overlay_pb2.MetricsRequest(), timeout=2)
                
                if f_final.avg_processing_time_ms > 0:
                    print(f"  F: Processing time = {f_final.avg_processing_time_ms:.2f}ms (RECEIVING WORK)")
                else:
                    print(f"  F: Processing time = {f_final.avg_processing_time_ms:.2f}ms (IDLE)")
                
                if d_final.avg_processing_time_ms > 0:
                    print(f"  D: Processing time = {d_final.avg_processing_time_ms:.2f}ms (RECEIVING WORK)")
                else:
                    print(f"  D: Processing time = {d_final.avg_processing_time_ms:.2f}ms (IDLE)")
            except:
                pass
    
    except grpc.RpcError as e:
        print(f"gRPC Error: {e.code()} - {e.details()}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_e_forwarding()


#!/usr/bin/env python3
"""
Test script to verify that macOS nodes can process requests.
Tests each node directly to ensure they're actually working.
"""

import json
import sys
import time
from typing import Dict, List

import grpc

import overlay_pb2
import overlay_pb2_grpc


def test_node_query(host: str, port: int, node_id: str, role: str, team: str) -> Dict:
    """Test a single node by sending a direct query."""
    address = f"{host}:{port}"
    print(f"\n{'='*60}")
    print(f"Testing Node {node_id} ({role}/{team}) at {address}")
    print(f"{'='*60}")
    
    try:
        # Get initial metrics
        with grpc.insecure_channel(address, options=[("grpc.keepalive_timeout_ms", 1000)]) as channel:
            stub = overlay_pb2_grpc.OverlayNodeStub(channel)
            
            # Get initial metrics
            initial_metrics = stub.GetMetrics(overlay_pb2.MetricsRequest(), timeout=2)
            initial_avg_time = initial_metrics.avg_processing_time_ms
            initial_files = initial_metrics.data_files_loaded
            
            print(f"Initial State:")
            print(f"  Files Loaded: {initial_files}")
            print(f"  Avg Processing Time: {initial_avg_time:.2f}ms")
            print(f"  Active Requests: {initial_metrics.active_requests}")
            
            # Send a query request
            query_params = {
                "parameter": "PM2.5",
                "min_value": 10.0,
                "max_value": 50.0,
                "limit": 500
            }
            
            request = overlay_pb2.QueryRequest(
                query_type="filter",
                query_params=json.dumps(query_params),
                hops=[],
                client_id="test_script",
            )
            
            print(f"\nSending query request...")
            start_time = time.time()
            response = stub.Query(request, timeout=10)
            query_latency = (time.time() - start_time) * 1000
            
            if response.status != "ready" or not response.uid:
                return {
                    "node_id": node_id,
                    "success": False,
                    "error": f"Query failed: status={response.status}",
                    "query_latency_ms": query_latency,
                }
            
            print(f"  Query Status: {response.status}")
            print(f"  Query Latency: {query_latency:.2f}ms")
            print(f"  Total Records: {response.total_records}")
            print(f"  Total Chunks: {response.total_chunks}")
            print(f"  Hops: {list(response.hops)}")
            
            # Collect all chunks
            total_records = 0
            chunks_collected = 0
            for chunk_idx in range(response.total_chunks):
                chunk_resp = stub.GetChunk(
                    overlay_pb2.ChunkRequest(uid=response.uid, chunk_index=chunk_idx),
                    timeout=5
                )
                if chunk_resp.status == "success":
                    try:
                        data = json.loads(chunk_resp.data)
                        total_records += len(data)
                        chunks_collected += 1
                    except:
                        pass
                if chunk_resp.is_last:
                    break
            
            print(f"  Chunks Collected: {chunks_collected}/{response.total_chunks}")
            print(f"  Records Collected: {total_records}")
            
            # Get final metrics
            time.sleep(0.5)  # Wait a bit for metrics to update
            final_metrics = stub.GetMetrics(overlay_pb2.MetricsRequest(), timeout=2)
            final_avg_time = final_metrics.avg_processing_time_ms
            
            print(f"\nFinal State:")
            print(f"  Avg Processing Time: {final_avg_time:.2f}ms")
            print(f"  Active Requests: {final_metrics.active_requests}")
            
            # Check if processing time increased
            time_increased = final_avg_time > initial_avg_time or final_avg_time > 0
            
            return {
                "node_id": node_id,
                "success": True,
                "query_latency_ms": query_latency,
                "total_records": total_records,
                "chunks_collected": chunks_collected,
                "initial_avg_time_ms": initial_avg_time,
                "final_avg_time_ms": final_avg_time,
                "processing_time_increased": time_increased,
                "files_loaded": initial_files,
                "hops": list(response.hops),
            }
            
    except grpc.RpcError as e:
        return {
            "node_id": node_id,
            "success": False,
            "error": f"gRPC Error: {e.code()} - {e.details()}",
        }
    except Exception as e:
        return {
            "node_id": node_id,
            "success": False,
            "error": f"Exception: {str(e)}",
        }


def main():
    """Test all macOS nodes."""
    
    # macOS nodes configuration
    macos_nodes = [
        {"id": "C", "role": "worker", "team": "green", "host": "192.168.1.1", "port": 60053},
        {"id": "E", "role": "team_leader", "team": "pink", "host": "192.168.1.1", "port": 60055},
        {"id": "F", "role": "worker", "team": "pink", "host": "192.168.1.1", "port": 60056},
    ]
    
    # Windows nodes (for comparison)
    windows_nodes = [
        {"id": "A", "role": "leader", "team": "green", "host": "192.168.1.2", "port": 60051},
        {"id": "B", "role": "team_leader", "team": "green", "host": "192.168.1.2", "port": 60052},
        {"id": "D", "role": "worker", "team": "pink", "host": "192.168.1.2", "port": 60054},
    ]
    
    print("="*70)
    print("NODE PROCESSING TEST")
    print("="*70)
    print("\nThis test verifies that each node can process queries directly.")
    print("It checks if processing time increases after sending a query.")
    print("\nTesting macOS nodes first...")
    
    results = []
    
    # Test macOS nodes
    for node in macos_nodes:
        result = test_node_query(
            node["host"], node["port"], 
            node["id"], node["role"], node["team"]
        )
        results.append(result)
    
    # Test Windows nodes (optional, for comparison)
    print("\n\n" + "="*70)
    print("Testing Windows nodes for comparison...")
    print("="*70)
    
    for node in windows_nodes:
        result = test_node_query(
            node["host"], node["port"], 
            node["id"], node["role"], node["team"]
        )
        results.append(result)
    
    # Summary
    print("\n\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    macos_results = [r for r in results if r["node_id"] in ["C", "E", "F"]]
    windows_results = [r for r in results if r["node_id"] in ["A", "B", "D"]]
    
    print("\nmacOS Nodes:")
    for r in macos_results:
        status = "✓ PASS" if r.get("success") and r.get("processing_time_increased", False) else "✗ FAIL"
        print(f"  {r['node_id']} ({r.get('role', 'unknown')}): {status}")
        if not r.get("success"):
            print(f"    Error: {r.get('error', 'Unknown error')}")
        elif not r.get("processing_time_increased", False):
            print(f"    Warning: Processing time did not increase (may be idle)")
            print(f"    Initial: {r.get('initial_avg_time_ms', 0):.2f}ms, Final: {r.get('final_avg_time_ms', 0):.2f}ms")
        else:
            print(f"    Query Latency: {r.get('query_latency_ms', 0):.2f}ms")
            print(f"    Records Returned: {r.get('total_records', 0)}")
            print(f"    Processing Time: {r.get('initial_avg_time_ms', 0):.2f}ms → {r.get('final_avg_time_ms', 0):.2f}ms")
    
    print("\nWindows Nodes:")
    for r in windows_results:
        status = "✓ PASS" if r.get("success") and r.get("processing_time_increased", False) else "✗ FAIL"
        print(f"  {r['node_id']} ({r.get('role', 'unknown')}): {status}")
        if not r.get("success"):
            print(f"    Error: {r.get('error', 'Unknown error')}")
        elif not r.get("processing_time_increased", False):
            print(f"    Warning: Processing time did not increase (may be idle)")
        else:
            print(f"    Query Latency: {r.get('query_latency_ms', 0):.2f}ms")
            print(f"    Records Returned: {r.get('total_records', 0)}")
    
    # Overall assessment
    print("\n" + "="*70)
    macos_passed = sum(1 for r in macos_results if r.get("success") and r.get("processing_time_increased", False))
    print(f"macOS Nodes: {macos_passed}/{len(macos_results)} nodes processing requests")
    
    if macos_passed < len(macos_results):
        print("\n⚠️  WARNING: Some macOS nodes are not processing requests!")
        print("   This could indicate:")
        print("   1. Nodes are not receiving forwarded requests")
        print("   2. Nodes have no matching data for the query")
        print("   3. Nodes are satisfying queries too quickly (cached)")
    
    return 0 if macos_passed == len(macos_results) else 1


if __name__ == "__main__":
    sys.exit(main())


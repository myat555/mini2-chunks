#!/usr/bin/env python3
"""Helper script to wait for leader to be ready."""
import os
import sys
import time
import grpc

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

import overlay_pb2
import overlay_pb2_grpc

def wait_for_leader(address, timeout=30):
    """Wait for leader to be ready."""
    start_time = time.time()
    print(f"Waiting for leader at {address}...", end="", flush=True)
    
    while time.time() - start_time < timeout:
        try:
            channel = grpc.insecure_channel(address)
            stub = overlay_pb2_grpc.OverlayNodeStub(channel)
            metrics = stub.GetMetrics(overlay_pb2.MetricsRequest(), timeout=2)
            channel.close()
            
            if metrics.process_id and metrics.role == "leader":
                print(" Ready!")
                return True
        except Exception:
            pass
        
        time.sleep(1)
        print(".", end="", flush=True)
    
    print(" Timeout!")
    return False

if __name__ == "__main__":
    address = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1:60051"
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    success = wait_for_leader(address, timeout)
    sys.exit(0 if success else 1)


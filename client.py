import grpc
import sys
import os

sys.path.append(os.path.dirname(__file__))

import overlay_pb2
import overlay_pb2_grpc

def test_single_request(server_host, server_port):
    address = f"{server_host}:{server_port}"
    print(f"Testing leader at {address}")
    
    channel = grpc.insecure_channel(address)
    stub = overlay_pb2_grpc.OverlayNodeStub(channel)
    
    req = overlay_pb2.Request(payload="test", hops=[])
    
    try:
        resp = stub.Forward(req)
        print(f"Response: {resp.result}")
        print(f"Hops: {resp.hops}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        channel.close()

def check_queue_status(server_host, server_port):
    address = f"{server_host}:{server_port}"
    channel = grpc.insecure_channel(address)
    stub = overlay_pb2_grpc.OverlayNodeStub(channel)
    
    try:
        metrics = stub.GetMetrics(overlay_pb2.MetricsRequest())
        print(f"\nQueue Status for {metrics.process_id}:")
        print(f"  Role: {metrics.role}")
        print(f"  Queue Size: {metrics.queue_size}")
        print(f"  Active Requests: {metrics.active_requests}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        channel.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python client.py <host> <port> [check]")
        print("Example: python client.py 192.168.1.100 50051")
        print("         python client.py 192.168.1.100 50051 check")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    
    if len(sys.argv) > 3 and sys.argv[3] == "check":
        check_queue_status(host, port)
    else:
        test_single_request(host, port)

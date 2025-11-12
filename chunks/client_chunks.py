import grpc
import overlay_pb2
import overlay_pb2_grpc
import sys

def main(server_host, server_port):
    """Client connects only to leader (A) - the portal/entry point"""
    address = f"{server_host}:{server_port}"
    print(f"Connecting to leader at {address}...")
    
    channel = grpc.insecure_channel(address)
    stub = overlay_pb2_grpc.OverlayNodeStub(channel)
    
    # Create request with empty hops (starting point)
    req = overlay_pb2.Request(payload="query", hops=[])
    
    try:
        # Send request to leader - only A can receive client requests
        resp = stub.Forward(req)
        print(f"\nResponse from network:")
        print(f"  Result: {resp.result}")
        print(f"  Hops: {resp.hops}")
        print(f"\nNote: Only the leader (A) should receive client requests.")
    except grpc.RpcError as e:
        print(f"Error: {e.code()} - {e.details()}")
    finally:
        channel.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python client_chunks.py <host> <port>")
        print("Example: python client_chunks.py localhost 50051")
        print("Note: Connect to leader (A) - typically port 50051")
        sys.exit(1)
    
    main(sys.argv[1], int(sys.argv[2]))

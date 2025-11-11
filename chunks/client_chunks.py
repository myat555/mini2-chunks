import grpc
import overlay_pb2
import overlay_pb2_grpc
import sys

def main(server_host, server_port):
    channel = grpc.insecure_channel(f"{server_host}:{server_port}")
    stub = overlay_pb2_grpc.OverlayNodeStub(channel)
    req = overlay_pb2.Request(payload="start", hops=[])
    resp = stub.Forward(req)
    print("Got aggregated result:", resp.result, "hops:", resp.hops)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python client.py <host> <port>")
        sys.exit(1)
    main(sys.argv[1], int(sys.argv[2]))

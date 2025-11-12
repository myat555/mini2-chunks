import grpc
import test_pb2
import test_pb2_grpc

def run():
    # Use localhost for single-machine testing, or replace with server's IP for network testing
    server_ip = "localhost"  # Use "localhost" or "127.0.0.1" for same machine, or actual IP for network
    channel = grpc.insecure_channel(f"{server_ip}:50051")
    stub = test_pb2_grpc.PingServiceStub(channel)

    response = stub.Ping(test_pb2.PingMessage(text="Hello from client!"))
    print("Received response:", response.text)

if __name__ == '__main__':
    run()

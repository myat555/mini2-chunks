import grpc
import test_pb2
import test_pb2_grpc

def run():
    # Use the server's LAN IP address; replace below as needed
    server_ip = "169.254.3.96"  # Replace with Windows PC IP for test
    channel = grpc.insecure_channel(f"{server_ip}:50051")
    stub = test_pb2_grpc.PingServiceStub(channel)

    response = stub.Ping(test_pb2.PingMessage(text="Hello from client!"))
    print("Received response:", response.text)

if __name__ == '__main__':
    run()

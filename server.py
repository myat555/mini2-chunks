import grpc
from concurrent import futures
import time
import test_pb2
import test_pb2_grpc

class PingServiceServicer(test_pb2_grpc.PingServiceServicer):
    def Ping(self, request, context):
        print(f"Received Ping: {request.text}")
        return test_pb2.PongMessage(text=f"Pong from server: {request.text}")

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=2))
    test_pb2_grpc.add_PingServiceServicer_to_server(PingServiceServicer(), server)
    # Listen on all network interfaces
    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server started on port 50051")
    try:
        while True:
            time.sleep(60*60*24)
    except KeyboardInterrupt:
        server.stop(0)
        print("Server stopped")

if __name__ == '__main__':
    serve()

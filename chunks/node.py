import grpc
import json
from concurrent import futures
import overlay_pb2
import overlay_pb2_grpc
import sys

class OverlayServicer(overlay_pb2_grpc.OverlayNodeServicer):
    def __init__(self, config):
        self.config = config
        self.neighbors = config["neighbors"]
        self.id = config["id"]

    def Forward(self, request, context):
        print(f"{self.id} got request with hops: {request.hops}")
        # Avoid loops: don't go back to places been
        new_hops = list(request.hops)
        new_hops.append(self.id)
        # Forward to neighbors who are not in hops
        if len(self.neighbors) > 0:
            responses = []
            for n in self.neighbors:
                if n['host'] not in request.hops:  # simplistic; could use neighbor 'id'
                    resp = forward_to_neighbor(n["host"], n["port"], request.payload, new_hops)
                    responses.append(resp)
            agg = ";".join(r.result for r in responses)
            return overlay_pb2.Response(result=f"{self.id}|{agg}", hops=new_hops)
        else:
            # Leaf node
            return overlay_pb2.Response(result=self.id, hops=new_hops)

def forward_to_neighbor(host, port, payload, hops):
    with grpc.insecure_channel(f"{host}:{port}") as channel:
        stub = overlay_pb2_grpc.OverlayNodeStub(channel)
        req = overlay_pb2.Request(payload=payload, hops=hops)
        resp = stub.Forward(req)
        return resp

def serve(config_path):
    with open(config_path) as f:
        config = json.load(f)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    servicer = OverlayServicer(config)
    overlay_pb2_grpc.add_OverlayNodeServicer_to_server(servicer, server)
    server.add_insecure_port(f"[::]:{config['listen_port']}")
    server.start()
    print(f"Node {config['id']} listening on port {config['listen_port']} with neighbors: {config['neighbors']}")
    server.wait_for_termination()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python node.py node_config.json")
        sys.exit(1)
    serve(sys.argv[1])

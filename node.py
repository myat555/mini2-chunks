import grpc
import json
import time
import threading
import queue
from concurrent import futures
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

import overlay_pb2
import overlay_pb2_grpc

class OverlayServicer(overlay_pb2_grpc.OverlayNodeServicer):
    def __init__(self, config_path, process_id):
        # Load configuration
        with open(config_path) as f:
            self.full_config = json.load(f)
        
        self.process_id = process_id
        self.process_config = self.full_config['processes'][process_id]
        
        # Extract process info
        self.id = self.process_config['id']
        self.role = self.process_config['role']
        self.team = self.process_config['team']
        self.host = self.process_config['host']
        self.port = self.process_config['port']
        self.neighbor_ids = self.process_config['neighbors']
        
        # Leader queue implementation
        self.request_queue = None
        self.queue_workers = []
        self.active_requests = {}
        self.max_capacity = 100
        
        # Initialize queue if leader
        if self.role == 'leader':
            self.request_queue = queue.Queue(maxsize=200)
            self.start_queue_workers()
        
        print(f"Process {self.id} started: {self.role}@{self.host}:{self.port}")

    def get_neighbor_address(self, neighbor_id):
        neighbor_config = self.full_config['processes'][neighbor_id]
        return f"{neighbor_config['host']}:{neighbor_config['port']}"

    def Forward(self, request, context):
        print(f"{self.id} ({self.role}) received request")
        
        # Loop prevention
        if self.id in request.hops:
            return overlay_pb2.Response(result="", hops=request.hops)
        
        # Capacity check
        if len(self.active_requests) >= self.max_capacity:
            return overlay_pb2.Response(result="", hops=request.hops)
        
        # Add to hops
        new_hops = list(request.hops)
        new_hops.append(self.id)
        
        # Leader queue handling
        if self.role == 'leader' and self.request_queue:
            try:
                self.request_queue.put((request, context, new_hops), timeout=5)
                return self.handle_leader_forward(request, new_hops)
            except queue.Full:
                return overlay_pb2.Response(result="", hops=request.hops)
        
        # Role-based processing
        if self.role == "leader":
            return self.handle_leader_forward(request, new_hops)
        elif self.role == "team_leader":
            return self.handle_team_leader_forward(request, new_hops)
        else:
            return self.handle_worker_process(request, new_hops)

    def handle_leader_forward(self, request, hops):
        responses = []
        for neighbor_id in self.neighbor_ids:
            neighbor_config = self.full_config['processes'][neighbor_id]
            if neighbor_config['role'] == 'team_leader':
                try:
                    address = self.get_neighbor_address(neighbor_id)
                    resp = forward_to_neighbor(address, request.payload, hops)
                    responses.append(resp)
                except Exception as e:
                    print(f"{self.id} error: {e}")
        
        if responses:
            non_empty = [r.result for r in responses if r.result]
            if non_empty:
                return overlay_pb2.Response(result=f"{self.id}|{';'.join(non_empty)}", hops=hops)
        
        return overlay_pb2.Response(result=self.id, hops=hops)

    def handle_team_leader_forward(self, request, hops):
        responses = []
        for neighbor_id in self.neighbor_ids:
            neighbor_config = self.full_config['processes'][neighbor_id]
            if neighbor_config['team'] == self.team:
                try:
                    address = self.get_neighbor_address(neighbor_id)
                    resp = forward_to_neighbor(address, request.payload, hops)
                    responses.append(resp)
                except Exception as e:
                    print(f"{self.id} error: {e}")
        
        # Process locally
        local_result = f"{self.id}-processed"
        responses.append(overlay_pb2.Response(result=local_result, hops=hops))
        
        if responses:
            non_empty = [r.result for r in responses if r.result]
            if non_empty:
                return overlay_pb2.Response(result=f"{self.id}|{';'.join(non_empty)}", hops=hops)
        
        return overlay_pb2.Response(result=self.id, hops=hops)

    def handle_worker_process(self, request, hops):
        return overlay_pb2.Response(result=f"{self.id}-processed", hops=hops)

    # Leader queue methods
    def start_queue_workers(self):
        def queue_worker():
            while True:
                try:
                    request_data = self.request_queue.get(timeout=1)
                    if len(request_data) == 3:
                        request, context, hops = request_data
                        self.handle_leader_forward(request, hops)
                    self.request_queue.task_done()
                except queue.Empty:
                    continue
        
        for i in range(5):  # 5 queue workers
            worker = threading.Thread(target=queue_worker, daemon=True)
            worker.start()
            self.queue_workers.append(worker)

    def GetMetrics(self, request, context):
        queue_size = self.request_queue.qsize() if self.request_queue else 0
        return overlay_pb2.MetricsResponse(
            process_id=self.id,
            role=self.role,
            team=self.team,
            active_requests=len(self.active_requests),
            max_capacity=self.max_capacity,
            is_healthy=True,
            queue_size=queue_size,
            avg_processing_time_ms=0.0
        )

def forward_to_neighbor(address, payload, hops):
    with grpc.insecure_channel(address) as channel:
        stub = overlay_pb2_grpc.OverlayNodeStub(channel)
        req = overlay_pb2.Request(payload=payload, hops=hops)
        return stub.Forward(req)

def serve(config_path, process_id):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    servicer = OverlayServicer(config_path, process_id)
    overlay_pb2_grpc.add_OverlayNodeServicer_to_server(servicer, server)
    
    with open(config_path) as f:
        config = json.load(f)
    process_config = config['processes'][process_id]
    server_address = f"0.0.0.0:{process_config['port']}"

    server.add_insecure_port(server_address)
    server.start()
    
    print(f"Process {process_id} listening on {process_config['host']}:{process_config['port']}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python node.py <config_file> <process_id>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    process_id = sys.argv[2]
    
    with open(config_path) as f:
        config = json.load(f)
    
    if process_id not in config['processes']:
        print(f"Error: Process {process_id} not found")
        sys.exit(1)
    
    serve(config_path, process_id)

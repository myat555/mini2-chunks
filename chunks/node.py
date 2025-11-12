import grpc
import json
import os
import time
import threading
import queue
from concurrent import futures
import overlay_pb2
import overlay_pb2_grpc
import sys

class OverlayServicer(overlay_pb2_grpc.OverlayNodeServicer):
    def __init__(self, config_path, process_id):
        # Load full configuration
        with open(config_path) as f:
            full_config = json.load(f)
        
        # Get this process's configuration
        self.process_id = process_id
        self.process_config = full_config['processes'][process_id]
        self.full_config = full_config
        
        # Extract process info
        self.id = self.process_config['id']
        self.role = self.process_config['role']
        self.team = self.process_config['team']
        self.host = self.process_config['host']
        self.port = self.process_config['port']
        
        # Get neighbor process IDs (not host:port, but process IDs)
        self.neighbor_ids = self.process_config['neighbors']
        
        # Request queue (for leader only)
        self.request_queue = None
        self.queue_workers = []
        self.active_requests = {}
        self.max_capacity = 100
        self.metrics_lock = threading.Lock()
        
        # Initialize queue if starting as leader
        if self.role == 'leader':
            self.request_queue = queue.Queue(maxsize=200)
            self.start_queue_workers()
        
        print(f"Process {self.id} initialized: role={self.role}, team={self.team}, neighbors={self.neighbor_ids}")

    def get_neighbor_address(self, neighbor_id):
        """Get host:port address for a neighbor process ID"""
        neighbor_config = self.full_config['processes'][neighbor_id]
        return f"{neighbor_config['host']}:{neighbor_config['port']}"

    def get_team_leader(self, team_name):
        """Get team leader process ID for a team"""
        for proc_id, proc_config in self.full_config['processes'].items():
            if proc_config['team'] == team_name and proc_config['role'] == 'team_leader':
                return proc_id
        return None

    def get_workers_in_team(self, team_name):
        """Get all worker process IDs in a team"""
        workers = []
        for proc_id, proc_config in self.full_config['processes'].items():
            if proc_config['team'] == team_name and proc_config['role'] == 'worker':
                workers.append(proc_id)
        return workers

    def Forward(self, request, context):
        """Handle request forwarding based on role"""
        print(f"{self.id} ({self.role}) received request with hops: {request.hops}")
        
        # Check if already processed (loop prevention)
        if self.id in request.hops:
            print(f"{self.id} already processed this request, returning empty")
            return overlay_pb2.Response(result="", hops=request.hops)
        
        # Check capacity
        if len(self.active_requests) >= self.max_capacity:
            print(f"{self.id} at capacity ({len(self.active_requests)}/{self.max_capacity})")
            return overlay_pb2.Response(result="", hops=request.hops)
        
        # Add self to hops
        new_hops = list(request.hops)
        new_hops.append(self.id)
        
        # Use queue if leader and queue is available
        if self.role == 'leader' and self.request_queue:
            try:
                # Add to queue (non-blocking with timeout)
                self.request_queue.put((request, context, new_hops), timeout=5)
                # Process immediately (queue is for fairness, but we can process now)
                # In a full implementation, queue workers would process this
                return self.handle_leader_forward(request, new_hops)
            except queue.Full:
                print(f"{self.id} queue full, rejecting request")
                return overlay_pb2.Response(result="", hops=request.hops)
        
        # Role-based forwarding
        if self.role == "leader":
            # Leader forwards to team leaders
            return self.handle_leader_forward(request, new_hops)
        elif self.role == "team_leader":
            # Team leader forwards to workers in same team, also processes locally
            return self.handle_team_leader_forward(request, new_hops)
        else:  # worker
            # Worker processes locally only
            return self.handle_worker_process(request, new_hops)

    def handle_leader_forward(self, request, hops):
        """Leader forwards to team leaders (B and E)"""
        print(f"{self.id} (leader) forwarding to team leaders")
        
        responses = []
        team_leaders = []
        
        # Find team leaders (B and E)
        for neighbor_id in self.neighbor_ids:
            neighbor_config = self.full_config['processes'][neighbor_id]
            if neighbor_config['role'] == 'team_leader':
                team_leaders.append(neighbor_id)
        
        # Forward to each team leader
        for team_leader_id in team_leaders:
            try:
                address = self.get_neighbor_address(team_leader_id)
                resp = forward_to_neighbor(address, request.payload, hops)
                responses.append(resp)
                print(f"{self.id} got response from {team_leader_id}")
            except Exception as e:
                print(f"{self.id} error forwarding to {team_leader_id}: {e}")
                continue
        
        # Aggregate responses
        if responses:
            non_empty = [r.result for r in responses if r.result]
            if non_empty:
                agg = ";".join(non_empty)
                return overlay_pb2.Response(result=f"{self.id}|{agg}", hops=hops)
        
        return overlay_pb2.Response(result=self.id, hops=hops)

    def handle_team_leader_forward(self, request, hops):
        """Team leader forwards to workers in same team, also processes locally"""
        print(f"{self.id} (team_leader) forwarding to workers in team {self.team}")
        
        responses = []
        
        # Find workers in same team
        workers = self.get_workers_in_team(self.team)
        
        # Forward to workers
        for worker_id in workers:
            if worker_id in self.neighbor_ids:  # Only forward to direct neighbors
                try:
                    address = self.get_neighbor_address(worker_id)
                    resp = forward_to_neighbor(address, request.payload, hops)
                    responses.append(resp)
                    print(f"{self.id} got response from worker {worker_id}")
                except Exception as e:
                    print(f"{self.id} error forwarding to {worker_id}: {e}")
                    continue
        
        # Also process locally (team leaders act as workers too)
        local_result = self.process_local(request)
        if local_result:
            responses.append(overlay_pb2.Response(result=local_result, hops=hops))
        
        # Aggregate responses
        if responses:
            non_empty = [r.result for r in responses if r.result]
            if non_empty:
                agg = ";".join(non_empty)
                return overlay_pb2.Response(result=f"{self.id}|{agg}", hops=hops)
        
        return overlay_pb2.Response(result=self.id, hops=hops)

    def handle_worker_process(self, request, hops):
        """Worker processes locally only"""
        print(f"{self.id} (worker) processing locally")
        result = self.process_local(request)
        return overlay_pb2.Response(result=result or self.id, hops=hops)

    def process_local(self, request):
        """Process request locally - returns simple result for now"""
        # TODO: Add actual data processing here later
        return f"{self.id}-processed"
    
    # ========== Request Queue Methods (Leader Only) ==========
    
    def start_queue_workers(self):
        """Start worker threads to process queue"""
        if not self.request_queue:
            return
        
        self.queue_workers = []
        num_workers = 10
        
        def queue_worker():
            while True:
                try:
                    request_data = self.request_queue.get(timeout=1)
                    if len(request_data) == 3:
                        request, context, hops = request_data
                        # Process request from queue
                        self.process_queued_request(request, context, hops)
                    self.request_queue.task_done()
                except queue.Empty:
                    continue
        
        for i in range(num_workers):
            worker = threading.Thread(target=queue_worker, daemon=True)
            worker.start()
            self.queue_workers.append(worker)
    
    def process_queued_request(self, request, context, hops):
        """Process a request from the queue"""
        # Process the request using leader forwarding logic
        return self.handle_leader_forward(request, hops)
    
    # ========== Metrics Methods ==========
    
    def GetMetrics(self, request, context):
        """Return performance metrics"""
        with self.metrics_lock:
            queue_size = self.request_queue.qsize() if self.request_queue else 0
            
            return overlay_pb2.MetricsResponse(
                process_id=self.id,
                role=self.role,
                team=self.team,
                active_requests=len(self.active_requests),
                max_capacity=self.max_capacity,
                is_healthy=True,
                queue_size=queue_size,
                avg_processing_time_ms=0.0  # TODO: Calculate from metrics
            )

def forward_to_neighbor(address, payload, hops):
    """Forward request to a neighbor by address"""
    with grpc.insecure_channel(address) as channel:
        stub = overlay_pb2_grpc.OverlayNodeStub(channel)
        req = overlay_pb2.Request(payload=payload, hops=hops)
        resp = stub.Forward(req)
        return resp

def serve(config_path, process_id):
    """Start the server for a specific process"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    servicer = OverlayServicer(config_path, process_id)
    overlay_pb2_grpc.add_OverlayNodeServicer_to_server(servicer, server)
    
    # Get address from config
    with open(config_path) as f:
        config = json.load(f)
    process_config = config['processes'][process_id]
    server_address = f"[::]:{process_config['port']}"
    
    server.add_insecure_port(server_address)
    server.start()
    
    print(f"Process {process_id} ({process_config['role']}, {process_config['team']}) "
          f"listening on {process_config['host']}:{process_config['port']}")
    print(f"Neighbors: {process_config['neighbors']}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)
        print(f"Process {process_id} stopped")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python node.py <config_file> <process_id>")
        print("Example: python node.py config/single_host.json A")
        sys.exit(1)
    
    config_path = sys.argv[1]
    process_id = sys.argv[2]
    
    # Validate process ID
    with open(config_path) as f:
        config = json.load(f)
    
    if process_id not in config['processes']:
        print(f"Error: Process {process_id} not found in config")
        print(f"Available processes: {list(config['processes'].keys())}")
        sys.exit(1)
    
    serve(config_path, process_id)

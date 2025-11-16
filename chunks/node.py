import grpc
import json
import os
import time
import threading
import queue
import csv
import random
from concurrent import futures
import overlay_pb2
import overlay_pb2_grpc
import sys

class FireDataStore:
    """Stores fire data for each process - loads from pre-partitioned files"""
    def __init__(self, process_id, team, data_dir="fire_data"):
        self.process_id = process_id
        self.team = team
        self.fires = []
        self.lock = threading.Lock()
        
        # Determine which region files this team should read
        if self.team == "green":
            self.region_files = ["fires_north.csv", "fires_central.csv"]
        else:
            self.region_files = ["fires_south.csv", "fires_east.csv", "fires_west.csv"]
        
        print(f"{process_id} ({team}) assigned to read: {self.region_files}")
        
        # Load data from pre-partitioned files
        self._load_from_partitioned_files(data_dir)
    
    def _load_from_partitioned_files(self, data_dir):
        """Load fire data from pre-partitioned region files"""
        if not os.path.exists(data_dir):
            print(f"Warning: Data directory '{data_dir}' not found. Generating sample data.")
            self._generate_sample_data()
            return
        
        total_loaded = 0
        
        for filename in self.region_files:
            file_path = os.path.join(data_dir, filename)
            
            if not os.path.exists(file_path):
                print(f"Warning: {file_path} not found, skipping")
                continue
            
            count = self._load_single_file(file_path)
            total_loaded += count
            print(f"  {self.process_id} loaded {count} fires from {filename}")
        
        if total_loaded == 0:
            print(f"Warning: No data loaded for {self.process_id}. Generating sample data.")
            self._generate_sample_data()
        else:
            print(f"{self.process_id} total: {len(self.fires)} fires loaded from {len(self.region_files)} files")
    
    def _load_single_file(self, file_path):
        """Load fires from a single CSV file"""
        count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    try:
                        fire = overlay_pb2.FireData(
                            fire_id=int(row['fire_id']),
                            latitude=float(row['latitude']),
                            longitude=float(row['longitude']),
                            temperature=float(row['temperature']),
                            intensity=float(row['intensity']),
                            timestamp=int(row['timestamp']),
                            region=row['region'].strip().lower(),
                            is_active=row.get('is_active', 'true').strip().lower() == 'true'
                        )
                        self.fires.append(fire)
                        count += 1
                    except (ValueError, KeyError) as e:
                        print(f"Error parsing line in {file_path}: {e}")
                        continue
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
        
        return count
    
    def _generate_sample_data(self):
        """Generate sample data if files don't exist"""
        if self.team == "green":
            regions = ["north", "central"]
        else:
            regions = ["south", "east", "west"]
        
        num_fires = random.randint(50, 100)
        for i in range(num_fires):
            fire = overlay_pb2.FireData(
                fire_id=hash(f"{self.process_id}-{i}") % 100000,
                latitude=random.uniform(32.0, 42.0),
                longitude=random.uniform(-125.0, -115.0),
                temperature=random.uniform(200.0, 1200.0),
                intensity=random.uniform(0.1, 1.0),
                timestamp=int(time.time()) - random.randint(0, 86400),
                region=random.choice(regions),
                is_active=random.random() > 0.3
            )
            self.fires.append(fire)
        print(f"{self.process_id}: Generated {num_fires} sample fires")
    
    def query_fires(self, query_type, region=None, min_temp=None):
        """Query fires based on criteria"""
        with self.lock:
            results = []
            for fire in self.fires:
                if query_type == 0:  # All fires
                    results.append(fire)
                elif query_type == 1:  # By region
                    if region and fire.region == region.lower():
                        results.append(fire)
                elif query_type == 2:  # By temperature
                    if min_temp and fire.temperature >= min_temp:
                        results.append(fire)
                elif query_type == 3:  # Active only
                    if fire.is_active:
                        results.append(fire)
            return results

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
        
        # Load balancing metrics
        self.processed_count = 0
        self.processing_times = []  # Track processing times for average
        self.max_processing_times = 100  # Keep last 100 times
        
        # Fire data store (loads from pre-partitioned files)
        self.fire_store = FireDataStore(self.id, self.team)
        
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
    
    def get_process_load(self, process_id):
        """Get current load of a process via GetMetrics"""
        try:
            address = self.get_neighbor_address(process_id)
            with grpc.insecure_channel(address) as channel:
                stub = overlay_pb2_grpc.OverlayNodeStub(channel)
                metrics = stub.GetMetrics(overlay_pb2.MetricsRequest())
                # Calculate load: (active_requests + queue_size) / max_capacity
                load = (metrics.active_requests + metrics.queue_size) / max(metrics.max_capacity, 1)
                return min(load, 1.0)  # Cap at 1.0
        except Exception as e:
            print(f"Error getting load for {process_id}: {e}")
            return 1.0  # Assume fully loaded if can't check
    
    def select_least_loaded(self, candidate_ids):
        """Select the least loaded process from candidates"""
        if not candidate_ids:
            return None
        
        if len(candidate_ids) == 1:
            return candidate_ids[0]
        
        loads = {}
        for proc_id in candidate_ids:
            loads[proc_id] = self.get_process_load(proc_id)
        
        # Return process with lowest load
        least_loaded = min(loads.items(), key=lambda x: x[1])
        print(f"Load balancing: {loads}, selected {least_loaded[0]} (load={least_loaded[1]:.2f})")
        return least_loaded[0]

    def Forward(self, request, context):
        """Handle request forwarding based on role"""
        try:
            start_time = time.time()
            request_id = f"{self.id}-{int(time.time()*1000)}"
            
            # Convert hops to list safely
            try:
                request_hops = list(request.hops) if request.hops else []
            except Exception as e:
                print(f"{self.id} ERROR converting hops to list: {e}", flush=True)
                request_hops = []
            
            print(f"{self.id} ({self.role}) received request with hops: {request_hops}", flush=True)
            
            # Check if already processed (loop prevention)
            if self.id in request_hops:
                print(f"{self.id} already processed this request, returning empty", flush=True)
                resp = overlay_pb2.Response(result="")
                if request_hops:
                    resp.hops.extend(request_hops)
                return resp
            
            # Check capacity
            if len(self.active_requests) >= self.max_capacity:
                print(f"{self.id} at capacity ({len(self.active_requests)}/{self.max_capacity})", flush=True)
                resp = overlay_pb2.Response(result="")
                if request_hops:
                    resp.hops.extend(request_hops)
                return resp
            
            # Track active request
            self.active_requests[request_id] = start_time
            
            # Add self to hops
            new_hops = list(request_hops)
            new_hops.append(self.id)
            
            try:
                # Role-based forwarding with load balancing
                if self.role == "leader":
                    result = self.handle_leader_forward(request, new_hops)
                elif self.role == "team_leader":
                    result = self.handle_team_leader_forward(request, new_hops)
                else:  # worker
                    result = self.handle_worker_process(request, new_hops)
                
                # Track processing time
                processing_time = (time.time() - start_time) * 1000  # ms
                with self.metrics_lock:
                    self.processed_count += 1
                    self.processing_times.append(processing_time)
                    if len(self.processing_times) > self.max_processing_times:
                        self.processing_times.pop(0)
                
                return result
            except Exception as e:
                print(f"{self.id} ERROR in role-based forwarding: {e}", flush=True)
                import traceback
                traceback.print_exc()
                # Return error response
                resp = overlay_pb2.Response(result="")
                if new_hops:
                    resp.hops.extend(new_hops)
                return resp
            finally:
                # Remove from active requests
                if request_id in self.active_requests:
                    del self.active_requests[request_id]
        except Exception as e:
            print(f"{self.id} FATAL ERROR in Forward: {e}", flush=True)
            import traceback
            traceback.print_exc()
            # Return minimal error response
            resp = overlay_pb2.Response(result="")
            return resp

    def handle_leader_forward(self, request, hops):
        """Leader forwards to team leaders (B and E)"""
        print(f"{self.id} (leader) forwarding to team leaders", flush=True)
        
        responses = []
        team_leaders = []
        
        # Find team leaders (B and E)
        for neighbor_id in self.neighbor_ids:
            neighbor_config = self.full_config['processes'][neighbor_id]
            if neighbor_config['role'] == 'team_leader':
                team_leaders.append(neighbor_id)
        
        print(f"{self.id} found {len(team_leaders)} team leaders: {team_leaders}", flush=True)
        
        # Forward to each team leader
        for team_leader_id in team_leaders:
            try:
                address = self.get_neighbor_address(team_leader_id)
                print(f"{self.id} forwarding to {team_leader_id} at {address} with hops: {hops}", flush=True)
                # Pass full request information
                fire_query = None
                try:
                    if request.HasField('fire_query'):
                        fire_query = request.fire_query
                except (AttributeError, ValueError):
                    pass  # fire_query not set
                query_type = request.query_type if request.query_type else 0
                resp = forward_to_neighbor(
                    address, 
                    request.payload, 
                    hops, 
                    fire_query,
                    query_type
                )
                responses.append(resp)
                print(f"{self.id} got response from {team_leader_id}, hops: {list(resp.hops)}, result: {resp.result[:50] if resp.result else 'empty'}", flush=True)
            except Exception as e:
                print(f"{self.id} error forwarding to {team_leader_id}: {e}", flush=True)
                import traceback
                traceback.print_exc()
                continue
        
        # Aggregate responses and merge hops
        all_hops = set(hops)  # Start with current hops (includes self.id already)
        result_parts = []
        
        for resp in responses:
            if resp.result:
                result_parts.append(resp.result)
            # Always merge hops from all responses - convert protobuf repeated to list
            resp_hops_list = list(resp.hops) if resp.hops else []
            if resp_hops_list:
                print(f"{self.id} merging hops from response: {resp_hops_list}")
                all_hops.update(resp_hops_list)
            else:
                print(f"{self.id} WARNING: response has no hops or empty hops")
        
        # Ensure current node is included (should already be in hops, but make sure)
        all_hops.add(self.id)
        merged_hops = sorted(list(all_hops))  # Sort for consistency
        print(f"{self.id} final merged hops: {merged_hops}")
        
        if result_parts:
            agg = "|".join(result_parts)
            resp = overlay_pb2.Response(result=f"{self.id}|{agg}")
            resp.hops.extend(merged_hops) if merged_hops else None
            return resp
        
        resp = overlay_pb2.Response(result=self.id)
        resp.hops.extend(merged_hops) if merged_hops else None
        return resp

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
                    # Pass full request information
                    fire_query = None
                    try:
                        if request.HasField('fire_query'):
                            fire_query = request.fire_query
                    except (AttributeError, ValueError):
                        pass  # fire_query not set
                    query_type = request.query_type if request.query_type else 0
                    resp = forward_to_neighbor(
                        address, 
                        request.payload, 
                        hops,
                        fire_query,
                        query_type
                    )
                    responses.append(resp)
                    print(f"{self.id} got response from worker {worker_id}, hops: {list(resp.hops)}")
                except Exception as e:
                    print(f"{self.id} error forwarding to {worker_id}: {e}")
                    continue
        
        # Also process locally (team leaders act as workers too)
        local_result = self.process_local(request)
        if local_result:
            # Local processing uses current hops (which already includes self.id)
            local_resp = overlay_pb2.Response(result=local_result)
            local_resp.hops.extend(hops) if hops else None
            responses.append(local_resp)
        
        # Aggregate responses and merge hops
        all_hops = set(hops)  # Start with current hops (includes self.id already)
        result_parts = []
        
        for resp in responses:
            if resp.result:
                result_parts.append(resp.result)
            # Always merge hops from all responses - convert protobuf repeated to list
            resp_hops_list = list(resp.hops) if resp.hops else []
            if resp_hops_list:
                print(f"{self.id} merging hops from response: {resp_hops_list}")
                all_hops.update(resp_hops_list)
            else:
                print(f"{self.id} WARNING: response has no hops or empty hops")
        
        # Ensure current node is included (should already be in hops, but make sure)
        all_hops.add(self.id)
        merged_hops = sorted(list(all_hops))  # Sort for consistency
        print(f"{self.id} final merged hops: {merged_hops}")
        
        if result_parts:
            agg = "|".join(result_parts)
            resp = overlay_pb2.Response(result=f"{self.id}|{agg}")
            resp.hops.extend(merged_hops) if merged_hops else None
            return resp
        
        resp = overlay_pb2.Response(result=self.id)
        resp.hops.extend(merged_hops) if merged_hops else None
        return resp

    def handle_worker_process(self, request, hops):
        """Worker processes locally only"""
        print(f"{self.id} (worker) processing locally")
        fires = self.process_local(request)
        result_str = f"{self.id}-processed" if fires else self.id
        
        resp = overlay_pb2.Response(
            result=result_str,
            fire_results=fires or [],
            result_count=len(fires) if fires else 0
        )
        resp.hops.extend(hops) if hops else None
        return resp

    def process_local(self, request):
        """Process request locally using fire data"""
        query_type = request.query_type if request.query_type else 0
        region = None
        min_temp = None
        
        # Extract query parameters from fire_query if present
        try:
            if request.HasField('fire_query') and request.fire_query:
                region = request.fire_query.region if request.fire_query.region else None
        except (AttributeError, ValueError):
            pass  # fire_query not set
        
        # Query fire data
        fires = self.fire_store.query_fires(query_type, region, min_temp)
        
        print(f"{self.id} processed {len(fires)} fires (query_type={query_type}, region={region})")
        return fires
    
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
            active_count = len(self.active_requests)
            current_load = (active_count + queue_size) / max(self.max_capacity, 1)
            
            # Calculate average processing time
            avg_time = 0.0
            if self.processing_times:
                avg_time = sum(self.processing_times) / len(self.processing_times)
            
            return overlay_pb2.MetricsResponse(
                process_id=self.id,
                role=self.role,
                team=self.team,
                active_requests=active_count,
                max_capacity=self.max_capacity,
                is_healthy=True,
                queue_size=queue_size,
                avg_processing_time_ms=avg_time,
                processed_count=self.processed_count,
                current_load=min(current_load, 1.0)
            )

def forward_to_neighbor(address, payload, hops, fire_query=None, query_type=0):
    """Forward request to a neighbor by address"""
    with grpc.insecure_channel(address) as channel:
        stub = overlay_pb2_grpc.OverlayNodeStub(channel)
        # Build request - for repeated fields, assign after creation
        req = overlay_pb2.Request(
            payload=payload,
            query_type=query_type
        )
        # Assign hops list properly for repeated field
        if hops:
            req.hops.extend(hops)
        if fire_query is not None:
            req.fire_query.CopyFrom(fire_query)
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


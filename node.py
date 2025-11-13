import grpc
import json
import time
import threading
import queue
from concurrent import futures
import sys
import os
import csv
import glob
from collections import defaultdict
import uuid

# Add current directory to path for imports
sys.path.append(os.path.dirname(__file__))

import overlay_pb2
import overlay_pb2_grpc

class DataStore:
    """Manages the 2020-fire dataset for this process"""
    def __init__(self, process_id, team, dataset_path="datasets/2020-fire/data"):
        self.process_id = process_id
        self.team = team
        self.dataset_path = dataset_path
        self.data = []
        self.data_by_date = defaultdict(list)
        self.load_data()
    
    def load_data(self):
        """Load data files based on team assignment"""
        # Team Green: 20200810-20200820, Team Pink: 20200821-20200924
        date_ranges = {
            'green': ('20200810', '20200820'),
            'pink': ('20200821', '20200924')
        }
        
        pattern = os.path.join(self.dataset_path, '*', '*.csv')
        files = glob.glob(pattern)
        
        loaded_count = 0
        for file_path in files:
            parts = file_path.split(os.sep)
            if len(parts) >= 2:
                date_str = parts[-2]
                if self.team == 'green' and '20200810' <= date_str <= '20200820':
                    self._load_file(file_path, date_str)
                    loaded_count += 1
                elif self.team == 'pink' and '20200821' <= date_str <= '20200924':
                    self._load_file(file_path, date_str)
                    loaded_count += 1
        
        print(f"Process {self.process_id}: Loaded {len(self.data)} records from {loaded_count} files")
    
    def _load_file(self, file_path, date_str):
        """Load a single CSV file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 6:
                        try:
                            record = {
                                'latitude': float(row[0].strip('"')),
                                'longitude': float(row[1].strip('"')),
                                'timestamp': row[2].strip('"'),
                                'parameter': row[3].strip('"'),
                                'value': float(row[4].strip('"')) if row[4].strip('"') else 0.0,
                                'unit': row[5].strip('"'),
                                'aqi': int(row[7].strip('"')) if len(row) > 7 and row[7].strip('"') else 0,
                                'site_name': row[9].strip('"') if len(row) > 9 else '',
                                'date': date_str
                            }
                            self.data.append(record)
                            self.data_by_date[date_str].append(record)
                        except (ValueError, IndexError):
                            continue
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    def query(self, query_params):
        """Execute a query on the data"""
        try:
            params = json.loads(query_params) if isinstance(query_params, str) else query_params
            results = self.data
            
            if 'parameter' in params:
                results = [r for r in results if r['parameter'] == params['parameter']]
            if 'min_value' in params:
                results = [r for r in results if r['value'] >= params['min_value']]
            if 'max_value' in params:
                results = [r for r in results if r['value'] <= params['max_value']]
            if 'date_start' in params:
                results = [r for r in results if r['date'] >= params['date_start']]
            if 'date_end' in params:
                results = [r for r in results if r['date'] <= params['date_end']]
            if 'limit' in params:
                results = results[:params['limit']]
            
            return results
        except Exception as e:
            print(f"Query error: {e}")
            return []

class QueryResult:
    """Stores query results with chunking capability"""
    def __init__(self, uid, data, chunk_size=100):
        self.uid = uid
        self.data = data
        self.chunk_size = chunk_size
        self.total_records = len(data)
        self.total_chunks = (len(data) + chunk_size - 1) // chunk_size if data else 0
        self.created_at = time.time()
        self.status = "ready"
    
    def get_chunk(self, chunk_index):
        """Get a specific chunk of data"""
        if chunk_index < 0 or chunk_index >= self.total_chunks:
            return None
        start_idx = chunk_index * self.chunk_size
        end_idx = min(start_idx + self.chunk_size, len(self.data))
        chunk_data = self.data[start_idx:end_idx]
        return {
            'data': chunk_data,
            'chunk_index': chunk_index,
            'total_chunks': self.total_chunks,
            'is_last': (chunk_index == self.total_chunks - 1)
        }

class OverlayServicer(overlay_pb2_grpc.OverlayNodeServicer):
    def __init__(self, config_path, process_id):
        with open(config_path) as f:
            self.full_config = json.load(f)
        
        self.process_id = process_id
        self.process_config = self.full_config['processes'][process_id]
        
        self.id = self.process_config['id']
        self.role = self.process_config['role']
        self.team = self.process_config['team']
        self.host = self.process_config['host']
        self.port = self.process_config['port']
        self.neighbor_ids = self.process_config['neighbors']
        
        # Initialize data store
        self.data_store = DataStore(self.id, self.team)
        
        # Request queue for non-blocking behavior
        self.request_queue = None
        self.queue_workers = []
        self.active_requests = {}  # UID -> QueryResult
        self.max_capacity = 100
        
        # Strategy 1: Chunked Response Management
        self.chunk_size = 100  # Configurable chunk size
        
        # Strategy 2: Fairness and Balancing
        self.request_counts = {}  # Track requests per team/neighbor
        self.processing_times = []  # Track processing times for balancing
        
        # Strategy 3: Capacity Management
        self.capacity_threshold = 0.8  # Start throttling at 80% capacity
        self.rejected_requests = 0
        
        # Statistics
        self.total_requests = 0
        self.total_processed = 0
        self.start_time = time.time()
        
        # Initialize queue if leader
        if self.role == 'leader':
            self.request_queue = queue.Queue(maxsize=200)
            self.start_queue_workers()
        
        print(f"Process {self.id} started: {self.role}@{self.host}:{self.port} (Team: {self.team})")
        print(f"  Data loaded: {len(self.data_store.data)} records")

    def get_neighbor_address(self, neighbor_id):
        neighbor_config = self.full_config['processes'][neighbor_id]
        return f"{neighbor_config['host']}:{neighbor_config['port']}"

    def Forward(self, request, context):
        self.total_requests += 1
        
        # Loop prevention
        if self.id in request.hops:
            return overlay_pb2.Response(result="", hops=request.hops)
        
        # Strategy 3: Capacity Management - Check capacity before processing
        current_load = len(self.active_requests) / self.max_capacity
        if current_load >= self.capacity_threshold:
            # Throttle: reject some requests to prevent overload
            if current_load >= 1.0:
                self.rejected_requests += 1
                return overlay_pb2.Response(result="", hops=request.hops)
        
        # Add to hops
        new_hops = list(request.hops)
        new_hops.append(self.id)
        
        # Parse payload - expect JSON with query info
        try:
            payload_data = json.loads(request.payload) if request.payload else {}
            query_type = payload_data.get('type', 'simple')
            
            if query_type == 'query' and self.role in ['leader', 'team_leader', 'worker']:
                # Generate UID for query tracking
                uid = str(uuid.uuid4())
                
                # Strategy 2: Fairness - Track request distribution
                if 'team' in payload_data:
                    team = payload_data['team']
                    self.request_counts[team] = self.request_counts.get(team, 0) + 1
                
                # Enqueue for processing (non-blocking)
                if self.role == 'leader' and self.request_queue:
                    try:
                        self.request_queue.put((uid, request, new_hops, context), timeout=5)
                        # Return immediately with UID (non-blocking behavior)
                        return overlay_pb2.Response(
                            result=json.dumps({'uid': uid, 'status': 'accepted', 'chunk_size': self.chunk_size}),
                            hops=new_hops
                        )
                    except queue.Full:
                        self.rejected_requests += 1
                        return overlay_pb2.Response(result="", hops=request.hops)
                else:
                    # Process synchronously for non-leader nodes
                    result = self.process_query(uid, request, new_hops)
                    return overlay_pb2.Response(
                        result=json.dumps({'uid': uid, 'status': 'ready', 'total_chunks': result.total_chunks}),
                        hops=new_hops
                    )
        except (json.JSONDecodeError, KeyError):
            pass
        
        # Default forwarding behavior
        if self.role == 'leader':
            return self.handle_leader_forward(request, new_hops)
        elif self.role == 'team_leader':
            return self.handle_team_leader_forward(request, new_hops)
        else:
            return self.handle_worker_process(request, new_hops)

    def process_query(self, uid, request, hops):
        """Process a query request"""
        start_time = time.time()
        
        try:
            payload_data = json.loads(request.payload) if request.payload else {}
            query_params = payload_data.get('query', {})
            
            # Process locally
            local_results = self.data_store.query(json.dumps(query_params))
            all_results = list(local_results)
            
            # Forward to team members
            if self.role == "leader":
                # Strategy 2: Fairness - Distribute to both teams
                for neighbor_id in self.neighbor_ids:
                    neighbor_config = self.full_config['processes'][neighbor_id]
                    if neighbor_config['role'] == 'team_leader':
                        try:
                            forwarded_results = self.forward_query_to_neighbor(neighbor_id, request, hops)
                            all_results.extend(forwarded_results)
                        except Exception as e:
                            print(f"{self.id} error forwarding to {neighbor_id}: {e}")
            
            elif self.role == "team_leader":
                # Forward to team workers
                for neighbor_id in self.neighbor_ids:
                    neighbor_config = self.full_config['processes'][neighbor_id]
                    if neighbor_config['team'] == self.team and neighbor_config['role'] == 'worker':
                        try:
                            forwarded_results = self.forward_query_to_neighbor(neighbor_id, request, hops)
                            all_results.extend(forwarded_results)
                        except Exception as e:
                            print(f"{self.id} error forwarding to {neighbor_id}: {e}")
            
            # Strategy 1: Create chunked result
            query_result = QueryResult(uid, all_results, chunk_size=self.chunk_size)
            self.active_requests[uid] = query_result
            
            processing_time = (time.time() - start_time) * 1000
            self.processing_times.append(processing_time)
            if len(self.processing_times) > 100:
                self.processing_times.pop(0)
            
            self.total_processed += 1
            print(f"{self.id}: Query {uid} processed: {len(all_results)} records, {query_result.total_chunks} chunks")
            
            return query_result
            
        except Exception as e:
            print(f"{self.id}: Error processing query: {e}")
            error_result = QueryResult(uid, [], chunk_size=self.chunk_size)
            error_result.status = "error"
            self.active_requests[uid] = error_result
            return error_result

    def forward_query_to_neighbor(self, neighbor_id, request, hops):
        """Forward query to neighbor and get results"""
        if neighbor_id in hops:
            return []
        
        address = self.get_neighbor_address(neighbor_id)
        try:
            with grpc.insecure_channel(address) as channel:
                stub = overlay_pb2_grpc.OverlayNodeStub(channel)
                resp = stub.Forward(request)
                
                # Parse response to get UID and retrieve chunks
                try:
                    resp_data = json.loads(resp.result)
                    if 'uid' in resp_data:
                        # Wait for processing, then retrieve chunks
                        time.sleep(0.1)
                        return self.retrieve_chunks_from_neighbor(address, resp_data['uid'])
                except (json.JSONDecodeError, KeyError):
                    pass
        except Exception as e:
            print(f"{self.id}: Error forwarding to {neighbor_id}: {e}")
        
        return []

    def retrieve_chunks_from_neighbor(self, address, uid):
        """Retrieve all chunks from a neighbor (simplified - would need GetChunk RPC)"""
        # This is a placeholder - in full implementation would use GetChunk RPC
        return []

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
        
        local_result = f"{self.id}-processed"
        responses.append(overlay_pb2.Response(result=local_result, hops=hops))
        
        if responses:
            non_empty = [r.result for r in responses if r.result]
            if non_empty:
                return overlay_pb2.Response(result=f"{self.id}|{';'.join(non_empty)}", hops=hops)
        
        return overlay_pb2.Response(result=self.id, hops=hops)

    def handle_worker_process(self, request, hops):
        return overlay_pb2.Response(result=f"{self.id}-processed", hops=hops)

    def start_queue_workers(self):
        def queue_worker():
            while True:
                try:
                    request_data = self.request_queue.get(timeout=1)
                    if len(request_data) == 4:
                        uid, request, hops, context = request_data
                        self.process_query(uid, request, hops)
                    self.request_queue.task_done()
                except queue.Empty:
                    continue
        
        for i in range(5):
            worker = threading.Thread(target=queue_worker, daemon=True)
            worker.start()
            self.queue_workers.append(worker)

    def GetMetrics(self, request, context):
        queue_size = self.request_queue.qsize() if self.request_queue else 0
        avg_processing_time = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0.0
        
        uptime = time.time() - self.start_time
        request_rate = self.total_requests / uptime if uptime > 0 else 0
        
        return overlay_pb2.MetricsResponse(
            process_id=self.id,
            role=self.role,
            team=self.team,
            active_requests=len(self.active_requests),
            max_capacity=self.max_capacity,
            is_healthy=True,
            queue_size=queue_size,
            avg_processing_time_ms=avg_processing_time
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
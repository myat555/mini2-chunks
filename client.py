import grpc
import sys
import os
import json
import time

sys.path.append(os.path.dirname(__file__))

import overlay_pb2
import overlay_pb2_grpc

def send_query(server_host, server_port, query_params):
    """Send a query request to the server"""
    address = f"{server_host}:{server_port}"
    print(f"Sending query to {address}")
    print(f"Query params: {query_params}\n")
    
    channel = grpc.insecure_channel(address)
    stub = overlay_pb2_grpc.OverlayNodeStub(channel)
    
    payload = json.dumps({
        'type': 'query',
        'query': query_params
    })
    
    req = overlay_pb2.Request(payload=payload, hops=[])
    
    try:
        start_time = time.time()
        resp = stub.Forward(req)
        end_time = time.time()
        
        print(f"Response received in {(end_time - start_time)*1000:.2f} ms")
        print(f"Hops: {resp.hops}")
        
        # Parse response
        try:
            resp_data = json.loads(resp.result)
            print(f"\nQuery Status: {resp_data.get('status', 'unknown')}")
            if 'uid' in resp_data:
                print(f"Query UID: {resp_data['uid']}")
            if 'total_chunks' in resp_data:
                print(f"Total Chunks: {resp_data['total_chunks']}")
        except json.JSONDecodeError:
            print(f"Response: {resp.result}")
        
        return resp
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        channel.close()

def get_metrics(server_host, server_port):
    """Get server metrics"""
    address = f"{server_host}:{server_port}"
    channel = grpc.insecure_channel(address)
    stub = overlay_pb2_grpc.OverlayNodeStub(channel)
    
    try:
        metrics = stub.GetMetrics(overlay_pb2.MetricsRequest())
        print(f"\n=== Metrics for {metrics.process_id} ===")
        print(f"Role: {metrics.role}")
        print(f"Team: {metrics.team}")
        print(f"Active Requests: {metrics.active_requests}")
        print(f"Max Capacity: {metrics.max_capacity}")
        print(f"Queue Size: {metrics.queue_size}")
        print(f"Avg Processing Time: {metrics.avg_processing_time_ms:.2f} ms")
        print(f"Is Healthy: {metrics.is_healthy}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        channel.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python client.py <host> <port> [command] [args...]")
        print("\nCommands:")
        print("  metrics                    - Get server metrics")
        print("  query <param> <min> <max> - Query dataset (e.g., query PM2.5 10 50)")
        print("  date <start> <end>        - Query by date range (e.g., date 20200810 20200820)")
        print("\nExample:")
        print("  python client.py 192.168.1.2 50051 query PM2.5 10 50")
        print("  python client.py 192.168.1.2 50051 metrics")
        sys.exit(1)
    
    host = sys.argv[1]
    port = int(sys.argv[2])
    
    if len(sys.argv) > 3:
        command = sys.argv[3]
        
        if command == "metrics":
            get_metrics(host, port)
        
        elif command == "query":
            if len(sys.argv) < 6:
                print("Usage: query <parameter> <min_value> <max_value>")
                sys.exit(1)
            
            param = sys.argv[4]
            min_val = float(sys.argv[5])
            max_val = float(sys.argv[6])
            
            query_params = {
                'parameter': param,
                'min_value': min_val,
                'max_value': max_val,
                'limit': 1000
            }
            
            send_query(host, port, query_params)
        
        elif command == "date":
            if len(sys.argv) < 5:
                print("Usage: date <start_date> <end_date>")
                sys.exit(1)
            
            start_date = sys.argv[4]
            end_date = sys.argv[5]
            
            query_params = {
                'date_start': start_date,
                'date_end': end_date,
                'limit': 1000
            }
            
            send_query(host, port, query_params)
        
        else:
            print(f"Unknown command: {command}")
    else:
        # Default: simple test
        query_params = {
            'parameter': 'PM2.5',
            'min_value': 10.0,
            'max_value': 50.0,
            'limit': 100
        }
        send_query(host, port, query_params)
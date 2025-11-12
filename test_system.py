#!/usr/bin/env python3
"""
Automated system test for 2-host leader-queue implementation
"""

import grpc
import time
import threading
import sys
import os

sys.path.append(os.path.dirname(__file__))

import overlay_pb2
import overlay_pb2_grpc

class SystemTester:
    def __init__(self, leader_host, leader_port):
        self.leader_address = f"{leader_host}:{leader_port}"
    
    def test_single_request(self):
        """Test a single request through the entire system"""
        print("Testing single request...")
        
        channel = grpc.insecure_channel(self.leader_address)
        stub = overlay_pb2_grpc.OverlayNodeStub(channel)
        
        req = overlay_pb2.Request(payload="system-test", hops=[])
        
        try:
            start_time = time.time()
            resp = stub.Forward(req)
            end_time = time.time()
            
            print(f"✅ Single Request Test PASSED")
            print(f"   Response: {resp.result}")
            print(f"   Hops: {resp.hops}")
            print(f"   Latency: {(end_time - start_time)*1000:.2f} ms")
            print(f"   Nodes visited: {len(resp.hops)}")
            
            return True
        except Exception as e:
            print(f"❌ Single Request Test FAILED: {e}")
            return False
        finally:
            channel.close()
    
    def test_queue_status(self):
        """Test queue status monitoring"""
        print("Testing queue status...")
        
        channel = grpc.insecure_channel(self.leader_address)
        stub = overlay_pb2_grpc.OverlayNodeStub(channel)
        
        try:
            metrics = stub.GetMetrics(overlay_pb2.MetricsRequest())
            print(f"   Queue Status Test PASSED")
            print(f"   Process: {metrics.process_id}")
            print(f"   Role: {metrics.role}")
            print(f"   Queue Size: {metrics.queue_size}")
            print(f"   Active Requests: {metrics.active_requests}")
            
            return True
        except Exception as e:
            print(f"   Queue Status Test FAILED: {e}")
            return False
        finally:
            channel.close()
    
    def test_concurrent_requests(self, num_requests=10):
        """Test concurrent request handling"""
        print(f"Testing {num_requests} concurrent requests...")
        
        results = []
        lock = threading.Lock()
        
        def send_request(request_id):
            try:
                channel = grpc.insecure_channel(self.leader_address)
                stub = overlay_pb2_grpc.OverlayNodeStub(channel)
                
                req = overlay_pb2.Request(payload=f"concurrent-{request_id}", hops=[])
                resp = stub.Forward(req)
                
                with lock:
                    results.append(True)
                
                channel.close()
            except Exception:
                with lock:
                    results.append(False)
        
        threads = []
        start_time = time.time()
        
        for i in range(num_requests):
            thread = threading.Thread(target=send_request, args=(i,))
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        success_count = sum(results)
        success_rate = (success_count / num_requests) * 100
        
        print(f"   Concurrent Request Test COMPLETED")
        print(f"   Success: {success_count}/{num_requests} ({success_rate:.1f}%)")
        print(f"   Total Time: {end_time - start_time:.2f} seconds")
        
        return success_rate > 80  # Allow some failures due to network
    
    def run_full_test(self):
        """Run all tests"""
        print("=" * 50)
        print("2-HOST LEADER-QUEUE SYSTEM TEST")
        print("=" * 50)
        print(f"Testing leader at: {self.leader_address}")
        print()
        
        tests = [
            ("Single Request", self.test_single_request),
            ("Queue Status", self.test_queue_status),
            ("Concurrent Requests", lambda: self.test_concurrent_requests(10))
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                print()
            except Exception as e:
                print(f"{test_name} Test FAILED with exception: {e}")
                print()
        
        print("=" * 50)
        print(f"TEST SUMMARY: {passed}/{total} tests passed")
        
        if passed == total:
            print(" ALL TESTS PASSED! System is working correctly.")
        else:
            print(" Some tests failed. Check process logs for details.")
        
        print("=" * 50)
        
        return passed == total

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python test_system.py <leader_host> <leader_port>")
        print("Example: python test_system.py 192.168.1.100 50051")
        sys.exit(1)
    
    leader_host = sys.argv[1]
    leader_port = int(sys.argv[2])
    
    tester = SystemTester(leader_host, leader_port)
    success = tester.run_full_test()
    
    sys.exit(0 if success else 1)

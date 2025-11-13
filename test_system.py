#!/usr/bin/env python3
"""
Automated system test for 2-host leader-queue implementation
"""

import grpc
import json
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

    def _open_stub(self):
        channel = grpc.insecure_channel(self.leader_address)
        return channel, overlay_pb2_grpc.OverlayNodeStub(channel)

    def _basic_query(self, payload: str):
        return overlay_pb2.QueryRequest(
            query_type="filter",
            query_params=json.dumps({"parameter": "PM2.5", "limit": 20}),
            hops=[],
            client_id=payload,
        )

    def test_single_request(self):
        print("Testing single request...")
        channel, stub = self._open_stub()
        try:
            start = time.time()
            response = stub.Query(self._basic_query("single"))
            latency = (time.time() - start) * 1000
            if response.status != "ready":
                print(f"   Single Request FAILED: status={response.status}")
                return False

            chunk = stub.GetChunk(overlay_pb2.ChunkRequest(uid=response.uid, chunk_index=0))
            if chunk.status != "success":
                print(f"   Single Request FAILED: chunk status={chunk.status}")
                return False

            rows = json.loads(chunk.data)
            print(f"   Single Request PASSED, rows={len(rows)}, latency={latency:.2f} ms, hops={list(response.hops)}")
            return True
        except Exception as exc:
            print(f"   Single Request FAILED: {exc}")
            return False
        finally:
            channel.close()

    def test_queue_status(self):
        print("Testing queue status...")
        channel, stub = self._open_stub()
        try:
            metrics = stub.GetMetrics(overlay_pb2.MetricsRequest())
            print(
                f"   Metrics: id={metrics.process_id} active={metrics.active_requests} "
                f"queue={metrics.queue_size} avg_ms={metrics.avg_processing_time_ms:.2f}"
            )
            return True
        except Exception as exc:
            print(f"   Queue Status FAILED: {exc}")
            return False
        finally:
            channel.close()

    def test_concurrent_requests(self, num_requests=10):
        print(f"Testing {num_requests} concurrent requests...")
        results = []
        lock = threading.Lock()

        def worker(idx: int):
            channel, stub = self._open_stub()
            try:
                request = self._basic_query(f"concurrent-{idx}")
                response = stub.Query(request)
                ok = response.status == "ready"
                if ok:
                    chunk = stub.GetChunk(overlay_pb2.ChunkRequest(uid=response.uid, chunk_index=0))
                    ok = chunk.status == "success"
                with lock:
                    results.append(ok)
            except Exception:
                with lock:
                    results.append(False)
            finally:
                channel.close()

        threads = []
        start = time.time()
        for idx in range(num_requests):
            thread = threading.Thread(target=worker, args=(idx,))
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()
        duration = time.time() - start
        success = sum(1 for r in results if r)
        rate = (success / num_requests) * 100
        print(f"   Concurrent requests success {success}/{num_requests} ({rate:.1f}%), time={duration:.2f}s")
        return rate >= 80

    def run_full_test(self):
        print("=" * 50)
        print("OVERLAY SYSTEM TEST")
        print("=" * 50)
        print(f"Leader address: {self.leader_address}\n")

        tests = [
            ("Single Request", self.test_single_request),
            ("Queue Status", self.test_queue_status),
            ("Concurrent Requests", lambda: self.test_concurrent_requests(10)),
        ]

        passed = 0
        for name, func in tests:
            print(f"[{name}]")
            if func():
                passed += 1
            print()

        print("=" * 50)
        print(f"TEST SUMMARY: {passed}/{len(tests)} passed")
        print("=" * 50)
        return passed == len(tests)

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

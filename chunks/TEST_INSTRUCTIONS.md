# Test Instructions

## Prerequisites

1. **Virtual Environment Setup:**
   ```bash
   cd /Users/spartan/Documents/JohnGashCMPE285/workingproject/fromMatt/mini2-chunks
   python3 -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   pip install -r requirements.txt
   ```

2. **Generate Proto Files:**
   ```bash
   cd chunks
   chmod +x build_proto_chunks.sh
   ./build_proto_chunks.sh
   ```

---

## Test 1: Basic Functionality Test

### Step 1: Start All Processes

**Option A: Automatic (Recommended)**
```bash
cd chunks
chmod +x scripts/run_single_host.sh
./scripts/run_single_host.sh
```

**Option B: Manual (6 terminals)**
```bash
# Terminal 1
cd chunks
python3 node.py config/single_host.json A

# Terminal 2
cd chunks
python3 node.py config/single_host.json B

# Terminal 3
cd chunks
python3 node.py config/single_host.json C

# Terminal 4
cd chunks
python3 node.py config/single_host.json D

# Terminal 5
cd chunks
python3 node.py config/single_host.json E

# Terminal 6
cd chunks
python3 node.py config/single_host.json F
```

### Step 2: Verify Processes Started

Check that all processes are running:
```bash
# Check if processes are listening on ports
lsof -i :50051  # Should show process A
lsof -i :50052  # Should show process B
lsof -i :50053  # Should show process C
lsof -i :50054  # Should show process D
lsof -i :50055  # Should show process E
lsof -i :50056  # Should show process F
```

Or check logs:
```bash
cd chunks
tail -f logs/A.log
```

### Step 3: Send a Single Request

```bash
cd chunks
python3 client_chunks.py localhost 50051
```

**Expected Output:**
```
Connecting to leader at localhost:50051...

Response from network:
  Result: A|B|B-processed;C-processed|E|E-processed;D-processed;F-processed
  Hops: ['A', 'B', 'C', 'E', 'D', 'F']

Note: Only the leader (A) should receive client requests.
```

**What to Verify:**
- ✅ Request reaches leader (A)
- ✅ Leader forwards to team leaders (B, E)
- ✅ Team leaders forward to workers (C, D, F)
- ✅ Responses aggregate back correctly
- ✅ All 6 processes are in the hops list

### Step 4: Check Logs

```bash
cd chunks
# View leader log
tail -20 logs/A.log

# View team leader log
tail -20 logs/B.log

# View worker log
tail -20 logs/C.log
```

**Expected in logs:**
- A: "Process A initialized: role=leader, team=green"
- A: "A (leader) received request with hops: []"
- A: "A (leader) forwarding to team leaders"
- B: "B (team_leader) forwarding to workers in team green"
- C: "C (worker) processing locally"

---

## Test 2: Load Test - 100 Requests

### Step 1: Ensure All Processes Are Running

```bash
cd chunks
./scripts/run_single_host.sh
# Wait a few seconds for all processes to start
sleep 5
```

### Step 2: Run Sequential Load Test

```bash
cd chunks
python3 load_test_client.py localhost:50051 100 sequential
```

**Expected Output:**
```
============================================================
LOAD TEST CLIENT
============================================================
Server: localhost:50051
Requests: 100
Mode: Sequential
============================================================
Sending 100 sequential requests to localhost:50051...
  Completed: 10/100
  Completed: 20/100
  ...
  Completed: 100/100

============================================================
PERFORMANCE TEST REPORT
============================================================
Total Requests: 100
Successful: 100
Failed: 0
Success Rate: 100.00%

Timing:
  Total Time: X.XX seconds
  Throughput: XX.XX requests/second

Latency (milliseconds):
  Average: XX.XX ms
  Median: XX.XX ms
  Min: XX.XX ms
  Max: XX.XX ms
  95th Percentile: XX.XX ms
  99th Percentile: XX.XX ms
============================================================

Results saved to performance_results.json
```

### Step 3: Run Concurrent Load Test

```bash
cd chunks
python3 load_test_client.py localhost:50051 100 concurrent
```

**Expected Output:**
Similar to sequential, but:
- Higher throughput (more requests/second)
- Potentially higher latency (due to concurrency)
- All 100 requests should still succeed

### Step 4: Check Results File

```bash
cd chunks
cat performance_results.json
```

**What to Verify:**
- ✅ Success rate is 100% (or close to it)
- ✅ All requests completed
- ✅ Latency values are reasonable
- ✅ Throughput is measured

---

## Test 3: Queue Testing

### Step 1: Check Queue Status (Before Requests)

Create a simple queue status checker:

```bash
cd chunks
cat > check_queue.py << 'EOF'
import grpc
import overlay_pb2
import overlay_pb2_grpc
import sys

def check_queue(server_address):
    channel = grpc.insecure_channel(server_address)
    stub = overlay_pb2_grpc.OverlayNodeStub(channel)
    try:
        metrics = stub.GetMetrics(overlay_pb2.MetricsRequest())
        print(f"Queue Status for {metrics.process_id}:")
        print(f"  Role: {metrics.role}")
        print(f"  Queue Size: {metrics.queue_size}")
        print(f"  Active Requests: {metrics.active_requests}")
        print(f"  Max Capacity: {metrics.max_capacity}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        channel.close()

if __name__ == "__main__":
    check_queue(sys.argv[1] if len(sys.argv) > 1 else "localhost:50051")
EOF

chmod +x check_queue.py
```

### Step 2: Check Initial Queue Status

```bash
cd chunks
python3 check_queue.py localhost:50051
```

**Expected Output:**
```
Queue Status for A:
  Role: leader
  Queue Size: 0
  Active Requests: 0
  Max Capacity: 100
```

### Step 3: Send Requests and Monitor Queue

```bash
# In one terminal, monitor queue
cd chunks
watch -n 1 "python3 check_queue.py localhost:50051"

# In another terminal, send requests
cd chunks
python3 load_test_client.py localhost:50051 100 sequential
```

**What to Observe:**
- Queue size may increase during load
- Queue size should decrease as requests are processed
- Active requests count should stay below max capacity (100)

### Step 4: Check Queue in Logs

```bash
cd chunks
grep -i "queue" logs/A.log | tail -20
```

**Expected Log Messages:**
- "A queued request (queue size: X)"
- "A queue full, rejecting request" (if queue exceeds 200)

---

## Test 4: Role-Based Forwarding Verification

### Step 1: Send Request and Trace Path

```bash
cd chunks
python3 client_chunks.py localhost 50051
```

### Step 2: Verify Request Path

Check that the request follows the correct path:
1. **Client → A (leader)**
2. **A → B, E (team leaders)**
3. **B → C (worker in green team)**
4. **E → D, F (workers in pink team)**

### Step 3: Verify Team Separation

Check logs to ensure:
- Green team (A, B, C) processes work together
- Pink team (D, E, F) processes work together
- No cross-team forwarding (except through leader)

```bash
cd chunks
# Check green team
grep -E "(A|B|C)" logs/*.log | grep "forwarding\|processing"

# Check pink team
grep -E "(D|E|F)" logs/*.log | grep "forwarding\|processing"
```

---

## Test 5: Capacity and Error Handling

### Step 1: Test Capacity Limits

Send more requests than capacity to test rejection:

```bash
cd chunks
# Send 150 requests (exceeds max capacity of 100)
python3 load_test_client.py localhost:50051 150 concurrent
```

**Expected Behavior:**
- Some requests may be rejected if capacity is exceeded
- Logs should show "at capacity" messages
- Success rate may be less than 100%

### Step 2: Test Queue Full Scenario

Send many requests quickly to fill queue (max 200):

```bash
cd chunks
# Send 250 requests very quickly
python3 load_test_client.py localhost:50051 250 concurrent
```

**Expected Behavior:**
- Queue may fill up (max 200)
- Some requests may be rejected with "queue full" message
- Logs should show queue full warnings

---

## Test 6: Loop Prevention

### Step 1: Verify Hops Tracking

Send a request and check hops:

```bash
cd chunks
python3 client_chunks.py localhost 50051
```

**Verify:**
- Hops list contains all visited nodes: `['A', 'B', 'C', 'E', 'D', 'F']`
- No duplicate nodes in hops
- Each node appears only once

### Step 2: Check Loop Prevention Logs

```bash
cd chunks
grep "already processed" logs/*.log
```

**Expected:**
- Should be empty (no loops detected)
- If loops occur, you'll see "already processed this request" messages

---

## Test 7: Multi-Request Stress Test

### Step 1: Send Multiple Batches

```bash
cd chunks
# Send 3 batches of 100 requests
for i in {1..3}; do
    echo "Batch $i:"
    python3 load_test_client.py localhost:50051 100 concurrent
    sleep 2
done
```

**What to Verify:**
- All batches complete successfully
- System remains stable
- No memory leaks or crashes
- Queue handles multiple batches

---

## Test 8: Clean Shutdown

### Step 1: Stop All Processes

```bash
cd chunks
./scripts/stop_all.sh
```

**Expected Output:**
```
Stopping all running processes...
Killing process XXXX from pids/A.pid
Killing process XXXX from pids/B.pid
...
All processes stopped.
```

### Step 2: Verify Processes Stopped

```bash
# Check ports are free
lsof -i :50051  # Should show nothing
lsof -i :50052  # Should show nothing
# ... etc
```

---

## Troubleshooting

### Issue: "Port already in use"

**Solution:**
```bash
cd chunks
./scripts/stop_all.sh
# Or manually kill processes
lsof -ti:50051 | xargs kill
```

### Issue: "Connection refused"

**Solution:**
- Ensure all 6 processes are running
- Check logs: `tail logs/*.log`
- Verify processes are listening: `lsof -i :50051`

### Issue: "Process not found in config"

**Solution:**
- Verify config file path: `config/single_host.json`
- Check process ID is A, B, C, D, E, or F
- Verify config file has correct structure

### Issue: "ModuleNotFoundError: No module named 'grpc'"

**Solution:**
```bash
source ../.venv/bin/activate
pip install -r ../requirements.txt
```

### Issue: Requests failing

**Solution:**
- Check all processes are running
- Verify network connectivity (all on localhost)
- Check logs for errors: `grep -i error logs/*.log`
- Verify config file is correct

---

## Expected Test Results Summary

| Test | Expected Result |
|------|----------------|
| Basic Test | ✅ All 6 processes respond, correct forwarding |
| Load Test (100 sequential) | ✅ 100% success, reasonable latency |
| Load Test (100 concurrent) | ✅ 100% success, higher throughput |
| Queue Status | ✅ Queue size tracked correctly |
| Role-Based Forwarding | ✅ Leader → Team Leaders → Workers |
| Capacity Limits | ✅ Requests rejected when at capacity |
| Loop Prevention | ✅ No duplicate nodes in hops |
| Clean Shutdown | ✅ All processes stop cleanly |

---

## Performance Benchmarks (Expected)

For 100 requests on localhost:

- **Sequential:**
  - Total Time: ~5-15 seconds
  - Throughput: ~7-20 requests/second
  - Average Latency: ~50-150 ms

- **Concurrent:**
  - Total Time: ~2-5 seconds
  - Throughput: ~20-50 requests/second
  - Average Latency: ~100-300 ms

*Note: Actual values depend on system performance*

---

## Quick Test Checklist

- [ ] All 6 processes start successfully
- [ ] Single request works end-to-end
- [ ] 100 sequential requests complete
- [ ] 100 concurrent requests complete
- [ ] Queue status can be checked
- [ ] Role-based forwarding works correctly
- [ ] Loop prevention works
- [ ] Capacity limits enforced
- [ ] Clean shutdown works
- [ ] Performance metrics are reasonable

---

## Next Steps After Testing

1. Review `performance_results.json` for detailed metrics
2. Check logs for any errors or warnings
3. Verify queue behavior matches expectations
4. Test with different request patterns
5. Test on multiple hosts (if available)


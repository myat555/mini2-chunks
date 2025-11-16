#!/usr/bin/env python3
"""
Debug script to trace why team leader E isn't forwarding to workers F and D.
"""

import json
import sys
from overlay_core import OverlayConfig

def debug_team_leader_e():
    """Debug team leader E's forwarding logic."""
    config = OverlayConfig("configs/two_hosts_config.json")
    process_e = config.get("E")
    
    print("="*70)
    print("DEBUGGING TEAM LEADER E FORWARDING")
    print("="*70)
    print(f"\nProcess E Configuration:")
    print(f"  ID: {process_e.id}")
    print(f"  Role: {process_e.role}")
    print(f"  Team: {process_e.team}")
    print(f"  Neighbors (raw): {process_e.neighbors}")
    
    # Get all neighbors
    all_neighbors = config.neighbors_of("E")
    print(f"\nAll Neighbors of E:")
    for n in all_neighbors:
        print(f"  - {n.id}: role={n.role}, team={n.team}")
    
    # Simulate _select_forward_targets for E
    print(f"\nSimulating _select_forward_targets() for E:")
    neighbors = all_neighbors
    if not neighbors:
        print("  ERROR: No neighbors found!")
        return
    
    # E is team_leader, so check the logic
    if process_e.role == "team_leader":
        own_team_workers = [
            n for n in neighbors 
            if n.team.lower() == process_e.team.lower() and n.role == "worker"
        ]
        print(f"  Own team workers (team={process_e.team}, role=worker):")
        if own_team_workers:
            for w in own_team_workers:
                print(f"    - {w.id}: team={w.team}, role={w.role}")
            print(f"  Selected targets: {[n.id for n in own_team_workers]}")
        else:
            print("    - NONE FOUND!")
            cross_team_workers = [n for n in neighbors if n.role == "worker"]
            print(f"  Fallback to cross-team workers: {[n.id for n in cross_team_workers]}")
    
    # Check allocations
    if own_team_workers:
        total_limit = 1000  # Example: E gets 1000 from leader A
        neighbor_count = len(own_team_workers)
        base = max(1, total_limit // neighbor_count)
        allocations = [base for _ in range(neighbor_count)]
        remainder = total_limit - base * neighbor_count
        idx = 0
        while remainder > 0:
            allocations[idx % neighbor_count] += 1
            remainder -= 1
            idx += 1
        
        print(f"\nAllocation for {neighbor_count} workers (total_limit={total_limit}):")
        for worker, allocation in zip(own_team_workers, allocations):
            print(f"  {worker.id}: {allocation} records")
    
    # Check what leader A sends to E
    print(f"\nLeader A's perspective:")
    process_a = config.get("A")
    a_neighbors = config.neighbors_of("A")
    team_leaders = [n for n in a_neighbors if n.role == "team_leader"]
    print(f"  Team leaders A forwards to: {[n.id for n in team_leaders]}")
    
    if process_e in team_leaders:
        total_limit = 2000  # Example query limit
        neighbor_count = len(team_leaders)
        base = max(1, total_limit // neighbor_count)
        allocations = [base for _ in range(neighbor_count)]
        remainder = total_limit - base * neighbor_count
        idx = 0
        while remainder > 0:
            allocations[idx % neighbor_count] += 1
            remainder -= 1
            idx += 1
        
        print(f"  Allocation from A to team leaders (total_limit={total_limit}):")
        for tl, allocation in zip(team_leaders, allocations):
            print(f"    {tl.id}: {allocation} records")
    
    # Check data distribution
    print(f"\nData Distribution (from benchmark):")
    print(f"  E (team_leader/pink): 420 files loaded")
    print(f"  F (worker/pink): 420 files loaded")
    print(f"  D (worker/pink): 156 files loaded")
    print(f"\n  Note: E has 420 files, which might allow it to satisfy")
    print(f"        queries locally without forwarding to F/D")
    
    print(f"\n" + "="*70)
    print("DIAGNOSIS")
    print("="*70)
    print("""
The forwarding logic appears correct - E should forward to F and D.

Possible issues:
1. E might be satisfying queries locally (420 files) and not forwarding
2. E might receive allocations but F/D return records quickly
3. E's forwarding might be happening but not logged
4. Hops list might prevent forwarding (loop detection)

Next step: Check actual logs from E during a benchmark run.
    """)

if __name__ == "__main__":
    try:
        debug_team_leader_e()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


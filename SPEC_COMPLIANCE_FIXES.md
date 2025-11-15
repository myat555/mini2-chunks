# Specification Compliance Fixes

## Issues Identified and Fixed

### Issue 1: Missing BD Overlay Edge
**Problem**: The configuration had D's neighbors as only `["E"]`, missing the required BD edge from the spec.

**Spec Requirement**: 
```
Overlay configuration of AB, BC, BD, AE, EF, and ED
```

**Fix**: Updated D's neighbors to `["B", "E"]` in both `configs/two_hosts_config.json` and `configs/one_host_config.json`.

### Issue 2: Leaders/Team Leaders Not Acting as Workers
**Problem**: Leaders (A) and team leaders (B, E) were configured as pure routers with no data.

**Spec Requirement**: 
```
"Leaders, team leaders, and workers all can act as workers."
```

**Fix**: 
1. Added `date_bounds` to all processes:
   - A (leader): `20200810-20200812` (3 days)
   - B (team_leader): `20200813-20200815` (3 days)
   - E (team_leader): `20200821-20200823` (3 days)
   - C (worker): `20200816-20200820` (5 days)
   - D (worker): `20200824-20200905` (13 days)
   - F (worker): `20200906-20200924` (19 days)

2. Updated `overlay_core/facade.py` to allow any process with `date_bounds` to load data, regardless of role.

## Updated Data Distribution

### Team Green (20200810-20200820)
- **A (Leader)**: 20200810-20200812 (3 days, ~36 files)
- **B (Team Leader)**: 20200813-20200815 (3 days, ~36 files)
- **C (Worker)**: 20200816-20200820 (5 days, ~60 files)

### Team Pink (20200821-20200924)
- **E (Team Leader)**: 20200821-20200823 (3 days, ~36 files)
- **D (Worker)**: 20200824-20200905 (13 days, ~156 files)
- **F (Worker)**: 20200906-20200924 (19 days, ~228 files)

## Overlay Topology (Now Compliant)

```
         A (Leader)
        / \
       B   E (Team Leaders)
      /|   |\
     C D   F D (Workers)
```

**Edges**: AB, BC, BD, AE, EF, ED ✓

## Testing Instructions

1. **Copy updated config to macOS**:
   ```bash
   scp configs/two_hosts_config.json myatbhonesan@10.0.0.26:~/Desktop/CMPE275/mini2-chunks/configs/
   ```

2. **Restart all nodes**:
   - Windows: Stop existing processes, run `scripts\start_two_hosts_windows.bat`
   - macOS: `pkill -f 'python.*node.py'`, then `bash scripts/start_two_hosts_macos.sh`

3. **Run benchmark**:
   ```bash
   scripts\run_benchmark_two_hosts_windows.bat
   ```

4. **Expected Results**:
   - All 6 processes should show `Files > 0`
   - All processes should show `AvgTime > 0` (indicating they processed queries)
   - Workload should be distributed across all nodes
   - BD edge should be utilized in routing

## Compliance Summary

| Requirement | Status |
|-------------|--------|
| Overlay edges: AB, BC, BD, AE, EF, ED | ✓ Fixed |
| Host distribution: 1:{A,B,D}, 2:{C,E,F} | ✓ Already compliant |
| Teams: Green:{A,B,C}, Pink:{D,E,F} | ✓ Already compliant |
| Leaders/team leaders can act as workers | ✓ Fixed |
| Non-overlapping data per team | ✓ Already compliant |
| Configuration-driven (not hardcoded) | ✓ Already compliant |
| gRPC communication | ✓ Already compliant |
| Only A replies to client | ✓ Already compliant |


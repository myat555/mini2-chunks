#!/usr/bin/env python3
"""
Verification script to confirm data is being loaded and accessible.
"""

import sys
import os

sys.path.append(os.path.dirname(__file__))

from overlay_core.data_store import DataStore
from overlay_core.config import OverlayConfig


def verify_data_loading(config_file: str = "one_host_config.json"):
    """Verify that all processes can load their assigned data."""
    print("=" * 80)
    print("DATA LOADING VERIFICATION")
    print("=" * 80)
    
    config = OverlayConfig(config_file)
    all_loaded = True
    
    for process_id, process in config.all_processes().items():
        print(f"\nProcess {process_id} ({process.role}, Team: {process.team}):")
        
        # Leader does not load data - it only coordinates
        if process.role == "leader":
            print(f"  Role: Leader (no data loaded - coordinates queries only)")
            continue
            
        try:
            store = DataStore(process.id, process.team)
            stats = store.stats()
            print(f"  Files loaded: {stats['files']}")
            print(f"  Records loaded: {stats['records']}")
            
            if stats['records'] == 0:
                print(f"  WARNING: No records loaded for {process_id}!")
                all_loaded = False
            else:
                # Test a query
                test_results = store.query({"parameter": "PM2.5", "limit": 5})
                print(f"  Test query (PM2.5): {len(test_results)} records")
                if test_results:
                    sample = test_results[0]
                    print(f"    Sample record: parameter={sample.get('parameter')}, "
                          f"value={sample.get('value')}, date={sample.get('date')}")
                
        except Exception as e:
            print(f"  ERROR: Failed to load data: {e}")
            all_loaded = False
    
    print("\n" + "=" * 80)
    if all_loaded:
        print("SUCCESS: All processes loaded data successfully!")
    else:
        print("FAILURE: Some processes failed to load data.")
    print("=" * 80)
    
    return all_loaded


if __name__ == "__main__":
    config_file = sys.argv[1] if len(sys.argv) > 1 else "one_host_config.json"
    success = verify_data_loading(config_file)
    sys.exit(0 if success else 1)


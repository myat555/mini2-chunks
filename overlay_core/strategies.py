"""Strategy pattern implementations for forwarding, chunking, and fairness."""

import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from concurrent import futures
from typing import Dict, List, Optional

import overlay_pb2

from .config import ProcessSpec


class ForwardingStrategy(ABC):
    """Base class for forwarding strategies."""

    @abstractmethod
    def forward_async(
        self,
        neighbors: List[ProcessSpec],
        request_func,
        filters: Dict,
        hops: List[str],
        client_id: Optional[str],
        remaining: int,
    ) -> List[Dict]:
        """Forward requests to neighbors and return aggregated results."""
        pass

    @abstractmethod
    def forward_blocking(
        self,
        neighbors: List[ProcessSpec],
        request_func,
        filters: Dict,
        hops: List[str],
        client_id: Optional[str],
        remaining: int,
    ) -> List[Dict]:
        """Forward requests sequentially (blocking)."""
        pass


class RoundRobinForwarding(ForwardingStrategy):
    """Sequential round-robin forwarding (blocking)."""

    def __init__(self, start_index: int = 0):
        self._lock = threading.Lock()
        self._index = start_index

    def forward_async(
        self,
        neighbors: List[ProcessSpec],
        request_func,
        filters: Dict,
        hops: List[str],
        client_id: Optional[str],
        remaining: int,
    ) -> List[Dict]:
        # For round-robin, async means parallel execution but still round-robin order
        return self._forward_parallel(neighbors, request_func, filters, hops, client_id, remaining)

    def forward_blocking(
        self,
        neighbors: List[ProcessSpec],
        request_func,
        filters: Dict,
        hops: List[str],
        client_id: Optional[str],
        remaining: int,
    ) -> List[Dict]:
        """Sequential round-robin forwarding."""
        aggregated = []
        
        with self._lock:
            start = self._index % len(neighbors) if neighbors else 0
            self._index += 1
        
        ordered_neighbors = neighbors[start:] + neighbors[:start] if neighbors else []
        
        for neighbor in ordered_neighbors:
            if neighbor.id in hops:
                continue
            if remaining <= 0:
                break
            
            try:
                rows = request_func(neighbor, filters, hops, client_id, remaining)
                aggregated.extend(rows)
                remaining -= len(rows)
            except Exception as exc:
                print(f"[RoundRobin] Failed forwarding to {neighbor.id}: {exc}")
        
        return aggregated

    def _forward_parallel(
        self,
        neighbors: List[ProcessSpec],
        request_func,
        filters: Dict,
        hops: List[str],
        client_id: Optional[str],
        remaining: int,
    ) -> List[Dict]:
        """Parallel forwarding with round-robin order preservation."""
        if not neighbors:
            return []
        
        with self._lock:
            start = self._index % len(neighbors)
            self._index += 1
        ordered_neighbors = neighbors[start:] + neighbors[:start]
        
        # Filter out neighbors already in hops
        valid_neighbors = [n for n in ordered_neighbors if n.id not in hops]
        if not valid_neighbors:
            return []
        
        # Use threading for parallel execution
        results_lock = threading.Lock()
        aggregated = []
        remaining_lock = threading.Lock()
        remaining_count = [remaining]
        
        def worker(neighbor: ProcessSpec):
            try:
                with remaining_lock:
                    local_remaining = remaining_count[0]
                    if local_remaining <= 0:
                        return
                
                rows = request_func(neighbor, filters, hops, client_id, local_remaining)
                
                with results_lock:
                    aggregated.extend(rows)
                    with remaining_lock:
                        remaining_count[0] -= len(rows)
            except Exception as exc:
                print(f"[RoundRobin-Parallel] Failed forwarding to {neighbor.id}: {exc}")
        
        threads = []
        for neighbor in valid_neighbors:
            if remaining_count[0] <= 0:
                break
            thread = threading.Thread(target=worker, args=(neighbor,))
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()
        
        return aggregated[:remaining]


class ParallelForwarding(ForwardingStrategy):
    """Parallel forwarding to all neighbors simultaneously (async)."""

    def forward_async(
        self,
        neighbors: List[ProcessSpec],
        request_func,
        filters: Dict,
        hops: List[str],
        client_id: Optional[str],
        remaining: int,
    ) -> List[Dict]:
        """Forward to all neighbors in parallel."""
        valid_neighbors = [n for n in neighbors if n.id not in hops]
        if not valid_neighbors:
            return []
        
        results_lock = threading.Lock()
        aggregated = []
        remaining_lock = threading.Lock()
        remaining_count = [remaining]
        
        def worker(neighbor: ProcessSpec):
            try:
                with remaining_lock:
                    local_remaining = remaining_count[0]
                    if local_remaining <= 0:
                        return
                
                rows = request_func(neighbor, filters, hops, client_id, local_remaining)
                
                with results_lock:
                    aggregated.extend(rows)
                    with remaining_lock:
                        remaining_count[0] -= len(rows)
            except Exception as exc:
                print(f"[Parallel] Failed forwarding to {neighbor.id}: {exc}")
        
        threads = []
        for neighbor in valid_neighbors:
            if remaining_count[0] <= 0:
                break
            thread = threading.Thread(target=worker, args=(neighbor,))
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()
        
        return aggregated[:remaining]

    def forward_blocking(
        self,
        neighbors: List[ProcessSpec],
        request_func,
        filters: Dict,
        hops: List[str],
        client_id: Optional[str],
        remaining: int,
    ) -> List[Dict]:
        """Fall back to sequential for blocking mode."""
        aggregated = []
        for neighbor in neighbors:
            if neighbor.id in hops:
                continue
            if remaining <= 0:
                break
            try:
                rows = request_func(neighbor, filters, hops, client_id, remaining)
                aggregated.extend(rows)
                remaining -= len(rows)
            except Exception as exc:
                print(f"[Parallel-Blocking] Failed forwarding to {neighbor.id}: {exc}")
        return aggregated


class ChunkingStrategy(ABC):
    """Base class for chunking strategies."""

    @abstractmethod
    def compute_chunk_size(self, total_records: int, filters: Dict) -> int:
        """Compute chunk size based on total records and filters."""
        pass


class FixedChunking(ChunkingStrategy):
    """Fixed chunk size strategy."""

    def __init__(self, chunk_size: int = 200):
        self.chunk_size = chunk_size

    def compute_chunk_size(self, total_records: int, filters: Dict) -> int:
        return self.chunk_size


class AdaptiveChunking(ChunkingStrategy):
    """Adaptive chunk size based on result size."""

    def __init__(self, base_size: int = 200, max_size: int = 1000):
        self.base_size = base_size
        self.max_size = max_size

    def compute_chunk_size(self, total_records: int, filters: Dict) -> int:
        if total_records <= 100:
            return min(50, total_records)
        elif total_records <= 500:
            return self.base_size
        elif total_records <= 2000:
            return min(self.base_size * 2, self.max_size)
        else:
            return self.max_size


class FairnessStrategy(ABC):
    """Base class for fairness strategies."""

    @abstractmethod
    def should_admit(self, team: Optional[str], active_per_team: Dict[str, int], max_active: int, per_team_limit: int) -> bool:
        """Determine if request should be admitted."""
        pass


class StrictPerTeamFairness(FairnessStrategy):
    """Strict per-team limits."""

    def should_admit(
        self,
        team: Optional[str],
        active_per_team: Dict[str, int],
        max_active: int,
        per_team_limit: int,
    ) -> bool:
        total_active = sum(active_per_team.values())
        if total_active >= max_active:
            return False
        
        if team:
            team_key = team.lower()
            if active_per_team.get(team_key, 0) >= per_team_limit:
                return False
        
        return True


class WeightedFairness(FairnessStrategy):
    """Weighted fairness based on team load."""

    def should_admit(
        self,
        team: Optional[str],
        active_per_team: Dict[str, int],
        max_active: int,
        per_team_limit: int,
    ) -> bool:
        total_active = sum(active_per_team.values())
        if total_active >= max_active:
            return False
        
        if team:
            team_key = team.lower()
            team_active = active_per_team.get(team_key, 0)
            # Allow slightly over limit if other teams are underutilized
            other_teams_total = sum(v for k, v in active_per_team.items() if k != team_key)
            if team_active >= per_team_limit and other_teams_total > per_team_limit * 0.8:
                return False
        
        return True


class HybridFairness(FairnessStrategy):
    """Hybrid: Strict when high load, weighted when low load."""

    def __init__(self, high_load_threshold: float = 0.8):
        self.high_load_threshold = high_load_threshold
        self._strict = StrictPerTeamFairness()
        self._weighted = WeightedFairness()

    def should_admit(
        self,
        team: Optional[str],
        active_per_team: Dict[str, int],
        max_active: int,
        per_team_limit: int,
    ) -> bool:
        total_active = sum(active_per_team.values())
        load_ratio = total_active / max_active if max_active > 0 else 0
        
        if load_ratio >= self.high_load_threshold:
            return self._strict.should_admit(team, active_per_team, max_active, per_team_limit)
        else:
            return self._weighted.should_admit(team, active_per_team, max_active, per_team_limit)


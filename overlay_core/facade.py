import json
import threading
import time
import uuid
from collections import deque
from typing import Dict, List, Optional

import overlay_pb2

from .config import OverlayConfig, ProcessSpec
from .data_store import DataStore
from .metrics import MetricsTracker
from .proxies import NeighborRegistry
from .request_controller import RequestAdmissionController
from .result_cache import ChunkedResult, ResultCache
from .strategies import (
    ForwardingStrategy,
    RoundRobinForwarding,
    ParallelForwarding,
    CapacityBasedForwarding,
    ChunkingStrategy,
    FixedChunking,
    AdaptiveChunking,
    QueryBasedChunking,
    FairnessStrategy,
    StrictPerTeamFairness,
    WeightedFairness,
    HybridFairness,
)


class QueryOrchestrator:
    """
    Orchestrates query execution across the overlay network.
    Coordinates caching, fairness controls, and neighbor communication.
    """

    def __init__(
        self,
        config: OverlayConfig,
        process: ProcessSpec,
        dataset_root: str,
        chunk_size: int = 200,
        result_ttl: int = 300,
        default_limit: int = 2000,
        forwarding_strategy: Optional[str] = "round_robin",
        use_async_forwarding: bool = False,
        chunking_strategy: Optional[str] = "fixed",
        fairness_strategy: Optional[str] = "strict",
    ):
        self._config = config
        self._process = process
        # Leaders and team leaders can act as workers if they have date_bounds configured
        # This follows the spec: "Leaders, team leaders, and workers all can act as workers"
        if process.date_bounds and len(process.date_bounds) == 2:
            bounds = (process.date_bounds[0], process.date_bounds[1])
            self._data_store = DataStore(
                process.id,
                process.team,
                dataset_root=dataset_root,
                date_bounds=bounds,
            )
        else:
            self._data_store = None
        
        # Initialize strategies
        self._forwarding_strategy = self._create_forwarding_strategy(forwarding_strategy)
        self._use_async_forwarding = use_async_forwarding
        self._chunking_strategy = self._create_chunking_strategy(chunking_strategy, chunk_size)
        fairness = self._create_fairness_strategy(fairness_strategy)
        
        self._cache = ResultCache(ttl_seconds=result_ttl)
        self._admission = RequestAdmissionController(fairness_strategy=fairness)
        self._metrics = MetricsTracker()
        self._neighbor_registry = NeighborRegistry(config, process.id)
        self._chunk_size = chunk_size  # Default/initial chunk size
        self._default_limit = default_limit
        self._rr_lock = threading.Lock()
        self._rr_index = 0
        self._log_buffer = deque(maxlen=50)  # Store last 50 log lines
        self._log_lock = threading.Lock()

    def _compute_leader_allocations(self, neighbor_count: int, total_limit: int) -> List[int]:
        if neighbor_count <= 0:
            return []
        total_limit = max(1, int(total_limit))
        base = max(1, total_limit // neighbor_count)
        allocations = [base for _ in range(neighbor_count)]
        remainder = total_limit - base * neighbor_count
        idx = 0
        while remainder > 0:
            allocations[idx % neighbor_count] += 1
            remainder -= 1
            idx += 1
        return allocations

    def execute_query(self, request: overlay_pb2.QueryRequest) -> overlay_pb2.QueryResponse:
        hops = list(request.hops)
        if self._process.id in hops:
            return overlay_pb2.QueryResponse(
                uid="",
                total_chunks=0,
                total_records=0,
                hops=hops,
                status="loop_detected",
            )
        hops.append(self._process.id)

        try:
            filters = self._parse_filters(request.query_params)
        except ValueError as exc:
            return overlay_pb2.QueryResponse(
                uid="",
                total_chunks=0,
                total_records=0,
                hops=hops,
                status=f"invalid_query:{exc}",
            )

        uid = str(uuid.uuid4())
        target_team = filters.get("team") or self._process.team

        if not self._admission.admit(uid, target_team):
            return overlay_pb2.QueryResponse(
                uid="",
                total_chunks=0,
                total_records=0,
                hops=hops,
                status="rejected",
            )

        start = time.time()
        try:
            records = self._collect_records(filters, hops, request.client_id, request.query_type)
            
            # Compute dynamic chunk size based on strategy
            dynamic_chunk_size = self._chunking_strategy.compute_chunk_size(len(records), filters)
            
            chunked = ChunkedResult(
                uid=uid,
                records=records,
                chunk_size=dynamic_chunk_size,
                ttl_seconds=self._cache.ttl,
                metadata={
                    "process": self._process.id,
                    "team": self._process.team,
                    "filters": filters,
                    "strategy": {
                        "forwarding": self._forwarding_strategy.__class__.__name__,
                        "async": self._use_async_forwarding,
                        "chunking": self._chunking_strategy.__class__.__name__,
                    },
                },
            )
            self._cache.store(chunked)
            duration_ms = (time.time() - start) * 1000
            self._metrics.record_completion(duration_ms)
            
            filter_summary = f"param={filters.get('parameter', 'any')}"
            if 'min_value' in filters or 'max_value' in filters:
                filter_summary += f", value=[{filters.get('min_value', '')}, {filters.get('max_value', '')}]"
            
            if self._process.role == "leader":
                log_msg = f"[Orchestrator] {self._process.id} coordinated query {uid[:8]}: aggregated {len(records)} records from team leaders, {duration_ms:.1f}ms, filters={{{filter_summary}}}"
            else:
                log_msg = f"[Orchestrator] {self._process.id} query {uid[:8]}: {len(records)} records, {duration_ms:.1f}ms, filters={{{filter_summary}}}"
            print(log_msg, flush=True)
            self._add_log(log_msg)

            return overlay_pb2.QueryResponse(
                uid=uid,
                total_chunks=chunked.total_chunks,
                total_records=chunked.total_records,
                hops=hops,
                status="ready",
            )
        finally:
            self._admission.release(uid)

    def get_chunk(self, uid: str, chunk_index: int) -> overlay_pb2.ChunkResponse:
        result = self._cache.get(uid)
        if not result:
            return overlay_pb2.ChunkResponse(
                uid=uid,
                chunk_index=chunk_index,
                total_chunks=0,
                data="[]",
                is_last=True,
                status="not_found",
            )

        chunk = result.get_chunk(chunk_index)
        if not chunk:
            return overlay_pb2.ChunkResponse(
                uid=uid,
                chunk_index=chunk_index,
                total_chunks=result.total_chunks,
                data="[]",
                is_last=True,
                status="out_of_range",
            )

        if chunk["is_last"]:
            self._cache.delete(uid)

        return overlay_pb2.ChunkResponse(
            uid=uid,
            chunk_index=chunk["chunk_index"],
            total_chunks=chunk["total_chunks"],
            data=json.dumps(chunk["data"]),
            is_last=chunk["is_last"],
            status="success",
        )

    def _add_log(self, message: str) -> None:
        """Add a log message to the buffer."""
        with self._log_lock:
            self._log_buffer.append(message)
    
    def _get_recent_logs(self, max_lines: int = 10) -> List[str]:
        """Get recent log lines from buffer."""
        with self._log_lock:
            return list(self._log_buffer)[-max_lines:]
    
    def build_metrics_response(self) -> overlay_pb2.MetricsResponse:
        stats = self._metrics.snapshot()
        admission = self._admission.snapshot()
        recent_logs = self._get_recent_logs(max_lines=10)
        return overlay_pb2.MetricsResponse(
            process_id=self._process.id,
            role=self._process.role,
            team=self._process.team,
            active_requests=admission["active"],
            max_capacity=self._admission.max_active,
            is_healthy=admission["rejections"] == 0,
            queue_size=len(self._cache),
            avg_processing_time_ms=float(stats["avg_ms"]),
            data_files_loaded=self._data_store.files_loaded if self._data_store else 0,
            forwarding_strategy=self._forwarding_strategy.__class__.__name__,
            async_forwarding=self._use_async_forwarding,
            chunking_strategy=self._chunking_strategy.__class__.__name__,
            fairness_strategy=self._admission._fairness.__class__.__name__,
            recent_logs=recent_logs,
        )

    def _parse_filters(self, raw_params: str) -> Dict[str, object]:
        filters = json.loads(raw_params) if raw_params else {}
        if not isinstance(filters, dict):
            raise ValueError("query_params must decode into a JSON object.")
        limit = filters.get("limit") or self._default_limit
        filters["limit"] = max(1, min(int(limit), self._default_limit))
        return filters

    def _collect_records(
        self,
        filters: Dict[str, object],
        hops: List[str],
        client_id: Optional[str],
        query_type: Optional[str],
    ) -> List[Dict[str, object]]:
        aggregated: List[Dict[str, object]] = []
        remaining = filters.get("limit", self._default_limit)

        # Only query local data if this process has a data store (not leader)
        if self._data_store is not None:
            local_rows = self._data_store.query(filters, limit=remaining)
            if local_rows:
                log_msg = f"[Orchestrator] {self._process.id} local query: {len(local_rows)} records from {self._data_store.records_loaded} total"
                print(log_msg, flush=True)
                self._add_log(log_msg)
            aggregated.extend(local_rows)
            remaining -= len(local_rows)
            if remaining <= 0:
                return aggregated[: filters["limit"]]

        neighbors = self._select_forward_targets()
        if neighbors:
            total_limit = max(1, filters.get("limit", self._default_limit))
            if self._process.role in ("leader", "team_leader"):
                allocations = self._compute_leader_allocations(len(neighbors), total_limit)
                team_hint = (
                    None if self._process.role == "leader" else self._process.team
                )
                for neighbor, allocation in zip(neighbors, allocations):
                    remote_rows = self._request_neighbor_records(
                        neighbor,
                        filters,
                        hops,
                        client_id,
                        allocation,
                        team_hint=team_hint or neighbor.team,
                    )
                    aggregated.extend(remote_rows)
            else:
                if self._use_async_forwarding:
                    remote_rows = self._forwarding_strategy.forward_async(
                        neighbors,
                        self._request_neighbor_records,
                        filters,
                        hops,
                        client_id,
                        remaining,
                    )
                else:
                    remote_rows = self._forwarding_strategy.forward_blocking(
                        neighbors,
                        self._request_neighbor_records,
                        filters,
                        hops,
                        client_id,
                        remaining,
                    )
                aggregated.extend(remote_rows)

        return aggregated[: filters["limit"]]

    def _select_forward_targets(self) -> List[ProcessSpec]:
        neighbors = self._config.neighbors_of(self._process.id)
        if not neighbors:
            return []

        if self._process.role == "leader":
            neighbors = [n for n in neighbors if n.role == "team_leader"]
        elif self._process.role == "team_leader":
            neighbors = [n for n in neighbors if n.team == self._process.team and n.role == "worker"]
        else:
            neighbors = []

        if not neighbors:
            return []

        with self._rr_lock:
            start = self._rr_index % len(neighbors)
            self._rr_index += 1
        return neighbors[start:] + neighbors[:start]

    def _request_neighbor_records(
        self,
        neighbor: ProcessSpec,
        filters: Dict[str, object],
        hops: List[str],
        client_id: Optional[str],
        limit: int,
        team_hint: Optional[str] = None,
    ) -> List[Dict[str, object]]:
        client = self._neighbor_registry.for_neighbor(neighbor.id)

        forward_filters = dict(filters)
        forward_filters["limit"] = max(1, int(limit))
        if team_hint:
            forward_filters["team"] = team_hint
        forward_request = overlay_pb2.QueryRequest(
            query_type="filter",
            query_params=json.dumps(forward_filters),
            hops=hops,
            client_id=client_id or self._process.id,
        )

        log_msg = f"[Orchestrator] {self._process.id} forwarding to {neighbor.id} ({neighbor.role}/{neighbor.team}), remaining={forward_filters['limit']}"
        print(log_msg, flush=True)
        self._add_log(log_msg)

        try:
            response = client.query(forward_request)
        except Exception as exc:
            log_msg = f"[Orchestrator] Failed forwarding to {neighbor.id} ({neighbor.address}): {exc}"
            print(log_msg, flush=True)
            self._add_log(log_msg)
            return []

        if response.status != "ready" or not response.uid:
            return []

        return self._drain_remote_chunks(client, response.uid, response.total_chunks, forward_filters["limit"])

    @staticmethod
    def _safe_json_loads(payload: str) -> List[Dict[str, object]]:
        try:
            data = json.loads(payload) if payload else []
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass
        return []

    def _drain_remote_chunks(
        self,
        client,
        remote_uid: str,
        total_chunks: int,
        remaining: int,
    ) -> List[Dict[str, object]]:
        collected: List[Dict[str, object]] = []
        for idx in range(total_chunks):
            if remaining <= 0:
                break
            chunk_resp = client.get_chunk(remote_uid, idx)
            if chunk_resp.status != "success":
                break
            rows = self._safe_json_loads(chunk_resp.data)
            for row in rows:
                collected.append(row)
                remaining -= 1
                if remaining <= 0:
                    break
            if chunk_resp.is_last:
                break
        return collected

    def _create_forwarding_strategy(self, strategy_name: str) -> ForwardingStrategy:
        """Create forwarding strategy instance."""
        strategy_name = (strategy_name or "round_robin").lower()
        if strategy_name == "parallel":
            return ParallelForwarding()
        elif strategy_name == "capacity":
            # Capacity-based needs metrics access - simplified for now
            return CapacityBasedForwarding()
        else:  # round_robin (default)
            return RoundRobinForwarding()

    def _create_chunking_strategy(self, strategy_name: str, base_size: int) -> ChunkingStrategy:
        """Create chunking strategy instance."""
        strategy_name = (strategy_name or "fixed").lower()
        if strategy_name == "adaptive":
            return AdaptiveChunking(base_size=base_size)
        elif strategy_name == "query_based":
            return QueryBasedChunking(base_size=base_size)
        else:  # fixed (default)
            return FixedChunking(chunk_size=base_size)

    def _create_fairness_strategy(self, strategy_name: str) -> FairnessStrategy:
        """Create fairness strategy instance."""
        strategy_name = (strategy_name or "strict").lower()
        if strategy_name == "weighted":
            return WeightedFairness()
        elif strategy_name == "hybrid":
            return HybridFairness()
        else:  # strict (default)
            return StrictPerTeamFairness()


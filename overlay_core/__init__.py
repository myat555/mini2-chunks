"""Shared infrastructure for overlay nodes (facades, proxies, data access)."""

from .config import ProcessSpec, OverlayConfig
from .data_store import DataStore
from .result_cache import ResultCache, ChunkedResult
from .request_controller import RequestAdmissionController
from .metrics import MetricsTracker
from .proxies import ProxyRegistry
from .facade import OverlayFacade
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

__all__ = [
    "ProcessSpec",
    "OverlayConfig",
    "DataStore",
    "ResultCache",
    "ChunkedResult",
    "RequestAdmissionController",
    "MetricsTracker",
    "ProxyRegistry",
    "OverlayFacade",
    "ForwardingStrategy",
    "RoundRobinForwarding",
    "ParallelForwarding",
    "CapacityBasedForwarding",
    "ChunkingStrategy",
    "FixedChunking",
    "AdaptiveChunking",
    "QueryBasedChunking",
    "FairnessStrategy",
    "StrictPerTeamFairness",
    "WeightedFairness",
    "HybridFairness",
]


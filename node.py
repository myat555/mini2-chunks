import argparse
import os
import sys
from concurrent import futures

import grpc

# Ensure local imports resolve when executed from scripts directory.
sys.path.append(os.path.dirname(__file__))

import overlay_pb2
import overlay_pb2_grpc
from overlay_core import OverlayConfig, OverlayFacade


class OverlayService(overlay_pb2_grpc.OverlayNodeServicer):
    """Thin gRPC service that delegates behavior to OverlayFacade."""

    def __init__(self, facade: OverlayFacade):
        self._facade = facade

    def Query(self, request, context):  # pylint: disable=invalid-name
        return self._facade.execute_query(request)

    def GetChunk(self, request, context):  # pylint: disable=invalid-name
        return self._facade.get_chunk(request.uid, request.chunk_index)

    def GetMetrics(self, request, context):  # pylint: disable=invalid-name
        return self._facade.build_metrics_response()

    def Shutdown(self, request, context):  # pylint: disable=invalid-name
        return overlay_pb2.ShutdownResponse(status="noop")


def serve(config_path: str, process_id: str, dataset_root: str, chunk_size: int, ttl: int):
    config = OverlayConfig(config_path)
    process = config.get(process_id)
    facade = OverlayFacade(
        config=config,
        process=process,
        dataset_root=dataset_root,
        chunk_size=chunk_size,
        result_ttl=ttl,
    )

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=16))
    overlay_pb2_grpc.add_OverlayNodeServicer_to_server(OverlayService(facade), server)
    server.add_insecure_port(f"0.0.0.0:{process.port}")

    server.start()
    print(
        f"[Overlay] {process.id} ({process.role}/{process.team}) "
        f"listening on {process.host}:{process.port}, dataset={dataset_root}"
    )
    server.wait_for_termination()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start an overlay process.")
    parser.add_argument("config", help="Path to JSON overlay configuration.")
    parser.add_argument("process_id", help="Process identifier (e.g., A, B, C).")
    parser.add_argument(
        "--dataset-root",
        default="datasets/2020-fire/data",
        help="Root folder for dataset partitions.",
    )
    parser.add_argument("--chunk-size", type=int, default=200, help="Chunk size for responses.")
    parser.add_argument("--result-ttl", type=int, default=300, help="Seconds to retain query results.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    serve(args.config, args.process_id, args.dataset_root, args.chunk_size, args.result_ttl)
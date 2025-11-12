#!/bin/bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. overlay.proto
echo "Proto files generated: overlay_pb2.py, overlay_pb2_grpc.py"

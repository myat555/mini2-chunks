#!/bin/bash

# Minimal script to auto-generate Python gRPC code from all .proto files

set -e

for proto in overlay.proto; do
    echo "Generating Python code for $proto ..."
    python3 -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. $proto
done

echo "[✓] Python gRPC stubs created for all .proto files."

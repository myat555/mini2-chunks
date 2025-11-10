# mini2-chunks


## Run a virtual environment
`python -m venv .venv`

## Activate the virtual environment
- On Windows: `.venv\Scripts\activate`

- On macOS/Linux: `source .venv/bin/activate`

## Install dependencies
`pip install -r requirements.txt`

## To generate gRPC code from proto file using bash script (Make sure the generated code used is same for all client and servers by always building from same proto file)
```
chmod +x build_proto.sh
./build_proto.sh
```
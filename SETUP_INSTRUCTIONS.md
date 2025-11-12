# Setup Instructions - Step by Step

## ✅ Yes, you should create a virtual environment!

**Why?** Virtual environments keep your project's dependencies separate from other Python projects on your computer. This prevents conflicts and keeps things organized.

---

## Complete Setup Steps

### Step 1: Navigate to the Project Directory
Open a terminal and go to the project folder:
```bash
cd /Users/spartan/Documents/JohnGashCMPE285/workingproject/fromMatt/mini2-chunks
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv .venv
```
This creates a folder called `.venv` (you might not see it in Finder, but it's there).

**What this does:** Creates an isolated Python environment just for this project.

**Note:** On macOS, use `python3` instead of `python`. If `python3` doesn't work, check the troubleshooting section below.

### Step 3: Activate the Virtual Environment

**On macOS/Linux (your system):**
```bash
source .venv/bin/activate
```

**On Windows (if you ever use it):**
```bash
.venv\Scripts\activate
```

**How to know it's activated:** You'll see `(.venv)` at the beginning of your terminal prompt:
```
(.venv) your-computer:mini2-chunks yourname$
```

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

This installs:
- `grpcio` - The gRPC library for Python
- `grpcio-tools` - Tools to generate code from .proto files

**Expected output:**
```
Collecting grpcio
Collecting grpcio-tools
...
Successfully installed grpcio-X.X.X grpcio-tools-X.X.X
```

### Step 5: Verify Installation
```bash
pip list
```

You should see `grpcio` and `grpcio-tools` in the list.

---

## Important Notes

### ✅ Always Activate Before Working
**Every time you open a new terminal to work on this project:**
1. Navigate to the project: `cd /Users/spartan/Documents/JohnGashCMPE285/workingproject/fromMatt/mini2-chunks`
2. Activate: `source .venv/bin/activate`
3. Then run your Python scripts

### ✅ How to Deactivate
When you're done working:
```bash
deactivate
```
This removes `(.venv)` from your prompt and returns to your system Python.

### ✅ Multiple Terminals
If you need multiple terminals (like for running server + client):
- **Each terminal needs to activate the virtual environment separately**
- Activate in Terminal 1, Terminal 2, Terminal 3, etc.

---

## Quick Reference Commands

```bash
# Create virtual environment (do this ONCE)
python3 -m venv .venv

# Activate (do this EVERY TIME you open a new terminal)
source .venv/bin/activate

# Install dependencies (do this ONCE after creating venv)
pip install -r requirements.txt

# Deactivate when done
deactivate
```

---

## Troubleshooting

### "command not found: python"
**This is normal on macOS!** Use `python3` instead:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Most macOS systems have Python 3 installed as `python3`, not `python`. Always use `python3` for this project.

### "No module named 'grpc'"
This means:
1. Virtual environment is not activated, OR
2. Dependencies are not installed

**Solution:**
```bash
source .venv/bin/activate  # Make sure it's activated
pip install -r requirements.txt  # Install dependencies
```

### "Permission denied"
If you get permission errors, you might be using system Python. Always use the virtual environment:
```bash
source .venv/bin/activate
```

---

## What's Next?

After setup, you can:

1. **Generate gRPC code:**
   ```bash
   chmod +x build_proto.sh
   ./build_proto.sh
   ```

2. **Test the ping-pong example:**
   - Terminal 1: `python server.py`
   - Terminal 2: `python client.py`

3. **Test the overlay network:**
   - See `SINGLE_MACHINE_TESTING.md` for details

---

## Summary

✅ **Do this once:**
- `python3 -m venv .venv`
- `source .venv/bin/activate`
- `pip install -r requirements.txt`

✅ **Do this every time you work:**
- `source .venv/bin/activate` (in each terminal you use)

✅ **Then you're ready to run the code!**


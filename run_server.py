#!/usr/bin/env python3
"""Run server and keep it alive."""
import subprocess
import sys
import time
import os

os.chdir(r"c:\Users\mouav\OneDrive\Desktop\FINAL3")

proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "dataverse_backend.app.main:app", 
     "--host", "0.0.0.0", "--port", "8000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=False,
    bufsize=1
)

# Keep server running
print("Server started. Press Ctrl+C to stop.", file=sys.stderr)
try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nStopping server...", file=sys.stderr)
    proc.terminate()
    proc.wait(timeout=5)

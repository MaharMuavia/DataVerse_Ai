#!/usr/bin/env python3
"""Run server and keep it alive."""
import subprocess
import sys
import time
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "dataverse_backend"
os.chdir(REPO_ROOT)

if not BACKEND_DIR.exists():
    raise FileNotFoundError(f"Expected backend directory at: {BACKEND_DIR}")

proc = subprocess.Popen(
    [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--app-dir",
        str(BACKEND_DIR),
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ],
    cwd=str(REPO_ROOT),
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

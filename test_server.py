#!/usr/bin/env python3
"""Simple test of the server."""
import asyncio
import sys
import time
import subprocess
import signal
from pathlib import Path

async def test_server():
    # Start server in a subprocess
    import os
    os.chdir(r"c:\Users\mouav\OneDrive\Desktop\FINAL3")
    
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "dataverse_backend.app.main:app", 
         "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Wait for server to start
    await asyncio.sleep(3)
    
    try:
        import requests
        response = requests.get("http://localhost:8000/api/health")
        print(f"Health check: {response.status_code}")
        print(f"Response: {response.json()}")
        return True
    except Exception as e:
        print(f"Request failed: {e}")
        return False
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except:
            proc.kill()

if __name__ == "__main__":
    result = asyncio.run(test_server())
    sys.exit(0 if result else 1)

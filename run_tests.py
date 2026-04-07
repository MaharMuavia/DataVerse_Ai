#!/usr/bin/env python
"""Simple test runner script without coverage plugins."""

import subprocess
import sys

# Try to run pytest with just basic options
cmd = [
    sys.executable, 
    "-m", 
    "pytest", 
    "tests/test_simple.py",
    "-v",
    "--tb=short"
]

print(f"Running: {' '.join(cmd)}")
result = subprocess.run(cmd, cwd="dataverse_backend")
sys.exit(result.returncode)

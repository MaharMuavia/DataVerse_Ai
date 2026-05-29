#!/usr/bin/env python
"""Test runner that writes output to file."""

import subprocess
import sys
import os

os.chdir("dataverse_backend")

# Run pytest and capture output
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
    capture_output=True,
    text=True
)

# Write to file
with open("../test_results.txt", "w") as f:
    f.write("STDOUT:\n")
    f.write(result.stdout)
    f.write("\n\nSTDERR:\n")
    f.write(result.stderr)
    f.write(f"\n\nReturn Code: {result.returncode}\n")

print("Test results written to test_results.txt")
sys.exit(result.returncode)

import subprocess
import os
import sys

# 1. Read secrets file from your laptop
with open("secrets.env") as f:
    for line in f:
        if "=" in line:
            key, value = line.strip().split("=", 1)
            os.environ[key] = value
            print(f"Set environment variable: {key}={value}")

def run(cmd):
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        sys.exit(result.returncode)

run(["idf.py", "build"])
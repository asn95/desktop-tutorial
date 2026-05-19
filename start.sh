#!/bin/bash
cd /Users/auzasyamil/capstone1
echo "Starting C3MR backend..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | tee /tmp/c3mr_server.log

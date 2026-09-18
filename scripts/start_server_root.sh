#!/bin/bash
# Root helper
cd /opt/omen-linux/backend
./venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000

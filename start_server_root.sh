#!/bin/bash
# Root helper
cd /opt/omen-linux/backend
./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000

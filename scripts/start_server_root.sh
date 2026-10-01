#!/bin/bash
# Run by launch.sh through pkexec: the backend needs root for /dev/mem.
cd /opt/omen-linux/backend || exit 1
exec ./venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000

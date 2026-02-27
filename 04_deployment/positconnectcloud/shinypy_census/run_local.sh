#!/usr/bin/env bash
# run_local.sh — Run the Census + AI Shiny app locally with python3.
# Usage: ./run_local.sh   or   bash run_local.sh
# Stop any existing run with Ctrl+C. If port is in use: kill the process or set PORT=8888 ./run_local.sh

set -e
cd "$(dirname "$0")"
PORT="${PORT:-8888}"

echo "Using Python: $(python3 -c 'import sys; print(sys.executable)')"
echo "Starting app at http://127.0.0.1:$PORT"
echo "(If port is in use, run: lsof -i :$PORT  then  kill <PID>  or use PORT=9999 ./run_local.sh)"
python3 -m shiny run app.py --port "$PORT"

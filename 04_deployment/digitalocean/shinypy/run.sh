#!/bin/bash
# Use PORT from environment (DigitalOcean App Platform) or default 8000
set -e
exec shiny run app.py --host 0.0.0.0 --port "${PORT:-8000}"

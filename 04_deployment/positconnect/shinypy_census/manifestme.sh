#!/usr/bin/env bash
# manifestme.sh
# Build manifest.json for this Shiny for Python app (app.py) for Posit Connect submission.
# Run from the repository root: ./04_deployment/positconnect/shinypy_census/manifestme.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

pip install rsconnect-python
rsconnect write-manifest shiny 04_deployment/positconnect/shinypy_census
echo "manifest.json written to 04_deployment/positconnect/shinypy_census/"

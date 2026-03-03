#!/usr/bin/env bash
# manifestme.sh
# Build manifest.json for the Shiny for Python app in positconnectcloud/shinypy
# and write it to this folder (positconnect/shinypy) for Posit Connect deployment.
# Run from the repository root: ./04_deployment/positconnect/shinypy/manifestme.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

pip install rsconnect-python
# Generate manifest for the app in positconnectcloud/shinypy
rsconnect write-manifest shiny 04_deployment/positconnectcloud/shinypy
# Copy manifest into positconnect folder as requested
cp 04_deployment/positconnectcloud/shinypy/manifest.json "$SCRIPT_DIR/manifest.json"
echo "manifest.json written to 04_deployment/positconnect/shinypy/"

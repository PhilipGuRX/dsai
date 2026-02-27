#!/usr/bin/env bash
# manifestme.sh
# Write a manifest.json for this Shiny for Python app (Census + AI) for Posit Connect Cloud.
# Run from the repository root: ./04_deployment/positconnectcloud/shinypy_census/manifestme.sh

set -e
# Run from repo root so path to app is correct for rsconnect
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
cd "$REPO_ROOT"

pip install rsconnect-python
rsconnect write-manifest shiny 04_deployment/positconnectcloud/shinypy_census

#!/bin/bash

# 01_example_curl.sh

# =============================
# Example: Making API Requests with curl
# =============================
# This script demonstrates how to use curl to interact with a sample API (https://reqres.in)
# Each section shows a different type of API call: GET, POST, PUT, PATCH, DELETE
# Headers and data are included as needed for each request

# NOTE: reqres.in recently made some updates.
# Now, you need an API key to get past the "are-you-human" check
# Register for a free API key at https://reqres.in/

# Load .env from project root (parent of this script's directory) so it works from any cwd
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -f "$PROJECT_ROOT/.env" ]; then
  set -a
  source "$PROJECT_ROOT/.env"
  set +a
fi
# Print it to the console
echo "TEST_API_KEY: $TEST_API_KEY"

# ---
# 1. GET request (simplest version, only works when no headers required)
#    Fetches user whose id is 2, using specific endpoint /api/users/2
# This will fail because we are not using an API key!
curl -s -X GET "https://reqres.in/api/users/2"
echo ""



# ---
# 2. GET request with custom header
#    Fetches user with id=2, using an API key in the header
curl -s -X GET "https://reqres.in/api/users/2" \
     -H "x-api-key: $TEST_API_KEY"
echo ""

# 3. GET request with query parameters
#    Fetches users on page 1, with id=5 (note: this API ignores id in query string)
curl -s -X GET "https://reqres.in/api/users?page=1&id=5" \
     -H "x-api-key: $TEST_API_KEY"
echo ""

# ---
# 4. POST request to create a new user
#    Sends JSON data with name and job fields
curl -s -X POST "https://reqres.in/api/users" \
     -H "Content-Type: application/json" \
     -H "x-api-key: $TEST_API_KEY" \
     -d '{"name": "Ada Lovelace", "job": "engineer"}'
echo ""

# ---
# 5. More API Call Method Examples
#    (Uncomment any line to try it)

# GET: Fetch a user by ID
# curl -X GET "https://reqres.in/api/users/2" \
#      -H "x-api-key: $TEST_API_KEY"

# POST: Create a new user
# curl -X POST "https://reqres.in/api/users" \
#      -H "Content-Type: application/json" \
#      -H "x-api-key: $TEST_API_KEY" \
#      -d '{"name": "Ada Lovelace", "job": "engineer"}'

# PUT: Update an existing user (replace all fields)
# curl -X PUT "https://reqres.in/api/users/2" \
#      -H "Content-Type: application/json" \
#      -H "x-api-key: $TEST_API_KEY" \
#      -d '{"name": "Ada Lovelace", "job": "scientist"}'

# PATCH: Update part of a user (partial update)
# curl -X PATCH "https://reqres.in/api/users/2" \
#      -H "Content-Type: application/json" \
#      -H "x-api-key: $TEST_API_KEY" \
#      -d '{"job": "mathematician"}'

# DELETE: Remove a user by ID
# curl -X DELETE "https://reqres.in/api/users/2" \
#      -H "x-api-key: $TEST_API_KEY"
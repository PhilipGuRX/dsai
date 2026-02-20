# test_requests.py
# POST request with JSON using the requests library
# Pairs with ACTIVITY_add_documentation_to_cursor (Stage 3B)
# Tim Fraser

# Makes a POST request to httpbin.org/post with JSON data.
# Demonstrates how to send a JSON body and read the JSON response.

# 0. Setup #################################

## 0.1 Load Packages ############################

import requests  # for HTTP requests

# 1. Make POST Request with JSON ###################################

# URL that echoes back the request (useful for testing)
url = "https://httpbin.org/post"

# Data to send as JSON in the request body
# The requests library will serialize this dict and set Content-Type: application/json
data = {"name": "test"}

# Send POST request; json= serializes data and sets the correct header
response = requests.post(url, json=data)

# 2. Inspect Response ###################################

# Status code (200 = success)
print(response.status_code)

# Parse response body as JSON and print (httpbin echoes back what we sent)
print(response.json())

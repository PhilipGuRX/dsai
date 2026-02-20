#!/usr/bin/env python3
"""
Load API key from .env and make a GET request.
Run from project root: python3 01_query_api/get_request.py
Or from this folder:   python3 get_request.py
"""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

# Find project root (parent of this script's directory) and load .env
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("TEST_API_KEY")
URL = "https://reqres.in/api/users/2"

response = requests.get(URL, headers={"x-api-key": API_KEY})

print(response.status_code)
print(response.json())

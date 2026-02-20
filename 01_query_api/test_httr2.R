#' @name test_httr2.R
#' @title GET request to GitHub API with httr2
#' @description
#' Topic: HTTP requests in R
#'
#' Makes a GET request to the GitHub API for user "octocat" using httr2.
#' Demonstrates building a request, performing it, and reading the JSON response.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

library(httr2)  # for HTTP requests

# 1. MAKE GET REQUEST ###################################

# Build the request: request() defaults to GET when no body is set
# See https://httr2.r-lib.org/reference/req_perform.html
req = request("https://api.github.com/users/octocat") |>
  req_method("GET")

# Perform the request and store the response
resp = req_perform(req)

# Check status (200 = success)
resp$status_code

# Parse response body as JSON (list in R)
user = resp_body_json(resp)

# Inspect: e.g. login, name, public repos
user$login
user$name
user$public_repos

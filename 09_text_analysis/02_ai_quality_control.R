# 02_ai_quality_control.R
# AI-Assisted Text Quality Control
# Tim Fraser

# This script demonstrates how to use AI (Ollama local, Ollama Cloud, or OpenAI) to perform quality control
# on AI-generated text reports. It implements quality control criteria including
# boolean accuracy checks and Likert scales for multiple quality dimensions.
# Students learn to design quality control prompts and structure AI outputs as JSON.

# 0. SETUP ###################################

## 0.1 Load Packages #################################

# If you haven't already, install required packages:
# install.packages(c("dplyr", "stringr", "readr", "httr2", "jsonlite"))

library(dplyr)    # for data wrangling
library(stringr)  # for text processing
library(readr)    # for reading files
library(httr2)    # for HTTP requests
library(jsonlite) # for JSON operations

## 0.2 Configuration ####################################

# Load API keys from project-root .env (OPENAI_API_KEY, OLLAMA_API_KEY, optional OLLAMA_HOST / OLLAMA_MODEL)
if (file.exists(".env")){  readRenviron(".env")  } else {  warning(".env file not found. Make sure it exists in the project root.") }

# Choose your AI provider: "ollama" or "openai"
# Lab: OpenAI avoids long local model runs (set OPENAI_API_KEY in project-root .env).
AI_PROVIDER = "ollama"  # must be lowercase: "ollama" or "openai"

# Ollama: "local" = Ollama app on this machine; "cloud" = ollama.com hosted models (free tier uses API key)
# Setup: 03_query_ai/ACTIVITY_ollama_api_key.md — add OLLAMA_API_KEY=... to .env; run 03_query_ai/03_ollama_cloud.R to test
OLLAMA_TARGET = "local"  # "local" (Ollama app) or "cloud" (needs OLLAMA_API_KEY in .env)

PORT = 11434
OLLAMA_HOST_LOCAL = paste0("http://localhost:", PORT)
OLLAMA_HOST_CLOUD = sub("/$", "", trimws(Sys.getenv("OLLAMA_HOST", "https://ollama.com")))
OLLAMA_API_KEY = Sys.getenv("OLLAMA_API_KEY")
# Override with OLLAMA_MODEL_LOCAL in .env if your pulled tag differs (e.g., gemma3:latest)
OLLAMA_MODEL_LOCAL = trimws(Sys.getenv("OLLAMA_MODEL_LOCAL", "llama3.2:latest"))
OLLAMA_MODEL_CLOUD = trimws(Sys.getenv("OLLAMA_MODEL", "gpt-oss:20b-cloud"))  # cloud tag from ollama.com/library

# OpenAI configuration
OPENAI_API_KEY = Sys.getenv("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o-mini"  # Low-cost model

## 0.3 Load Sample Data ####################################

# Load sample report text for quality control
sample_text = read_file("09_text_analysis/data/sample_reports.txt")
reports = strsplit(sample_text, "\n\n")[[1]]
reports = trimws(reports)
reports = reports[reports != ""]  # Remove empty strings
report = reports[1]

# Load source data (if available) for accuracy checking
# In this example, we'll use a simple data structure
source_data = "White County, IL | 2015 | PM10 | Time Driven | hours
|type        |label_value |label_percent |
|:-----------|:-----------|:-------------|
|Light Truck |2.7 M       |51.8%         |
|Car/ Bike   |1.9 M       |36.1%         |
|Combo Truck |381.3 k     |7.3%          |
|Heavy Truck |220.7 k     |4.2%          |
|Bus         |30.6 k      |0.6%          |"

cat("📝 Report for Quality Control:\n")
cat("---\n")
cat(report)
cat("\n---\n\n")

# 1. AI QUALITY CONTROL FUNCTION ###################################

## 1.1 Create Quality Control Prompt #################################

# Create a comprehensive quality control prompt based on samplevalidation.tex
# This prompt asks the AI to evaluate text on multiple criteria
create_quality_control_prompt = function(report_text, source_data = NULL) {
  
  # Base instructions: ground truth + strict JSON (iteration for lab Task 4)
  instructions = paste0(
    "You are a quality control validator for AI-generated reports. ",
    "When Source Data is provided, treat it as ground truth: flag wrong years, geographies, ",
    "pollutants, category labels, counts (M/k), or percentages that contradict the source. ",
    "Verify internal arithmetic when the report combines categories (e.g., summed shares should match stated totals within rounding). ",
    "Likert scores must be JSON numbers (integers 1–5 only, no decimals, not quoted strings). ",
    "The boolean accurate must be JSON true/false (lowercase), not strings. ",
    "Return exactly one JSON object with the keys below—no markdown fences, no prose before or after."
  )
  
  # Add source data if provided for accuracy checking
  data_context = ""
  if (!is.null(source_data)) {
    data_context = paste0(
      "\n\nSource Data (ground truth for accuracy checks):\n",
      source_data,
      "\n"
    )
  }
  
  # Quality control criteria (from samplevalidation.tex), with rubric anchors + extra check
  criteria = "
  
Quality Control Criteria:

1. **accurate** (boolean): TRUE only if every quantitative claim and category description matches Source Data when provided; otherwise judge internal plausibility. FALSE if any mismatch, invented numbers, or mislabeled categories.

2. **accuracy** (Likert 1–5): 1 = multiple factual or interpretive errors vs data; 3 = minor ambiguity; 5 = fully aligned with Source Data (or clearly sound if no source).

3. **formality** (Likert 1–5): 1 = conversational/slang; 3 = mixed; 5 = neutral, professional tone suitable for a government or technical memo.

4. **faithfulness** (Likert 1–5): 1 = causal or policy claims not supported by the tabulated shares (e.g., invented mechanisms); 3 = recommendations loosely tied to the distribution; 5 = every substantive claim maps to a number or category in Source Data (or is explicitly labeled as interpretation).

5. **clarity** (Likert 1–5): 1 = vague or hard to follow; 3 = understandable with effort; 5 = precise wording and clear structure.

6. **succinctness** (Likert 1–5): 1 = padded or repetitive; 3 = acceptable length; 5 = concise with no needless words.

7. **relevance** (Likert 1–5): 1 = off-topic filler; 3 = partly on topic; 5 = focused on the data and implications.

8. **consistency** (Likert 1–5): 1 = internal contradictions or math that does not add up; 3 = small tension; 5 = logically consistent throughout.

9. **actionability** (Likert 1–5): 1 = no concrete next steps or only generic platitudes; 3 = one usable idea (e.g., \"tighten standards\") without detail; 5 = specific, implementable recommendations clearly tied to the top emitting categories.

10. **terminology_alignment** (Likert 1–5): 1 = category names or pollutant wording clearly clash with Source Data (e.g., wrong pollutant or garbled labels); 3 = minor informal synonyms (\"cars\" for Car/ Bike); 5 = labels align with Source Data or clearly intentional, consistent abbreviations.

Return your response as valid JSON in this exact format (use lowercase true/false for the boolean):
{
  \"accurate\": true,
  \"accuracy\": 5,
  \"formality\": 5,
  \"faithfulness\": 5,
  \"clarity\": 5,
  \"succinctness\": 5,
  \"relevance\": 5,
  \"consistency\": 5,
  \"actionability\": 5,
  \"terminology_alignment\": 5,
  \"details\": \"Brief explanation (max 50 words); mention any numeric mismatch with Source Data if applicable.\"
}
"
  
  # Combine into full prompt
  full_prompt = paste0(
    instructions,
    data_context,
    "\n\nReport Text to Validate:\n",
    report_text,
    criteria
  )
  
  return(full_prompt)
}

## 1.2 Query AI Function #################################

# Function to query AI and get quality control results
query_ai_quality_control = function(prompt, provider = AI_PROVIDER) {
  
  if (provider == "ollama") {
    # Ollama local (no key) vs Ollama Cloud (Bearer token) — same /api/chat shape as 03_ollama_cloud.R
    use_cloud = identical(OLLAMA_TARGET, "cloud")
    if (use_cloud) {
      if (OLLAMA_API_KEY == "") {
        stop("OLLAMA_TARGET is \"cloud\" but OLLAMA_API_KEY is empty. Add OLLAMA_API_KEY to .env; see 03_query_ai/ACTIVITY_ollama_api_key.md")
      }
      url = paste0(OLLAMA_HOST_CLOUD, "/api/chat")
      ollama_model = OLLAMA_MODEL_CLOUD
    } else {
      url = paste0(OLLAMA_HOST_LOCAL, "/api/chat")
      ollama_model = OLLAMA_MODEL_LOCAL
    }
    
    body = list(
      model = ollama_model,
      messages = list(
        list(
          role = "user",
          content = prompt
        )
      ),
      format = "json",  # Request JSON output
      stream = FALSE
    )
    
    req = request(url) %>%
      req_body_json(body) %>%
      req_method("POST")
    if (use_cloud) {
      req = req %>%
        req_headers(
          "Authorization" = paste0("Bearer ", OLLAMA_API_KEY),
          "Content-Type" = "application/json"
        ) %>%
        req_retry(max_tries = 6, max_seconds = 120)
    }
    res = req %>% req_perform()
    
    response = resp_body_json(res)
    output = response$message$content
    
  } else if (provider == "openai") {
    # Query OpenAI
    if (OPENAI_API_KEY == "") {
      stop("OPENAI_API_KEY not found in .env file. Please set it up first.")
    }
    
    url = "https://api.openai.com/v1/chat/completions"
    
    body = list(
      model = OPENAI_MODEL,
      messages = list(
        list(
          role = "system",
          content = "You are a quality control validator. Always return your responses as valid JSON."
        ),
        list(
          role = "user",
          content = prompt
        )
      ),
      response_format = list(type = "json_object"),  # Request JSON output
      temperature = 0.3  # Lower temperature for more consistent validation
    )
    
    # 429 Too Many Requests: OpenAI rate-limits by key/tier. req_retry() waits
    # (Retry-After header or exponential backoff) and tries again—see ?httr2::req_retry
    res = request(url) %>%
      req_headers(
        "Authorization" = paste0("Bearer ", OPENAI_API_KEY),
        "Content-Type" = "application/json"
      ) %>%
      req_body_json(body) %>%
      req_method("POST") %>%
      req_retry(max_tries = 6, max_seconds = 120) %>%
      req_perform()
    
    response = resp_body_json(res)
    output = response$choices[[1]]$message$content
    
  } else {
    stop("Invalid provider. Use 'ollama' (set OLLAMA_TARGET to 'local' or 'cloud') or 'openai'.")
  }
  
  return(output)
}

## 1.3 Parse Quality Control Results #################################

# Parse JSON response and convert to tibble
parse_quality_control_results = function(json_response) {
  # Try to parse JSON
  # Sometimes AI returns text with JSON, so we extract JSON if needed
  json_match = str_extract(json_response, "\\{.*\\}")
  if (!is.na(json_match)) {
    json_response = json_match
  }
  
  # Parse JSON
  quality_data = fromJSON(json_response)
  
  # Convert to tibble (optional keys default to NA if an older prompt/model omits them)
  pick_num = function(nm) {
    if (nm %in% names(quality_data)) quality_data[[nm]] else NA_real_
  }
  consistency_val = pick_num("consistency")
  actionability_val = pick_num("actionability")
  terminology_val = pick_num("terminology_alignment")
  results = tibble(
    accurate = quality_data$accurate,
    accuracy = quality_data$accuracy,
    formality = quality_data$formality,
    faithfulness = quality_data$faithfulness,
    clarity = quality_data$clarity,
    succinctness = quality_data$succinctness,
    relevance = quality_data$relevance,
    consistency = consistency_val,
    actionability = actionability_val,
    terminology_alignment = terminology_val,
    details = quality_data$details
  )
  
  return(results)
}

# 2. RUN QUALITY CONTROL ###################################

## 2.1 Create Quality Control Prompt #################################

quality_prompt = create_quality_control_prompt(report, source_data)

cat("🤖 Querying AI for quality control...\n\n")

## 2.2 Query AI #################################

ai_response = query_ai_quality_control(quality_prompt, provider = AI_PROVIDER)

cat("📥 AI Response (raw):\n")
cat(ai_response)
cat("\n\n")

## 2.3 Parse and Display Results #################################

quality_results = parse_quality_control_results(ai_response)

cat("✅ Quality Control Results:\n")
print(quality_results)
cat("\n")

## 2.4 Calculate Overall Score #################################

# Average Likert score (exclude boolean accurate; include consistency when present)
likert_cols = c(
  "accuracy", "formality", "faithfulness", "clarity",
  "succinctness", "relevance", "consistency",
  "actionability", "terminology_alignment"
)
# base::intersect: dplyr masks intersect() for data frames; we need vector names here
likert_present = base::intersect(likert_cols, names(quality_results))
overall_score = quality_results %>%
  select(all_of(likert_present)) %>%
  rowMeans(na.rm = TRUE)

quality_results = quality_results %>%
  mutate(overall_score = round(overall_score, 2))

cat("📊 Overall Quality Score (average of Likert scales): ", overall_score, "/ 5.0\n")
cat("📊 Accuracy Check: ", ifelse(quality_results$accurate, "✅ PASS", "❌ FAIL"), "\n\n")

# 3. QUALITY CONTROL MULTIPLE REPORTS ###################################

## 3.1 Batch Quality Control Function #################################

# Function to check multiple reports
check_multiple_reports = function(reports, source_data = NULL) {
  
  cat("🔄 Performing quality control on ", length(reports), " reports...\n\n")
  
  all_results = list()
  
  for (i in 1:length(reports)) {
    cat("Checking report ", i, " of ", length(reports), "...\n")
    
    # Create prompt
    prompt = create_quality_control_prompt(reports[i], source_data)
    
    # Query AI
    tryCatch({
      response = query_ai_quality_control(prompt, provider = AI_PROVIDER)
      results = parse_quality_control_results(response)
      results = results %>% mutate(report_id = i)
      all_results[[i]] = results
    }, error = function(e) {
      cat("❌ Error checking report ", i, ": ", e$message, "\n")
    })
    
    # Small delay to avoid rate limiting
    Sys.sleep(1)
  }
  
  # Combine all results
  combined_results = bind_rows(all_results)
  
  return(combined_results)
}

## 3.2 Run Batch Quality Control (Optional) #################################

# Uncomment to check all reports
# if (length(reports) > 1) {
#   batch_results = check_multiple_reports(reports, source_data)
#   cat("\n📊 Batch Quality Control Results:\n")
#   print(batch_results)
# }

cat("✅ AI quality control complete!\n")
cat("💡 Compare these results with manual quality control (01_manual_quality_control.R) to see how AI performs.\n")

# 4. PROMPT ITERATION NOTES (LAB TASK 4) ###################################
#
# What worked:
# - Ground-truth Source Data in the prompt improved accuracy/faithfulness checks vs
#   manual keyword counts (manual QC misses wrong pollutant labels if digits still appear).
# - Explicit JSON typing (numbers not strings, boolean not \"true\") reduced parse failures.
# - Extra Likert dimensions (actionability, terminology_alignment) separate vague report #4
#   from data-rich report #1 better than boolean pattern rules alone.
#
# What did not work as well:
# - Models sometimes still emit markdown fences despite instructions; str_extract() patch
#   helps but brittle if multiple braces appear in \"details\".
# - Arithmetic checks depend on the model doing light math; small rounding differences can
#   inflate false negatives on **accurate** unless you allow \"within 0.1%\" in the rubric.

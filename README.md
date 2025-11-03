# Batch Processing System - Complete Guide

This folder contains a complete batch processing system for news classification using Google Gemini Batch API, optimized for Tier 1 with 8-10k character articles.

## 📁 File Structure

```
batch_processing/
├── batch_processor.py          # Core engine (Gemini Batch API integration)
├── batch_cli.py                # Command-line interface
├── batch_api.py                # REST API (FastAPI)
├── process_large_batch.py      # Large-scale processing (12k+ articles)
└── README.md                   # This file
```

---

## 🔧 1. batch_processor.py - Core Engine

### Purpose
Handles all interactions with Google Gemini Batch API:
- Creates JSONL batch files in correct Google format
- Uploads files and creates batch jobs
- Monitors job status
- Retrieves and parses results

### Key Components

#### Class: `BatchProcessor`

**Initialization:**
```python
processor = BatchProcessor(
    gemini_key="YOUR_API_KEY",
    batch_dir="./batch_jobs",         # Where batch files are stored
    max_batch_size=1000,              # Max items per batch
    batch_model="gemini-1.5-flash"    # Model to use (changeable)
)
```

**Main Methods:**

1. **`prepare_batch_from_urls(urls, batch_name)`** - Extract & prepare
   - Fetches content from URLs concurrently
   - Creates JSONL file with correct Google format
   - Returns path to batch file

2. **`prepare_batch_from_contents(contents, batch_name)`** - Pre-crawled content
   - Skips URL extraction (faster)
   - Directly creates JSONL from provided content
   - Use this when you already have article text

3. **`submit_batch(batch_file_path)`** - Submit to API
   - Uploads JSONL file to Google
   - Creates batch job
   - Returns job_id for tracking
   - Saves metadata locally

4. **`check_status(job_id)`** - Monitor progress
   - Queries job status
   - Returns state, completion count, timestamps

5. **`wait_for_completion(job_id, poll_interval, max_wait_time)`** - Block until done
   - Polls status every N seconds
   - Returns True if succeeded, False if failed/timeout

6. **`retrieve_results(job_id, batch_name)`** - Get results
   - Downloads result JSONL
   - Parses into `ClassificationResultFromText` objects
   - Returns list of results

### JSONL Format (Google Style)

**✅ Correct Format (Current Implementation):**
```json
{
  "key": "request_0",
  "request": {
    "contents": [{
      "role": "user",
      "parts": [{"text": "Title: ...\n\nContent: ..."}]
    }],
    "systemInstruction": {
      "parts": [{"text": "Analyze financial news..."}]
    },
    "generationConfig": {
      "response_mime_type": "application/json",
      "response_schema": {...}
    }
  }
}
```

**❌ Old Format (OpenAI style - Don't use):**
```json
{
  "custom_id": "request_0",
  "method": "POST",
  "url": "/v1/models/gemini-2.0-flash:generateContent",
  "body": {...}
}
```

### Workflow Example

```python
from batch_processor import BatchProcessor
import os

# Initialize
processor = BatchProcessor(gemini_key=os.getenv('GOOGLE_API_KEY'))

# Option A: From URLs
batch_file = await processor.prepare_batch_from_urls(
    urls=["https://example.com/article1", "..."],
    batch_name="news_batch_001"
)

# Option B: From pre-crawled content (recommended)
contents = [
    {"id": "1", "title": "...", "contents": "..."},
    {"id": "2", "title": "...", "contents": "..."}
]
batch_file = processor.prepare_batch_from_contents(
    contents=contents,
    batch_name="news_batch_001"
)

# Submit
job_id = processor.submit_batch(batch_file)
print(f"Job submitted: {job_id}")

# Wait for completion (blocking)
success = processor.wait_for_completion(job_id, poll_interval=30)

# Retrieve results
if success:
    results = processor.retrieve_results(job_id, "news_batch_001")
    for result in results:
        print(f"{result.page_title}: {result.is_financial}")
```

---

## 💻 2. batch_cli.py - Command-Line Interface

### Purpose
Provides CLI commands for batch management without writing Python code.

### Commands

#### Submit Batch from URLs
```bash
python batch_cli.py submit urls.txt --name my_batch
python batch_cli.py submit urls.txt --name my_batch --wait  # Wait for completion
```

**urls.txt format:**
```
https://example.com/article1
https://example.com/article2
# Comments are ignored
https://example.com/article3
```

#### Submit Batch from JSON Content
```bash
python batch_cli.py submit-contents batch_contents.json --name my_batch
```

**batch_contents.json format:**
```json
[
  {
    "id": "article_1",
    "title": "Article Title",
    "contents": "Full article text..."
  },
  {
    "id": "article_2",
    "title": "Another Article",
    "contents": "More text..."
  }
]
```

#### Check Status
```bash
python batch_cli.py status <JOB_ID>
```

Output:
```
📊 Batch Job Status
==================================================
  Job ID: batch_jobs/xyz123
  State: JOB_STATE_RUNNING
  Progress: 45/100
  Completion: 45.0%
  Created: 2025-01-04 10:30:00
  Updated: 2025-01-04 10:35:00
==================================================

⏳ Job is still running. Check again later.
```

#### Retrieve Results
```bash
python batch_cli.py results <JOB_ID> <BATCH_NAME>
python batch_cli.py results <JOB_ID> <BATCH_NAME> --show-preview
```

Output:
```
📥 Retrieving results for job batch_jobs/xyz123...

✓ Retrieved 100 results

💾 Results saved to: results_my_batch.json

📈 Summary:
  Financial news: 78/100
  Sentiment breakdown:
    Positive: 45
    Negative: 23
    Neutral: 32
```

#### List All Batches
```bash
python batch_cli.py list
```

Output:
```
📋 Batch Jobs (5 total)

Batch Name            Job ID              Status              Submitted
===================================================================================
news_batch_001        batch_jobs/xyz123   JOB_STATE_SUCCEED  2025-01-04T10:30:00
news_batch_002        batch_jobs/abc456   JOB_STATE_RUNNING  2025-01-04T11:00:00
```

### Workflow Example

```bash
# Step 1: Submit batch
python batch_cli.py submit-contents my_articles.json --name batch_jan_04

# Output:
# 📦 Submitting batch with 50 pre-crawled items...
# ✓ Batch submitted successfully!
#   Job ID: batch_jobs/abc123xyz
#   Batch name: batch_jan_04
# Check status with: python batch_cli.py status batch_jobs/abc123xyz

# Step 2: Monitor (run periodically)
python batch_cli.py status batch_jobs/abc123xyz

# Step 3: Retrieve when done
python batch_cli.py results batch_jobs/abc123xyz batch_jan_04 --show-preview
```

---

## 🌐 3. batch_api.py - REST API

### Purpose
Provides HTTP endpoints for batch processing, enabling integration with web apps, services, or remote systems.

### Tech Stack
- **FastAPI**: Modern Python web framework
- **Pydantic**: Data validation
- **Async**: Non-blocking I/O

### Endpoints

#### POST /batch/submit
Submit URLs for processing.

**Request:**
```json
{
  "urls": [
    "https://example.com/article1",
    "https://example.com/article2"
  ],
  "batch_name": "my_batch",
  "wait_for_completion": false
}
```

**Response:**
```json
{
  "job_id": "batch_jobs/xyz123",
  "batch_name": "my_batch",
  "url_count": 2,
  "status": "SUBMITTED",
  "message": "Batch submitted. Use GET /batch/status/xyz123 to check progress"
}
```

#### POST /batch/submit-contents
Submit pre-crawled content (faster, no URL extraction).

**Request:**
```json
{
  "contents": [
    {
      "id": "article_1",
      "title": "Article Title",
      "contents": "Full article text..."
    }
  ],
  "batch_name": "my_batch",
  "wait_for_completion": false
}
```

**Response:** Same as `/batch/submit`

#### GET /batch/status/{job_id}
Check batch job status.

**Response:**
```json
{
  "job_id": "batch_jobs/xyz123",
  "state": "JOB_STATE_RUNNING",
  "completed_count": 45,
  "total_count": 100,
  "progress_percent": 45.0
}
```

**States:**
- `JOB_STATE_PENDING` - Queued
- `JOB_STATE_RUNNING` - Processing
- `JOB_STATE_SUCCEEDED` - Complete
- `JOB_STATE_FAILED` - Failed

#### GET /batch/results/{job_id}/{batch_name}
Retrieve completed results.

**Response:**
```json
{
  "job_id": "batch_jobs/xyz123",
  "results": [
    {
      "page_title": "Article Title",
      "is_financial": "Yes",
      "sector": ["Technology", "Banking"],
      "companies": ["Apple", "Goldman Sachs"],
      "sentiment": "Positive",
      "confident_score": 9.5,
      "summary_en": "...",
      "summary_tr": "..."
    }
  ],
  "total_count": 100
}
```

#### GET /batch/jobs
List all batches.

**Response:**
```json
{
  "jobs": [
    {
      "job_id": "batch_jobs/xyz123",
      "batch_file": "./batch_jobs/my_batch.jsonl",
      "submitted_at": "2025-01-04T10:30:00",
      "status": "JOB_STATE_SUCCEEDED"
    }
  ],
  "total": 5
}
```

### Running the API

**Start server:**
```bash
python batch_api.py
# Or with uvicorn:
uvicorn batch_api:app --host 0.0.0.0 --port 8001 --reload
```

**Access:**
- API: http://localhost:8001
- Docs: http://localhost:8001/docs (Swagger UI)
- Health: http://localhost:8001/health

### API Usage Examples

**cURL:**
```bash
# Submit batch
curl -X POST "http://localhost:8001/batch/submit-contents" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [
      {"id": "1", "title": "Test", "contents": "Test content..."}
    ],
    "batch_name": "test_batch"
  }'

# Check status
curl "http://localhost:8001/batch/status/batch_jobs/xyz123"

# Get results
curl "http://localhost:8001/batch/results/batch_jobs/xyz123/test_batch"
```

**Python:**
```python
import requests

# Submit
response = requests.post(
    "http://localhost:8001/batch/submit-contents",
    json={
        "contents": [
            {"id": "1", "title": "Test", "contents": "Test content..."}
        ],
        "batch_name": "test_batch"
    }
)
job_id = response.json()["job_id"]

# Poll status
import time
while True:
    status = requests.get(f"http://localhost:8001/batch/status/{job_id}").json()
    print(f"Progress: {status['progress_percent']}%")
    if status["state"] == "JOB_STATE_SUCCEEDED":
        break
    time.sleep(30)

# Get results
results = requests.get(
    f"http://localhost:8001/batch/results/{job_id}/test_batch"
).json()
```

---

## 🚀 4. process_large_batch.py - Large-Scale Processing

### Purpose
Handles processing of 12,000+ articles with Tier 1 optimizations, respecting the 10M enqueued tokens limit through wave-based processing.

### Key Features

1. **Wave-Based Processing**
   - Automatically splits large datasets into waves
   - Each wave stays under 10M token limit
   - Sequential wave processing (wait for completion)

2. **Tier 1 Optimized**
   - Configured for 2,000 RPM (real-time)
   - 10M batch enqueued tokens limit
   - Token estimates for 8-10k char articles

3. **Two Processing Modes**
   - **Batch API**: Cost-effective ($7.29 for 12k)
   - **Real-time API**: Faster or daily limits ($14.58 for 12k)

### Configuration Constants

```python
# Tier 1 Settings
BATCH_SIZE = 1000                        # Items per batch job
REALTIME_RPM = 2000                      # Tier 1 real-time speed
ITEMS_PER_DAY = 400                      # Custom daily limit

# Token Estimates (8-10k chars/article)
AVG_INPUT_TOKENS_PER_ARTICLE = 2800      # ~9k chars average
AVG_OUTPUT_TOKENS_PER_ARTICLE = 150      # Structured JSON

# Tier 1 Batch Limits
BATCH_ENQUEUED_TOKENS_LIMIT = 10_000_000  # Google's hard limit
SAFE_ENQUEUED_TOKENS = 9_000_000          # 90% safety margin
MAX_ARTICLES_PER_WAVE = 3_214             # ~9M tokens per wave
```

### Mode 1: Batch API (Wave-Based)

**For 12,000 articles:**
- 4 waves of ~3,200 articles each
- Each wave: 3-4 batches of 1,000 items
- Total: ~12 batch jobs
- Sequential processing (respects 10M token limit)

**Cost:** $7.29
**Time:** 2-4 hours

**Usage:**
```python
import asyncio
from process_large_batch import process_with_batch_api

# Load your data
with open('12k_articles.json') as f:
    items = json.load(f)

# Process with automatic wave management
job_ids = await process_with_batch_api(
    items,
    output_dir="./batch_results",
    wait_for_waves=True  # Auto-waits between waves (recommended)
)

# Workflow:
# Wave 1: Submit 3 batches → Wait ~40min → Complete
# Wave 2: Submit 3 batches → Wait ~40min → Complete
# Wave 3: Submit 3 batches → Wait ~40min → Complete
# Wave 4: Submit 2 batches → Wait ~30min → Complete
# Total: ~2.5 hours
```

**What Happens:**
1. Calculates needed waves (12,000 ÷ 3,214 = 4 waves)
2. Shows cost estimate (~$7.29)
3. For each wave:
   - Splits into 3-4 batches of 1,000 items
   - Submits all batches in wave
   - Waits for wave to complete
   - Moves to next wave
4. Saves job tracking to `job_tracking.json`

**Output:**
```
================================================================================
PROCESSING WITH BATCH API (TIER 1 OPTIMIZED)
================================================================================

📊 Tier 1 Batch Limits:
   Max enqueued tokens: 10,000,000
   Safe enqueued tokens: 9,000,000 (90% of limit)
   Avg tokens per article: 2,800
   Max articles per wave: 3,214

📦 Processing Strategy:
   Total articles: 12,000
   Articles per wave: ~3,214
   Number of waves: 4
   Batches per wave: ~3

💰 Estimated cost: $7.29
   Input: 33,600,000 tokens (33.6M)
   Output: 1,800,000 tokens (1.8M)

================================================================================
WAVE 1/4: Processing 3,214 articles
================================================================================
Wave tokens: 9,000,000 / 9,000,000 (safe limit)
Split into 3 batches of ~1000 items

  [1/3] Preparing wave01_batch001_20250104_1030...
     ✓ Batch file created
     ✓ Submitted: batch_jobs/xyz123...

  [2/3] Preparing wave01_batch002_20250104_1032...
     ✓ Batch file created
     ✓ Submitted: batch_jobs/abc456...

  [3/3] Preparing wave01_batch003_20250104_1034...
     ✓ Batch file created
     ✓ Submitted: batch_jobs/def789...

✅ Wave 1 submitted: 3 batches

⏳ Waiting for Wave 1 to complete before submitting Wave 2...
   This ensures we don't exceed the 10,000,000 enqueued tokens limit
   Wave 1 status: 0 completed, 3 running, 0 failed
   Wave 1 status: 1 completed, 2 running, 0 failed
   ...
   Wave 1 status: 3 completed, 0 running, 0 failed
   ✅ Wave 1 complete!

[Repeat for Waves 2, 3, 4...]

================================================================================
✅ ALL WAVES SUBMITTED
================================================================================
   Total batches: 12
   Total articles: 12,000

📊 Job tracking saved to: ./batch_results/job_tracking.json
```

### Mode 2: Real-Time API

**Option A: Fast (Tier 1 Speed)**
- 2,000 RPM (Tier 1)
- **Time:** 6 minutes for 12k
- **Cost:** $14.58 (2x batch)

**Option B: Daily Limit**
- 400 articles/day
- **Time:** 30 days
- **Cost:** $14.58
- Auto-saves progress, resumable

**Usage:**
```python
from process_large_batch import process_with_realtime_api

# Fast version (Tier 1)
results = await process_with_realtime_api(
    items,
    rpm_limit=2000,      # Tier 1 speed
    items_per_day=12000  # No daily limit
)
# Cost: $14.58, Time: 6 minutes

# Daily limit version
results = await process_with_realtime_api(
    items,
    rpm_limit=15,        # Conservative
    items_per_day=400    # 400/day for 30 days
)
# Cost: $14.58, Time: 30 days (resumable)
```

### CLI Usage

```bash
# Batch mode (recommended)
python process_large_batch.py batch 12k_articles.json

# Real-time mode
python process_large_batch.py realtime 12k_articles.json
```

### Collecting Results

After all waves complete:

```python
from batch_processor import BatchProcessor
import json

processor = BatchProcessor(gemini_key=os.getenv('GOOGLE_API_KEY'))

# Load job tracking
with open('./batch_results/job_tracking.json') as f:
    jobs = json.load(f)

# Collect all results
all_results = []
for job in jobs:
    print(f"Retrieving Wave {job['wave']} Batch {job['batch_num']}...")
    results = processor.retrieve_results(job['job_id'], job['batch_name'])
    all_results.extend([r.model_dump() for r in results])

# Save combined
with open('results_12k_final.json', 'w') as f:
    json.dump(all_results, f, indent=2, default=str)

print(f"✅ Total: {len(all_results)}/12,000 articles processed")
```

---

## 💰 Cost Comparison

### For 12,000 Articles @ 9k chars each

| Method | Cost | Time | Best For |
|--------|------|------|----------|
| **Batch (Wave)** | **$7.29** | **2-4 hrs** | **Bulk processing** ⭐ |
| Real-time (Fast) | $14.58 | 6 min | Immediate results |
| Real-time (400/day) | $14.58 | 30 days | Daily processing |

**Recommendation:** Use batch API for bulk processing. 50% cost savings and fully automated.

---

## 🔄 Complete Workflow Example

### Scenario: Process 12,000 News Articles

**Step 1: Prepare Data**
```python
# Assuming you have article data
articles = [
    {"id": "1", "title": "...", "contents": "..."},
    {"id": "2", "title": "...", "contents": "..."},
    # ... 12,000 total
]

# Save to JSON
with open('12k_articles.json', 'w') as f:
    json.dump(articles, f)
```

**Step 2: Process with Batch API**
```python
import asyncio
from process_large_batch import process_with_batch_api

# In Jupyter notebook:
job_ids = await process_with_batch_api(
    articles,
    wait_for_waves=True
)

# Or from command line:
# python process_large_batch.py batch 12k_articles.json
```

**Step 3: Wait (2-4 hours)**
The script automatically:
- Submits Wave 1 (3 batches)
- Waits ~40 min
- Submits Wave 2 (3 batches)
- Waits ~40 min
- Submits Wave 3 (3 batches)
- Waits ~40 min
- Submits Wave 4 (2 batches)
- Waits ~30 min
- Done!

**Step 4: Collect Results**
```python
from batch_processor import BatchProcessor
import json

processor = BatchProcessor(gemini_key=os.getenv('GOOGLE_API_KEY'))

with open('./batch_results/job_tracking.json') as f:
    jobs = json.load(f)

all_results = []
for job in jobs:
    results = processor.retrieve_results(job['job_id'], job['batch_name'])
    all_results.extend([r.model_dump() for r in results])

with open('results_final.json', 'w') as f:
    json.dump(all_results, f, indent=2, default=str)

# Analyze
financial_count = sum(1 for r in all_results if r['is_financial'] == 'Yes')
print(f"Financial news: {financial_count}/12,000")
```

**Total Cost:** $7.29
**Total Time:** ~2.5 hours

---

## 🐛 Troubleshooting

### 429 RESOURCE_EXHAUSTED Error

**Cause:** Too many concurrent batch jobs or enqueued tokens limit exceeded.

**Solution:**
1. Check active jobs:
   ```python
   client = genai.Client(api_key=api_key)
   batches = list(client.batches.list())
   active = [b for b in batches if 'RUNNING' in str(b.state)]
   print(f"Active: {len(active)}/100")
   ```

2. If >90 active jobs, wait or cancel some
3. Use `process_large_batch.py` which handles this automatically

### Billing Not Enabled

**Error:** Can list jobs but can't create them.

**Solution:**
1. Go to https://console.cloud.google.com/billing
2. Enable billing on your project
3. Wait 5-10 minutes
4. Try again

### Results Not Found

**Error:** `retrieve_results()` fails.

**Cause:** Job not completed or wrong batch_name.

**Solution:**
1. Check status first:
   ```python
   status = processor.check_status(job_id)
   print(status['state'])  # Must be 'JOB_STATE_SUCCEEDED'
   ```
2. Verify batch_name matches the one used in `prepare_batch_from_contents()`

---

## 📚 Additional Resources

- **[TIER1_12K_SUMMARY.md](../TIER1_12K_SUMMARY.md)** - Cost analysis for 12k articles
- **[BATCH_API_TROUBLESHOOTING.md](../BATCH_API_TROUBLESHOOTING.md)** - Detailed troubleshooting
- **[Google Batch API Docs](https://ai.google.dev/gemini-api/docs/batch-api)** - Official documentation

---

## 🎯 Quick Reference

### Common Commands

```bash
# CLI
python batch_cli.py submit-contents data.json --name batch1
python batch_cli.py status <JOB_ID>
python batch_cli.py results <JOB_ID> batch1
python batch_cli.py list

# Large-scale
python process_large_batch.py batch 12k_articles.json
python process_large_batch.py realtime 12k_articles.json

# API
python batch_api.py  # Start server on port 8001
```

### Import Quick Reference

```python
# Core engine
from batch_processor import BatchProcessor, process_batch_workflow

# Large-scale processing
from process_large_batch import process_with_batch_api, process_with_realtime_api

# Usage
processor = BatchProcessor(gemini_key="...")
```

---

**Last Updated:** January 2025
**Optimized For:** Tier 1, 8-10k char articles, 12k+ items

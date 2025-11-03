# Quick Start Guide - Batch Processing

Get started with batch processing in 5 minutes!

## Prerequisites

```bash
# Install dependencies
pip install google-genai fastapi uvicorn python-dotenv

# Set API key
echo "GOOGLE_API_KEY=your_key_here" > .env
```

## 1. Smallest Example (10 Articles)

### Option A: Python Script

```python
import os
import asyncio
from batch_processing.batch_processor import BatchProcessor

# Your articles
articles = [
    {"id": "1", "title": "Market Update", "contents": "Stock markets rise..."},
    {"id": "2", "title": "Tech News", "contents": "Apple announces..."},
    # ... 8 more articles
]

async def main():
    # Initialize
    processor = BatchProcessor(gemini_key=os.getenv('GOOGLE_API_KEY'))

    # Prepare & submit
    batch_file = processor.prepare_batch_from_contents(articles, "test_batch")
    job_id = processor.submit_batch(batch_file)
    print(f"Submitted: {job_id}")

    # Wait for completion
    processor.wait_for_completion(job_id)

    # Get results
    results = processor.retrieve_results(job_id, "test_batch")

    for r in results:
        print(f"{r.page_title}: {r.is_financial} | {r.sentiment}")

asyncio.run(main())
```

### Option B: Command Line

```bash
# Create data file
cat > test_articles.json << EOF
[
  {"id": "1", "title": "Market Update", "contents": "Stock markets rise..."},
  {"id": "2", "title": "Tech News", "contents": "Apple announces..."}
]
EOF

# Submit
python batch_processing/batch_cli.py submit-contents test_articles.json \
  --name test_batch --wait

# Results auto-saved to results_test_batch.json
```

**Time:** ~10 minutes
**Cost:** ~$0.01

---

## 2. Medium Batch (1,000 Articles)

```python
import json
import asyncio
from batch_processing.batch_processor import BatchProcessor

# Load your data
with open('1k_articles.json') as f:
    articles = json.load(f)

async def main():
    processor = BatchProcessor(gemini_key=os.getenv('GOOGLE_API_KEY'))

    # Submit
    batch_file = processor.prepare_batch_from_contents(articles, "batch_1k")
    job_id = processor.submit_batch(batch_file)

    print(f"Job: {job_id}")
    print("Wait 20-30 minutes, then run:")
    print(f"  python batch_processing/batch_cli.py results {job_id} batch_1k")

asyncio.run(main())
```

**Time:** 20-30 minutes
**Cost:** ~$0.61

---

## 3. Large Scale (12,000 Articles)

### Using process_large_batch.py (Recommended)

```python
import json
import asyncio
from batch_processing.process_large_batch import process_with_batch_api

# Load data
with open('12k_articles.json') as f:
    articles = json.load(f)

# Process with automatic wave management
await process_with_batch_api(
    articles,
    wait_for_waves=True  # Auto-waits between waves
)

# Script handles everything:
# - Splits into 4 waves
# - Submits batches
# - Waits for completion
# - Saves job tracking

# Results collected after ~2-4 hours
```

**Time:** 2-4 hours
**Cost:** ~$7.29

---

## 4. Using the REST API

### Start Server

```bash
cd batch_processing
python batch_api.py
# Server runs on http://localhost:8001
```

### Submit Batch

```bash
curl -X POST "http://localhost:8001/batch/submit-contents" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [
      {"id": "1", "title": "Test", "contents": "Test article..."}
    ],
    "batch_name": "api_test",
    "wait_for_completion": false
  }'
```

**Response:**
```json
{
  "job_id": "batch_jobs/xyz123",
  "batch_name": "api_test",
  "status": "SUBMITTED",
  "message": "Batch submitted. Use GET /batch/status/xyz123 to check progress"
}
```

### Check Status

```bash
curl "http://localhost:8001/batch/status/batch_jobs/xyz123"
```

### Get Results

```bash
curl "http://localhost:8001/batch/results/batch_jobs/xyz123/api_test"
```

---

## Common Workflows

### Workflow 1: Daily Processing (400 articles/day)

```python
# day1_process.py
import json
import asyncio
from batch_processing.batch_processor import BatchProcessor

async def process_daily_batch(articles):
    processor = BatchProcessor(gemini_key=os.getenv('GOOGLE_API_KEY'))

    batch_file = processor.prepare_batch_from_contents(
        articles[:400],  # First 400
        batch_name=f"daily_{datetime.now().strftime('%Y%m%d')}"
    )

    job_id = processor.submit_batch(batch_file)
    return job_id

# Run daily
with open('articles.json') as f:
    articles = json.load(f)

job_id = await process_daily_batch(articles)
print(f"Today's job: {job_id}")
```

### Workflow 2: Real-time Processing

```python
from batch_processing.process_large_batch import process_with_realtime_api

# Fast processing with Tier 1 (2,000 RPM)
results = await process_with_realtime_api(
    articles,
    rpm_limit=2000,
    items_per_day=len(articles)  # Process all
)

# 12k articles in 6 minutes
# Cost: $14.58 (2x batch but immediate)
```

### Workflow 3: Monitoring Active Jobs

```python
from batch_processing.batch_processor import BatchProcessor
import json

processor = BatchProcessor(gemini_key=os.getenv('GOOGLE_API_KEY'))

# Load job tracking
with open('./batch_results/job_tracking.json') as f:
    jobs = json.load(f)

# Check all jobs
for job in jobs:
    status = processor.check_status(job['job_id'])
    print(f"Wave {job['wave']} Batch {job['batch_num']}: "
          f"{status['state']} ({status['completed_count']}/{status['total_count']})")
```

---

## Troubleshooting

### Problem: 429 RESOURCE_EXHAUSTED

**Quick check:**
```python
from google import genai
import os

client = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))
batches = list(client.batches.list())
active = [b for b in batches if 'RUNNING' in str(b.state)]

print(f"Active jobs: {len(active)}/100")
if len(active) >= 90:
    print("⚠️  At limit! Wait for jobs to complete.")
else:
    print("✅ Room for more jobs")
```

**Solution:**
- If at limit: Wait or cancel old jobs
- If no jobs: Enable billing at https://console.cloud.google.com/billing

### Problem: Batch Takes Too Long

**Check status:**
```bash
python batch_processing/batch_cli.py status <JOB_ID>
```

**Expected times:**
- 100 articles: 10-15 minutes
- 1,000 articles: 20-30 minutes
- 3,000 articles: 30-40 minutes

If stuck for >1 hour, check job state.

### Problem: Can't Find Results

**Verify job completed:**
```python
status = processor.check_status(job_id)
print(status['state'])  # Must be 'JOB_STATE_SUCCEEDED'
```

**Check batch name:**
```bash
ls batch_jobs/*_mapping.json
# Use the filename (without _mapping.json) as batch_name
```

---

## Next Steps

1. **Read Full Docs**
   - [README.md](README.md) - Complete guide
   - [ARCHITECTURE.md](ARCHITECTURE.md) - How it works
   - [TIER1_12K_SUMMARY.md](../TIER1_12K_SUMMARY.md) - Cost analysis

2. **Try Examples**
   - Start with 10 articles
   - Scale to 100, then 1,000
   - Use `process_large_batch.py` for 12k+

3. **Integrate**
   - Use CLI for ad-hoc processing
   - Use API for web integration
   - Use Python lib for notebooks

---

## Cheat Sheet

```bash
# Install
pip install google-genai fastapi uvicorn python-dotenv

# Submit
python batch_processing/batch_cli.py submit-contents data.json --name batch1

# Status
python batch_processing/batch_cli.py status <JOB_ID>

# Results
python batch_processing/batch_cli.py results <JOB_ID> batch1

# List all
python batch_processing/batch_cli.py list

# Large-scale (12k+)
python batch_processing/process_large_batch.py batch 12k_articles.json

# Start API
python batch_processing/batch_api.py
```

---

## Cost Calculator

```python
def estimate_cost(num_articles, avg_chars=9000):
    """
    Estimate batch processing cost.

    Args:
        num_articles: Number of articles
        avg_chars: Average characters per article (default: 9k)

    Returns:
        Estimated cost in USD
    """
    # Token estimates
    input_tokens = num_articles * (avg_chars / 3.2)  # ~2,800 tokens per 9k chars
    output_tokens = num_articles * 150

    # Batch API pricing
    input_cost = (input_tokens / 1_000_000) * 0.15
    output_cost = (output_tokens / 1_000_000) * 1.25

    total = input_cost + output_cost

    print(f"Articles: {num_articles:,}")
    print(f"Input tokens: {input_tokens:,.0f} ({input_tokens/1_000_000:.1f}M)")
    print(f"Output tokens: {output_tokens:,.0f} ({output_tokens/1_000_000:.1f}M)")
    print(f"Estimated cost: ${total:.2f}")

    return total

# Examples
estimate_cost(100)      # ~$0.06
estimate_cost(1000)     # ~$0.61
estimate_cost(12000)    # ~$7.29
```

---

**Ready to start?** Run the smallest example above and scale up from there!

# Batch Processing Guide

Complete guide for using batch processing to save 50% on API costs.

## 📊 Cost Comparison

### Your Current Volume: 10,000-12,000 URLs/day

#### Standard (Real-time) Processing
- **Model**: Gemini 2.0 Flash Lite
- **Input**: $0.30 per 1M tokens
- **Output**: $2.50 per 1M tokens

**Daily Cost (10,000 URLs):**
```
Input:  20M tokens × $0.30/1M = $6.00/day
Output:  2M tokens × $2.50/1M = $5.00/day
───────────────────────────────────────────
Total: $11.00/day = $330/month
```

**Daily Cost (12,000 URLs):**
```
Input:  24M tokens × $0.30/1M = $7.20/day
Output: 2.4M tokens × $2.50/1M = $6.00/day
───────────────────────────────────────────
Total: $13.20/day = $396/month
```

#### Batch Processing
- **Model**: Gemini 2.0 Flash
- **Input**: $0.15 per 1M tokens (50% cheaper)
- **Output**: $1.25 per 1M tokens (50% cheaper)

**Daily Cost (10,000 URLs):**
```
Input:  20M tokens × $0.15/1M = $3.00/day
Output:  2M tokens × $1.25/1M = $2.50/day
───────────────────────────────────────────
Total: $5.50/day = $165/month
💰 SAVINGS: $165/month (50%)
```

**Daily Cost (12,000 URLs):**
```
Input:  24M tokens × $0.15/1M = $3.60/day
Output: 2.4M tokens × $1.25/1M = $3.00/day
───────────────────────────────────────────
Total: $6.60/day = $198/month
💰 SAVINGS: $198/month (50%)
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install google-generativeai
```

### 2. Set API Key

```bash
export GOOGLE_API_KEY="your-api-key"
```

### 3. Prepare URLs File

Create `urls.txt`:
```
https://www.reuters.com/business/article1
https://www.bloomberg.com/news/article2
https://www.ft.com/content/article3
# Add more URLs (one per line)
```

### 4. Submit Batch

```bash
# Simple submission
python batch_cli.py submit urls.txt --name daily_batch

# Submit and wait for completion
python batch_cli.py submit urls.txt --name daily_batch --wait

# Check status
python batch_cli.py status JOB_ID

# Get results
python batch_cli.py results JOB_ID daily_batch
```

---

## 📖 Usage Methods

### Method 1: Command Line (Recommended for automation)

```bash
# Submit batch
python batch_cli.py submit urls.txt --name batch_$(date +%Y%m%d)

# List all jobs
python batch_cli.py list

# Check specific job
python batch_cli.py status JOB_ID

# Download results
python batch_cli.py results JOB_ID BATCH_NAME --show-preview
```

### Method 2: REST API

Start the batch API server:
```bash
python batch_api.py
# Runs on http://localhost:8001
```

**Submit batch:**
```bash
curl -X POST http://localhost:8001/batch/submit \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://example.com/article1",
      "https://example.com/article2"
    ],
    "batch_name": "my_batch",
    "wait_for_completion": false
  }'
```

**Check status:**
```bash
curl http://localhost:8001/batch/status/JOB_ID
```

**Get results:**
```bash
curl http://localhost:8001/batch/results/JOB_ID/BATCH_NAME
```

### Method 3: Python Script

```python
import asyncio
from batch_processor import process_batch_workflow

urls = [
    "https://www.reuters.com/...",
    "https://www.bloomberg.com/...",
]

results = asyncio.run(
    process_batch_workflow(
        urls=urls,
        gemini_key="YOUR_API_KEY",
        batch_name="my_batch",
        wait_for_completion=True
    )
)

for result in results:
    print(f"{result.page_title}: {result.sentiment}")
```

---

## ⚙️ Batch Processing Workflow

```
┌─────────────────┐
│  1. Extract     │  Fetch content from URLs
│     Content     │  (parallel, fast)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  2. Create      │  Generate JSONL batch file
│     Batch File  │  with all requests
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  3. Submit to   │  Upload to Google Gemini
│     Gemini API  │  Batch API
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  4. Wait for    │  Poll status every 60s
│     Completion  │  (usually 10-30 minutes)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  5. Download    │  Parse results and save
│     Results     │  to JSON
└─────────────────┘
```

**Typical Processing Time:**
- 100 URLs: ~5-10 minutes
- 1,000 URLs: ~15-30 minutes
- 10,000 URLs: ~2-4 hours

---

## 📁 File Structure

After running batch jobs:

```
batch_jobs/
├── batch_20250103_120000.jsonl          # Input requests
├── batch_20250103_120000_mapping.json   # URL mappings
├── batch_20250103_120000_job.json       # Job metadata
└── batch_20250103_120000_results.jsonl  # Raw results

results_batch_20250103_120000.json       # Parsed results
```

---

## 🔄 Daily Automation Example

### Cron Job for Daily Processing

```bash
# crontab -e
# Run daily at 2 AM
0 2 * * * cd /path/to/project && python daily_batch.py >> logs/batch.log 2>&1
```

**daily_batch.py:**
```python
import os
import asyncio
from datetime import datetime
from batch_processor import process_batch_workflow

def load_daily_urls():
    """Load URLs from your data source."""
    # Example: Read from database, API, or file
    urls = []
    # ... your logic to get URLs
    return urls

async def main():
    batch_name = f"daily_{datetime.now().strftime('%Y%m%d')}"
    urls = load_daily_urls()

    print(f"Processing {len(urls)} URLs in batch '{batch_name}'")

    results = await process_batch_workflow(
        urls=urls,
        gemini_key=os.getenv("GOOGLE_API_KEY"),
        batch_name=batch_name,
        wait_for_completion=True
    )

    # Save to database or file
    print(f"Completed: {len(results)} articles classified")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🆚 When to Use Each Method

### Use Real-time API (Current app.py) when:
- ✅ Need immediate results (< 10 seconds)
- ✅ Processing < 100 URLs at once
- ✅ User-facing application
- ✅ Interactive use cases

### Use Batch API when:
- ✅ Processing 100+ URLs at once
- ✅ Can wait 10-30 minutes for results
- ✅ Daily/scheduled processing
- ✅ Cost optimization is priority
- ✅ Processing historical data

### Hybrid Approach (Best):
1. **Real-time API** for user requests (app.py)
2. **Batch API** for bulk/daily processing
3. Save 50% on bulk operations while keeping real-time responsiveness

---

## 🎯 Best Practices

### 1. Batch Size
- **Optimal**: 500-1,000 URLs per batch
- **Maximum**: 1,000 URLs per batch (Gemini limit)
- For 10k URLs/day: Split into 10 batches of 1,000

### 2. Error Handling
```python
# Check status before retrieving results
status = processor.check_status(job_id)
if status['state'] != 'JOB_STATE_SUCCEEDED':
    print(f"Job not ready: {status['state']}")
```

### 3. Retry Failed Extractions
```python
# The processor logs failed URL extractions
# Review logs and resubmit failed URLs
```

### 4. Storage Management
```python
# Clean up old batch files periodically
import shutil
from pathlib import Path

batch_dir = Path("./batch_jobs")
old_batches = [f for f in batch_dir.glob("*.jsonl")
               if f.stat().st_mtime < (time.time() - 30*86400)]

for batch in old_batches:
    batch.unlink()  # Delete files older than 30 days
```

---

## 📈 Cost Optimization Tips

### 1. Combine with Content Truncation
```python
# In batch_processor.py, add truncation
def _truncate_content(content: str, max_chars: int = 8000) -> str:
    if len(content) <= max_chars:
        return content
    return content[:max_chars] + "... [truncated]"
```
**Additional savings**: 30-40%

### 2. Filter Non-Financial Articles First
```python
# Use cheap screening before batch submission
# Process only financial news
```
**Additional savings**: 50%+ if many non-financial

### 3. Cache Results by URL
```python
# Check cache before adding to batch
# Don't reprocess same URLs
```
**Additional savings**: 70-90% on repeats

### Combined Savings Potential:
- Batch API: 50% savings
- + Truncation: 70% savings
- + Screening: 85% savings
- + Caching: 95%+ savings

**Total monthly cost for 10k/day:**
- Without optimization: $330/month
- With all optimizations: $16-33/month
- **Savings: $297-314/month (90-95%)**

---

## 🐛 Troubleshooting

### "Job not found" error
- Job ID might be incorrect
- Check with: `python batch_cli.py list`

### "Job failed" status
- Check Google API quotas
- Review batch file for malformed requests
- Check logs in `./logs/`

### Results file not found
- Job might still be processing
- Check status first: `python batch_cli.py status JOB_ID`

### Extraction failures
- Some URLs might be behind paywalls
- Check timeout settings
- Review logs for specific URLs

---

## 📞 Support

For issues or questions:
1. Check logs in `./logs/`
2. Review job metadata in `./batch_jobs/*_job.json`
3. Verify API key and quotas
4. Check Google Gemini API status

---

## 🔗 References

- [Google Gemini Batch API Docs](https://ai.google.dev/gemini-api/docs/batch)
- [Pricing Information](https://ai.google.dev/pricing)
- [Quota Limits](https://ai.google.dev/gemini-api/docs/quota)

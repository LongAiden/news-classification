# Batch Processing System - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     YOUR APPLICATION                                 │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │              │  │              │  │              │             │
│  │   CLI Tool   │  │   REST API   │  │   Notebook   │             │
│  │ batch_cli.py │  │batch_api.py  │  │   Script     │             │
│  │              │  │              │  │              │             │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘             │
│         │                 │                 │                       │
│         └─────────────────┼─────────────────┘                       │
│                           │                                         │
│                           ▼                                         │
│              ┌────────────────────────────┐                         │
│              │   Core Engine              │                         │
│              │   batch_processor.py       │                         │
│              │                            │                         │
│              │  • prepare_batch           │                         │
│              │  • submit_batch            │                         │
│              │  • check_status            │                         │
│              │  • retrieve_results        │                         │
│              └────────────┬───────────────┘                         │
│                           │                                         │
│              ┌────────────┴───────────────┐                         │
│              │   Large-Scale Handler      │                         │
│              │   process_large_batch.py   │                         │
│              │                            │                         │
│              │  • Wave-based processing   │                         │
│              │  • Token limit management  │                         │
│              │  • Real-time fallback      │                         │
│              └────────────┬───────────────┘                         │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │  Google Gemini Batch API     │
              │                              │
              │  • Upload JSONL              │
              │  • Create batch job          │
              │  • Process asynchronously    │
              │  • Return results            │
              └──────────────────────────────┘
```

---

## Component Interactions

### 1. Submission Flow

```
User/App
   │
   ├─→ CLI: python batch_cli.py submit-contents data.json
   ├─→ API: POST /batch/submit-contents
   └─→ Script: processor.prepare_batch_from_contents(...)
           │
           ▼
    batch_processor.py
           │
           ├─→ Create JSONL file (Google format)
           │   ┌─────────────────────────────────┐
           │   │ {"key": "req_0",                │
           │   │  "request": {                   │
           │   │    "contents": [...],           │
           │   │    "systemInstruction": {...},  │
           │   │    "generationConfig": {...}    │
           │   │  }}                             │
           │   └─────────────────────────────────┘
           │
           ├─→ Save to ./batch_jobs/my_batch.jsonl
           ├─→ Save mapping to my_batch_mapping.json
           │
           ▼
    submit_batch(batch_file)
           │
           ├─→ Upload file to Google
           ├─→ Create batch job with model
           ├─→ Get job_id
           └─→ Save metadata to my_batch_job.json
           │
           ▼
    Return job_id to user
```

### 2. Monitoring Flow

```
User/App
   │
   └─→ CLI: python batch_cli.py status JOB_ID
           │
           ▼
    batch_processor.check_status(job_id)
           │
           ├─→ Query Google Gemini API
           └─→ Return:
               {
                 "state": "JOB_STATE_RUNNING",
                 "completed_count": 45,
                 "total_count": 100,
                 "create_time": "...",
                 "update_time": "..."
               }
           │
           ▼
    Display progress to user
```

### 3. Retrieval Flow

```
User/App
   │
   └─→ CLI: python batch_cli.py results JOB_ID BATCH_NAME
           │
           ▼
    batch_processor.retrieve_results(job_id, batch_name)
           │
           ├─→ 1. Check job state (must be SUCCEEDED)
           │
           ├─→ 2. Get output_file from batch job
           │
           ├─→ 3. Download results JSONL from Google
           │   └─→ Save to my_batch_results.jsonl
           │
           ├─→ 4. Load mapping (my_batch_mapping.json)
           │
           ├─→ 5. Parse each line in results JSONL:
           │       {
           │         "key": "req_0",
           │         "response": {
           │           "candidates": [{
           │             "content": {
           │               "parts": [{
           │                 "text": "{\"page_title\":\"...\",\"is_financial\":\"Yes\",...}"
           │               }]
           │             }
           │           }]
           │         }
           │       }
           │
           ├─→ 6. Convert to ClassificationResultFromText objects
           │
           └─→ Return list of results
           │
           ▼
    Save to results_my_batch.json
```

---

## Wave-Based Processing (12k+ Articles)

### Problem
Tier 1 has 10M enqueued tokens limit. With 2,800 tokens/article:
- 12,000 articles = 33.6M tokens
- Can't submit all at once (exceeds 10M limit)

### Solution
Split into 4 waves of ~3,200 articles each (~9M tokens per wave).

```
process_large_batch.py
        │
        ├─→ Calculate waves needed: 12,000 ÷ 3,200 = 4 waves
        │
        ├─→ Show cost estimate: $7.29
        │
        └─→ For each wave (sequential):
                │
                ├─→ WAVE 1 (3,200 articles, 8.96M tokens)
                │   │
                │   ├─→ Split into 3 batches of 1,000
                │   │   ├─→ Submit batch 1
                │   │   ├─→ Submit batch 2
                │   │   └─→ Submit batch 3
                │   │
                │   └─→ Wait for all 3 to complete (~40 min)
                │       └─→ Poll status every 30 seconds
                │
                ├─→ WAVE 2 (3,200 articles, 8.96M tokens)
                │   │
                │   ├─→ Split into 3 batches of 1,000
                │   └─→ Submit & wait (~40 min)
                │
                ├─→ WAVE 3 (3,200 articles, 8.96M tokens)
                │   │
                │   ├─→ Split into 3 batches of 1,000
                │   └─→ Submit & wait (~40 min)
                │
                └─→ WAVE 4 (2,400 articles, 6.72M tokens)
                    │
                    ├─→ Split into 2 batches of 1,000
                    └─→ Submit & wait (~30 min)
                │
                ▼
        Total: 12 batch jobs, 12,000 articles
        Time: ~2.5 hours
        Cost: $7.29
```

### Key: Sequential Wave Processing

```
Timeline:
─────────────────────────────────────────────────────────────
          Wave 1              Wave 2              Wave 3              Wave 4
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │ Submit 3     │    │ Submit 3     │    │ Submit 3     │    │ Submit 2     │
    │ batches      │    │ batches      │    │ batches      │    │ batches      │
    │              │    │              │    │              │    │              │
    │ Wait 40min   │    │ Wait 40min   │    │ Wait 40min   │    │ Wait 30min   │
    │ for complete │    │ for complete │    │ for complete │    │ for complete │
    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
         ▲                    ▲                    ▲                    ▲
         │                    │                    │                    │
    9M tokens           9M tokens           9M tokens           6.7M tokens
    (under limit)       (under limit)       (under limit)       (under limit)
```

**Why wait between waves?**
- Respects 10M enqueued tokens limit
- Prevents 429 RESOURCE_EXHAUSTED errors
- Ensures system stability

---

## Data Flow Diagram

### Batch Processing Journey

```
┌───────────────┐
│   Raw Data    │
│               │
│ • URLs        │
│ • JSON files  │
│ • Database    │
└───────┬───────┘
        │
        ▼
┌───────────────────────┐
│  prepare_batch_from_  │
│  • urls               │──→ Extract content from URLs (async)
│  • contents           │──→ Or use pre-crawled content
└───────┬───────────────┘
        │
        ▼
┌───────────────────────┐
│   JSONL Generation    │
│                       │
│ For each article:     │
│ {                     │
│   "key": "req_0",     │
│   "request": {        │
│     "contents": [     │
│       {               │
│         "role": "user"│
│         "parts": [{   │
│           "text": "..│
│         }]            │
│       }               │
│     ],                │
│     "systemInstr...": │
│     "generationCo..": │
│   }                   │
│ }                     │
└───────┬───────────────┘
        │
        ▼
┌───────────────────────┐
│  Local Storage        │
│                       │
│ ./batch_jobs/         │
│   ├─ my_batch.jsonl   │
│   ├─ my_batch_        │
│   │  mapping.json     │
│   └─ my_batch_        │
│      job.json         │
└───────┬───────────────┘
        │
        ▼
┌───────────────────────┐
│  submit_batch()       │
│                       │
│ 1. Upload JSONL       │──→ files.upload()
│ 2. Create batch job   │──→ batches.create()
│ 3. Get job_id         │──→ Return to caller
└───────┬───────────────┘
        │
        ▼
┌───────────────────────┐
│ Google Gemini         │
│ Batch API             │
│                       │
│ State: PENDING        │
│   ↓                   │
│ State: RUNNING        │
│   ↓ (10-30 minutes)   │
│ State: SUCCEEDED      │
└───────┬───────────────┘
        │
        ▼
┌───────────────────────┐
│  check_status()       │
│                       │
│ Poll every 30-60s     │
│ until SUCCEEDED       │
└───────┬───────────────┘
        │
        ▼
┌───────────────────────┐
│  retrieve_results()   │
│                       │
│ 1. Download results   │──→ files.get()
│ 2. Parse JSONL        │
│ 3. Convert to objects │
└───────┬───────────────┘
        │
        ▼
┌───────────────────────┐
│  Final Results        │
│                       │
│ • JSON file           │
│ • Python objects      │
│ • Analytics           │
└───────────────────────┘
```

---

## API Architecture (batch_api.py)

```
┌─────────────────────────────────────────────┐
│           FastAPI Application               │
├─────────────────────────────────────────────┤
│                                             │
│  POST /batch/submit                         │
│  │                                          │
│  ├─→ Parse URLs from request               │
│  ├─→ await prepare_batch_from_urls()       │
│  ├─→ submit_batch()                        │
│  └─→ Return job_id                         │
│                                             │
│  POST /batch/submit-contents                │
│  │                                          │
│  ├─→ Parse contents from request           │
│  ├─→ prepare_batch_from_contents()         │
│  ├─→ submit_batch()                        │
│  └─→ Return job_id                         │
│                                             │
│  GET /batch/status/{job_id}                 │
│  │                                          │
│  ├─→ check_status(job_id)                  │
│  └─→ Return state, progress               │
│                                             │
│  GET /batch/results/{job_id}/{batch_name}   │
│  │                                          │
│  ├─→ check_status() first                  │
│  ├─→ If SUCCEEDED: retrieve_results()      │
│  └─→ Return list of results               │
│                                             │
│  GET /batch/jobs                            │
│  │                                          │
│  ├─→ List ./batch_jobs/*_job.json         │
│  └─→ Return all job metadata              │
│                                             │
└─────────────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  batch_processor.py   │
         │  (Shared Instance)    │
         └───────────────────────┘
```

### Request/Response Flow

```
Client (Browser/App/cURL)
        │
        ├─→ POST /batch/submit-contents
        │   Body: {contents: [...], batch_name: "test"}
        │
        ▼
FastAPI Endpoint (batch_api.py)
        │
        ├─→ Validate request (Pydantic)
        ├─→ Convert to dict
        │
        ▼
batch_processor.prepare_batch_from_contents()
        │
        ├─→ Create JSONL
        └─→ Return batch_file path
        │
        ▼
batch_processor.submit_batch(batch_file)
        │
        ├─→ Upload to Google
        └─→ Return job_id
        │
        ▼
FastAPI Response
        │
        └─→ {
              "job_id": "...",
              "batch_name": "test",
              "status": "SUBMITTED",
              "message": "..."
            }
        │
        ▼
Client receives response
```

---

## File System Layout

```
news-classification/
│
├── batch_processing/           # Core batch system
│   ├── batch_processor.py      # Core engine
│   ├── batch_cli.py            # CLI interface
│   ├── batch_api.py            # REST API
│   ├── process_large_batch.py  # Large-scale handler
│   ├── README.md               # This guide
│   └── ARCHITECTURE.md         # Architecture doc
│
├── batch_jobs/                 # Generated batch files
│   ├── my_batch.jsonl          # Batch request file
│   ├── my_batch_mapping.json   # ID mappings
│   ├── my_batch_job.json       # Job metadata
│   └── my_batch_results.jsonl  # Downloaded results
│
├── batch_results/              # Large-scale results
│   ├── job_tracking.json       # All job IDs
│   └── [wave results...]       # Individual wave results
│
├── models.py                   # Data models
├── news_analyzer.py            # Content analyzer
└── .env                        # API keys
```

---

## Error Handling Flow

```
User Action
    │
    ▼
try:
    batch_processor.submit_batch()
    │
    ├─→ Upload file
    │   └─→ Error? → Retry logic
    │
    ├─→ Create batch job
    │   │
    │   ├─→ 429 RESOURCE_EXHAUSTED
    │   │   └─→ Too many active jobs
    │   │       └─→ Solution: Wait or cancel jobs
    │   │
    │   ├─→ 404 Not Found
    │   │   └─→ Model not available
    │   │       └─→ Solution: Use different model
    │   │
    │   └─→ 403 Forbidden
    │       └─→ No batch permissions
    │           └─→ Solution: Enable billing
    │
    └─→ Return job_id

except Exception as e:
    │
    ├─→ Log error
    ├─→ Save context
    └─→ Return user-friendly message
```

### Graceful Degradation

```
Batch API fails (429 or no access)
        │
        ├─→ Inform user
        │
        └─→ Offer alternatives:
            │
            ├─→ Real-time API (2x cost, works immediately)
            │
            ├─→ Retry later
            │
            └─→ Enable billing instructions
```

---

## Scalability Strategy

### Current Limits (Tier 1)

```
┌──────────────────────────────────────────────┐
│  Tier 1 Constraints                          │
├──────────────────────────────────────────────┤
│  • Concurrent batches: 100                   │
│  • Enqueued tokens: 10M                      │
│  • Real-time RPM: 2,000                      │
│  • Real-time RPD: Unlimited (*)              │
└──────────────────────────────────────────────┘
```

### Scaling Beyond 12k Articles

**For 100,000 articles:**

```
100,000 articles × 2,800 tokens = 280M tokens total

Wave strategy:
  280M ÷ 9M per wave = 32 waves

Timing:
  32 waves × 40 min per wave = 1,280 minutes = ~21 hours

Cost:
  280M tokens × $0.15/M = $42 input
  100k × 150 tokens × $1.25/M = $18.75 output
  Total: ~$60.75

Optimization:
  • Parallelize within each wave (3-4 batches)
  • Use multiple API keys (if available)
  • Consider Tier 2/3 upgrade for higher limits
```

---

## State Machine (Batch Job)

```
       ┌─────────────┐
       │   CREATED   │ (Local file created)
       └──────┬──────┘
              │
              ▼
       ┌─────────────┐
       │  UPLOADING  │ (files.upload())
       └──────┬──────┘
              │
              ▼
       ┌─────────────┐
       │   PENDING   │ (batches.create() returns)
       └──────┬──────┘
              │
              ▼
       ┌─────────────┐
       │   RUNNING   │ (Google processing)
       └──────┬──────┘
              │
              ├───────────────┬───────────────┐
              │               │               │
              ▼               ▼               ▼
       ┌──────────┐    ┌──────────┐   ┌──────────┐
       │ SUCCEEDED│    │  FAILED  │   │CANCELLED │
       └──────────┘    └──────────┘   └──────────┘
              │
              ▼
       ┌──────────────┐
       │   RESULTS    │ (retrieve_results())
       │  DOWNLOADED  │
       └──────────────┘
```

---

## Performance Optimization

### Batch API (Recommended)

```
Optimization Strategy:
    │
    ├─→ Use pre-crawled content
    │   (Skip URL extraction step)
    │
    ├─→ Batch size: 1,000 items
    │   (Balance between efficiency and manageability)
    │
    ├─→ Wave-based submission
    │   (Respect token limits)
    │
    └─→ Parallel wave monitoring
        (Check multiple jobs simultaneously)

Performance:
    • 12k articles in 2-4 hours
    • 50% cost savings vs real-time
    • Fully automated
```

### Real-Time API (Fast Option)

```
Optimization Strategy:
    │
    ├─→ Tier 1: 2,000 RPM
    │   (60 articles/second)
    │
    ├─→ Async processing
    │   (asyncio for parallel requests)
    │
    └─→ Rate limiting
        (Respect quotas)

Performance:
    • 12k articles in 6 minutes
    • 2x cost vs batch
    • Immediate results
```

---

## Security Considerations

```
┌──────────────────────────────────────────────┐
│  Security Measures                           │
├──────────────────────────────────────────────┤
│                                              │
│  ✓ API keys from environment variables       │
│  ✓ No hardcoded credentials                  │
│  ✓ Local file storage (not cloud exposed)    │
│  ✓ HTTPS for API communication                │
│  ✓ Input validation (Pydantic)                │
│  ✓ Rate limiting respect                      │
│  ✓ Error messages don't leak secrets          │
│                                              │
└──────────────────────────────────────────────┘
```

### Best Practices

```
1. Environment Variables
   ✓ Store in .env file
   ✓ Add .env to .gitignore
   ✓ Use python-dotenv to load

2. API Key Management
   ✓ One key per environment
   ✓ Rotate regularly
   ✓ Monitor usage in Google Cloud Console

3. Data Privacy
   ✓ Don't log article content
   ✓ Clean up batch files after processing
   ✓ Encrypt sensitive results if needed
```

---

## Summary

This batch processing system provides:

1. **Multiple Interfaces**
   - CLI for command-line users
   - REST API for web integration
   - Python library for notebooks/scripts

2. **Scalability**
   - Handles 12k+ articles automatically
   - Wave-based processing for token limits
   - Real-time fallback if batch unavailable

3. **Cost Efficiency**
   - 50% savings with Batch API
   - $7.29 for 12k articles vs $14.58 real-time

4. **Reliability**
   - Auto-retry on errors
   - Progress tracking
   - Resumable processing

5. **Flexibility**
   - Multiple models supported
   - Configurable batch sizes
   - Customizable prompts

**Recommended workflow:** Use `process_large_batch.py` for bulk processing (12k+ articles) and `batch_cli.py` for smaller batches (<1k articles).

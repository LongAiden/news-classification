# Processing 12,000 Articles - Tier 1 Analysis

## Your Configuration

- **Tier**: Tier 1 (billing enabled)
- **Articles**: 12,000
- **Average length**: 8-10k characters per article
- **Daily limit**: 400 articles (custom)

## Token Estimates (Updated)

| Metric | Per Article | For 12,000 Articles |
|--------|-------------|---------------------|
| **Characters** | 9,000 (average) | 108,000,000 |
| **Input tokens** | 2,800 | 33,600,000 (33.6M) |
| **Output tokens** | 150 | 1,800,000 (1.8M) |

**Note**: Your articles are 3x longer than initially estimated (9k vs 3.5k chars), so token costs are ~3x higher.

---

## Tier 1 Limits (From Your Screenshot)

### Gemini 2.0 Flash (Recommended for Batch)
- ✅ **RPM**: 2,000
- ✅ **TPM**: 4,000,000
- ✅ **RPD**: Unlimited (*)
- ⚠️ **Batch Enqueued Tokens**: **10,000,000** (Critical limit!)
- ✅ **Concurrent Batches**: 100

### The Critical Constraint: Enqueued Tokens

**Problem**: 10M enqueued tokens limit means you can only have ~3,200 articles in active batch jobs at once.

**Math**:
```
10,000,000 tokens ÷ 2,800 tokens/article = 3,571 articles max
Safe limit (90%): 9,000,000 ÷ 2,800 = 3,214 articles per wave
```

**For 12,000 articles, you need 4 waves:**
- Wave 1: 3,200 articles (8.96M tokens)
- Wave 2: 3,200 articles (8.96M tokens)
- Wave 3: 3,200 articles (8.96M tokens)
- Wave 4: 2,400 articles (6.72M tokens)

---

## Cost Comparison

### Option 1: Batch API (Wave-Based) ⭐ RECOMMENDED

**Pricing:**
- Input: $0.15 per 1M tokens
- Output: $1.25 per 1M tokens

**Cost Breakdown:**
```
Input:  33.6M tokens × $0.15/M = $5.04
Output:  1.8M tokens × $1.25/M = $2.25
──────────────────────────────────────
TOTAL:                          $7.29
──────────────────────────────────────
Per article:                    $0.00061
```

**Processing Strategy:**
- Enable billing first (one-time, 5 minutes)
- Process in 4 waves of ~3,200 articles each
- Each wave waits for previous to complete (respects 10M token limit)
- **Total time: 2-4 hours** (waves processed sequentially)

**Timeline:**
- Wave 1: Submit 3 batches → Wait 20-40 min → Complete
- Wave 2: Submit 3 batches → Wait 20-40 min → Complete
- Wave 3: Submit 3 batches → Wait 20-40 min → Complete
- Wave 4: Submit 2 batches → Wait 20-40 min → Complete

---

### Option 2: Real-Time API (Tier 1 Speed)

**Pricing:**
- Input: $0.30 per 1M tokens
- Output: $2.50 per 1M tokens

**Cost Breakdown:**
```
Input:  33.6M tokens × $0.30/M = $10.08
Output:  1.8M tokens × $2.50/M =  $4.50
──────────────────────────────────────
TOTAL:                          $14.58
──────────────────────────────────────
Per article:                    $0.00122
Extra vs Batch:                 $7.29 (2x)
```

**Processing Options:**

#### A. Fast Processing (2,000 RPM - Tier 1)
- Process at 2,000 requests/minute
- **Time: 6 minutes** for 12,000 articles
- Super fast, but costs 2x

#### B. Daily Limit (400/day)
- Process 400 articles per day
- **Time: 30 days**
- Auto-saves progress, resume each day
- Good for spread-out processing

---

## Detailed Cost at Scale

| Articles | Batch API (Wave) | Real-Time (Fast) | Real-Time (400/day) | Time (Batch) | Time (Real-time) |
|----------|------------------|------------------|---------------------|--------------|------------------|
| 400 | $0.24 | $0.49 | $0.49 | 20-40 min | 12 sec OR 1 day |
| 1,000 | $0.61 | $1.22 | $1.22 | 20-40 min | 30 sec OR 3 days |
| 3,200 | $1.94 | $3.89 | $3.89 | 30-60 min | 96 sec OR 8 days |
| **12,000** | **$7.29** | **$14.58** | **$14.58** | **2-4 hours** | **6 min OR 30 days** |

---

## Recommendation: Batch API with Waves

### Step 1: Enable Billing (One-Time)

If you haven't already:
1. Go to https://console.cloud.google.com/billing
2. Enable billing on your Google Cloud project
3. Wait 5-10 minutes for propagation
4. This unlocks full Batch API access

### Step 2: Process in Your Notebook

```python
import json
import asyncio
from process_large_batch import process_with_batch_api

# Load your 12k articles
with open('your_12k_articles.json') as f:
    items = json.load(f)

print(f"Loaded {len(items):,} articles")

# Process with wave-based batch API
job_ids = await process_with_batch_api(
    items,
    output_dir="./batch_results_12k",
    wait_for_waves=True  # Wait for each wave to complete (recommended)
)

print(f"✅ Submitted {len(job_ids)} batch jobs across 4 waves")
```

### Step 3: Monitor Progress

The script will:
1. Submit Wave 1 (3 batches, 3,200 articles)
2. Wait for Wave 1 to complete (~30-40 minutes)
3. Submit Wave 2 (3 batches, 3,200 articles)
4. Wait for Wave 2 to complete (~30-40 minutes)
5. Submit Wave 3 (3 batches, 3,200 articles)
6. Wait for Wave 3 to complete (~30-40 minutes)
7. Submit Wave 4 (2 batches, 2,400 articles)
8. Wait for Wave 4 to complete (~20-30 minutes)

**Total time: ~2-3 hours**

### Step 4: Collect Results

```python
# After all waves complete
from batch_processor import BatchProcessor
import json

processor = BatchProcessor(gemini_key=os.getenv('GOOGLE_API_KEY'))

# Load job tracking
with open('./batch_results_12k/job_tracking.json') as f:
    jobs = json.load(f)

# Collect all results
all_results = []
for job in jobs:
    print(f"Retrieving Wave {job['wave']} Batch {job['batch_num']}...")
    try:
        results = processor.retrieve_results(job['job_id'], job['batch_name'])
        all_results.extend([r.model_dump() for r in results])
        print(f"  ✓ Got {len(results)} results")
    except Exception as e:
        print(f"  ✗ Error: {e}")

# Save combined results
with open('results_12k_combined.json', 'w') as f:
    json.dump(all_results, f, indent=2, default=str)

print(f"\n✅ Total results: {len(all_results):,}/12,000")
```

---

## Alternative: Real-Time API (If Batch Fails)

If you can't get Batch API working:

```python
from process_large_batch import process_with_realtime_api

# Fast version (Tier 1: 2,000 RPM)
results = await process_with_realtime_api(
    items,
    rpm_limit=2000,  # Tier 1 speed
    items_per_day=12000  # Process all at once
)
# Cost: $14.58, Time: 6 minutes

# OR Daily limit version
results = await process_with_realtime_api(
    items,
    rpm_limit=15,
    items_per_day=400  # Process 400/day for 30 days
)
# Cost: $14.58, Time: 30 days
```

---

## Cost Summary

### Your Situation
- **12,000 articles** @ 9k chars each
- **Tier 1** with billing enabled

### Best Option: Batch API with Waves
- **Cost: $7.29**
- **Time: 2-4 hours**
- **Savings: $7.29** vs real-time
- **Setup: 5 min** (enable billing once)

### If "400/day" is a Hard Requirement

**Real-time API @ 400/day:**
- **Cost: $14.58** (for all 12k over 30 days)
- **Daily cost: $0.49** (for 400 articles)
- **Time: 30 days**

**OR Batch API @ 400/day:**
- Can't use batch for 400/day (batch needs larger volumes)
- Batch is designed for bulk processing, not daily trickle

---

## Files Updated

✅ **[process_large_batch.py](process_large_batch.py)** - Wave-based batch processing
- Splits 12k articles into 4 waves of ~3,200 each
- Respects 10M enqueued tokens limit
- Auto-waits between waves
- Tier 1 optimized (2,000 RPM for real-time)

✅ **[batch_processor.py](batch_processor.py)** - Core engine
- Fixed JSONL format (Google style)
- Flexible model selection
- Defaults to gemini-1.5-flash (more stable)

---

## Quick Start Command

```bash
# In your notebook
import json
import asyncio
from process_large_batch import process_with_batch_api

with open('your_12k.json') as f:
    items = json.load(f)

# This will handle everything automatically
await process_with_batch_api(items, wait_for_waves=True)
```

**Done!** The script handles wave management, waiting, and error recovery automatically.

---

## Summary Table

| Method | Cost | Time | Setup | Best For |
|--------|------|------|-------|----------|
| **Batch (Waves)** | **$7.29** | **2-4 hrs** | 5 min | **Bulk processing** |
| Real-time (Fast) | $14.58 | 6 min | None | Immediate results |
| Real-time (400/day) | $14.58 | 30 days | None | Daily processing |

**Recommendation**: Use batch API with waves. Saves $7.29 and completes in 2-4 hours.

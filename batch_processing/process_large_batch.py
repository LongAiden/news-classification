"""
Strategy for processing 12,000+ items efficiently.
Handles both batch API and real-time API with rate limiting.
"""

import os
import json
import asyncio
import time
from typing import List, Dict
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Configuration for Tier 1
BATCH_SIZE = 1000  # Items per batch job
REALTIME_RPM = 2000  # Tier 1: 2,000 RPM for gemini-2.0-flash
ITEMS_PER_DAY = 400  # Your daily limit (custom)

# Token estimates (based on 8-10k chars per article)
AVG_INPUT_TOKENS_PER_ARTICLE = 2800  # ~9k chars average
AVG_OUTPUT_TOKENS_PER_ARTICLE = 150  # Structured JSON output

# Tier 1 Batch Limits (from Google quotas)
BATCH_ENQUEUED_TOKENS_LIMIT = 10_000_000  # 10M tokens max in active batches
MAX_CONCURRENT_BATCHES = 100  # Google's hard limit

# Calculate safe batch wave size (90% of limit for safety margin)
SAFE_ENQUEUED_TOKENS = int(BATCH_ENQUEUED_TOKENS_LIMIT * 0.9)  # 9M tokens
MAX_ARTICLES_PER_WAVE = SAFE_ENQUEUED_TOKENS // AVG_INPUT_TOKENS_PER_ARTICLE  # ~3,200 articles


def split_into_batches(items: List[Dict], batch_size: int) -> List[List[Dict]]:
    """Split items into batches."""
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


async def process_with_batch_api(
    items: List[Dict],
    output_dir: str = "./batch_results",
    wait_for_waves: bool = True
):
    """
    Process large dataset using Batch API with wave-based submission.

    For 12,000 items with Tier 1 (10M enqueued tokens limit):
    - Split into waves of ~3,200 articles each (9M tokens per wave)
    - Process 4 waves sequentially to stay under enqueued token limit
    - Each wave has 3-4 batches of 1,000 items
    - Total cost: ~$6.30 (updated for 8-10k chars/article)
    - Total time: 2-4 hours (if waves processed sequentially)

    Args:
        items: List of items to process
        output_dir: Directory to save results
        wait_for_waves: If True, wait for each wave to complete before submitting next
    """
    from batch_processor import BatchProcessor

    print("=" * 80)
    print("PROCESSING WITH BATCH API (TIER 1 OPTIMIZED)")
    print("=" * 80)

    processor = BatchProcessor(gemini_key=os.getenv('GOOGLE_API_KEY'))

    # Calculate waves needed
    num_waves = (len(items) + MAX_ARTICLES_PER_WAVE - 1) // MAX_ARTICLES_PER_WAVE
    articles_per_wave_tokens = MAX_ARTICLES_PER_WAVE * AVG_INPUT_TOKENS_PER_ARTICLE

    print(f"\n📊 Tier 1 Batch Limits:")
    print(f"   Max enqueued tokens: {BATCH_ENQUEUED_TOKENS_LIMIT:,}")
    print(f"   Safe enqueued tokens: {SAFE_ENQUEUED_TOKENS:,} (90% of limit)")
    print(f"   Avg tokens per article: {AVG_INPUT_TOKENS_PER_ARTICLE:,}")
    print(f"   Max articles per wave: {MAX_ARTICLES_PER_WAVE:,}")

    print(f"\n📦 Processing Strategy:")
    print(f"   Total articles: {len(items):,}")
    print(f"   Articles per wave: ~{MAX_ARTICLES_PER_WAVE:,}")
    print(f"   Number of waves: {num_waves}")
    print(f"   Batches per wave: ~{MAX_ARTICLES_PER_WAVE // BATCH_SIZE}")

    # Cost estimate (updated for 8-10k chars)
    total_input_tokens = len(items) * AVG_INPUT_TOKENS_PER_ARTICLE
    total_output_tokens = len(items) * AVG_OUTPUT_TOKENS_PER_ARTICLE
    estimated_cost = (total_input_tokens / 1_000_000 * 0.15) + (total_output_tokens / 1_000_000 * 1.25)

    print(f"\n💰 Estimated cost: ${estimated_cost:.2f}")
    print(f"   Input: {total_input_tokens:,} tokens ({total_input_tokens/1_000_000:.1f}M)")
    print(f"   Output: {total_output_tokens:,} tokens ({total_output_tokens/1_000_000:.1f}M)")

    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Split into waves to respect enqueued token limit
    waves = []
    for wave_num in range(num_waves):
        start_idx = wave_num * MAX_ARTICLES_PER_WAVE
        end_idx = min(start_idx + MAX_ARTICLES_PER_WAVE, len(items))
        wave_items = items[start_idx:end_idx]
        waves.append(wave_items)

    all_job_ids = []

    # Process each wave
    for wave_num, wave_items in enumerate(waves, 1):
        print(f"\n{'='*80}")
        print(f"WAVE {wave_num}/{num_waves}: Processing {len(wave_items):,} articles")
        print(f"{'='*80}")

        wave_tokens = len(wave_items) * AVG_INPUT_TOKENS_PER_ARTICLE
        print(f"Wave tokens: {wave_tokens:,} / {SAFE_ENQUEUED_TOKENS:,} (safe limit)")

        # Split wave into batches
        batches = split_into_batches(wave_items, BATCH_SIZE)
        print(f"Split into {len(batches)} batches of ~{BATCH_SIZE} items")

        wave_job_ids = []

        # Submit all batches in this wave
        for i, batch in enumerate(batches, 1):
            batch_name = f"wave{wave_num:02d}_batch{i:03d}_{datetime.now().strftime('%Y%m%d_%H%M')}"

            print(f"\n  [{i}/{len(batches)}] Preparing {batch_name}...")

            try:
                # Prepare batch file
                batch_file = processor.prepare_batch_from_contents(batch, batch_name)
                print(f"     ✓ Batch file created")

                # Submit
                job_id = processor.submit_batch(batch_file)
                print(f"     ✓ Submitted: {job_id[:50]}...")

                job_info = {
                    'wave': wave_num,
                    'batch_num': i,
                    'batch_name': batch_name,
                    'job_id': job_id,
                    'item_count': len(batch),
                    'submitted_at': datetime.now().isoformat()
                }
                wave_job_ids.append(job_info)
                all_job_ids.append(job_info)

                # Save job tracking after each submission
                with open(output_path / 'job_tracking.json', 'w') as f:
                    json.dump(all_job_ids, f, indent=2)

                # Small delay to avoid rate limits on submission
                if i < len(batches):
                    await asyncio.sleep(2)

            except Exception as e:
                print(f"     ✗ Error submitting batch {i}: {e}")
                if "429" in str(e):
                    print(f"     ⚠️  Hit rate limit. Waiting 60 seconds...")
                    await asyncio.sleep(60)

        print(f"\n✅ Wave {wave_num} submitted: {len(wave_job_ids)} batches")

        # Wait for this wave to complete before starting next wave
        if wait_for_waves and wave_num < num_waves:
            print(f"\n⏳ Waiting for Wave {wave_num} to complete before submitting Wave {wave_num + 1}...")
            print(f"   This ensures we don't exceed the {BATCH_ENQUEUED_TOKENS_LIMIT:,} enqueued tokens limit")

            # Monitor wave completion
            while True:
                completed = 0
                failed = 0
                running = 0

                for job_info in wave_job_ids:
                    try:
                        status = processor.check_status(job_info['job_id'])
                        state = status['state']

                        if state == 'JOB_STATE_SUCCEEDED':
                            completed += 1
                        elif state in ['JOB_STATE_FAILED', 'JOB_STATE_CANCELLED']:
                            failed += 1
                        else:
                            running += 1
                    except:
                        pass

                print(f"   Wave {wave_num} status: {completed} completed, {running} running, {failed} failed")

                if completed + failed == len(wave_job_ids):
                    print(f"   ✅ Wave {wave_num} complete!")
                    break

                # Wait before checking again
                await asyncio.sleep(30)

    print(f"\n{'='*80}")
    print(f"✅ ALL WAVES SUBMITTED")
    print(f"{'='*80}")
    print(f"   Total batches: {len(all_job_ids)}")
    print(f"   Total articles: {len(items):,}")

    print(f"\n📊 Job tracking saved to: {output_path / 'job_tracking.json'}")

    print(f"\n⏳ Batches will complete in 10-30 minutes each")
    print(f"   You can check status with:")
    print(f"   python batch_cli.py status <JOB_ID>")

    print(f"\n🔄 To monitor all jobs:")
    print(f"""
import json
from batch_processor import BatchProcessor
processor = BatchProcessor(gemini_key=os.getenv('GOOGLE_API_KEY'))

with open('{output_path / 'job_tracking.json'}') as f:
    jobs = json.load(f)

for job in jobs:
    status = processor.check_status(job['job_id'])
    print(f"Wave {{job['wave']}} Batch {{job['batch_num']}}: {{status['state']}} ({{status['completed_count']}}/{{status['total_count']}})")
""")

    return all_job_ids


async def process_with_realtime_api(
    items: List[Dict],
    output_file: str = "results_realtime_large.json",
    rpm_limit: int = REALTIME_RPM,
    items_per_day: int = ITEMS_PER_DAY
):
    """
    Process large dataset using real-time API with rate limiting.

    For 12,000 items:
    - Respects RPM limits (15 RPM = 13-14 hours)
    - Can resume if interrupted
    - Total cost: ~$7.92 (2x batch)
    - Can split across multiple days if daily limits apply
    """
    from news_analyzer import get_analyzer

    print("=" * 80)
    print("PROCESSING WITH REAL-TIME API")
    print("=" * 80)

    # Cost estimate (updated for 8-10k chars per article)
    total_input_tokens = len(items) * AVG_INPUT_TOKENS_PER_ARTICLE
    total_output_tokens = len(items) * AVG_OUTPUT_TOKENS_PER_ARTICLE
    estimated_cost = (total_input_tokens / 1_000_000 * 0.30) + (total_output_tokens / 1_000_000 * 2.50)

    print(f"\n💰 Estimated cost: ${estimated_cost:.2f}")
    print(f"   Input: {total_input_tokens:,} tokens ({total_input_tokens/1_000_000:.1f}M)")
    print(f"   Output: {total_output_tokens:,} tokens ({total_output_tokens/1_000_000:.1f}M)")
    print(f"⏱️  Estimated time: {len(items) / rpm_limit / 60:.1f} hours at {rpm_limit} RPM")

    if rpm_limit >= 1000:
        print(f"   (Tier 1: {rpm_limit:,} RPM available)")

    if len(items) > items_per_day:
        days_needed = (len(items) + items_per_day - 1) // items_per_day
        print(f"⚠️  Daily limit: {items_per_day} items/day")
        print(f"   Need {days_needed} days to complete")

    # Load existing results if resuming
    results = []
    processed_ids = set()

    if Path(output_file).exists():
        print(f"\n📂 Found existing results, resuming...")
        with open(output_file) as f:
            results = json.load(f)
            processed_ids = {r.get('original_id', r.get('page_title')) for r in results}
        print(f"   Already processed: {len(processed_ids)} items")

    # Filter unprocessed items
    items_to_process = [item for item in items if item.get('id') not in processed_ids]
    print(f"\n📦 Items to process: {len(items_to_process)}/{len(items)}")

    if not items_to_process:
        print("\n✅ All items already processed!")
        return results

    # Calculate rate limiting
    seconds_per_request = 60 / rpm_limit
    print(f"\n⏱️  Rate limit: {rpm_limit} requests/minute ({seconds_per_request:.1f}s per request)")

    analyzer = get_analyzer()

    print(f"\n{'='*80}")
    print("PROCESSING")
    print(f"{'='*80}\n")

    start_time = time.time()
    today_count = 0

    for i, item in enumerate(items_to_process, 1):
        item_id = item.get('id', f'item_{i}')
        title = item.get('title', '')
        content = item.get('contents', '')

        # Check daily limit
        if today_count >= items_per_day:
            print(f"\n⚠️  Reached daily limit of {items_per_day} items")
            print(f"   Processed: {len(results)} total")
            print(f"   Remaining: {len(items_to_process) - i + 1}")
            print(f"\n💾 Progress saved to: {output_file}")
            print(f"   Resume tomorrow by running this script again")
            break

        print(f"[{len(results) + 1}/{len(items)}] {item_id}...", end=" ")

        try:
            result = await analyzer.analyze_with_contents(text=content, title=title)

            result_dict = result.model_dump()
            result_dict['original_id'] = item_id
            results.append(result_dict)

            print(f"✓ {result.is_financial} | {result.sentiment} | {result.confident_score:.1f}")

            today_count += 1

            # Save progress every 10 items
            if len(results) % 10 == 0:
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2, default=str)

            # Rate limiting
            if i < len(items_to_process):
                await asyncio.sleep(seconds_per_request)

        except Exception as e:
            print(f"✗ Error: {e}")
            results.append({
                'original_id': item_id,
                'error': str(e)
            })

            # Save on error
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)

    # Final save
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    elapsed = time.time() - start_time

    print(f"\n{'='*80}")
    print(f"✅ SESSION COMPLETE")
    print(f"{'='*80}")
    print(f"\n📊 Results:")
    print(f"   Processed this session: {today_count}")
    print(f"   Total processed: {len(results)}/{len(items)}")
    print(f"   Time elapsed: {elapsed/60:.1f} minutes")
    print(f"   Average: {elapsed/today_count:.1f}s per item")
    print(f"\n💾 Saved to: {output_file}")

    if len(results) < len(items):
        remaining = len(items) - len(results)
        print(f"\n⏭️  Remaining: {remaining} items")
        print(f"   Run again tomorrow to continue")

    return results


async def main():
    """Main entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python process_large_batch.py batch <input_file>")
        print("  python process_large_batch.py realtime <input_file>")
        print("\nExample:")
        print("  python process_large_batch.py batch batch_contents.json")
        return

    mode = sys.argv[1]
    input_file = sys.argv[2] if len(sys.argv) > 2 else "batch_contents.json"

    # Load data
    print(f"Loading data from {input_file}...")
    with open(input_file) as f:
        items = json.load(f)

    print(f"Loaded {len(items)} items\n")

    if mode == "batch":
        await process_with_batch_api(items)
    elif mode == "realtime":
        await process_with_realtime_api(items)
    else:
        print(f"Unknown mode: {mode}")
        print("Use 'batch' or 'realtime'")


if __name__ == "__main__":
    asyncio.run(main())

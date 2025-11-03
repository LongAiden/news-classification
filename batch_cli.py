#!/usr/bin/env python3
"""
Command-line tool for managing batch processing jobs.

Usage:
    python batch_cli.py submit urls.txt --name my_batch
    python batch_cli.py status JOB_ID
    python batch_cli.py results JOB_ID BATCH_NAME
    python batch_cli.py list
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path

from batch_processor import BatchProcessor, process_batch_workflow


def load_urls_from_file(file_path: str) -> list[str]:
    """Load URLs from a text file (one URL per line)."""
    with open(file_path) as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return urls


async def cmd_submit(args):
    """Submit a new batch job."""
    # Load URLs
    if args.urls_file:
        urls = load_urls_from_file(args.urls_file)
    elif args.urls:
        urls = args.urls
    else:
        print("Error: Provide either --urls-file or --urls")
        sys.exit(1)

    print(f"📦 Submitting batch with {len(urls)} URLs...")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not set")
        sys.exit(1)

    processor = BatchProcessor(gemini_key=api_key)

    # Prepare batch
    batch_file = await processor.prepare_batch_from_urls(urls, args.name)
    batch_name = Path(batch_file).stem

    # Submit
    job_id = processor.submit_batch(batch_file)

    print(f"\n✓ Batch submitted successfully!")
    print(f"  Job ID: {job_id}")
    print(f"  Batch name: {batch_name}")
    print(f"\nCheck status with: python batch_cli.py status {job_id}")

    # Wait if requested
    if args.wait:
        print(f"\n⏳ Waiting for completion...")
        success = processor.wait_for_completion(job_id, poll_interval=args.poll_interval)

        if success:
            print(f"\n✓ Batch completed!")
            print(f"Get results with: python batch_cli.py results {job_id} {batch_name}")
        else:
            print(f"\n✗ Batch failed or timed out")
            sys.exit(1)


def cmd_submit_contents(args):
    """Submit a new batch job with pre-crawled content."""
    # Load content from JSON file
    with open(args.contents_file) as f:
        contents = json.load(f)

    print(f"📦 Submitting batch with {len(contents)} pre-crawled items...")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not set")
        sys.exit(1)

    processor = BatchProcessor(gemini_key=api_key)

    # Prepare batch from contents (no URL extraction)
    batch_file = processor.prepare_batch_from_contents(contents, args.name)
    batch_name = Path(batch_file).stem

    # Submit
    job_id = processor.submit_batch(batch_file)

    print(f"\n✓ Batch submitted successfully!")
    print(f"  Job ID: {job_id}")
    print(f"  Batch name: {batch_name}")
    print(f"\nCheck status with: python batch_cli.py status {job_id}")

    # Wait if requested
    if args.wait:
        print(f"\n⏳ Waiting for completion...")
        success = processor.wait_for_completion(job_id, poll_interval=args.poll_interval)

        if success:
            print(f"\n✓ Batch completed!")
            print(f"Get results with: python batch_cli.py results {job_id} {batch_name}")
        else:
            print(f"\n✗ Batch failed or timed out")
            sys.exit(1)


def cmd_status(args):
    """Check status of a batch job."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not set")
        sys.exit(1)

    processor = BatchProcessor(gemini_key=api_key)
    status = processor.check_status(args.job_id)

    # Print status
    print(f"\n📊 Batch Job Status")
    print(f"{'='*50}")
    print(f"  Job ID: {status['job_id']}")
    print(f"  State: {status['state']}")
    print(f"  Progress: {status['completed_count']}/{status['total_count']}")

    if status['total_count'] > 0:
        progress = (status['completed_count'] / status['total_count']) * 100
        print(f"  Completion: {progress:.1f}%")

    print(f"  Created: {status['create_time']}")
    print(f"  Updated: {status['update_time']}")
    print(f"{'='*50}\n")

    if status['state'] == 'JOB_STATE_SUCCEEDED':
        print("✓ Job completed! Retrieve results with:")
        print(f"  python batch_cli.py results {args.job_id} BATCH_NAME")
    elif status['state'] == 'JOB_STATE_RUNNING':
        print("⏳ Job is still running. Check again later.")
    elif status['state'] == 'JOB_STATE_FAILED':
        print("✗ Job failed.")


def cmd_results(args):
    """Retrieve results from a completed job."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not set")
        sys.exit(1)

    processor = BatchProcessor(gemini_key=api_key)

    print(f"📥 Retrieving results for job {args.job_id}...")

    try:
        results = processor.retrieve_results(args.job_id, args.batch_name)

        print(f"\n✓ Retrieved {len(results)} results\n")

        # Save to JSON file
        output_file = f"results_{args.batch_name}.json"
        with open(output_file, 'w') as f:
            json.dump(
                [r.model_dump() for r in results],
                f,
                indent=2,
                default=str
            )

        print(f"💾 Results saved to: {output_file}")

        # Print summary
        print(f"\n📈 Summary:")
        financial_count = sum(1 for r in results if r.is_financial == "Yes")
        print(f"  Financial news: {financial_count}/{len(results)}")

        sentiments = {}
        for r in results:
            sentiments[r.sentiment] = sentiments.get(r.sentiment, 0) + 1

        print(f"  Sentiment breakdown:")
        for sentiment, count in sentiments.items():
            print(f"    {sentiment}: {count}")

        # Show first few results
        if args.show_preview:
            print(f"\n📰 First {min(3, len(results))} results:")
            for i, result in enumerate(results[:3], 1):
                print(f"\n  {i}. {result.page_title}")
                print(f"     Financial: {result.is_financial}")
                print(f"     Sentiment: {result.sentiment}")
                print(f"     Summary: {result.summary_en[:100]}...")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def cmd_list(args):
    """List all batch jobs."""
    batch_dir = Path("./batch_jobs")

    if not batch_dir.exists():
        print("No batch jobs found")
        return

    job_files = list(batch_dir.glob("*_job.json"))

    if not job_files:
        print("No batch jobs found")
        return

    print(f"\n📋 Batch Jobs ({len(job_files)} total)\n")
    print(f"{'Batch Name':<30} {'Job ID':<20} {'Status':<20} {'Submitted'}")
    print("=" * 100)

    for job_file in sorted(job_files, key=lambda x: x.stat().st_mtime, reverse=True):
        with open(job_file) as f:
            job_data = json.load(f)

        batch_name = job_file.stem.replace("_job", "")
        print(
            f"{batch_name:<30} "
            f"{job_data['job_id'][:18]:<20} "
            f"{job_data['status']:<20} "
            f"{job_data['submitted_at']}"
        )

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Batch processing CLI for news classification"
    )
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Submit command
    submit_parser = subparsers.add_parser('submit', help='Submit a new batch job')
    submit_parser.add_argument(
        'urls_file',
        nargs='?',
        help='Text file with URLs (one per line)'
    )
    submit_parser.add_argument(
        '--urls',
        nargs='+',
        help='URLs to process'
    )
    submit_parser.add_argument(
        '--name',
        help='Batch name (auto-generated if not provided)'
    )
    submit_parser.add_argument(
        '--wait',
        action='store_true',
        help='Wait for batch to complete'
    )
    submit_parser.add_argument(
        '--poll-interval',
        type=int,
        default=60,
        help='Polling interval in seconds (default: 60)'
    )

    # Submit contents command
    submit_contents_parser = subparsers.add_parser(
        'submit-contents',
        help='Submit batch with pre-crawled content (no URL extraction)'
    )
    submit_contents_parser.add_argument(
        'contents_file',
        help='JSON file with pre-crawled content (format: [{"id": "...", "title": "...", "contents": "..."}])'
    )
    submit_contents_parser.add_argument(
        '--name',
        help='Batch name (auto-generated if not provided)'
    )
    submit_contents_parser.add_argument(
        '--wait',
        action='store_true',
        help='Wait for batch to complete'
    )
    submit_contents_parser.add_argument(
        '--poll-interval',
        type=int,
        default=60,
        help='Polling interval in seconds (default: 60)'
    )

    # Status command
    status_parser = subparsers.add_parser('status', help='Check batch job status')
    status_parser.add_argument('job_id', help='Batch job ID')

    # Results command
    results_parser = subparsers.add_parser('results', help='Retrieve batch results')
    results_parser.add_argument('job_id', help='Batch job ID')
    results_parser.add_argument('batch_name', help='Batch name')
    results_parser.add_argument(
        '--show-preview',
        action='store_true',
        help='Show preview of first few results'
    )

    # List command
    list_parser = subparsers.add_parser('list', help='List all batch jobs')

    args = parser.parse_args()

    if args.command == 'submit':
        asyncio.run(cmd_submit(args))
    elif args.command == 'submit-contents':
        cmd_submit_contents(args)
    elif args.command == 'status':
        cmd_status(args)
    elif args.command == 'results':
        cmd_results(args)
    elif args.command == 'list':
        cmd_list(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

"""
Example usage of batch processing vs single processing.

This script demonstrates both methods and compares their performance.
"""

import os
import asyncio
import time
from datetime import datetime

from batch_processor import process_batch_workflow
from news_analyzer import NewsAnalyzer


# Example URLs (replace with your actual URLs)
EXAMPLE_URLS = [
    "https://www.reuters.com/business/finance/wall-street-week-ahead-investors-brace-volatility-2024-01-05/",
    "https://www.bloomberg.com/news/articles/2024-01-05/stock-market-today-dow-sp-live-updates",
    "https://www.cnbc.com/2024/01/05/stocks-making-the-biggest-moves-midday.html",
    # Add more URLs here...
]


async def single_processing_example():
    """Example: Process URLs one by one (real-time API)."""
    print("\n" + "="*60)
    print("🔄 SINGLE PROCESSING (Real-time API)")
    print("="*60)

    api_key = os.getenv("GOOGLE_API_KEY")
    analyzer = NewsAnalyzer(gemini_key=api_key)

    start_time = time.time()
    results = []

    for i, url in enumerate(EXAMPLE_URLS, 1):
        print(f"\nProcessing {i}/{len(EXAMPLE_URLS)}: {url}")

        try:
            result = await analyzer.analyze_with_url(url)
            results.append(result)
            print(f"  ✓ {result.page_title}")
            print(f"    Financial: {result.is_financial}, Sentiment: {result.sentiment}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

    elapsed = time.time() - start_time

    print(f"\n{'─'*60}")
    print(f"✓ Completed: {len(results)}/{len(EXAMPLE_URLS)} articles")
    print(f"⏱️  Time: {elapsed:.1f} seconds ({elapsed/len(EXAMPLE_URLS):.1f}s per URL)")
    print(f"💰 Cost: ~$0.0033 per article (standard pricing)")
    print(f"   Total: ~${len(EXAMPLE_URLS) * 0.0033:.2f}")
    print("="*60 + "\n")

    return results


async def batch_processing_example():
    """Example: Process URLs in batch (50% cheaper)."""
    print("\n" + "="*60)
    print("⚡ BATCH PROCESSING (50% cheaper)")
    print("="*60)

    api_key = os.getenv("GOOGLE_API_KEY")
    batch_name = f"example_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print(f"\n📦 Submitting batch of {len(EXAMPLE_URLS)} URLs...")
    print(f"   Batch name: {batch_name}")

    start_time = time.time()

    results = await process_batch_workflow(
        urls=EXAMPLE_URLS,
        gemini_key=api_key,
        batch_name=batch_name,
        wait_for_completion=True  # Set False for async processing
    )

    elapsed = time.time() - start_time

    if results:
        print(f"\n✓ Batch completed!")
        print(f"\n{'─'*60}")
        print(f"Results:")
        for i, result in enumerate(results[:5], 1):  # Show first 5
            print(f"  {i}. {result.page_title}")
            print(f"     Financial: {result.is_financial}, Sentiment: {result.sentiment}")
            print(f"     Summary: {result.summary_en[:80]}...")

        if len(results) > 5:
            print(f"  ... and {len(results) - 5} more")

        print(f"\n{'─'*60}")
        print(f"✓ Completed: {len(results)}/{len(EXAMPLE_URLS)} articles")
        print(f"⏱️  Time: {elapsed:.1f} seconds")
        print(f"💰 Cost: ~$0.00165 per article (batch pricing - 50% cheaper)")
        print(f"   Total: ~${len(EXAMPLE_URLS) * 0.00165:.2f}")
        print(f"   💵 Savings: ~${len(EXAMPLE_URLS) * (0.0033 - 0.00165):.2f} vs single processing")
        print("="*60 + "\n")

        return results
    else:
        print("\n✗ Batch processing failed")
        return None


async def comparison_demo():
    """Run both methods and compare."""
    print("\n" + "="*60)
    print("📊 COMPARISON: SINGLE vs BATCH PROCESSING")
    print("="*60)
    print(f"\nProcessing {len(EXAMPLE_URLS)} URLs using both methods...")
    print("\nNote: Batch processing takes longer initially but is 50% cheaper")
    print("      For large volumes (1000+ URLs), batch is much more cost-effective")

    # Run single processing
    print("\n" + "─"*60)
    print("Method 1: Single Processing")
    print("─"*60)
    single_results = await single_processing_example()

    # Run batch processing
    print("\n" + "─"*60)
    print("Method 2: Batch Processing")
    print("─"*60)
    batch_results = await batch_processing_example()

    # Summary
    print("\n" + "="*60)
    print("📈 COMPARISON SUMMARY")
    print("="*60)
    print("\n┌─────────────────────┬──────────────┬──────────────┐")
    print("│ Metric              │ Single       │ Batch        │")
    print("├─────────────────────┼──────────────┼──────────────┤")
    print(f"│ Cost per URL        │ $0.00330     │ $0.00165     │")
    print(f"│ Cost for {len(EXAMPLE_URLS):2d} URLs    │ ${len(EXAMPLE_URLS) * 0.0033:>11.2f} │ ${len(EXAMPLE_URLS) * 0.00165:>11.2f} │")
    print(f"│ Speed (latency)     │ ~5s per URL  │ Batch time   │")
    print(f"│ Best for            │ Real-time    │ Bulk/Daily   │")
    print("└─────────────────────┴──────────────┴──────────────┘")

    print("\n💡 Recommendation:")
    print("  • Use SINGLE processing for: Real-time user requests (<100 URLs)")
    print("  • Use BATCH processing for: Daily bulk processing (100+ URLs)")
    print("  • Hybrid approach: Real-time API + scheduled batch jobs")

    print("\n💰 Annual Savings (for 10,000 URLs/day):")
    daily_savings = 10000 * (0.0033 - 0.00165)
    print(f"  • Daily: ${daily_savings:.2f}")
    print(f"  • Monthly: ${daily_savings * 30:.2f}")
    print(f"  • Annual: ${daily_savings * 365:.2f}")

    print("\n" + "="*60 + "\n")


async def quick_test():
    """Quick test with just the URLs provided."""
    if not EXAMPLE_URLS:
        print("⚠️  No URLs provided. Please add URLs to EXAMPLE_URLS list.")
        return

    print("\n🚀 Running quick batch test...")
    print(f"   URLs: {len(EXAMPLE_URLS)}")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ Error: GOOGLE_API_KEY not set")
        print("   Set it with: export GOOGLE_API_KEY='your-key'")
        return

    # Just run batch processing
    await batch_processing_example()


if __name__ == "__main__":
    import sys

    # Check if API key is set
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Error: GOOGLE_API_KEY environment variable not set")
        print("\nSet it with:")
        print("  export GOOGLE_API_KEY='your-api-key'")
        sys.exit(1)

    # Check if URLs are provided
    if not EXAMPLE_URLS or len(EXAMPLE_URLS) < 2:
        print("⚠️  Warning: Only a few example URLs provided")
        print("   Add more URLs to EXAMPLE_URLS list for a better demo")

    # Run the demo
    print("\n" + "="*60)
    print("🎯 BATCH PROCESSING DEMO")
    print("="*60)
    print("\nChoose a mode:")
    print("  1. Quick test (batch processing only)")
    print("  2. Full comparison (single vs batch)")
    print("  3. Single processing only")
    print("  4. Batch processing only")

    try:
        choice = input("\nEnter choice (1-4, default=1): ").strip() or "1"

        if choice == "1":
            asyncio.run(quick_test())
        elif choice == "2":
            asyncio.run(comparison_demo())
        elif choice == "3":
            asyncio.run(single_processing_example())
        elif choice == "4":
            asyncio.run(batch_processing_example())
        else:
            print("Invalid choice")
    except KeyboardInterrupt:
        print("\n\n✋ Interrupted by user")

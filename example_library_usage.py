#!/usr/bin/env python3
"""
Example script demonstrating how to use news-classification as a library.

This shows how to import and use the analyzer programmatically from another project.
"""

import asyncio
import os
from dotenv import load_dotenv

# Import from the library
from news_analyzer import NewsAnalyzer, get_analyzer, shutdown_analyzer
from models import ClassificationResult

load_dotenv()


async def example_1_basic_usage():
    """Example 1: Basic usage with manual instance management."""
    print("\n=== Example 1: Basic Usage ===")

    analyzer = NewsAnalyzer(
        gemini_key=os.getenv("GOOGLE_API_KEY"),
        max_input_chars=8000,
        fetch_timeout=10.0,
        llm_timeout=30.0,
    )

    await analyzer.start()

    try:
        # Classify from URL
        result = await analyzer.analyze_with_url(
            "https://www.cnbc.com/2024/01/15/starbucks-leans-on-discounts-china.html",
            fetch_timeout=10.0,
            llm_timeout=30.0,
        )

        print(f"✓ Financial: {result.is_financial}")
        print(f"✓ Sentiment: {result.sentiment}")
        print(f"✓ Companies: {', '.join(result.companies)}")
        print(f"✓ Summary: {result.summary_en[:100]}...")

    finally:
        await analyzer.shutdown()


async def example_2_singleton_pattern():
    """Example 2: Using singleton pattern (recommended for web apps)."""
    print("\n=== Example 2: Singleton Pattern ===")

    # get_analyzer() returns a cached instance
    analyzer = get_analyzer()

    # Classify raw text
    result = await analyzer.analyze_with_contents(
        title="Apple Reports Record Earnings",
        text="""
        Apple Inc. reported record quarterly earnings today, beating Wall Street expectations.
        The tech giant posted revenue of $123.9 billion, up 8% year-over-year, driven by
        strong iPhone sales and growing services revenue. CEO Tim Cook highlighted the
        company's expansion in emerging markets as a key growth driver.
        """,
        llm_timeout=30.0,
    )

    print(f"✓ Financial: {result.is_financial}")
    print(f"✓ Sentiment: {result.sentiment}")
    print(f"✓ Score: {result.confident_score}/10")
    print(f"✓ Sectors: {', '.join(result.sector)}")

    # Cleanup when done
    await shutdown_analyzer()


async def example_3_concurrent_processing():
    """Example 3: Process multiple articles concurrently."""
    print("\n=== Example 3: Concurrent Processing ===")

    analyzer = get_analyzer()

    articles = [
        {
            "title": "Tesla Stock Surges on Earnings Beat",
            "text": "Tesla shares jumped 12% after the company reported better-than-expected quarterly earnings...",
        },
        {
            "title": "Federal Reserve Holds Rates Steady",
            "text": "The Federal Reserve announced it would maintain current interest rates, citing mixed economic signals...",
        },
        {
            "title": "Amazon Expands Cloud Services",
            "text": "Amazon Web Services launched three new data centers in Asia, expanding its cloud computing footprint...",
        },
    ]

    # Process all articles concurrently
    tasks = [
        analyzer.analyze_with_contents(
            title=article["title"], text=article["text"], llm_timeout=30.0
        )
        for article in articles
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"✗ Article {i+1} failed: {result}")
        else:
            print(
                f"✓ Article {i+1}: {articles[i]['title'][:50]}... → {result.sentiment}"
            )

    await shutdown_analyzer()


async def example_4_error_handling():
    """Example 4: Proper error handling."""
    print("\n=== Example 4: Error Handling ===")

    analyzer = get_analyzer()

    # Try to fetch an invalid URL
    try:
        result = await analyzer.analyze_with_url(
            "https://invalid-url-that-does-not-exist.com/article",
            fetch_timeout=5.0,
        )
    except TimeoutError as e:
        print(f"✓ Caught timeout: {e}")
    except ValueError as e:
        print(f"✓ Caught value error: {e}")
    except Exception as e:
        print(f"✓ Caught unexpected error: {e}")

    # Try with empty text
    try:
        result = await analyzer.analyze_with_contents(title="Empty", text="")
    except ValueError as e:
        print(f"✓ Caught empty text error: {e}")

    await shutdown_analyzer()


async def main():
    """Run all examples."""
    print("=" * 60)
    print("News Classification Library - Usage Examples")
    print("=" * 60)

    # Check if API key is set
    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GEMINI_API_KEY"):
        print("\n❌ Error: GOOGLE_API_KEY or GEMINI_API_KEY not set!")
        print("Set it in .env file or export GOOGLE_API_KEY='your-key'")
        return

    # Run examples
    await example_1_basic_usage()
    await example_2_singleton_pattern()
    await example_3_concurrent_processing()
    await example_4_error_handling()

    print("\n" + "=" * 60)
    print("✓ All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

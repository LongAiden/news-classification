"""
Batch processing script for entity extraction from articles.

This script processes articles that haven't had entity extraction yet
and extracts entities (people, organizations, locations) using Gemini NER.

Usage:
    python batch_processing/entity_batch.py [--limit LIMIT] [--verbose]

Environment Variables:
    GOOGLE_API_KEY: Google Gemini API key (required)
    SUPABASE_URL: Supabase URL (required)
    SUPABASE_SERVICE_KEY: Supabase service role key (required)
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path to import entity_extraction module
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from entity_extraction import extract_entities, store_entities, mark_article_entities_extracted
from entity_extraction.storage import get_articles_without_entities, get_supabase_client

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def process_article_batch(limit: int = 50) -> dict:
    """
    Process a batch of articles for entity extraction.

    Args:
        limit: Maximum number of articles to process (default: 50)

    Returns:
        Dictionary with batch processing stats
    """
    logger.info(f"Starting entity extraction batch processing (limit: {limit})")

    # Validate environment variables
    required_vars = ["GOOGLE_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    # Get Supabase client
    supabase = get_supabase_client()

    # Fetch articles without entity extraction
    articles = await get_articles_without_entities(limit=limit, supabase=supabase)

    if not articles:
        logger.info("No articles found requiring entity extraction")
        return {
            "articles_processed": 0,
            "articles_failed": 0,
            "total_entities_extracted": 0,
            "total_entities_created": 0,
            "total_entities_linked": 0,
        }

    logger.info(f"Found {len(articles)} articles to process")

    # Process statistics
    stats = {
        "articles_processed": 0,
        "articles_failed": 0,
        "total_entities_extracted": 0,
        "total_entities_created": 0,
        "total_entities_linked": 0,
        "total_duplicates_found": 0,
    }

    # Process each article
    for idx, article in enumerate(articles, 1):
        article_id = article["id"]
        title = article["title"]

        try:
            logger.info(
                f"[{idx}/{len(articles)}] Processing article: {title[:60]}..."
            )

            # Extract entities using Gemini
            extraction_result = await extract_entities(
                content=article["content"],
                title=title,
                timeout_seconds=30.0,
            )

            entities_count = len(extraction_result.entities)
            logger.info(f"  → Extracted {entities_count} entities")

            # Store entities in database
            storage_stats = await store_entities(
                article_id=article_id,
                entities=extraction_result.entities,
                supabase=supabase,
            )

            # Mark article as processed
            await mark_article_entities_extracted(
                article_id=article_id,
                supabase=supabase,
            )

            # Update stats
            stats["articles_processed"] += 1
            stats["total_entities_extracted"] += entities_count
            stats["total_entities_created"] += storage_stats["entities_created"]
            stats["total_entities_linked"] += storage_stats["entities_linked"]
            stats["total_duplicates_found"] += storage_stats["duplicates_found"]

            logger.info(
                f"  ✓ Article processed successfully "
                f"({storage_stats['entities_created']} created, "
                f"{storage_stats['duplicates_found']} duplicates)"
            )

        except Exception as e:
            logger.error(f"  ✗ Failed to process article {article_id}: {e}")
            stats["articles_failed"] += 1
            continue

    # Log final summary
    logger.info("═" * 80)
    logger.info("Batch Processing Summary:")
    logger.info(f"  Articles Processed: {stats['articles_processed']}")
    logger.info(f"  Articles Failed: {stats['articles_failed']}")
    logger.info(f"  Total Entities Extracted: {stats['total_entities_extracted']}")
    logger.info(f"  New Entities Created: {stats['total_entities_created']}")
    logger.info(f"  Entity Links Created: {stats['total_entities_linked']}")
    logger.info(f"  Duplicate Entities Found: {stats['total_duplicates_found']}")
    logger.info("═" * 80)

    return stats


async def main():
    """Main entry point for batch processing."""
    parser = argparse.ArgumentParser(
        description="Batch process articles for entity extraction using Gemini NER"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of articles to process (default: 50)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    try:
        stats = await process_article_batch(limit=args.limit)

        # Exit with appropriate code
        if stats["articles_failed"] > 0:
            sys.exit(1)  # Partial failure
        else:
            sys.exit(0)  # Success

    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

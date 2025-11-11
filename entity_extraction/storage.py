"""Database storage for extracted entities with deduplication logic."""

from __future__ import annotations

import logging
import os
from typing import Optional
from uuid import UUID

from dotenv import load_dotenv
from supabase import Client, create_client

from .extractor import ExtractedEntity, normalize_entity_name

load_dotenv()

logger = logging.getLogger(__name__)


def get_supabase_client() -> Client:
    """
    Create and return Supabase client using service role key.

    Returns:
        Supabase client instance

    Raises:
        ValueError: If environment variables are not set
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_service_key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables must be set"
        )

    return create_client(supabase_url, supabase_service_key)


async def store_entities(
    article_id: str | UUID,
    entities: list[ExtractedEntity],
    supabase: Optional[Client] = None,
) -> dict:
    """
    Store extracted entities in database with deduplication.

    This function:
    1. Normalizes entity names for deduplication
    2. Checks if entity already exists in entities table
    3. Creates new entity if not found, or increments mention_count
    4. Links entity to article via article_entities junction table

    Args:
        article_id: UUID of the article
        entities: List of extracted entities
        supabase: Optional Supabase client (creates new one if None)

    Returns:
        Dictionary with stats: {
            "entities_created": int,
            "entities_linked": int,
            "duplicates_found": int
        }

    Raises:
        Exception: If database operations fail
    """
    if supabase is None:
        supabase = get_supabase_client()

    article_id_str = str(article_id)

    stats = {
        "entities_created": 0,
        "entities_linked": 0,
        "duplicates_found": 0,
    }

    for entity in entities:
        try:
            # Normalize entity name for deduplication
            canonical_name = normalize_entity_name(entity.text, entity.entity_type)

            # Check if entity already exists
            existing_response = (
                supabase.table("entities")
                .select("id, mention_count")
                .eq("canonical_name", canonical_name)
                .eq("entity_type", entity.entity_type)
                .execute()
            )

            if existing_response.data and len(existing_response.data) > 0:
                # Entity exists - get ID and increment mention count
                entity_id = existing_response.data[0]["id"]
                current_count = existing_response.data[0]["mention_count"] or 0

                # Increment mention count
                supabase.table("entities").update(
                    {"mention_count": current_count + 1}
                ).eq("id", entity_id).execute()

                stats["duplicates_found"] += 1
                logger.debug(
                    f"Entity '{canonical_name}' already exists. Incremented count to {current_count + 1}"
                )

            else:
                # Create new entity
                new_entity_response = (
                    supabase.table("entities")
                    .insert(
                        {
                            "canonical_name": canonical_name,
                            "entity_type": entity.entity_type,
                            "mention_count": 1,
                        }
                    )
                    .execute()
                )

                if not new_entity_response.data or len(new_entity_response.data) == 0:
                    raise Exception(f"Failed to create entity: {canonical_name}")

                entity_id = new_entity_response.data[0]["id"]
                stats["entities_created"] += 1
                logger.debug(f"Created new entity: {canonical_name} ({entity.entity_type})")

            # Link entity to article (avoid duplicates with UNIQUE constraint)
            try:
                supabase.table("article_entities").insert(
                    {
                        "article_id": article_id_str,
                        "entity_id": entity_id,
                        "entity_text": entity.text,
                        "confidence": entity.confidence,
                        "context": entity.context,
                    }
                ).execute()

                stats["entities_linked"] += 1
                logger.debug(f"Linked entity '{canonical_name}' to article {article_id_str}")

            except Exception as link_error:
                # If unique constraint fails, entity is already linked to this article
                if "duplicate key" in str(link_error).lower():
                    logger.debug(
                        f"Entity '{canonical_name}' already linked to article {article_id_str}"
                    )
                else:
                    raise

        except Exception as e:
            logger.error(
                f"Failed to store entity '{entity.text}' ({entity.entity_type}): {e}"
            )
            # Continue with next entity instead of failing entire batch
            continue

    logger.info(
        f"Entity storage complete for article {article_id_str}: "
        f"{stats['entities_created']} created, "
        f"{stats['entities_linked']} linked, "
        f"{stats['duplicates_found']} duplicates found"
    )

    return stats


async def mark_article_entities_extracted(
    article_id: str | UUID,
    supabase: Optional[Client] = None,
) -> None:
    """
    Mark article as having entities extracted.

    Args:
        article_id: UUID of the article
        supabase: Optional Supabase client (creates new one if None)

    Raises:
        Exception: If database update fails
    """
    if supabase is None:
        supabase = get_supabase_client()

    article_id_str = str(article_id)

    try:
        supabase.table("articles").update({"entities_extracted": True}).eq(
            "id", article_id_str
        ).execute()

        logger.debug(f"Marked article {article_id_str} as entities_extracted=True")

    except Exception as e:
        logger.error(
            f"Failed to mark article {article_id_str} as entities_extracted: {e}"
        )
        raise


async def get_articles_without_entities(
    limit: int = 50,
    supabase: Optional[Client] = None,
) -> list[dict]:
    """
    Fetch articles that haven't had entities extracted yet.

    Args:
        limit: Maximum number of articles to return (default: 50)
        supabase: Optional Supabase client (creates new one if None)

    Returns:
        List of article dictionaries with id, content, title fields

    Raises:
        Exception: If database query fails
    """
    if supabase is None:
        supabase = get_supabase_client()

    try:
        response = (
            supabase.table("articles")
            .select("id, content, title")
            .eq("entities_extracted", False)
            .limit(limit)
            .execute()
        )

        logger.info(
            f"Found {len(response.data) if response.data else 0} articles without entity extraction"
        )

        return response.data or []

    except Exception as e:
        logger.error(f"Failed to fetch articles without entities: {e}")
        raise

"""Entity extraction using Gemini AI for Named Entity Recognition (NER)."""

from __future__ import annotations

import logging
import os
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

load_dotenv()

logger = logging.getLogger(__name__)

# Configuration
LLM_MODEL = "gemini-2.0-flash-exp"  # Using latest Gemini model for better entity extraction
LLM_TIMEOUT_SECONDS = 30.0
MAX_INPUT_CHARACTERS = 8000  # Limit content to control costs and latency


class ExtractedEntity(BaseModel):
    """Single extracted entity with metadata."""

    text: str = Field(
        description="Entity text as it appears in the article (e.g., 'Apple Inc.', 'Tim Cook, CEO')"
    )
    canonical_name: str = Field(
        description="Normalized entity name for deduplication (e.g., 'Apple', 'Tim Cook')"
    )
    entity_type: Literal["PERSON", "ORGANIZATION", "LOCATION"] = Field(
        description="Entity type: PERSON, ORGANIZATION, or LOCATION"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0) based on context clarity and extraction certainty",
    )
    context: str = Field(
        description="Surrounding sentence or phrase providing context for the entity mention"
    )


class EntityExtractionResult(BaseModel):
    """Result containing all extracted entities from an article."""

    entities: list[ExtractedEntity] = Field(
        default_factory=list, description="List of extracted entities with metadata"
    )


# System prompt for entity extraction
ENTITY_EXTRACTION_PROMPT = """You are an expert Named Entity Recognition (NER) system specializing in financial news.

Your task is to extract ALL relevant entities from news articles and categorize them into three types:

1. **PERSON**: Individual people mentioned in the article
   - Include: CEOs, politicians, analysts, experts, investors
   - Canonical name: Remove titles and positions (e.g., "Tim Cook, CEO" → "Tim Cook")

2. **ORGANIZATION**: Companies, institutions, organizations
   - Include: Corporations, startups, government agencies, NGOs, unions
   - Canonical name: Remove legal suffixes (e.g., "Apple Inc." → "Apple", "Microsoft Corp." → "Microsoft")
   - EXCLUDE: Media outlets (unless they are the subject of the article), stock indices (S&P 500, NASDAQ)

3. **LOCATION**: Geographic entities
   - Include: Countries, cities, regions, continents
   - Canonical name: Use standard names (e.g., "New York City, NY" → "New York City", "UK" → "United Kingdom")

**Extraction Guidelines**:
- **Confidence scoring**:
  - 0.9-1.0: Entity is central to the article, clearly identified
  - 0.7-0.9: Entity is mentioned with clear context
  - 0.5-0.7: Entity is mentioned but context is ambiguous
  - 0.3-0.5: Possible entity, uncertain classification
  - 0.0-0.3: Very uncertain, likely false positive

- **Context**: Provide the surrounding sentence or phrase (20-80 words) that contains the entity mention

- **Quality over quantity**: Only extract entities that are:
  1. Clearly identifiable as PERSON, ORGANIZATION, or LOCATION
  2. Mentioned in a meaningful context (not just passing references)
  3. Relevant to the article's main topic

**Return JSON with entities array**. If no entities found, return empty array.

═══════════════════════════════════════════════════════════════════════════════
IMPORTANT: Return valid JSON following the EntityExtractionResult schema.
═══════════════════════════════════════════════════════════════════════════════
"""


async def extract_entities(
    content: str,
    title: str,
    timeout_seconds: float = LLM_TIMEOUT_SECONDS,
) -> EntityExtractionResult:
    """
    Extract entities from article using Gemini AI.

    Args:
        content: Article content (plain text)
        title: Article title
        timeout_seconds: LLM timeout in seconds (default: 30s)

    Returns:
        EntityExtractionResult containing list of extracted entities

    Raises:
        Exception: If API call fails or times out
    """
    # Trim content to max characters to control costs
    trimmed_content = content[:MAX_INPUT_CHARACTERS]
    if len(content) > MAX_INPUT_CHARACTERS:
        logger.warning(
            f"Content truncated from {len(content)} to {MAX_INPUT_CHARACTERS} characters"
        )

    # Build prompt
    user_prompt = f"""Extract all entities from this news article:

**Title**: {title}

**Content**:
{trimmed_content}

Return JSON with entities array following the EntityExtractionResult schema.
"""

    # Initialize Pydantic AI agent
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("GOOGLE_API_KEY environment variable not set")

    # Pass api_key via GoogleProvider (Pydantic AI v0.0.14+ requirement)
    provider = GoogleProvider(api_key=google_api_key)
    model = GoogleModel(LLM_MODEL, provider=provider)
    agent: Agent[None, EntityExtractionResult] = Agent(
        model=model,
        output_type=EntityExtractionResult,  # Changed from result_type to output_type
        instructions=ENTITY_EXTRACTION_PROMPT,  # Changed from system_prompt to instructions
    )

    # Run extraction with timeout
    try:
        logger.info(f"Extracting entities from article: {title[:50]}...")

        result = await agent.run(
            user_prompt,
            message_history=[],
        )

        logger.info(
            f"Extracted {len(result.output.entities)} entities from article: {title[:50]}"
        )

        return result.output

    except Exception as e:
        logger.error(f"Entity extraction failed for article '{title[:50]}': {e}")
        raise


def normalize_entity_name(name: str, entity_type: str) -> str:
    """
    Normalize entity name for deduplication.

    Args:
        name: Original entity name
        entity_type: PERSON, ORGANIZATION, or LOCATION

    Returns:
        Normalized canonical name
    """
    name = name.strip()

    if entity_type == "ORGANIZATION":
        # Remove common legal suffixes
        suffixes = [
            "Inc.",
            "Inc",
            "Corp.",
            "Corp",
            "Ltd.",
            "Ltd",
            "LLC",
            "L.L.C.",
            "Limited",
            "Co.",
            "Company",
            "Technologies",
            "Tech",
        ]
        for suffix in suffixes:
            # Case-insensitive replacement at the end
            if name.lower().endswith(suffix.lower()):
                name = name[: -len(suffix)].strip()

    elif entity_type == "PERSON":
        # Remove titles and positions (after comma)
        if "," in name:
            name = name.split(",")[0].strip()
        # Remove common titles at the start
        titles = ["Mr.", "Ms.", "Mrs.", "Dr.", "Prof.", "CEO", "President"]
        for title in titles:
            if name.startswith(title + " "):
                name = name[len(title) + 1 :].strip()

    elif entity_type == "LOCATION":
        # Standardize common abbreviations
        replacements = {
            "U.S.": "United States",
            "US": "United States",
            "USA": "United States",
            "U.K.": "United Kingdom",
            "UK": "United Kingdom",
            "UAE": "United Arab Emirates",
        }
        for abbr, full in replacements.items():
            if name == abbr:
                name = full
                break

    return name.strip()

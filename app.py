from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Query

from models import ClassificationResult, TextClassificationRequest
from news_analyzer import NewsAnalyzer, get_analyzer, shutdown_analyzer
from entity_extraction import extract_entities, store_entities, mark_article_entities_extracted
from entity_extraction.storage import get_supabase_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    analyzer = get_analyzer()
    await analyzer.start()
    try:
        yield
    finally:
        await shutdown_analyzer()


app = FastAPI(title="News Classification API", version="1.1.0", lifespan=lifespan)


@app.get("/health")
def healthcheck() -> dict:
    return {"ok": True}


@app.get("/classify/url", response_model=ClassificationResult)
async def analyze_url(
    url: str = Query(
        ...,
        min_length=1,
        max_length=2083,
        description="Public article URL",
    ),
    fetch_timeout: Optional[float] = Query(
        default=None,
        ge=1.0,
        le=120.0,
        description="Override the timeout (seconds) used to download the article.",
    ),
    llm_timeout: Optional[float] = Query(
        default=None,
        ge=5.0,
        le=180.0,
        description="Override the timeout (seconds) used for the LLM call.",
    ),
    analyzer: NewsAnalyzer = Depends(get_analyzer),
) -> ClassificationResult:
    """Classify a news article fetched from a remote URL."""
    try:
        return await analyzer.analyze_with_url(
            str(url),
            fetch_timeout=fetch_timeout,
            llm_timeout=llm_timeout,
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@app.post("/classify/text", response_model=ClassificationResult)
async def analyze_text(
    request: TextClassificationRequest,
    analyzer: NewsAnalyzer = Depends(get_analyzer),
) -> ClassificationResult:
    """Classify raw article text supplied directly by the caller via JSON body."""
    try:
        return await analyzer.analyze_with_contents(request)
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


@app.post("/extract-entities")
async def extract_entities_endpoint(
    article_id: str = Query(
        ...,
        min_length=36,
        max_length=36,
        description="Article UUID to extract entities from",
    ),
    timeout_seconds: Optional[float] = Query(
        default=None,
        ge=5.0,
        le=180.0,
        description="Override the timeout (seconds) used for entity extraction.",
    ),
) -> dict:
    """
    Extract entities (people, organizations, locations) from article using Gemini NER.

    This endpoint:
    1. Fetches article content from database
    2. Extracts entities using Gemini AI
    3. Stores entities with deduplication
    4. Marks article as entities_extracted=True

    Returns:
        Dictionary with extracted entities and stats
    """
    try:
        # Get Supabase client
        supabase = get_supabase_client()

        # Fetch article from database
        article_response = (
            supabase.table("articles")
            .select("id, content, title")
            .eq("id", article_id)
            .single()
            .execute()
        )

        if not article_response.data:
            raise HTTPException(status_code=404, detail=f"Article {article_id} not found")

        article = article_response.data

        # Extract entities using Gemini
        extraction_result = await extract_entities(
            content=article["content"],
            title=article["title"],
            timeout_seconds=timeout_seconds or 30.0,
        )

        # Store entities in database
        stats = await store_entities(
            article_id=article["id"],
            entities=extraction_result.entities,
            supabase=supabase,
        )

        # Mark article as processed
        await mark_article_entities_extracted(
            article_id=article["id"],
            supabase=supabase,
        )

        return {
            "article_id": article["id"],
            "entities_count": len(extraction_result.entities),
            "entities": [
                {
                    "text": e.text,
                    "canonical_name": e.canonical_name,
                    "entity_type": e.entity_type,
                    "confidence": e.confidence,
                    "context": e.context[:100] + "..." if len(e.context) > 100 else e.context,
                }
                for e in extraction_result.entities
            ],
            "stats": stats,
        }

    except HTTPException:
        raise
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}") from exc


if __name__ == "__main__":
    # Optional: run with `python app.py`
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

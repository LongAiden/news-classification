from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Query

from models import ClassificationResult
from news_analyzer import NewsAnalyzer, get_analyzer, shutdown_analyzer


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
    text: str = Query(
        ...,
        min_length=20,
        max_length=100000,
        description="Plain-text contents of the article. Long inputs are auto-trimmed to control costs.",
    ),
    title: Optional[str] = Query(
        default=None,
        min_length=3,
        max_length=500,
        description="Optional headline for the article. Auto-derived from text when omitted.",
    ),
    llm_timeout_seconds: Optional[float] = Query(
        default=None,
        ge=5.0,
        le=180.0,
        description="Override the default timeout (seconds) used for the LLM call.",
    ),
    analyzer: NewsAnalyzer = Depends(get_analyzer),
) -> ClassificationResult:
    """Classify raw article text supplied directly by the caller."""
    try:
        return await analyzer.analyze_with_contents(
            text=text,
            title=title,
            llm_timeout=llm_timeout_seconds,
        )
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

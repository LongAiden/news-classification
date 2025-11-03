from __future__ import annotations

import os
import requests
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import HttpUrl

from models import ClassificationRequest, ClassificationResult
from news_analyzer import NewsAnalyzer


app = FastAPI(title="News Classification API", version="1.0.0")


def get_analyzer() -> NewsAnalyzer:
    """Get or create the NewsAnalyzer singleton instance."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "Missing API key. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable."
        )
    analyzer = NewsAnalyzer(gemini_key=api_key)
    return analyzer


@app.get("/health")
def healthcheck() -> dict:
    return {"ok": True}


@app.get("/classify/url", response_model=ClassificationResult)
async def analyze_url(url: HttpUrl = Query(..., description="Public article URL"),
                      timeout=int):
    """Classify a news article from URL (GET request)."""
    try:
        analyzer = get_analyzer()
        result = await analyzer.analyze_with_url(str(url))
        return result

    except requests.Timeout:
        raise HTTPException(status_code=504, detail="Upstream request timed out while fetching the URL.")
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        raise HTTPException(status_code=status, detail=f"HTTP error while fetching the URL: {exc}")
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Network error while fetching the URL: {exc}")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}")


@app.post("/classify/text", response_model=ClassificationResult)
async def analyze_text(text:str, title:str):
    """Classify a news article from URL (POST request)."""
    try:
        analyzer = get_analyzer()
        result = await analyzer.analyze_with_contents(text=text, title=title)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    # Optional: run with `python app.py`
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


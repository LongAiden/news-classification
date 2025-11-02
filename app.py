from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from pydantic import HttpUrl

from .models import ClassificationRequest, ClassificationResult
from .classifier import classify_url


app = FastAPI(title="News Classification (Draft)", version="0.1.0")


@app.get("/healthz")
def healthcheck() -> dict:
    return {"ok": True}


@app.get("/classify", response_model=ClassificationResult)
def classify_get(url: HttpUrl = Query(..., description="Public article URL")):
    try:
        result, _ = classify_url(str(url))
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/classify", response_model=ClassificationResult)
def classify_post(payload: ClassificationRequest):
    try:
        result, _ = classify_url(str(payload.url))
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


if __name__ == "__main__":
    # Optional: run with `python -m news_classification.app`
    import uvicorn

    uvicorn.run(
        "news_classification.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


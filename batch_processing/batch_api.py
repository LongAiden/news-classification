"""
FastAPI endpoints for batch processing.
"""

import os
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl, Field

from batch_processor import BatchProcessor, process_batch_workflow
from models import ClassificationResultFromText

# Initialize batch processor
GEMINI_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
batch_processor = BatchProcessor(gemini_key=GEMINI_KEY)

app = FastAPI(title="News Classification Batch API", version="1.0.0")


class ContentItem(BaseModel):
    """Single content item with title and contents."""
    id: str
    title: str
    contents: str


class BatchRequest(BaseModel):
    """Request model for batch processing with URLs."""
    urls: List[HttpUrl] = Field(..., min_items=1, max_items=1000)
    batch_name: Optional[str] = None
    wait_for_completion: bool = False


class BatchContentRequest(BaseModel):
    """Request model for batch processing with pre-crawled content."""
    contents: List[ContentItem] = Field(..., min_items=1, max_items=1000)
    batch_name: Optional[str] = None
    wait_for_completion: bool = False


class BatchSubmitResponse(BaseModel):
    """Response after batch submission."""
    job_id: str
    batch_name: str
    url_count: int
    status: str
    message: str


class BatchStatusResponse(BaseModel):
    """Batch job status response."""
    job_id: str
    state: str
    completed_count: int
    total_count: int
    progress_percent: float


class BatchResultsResponse(BaseModel):
    """Batch results response."""
    job_id: str
    results: List[ClassificationResultFromText]
    total_count: int


@app.post("/batch/submit", response_model=BatchSubmitResponse)
async def submit_batch(
    request: BatchRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit a batch of URLs for processing.

    - **Async mode** (wait_for_completion=False): Returns immediately with job_id
    - **Sync mode** (wait_for_completion=True): Waits for results (use for small batches)

    Cost: 50% cheaper than real-time API ($0.15 input, $1.25 output per 1M tokens)
    """
    try:
        urls = [str(url) for url in request.urls]

        # Prepare batch
        batch_file = await batch_processor.prepare_batch_from_urls(
            urls,
            batch_name=request.batch_name
        )
        batch_name = Path(batch_file).stem

        # Submit to Gemini
        job_id = batch_processor.submit_batch(batch_file)

        # If async mode, return immediately
        if not request.wait_for_completion:
            return BatchSubmitResponse(
                job_id=job_id,
                batch_name=batch_name,
                url_count=len(urls),
                status="SUBMITTED",
                message=f"Batch submitted. Use GET /batch/status/{job_id} to check progress"
            )

        # Sync mode: wait for completion
        success = batch_processor.wait_for_completion(job_id, poll_interval=30)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Batch processing failed or timed out"
            )

        return BatchSubmitResponse(
            job_id=job_id,
            batch_name=batch_name,
            url_count=len(urls),
            status="COMPLETED",
            message=f"Batch completed. Use GET /batch/results/{job_id}/{batch_name} to retrieve"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batch/submit-contents", response_model=BatchSubmitResponse)
def submit_batch_contents(
    request: BatchContentRequest,
    background_tasks: BackgroundTasks
):
    """
    Submit a batch with pre-crawled content (no URL crawling needed).

    - **Async mode** (wait_for_completion=False): Returns immediately with job_id
    - **Sync mode** (wait_for_completion=True): Waits for results (use for small batches)

    Cost: 50% cheaper than real-time API ($0.15 input, $1.25 output per 1M tokens)
    """
    try:
        # Convert ContentItem objects to dicts
        contents = [item.model_dump() for item in request.contents]

        # Prepare batch
        batch_file = batch_processor.prepare_batch_from_contents(
            contents,
            batch_name=request.batch_name
        )
        batch_name = Path(batch_file).stem

        # Submit to Gemini
        job_id = batch_processor.submit_batch(batch_file)

        # If async mode, return immediately
        if not request.wait_for_completion:
            return BatchSubmitResponse(
                job_id=job_id,
                batch_name=batch_name,
                url_count=len(contents),
                status="SUBMITTED",
                message=f"Batch submitted. Use GET /batch/status/{job_id} to check progress"
            )

        # Sync mode: wait for completion
        success = batch_processor.wait_for_completion(job_id, poll_interval=30)

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Batch processing failed or timed out"
            )

        return BatchSubmitResponse(
            job_id=job_id,
            batch_name=batch_name,
            url_count=len(contents),
            status="COMPLETED",
            message=f"Batch completed. Use GET /batch/results/{job_id}/{batch_name} to retrieve"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/batch/status/{job_id}", response_model=BatchStatusResponse)
def get_batch_status(job_id: str):
    """
    Check the status of a batch job.

    States:
    - JOB_STATE_PENDING: Job is queued
    - JOB_STATE_RUNNING: Job is processing
    - JOB_STATE_SUCCEEDED: Job completed successfully
    - JOB_STATE_FAILED: Job failed
    """
    try:
        status = batch_processor.check_status(job_id)

        progress = 0.0
        if status["total_count"] > 0:
            progress = (status["completed_count"] / status["total_count"]) * 100

        return BatchStatusResponse(
            job_id=job_id,
            state=status["state"],
            completed_count=status["completed_count"],
            total_count=status["total_count"],
            progress_percent=round(progress, 2)
        )

    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Job not found: {str(e)}")


@app.get("/batch/results/{job_id}/{batch_name}", response_model=BatchResultsResponse)
def get_batch_results(job_id: str, batch_name: str):
    """
    Retrieve results from a completed batch job.

    The batch must be in SUCCEEDED state to retrieve results.
    """
    try:
        # Check if completed
        status = batch_processor.check_status(job_id)

        if status["state"] != "JOB_STATE_SUCCEEDED":
            raise HTTPException(
                status_code=400,
                detail=f"Job not ready. Current state: {status['state']}"
            )

        # Retrieve results
        results = batch_processor.retrieve_results(job_id, batch_name)

        return BatchResultsResponse(
            job_id=job_id,
            results=results,
            total_count=len(results)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/batch/jobs")
def list_batch_jobs():
    """
    List all batch jobs (from local metadata files).
    """
    try:
        batch_dir = Path("./batch_jobs")
        job_files = list(batch_dir.glob("*_job.json"))

        jobs = []
        for job_file in job_files:
            import json
            with open(job_file) as f:
                job_data = json.load(f)
                jobs.append(job_data)

        return {"jobs": jobs, "total": len(jobs)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "batch_api"}


# Example usage documentation
@app.get("/")
def root():
    """API documentation."""
    return {
        "service": "News Classification Batch API",
        "version": "1.0.0",
        "cost_savings": "50% compared to real-time API",
        "endpoints": {
            "submit_batch": "POST /batch/submit",
            "check_status": "GET /batch/status/{job_id}",
            "get_results": "GET /batch/results/{job_id}/{batch_name}",
            "list_jobs": "GET /batch/jobs"
        },
        "pricing": {
            "input_tokens": "$0.15 per 1M tokens",
            "output_tokens": "$1.25 per 1M tokens",
            "vs_realtime": "50% cheaper"
        },
        "example": {
            "submit": {
                "method": "POST",
                "url": "/batch/submit",
                "body": {
                    "urls": [
                        "https://example.com/article1",
                        "https://example.com/article2"
                    ],
                    "batch_name": "my_batch",
                    "wait_for_completion": False
                }
            },
            "status": {
                "method": "GET",
                "url": "/batch/status/{job_id}"
            },
            "results": {
                "method": "GET",
                "url": "/batch/results/{job_id}/{batch_name}"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "batch_api:app",
        host="0.0.0.0",
        port=8001,  # Different port from main API
        reload=True
    )

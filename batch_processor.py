"""
Batch processing module for news classification using Google Gemini Batch API.

This module handles:
1. Creating batch jobs from URLs
2. Submitting to Gemini Batch API
3. Polling for completion
4. Retrieving and parsing results

Cost savings: ~50% compared to real-time API calls
"""

import os
import json
import time
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

import httpx
from google import generativeai as genai

from models import ClassificationResultFromText
from news_analyzer import NewsAnalyzer, LLM_MODEL, BATCH_LIMIT

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Handle batch processing of news URLs using Google Gemini Batch API."""

    def __init__(
        self,
        gemini_key: str,
        batch_dir: str = "./batch_jobs",
        max_batch_size: int = BATCH_LIMIT
    ):
        """
        Initialize batch processor.

        Args:
            gemini_key: Google API key
            batch_dir: Directory to store batch files
            max_batch_size: Maximum URLs per batch (Gemini limit)
        """
        self.api_key = gemini_key
        self.batch_dir = Path(batch_dir)
        self.batch_dir.mkdir(exist_ok=True)
        self.max_batch_size = max_batch_size

        # Initialize Gemini for batch API
        genai.configure(api_key=gemini_key)

        # NewsAnalyzer for content extraction
        self.analyzer = NewsAnalyzer(gemini_key=gemini_key)

        logger.info(f"✓ BatchProcessor initialized. Batch dir: {self.batch_dir}")

    async def prepare_batch_from_urls(
        self,
        urls: List[str],
        batch_name: Optional[str] = None
    ) -> str:
        """
        Extract content from URLs and prepare batch JSONL file.

        Args:
            urls: List of news article URLs
            batch_name: Optional name for the batch

        Returns:
            Path to the batch JSONL file
        """
        if len(urls) > self.max_batch_size:
            raise ValueError(
                f"Batch size {len(urls)} exceeds max {self.max_batch_size}. "
                f"Split into multiple batches."
            )

        batch_name = batch_name or f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Preparing batch '{batch_name}' with {len(urls)} URLs")

        # Extract content from all URLs concurrently
        extraction_tasks = [self.analyzer.extract_url(url) for url in urls]
        extractions = await asyncio.gather(*extraction_tasks, return_exceptions=True)

        # Build batch requests
        batch_requests = []
        url_mapping = {}  # custom_id -> url mapping

        for idx, (url, extraction) in enumerate(zip(urls, extractions)):
            if isinstance(extraction, Exception):
                logger.warning(f"Failed to extract {url}: {extraction}")
                continue

            title, content = extraction

            if not content:
                logger.warning(f"Empty content for {url}")
                continue

            custom_id = f"request_{idx}"
            url_mapping[custom_id] = url

            # Create batch request in Gemini format
            request = {
                "custom_id": custom_id,
                "method": "POST",
                "url": f"/v1/models/{LLM_MODEL}:generateContent",
                "body": {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "text": f"Title: {title}\n\nContent: {content}"
                                }
                            ]
                        }
                    ],
                    "systemInstruction": {
                        "parts": [
                            {
                                "text": self._get_system_prompt()
                            }
                        ]
                    },
                    "generationConfig": {
                        "response_mime_type": "application/json",
                        "response_schema": self._get_response_schema()
                    }
                }
            }

            batch_requests.append(request)

        # Write to JSONL file
        batch_file = self.batch_dir / f"{batch_name}.jsonl"
        with open(batch_file, 'w') as f:
            for req in batch_requests:
                f.write(json.dumps(req) + '\n')

        # Save URL mapping
        mapping_file = self.batch_dir / f"{batch_name}_mapping.json"
        with open(mapping_file, 'w') as f:
            json.dump(url_mapping, f, indent=2)

        logger.info(
            f"✓ Batch prepared: {len(batch_requests)}/{len(urls)} requests "
            f"written to {batch_file}"
        )

        return str(batch_file)

    def prepare_batch_from_contents(
        self,
        contents: List[Dict[str, str]],
        batch_name: Optional[str] = None
    ) -> str:
        """
        Prepare batch JSONL file from pre-crawled content (no URL extraction needed).

        Args:
            contents: List of dicts with keys 'id', 'title', 'contents'
            batch_name: Optional name for the batch

        Returns:
            Path to the batch JSONL file
        """
        if len(contents) > self.max_batch_size:
            raise ValueError(
                f"Batch size {len(contents)} exceeds max {self.max_batch_size}. "
                f"Split into multiple batches."
            )

        batch_name = batch_name or f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Preparing batch '{batch_name}' with {len(contents)} pre-crawled items")

        # Build batch requests
        batch_requests = []
        id_mapping = {}  # custom_id -> original id mapping

        for idx, item in enumerate(contents):
            item_id = item.get('id', f'item_{idx}')
            title = item.get('title', '')
            content = item.get('contents', '')

            if not content:
                logger.warning(f"Empty content for {item_id}")
                continue

            custom_id = f"request_{idx}"
            id_mapping[custom_id] = item_id

            # Create batch request in Gemini format
            request = {
                "custom_id": custom_id,
                "method": "POST",
                "url": f"/v1/models/{LLM_MODEL}:generateContent",
                "body": {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "text": f"Title: {title}\n\nContent: {content}"
                                }
                            ]
                        }
                    ],
                    "systemInstruction": {
                        "parts": [
                            {
                                "text": self._get_system_prompt()
                            }
                        ]
                    },
                    "generationConfig": {
                        "response_mime_type": "application/json",
                        "response_schema": self._get_response_schema()
                    }
                }
            }

            batch_requests.append(request)

        # Write to JSONL file
        batch_file = self.batch_dir / f"{batch_name}.jsonl"
        with open(batch_file, 'w') as f:
            for req in batch_requests:
                f.write(json.dumps(req) + '\n')

        # Save ID mapping
        mapping_file = self.batch_dir / f"{batch_name}_mapping.json"
        with open(mapping_file, 'w') as f:
            json.dump(id_mapping, f, indent=2)

        logger.info(
            f"✓ Batch prepared: {len(batch_requests)}/{len(contents)} requests "
            f"written to {batch_file}"
        )

        return str(batch_file)

    def submit_batch(self, batch_file_path: str) -> str:
        """
        Submit batch job to Google Gemini Batch API.

        Args:
            batch_file_path: Path to the batch JSONL file

        Returns:
            Batch job ID
        """
        logger.info(f"Submitting batch job: {batch_file_path}")

        # Upload batch file (specify MIME type for .jsonl files)
        batch_file = genai.upload_file(
            batch_file_path,
            mime_type="application/json"  # JSONL is treated as JSON
        )

        # Create batch job
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")

        batch_job = model.batch_predict(
            src=batch_file.uri,
            config=genai.types.BatchPredictionConfig(
                temperature=0.7,
                top_p=0.95,
            )
        )

        job_id = batch_job.name

        logger.info(f"✓ Batch job submitted. Job ID: {job_id}")
        logger.info(f"  Status: {batch_job.state}")

        # Save job metadata
        batch_name = Path(batch_file_path).stem
        metadata_file = self.batch_dir / f"{batch_name}_job.json"

        with open(metadata_file, 'w') as f:
            json.dump({
                "job_id": job_id,
                "batch_file": batch_file_path,
                "submitted_at": datetime.now().isoformat(),
                "status": str(batch_job.state)
            }, f, indent=2)

        return job_id

    def check_status(self, job_id: str) -> Dict:
        """
        Check status of a batch job.

        Args:
            job_id: Batch job ID

        Returns:
            Job status information
        """
        batch_job = genai.BatchJob(name=job_id)

        return {
            "job_id": job_id,
            "state": str(batch_job.state),
            "create_time": str(batch_job.create_time),
            "update_time": str(batch_job.update_time),
            "completed_count": batch_job.completed_count,
            "total_count": batch_job.total_count,
        }

    def wait_for_completion(
        self,
        job_id: str,
        poll_interval: int = 60,
        max_wait_time: int = 3600
    ) -> bool:
        """
        Wait for batch job to complete.

        Args:
            job_id: Batch job ID
            poll_interval: Seconds between status checks
            max_wait_time: Maximum time to wait in seconds

        Returns:
            True if completed successfully, False otherwise
        """
        logger.info(f"Waiting for batch job {job_id} to complete...")

        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            status = self.check_status(job_id)
            state = status["state"]

            logger.info(
                f"Job {job_id}: {state} - "
                f"{status['completed_count']}/{status['total_count']} completed"
            )

            if state == "JOB_STATE_SUCCEEDED":
                logger.info(f"✓ Batch job {job_id} completed successfully!")
                return True
            elif state in ["JOB_STATE_FAILED", "JOB_STATE_CANCELLED"]:
                logger.error(f"✗ Batch job {job_id} failed with state: {state}")
                return False

            time.sleep(poll_interval)

        logger.warning(f"Batch job {job_id} timed out after {max_wait_time}s")
        return False

    def retrieve_results(
        self,
        job_id: str,
        batch_name: str
    ) -> List[ClassificationResultFromText]:
        """
        Retrieve and parse results from completed batch job.

        Args:
            job_id: Batch job ID
            batch_name: Name of the batch (to load URL mapping)

        Returns:
            List of classification results
        """
        logger.info(f"Retrieving results for job {job_id}")

        # Get batch job
        batch_job = genai.BatchJob(name=job_id)

        if batch_job.state != "JOB_STATE_SUCCEEDED":
            raise ValueError(f"Job not completed. State: {batch_job.state}")

        # Download results
        results_file = self.batch_dir / f"{batch_name}_results.jsonl"

        # The results are in the output file
        output_uri = batch_job.output.uri
        logger.info(f"Downloading results from {output_uri}")

        # Download using genai
        output_file = genai.get_file(output_uri)

        with open(results_file, 'wb') as f:
            f.write(output_file.read())

        # Parse results
        results = []
        url_mapping_file = self.batch_dir / f"{batch_name}_mapping.json"

        with open(url_mapping_file) as f:
            url_mapping = json.load(f)

        with open(results_file) as f:
            for line in f:
                result_data = json.loads(line)
                custom_id = result_data.get("custom_id")

                if "response" in result_data:
                    response_text = result_data["response"]["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(response_text)

                    result = ClassificationResultFromText(
                        page_title=parsed.get("page_title"),
                        is_financial=parsed.get("is_financial"),
                        country=parsed.get("country", []),
                        sector=parsed.get("sector", []),
                        companies=parsed.get("companies", []),
                        confident_score=parsed.get("confident_score", 0.0),
                        sentiment=parsed.get("sentiment"),
                        summary_en=parsed.get("summary_en"),
                        summary_tr=parsed.get("summary_tr"),
                        extracted_characters=0
                    )

                    results.append(result)
                else:
                    logger.warning(f"No response for {custom_id}")

        logger.info(f"✓ Retrieved {len(results)} results")
        return results

    def _get_system_prompt(self) -> str:
        """Get the system prompt for batch requests."""
        return """Analyze financial news. Return structured JSON:

1. Financial: Yes/No
2. Country: List of countries mentioned
3. Sectors: List (Technology, Banking, Energy, etc.)
4. Companies: List all companies/indices mentioned
5. Sentiment: Positive/Neutral/Negative
6. Confidence: Float 1.0-10.0
7. Summary EN: 2-3 sentences
8. Summary TR: 2-3 sentences (Turkish)

Be concise and accurate."""

    def _get_response_schema(self) -> Dict:
        """Get JSON schema for structured output."""
        return {
            "type": "object",
            "properties": {
                "page_title": {"type": "string"},
                "is_financial": {"type": "string", "enum": ["Yes", "No"]},
                "country": {"type": "array", "items": {"type": "string"}},
                "sector": {"type": "array", "items": {"type": "string"}},
                "companies": {"type": "array", "items": {"type": "string"}},
                "confident_score": {"type": "number"},
                "sentiment": {"type": "string", "enum": ["Positive", "Neutral", "Negative"]},
                "summary_en": {"type": "string"},
                "summary_tr": {"type": "string"}
            },
            "required": [
                "is_financial", "sector", "companies", "sentiment",
                "summary_en", "summary_tr", "confident_score"
            ]
        }


async def process_batch_workflow(
    urls: List[str],
    gemini_key: str,
    batch_name: Optional[str] = None,
    wait_for_completion: bool = True
) -> Optional[List[ClassificationResultFromText]]:
    """
    Complete batch processing workflow.

    Args:
        urls: List of news URLs to process
        gemini_key: Google API key
        batch_name: Optional batch name
        wait_for_completion: Whether to wait for results

    Returns:
        List of classification results if wait_for_completion=True
    """
    processor = BatchProcessor(gemini_key=gemini_key)

    # Step 1: Prepare batch
    batch_file = await processor.prepare_batch_from_urls(urls, batch_name)
    batch_name = Path(batch_file).stem

    # Step 2: Submit batch
    job_id = processor.submit_batch(batch_file)

    if not wait_for_completion:
        logger.info(f"Batch submitted. Job ID: {job_id}")
        return None

    # Step 3: Wait for completion
    success = processor.wait_for_completion(job_id)

    if not success:
        logger.error("Batch processing failed")
        return None

    # Step 4: Retrieve results
    results = processor.retrieve_results(job_id, batch_name)

    return results


# CLI for testing
if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Example usage
    test_urls = [
        "https://www.reuters.com/business/...",
        "https://www.bloomberg.com/news/...",
        # Add your URLs here
    ]

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not set")
        sys.exit(1)

    # Run batch processing
    results = asyncio.run(
        process_batch_workflow(
            urls=test_urls,
            gemini_key=api_key,
            batch_name="test_batch",
            wait_for_completion=True
        )
    )

    if results:
        print(f"\n✓ Processed {len(results)} articles")
        for i, result in enumerate(results[:3], 1):
            print(f"\n{i}. {result.page_title}")
            print(f"   Financial: {result.is_financial}")
            print(f"   Sentiment: {result.sentiment}")
            print(f"   Summary: {result.summary_en[:100]}...")

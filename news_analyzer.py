from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from threading import Lock
from typing import Optional, Tuple

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleProvider

from models import ClassificationResult, TextClassificationRequest

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}
FETCH_TIMEOUT_SECONDS = 10.0  # Reduced from 20s
LLM_TIMEOUT_SECONDS = 30.0  # Reduced from 45s
MAX_INPUT_CHARACTERS = 10000  # Reduced from 12,000 for faster LLM processing
LLM_MODEL = "gemini-2.5-flash-lite"  # Faster experimental model with better performance
BATCH_LIMIT = 500
MAX_CONCURRENT_REQUESTS = 30  # Conservative for Tier 1 (4,000 RPM limit)
MIN_REQUEST_INTERVAL = 0.05  # Minimum seconds between requests (Tier 1: 60 RPM = 1s interval)

SYSTEM_PROMPT = """You are a professional news analyst specialising in financial and business reporting.
Interpret the supplied article title and body, then populate the output schema exactly.

For each article determine:
1. is_financial: True if the piece has a financial or business focus, otherwise False.
2. sector: Industry or market sectors referenced (list of strings, empty if none).
3. companies: 
   - Include only named operating companies or subsidiaries that are materially involved or affected in the article.
   - Exclude unless the article is about them:
     • Media outlets (Reuters, CNBC, etc.)
     • Data/survey/benchmark providers (S&P Global, Markit, PMI compilers)
     • Government agencies, regulators, NGOs, think tanks
     • Stock indices or ETFs (S&P 500, MSCI, etc.)
     • Generic groups with no explicit company names (“Chinese automakers”)
   - Use canonical company names, no duplicates.
   - If no target companies appear, return an empty list.
4. country: Countries or regions mentioned (list of strings, empty if none).
5. sentiment: One of Negative, Neutral, Positive describing the overall tone.
6. confident_score: Numeric confidence between 0.0 and 10.0.
7. summary_en: Complete 2-3 sentence English summary (50-100 words). Always finish complete sentences.
8. summary_tr: Complete 2-3 sentence Turkish summary (50-100 words). Always finish complete sentences.

Always respond in JSON compatible with the provided schema. Do not include additional commentary."""

WHITESPACE_RE = re.compile(r"\s+")


class NewsAnalyzer:
    """High level orchestrator that extracts article contents and queries Gemini."""

    def __init__(
        self,
        gemini_key: str,
        *,
        max_input_chars: int = MAX_INPUT_CHARACTERS,
        fetch_timeout: float = FETCH_TIMEOUT_SECONDS,
        llm_timeout: float = LLM_TIMEOUT_SECONDS,
        max_concurrent: int = MAX_CONCURRENT_REQUESTS,
    ) -> None:
        self.fetch_timeout = fetch_timeout
        self.llm_timeout = llm_timeout
        self.max_input_chars = max_input_chars
        self.max_concurrent = max_concurrent

        self.provider = GoogleProvider(api_key=gemini_key)
        self.model = GoogleModel(LLM_MODEL, provider=self.provider)
        self.agent = Agent(
            self.model,
            output_type=ClassificationResult,
            system_prompt=SYSTEM_PROMPT,
            model_settings={
                "max_tokens": 2048,  # Reduced from 2048 for faster responses
                "temperature": 0.3,  # Lower temperature = faster, more deterministic
            },
        )

        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()

        # Semaphore for concurrent request limiting
        self._llm_semaphore: Optional[asyncio.Semaphore] = None
        self._semaphore_lock = asyncio.Lock()

        # Rate limiting for Tier 1
        self._last_request_time: float = 0.0
        self._rate_limit_lock = asyncio.Lock()

        logger.info(
            "NewsAnalyzer ready with model %s (max_concurrent=%d, rate_limit=%.1fs)",
            LLM_MODEL,
            max_concurrent,
            MIN_REQUEST_INTERVAL
        )

    async def start(self) -> None:
        """Warm the HTTP client and semaphore ahead of serving requests."""
        await self._get_http_client()
        await self._get_semaphore()

    async def shutdown(self) -> None:
        """Tear down the shared HTTP client."""
        async with self._client_lock:
            if self._client is not None:
                await self._client.aclose()
                self._client = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Create (or return) a shared async HTTP client."""
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    timeout = httpx.Timeout(self.fetch_timeout)
                    self._client = httpx.AsyncClient(
                        headers=DEFAULT_HEADERS,
                        timeout=timeout,
                    )
        return self._client

    async def _get_semaphore(self) -> asyncio.Semaphore:
        """Create (or return) a shared semaphore for rate limiting."""
        if self._llm_semaphore is None:
            async with self._semaphore_lock:
                if self._llm_semaphore is None:
                    self._llm_semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._llm_semaphore

    async def extract_url(
        self, url: str, fetch_timeout: Optional[float] = None
    ) -> Tuple[str, str]:
        """Download, clean, and return the article title and body."""
        client = await self._get_http_client()
        timeout = fetch_timeout or self.fetch_timeout

        try:
            response = await client.get(
                url,
                timeout=timeout,
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning("Timed out fetching %s after %.1fs", url, timeout)
            raise TimeoutError(
                f"Timed out fetching article after {timeout} seconds."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ValueError(
                f"HTTP {exc.response.status_code} error while fetching article."
            ) from exc
        except httpx.RequestError as exc:
            raise ValueError(
                f"Network error while fetching article: {exc}"
            ) from exc

        title, body = self._parse_article(response.text)
        if not body:
            raise ValueError("Could not extract readable text from the article.")

        return title or str(response.url), body

    def _parse_article(self, html: str) -> Tuple[Optional[str], str]:
        soup = BeautifulSoup(html, "html.parser")

        title: Optional[str]
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        else:
            title = None

        for tag in soup(
            [
                "script",
                "style",
                "noscript",
                "header",
                "footer",
                "svg",
                "form",
                "iframe",
                "nav",
                "aside",
            ]
        ):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        cleaned_text = self._clean_text(text)

        return title, cleaned_text

    def _clean_text(self, text: str) -> str:
        """Collapse whitespace and trim to the configured maximum."""
        collapsed = WHITESPACE_RE.sub(" ", (text or "")).strip()
        if len(collapsed) > self.max_input_chars:
            logger.debug(
                "Truncating article from %d to %d characters for cost control.",
                len(collapsed),
                self.max_input_chars,
            )
            return collapsed[: self.max_input_chars]
        return collapsed

    async def llm_analyzer(
        self, contents: str, title: str, llm_timeout: Optional[float] = None
    ) -> ClassificationResult:
        """Send the cleaned article to Gemini and return a structured result."""
        if not contents:
            raise ValueError("Article contents are empty after preprocessing.")

        payload = f"- Title: {title}\n- Contents: {contents}"
        timeout = llm_timeout or self.llm_timeout

        # Use semaphore to limit concurrent API calls
        semaphore = await self._get_semaphore()

        async with semaphore:
            # Rate limiting: ensure minimum interval between requests
            async with self._rate_limit_lock:
                current_time = time.time()
                time_since_last = current_time - self._last_request_time

                if time_since_last < MIN_REQUEST_INTERVAL:
                    wait_time = MIN_REQUEST_INTERVAL - time_since_last
                    logger.debug("Rate limiting: waiting %.2fs before next request", wait_time)
                    await asyncio.sleep(wait_time)

                self._last_request_time = time.time()

            try:
                response = await asyncio.wait_for(
                    self.agent.run(payload),
                    timeout=timeout,
                )
            except asyncio.TimeoutError as exc:
                logger.error("LLM analysis timed out after %.1fs", timeout)
                raise TimeoutError(
                    f"LLM analysis exceeded timeout of {timeout} seconds."
                ) from exc
            except Exception as exc:
                logger.exception("Unexpected error during LLM analysis")
                raise

        result_data = response.output.model_dump()
        result_data.setdefault("page_title", title)
        result_data["page_title"] = result_data.get("page_title") or title
        result_data["extracted_characters"] = len(contents)

        return ClassificationResult.model_validate(result_data)

    async def analyze_with_url(
        self,
        url: str,
        *,
        fetch_timeout: Optional[float] = None,
        llm_timeout: Optional[float] = None,
    ) -> ClassificationResult:
        """Fetch and analyse a remote article."""
        title, text = await self.extract_url(
            url,
            fetch_timeout=fetch_timeout,
        )

        # Create a TextClassificationRequest from the extracted data
        request = TextClassificationRequest(
            text=text,
            title=title or str(url),
            llm_timeout_seconds=llm_timeout,
        )

        result = await self.analyze_with_contents(request)
        result_payload = result.model_dump()
        result_payload.update(
            {
                "source_url": url,
                "page_title": result_payload.get("page_title") or title or str(url),
            }
        )
        return ClassificationResult.model_validate(result_payload)

    async def analyze_with_contents(
        self,
        request: TextClassificationRequest,
    ) -> ClassificationResult:
        """Analyse raw article text supplied by the caller via JSON body."""
        # The TextClassificationRequest model already validates and cleans the inputs
        cleaned_text = self._clean_text(request.text)

        if not cleaned_text or len(cleaned_text) < 20:
            raise ValueError(
                "Article text is empty or too short after cleaning. "
                f"Cleaned length: {len(cleaned_text)}"
            )

        return await self.llm_analyzer(
            cleaned_text,
            request.title,
            llm_timeout=request.llm_timeout_seconds,
        )


_cached_analyzer: Optional[NewsAnalyzer] = None
_cached_analyzer_lock = Lock()


def get_analyzer() -> NewsAnalyzer:
    """Return a singleton NewsAnalyzer instance, creating it on first use."""
    global _cached_analyzer
    with _cached_analyzer_lock:
        if _cached_analyzer is None:
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError(
                    "Missing API key. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable."
                )
            _cached_analyzer = NewsAnalyzer(gemini_key=api_key)
        return _cached_analyzer


async def shutdown_analyzer() -> None:
    """Close the cached analyzer and reset the singleton."""
    global _cached_analyzer
    with _cached_analyzer_lock:
        analyzer = _cached_analyzer
        _cached_analyzer = None

    if analyzer is not None:
        await analyzer.shutdown()

from __future__ import annotations

from typing import Tuple

from .extract import fetch_page
from .llm import LLMClient
from .models import ClassificationResult


def classify_url(url: str) -> Tuple[ClassificationResult, str]:
    """Pipeline: fetch -> heuristic LLM -> structured result.

    Returns (result, raw_text) for optional debugging.
    """
    title, text = fetch_page(url)
    client = LLMClient()
    llm_out = client.classify(text=text, title=title)

    result = ClassificationResult(
        source_url=url,
        page_title=title,
        is_financial=llm_out.is_financial,
        country=llm_out.country,
        sector=llm_out.sector,
        companies=llm_out.companies,
        sentiment=llm_out.sentiment,
        summary_en=llm_out.summary_en,
        summary_tr=llm_out.summary_tr,
        extracted_characters=len(text or ""),
    )
    return result, text


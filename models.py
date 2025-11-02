from typing import List, Optional, Literal
from pydantic import BaseModel, HttpUrl, Field


class ClassificationRequest(BaseModel):
    url: HttpUrl = Field(..., description="Public URL of a news article")


class ClassificationResult(BaseModel):
    source_url: HttpUrl
    page_title: Optional[str] = None
    is_financial: bool
    country: Optional[str] = None
    sector: Optional[str] = None
    companies: List[str] = []
    sentiment: Literal["negative", "neutral", "positive"]
    summary_en: str
    summary_tr: str
    extracted_characters: int = 0
    model_version: str = "draft-0.1"


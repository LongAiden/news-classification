from typing import List, Optional, Literal
from pydantic import BaseModel, HttpUrl, Field


class ClassificationRequest(BaseModel):
    url: HttpUrl = Field(..., description="Public URL of a news article")


class ClassificationResultFromUrl(BaseModel):
    source_url: HttpUrl
    page_title: Optional[str] = None
    is_financial: bool
    country: List[str] = None
    sector: List[str] = []
    companies: List[str] = []
    sentiment: Literal["Negative", "Neutral", "Positive"]
    summary_en: str
    summary_tr: str
    extracted_characters: int = 0

class ClassificationResultFromText(BaseModel):
    page_title: Optional[str] = None
    is_financial: Literal["Yes", "No"]
    country: List[str] = []
    sector: List[str] = []
    companies: List[str] = []
    confident_score: float
    sentiment: Literal["Negative", "Neutral", "Positive"]
    summary_en: str
    summary_tr: str
    extracted_characters: int = 0


# Alias for API compatibility
ClassificationResult = ClassificationResultFromText
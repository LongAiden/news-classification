from typing import List, Optional, Literal

from pydantic import BaseModel, Field, HttpUrl, ConfigDict, field_validator, model_validator


class TextClassificationRequest(BaseModel):
    """Payload accepted by the /classify/text endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Starbucks leans on discounts as China rivals surge",
                "text": "Today, the company has roughly 6,000 locations in China, but Starbucks has big ambitions for the market..."
                        " However, an economic slowdown and increased competition from local chains have weighed on sales.",
                "llm_timeout_seconds": 45,
            }
        }
    )

    title: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=500,
        description="Optional headline for the article. Auto-derived from text when omitted.",
    )
    text: str = Field(
        ...,
        min_length=20,
        max_length=100000,
        description="Plain-text contents of the article. Long inputs are auto-trimmed to control costs.",
    )
    llm_timeout_seconds: Optional[float] = Field(
        default=None,
        ge=5.0,
        le=180.0,
        description="Override the default timeout (seconds) used for the LLM call.",
    )

    @field_validator("text")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        stripped = value.strip()
        # Check if text is meaningful (more than just whitespace or very short)
        if len(stripped) < 20:
            raise ValueError("Article text must be at least 20 characters long and contain meaningful content.")
        return stripped

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, value):
        """Validate title is meaningful."""
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        stripped = value.strip()
        # Return None if too short, will be auto-generated from text
        return stripped if len(stripped) >= 3 else None

    @model_validator(mode="after")
    def _ensure_title(self):
        candidate = (self.title or "").strip()
        if not candidate or len(candidate) < 3:
            stripped = self.text.strip()
            if stripped:
                candidate = stripped.splitlines()[0][:120].strip()
                # Ensure the derived title is meaningful
                if len(candidate) < 3:
                    candidate = "Untitled article"
            else:
                candidate = "Untitled article"
        self.title = candidate
        return self


class ClassificationResult(BaseModel):
    """Unified result returned by both real-time and batch classifiers."""

    model_config = ConfigDict(extra="ignore")

    source_url: Optional[HttpUrl] = Field(
        default=None, description="Original article URL when content was fetched remotely."
    )
    page_title: Optional[str] = Field(
        default=None,
        min_length=3,
        description="Title inferred from the article or provided by the caller."
    )
    country: List[str] = Field(
        default_factory=list, description="Countries or regions referenced in the article."
    )
    sector: List[str] = Field(
        default_factory=list, description="Industry sectors mentioned in the article."
    )
    companies: List[str] = Field(
        default_factory=list, description="Companies, organisations, or indices that appear."
    )
    confident_score: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Confidence score supplied by the model on a 0-10 scale.",
    )
    sentiment: Literal["Negative", "Neutral", "Positive"] = Field(
        ..., description="Overall sentiment classification."
    )
    summary_en: str = Field(
        ...,
        min_length=8,
        description="Two to three sentence English summary, or 'No Value' for non-news content."
    )
    summary_tr: str = Field(
        ...,
        min_length=8,
        description="Two to three sentence Turkish summary, or 'No Value' for non-news content."
    )

    summary_kr: str = Field(
        ...,
        min_length=8,
        description="Two to three sentence Korean summary, or 'No Value' for non-news content."
    )

    is_news: bool = Field(
        ..., description="True when the article is news."
    )

    is_financial: bool = Field(
        ..., description="True when the article is related to finance, business, or markets."
    )

    @field_validator("page_title", mode="before")
    @classmethod
    def _validate_page_title(cls, value):
        """Ensure page_title is a valid string, not a type object."""
        if value is None:
            return None
        if isinstance(value, type):
            return None
        if not isinstance(value, str):
            return str(value) if value else None
        stripped = value.strip()
        return stripped if len(stripped) >= 3 else None
    

    @field_validator("summary_en", "summary_tr", "summary_kr", mode="before")
    @classmethod
    def _validate_summaries(cls, value):
        """Ensure summaries are meaningful and not truncated, or 'No Value' for non-news."""
        if not isinstance(value, str):
            return str(value) if value else "No Value"

        stripped = value.strip()

        # Allow "No Value" for non-news content (confident_score will be 0.0)
        if stripped == "No Value":
            return stripped

        # Reject if too short or clearly truncated
        if len(stripped) < 20:
            return "No Value"

        # Check if summary ends abruptly (no punctuation)
        if stripped and stripped[-1] not in '.!?':
            # Add period to complete the sentence
            stripped += "."

        return stripped
    extracted_characters: int = Field(
        default=0,
        ge=0,
        description="Number of characters from the article that were processed by the model.",
    )

    @field_validator("confident_score", mode="before")
    @classmethod
    def _validate_confident_score(cls, value):
        """Ensure confident_score is always provided."""
        if value is None:
            raise ValueError("confident_score is required and cannot be None. Model must provide a confidence score between 0.0 and 10.0.")
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                raise ValueError(f"confident_score must be numeric, got: {value}")
        return float(value)

    @field_validator("is_financial", mode="before")
    @classmethod
    def _normalize_is_financial(cls, value) -> bool:
        """Accept booleans or Yes/No style strings from LLM output."""
        if isinstance(value, str):
            normalised = value.strip().lower()
            if normalised in {"yes", "true", "1"}:
                return True
            if normalised in {"no", "false", "0"}:
                return False
        return bool(value)

    @field_validator("country", "sector", "companies", mode="before")
    @classmethod
    def _default_list(cls, value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str) and not value.strip():
            return []
        return list(value) if not isinstance(value, (str, bytes)) else [value]
    
    @field_validator("is_news", mode="before")
    @classmethod
    def _normalize_is_news(cls, value) -> bool:
        """Accept booleans or Yes/No style strings from LLM output."""
        if isinstance(value, str):
            normalised = value.strip().lower()
            if normalised in {"yes", "true", "1"}:
                return True
            if normalised in {"no", "false", "0"}:
                return False
        return bool(value)

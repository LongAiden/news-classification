from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Literal


Sentiment = Literal["negative", "neutral", "positive"]


@dataclass
class LLMOutput:
    is_financial: bool
    country: Optional[str]
    sector: Optional[str]
    companies: List[str]
    sentiment: Sentiment
    summary_en: str
    summary_tr: str


class LLMClient:
    """Draft stub that simulates an LLM.

    Replace with a real LLM call (OpenAI, Azure, etc.) and map outputs
    back into the structured fields. Keep interface stable for FastAPI.
    """

    POSITIVE = {
        "growth",
        "profit",
        "profits",
        "beat",
        "beats",
        "surge",
        "record",
        "gain",
        "gains",
        "upgraded",
        "expansion",
    }
    NEGATIVE = {
        "loss",
        "losses",
        "decline",
        "declines",
        "downgrade",
        "lawsuit",
        "bankrupt",
        "ban",
        "fraud",
        "layoff",
        "layoffs",
        "debt",
        "default",
    }

    FINANCE_HINTS = {
        "stock",
        "stocks",
        "market",
        "markets",
        "earnings",
        "revenue",
        "bank",
        "banking",
        "finance",
        "financial",
        "investment",
        "investor",
        "acquisition",
        "merger",
        "ipo",
        "m&a",
        "private equity",
        "pe fund",
        "loan",
        "interest rate",
        "inflation",
    }

    COUNTRY_MAP = {
        "turkey": ["turkey", "türkiye", "istanbul", "ankara", "izmir"],
        "united states": ["united states", "u.s.", "us ", "usa", "new york", "washington"],
        "united kingdom": ["united kingdom", "uk ", "london"],
        "germany": ["germany", "berlin", "frankfurt"],
        "france": ["france", "paris"],
        "china": ["china", "beijing", "shanghai"],
    }

    SECTOR_HINTS = {
        "banking": ["bank", "banking", "lending", "deposit"],
        "financial services": ["brokerage", "asset management", "insurance", "fintech"],
        "private equity": ["private equity", "buyout", "pe fund"],
        "technology": ["software", "ai ", "cloud", "saas", "chip"],
        "energy": ["oil", "gas", "renewable", "power"],
        "telecom": ["telecom", "5g", "carrier"],
    }

    COMPANY_LIST = [
        "Apple",
        "Microsoft",
        "Amazon",
        "Google",
        "Alphabet",
        "Meta",
        "OpenAI",
        "JPMorgan",
        "JP Morgan",
        "Goldman Sachs",
        "HSBC",
        "Deutsche Bank",
        "Garanti",
        "Akbank",
    ]

    def classify(self, text: str, title: Optional[str] = None) -> LLMOutput:
        """Heuristic placeholder that approximates the requested outputs.

        This is intentionally simple and deterministic to be replaced later.
        """
        content = f"{title or ''} \n {text}".lower()

        is_financial = any(h in content for h in self.FINANCE_HINTS)

        country = None
        for name, hints in self.COUNTRY_MAP.items():
            if any(h in content for h in hints):
                country = name
                break

        sector = None
        for name, hints in self.SECTOR_HINTS.items():
            if any(h in content for h in hints):
                sector = name
                break

        companies: List[str] = []
        content_orig = f"{title or ''} \n {text}"
        for comp in self.COMPANY_LIST:
            if comp.lower() in content:
                companies.append(comp)

        # Simple sentiment rules
        pos_hits = sum(w in content for w in self.POSITIVE)
        neg_hits = sum(w in content for w in self.NEGATIVE)
        if neg_hits > pos_hits:
            sentiment: Sentiment = "negative"
        elif pos_hits > neg_hits:
            sentiment = "positive"
        else:
            sentiment = "neutral"

        summary_en = self._summarize_english(content_orig)
        summary_tr = self._summarize_turkish_placeholder(summary_en)

        return LLMOutput(
            is_financial=is_financial,
            country=country,
            sector=sector,
            companies=companies,
            sentiment=sentiment,
            summary_en=summary_en,
            summary_tr=summary_tr,
        )

    def _summarize_english(self, text: str) -> str:
        # Title-first 1-liner, else first ~30 words
        parts = [p.strip() for p in text.splitlines() if p.strip()]
        first_line = parts[0] if parts else ""
        words = first_line.split()
        if 8 <= len(words) <= 40:
            return first_line
        words = (" ".join(parts)).split()
        return " ".join(words[:30]) + ("…" if len(words) > 30 else "")

    def _summarize_turkish_placeholder(self, summary_en: str) -> str:
        # Minimal placeholder for TR summary; replace via real translation later.
        return f"[TR] {summary_en}"


from dataclasses import dataclass
from typing import List, Literal, Optional

Plan = Literal["batch", "standard"]

# === PRICES: text-only (from your screenshots) ===
# Standard:  Input $0.30/M, Output $2.50/M, Cache write $0.03/M, Storage $1.00/M/hour
# Batch:     Input $0.15/M, Output $1.25/M, Cache write $0.03/M, Storage $1.00/M/hour

@dataclass(frozen=True)
class TextPrices:
    input_per_million: float
    output_per_million: float
    cache_write_per_million: float
    cache_storage_per_million_per_hour: float

PRICES_TEXT = {
    "standard": TextPrices(
        input_per_million=0.30,
        output_per_million=2.50,
        cache_write_per_million=0.03,
        cache_storage_per_million_per_hour=1.00,
    ),
    "batch": TextPrices(
        input_per_million=0.15,
        output_per_million=1.25,
        cache_write_per_million=0.03,
        cache_storage_per_million_per_hour=1.00,
    ),
}

GROUNDING_SEARCH_USD_PER_1000 = 35.00  # both plans; batch maps not available
TOKEN_SCALE = 1_000_000.0


def tokens_to_usd(tokens: int, usd_per_million: float) -> float:
    return (tokens / TOKEN_SCALE) * usd_per_million


def calc_text_cost_usd(
    *,
    plan: Plan,                 # "batch" (your use-case) or "standard"
    prompt_tokens: int,         # total input tokens for ONE request (system + title + content + etc.)
    output_tokens: int,         # output tokens for ONE request
    cache_write_tokens: int = 0,
    cache_storage_tokens: int = 0,
    cache_storage_hours: float = 0.0,
    grounded_search_prompts_paid: int = 0,  # after subtracting free quota
) -> dict:
    """
    Cost for a single **text-only** request.
    """
    p = PRICES_TEXT[plan]

    input_cost = tokens_to_usd(prompt_tokens, p.input_per_million)
    output_cost = tokens_to_usd(output_tokens, p.output_per_million)
    cache_write_cost = tokens_to_usd(cache_write_tokens, p.cache_write_per_million) if cache_write_tokens else 0.0

    cache_storage_cost = 0.0
    if cache_storage_tokens and cache_storage_hours:
        per_hour = tokens_to_usd(cache_storage_tokens, p.cache_storage_per_million_per_hour)
        cache_storage_cost = per_hour * cache_storage_hours

    grounding_search_cost = (grounded_search_prompts_paid / 1000.0) * GROUNDING_SEARCH_USD_PER_1000

    total = round(input_cost + output_cost + cache_write_cost + cache_storage_cost + grounding_search_cost, 6)

    return {
        "plan": plan,
        "input_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "costs": {
            "input_usd": round(input_cost, 6),
            "output_usd": round(output_cost, 6),
            "cache_write_usd": round(cache_write_cost, 6),
            "cache_storage_usd": round(cache_storage_cost, 6),
            "grounding_search_usd": round(grounding_search_cost, 6),
        },
        "total_usd": total,
        "rates_per_1M": {
            "input": p.input_per_million,
            "output": p.output_per_million,
            "cache_write": p.cache_write_per_million,
            "cache_storage_per_hour": p.cache_storage_per_million_per_hour,
            "grounding_search_per_1000": GROUNDING_SEARCH_USD_PER_1000,
        },
    }

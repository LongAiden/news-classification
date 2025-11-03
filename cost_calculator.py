#!/usr/bin/env python3
"""
Cost calculator for comparing single vs batch processing.

Usage:
    python cost_calculator.py --urls 10000
    python cost_calculator.py --urls 12000 --avg-tokens 2500
"""

import argparse
from typing import Dict


class CostCalculator:
    """Calculate API costs for different processing modes."""

    # Pricing per 1M tokens (from Google Gemini pricing)
    PRICING = {
        "standard": {
            "name": "Gemini 2.0 Flash Lite (Standard)",
            "input": 0.30,
            "output": 2.50,
        },
        "batch": {
            "name": "Gemini 2.0 Flash (Batch)",
            "input": 0.15,
            "output": 1.25,
        }
    }

    def __init__(
        self,
        daily_urls: int,
        avg_input_tokens: int = 2000,
        avg_output_tokens: int = 200
    ):
        """
        Initialize cost calculator.

        Args:
            daily_urls: Number of URLs processed per day
            avg_input_tokens: Average input tokens per request (prompt + article)
            avg_output_tokens: Average output tokens per request
        """
        self.daily_urls = daily_urls
        self.avg_input_tokens = avg_input_tokens
        self.avg_output_tokens = avg_output_tokens

    def calculate_tokens(self) -> Dict[str, int]:
        """Calculate daily token usage."""
        return {
            "input_tokens": self.daily_urls * self.avg_input_tokens,
            "output_tokens": self.daily_urls * self.avg_output_tokens,
        }

    def calculate_cost(self, mode: str = "standard") -> Dict[str, float]:
        """
        Calculate costs for a processing mode.

        Args:
            mode: "standard" or "batch"

        Returns:
            Dictionary with cost breakdown
        """
        pricing = self.PRICING[mode]
        tokens = self.calculate_tokens()

        # Convert to millions
        input_m = tokens["input_tokens"] / 1_000_000
        output_m = tokens["output_tokens"] / 1_000_000

        # Calculate costs
        input_cost_day = input_m * pricing["input"]
        output_cost_day = output_m * pricing["output"]
        total_cost_day = input_cost_day + output_cost_day

        return {
            "mode": mode,
            "name": pricing["name"],
            "input_tokens_m": input_m,
            "output_tokens_m": output_m,
            "input_cost_day": input_cost_day,
            "output_cost_day": output_cost_day,
            "total_cost_day": total_cost_day,
            "total_cost_month": total_cost_day * 30,
            "total_cost_year": total_cost_day * 365,
        }

    def compare(self) -> Dict:
        """Compare standard vs batch processing."""
        standard = self.calculate_cost("standard")
        batch = self.calculate_cost("batch")

        savings_day = standard["total_cost_day"] - batch["total_cost_day"]
        savings_month = standard["total_cost_month"] - batch["total_cost_month"]
        savings_year = standard["total_cost_year"] - batch["total_cost_year"]
        savings_percent = (savings_day / standard["total_cost_day"]) * 100

        return {
            "standard": standard,
            "batch": batch,
            "savings": {
                "per_day": savings_day,
                "per_month": savings_month,
                "per_year": savings_year,
                "percent": savings_percent,
            }
        }

    def print_report(self):
        """Print detailed cost comparison report."""
        comparison = self.compare()
        standard = comparison["standard"]
        batch = comparison["batch"]
        savings = comparison["savings"]

        print("\n" + "=" * 80)
        print("📊 COST COMPARISON: STANDARD vs BATCH PROCESSING")
        print("=" * 80)

        print(f"\n📈 Processing Volume:")
        print(f"  Daily URLs: {self.daily_urls:,}")
        print(f"  Avg input tokens/request: {self.avg_input_tokens:,}")
        print(f"  Avg output tokens/request: {self.avg_output_tokens:,}")

        tokens = self.calculate_tokens()
        print(f"\n  Daily input tokens: {tokens['input_tokens']:,} ({tokens['input_tokens']/1_000_000:.1f}M)")
        print(f"  Daily output tokens: {tokens['output_tokens']:,} ({tokens['output_tokens']/1_000_000:.1f}M)")

        print("\n" + "-" * 80)
        print("💰 STANDARD PROCESSING (Real-time API)")
        print("-" * 80)
        print(f"  Model: {standard['name']}")
        print(f"  Input pricing: ${self.PRICING['standard']['input']:.2f} per 1M tokens")
        print(f"  Output pricing: ${self.PRICING['standard']['output']:.2f} per 1M tokens")
        print()
        print(f"  Daily costs:")
        print(f"    Input:  {standard['input_tokens_m']:.1f}M tokens × ${self.PRICING['standard']['input']:.2f} = ${standard['input_cost_day']:.2f}")
        print(f"    Output: {standard['output_tokens_m']:.1f}M tokens × ${self.PRICING['standard']['output']:.2f} = ${standard['output_cost_day']:.2f}")
        print(f"    ─────────────────────────────────────")
        print(f"    TOTAL: ${standard['total_cost_day']:.2f}/day")
        print()
        print(f"  Monthly cost: ${standard['total_cost_month']:.2f}")
        print(f"  Annual cost:  ${standard['total_cost_year']:.2f}")

        print("\n" + "-" * 80)
        print("⚡ BATCH PROCESSING (50% cheaper)")
        print("-" * 80)
        print(f"  Model: {batch['name']}")
        print(f"  Input pricing: ${self.PRICING['batch']['input']:.2f} per 1M tokens")
        print(f"  Output pricing: ${self.PRICING['batch']['output']:.2f} per 1M tokens")
        print()
        print(f"  Daily costs:")
        print(f"    Input:  {batch['input_tokens_m']:.1f}M tokens × ${self.PRICING['batch']['input']:.2f} = ${batch['input_cost_day']:.2f}")
        print(f"    Output: {batch['output_tokens_m']:.1f}M tokens × ${self.PRICING['batch']['output']:.2f} = ${batch['output_cost_day']:.2f}")
        print(f"    ─────────────────────────────────────")
        print(f"    TOTAL: ${batch['total_cost_day']:.2f}/day")
        print()
        print(f"  Monthly cost: ${batch['total_cost_month']:.2f}")
        print(f"  Annual cost:  ${batch['total_cost_year']:.2f}")

        print("\n" + "=" * 80)
        print("💵 SAVINGS WITH BATCH PROCESSING")
        print("=" * 80)
        print(f"  Per day:   ${savings['per_day']:.2f} ({savings['percent']:.1f}% savings)")
        print(f"  Per month: ${savings['per_month']:.2f}")
        print(f"  Per year:  ${savings['per_year']:.2f}")
        print()
        print(f"  🎯 You save {savings['percent']:.0f}% by using batch processing!")
        print("=" * 80 + "\n")

        # Additional optimization tips
        print("💡 ADDITIONAL COST OPTIMIZATION TIPS:")
        print()
        print("  1. Content Truncation (8k chars)")
        print(f"     Additional savings: ~40%")
        print(f"     New monthly cost: ${batch['total_cost_month'] * 0.6:.2f}")
        print()
        print("  2. Financial Screening (filter non-financial)")
        print(f"     Additional savings: ~50% (if 50% are non-financial)")
        print(f"     New monthly cost: ${batch['total_cost_month'] * 0.5:.2f}")
        print()
        print("  3. URL Caching (70% cache hit rate)")
        print(f"     Additional savings: ~70%")
        print(f"     New monthly cost: ${batch['total_cost_month'] * 0.3:.2f}")
        print()
        print("  4. COMBINED (Batch + All optimizations)")
        print(f"     Total savings: ~95%")
        print(f"     NEW MONTHLY COST: ${batch['total_cost_month'] * 0.05:.2f}")
        print(f"     Total savings: ${standard['total_cost_month'] - (batch['total_cost_month'] * 0.05):.2f}/month")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Calculate API costs for news classification"
    )
    parser.add_argument(
        "--urls",
        type=int,
        required=True,
        help="Number of URLs processed per day"
    )
    parser.add_argument(
        "--avg-input-tokens",
        type=int,
        default=2000,
        help="Average input tokens per request (default: 2000)"
    )
    parser.add_argument(
        "--avg-output-tokens",
        type=int,
        default=200,
        help="Average output tokens per request (default: 200)"
    )

    args = parser.parse_args()

    calculator = CostCalculator(
        daily_urls=args.urls,
        avg_input_tokens=args.avg_input_tokens,
        avg_output_tokens=args.avg_output_tokens
    )

    calculator.print_report()


if __name__ == "__main__":
    main()

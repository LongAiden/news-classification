import re
import os
import json
import logging
import asyncio
import httpx
from typing import Tuple, Optional, List, Dict
from pathlib import Path

from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleProvider

from models import ClassificationResultFromText
from dotenv import load_dotenv
load_dotenv()

# Configure logger
logging.basicConfig(filename="./logs/newfile.log",
                    format='%(asctime)s %(message)s',
                    filemode='w')
logger = logging.getLogger(__name__)

GEMINI_KEY = os.getenv('GOOGLE_API_KEY')
# Default headers for HTTP requests
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
TIMEOUT = 30
LLM_MODEL = 'gemini-2.5-flash-lite'
BATCH_LIMIT = 500

SYSTEM_PROMPT = """You are a professional news analyst specializing in financial and business reporting.
Your goal is to interpret a given news article and provide a concise, structured analysis.:
Given a news title and content, perform the following tasks clearly and objectively:

1. Financial Relevance:
- Determine whether the news is related to finance, economy, or markets.
- Output: Yes or No.

2. Sector Classification:
- Identify which industry or sector the news focuses on.
- (Examples: Technology, Banking, F&B, Heavy Industry, Manufacturing, Energy, Healthcare, etc.)

3. Companies Mentioned:
- List all companies, organizations, or indices mentioned in the article.
- If none are directly mentioned, state: None.

4. Sentiment Analysis:
- Classify the overall tone of the news as Positive, Negative, or Neutral.
- Provide a confidence score between 1.0 and 10.0, where 10.0 = highest confidence.

5. Summaries:
- English Summary: 2–3 sentences summarizing the main points.
- Turkish Summary: 2–3 sentences summarizing the same in Turkish.

Example:
China's factory activity growth in October missed market expectations,
dragged down by a sharper drop in new export orders,
as trade tensions with the U.S. intensified during the month, according to a private survey released Monday.
The RatingDog China General Manufacturing PMI, compiled by S&P Global,
dropped to 50.6 in October from the six-month high of 51.2 in September,
missing analysts' expectations of 50.9 in a Reuters poll.
New export orders fell at the quickest pace since May,
which the survey respondents attributed to "rising trade uncertainty.

Output:
- Financial Check: Yes
- Sector: Manufacturing, Industrial Production
- Companies Mentioned: S&P Global, RatingDog China General Manufacturing PMI
- Sentiment Classification: Negative
Reason: Factory growth slowed, missed expectations, and export orders fell sharply amid U.S. trade tensions.
- Confidence Score: 9.0 / 10.0
- English Summary:
China's manufacturing sector lost momentum in October as the RatingDog China General Manufacturing PMI slipped to 50.6, below expectations. New export orders dropped at the fastest rate since May due to growing trade tensions with the U.S., signaling mounting pressure on the industrial economy.
- Turkish Summary:
Çin'in imalat sektörü Ekim ayında ivme kaybetti. RatingDog Çin Genel İmalat PMI endeksi 50,6'ya gerileyerek beklentilerin altında kaldı. Yeni ihracat siparişleri, ABD ile artan ticaret gerilimi nedeniyle Mayıs ayından bu yana en hızlı düşüşünü yaşadı.
Bu durum, sanayi ekonomisi üzerindeki baskının arttığını gösteriyor."""

class NewsAnalyzer:
    def __init__(self, gemini_key: str):
        self.provider = GoogleProvider(api_key=gemini_key)
        self.model = GoogleModel(LLM_MODEL, provider=self.provider)

        # Create agent with system prompt and output type
        self.agent = Agent(
            self.model,
            output_type=ClassificationResultFromText,
            system_prompt=SYSTEM_PROMPT
        )

        # Test the agent with a simple query
        logger.info("✓ Pydantic AI Agent configured successfully")

    async def llm_analyzer(
        self, contents: str, title: str, timeout: float = TIMEOUT
    ) -> ClassificationResultFromText:
        """Analyze news content with LLM. Includes timeout protection for long inference."""
        user_message = f"- Title: {title}\n- Contents: {contents}"

        try:
            logger.info(f"Analyzing {len(contents)} chars of text via LLM")

            response = await asyncio.wait_for(self.agent.run(user_message), timeout=timeout)

            return ClassificationResultFromText(
                page_title=title,
                is_financial=response.output.is_financial,
                country=getattr(response.output, "country", None),
                sector=response.output.sector,
                companies=response.output.companies,
                confident_score=response.output.confident_score,
                sentiment=response.output.sentiment,
                summary_en=response.output.summary_en,
                summary_tr=response.output.summary_tr,
                extracted_characters=len(contents or ""),
            )

        except asyncio.TimeoutError:
            logger.error("LLM analysis timed out.")
            raise TimeoutError(
                f"LLM analysis exceeded timeout of {timeout} seconds.")
        except Exception as e:
            logger.exception(f"Error during LLM analysis: {e}")
            raise

    async def analyze_with_url(self, url: str, timeout=TIMEOUT) -> ClassificationResultFromText:
        """Complete analysis pipeline: extract URL content and analyze with LLM."""
        title, text = await self.extract_url(url)
        llm_output = await self.llm_analyzer(contents=text, title=title, timeout=TIMEOUT)

        return llm_output

    async def analyze_with_contents(self, text: str, title: str, timeout=TIMEOUT) -> ClassificationResultFromText:
        """Complete analysis pipeline: analyze with text and title"""
        llm_output = await self.llm_analyzer(contents=text, title=title)

        return llm_output

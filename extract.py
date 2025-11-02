from __future__ import annotations

import re
from typing import Tuple, Optional

import requests


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}


def fetch_page(url: str, timeout: float = 15.0) -> Tuple[Optional[str], str]:
    """Fetches a URL and returns (title, text). Best-effort, no external services.

    - Uses requests with a friendly UA and timeout.
    - Tries BeautifulSoup if available for better parsing; otherwise falls back to regex strip.
    """
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    resp.raise_for_status()
    html = resp.text

    title = None
    text_content = None

    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(strip=True) if soup.title else None
        # Remove script/style
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text_content = soup.get_text(" ", strip=True)
    except Exception:
        # Fallback: naive tag removal
        title_match = re.search(r"<title>(.*?)</title>", html, flags=re.I | re.S)
        if title_match:
            title = re.sub(r"\s+", " ", title_match.group(1)).strip()
        # Remove scripts/styles
        html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
        html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
        # Strip tags
        text_only = re.sub(r"<[^>]+>", " ", html)
        text_content = re.sub(r"\s+", " ", text_only).strip()

    return title, text_content or ""


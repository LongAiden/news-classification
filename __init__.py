"""
News Classification Library

This package provides both real-time and batch news classification using Google Gemini.

Example usage as a library:
    from news_classification import NewsAnalyzer, ClassificationResult

    analyzer = NewsAnalyzer(gemini_key="your-key")
    await analyzer.start()
    result = await analyzer.analyze_with_url("https://example.com/article")
    await analyzer.shutdown()
"""

from .news_analyzer import NewsAnalyzer, get_analyzer, shutdown_analyzer
from .models import ClassificationResult, TextClassificationRequest

# Optional: batch processing imports
try:
    from .batch_processing.batch_processor import BatchProcessor
except ImportError:
    BatchProcessor = None

__all__ = [
    "NewsAnalyzer",
    "ClassificationResult",
    "TextClassificationRequest",
    "get_analyzer",
    "shutdown_analyzer",
    "BatchProcessor",
]

__version__ = "1.1.0"


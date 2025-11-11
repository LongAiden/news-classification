"""Entity extraction module for Named Entity Recognition (NER) using Gemini AI."""

from .extractor import extract_entities, ExtractedEntity, EntityExtractionResult
from .storage import store_entities

__all__ = ["extract_entities", "ExtractedEntity", "EntityExtractionResult", "store_entities"]

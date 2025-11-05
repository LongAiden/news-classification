# News Classification API & Library

This project provides news classification using Google Gemini, available as both:
1. **FastAPI REST service** - Standalone HTTP API server
2. **Python library** - Import and use directly in your code (see [LIBRARY_USAGE.md](LIBRARY_USAGE.md))

This guide shows how to stand up the News Classification API, call it in real time, and cut latency and token costs.

## 1. Environment setup
- Install dependencies once: `pip install -r requirements.txt`
- Provide a Gemini API key: `export GOOGLE_API_KEY="your-key"` (fallback: `GEMINI_API_KEY`)
- Optional: create a `.env` file with the same key so local scripts pick it up automatically.

## 2. Start the API
- From the project root run `uvicorn app:app --reload`
- The FastAPI docs are at http://127.0.0.1:8000/docs and include example payloads.
- Health check: `curl http://127.0.0.1:8000/health`

## 3. Classify news in real time
### POST `/classify/text`
```
curl -X POST http://127.0.0.1:8000/classify/text \
  -H "Content-Type: application/json" \
  -d '{
        "title": "Few CRE companies have achieved their AI goals. Here is why",
        "text": "...full article text...",
        "llm_timeout_seconds": 60
      }'
```
- The body matches `TextClassificationRequest` so it can be re-used in scripts.
- Responses follow the unified `ClassificationResult` schema:
  - `is_financial` (bool), `sector`, `companies`, `country`
  - `confident_score`, `sentiment`
  - `summary_en`, `summary_tr`, `extracted_characters`, `source_url`

## 4. Speed & cost optimisations built in
- **Connection reuse**: the API keeps a single async HTTP client, avoiding TLS handshakes on every request.
- **Token control**: article bodies are cleaned and capped at `12_000` characters before reaching Gemini, reducing spend on long pieces.
- **Timeout knobs**: per-request `fetch_timeout` and `llm_timeout` let you fail fast instead of paying for slow calls.
- **Smaller model**: default model `gemini-2.5-flash-lite` is tuned for low latency; swap to a larger model only when extra reasoning is required.

## 5. Batch for large volumes (≈50% cheaper)
- Use `batch_processing/batch_processor.py` when you have pre-crawled text and want to push hundreds of items at once.
- Batch mode amortises the prompt cost and is ideal for nightly crawls of >100 articles.
- Sample flow:
  1. Collect items shaped like `{"id": "...", "title": "...", "contents": "...clean text..."}`.
  2. Run `BatchProcessor.prepare_batch_from_contents(...)` to build the JSONL payload locally.
  3. Submit with `submit_batch(...)`, then poll `wait_for_completion(...)`.
  4. Parse the JSONL results back into `ClassificationResult` objects—no extra URL fetching required.

## 6. Using as a Library (Alternative to API)

Instead of running as an HTTP service, you can import this package directly:

```python
from news_classification import NewsAnalyzer, get_analyzer

# Option 1: Direct instantiation
analyzer = NewsAnalyzer(gemini_key="your-key")
await analyzer.start()
result = await analyzer.analyze_with_url("https://example.com/article")
await analyzer.shutdown()

# Option 2: Singleton pattern (recommended)
analyzer = get_analyzer()
result = await analyzer.analyze_with_contents(title="...", text="...")
```

**Benefits:**
- No HTTP overhead
- Type-safe Pydantic models
- Shared resource pooling
- Direct integration with your code

See [LIBRARY_USAGE.md](LIBRARY_USAGE.md) for complete examples and [example_library_usage.py](example_library_usage.py) for runnable demos.

## 7. Troubleshooting
- 504 errors indicate the fetch or LLM timeout was reached; increase the relevant timeout or inspect logs.
- 422 errors mean no readable text was extracted—verify the URL is public or strip HTML from custom payloads.
- Inspect `logs/` for detailed traces; adjust logging in `news_analyzer.py` if you need more verbosity.

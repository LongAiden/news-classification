# News Classification (Draft)

Minimal scaffold to classify a news URL and return a validated Pydantic model via a FastAPI endpoint. It includes:

- Text extraction from a web page (requests + BeautifulSoup if available, regex fallback)
- Heuristic LLM stub to approximate: financial relevance, country, sector, companies, sentiment
- Summaries in English and a Turkish placeholder
- Pydantic request/response models for strict IO validation
- FastAPI endpoint that accepts a URL and returns the structured result

Note: This is a draft. Replace the heuristic LLM with a real model/provider and improve extraction and translation as needed.

## Quickstart

1) Install dependencies (suggested):

```
pip install fastapi uvicorn[standard] pydantic requests beautifulsoup4
```

2) Run the API:

```
uvicorn news_classification.app:app --reload --port 8000
```

3) Try it:

```
curl "http://127.0.0.1:8000/classify?url=https://example.com"
```

Or POST JSON:

```
curl -X POST http://127.0.0.1:8000/classify \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

## Code Structure

- `news_classification/models.py` – Pydantic request/response models
- `news_classification/extract.py` – Fetch and parse page title/body text
- `news_classification/llm.py` – Heuristic LLM stub (replace later)
- `news_classification/classifier.py` – Pipeline orchestrator
- `news_classification/app.py` – FastAPI app exposing the `/classify` endpoint

## Next Steps (suggested)

- Replace `LLMClient` with a real LLM call and prompts
- Improve company and country detection (NER, geocoding)
- Add proper Turkish translation (e.g., provider API) for `summary_tr`
- Harden extraction (readability, boilerplate removal, paywall handling)
- Add tests and logging

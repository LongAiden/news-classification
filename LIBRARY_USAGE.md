# Using News-Classification as a Library

This guide shows how to use `news-classification` as a submodule or dependency in your own project.

## Installation Options

### Option 1: Git Submodule
```bash
# In your parent project
git submodule add https://github.com/yourusername/news-classification.git libs/news-classification
cd libs/news-classification
pip install -r requirements.txt
```

### Option 2: Local Package Installation
```bash
# In your parent project
pip install -e /path/to/news-classification
```

### Option 3: Direct Import (Add to PYTHONPATH)
```bash
export PYTHONPATH="/path/to/news-classification:$PYTHONPATH"
```

## Usage Examples

### 1. Basic Real-Time Classification

```python
import asyncio
from news_classification import NewsAnalyzer

async def classify_article():
    # Initialize analyzer
    analyzer = NewsAnalyzer(gemini_key="your-api-key")
    await analyzer.start()

    try:
        # Classify from URL
        result = await analyzer.analyze_with_url(
            "https://example.com/article",
            fetch_timeout=10.0,
            llm_timeout=30.0
        )

        print(f"Financial: {result.is_financial}")
        print(f"Sentiment: {result.sentiment}")
        print(f"Summary: {result.summary_en}")
        print(f"Companies: {result.companies}")

    finally:
        await analyzer.shutdown()

# Run
asyncio.run(classify_article())
```

### 2. Classify Raw Text Content

```python
import asyncio
from news_classification import NewsAnalyzer

async def classify_text():
    analyzer = NewsAnalyzer(gemini_key="your-api-key")
    await analyzer.start()

    try:
        result = await analyzer.analyze_with_contents(
            title="Market Update",
            text="Apple stock surged 5% today after announcing record earnings...",
            llm_timeout=30.0
        )

        return result

    finally:
        await analyzer.shutdown()

result = asyncio.run(classify_text())
```

### 3. Using Singleton Pattern (Recommended for Web Apps)

```python
from news_classification import get_analyzer, shutdown_analyzer

async def classify_multiple():
    # get_analyzer() returns a singleton - reuses the same instance
    analyzer = get_analyzer()

    # No need to call start() - it's handled automatically
    result1 = await analyzer.analyze_with_url("https://example.com/article1")
    result2 = await analyzer.analyze_with_url("https://example.com/article2")

    return [result1, result2]

# Cleanup when app shuts down
async def app_shutdown():
    await shutdown_analyzer()
```

### 4. Batch Processing (50% Cost Savings)

```python
import asyncio
from news_classification import BatchProcessor

async def batch_classify():
    processor = BatchProcessor(
        gemini_key="your-api-key",
        batch_dir="./batch_jobs"
    )

    # Prepare batch from URLs
    urls = [
        "https://example.com/article1",
        "https://example.com/article2",
        "https://example.com/article3",
    ]

    batch_file = await processor.prepare_batch(urls)

    # Submit and wait for results
    batch_name = await processor.submit_batch(batch_file)
    results = await processor.wait_for_completion(batch_name, poll_interval=30)

    # Process results
    for url, result in results.items():
        print(f"{url}: {result.summary_en}")

asyncio.run(batch_classify())
```

### 5. Integration with FastAPI (Parent Project)

```python
from fastapi import FastAPI
from news_classification import get_analyzer, shutdown_analyzer, ClassificationResult
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize analyzer
    analyzer = get_analyzer()
    await analyzer.start()
    yield
    # Shutdown: Cleanup
    await shutdown_analyzer()

app = FastAPI(lifespan=lifespan)

@app.post("/analyze", response_model=ClassificationResult)
async def analyze(url: str):
    analyzer = get_analyzer()
    return await analyzer.analyze_with_url(url)
```

### 6. Integration with Django/Flask (Sync Context)

```python
import asyncio
from news_classification import NewsAnalyzer

def classify_sync(url: str):
    """Synchronous wrapper for Django/Flask views"""
    async def _classify():
        analyzer = NewsAnalyzer(gemini_key="your-key")
        await analyzer.start()
        try:
            return await analyzer.analyze_with_url(url)
        finally:
            await analyzer.shutdown()

    return asyncio.run(_classify())

# Use in Django view
def article_view(request):
    url = request.GET.get('url')
    result = classify_sync(url)
    return JsonResponse(result.model_dump())
```

### 7. Custom Configuration

```python
from news_classification import NewsAnalyzer

# Custom timeouts and input limits
analyzer = NewsAnalyzer(
    gemini_key="your-key",
    max_input_chars=5000,      # Limit input for faster processing
    fetch_timeout=5.0,          # 5 second fetch timeout
    llm_timeout=20.0            # 20 second LLM timeout
)
```

## Environment Variables

Set these in your parent project:

```bash
# .env file
GOOGLE_API_KEY=your_gemini_api_key
GEMINI_API_KEY=your_gemini_api_key  # Alternative
```

Or load programmatically:

```python
import os
os.environ['GOOGLE_API_KEY'] = 'your-key'

from news_classification import get_analyzer
```

## Benefits of Using as a Library

1. **No HTTP Overhead** - Direct Python calls, no REST API latency
2. **Shared Resources** - Reuse HTTP clients and connections
3. **Type Safety** - Full Pydantic model validation
4. **Flexibility** - Customize timeouts, models, and processing logic
5. **Cost Control** - Batch processing for 50% savings on large volumes

## Requirements in Parent Project

Add to your `requirements.txt`:

```txt
httpx>=0.27.0
beautifulsoup4>=4.12.0
pydantic>=2.0.0
pydantic-ai>=0.0.14
python-dotenv>=1.0.0
google-genai>=0.2.0  # For batch processing
lxml>=5.0.0  # Optional: faster HTML parsing
```

## Error Handling

```python
from news_classification import NewsAnalyzer

async def safe_classify(url: str):
    analyzer = get_analyzer()

    try:
        result = await analyzer.analyze_with_url(url)
        return result
    except TimeoutError as e:
        print(f"Timeout: {e}")
    except ValueError as e:
        print(f"Invalid content: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
```

## Performance Tips

1. **Use singleton pattern** - Call `get_analyzer()` instead of creating new instances
2. **Enable HTTP/2** - Already enabled by default
3. **Batch similar requests** - Process multiple URLs concurrently
4. **Adjust input limits** - Lower `max_input_chars` for faster responses
5. **Use batch API** - For >100 articles, use `BatchProcessor` for 50% cost savings

## Next Steps

- See [README.md](README.md) for API server deployment
- See [workflow_quick.md](workflow_quick.md) for batch processing details
- Check [models.py](models.py) for full response schema

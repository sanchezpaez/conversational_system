# Conversational Parloa Prototype

Python prototype of a customer support AI agent using FastAPI and the OpenAI API.

## Features

- Endpoint: `/chat`
- Input: user message
- Pipeline:
	1. Intent classification (`order_status`, `change_booking`, `fallback`) using structured prompts and few-shot examples
	2. Entity extraction (`order_id`, `date`) with JSON output
	3. Mock backend function call
	4. Final response generation via prompt templates
- Simple logging of decisions

## Quick Start

### Option 1: Try the demo (no API key needed)

Run interactive conversation with mocked LLM:

```bash
uv sync
uv run python scripts/demo.py
```

Or run batch demo with predefined queries:

```bash
uv run python scripts/demo.py --batch
```

**Example queries:**
- "Where is my order AB-123?"
- "Can you move booking order 7821 to 2026-04-02?"
- "I have a complaint about your website."

### Option 2: Run the API server (requires OpenAI API key)

1. Set up `.env` with your OpenAI API key:

   ```bash
   cp .env.example .env
   ```

   Edit `.env`:

   ```dotenv
   OPENAI_API_KEY=sk-...
   ```

2. Start the server:

   ```bash
   uv sync
   uv run uvicorn main:app --reload
   ```

3. Test with curl:

   ```bash
   curl -X POST http://127.0.0.1:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Where is my order AB-123?"}'
   ```

   Or visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for interactive API docs.

## Setup

1. Install base dependencies:

   ```bash
   uv sync
   ```

2. (Optional) For API server: Create `.env` and add your OpenAI API key:

   ```bash
   cp .env.example .env
   # Edit .env and add: OPENAI_API_KEY=your_key
   ```

## How the API key is loaded

- The project loads `.env` from the repository root through the centralized module `app/config.py`.
- The key is read from environment variable `OPENAI_API_KEY`.
- If `OPENAI_API_KEY` is missing, the API returns `503 Service Unavailable`.
- Demo mode does not require an API key.

## Project structure

```
app/
  __init__.py
  agent.py          # Main agent pipeline
  backend.py        # Mock backend handlers
  config.py         # .env loading and config
  exceptions.py     # Custom exceptions
  llm.py            # OpenAI client and prompts
  models.py         # Pydantic models
scripts/
  evaluate.py       # Sample evaluation script
tests/
  conftest.py       # Pytest fixtures
  test_agent.py     # Agent pipeline tests
  test_api.py       # FastAPI endpoint tests
main.py            # FastAPI app entry point
pyproject.toml     # Dependencies
```

## Development

Install dev dependencies:

```bash
uv sync --all-extras
```

Run all tests:

```bash
uv run pytest -v
```

Run tests with coverage:

```bash
uv run pytest --cov=app --cov-report=term-missing
```

Run evaluation script with real OpenAI API:

```bash
uv run python scripts/evaluate.py  # requires OPENAI_API_KEY in .env
```

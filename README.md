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

## Setup

1. Install dependencies:

	 ```bash
	 uv sync
	 ```

2. Create your local environment file:

	 ```bash
	 cp .env.example .env
	 ```

3. Edit `.env` and set your OpenAI API key:

	 ```dotenv
	 OPENAI_API_KEY=your_real_api_key
	 ```

## How the API key is loaded

- The project loads `.env` from the repository root through the centralized module `app/config.py`.
- The key is read from environment variable `OPENAI_API_KEY`.
- If `OPENAI_API_KEY` is missing, the app raises a clear error.

## Run API

```bash
uv run uvicorn main:app --reload
```

Test request:

```bash
curl -X POST http://127.0.0.1:8000/chat \
	-H "Content-Type: application/json" \
	-d '{"message": "Where is my order AB-123?"}'
```

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

Run tests:

```bash
uv run pytest
```

Run tests with coverage:

```bash
uv run pytest --cov=app --cov-report=term-missing
```

Run evaluation script (sample queries with real OpenAI API):

```bash
uv run python scripts/evaluate.py
```

# Conversational Parloa Prototype

Python prototype of a customer support AI agent using FastAPI and the OpenAI API.

## Features

- Endpoint: `/chat`
- Input: user message
- Pipeline:
	1. Intent classification (`order_status`, `change_booking`, `fallback`) using structured prompts and few-shot examples
	2. Entity extraction (`order_id`, `date`) with JSON output
   3. Clarification step when required entities are missing
   4. Mock backend function call
   5. Final response generation via prompt templates
- Simple logging of decisions

## Conversation contract (v1)

- Ask for missing critical data before backend calls.
- Ask one concise clarification question whenever possible.
- For `order_status`, require `order_id`.
- For `change_booking`, require both `order_id` and `date`.
- Keep reply tone short, clear, and action-oriented.
- If intent is unclear, route to `fallback` and offer support escalation.
- Never invent order IDs or dates.
- Log intent, entities, missing fields, backend result, and final reply.

## Session memory (v1)

- Multi-turn memory is supported via optional `session_id` in `/chat` requests.
- When clarification is required, the agent stores missing context per `session_id`.
- Next user turns in the same session can provide only missing fields (for example, just date).
- Each response includes per-session metrics in `metrics`:
   - `turns_to_resolution`
   - `clarification_rate`
   - `success_rate`
- Language is detected automatically per message (`en`/`es`) and stored per session.
- Final agent replies are returned in the detected session language (`en` or `es`).

Example multi-turn flow:
- Turn 1: `{"message": "I need to change my booking", "session_id": "s1"}`
- Turn 2: `{"message": "Order 7821", "session_id": "s1"}`
- Turn 3: `{"message": "2026-05-10", "session_id": "s1"}`

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
   conversation_memory.py  # In-memory per-session state
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

Run deterministic evaluation (default, no API key required):

```bash
uv run python scripts/evaluate.py
```

Run evaluation script with real OpenAI API:

```bash
uv run python scripts/evaluate.py --real  # requires OPENAI_API_KEY in .env
```

Note: deterministic mode uses an internal mock LLM in `scripts/evaluate.py`
(`_mock_classify_intent` and `_mock_extract_entities`) only for evaluation.
Production logic remains in `app/llm.py`.

Structured JSON logs are emitted for key events in each turn (`intent_detected`,
`entities_extracted`, `clarification_requested`, `backend_result`, `reply_generated`).
Each event includes stable traceability fields: `timestamp`, `event`, `session_id`,
`intent`, `entities`, `missing_fields`, `backend_code`, and `ok`.

## Project evolution (summary)

- v0: FastAPI foundation with `/chat` endpoint
- v1.0: Core conversational pipeline (intent + entities + backend mock + response)
- v1.1: Clarification policy for missing required fields before backend calls
- v1.2: Multi-turn memory by `session_id`
- v1.3: Conversational error recovery with actionable replies
- v1.4: Mid-conversation intent switch handling
- v1.5: More empathetic tone in fallback and error replies
- v2.0: Local regex-based entity extraction + date normalization

## Agentic evolution (post-roadmap)

- **Stage A — Agentic-lite router**: constrained tool-calling over existing tools with strict guardrails.
- **Stage B — Adaptive execution**: dynamic tool selection, retry policy, and confidence thresholds.
- **Stage C — Planner/Critic (optional)**: multi-step planning only for complex requests with clear benefit.
- **Exit criteria per stage**: track success rate, clarification rate, average turns to resolution, and regression thresholds before rollout.

## Roadmap

### Phase 1 — Conversational quality *(complete)*
- [x] Core pipeline: intent + entities + backend + response
- [x] Clarification policy before calling backend
- [x] Multi-turn memory per `session_id`
- [x] Conversational error recovery: useful response + next step when backend fails
- [x] Mid-conversation intent change handling
- [x] Empathetic tone in fallback and error responses

### Phase 2 — Robust entity extraction
- [x] Regex + local normalisation for `order_id` and `date` (reduce LLM dependency)
- [x] Semantic entity validation (e.g. date cannot be in the past for a booking change)
- [x] Basic anaphora resolution ("that order", "the same date")

### Phase 3 — Evaluation and observability
- [x] Automated evaluation script with labelled test cases
- [x] Per-session metrics: turns to resolution, clarification rate, success rate
- [x] Structured JSON logging for full traceability

### Phase 4 — Multilingual support
- [x] Automatic language detection from user message
- [x] Prompts and responses in detected language (English and Spanish as v1)

### Phase 5 — Integrations
- [ ] Session persistence in a database (SQLite for dev, PostgreSQL for prod)
- [ ] Basic authentication for `/chat` endpoint
- [ ] Replace mock backend with real API calls

### Phase 6 — UI and experience
- [ ] Minimal chat web interface (Gradio or plain HTML/JS)
- [ ] Quick-action buttons ("check my order", "change date")
- [ ] Visible conversation history in UI

### Phase 7 — Production
- [ ] Dockerfile and docker-compose
- [ ] CI/CD with GitHub Actions (lint + tests on PR)
- [ ] Environment-based configuration (dev / staging / prod)

### Future ideas
- [ ] Sentiment analysis: detect frustration or urgency and adapt reply tone dynamically

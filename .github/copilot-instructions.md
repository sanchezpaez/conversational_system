# Instructions for GitHub Copilot

This repository uses Python with a local virtual environment.

## Project goal
Build a foundation for a Parloa conversational assistant.

## Working rules
- Keep changes small and focused.
- Do not change file names or public APIs unless necessary.
- Follow the existing project style.
- Prioritize clarity over complexity.
- Add comments only when they provide non-obvious context.
- All code comments must be written in English.
- Make changes only after explicit user approval.
- Work modularly, delivering changes in small, reviewable units.
- Always store API keys and secrets in `.env`.
- Never hardcode secrets in source code or documentation examples.
- Load environment variables from `.env` via a centralized config module.
- Read `OPENAI_API_KEY` from environment variables after loading `.env`.
- Keep `.env` out of version control and provide a `.env.example` file when needed.

## Change workflow
- Each change must be small, reviewable and focused on one thing.
- Required approval flow for every slice:
	1. Propose the exact planned changes (scope + files + tests).
	2. Wait for explicit user OK.
	3. Implement the changes.
	4. Show results and test output.
	4.1. Provide a step-by-step walkthrough in execution order (what runs first, next, and why), with file-by-file review pointers.
	5. Wait for explicit user OK before commit.
	6. Commit only after that final OK.
- One commit = one small vertical feature slice.
- A single commit may include code + tests + minimal docs, as long as all changes belong to the same feature.
- Split into multiple commits only when there are multiple responsibilities or independent features.
- Prefer small commits (ideally 1-5 files) that are easy to review and revert.
- If a proposed change touches multiple concerns, stop and propose a commit split plan before committing.
- Write tests for any new code before considering the change complete.
- Run tests: `uv run pytest`
- Commit changes to git only after approval and passing tests.
- State clearly: what changed, why it changed, and test results.

## Python
- Use type hints when useful.
- Prefer simple, reusable functions.
- Handle errors explicitly.

## Testing
- Write tests in `tests/` folder using pytest.
- Mock external dependencies (OpenAI API) in tests.
- Use fixtures in `tests/conftest.py` for reusable mocks.
- Run tests before any change is considered complete.
- Tests must pass before code is committed.

## Validation
- If you make code changes, run relevant minimal tests or validations.
- Do not fix unrelated issues unless requested.

## Documentation
- Update `README.md` when visible behavior changes.

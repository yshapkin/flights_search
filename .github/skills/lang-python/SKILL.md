---
name: lang-python
description: 'Implement, debug, refactor, and test Python code in this repository. Use for Python modules, type hints, package imports and exports, uv dependencies, pytest tests, Ruff diagnostics, and HTTP client changes.'
---

# Python Development

## Scope

Use this skill for Python implementation, debugging, dependency management,
testing, and lint fixes. Follow the repository instructions and existing APIs.

## Local Setup

Install the locked runtime and development dependencies from the repository root
with `uv sync --locked`. Application, test, lint, and dependency-management
commands are defined in the [project instructions](../../copilot-instructions.md).

The application uses these environment variables, which can be supplied in the
Git-ignored `.env` file:

```dotenv
RAPID_API_HOST=flights-sky.p.rapidapi.com
RAPID_API_KEY=your-rapidapi-key
```

Never commit credentials or include real secrets in documentation or test output.

## Code Style
- Use 4-space indentation, an 80-character line target, and implicit line
	continuation inside parentheses. Keep quotes consistent within each file.
- Document modules, classes, and public APIs with triple-double-quoted
	docstrings. Use Google-style `Args:`, `Returns:`, `Yields:`, and `Raises:`
	sections when needed; do not add redundant test docstrings.
- Import modules using absolute package paths, not individual classes or
	functions. Imports from `typing` and `collections.abc` are exceptions.
- Group imports as future, standard library, third-party, then repository
	modules, sorting each group by full module path.
- Annotate public APIs and non-obvious types. Use Python 3.11-compatible
	built-in generic types, `X | None`, and abstract `Mapping`/`Sequence` inputs.
- Use `from __future__ import annotations` when forward references need it.
- For logging, pass a literal format string and arguments separately, such as
	`logger.info("Status: %s", status)`. Never use f-strings in logging calls.
	For other strings, choose the clearest formatting method.
- Prefer simple comprehensions; use loops for multiple clauses or complex logic.
- Keep functions focused, avoid mutable defaults and mutable global state,
	and put executable behavior in `main()` behind the module execution guard.
- Use properties only for cheap computation or controlled attribute access.

## File Naming
- Use lowercase `snake_case` for Python module filenames, for example
	`rapid_api_parameters.py`, not `rapidApiParameters.py`
- Keep class names in `PascalCase`: `RapidApiParameters` belongs in
	`rapid_api_parameters.py`
- Use `snake_case` for functions, methods, properties, parameters, and variables;
	use `UPPER_CASE` for constants and a single leading underscore for internals.
- When renaming a module, update its imports, `__init__.py` exports, and affected tests

## Project Structure
- Follow `src/` layout: `src/<package>/`, `tests/`, `pyproject.toml`
- Use `pyproject.toml` for all project config (no `setup.py`, `setup.cfg`)
- Use `ruff` for linting and formatting (replaces black, isort, flake8)

- Use `pytest` for testing, `pytest-cov` for coverage
- Use `uv` for dependency management

## Patterns
- Use context managers (`with` statements) for resource management
- Use `logging` module, never `print()` for production code
- Never log credentials, request headers/query values, or sensitive exception text
- Add dataclasses, enums, caching, or concurrency only when the problem needs them

## Error Handling
- Use built-in exceptions where appropriate; custom exceptions should end in `Error`
- Catch specific exceptions and keep `try` blocks narrow; never use bare `except:`
- Use `finally` or context managers for cleanup; do not silently suppress failures

## Testing
- Name test files `test_<module>.py`, test functions `test_<behavior>()`
- Use `pytest.fixture` for setup, parametrize for data-driven tests
- Use `unittest.mock.patch` or `pytest-mock` for mocking
- Aim for >80% coverage on business logic
- Run the coverage gate with
	`uv run pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80`
- Place unit tests in `tests/` and run focused tests immediately after behavior changes
- Use the suite, lint, and formatting commands from the
	[project instructions](../../copilot-instructions.md) instead of maintaining
	duplicate command definitions here.

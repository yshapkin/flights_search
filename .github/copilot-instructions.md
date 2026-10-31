## Project structure

- `src/`: Application source code.
- `tests/`: Unit tests.
- `doc/`: Project specifications.

Place new code, unit tests, and specifications in their respective directories.

## Python tooling

Follow the Google Python Style Guide:
https://google.github.io/styleguide/pyguide.html
See `.github/skills/python/SKILL.md` for project-specific compatibility
exceptions and the Google-style rules enforced by Ruff.

Use `uv` to manage Python dependencies and the project virtual environment.

- Run `uv sync` to create or update `.venv` from `pyproject.toml` and `uv.lock`.
- Add runtime dependencies with `uv add <package>`.
- Add development dependencies with `uv add --dev <package>`.
- Run the application with `uv run python src/main.py`.
- Run unit tests with `uv run pytest tests/`.
- Run lint checks with `uv run ruff check src/ tests/`.
- Check formatting with `uv run ruff format --check src/ tests/`.

Keep `uv.lock` in version control and update it when dependencies change.
Prefer `uv run` over invoking globally installed Python tools, and do not add
separate requirements files unless explicitly requested.

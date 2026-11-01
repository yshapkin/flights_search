## Project structure

- `src/`: Application source code.
- `tests/`: Unit tests.
- `doc/`: Project specifications.

Place new code, unit tests, and specifications in their respective directories.

## Copilot documentation

- Keep `README.md` limited to the project title and a concise project description.
	Do not add setup commands, development guidance, Copilot workflows, or copies
	of instructions to it.
- Store all Copilot instructions and supporting documentation in this file or
	`.github/skills/<skill-name>/` (`SKILL.md` and its supporting resources).
- Use this file for repository-wide rules and skills for task-specific guidance,
	workflow usage, tooling details, and client compatibility documentation.
- Maintain a single authoritative source for each instruction or documented
	procedure. Reference that source instead of duplicating its content elsewhere.
- Keep agent profiles and prompt entry points in their required native locations,
	`.github/agents/` and `.github/prompts/`. Limit them to role definitions and
	invocation contracts; reference shared instructions and skills rather than
	copying general documentation into them.

## Python tooling

Follow the Google Python Style Guide:
https://google.github.io/styleguide/pyguide.html
See `.github/skills/lang-python/SKILL.md` for project-specific compatibility
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

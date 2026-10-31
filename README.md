# Flights Search

Flight-search experiments using Python and the Flights Sky API on RapidAPI.

## Setup

Install locked runtime and development dependencies from the repository root:

```sh
uv sync --locked
```

```dotenv
RAPID_API_HOST=flights-sky.p.rapidapi.com
RAPID_API_KEY=your-rapidapi-key
```

The `.env` file is ignored by Git. Do not commit credentials.

## Run

```sh
uv run python src/main.py
```

## Development

```sh
uv run pytest tests/
uv run pytest tests/ --cov=src --cov-report=term-missing --cov-fail-under=80
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv add <package>
uv add --dev <package>
```

## Documentation
- [docs/](docs/): Project documentation.

## License
See [LICENSE](LICENSE).

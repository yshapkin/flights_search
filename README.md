# Flights Search

Flight-search experiments using Python and the Flights Sky API on RapidAPI.

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


# Dreams Coding Engine

This repository provides a rule-based coding engine for dream narratives. It includes:

- Lexicon-driven tagging rules with negation and idiom guards (`src/rules.py`).
- A command-line batch analyzer (`src/analyze.py`).
- A FastAPI layer for integrations with Google Sheets and GitHub webhooks (`api/`).

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-api.txt  # optional but required for the API
python -m spacy download en_core_web_sm
```

## Command-line Analyzer

```bash
python -m src.analyze --in_file data/raw/dreams.csv --text_col text
```

The analyzer merges the coded fields into a new CSV written to `data/processed/` by default.

## FastAPI Service

Start the API locally with Uvicorn:

```bash
uvicorn api.main:app --reload --port 8000
```

### Configuration

| Environment Variable      | Default Value               | Description |
| ------------------------- | --------------------------- | ----------- |
| `PRESET_DIR`              | `configs/presets`           | Directory scanned for preset JSON files. |
| `SCHEMA_PATH`             | `schema/ruleset.schema.json`| JSON Schema used by `/validate_preset`. |
| `ENGINE_VERSION`          | `0.3.0`                     | Version string stamped onto `/code` results. |
| `GITHUB_WEBHOOK_SECRET`   | `CHANGE_ME`                 | Shared secret for `/gh/webhook`. |
| `CORS_ALLOW_ORIGINS`      | `*`                         | Comma-separated list of allowed origins. |

### Endpoints

- `POST /code` — Batch-code rows using the rule engine. Pass an optional `preset` key to apply a cached preset.
- `GET /presets` — List available presets (`name@version`).
- `POST /extend_lexicon` — Generate deterministic lexicon extension proposals.
- `POST /validate_preset` — Validate a preset JSON payload against the schema.
- `POST /gh/webhook` — Refresh the in-memory preset cache when triggered by a GitHub push event.

### Docker

Build and run the API using the provided Dockerfile:

```bash
docker build -t dreams-engine .
docker run -p 8000:8000 --env GITHUB_WEBHOOK_SECRET=changeme dreams-engine
```

## Google Sheets Add-on

See [`README_SHEETS_ADDON.md`](README_SHEETS_ADDON.md) for the Apps Script snippet that integrates the `/code`
endpoint with Google Sheets.

## Testing

Run the unit test suite with:

```bash
pytest
```

# OpenPraxis

AI Bandwidth Amplifier - turn notes into structured practice and actionable learning insights.

## Requirements

- Python 3.11+
- OpenAI API Key

## Installation

```bash
pip install -e .
# or install with dev dependencies: pip install -e ".[dev]"
```

## Configuration

Copy `config.example.toml` to `~/.openpraxis/config.toml` and set `api_key`.
You can also configure it with the `OPENAI_API_KEY` environment variable.

## Usage

```bash
praxis add <file> [--type report|interview|reflection|idea]
praxis practice <input_id>
praxis answer <scene_id> [--editor] [--file <path>]
praxis insight [<input_id>] [--type <insight_type>] [--min-intensity <n>]
praxis show <id>
praxis export [--format md|json] [--output <path>]
praxis list [--type report|interview|reflection|idea] [--limit N]
```

## Development

```bash
pytest
ruff check src tests
```

## License

See the project repository.

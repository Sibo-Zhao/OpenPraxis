# OpenPraxis

AI Bandwidth Amplifier - turn notes into structured practice and actionable learning insights.

## Requirements

- Python 3.11+
- LLM API Key (OpenAI / Doubao / Kimi / DeepSeek)

## Installation

```bash
pip install -e .
# or install with dev dependencies: pip install -e ".[dev]"
```

## Configuration

Copy `config.example.toml` to `~/.openpraxis/config.toml` and set `api_key`.
You can switch providers via `llm.provider`:

- `openai` (default): native structured output parse
- `doubao`: native structured output parse
- `kimi` / `deepseek`: JSON mode + JSON string -> Pydantic validation

API key env vars (higher priority than `llm.api_key`):

- `OPENAI_API_KEY` for `openai`
- `ARK_API_KEY` for `doubao`
- `MOONSHOT_API_KEY` for `kimi`
- `DEEPSEEK_API_KEY` for `deepseek`

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

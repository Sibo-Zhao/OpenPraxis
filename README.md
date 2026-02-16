# OpenPraxis

Built for applied mastery of your local knowledge bases, notes, and other multi-source materials: turn raw inputs into structured practice so you can use what you know, not just store it.

## Requirements

- Python 3.11+
- LLM API Key (OpenAI / Doubao / Kimi / DeepSeek)

## Installation

```bash
pip install -e .
# or install with dev dependencies: pip install -e ".[dev]"
```

## Configuration

Recommended first-time setup:

```bash
praxis llm setup
praxis llm show
```

This saves your default provider/model/api_key into `~/.openpraxis/config.toml`.
You can also edit `config.example.toml` manually and copy it to `~/.openpraxis/config.toml`.

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

`praxis add` accepts both text/markdown files and common image formats (`.png`, `.jpg`, `.webp`, ...). For images, OpenPraxis uses a vision-capable model to extract readable text first (providers: `openai` or `doubao`).

Global runtime LLM overrides (for a single command):

```bash
praxis --provider doubao --model doubao-seed-1-6-251015 add note.md
praxis --provider kimi --model kimi-k2-turbo-preview practice <input_id>
praxis --provider deepseek --model deepseek-chat answer <scene_id> --file answer.md
```

## Development

```bash
pytest
ruff check src tests
```

## Vision

Increase your "AI bandwidth" by converting fragmented inputs into reusable practice loops that build real transfer: faster recall, clearer decisions, better on-the-job application.

## License

See the project repository.

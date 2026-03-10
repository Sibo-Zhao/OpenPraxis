# OpenPraxis

An OpenClaw-native knowledge retention skill that turns raw inputs into structured practice so you can use what you know, not just store it.

**OpenClaw users**: zero extra API key configuration — the host agent's model is reused automatically.
**Standalone CLI users**: configure your own provider with `praxis llm setup`.

## Requirements

- Python 3.11+

## OpenClaw Users: Zero-Config Path

When running as an OpenClaw skill, OpenPraxis delegates all LLM calls to the host agent. No local API key is needed.

```bash
pip install openpraxis
export OPENPRAXIS_MODE=openclaw
```

Then use the skill directly from your OpenClaw agent — import knowledge, generate practice, evaluate answers, and produce insight cards.

See `openclaw-knowledge-coach/SKILL.md` for the full skill workflow.

## Standalone CLI Users: Manual Setup

For use outside of OpenClaw, configure your own provider and API key:

```bash
pip install openpraxis
praxis llm setup
praxis llm show
```

Or install from source (for development):

```bash
git clone https://github.com/Sibo-Zhao/OpenPraxis.git
cd OpenPraxis
pip install -e ".[dev]"
```

Supported providers:

- `openai` (default): native structured output parse
- `doubao`: native structured output parse
- `kimi` / `deepseek`: JSON mode + Pydantic validation

API key env vars (higher priority than config file):

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

Global runtime LLM overrides (for a single command, standalone CLI mode):

```bash
praxis --provider doubao --model doubao-seed-1-6-251015 add note.md
praxis --provider kimi --model kimi-k2-turbo-preview practice <input_id>
praxis --provider deepseek --model deepseek-chat answer <scene_id> --file answer.md
```

## Architecture: Host-Managed LLM vs CLI-Managed LLM

OpenPraxis separates **business workflow** (schema, prompts, graph, scoring, persistence) from **LLM call implementation** via a backend abstraction:

- **OpenClaw mode** (`OPENPRAXIS_MODE=openclaw`): LLM calls are delegated to the host agent. No local API key needed.
- **Standalone CLI mode** (default): LLM calls use the locally configured provider and API key.

Nodes and graph logic depend only on `LLMBackend` interface, not on any specific provider. See `ARCHITECTURE.md` for details.

## Development

```bash
pytest
ruff check src tests
```

## Vision

Increase your "AI bandwidth" by converting fragmented inputs into reusable practice loops that build real transfer: faster recall, clearer decisions, better on-the-job application.

## License

See the project repository.

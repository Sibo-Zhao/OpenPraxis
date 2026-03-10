---
name: openclaw-knowledge-coach
description: OpenClaw-native knowledge retention skill. Imports local documents, generates retrieval practice, evaluates answers, and produces insight cards — all using the host agent's LLM with zero extra API key configuration. Use when users ask to ingest local knowledge, generate practice exercises, or master stored knowledge.
---

# OpenClaw Knowledge Coach

An OpenClaw-native skill for local knowledge retention. Import knowledge, generate practice, evaluate answers, and produce insight cards — all powered by the host agent's model, with **zero extra API key configuration**.

## OpenClaw Users (Recommended)

When running inside an OpenClaw agent, the host provides model configuration.
No `praxis llm setup` or API key setup is required.

Install the library:

```bash
pip install openpraxis
```

The skill uses the host agent's LLM capability automatically. Set the environment variable to enable OpenClaw mode:

```bash
export OPENPRAXIS_MODE=openclaw
```

## Standalone CLI (Fallback)

For use outside of an OpenClaw agent, configure your own provider:

```bash
pip install openpraxis
praxis llm setup
praxis llm show
```

Environment variables override config file values:

```bash
export OPENAI_API_KEY="your_key_here"
# or ARK_API_KEY / MOONSHOT_API_KEY / DEEPSEEK_API_KEY based on provider
```

## Core Workflow

1. Confirm scope and source
- Confirm knowledge domains, source folders, and accepted file types.
- Confirm whether to preserve existing metadata (tags, dates, project names).

2. Define import contract
- Normalize each source into a record with `doc_id`, `title`, `source_path`, `tags`, `created_at`, and `content`.
- Split long content into chunks with stable IDs such as `doc_id#chunk-001`.

3. Import into OpenClaw
- Ingest normalized records into the local OpenClaw knowledge base.
- Keep a deterministic mapping between source file and imported IDs for later updates.

4. Generate exercises at import time
- For each chunk, create at least one retrieval exercise.
- Prefer three exercise types:
  - `free-recall`: ask the user to explain from memory.
  - `qa`: ask direct question-answer pairs.
  - `application`: ask scenario-based transfer questions.
- Save answer keys and concise grading rubrics.

5. Build review queue
- Group exercises by topic and difficulty.
- Schedule spaced review windows (for example: day 1, day 3, day 7, day 14).

6. Validate quality
- Reject exercises that can be answered without the imported knowledge.
- Reject ambiguous or duplicate questions.
- Ensure every exercise points back to `doc_id` and `chunk_id`.

## CLI Command Playbook

Run this sequence when the user asks to import local knowledge and create practice:

1. Add a local file

```bash
praxis add "/absolute/path/to/note.md" --type report
```

2. List recent inputs and capture target `input_id`

```bash
praxis list --limit 20
```

3. Force-generate a new practice scene for an existing input

```bash
praxis practice <input_id>
```

4. Submit answer by file (preferred for deterministic runs)

```bash
praxis answer <scene_id> --file "/absolute/path/to/answer.md"
```

5. Inspect pipeline results and insight cards

```bash
praxis show <input_id>
praxis insight <input_id>
```

6. Export insights to Markdown/JSON

```bash
praxis export --format md --output "/absolute/path/to/insights.md"
praxis export --format json --output "/absolute/path/to/insights.json"
```

## Agent Execution Rules

- Prefer `praxis add` for import and initial exercise generation.
- Parse IDs from CLI output, then chain `praxis practice` and `praxis answer`.
- Use `praxis answer --file` instead of interactive stdin in automation flows.
- If duplicate content is skipped, rerun with `praxis add ... --force` when user wants reprocessing.
- Use one-shot runtime model override only when requested:

```bash
praxis --provider openai --model gpt-4.1-mini add "/absolute/path/to/note.md"
```

- For image notes, pass image file path directly to `praxis add`; OCR extraction is built in.
- Always finish with `praxis show` plus `praxis insight` or `praxis export` so user gets concrete output artifacts.

## Output Contract

When executing tasks with this skill, always provide these outputs:

- Import summary: files processed, chunks created, failures.
- Exercise summary: counts by type/topic/difficulty.
- Review plan: next due batches and estimated workload.
- Traceability map: `source -> doc_id -> chunk_id -> exercise_id`.

## Exercise Format

Use this compact JSON-like structure per exercise:

```json
{
  "exercise_id": "ex-...",
  "doc_id": "...",
  "chunk_id": "...",
  "type": "free-recall | qa | application",
  "question": "...",
  "answer_key": "...",
  "rubric": ["point 1", "point 2"],
  "difficulty": "easy | medium | hard",
  "next_review": "YYYY-MM-DD"
}
```

For more generation patterns, read `references/exercise-patterns.md`.

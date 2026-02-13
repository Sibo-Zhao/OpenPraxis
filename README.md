# OpenPraxis

AI Bandwidth Amplifier — 将笔记转化为结构化实践与认知洞察。

## 要求

- Python 3.11+
- OpenAI API Key

## 安装

```bash
pip install -e .
# 或开发依赖：pip install -e ".[dev]"
```

## 配置

复制 `config.example.toml` 到 `~/.openpraxis/config.toml`，填写 `api_key`。也可通过环境变量 `OPENAI_API_KEY` 设置。

## 使用

```bash
praxis add <file> [--type report|interview|reflection|idea]
praxis practice <input_id>
praxis answer <scene_id> [--editor] [--file <path>]
praxis insight [<input_id>] [--type <insight_type>] [--min-intensity <n>]
praxis show <id>
praxis export [--format md|json] [--output <path>]
praxis list [--type report|interview|reflection|idea] [--limit N]
```

## 开发

```bash
pytest
ruff check src tests
```

## 许可

见项目仓库。

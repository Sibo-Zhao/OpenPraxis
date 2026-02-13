"""配置加载（TOML + 环境变量）。"""

import os
from pathlib import Path

import tomllib
from pydantic import BaseModel, Field

_DEFAULT_CONFIG_DIR = Path.home() / ".openpraxis"
_DEFAULT_CONFIG_PATH = _DEFAULT_CONFIG_DIR / "config.toml"
_DEFAULT_DATA_DIR = _DEFAULT_CONFIG_DIR / "data"


class Settings(BaseModel):
    openai_api_key: str = ""
    model_name: str = "gpt-4o"
    temperature: float = 0.7
    data_dir: Path = _DEFAULT_DATA_DIR
    db_path: Path = Field(default_factory=lambda: _DEFAULT_DATA_DIR / "praxis.db")
    color: bool = True


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is not None:
        return _settings

    config: dict = {}
    if _DEFAULT_CONFIG_PATH.exists():
        with open(_DEFAULT_CONFIG_PATH, "rb") as f:
            config = tomllib.load(f)

    llm_cfg = config.get("llm", {})
    storage_cfg = config.get("storage", {})
    display_cfg = config.get("display", {})

    api_key = llm_cfg.get("api_key") or os.environ.get("OPENAI_API_KEY", "")
    data_dir = Path(
        storage_cfg.get("data_dir", str(_DEFAULT_DATA_DIR))
    ).expanduser()
    data_dir.mkdir(parents=True, exist_ok=True)

    _settings = Settings(
        openai_api_key=api_key,
        model_name=llm_cfg.get("model", "gpt-4o"),
        temperature=llm_cfg.get("temperature", 0.7),
        data_dir=data_dir,
        db_path=data_dir / "praxis.db",
        color=display_cfg.get("color", True),
    )
    return _settings

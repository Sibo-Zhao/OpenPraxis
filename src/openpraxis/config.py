"""Config loading (TOML + env vars)."""

import os
from pathlib import Path

import tomllib
from pydantic import BaseModel, Field

_DEFAULT_CONFIG_DIR = Path.home() / ".openpraxis"
_DEFAULT_CONFIG_PATH = _DEFAULT_CONFIG_DIR / "config.toml"
_DEFAULT_DATA_DIR = _DEFAULT_CONFIG_DIR / "data"

_PROVIDER_ENV_KEY_MAP = {
    "openai": "OPENAI_API_KEY",
    "doubao": "ARK_API_KEY",
    "kimi": "MOONSHOT_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
}

_PROVIDER_BASE_URL_MAP = {
    "doubao": "https://ark.cn-beijing.volces.com/api/v3",
    "kimi": "https://api.moonshot.ai/v1",
    "deepseek": "https://api.deepseek.com",
}


class Settings(BaseModel):
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_base_url: str | None = None
    model_name: str = "gpt-4o"
    temperature: float = 0.7
    data_dir: Path = _DEFAULT_DATA_DIR
    db_path: Path = Field(default_factory=lambda: _DEFAULT_DATA_DIR / "praxis.db")
    color: bool = True

    @property
    def openai_api_key(self) -> str:
        """Backward-compatible alias for legacy callers."""
        return self.llm_api_key


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

    provider = str(llm_cfg.get("provider", "openai")).strip().lower()
    env_key = _PROVIDER_ENV_KEY_MAP.get(provider, "OPENAI_API_KEY")
    api_key = os.environ.get(env_key) or llm_cfg.get("api_key", "")
    base_url = llm_cfg.get("base_url") or _PROVIDER_BASE_URL_MAP.get(provider)
    data_dir = Path(
        storage_cfg.get("data_dir", str(_DEFAULT_DATA_DIR))
    ).expanduser()
    data_dir.mkdir(parents=True, exist_ok=True)

    _settings = Settings(
        llm_provider=provider,
        llm_api_key=api_key,
        llm_base_url=base_url,
        model_name=llm_cfg.get("model", "gpt-4o"),
        temperature=llm_cfg.get("temperature", 0.7),
        data_dir=data_dir,
        db_path=data_dir / "praxis.db",
        color=display_cfg.get("color", True),
    )
    return _settings

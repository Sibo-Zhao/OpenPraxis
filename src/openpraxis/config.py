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
SUPPORTED_LLM_PROVIDERS = tuple(_PROVIDER_ENV_KEY_MAP.keys())


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


def set_runtime_llm_overrides(
    provider: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    temperature: float | None = None,
) -> None:
    """Apply per-process LLM overrides (used by CLI runtime flags)."""
    global _settings
    if all(value is None for value in (provider, api_key, base_url, model, temperature)):
        return

    settings = get_settings()
    updates: dict = {}
    normalized_provider: str | None = None

    if provider is not None:
        normalized_provider = provider.strip().lower()
        if normalized_provider not in _PROVIDER_ENV_KEY_MAP:
            allowed = ", ".join(SUPPORTED_LLM_PROVIDERS)
            raise ValueError(f"Unsupported llm provider: {provider}. Allowed: {allowed}")
        updates["llm_provider"] = normalized_provider
        # If provider changes and caller did not specify base_url, reset to provider default.
        if base_url is None:
            updates["llm_base_url"] = _PROVIDER_BASE_URL_MAP.get(normalized_provider)

    if api_key is not None:
        updates["llm_api_key"] = api_key
    elif normalized_provider is not None:
        env_key = _PROVIDER_ENV_KEY_MAP[normalized_provider]
        env_value = os.environ.get(env_key)
        if env_value:
            updates["llm_api_key"] = env_value

    if base_url is not None:
        updates["llm_base_url"] = base_url or None
    if model is not None:
        updates["model_name"] = model
    if temperature is not None:
        updates["temperature"] = temperature

    _settings = settings.model_copy(update=updates)

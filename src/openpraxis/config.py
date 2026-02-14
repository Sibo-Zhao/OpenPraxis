"""Config loading (TOML + env vars)."""

import os
from pathlib import Path
from typing import Any

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
_PROVIDER_MODEL_MAP = {
    "openai": "gpt-4o",
    "doubao": "doubao-seed-1-6-251015",
    "kimi": "kimi-k2-turbo-preview",
    "deepseek": "deepseek-chat",
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


def _normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized not in _PROVIDER_ENV_KEY_MAP:
        allowed = ", ".join(SUPPORTED_LLM_PROVIDERS)
        raise ValueError(f"Unsupported llm provider: {provider}. Allowed: {allowed}")
    return normalized


def get_provider_default_base_url(provider: str) -> str | None:
    return _PROVIDER_BASE_URL_MAP.get(_normalize_provider(provider))


def get_provider_default_model(provider: str) -> str:
    return _PROVIDER_MODEL_MAP[_normalize_provider(provider)]


def load_config_dict() -> dict[str, Any]:
    if not _DEFAULT_CONFIG_PATH.exists():
        return {}
    with open(_DEFAULT_CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def get_llm_api_key_source(provider: str, config: dict[str, Any] | None = None) -> str:
    provider_name = _normalize_provider(provider)
    env_key = _PROVIDER_ENV_KEY_MAP[provider_name]
    if os.environ.get(env_key):
        return f"env:{env_key}"
    cfg = config if config is not None else load_config_dict()
    llm_cfg = cfg.get("llm", {})
    if llm_cfg.get("api_key"):
        return "config"
    return "unset"


def mask_secret(secret: str, prefix: int = 3, suffix: int = 4) -> str:
    if not secret:
        return "(unset)"
    if len(secret) <= prefix + suffix:
        if len(secret) <= 2:
            return "*" * len(secret)
        return f"{secret[0]}***{secret[-1]}"
    return f"{secret[:prefix]}***{secret[-suffix:]}"


def persist_llm_config(
    provider: str,
    api_key: str,
    base_url: str | None,
    model: str,
    temperature: float,
) -> Path:
    global _settings
    provider_name = _normalize_provider(provider)
    config = load_config_dict()
    llm_cfg = dict(config.get("llm", {}))
    llm_cfg.update(
        {
            "provider": provider_name,
            "api_key": api_key,
            "base_url": base_url or "",
            "model": model,
            "temperature": float(temperature),
        }
    )
    config["llm"] = llm_cfg

    _DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        import tomli_w
    except ModuleNotFoundError as exc:  # pragma: no cover - validated in runtime env
        raise RuntimeError(
            "tomli-w is required for writing config files. Install dependencies with `pip install -e .`."
        ) from exc

    with open(_DEFAULT_CONFIG_PATH, "wb") as f:
        tomli_w.dump(config, f)

    # Reset cache so follow-up reads in the same process load fresh values.
    _settings = None
    return _DEFAULT_CONFIG_PATH


def get_settings() -> Settings:
    global _settings
    if _settings is not None:
        return _settings

    config = load_config_dict()

    llm_cfg = config.get("llm", {})
    storage_cfg = config.get("storage", {})
    display_cfg = config.get("display", {})

    provider = _normalize_provider(str(llm_cfg.get("provider", "openai")))
    env_key = _PROVIDER_ENV_KEY_MAP[provider]
    api_key = os.environ.get(env_key) or str(llm_cfg.get("api_key", ""))
    base_url = str(llm_cfg.get("base_url") or "") or get_provider_default_base_url(provider)
    data_dir = Path(
        storage_cfg.get("data_dir", str(_DEFAULT_DATA_DIR))
    ).expanduser()
    data_dir.mkdir(parents=True, exist_ok=True)

    _settings = Settings(
        llm_provider=provider,
        llm_api_key=api_key,
        llm_base_url=base_url,
        model_name=str(llm_cfg.get("model", get_provider_default_model(provider))),
        temperature=float(llm_cfg.get("temperature", 0.7)),
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
        normalized_provider = _normalize_provider(provider)
        updates["llm_provider"] = normalized_provider
        # If provider changes and caller did not specify base_url, reset to provider default.
        if base_url is None:
            updates["llm_base_url"] = get_provider_default_base_url(normalized_provider)

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

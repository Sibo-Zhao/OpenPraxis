"""Config persistence and reload tests."""

import tomllib

import pytest

import openpraxis.config as config_module


@pytest.fixture
def tmp_user_config(monkeypatch: pytest.MonkeyPatch, tmp_path):
    cfg_dir = tmp_path / ".openpraxis"
    cfg_path = cfg_dir / "config.toml"
    monkeypatch.setattr(config_module, "_DEFAULT_CONFIG_DIR", cfg_dir)
    monkeypatch.setattr(config_module, "_DEFAULT_CONFIG_PATH", cfg_path)
    monkeypatch.setattr(config_module, "_DEFAULT_DATA_DIR", cfg_dir / "data")
    monkeypatch.setattr(config_module, "_settings", None)
    yield cfg_path
    monkeypatch.setattr(config_module, "_settings", None)


def test_persist_llm_config_creates_config_dir_and_file(tmp_user_config) -> None:
    saved_path = config_module.persist_llm_config(
        provider="openai",
        api_key="sk-test-openai",
        base_url="",
        model="gpt-4o",
        temperature=0.7,
    )

    assert saved_path == tmp_user_config
    assert tmp_user_config.exists()
    with open(tmp_user_config, "rb") as f:
        cfg = tomllib.load(f)
    assert cfg["llm"]["provider"] == "openai"
    assert cfg["llm"]["api_key"] == "sk-test-openai"
    assert cfg["llm"]["model"] == "gpt-4o"
    assert cfg["llm"]["temperature"] == 0.7


def test_persist_llm_config_updates_only_llm_section_keys(tmp_user_config) -> None:
    tmp_user_config.parent.mkdir(parents=True, exist_ok=True)
    tmp_user_config.write_text(
        (
            "[llm]\n"
            "provider = \"openai\"\n"
            "api_key = \"old\"\n"
            "model = \"gpt-4o\"\n"
            "temperature = 0.7\n"
            "note = \"keep\"\n\n"
            "[storage]\n"
            "data_dir = \"~/.openpraxis/data\"\n\n"
            "[display]\n"
            "color = true\n"
        ),
        encoding="utf-8",
    )

    config_module.persist_llm_config(
        provider="kimi",
        api_key="new-kimi-key",
        base_url="",
        model="kimi-k2-turbo-preview",
        temperature=0.6,
    )

    with open(tmp_user_config, "rb") as f:
        cfg = tomllib.load(f)
    assert cfg["llm"]["provider"] == "kimi"
    assert cfg["llm"]["api_key"] == "new-kimi-key"
    assert cfg["llm"]["model"] == "kimi-k2-turbo-preview"
    assert cfg["llm"]["temperature"] == 0.6
    assert cfg["llm"]["note"] == "keep"
    assert cfg["storage"]["data_dir"] == "~/.openpraxis/data"
    assert cfg["display"]["color"] is True


def test_reload_settings_after_persist(tmp_user_config, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ARK_API_KEY", raising=False)
    monkeypatch.delenv("MOONSHOT_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    config_module.persist_llm_config(
        provider="openai",
        api_key="sk-openai-1",
        base_url="",
        model="gpt-4o",
        temperature=0.7,
    )
    first = config_module.get_settings()
    assert first.llm_provider == "openai"
    assert first.llm_api_key == "sk-openai-1"
    assert first.model_name == "gpt-4o"

    config_module.persist_llm_config(
        provider="deepseek",
        api_key="sk-deepseek-2",
        base_url="",
        model="deepseek-chat",
        temperature=0.3,
    )
    second = config_module.get_settings()
    assert second.llm_provider == "deepseek"
    assert second.llm_api_key == "sk-deepseek-2"
    assert second.model_name == "deepseek-chat"
    assert second.temperature == 0.3

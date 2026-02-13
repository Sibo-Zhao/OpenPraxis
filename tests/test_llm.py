"""LLM provider compatibility tests."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from openpraxis.llm import call_chat_structured, call_structured


class DemoResponse(BaseModel):
    text: str


def _settings(provider: str) -> SimpleNamespace:
    return SimpleNamespace(
        llm_provider=provider,
        llm_api_key="test-key",
        llm_base_url=None,
        model_name="test-model",
    )


def test_call_structured_openai_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    parsed = DemoResponse(text="ok")
    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed, refusal=None))]
    )
    client = MagicMock()
    client.beta.chat.completions.parse.return_value = completion

    monkeypatch.setattr("openpraxis.llm.get_settings", lambda: _settings("openai"))
    monkeypatch.setattr("openpraxis.llm.get_client", lambda: client)

    result = call_structured("system", "user", DemoResponse)

    assert result == parsed
    kwargs = client.beta.chat.completions.parse.call_args.kwargs
    assert kwargs["response_format"] is DemoResponse
    assert kwargs["messages"][0]["role"] == "system"
    assert kwargs["messages"][1]["role"] == "user"


def test_call_structured_doubao_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    parsed = DemoResponse(text="doubao")
    client = MagicMock()
    client.responses.parse.return_value = SimpleNamespace(output_parsed=parsed)

    monkeypatch.setattr("openpraxis.llm.get_settings", lambda: _settings("doubao"))
    monkeypatch.setattr("openpraxis.llm.get_client", lambda: client)

    result = call_structured("sys prompt", "user prompt", DemoResponse)

    assert result == parsed
    kwargs = client.responses.parse.call_args.kwargs
    assert kwargs["text_format"] is DemoResponse
    assert kwargs["input"][0]["role"] == "system"
    assert kwargs["input"][0]["content"][0]["text"] == "sys prompt"
    assert kwargs["input"][1]["role"] == "user"
    assert kwargs["input"][1]["content"][0]["text"] == "user prompt"


def test_call_chat_structured_kimi_json_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"text":"kimi"}'))]
    )
    messages = [
        {"role": "system", "content": "be helpful"},
        {"role": "user", "content": "hello"},
    ]

    monkeypatch.setattr("openpraxis.llm.get_settings", lambda: _settings("kimi"))
    monkeypatch.setattr("openpraxis.llm.get_client", lambda: client)

    result = call_chat_structured(messages, DemoResponse)

    assert result == DemoResponse(text="kimi")
    kwargs = client.chat.completions.create.call_args.kwargs
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["messages"][0]["role"] == "system"
    assert kwargs["messages"][1:] == messages


def test_call_structured_deepseek_invalid_json_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = MagicMock()
    client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"answer":"x"}'))]
    )

    monkeypatch.setattr("openpraxis.llm.get_settings", lambda: _settings("deepseek"))
    monkeypatch.setattr("openpraxis.llm.get_client", lambda: client)

    with pytest.raises(RuntimeError, match="does not match"):
        call_structured("system", "user", DemoResponse)

"""LLM backend abstraction tests."""

import pytest
from pydantic import BaseModel

from openpraxis.llm_backends.base import LLMBackend
from openpraxis.llm_backends.cli_backend import CLIBackend
from openpraxis.llm_backends.openclaw_backend import OpenClawBackend


class DummyModel(BaseModel):
    text: str


def test_cli_backend_is_llm_backend() -> None:
    assert issubclass(CLIBackend, LLMBackend)


def test_openclaw_backend_is_llm_backend() -> None:
    assert issubclass(OpenClawBackend, LLMBackend)


def test_openclaw_call_structured_raises() -> None:
    backend = OpenClawBackend()
    with pytest.raises(NotImplementedError, match="host-provided LLM integration"):
        backend.call_structured("sys", "user", DummyModel)


def test_openclaw_call_chat_structured_raises() -> None:
    backend = OpenClawBackend()
    with pytest.raises(NotImplementedError, match="host-provided LLM integration"):
        backend.call_chat_structured([], DummyModel)


def test_openclaw_call_vision_text_raises() -> None:
    backend = OpenClawBackend()
    with pytest.raises(NotImplementedError, match="host-provided LLM integration"):
        backend.call_vision_text("img.png", "describe")


def test_custom_backend_works() -> None:
    """A custom backend subclass should satisfy the interface."""

    class MyBackend(LLMBackend):
        def call_structured(self, system_prompt, user_content, response_model, **kw):
            return response_model(text="custom")

        def call_chat_structured(self, messages, response_model, **kw):
            return response_model(text="chat")

        def call_vision_text(self, image, prompt, **kw):
            return "vision"

    b = MyBackend()
    assert b.call_structured("", "", DummyModel).text == "custom"
    assert b.call_chat_structured([], DummyModel).text == "chat"
    assert b.call_vision_text("img", "prompt") == "vision"

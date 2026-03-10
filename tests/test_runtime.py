"""Runtime execution mode and backend management tests."""

import os

import pytest

from openpraxis import runtime
from openpraxis.llm_backends.base import LLMBackend
from openpraxis.llm_backends.cli_backend import CLIBackend
from openpraxis.llm_backends.openclaw_backend import OpenClawBackend
from openpraxis.runtime import ExecutionMode


@pytest.fixture(autouse=True)
def _reset_runtime():
    """Ensure clean runtime state for every test."""
    runtime.reset()
    yield
    runtime.reset()


def test_default_mode_is_standalone_cli() -> None:
    assert runtime.get_execution_mode() == ExecutionMode.STANDALONE_CLI


def test_set_execution_mode() -> None:
    runtime.set_execution_mode(ExecutionMode.OPENCLAW)
    assert runtime.get_execution_mode() == ExecutionMode.OPENCLAW


def test_auto_detect_openclaw_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENPRAXIS_MODE", "openclaw")
    runtime.reset()
    assert runtime.get_execution_mode() == ExecutionMode.OPENCLAW


def test_auto_detect_standalone_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENPRAXIS_MODE", raising=False)
    runtime.reset()
    assert runtime.get_execution_mode() == ExecutionMode.STANDALONE_CLI


def test_get_backend_returns_cli_by_default() -> None:
    backend = runtime.get_backend()
    assert isinstance(backend, CLIBackend)


def test_get_backend_returns_openclaw_when_mode_set() -> None:
    runtime.set_execution_mode(ExecutionMode.OPENCLAW)
    backend = runtime.get_backend()
    assert isinstance(backend, OpenClawBackend)


def test_set_backend_overrides_auto() -> None:
    class DummyBackend(LLMBackend):
        def call_structured(self, *a, **kw):
            return None
        def call_chat_structured(self, *a, **kw):
            return None
        def call_vision_text(self, *a, **kw):
            return ""

    dummy = DummyBackend()
    runtime.set_backend(dummy)
    assert runtime.get_backend() is dummy


def test_set_execution_mode_resets_cached_backend() -> None:
    _ = runtime.get_backend()  # cache a CLIBackend
    runtime.set_execution_mode(ExecutionMode.OPENCLAW)
    backend = runtime.get_backend()
    assert isinstance(backend, OpenClawBackend)


def test_reset_clears_everything() -> None:
    runtime.set_execution_mode(ExecutionMode.OPENCLAW)
    _ = runtime.get_backend()
    runtime.reset()
    assert runtime.get_execution_mode() == ExecutionMode.STANDALONE_CLI
    assert isinstance(runtime.get_backend(), CLIBackend)

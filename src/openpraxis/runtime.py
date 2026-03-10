"""Execution mode and LLM backend management.

This module is the single place that decides *how* LLM calls are dispatched.
Nodes and the graph never import a concrete backend directly — they call
``get_backend()`` and use the returned ``LLMBackend`` instance.

Two execution modes are supported:

* ``STANDALONE_CLI`` (default) — uses the local provider config managed by
  ``praxis llm setup`` or environment variables.
* ``OPENCLAW`` — delegates to the OpenClaw host agent.  No local API key
  configuration is required.

The mode can be set explicitly via ``set_execution_mode()`` or auto-detected
from the ``OPENPRAXIS_MODE`` environment variable (value ``openclaw``).
"""

from __future__ import annotations

import os
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openpraxis.llm_backends.base import LLMBackend


class ExecutionMode(str, Enum):
    OPENCLAW = "openclaw"
    STANDALONE_CLI = "standalone_cli"


_backend: LLMBackend | None = None
_execution_mode: ExecutionMode = ExecutionMode.STANDALONE_CLI
_mode_initialized: bool = False


def _auto_detect_mode() -> ExecutionMode:
    """Detect execution mode from the ``OPENPRAXIS_MODE`` env var."""
    env = os.environ.get("OPENPRAXIS_MODE", "").strip().lower()
    if env == "openclaw":
        return ExecutionMode.OPENCLAW
    return ExecutionMode.STANDALONE_CLI


def get_execution_mode() -> ExecutionMode:
    global _execution_mode, _mode_initialized
    if not _mode_initialized:
        _execution_mode = _auto_detect_mode()
        _mode_initialized = True
    return _execution_mode


def set_execution_mode(mode: ExecutionMode) -> None:
    global _execution_mode, _mode_initialized, _backend
    _execution_mode = mode
    _mode_initialized = True
    # Reset backend so the next get_backend() picks the right one.
    _backend = None


def get_backend() -> LLMBackend:
    global _backend
    if _backend is not None:
        return _backend

    mode = get_execution_mode()
    if mode == ExecutionMode.OPENCLAW:
        from openpraxis.llm_backends.openclaw_backend import OpenClawBackend

        _backend = OpenClawBackend()
    else:
        from openpraxis.llm_backends.cli_backend import CLIBackend

        _backend = CLIBackend()
    return _backend


def set_backend(backend: LLMBackend | None) -> None:
    global _backend
    _backend = backend


def reset() -> None:
    """Reset runtime state. Useful for testing."""
    global _backend, _execution_mode, _mode_initialized
    _backend = None
    _execution_mode = ExecutionMode.STANDALONE_CLI
    _mode_initialized = False

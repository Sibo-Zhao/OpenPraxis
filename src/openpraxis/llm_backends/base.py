"""Abstract LLM backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel


class LLMBackend(ABC):
    """Unified interface for LLM calls.

    Decouples business workflow (nodes, graph) from the concrete model provider.
    Two implementations ship today:

    * ``CLIBackend``  – uses local provider config (config.toml / env vars).
    * ``OpenClawBackend`` – placeholder for host-managed LLM in OpenClaw skill mode.
    """

    @abstractmethod
    def call_structured(
        self,
        system_prompt: str,
        user_content: str,
        response_model: type[BaseModel],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> BaseModel:
        """Call LLM with structured output, return parsed Pydantic model."""

    @abstractmethod
    def call_chat_structured(
        self,
        messages: list[dict],
        response_model: type[BaseModel],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> BaseModel:
        """Call LLM with a full message list and structured output."""

    @abstractmethod
    def call_vision_text(
        self,
        image: str | Path,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        """Call a vision-capable model with an image + prompt, return plain text."""

"""CLI backend – wraps existing llm.py provider logic for standalone CLI mode."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from openpraxis.llm_backends.base import LLMBackend


class CLIBackend(LLMBackend):
    """Backend that uses local provider configuration (config.toml / env vars).

    This is the default backend for ``praxis`` CLI users who manage their own
    API keys via ``praxis llm setup`` or environment variables.
    """

    def call_structured(
        self,
        system_prompt: str,
        user_content: str,
        response_model: type[BaseModel],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> BaseModel:
        from openpraxis.llm import call_structured

        return call_structured(
            system_prompt, user_content, response_model,
            model=model, temperature=temperature,
        )

    def call_chat_structured(
        self,
        messages: list[dict],
        response_model: type[BaseModel],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> BaseModel:
        from openpraxis.llm import call_chat_structured

        return call_chat_structured(
            messages, response_model,
            model=model, temperature=temperature,
        )

    def call_vision_text(
        self,
        image: str | Path,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        from openpraxis.llm import call_vision_text

        return call_vision_text(image, prompt, model=model, temperature=temperature)

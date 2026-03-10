"""OpenClaw backend – delegates LLM calls to the OpenClaw host agent.

In a real OpenClaw skill context the host agent owns model configuration and
authentication.  This backend is the integration point: an OpenClaw runner
would subclass or replace it to wire calls through the host's LLM capability.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from openpraxis.llm_backends.base import LLMBackend


class OpenClawBackend(LLMBackend):
    """Backend for running inside an OpenClaw skill context.

    No local API key configuration is required.  All model calls are expected
    to be satisfied by the host agent.

    The default implementation raises ``NotImplementedError`` to make it clear
    that a concrete host integration is needed.  An OpenClaw runner should
    either:

    1. Subclass this and override the three methods, or
    2. Provide a fully custom ``LLMBackend`` via ``runtime.set_backend()``.
    """

    def call_structured(
        self,
        system_prompt: str,
        user_content: str,
        response_model: type[BaseModel],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> BaseModel:
        raise NotImplementedError(
            "OpenClaw backend requires a host-provided LLM integration. "
            "Subclass OpenClawBackend or supply a custom backend via "
            "runtime.set_backend()."
        )

    def call_chat_structured(
        self,
        messages: list[dict],
        response_model: type[BaseModel],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> BaseModel:
        raise NotImplementedError(
            "OpenClaw backend requires a host-provided LLM integration. "
            "Subclass OpenClawBackend or supply a custom backend via "
            "runtime.set_backend()."
        )

    def call_vision_text(
        self,
        image: str | Path,
        prompt: str,
        model: str | None = None,
        temperature: float = 0.0,
    ) -> str:
        raise NotImplementedError(
            "OpenClaw backend requires a host-provided LLM integration. "
            "Subclass OpenClawBackend or supply a custom backend via "
            "runtime.set_backend()."
        )

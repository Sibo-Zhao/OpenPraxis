"""OpenAI client wrapper."""

import base64
import json
import mimetypes
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel

from openpraxis.config import get_settings

if TYPE_CHECKING:
    from openai import OpenAI

_client: "OpenAI | None" = None
_client_signature: tuple[str, str | None, str] | None = None
_SUPPORTED_PROVIDERS = {"openai", "doubao", "kimi", "deepseek"}


def get_client():  # -> OpenAI
    global _client
    global _client_signature

    settings = get_settings()
    provider = settings.llm_provider
    signature = (provider, settings.llm_base_url, settings.llm_api_key)

    if provider not in _SUPPORTED_PROVIDERS:
        raise ValueError(f"Unsupported llm provider: {provider}")

    if _client is None or _client_signature != signature:
        from openai import OpenAI

        kwargs = {"api_key": settings.llm_api_key}
        if settings.llm_base_url:
            kwargs["base_url"] = settings.llm_base_url
        _client = OpenAI(**kwargs)
        _client_signature = signature
    return _client


def _parse_or_raise(content: str | None, response_model: type[BaseModel]) -> BaseModel:
    if not content:
        raise RuntimeError("LLM returned empty JSON content.")
    try:
        return response_model.model_validate_json(content)
    except Exception as exc:  # pragma: no cover - exact exception types vary by SDK version
        raise RuntimeError(
            f"LLM JSON output does not match {response_model.__name__}: {content}"
        ) from exc


def _json_schema_instruction(response_model: type[BaseModel]) -> str:
    schema = response_model.model_json_schema()
    return (
        "Return ONLY a JSON object that matches this JSON Schema exactly.\n"
        f"{json.dumps(schema, ensure_ascii=True)}"
    )


def _as_responses_input(messages: list[dict]) -> list[dict]:
    converted: list[dict] = []
    for message in messages:
        role = str(message.get("role", "user"))
        content = message.get("content", "")
        if isinstance(content, list):
            converted.append({"role": role, "content": content})
            continue
        converted.append(
            {
                "role": role,
                "content": [{"type": "input_text", "text": str(content)}],
            }
        )
    return converted


def _guess_image_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    if mime and mime.startswith("image/"):
        return mime
    # Fallback for common extensions when mimetypes is incomplete.
    suffix = path.suffix.lower().lstrip(".")
    if suffix in {"jpg", "jpeg"}:
        return "image/jpeg"
    if suffix in {"png", "webp", "gif", "bmp", "tiff"}:
        return f"image/{suffix}"
    return "image/png"


def _image_to_data_url(path: Path) -> str:
    mime = _guess_image_mime(path)
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _response_text(response) -> str:
    text = getattr(response, "output_text", None)
    if isinstance(text, str) and text.strip():
        return text

    # Best-effort fallback across SDK variants.
    output = getattr(response, "output", None)
    if not isinstance(output, list):
        raise RuntimeError("LLM returned empty text output.")
    chunks: list[str] = []
    for item in output:
        content = getattr(item, "content", None) or item.get("content") if isinstance(item, dict) else None
        if not isinstance(content, list):
            continue
        for part in content:
            part_type = getattr(part, "type", None) or part.get("type") if isinstance(part, dict) else None
            if part_type in {"output_text", "text"}:
                val = getattr(part, "text", None) or part.get("text") if isinstance(part, dict) else None
                if isinstance(val, str):
                    chunks.append(val)
    combined = "\n".join([c for c in chunks if c.strip()]).strip()
    if not combined:
        raise RuntimeError("LLM returned empty text output.")
    return combined


def call_vision_text(
    image: str | Path,
    prompt: str,
    model: str | None = None,
    temperature: float = 0.0,
) -> str:
    """Call a vision-capable model with an image + prompt, return plain text."""
    settings = get_settings()
    if settings.llm_provider not in {"openai", "doubao"}:
        raise ValueError(
            f"Vision input is only supported for openai/doubao providers (got {settings.llm_provider})."
        )

    if isinstance(image, Path):
        image_url = _image_to_data_url(image)
    else:
        image_url = str(image)

    client = get_client()
    response = client.responses.create(
        model=model or settings.model_name,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": image_url},
                    {"type": "input_text", "text": str(prompt)},
                ],
            }
        ],
        temperature=temperature,
    )
    return _response_text(response)


def _call_openai_parse(
    messages: list[dict],
    response_model: type[BaseModel],
    model_name: str,
    temperature: float,
) -> BaseModel:
    client = get_client()
    completion = client.beta.chat.completions.parse(
        model=model_name,
        messages=messages,
        response_format=response_model,
        temperature=temperature,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        refusal = getattr(
            completion.choices[0].message, "refusal", None
        ) or "(unknown)"
        raise RuntimeError(f"LLM did not return valid output. Refusal: {refusal}")
    return parsed


def _call_doubao_parse(
    messages: list[dict],
    response_model: type[BaseModel],
    model_name: str,
    temperature: float,
) -> BaseModel:
    client = get_client()
    response = client.responses.parse(
        model=model_name,
        input=_as_responses_input(messages),
        text_format=response_model,
        temperature=temperature,
    )
    parsed = getattr(response, "output_parsed", None)
    if parsed is None:
        raise RuntimeError("Doubao did not return valid structured output.")
    return parsed


def _call_json_mode(
    messages: list[dict],
    response_model: type[BaseModel],
    model_name: str,
    temperature: float,
) -> BaseModel:
    client = get_client()
    completion = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "system", "content": _json_schema_instruction(response_model)}, *messages],
        response_format={"type": "json_object"},
        temperature=temperature,
    )
    content = completion.choices[0].message.content
    return _parse_or_raise(content, response_model)


def _call_provider_structured(
    messages: list[dict],
    response_model: type[BaseModel],
    model_name: str,
    temperature: float,
) -> BaseModel:
    settings = get_settings()
    provider = settings.llm_provider
    if provider == "openai":
        return _call_openai_parse(messages, response_model, model_name, temperature)
    if provider == "doubao":
        return _call_doubao_parse(messages, response_model, model_name, temperature)
    if provider in {"kimi", "deepseek"}:
        return _call_json_mode(messages, response_model, model_name, temperature)
    raise ValueError(f"Unsupported llm provider: {provider}")


def call_structured(
    system_prompt: str,
    user_content: str,
    response_model: type[BaseModel],
    model: str | None = None,
    temperature: float = 0.7,
) -> BaseModel:
    """Call configured LLM with structured output, return parsed Pydantic model."""
    settings = get_settings()
    return _call_provider_structured(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_model=response_model,
        model_name=model or settings.model_name,
        temperature=temperature,
    )


def call_chat_structured(
    messages: list[dict],
    response_model: type[BaseModel],
    model: str | None = None,
    temperature: float = 0.7,
) -> BaseModel:
    """Call configured LLM with a full message list and structured output."""
    settings = get_settings()
    return _call_provider_structured(
        messages=[
            {"role": str(message.get("role", "")), "content": message.get("content", "")}
            for message in messages
        ],
        response_model=response_model,
        model_name=model or settings.model_name,
        temperature=temperature,
    )

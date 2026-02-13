"""OpenAI 客户端封装。"""

from pydantic import BaseModel

from openpraxis.config import get_settings

_client: "OpenAI | None" = None


def get_client():  # -> OpenAI
    global _client
    if _client is None:
        from openai import OpenAI

        settings = get_settings()
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def call_structured(
    system_prompt: str,
    user_content: str,
    response_model: type[BaseModel],
    model: str | None = None,
    temperature: float = 0.7,
) -> BaseModel:
    """调用 GPT-4o，使用 structured output 返回解析后的 Pydantic 模型。"""
    settings = get_settings()
    client = get_client()

    completion = client.beta.chat.completions.parse(
        model=model or settings.model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        response_format=response_model,
        temperature=temperature,
    )

    parsed = completion.choices[0].message.parsed
    if parsed is None:
        refusal = getattr(
            completion.choices[0].message, "refusal", None
        ) or "(unknown)"
        raise RuntimeError(f"LLM 未返回有效输出。Refusal: {refusal}")
    return parsed

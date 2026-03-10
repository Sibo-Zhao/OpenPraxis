"""Tagger Agent node."""

from openpraxis.models import RoutingPolicy, TaggerOutput
from openpraxis.prompts import get_tagger_system_prompt
from openpraxis.runtime import get_backend


def tagger_node(state: dict) -> dict:
    """Call LLM to classify and map capabilities; return tagger_output and should_practice."""
    raw_text = state["raw_text"]
    type_hint = state.get("type_hint")
    user_content = raw_text
    if type_hint:
        user_content = f"[User type hint: {type_hint}]\n\n{raw_text}"

    backend = get_backend()
    output: TaggerOutput = backend.call_structured(
        get_tagger_system_prompt(),
        user_content,
        TaggerOutput,
    )
    should = output.routing_policy != RoutingPolicy.NONE
    return {"tagger_output": output, "should_practice": should}

"""Insight generation node."""

from openpraxis.llm import call_structured
from openpraxis.models import InsightCard, InsightList
from openpraxis.prompts import get_insight_generator_system_prompt


def insight_generator_node(state: dict) -> dict:
    """Generate insight cards from Tagger + scene + answer + evaluation."""
    tagger_output = state["tagger_output"]
    scene = state["scene"]
    user_answer = state["user_answer"]
    performance = state["performance"]
    user_content = (
        f"Input summary: {tagger_output.summary}\n"
        f"Capability map: {tagger_output.capability_map.model_dump()}\n\n"
        f"Scene: {scene.role} — {scene.task}\n"
        f"User answer: {user_answer}\n\n"
        f"Evaluation: {performance.performance_signal.model_dump()}\n"
        f"Improvement vectors: {performance.improvement_vectors}\n\n"
        f"scene_id: {scene.scene_id}"
    )
    result: InsightList = call_structured(
        get_insight_generator_system_prompt(),
        user_content,
        InsightList,
    )
    return {"insights": result.cards}

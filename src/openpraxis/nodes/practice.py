"""Practice generation + human answer + evaluation nodes."""

from uuid import uuid4

from langgraph.types import interrupt

from openpraxis.llm import call_structured
from openpraxis.models import (
    PracticePerformance,
    PracticeScene,
    PracticeSceneLLM,
)
from openpraxis.prompts import (
    get_practice_evaluator_system_prompt,
    get_practice_generator_system_prompt,
)


def practice_generator_node(state: dict) -> dict:
    """Generate practice scene."""
    tagger_output = state["tagger_output"]
    raw_text = state["raw_text"]
    seed = tagger_output.practice_seed
    user_content = (
        f"Summary: {tagger_output.summary}\n\n"
        f"Raw content:\n{raw_text}\n\n"
        f"Preferred scene type: {seed.preferred_scene.value}\n"
        f"Skills: {seed.skills}\nConcepts: {seed.concepts}\nConstraints: {seed.constraints}"
    )
    llm_scene: PracticeSceneLLM = call_structured(
        get_practice_generator_system_prompt(),
        user_content,
        PracticeSceneLLM,
    )
    scene = PracticeScene(
        scene_id=str(uuid4()),
        scene_type=llm_scene.scene_type,
        role=llm_scene.role,
        task=llm_scene.task,
        constraints=llm_scene.constraints,
        rubric=llm_scene.rubric,
        expected_structure_hint=llm_scene.expected_structure_hint,
    )
    return {"scene": scene}


def human_answer_node(state: dict) -> dict:
    """interrupt() pauses graph until user answers, then resume."""
    scene = state["scene"]
    payload = {
        "scene_id": scene.scene_id,
        "role": scene.role,
        "task": scene.task,
        "constraints": scene.constraints,
        "expected_structure_hint": scene.expected_structure_hint,
    }
    user_answer = interrupt(payload)
    return {"user_answer": user_answer}


def practice_evaluator_node(state: dict) -> dict:
    """Score user answer."""
    scene = state["scene"]
    user_answer = state["user_answer"]
    raw_text = state.get("raw_text", "")
    user_content = (
        f"Scene task: {scene.task}\nConstraints: {scene.constraints}\n"
        f"Rubric: {scene.rubric}\n\n"
        f"User answer:\n{user_answer}\n\n"
        f"Raw learning content (reference):\n{raw_text}"
    )
    performance: PracticePerformance = call_structured(
        get_practice_evaluator_system_prompt(),
        user_content,
        PracticePerformance,
    )
    return {"performance": performance}

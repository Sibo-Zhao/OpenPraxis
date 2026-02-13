"""Practice generation + multi-turn coaching + evaluation nodes."""

from uuid import uuid4

from langgraph.types import interrupt

from openpraxis.llm import call_chat_structured, call_structured
from openpraxis.models import (
    CoachReply,
    PracticeMessage,
    PracticePerformance,
    PracticeScene,
    PracticeSceneLLM,
)
from openpraxis.prompts import (
    get_practice_coach_system_prompt,
    get_practice_evaluator_system_prompt,
    get_practice_generator_system_prompt,
)

MAX_PRACTICE_ROUNDS = 3


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


def _build_coach_messages(
    scene: PracticeScene,
    practice_messages: list[PracticeMessage],
) -> list[dict]:
    """Build the OpenAI message list for the coach LLM."""
    system_prompt = get_practice_coach_system_prompt()
    scene_context = (
        f"Scene role: {scene.role}\n"
        f"Task: {scene.task}\n"
        f"Constraints: {scene.constraints}\n"
        f"Structure hints: {scene.expected_structure_hint}"
    )
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"[Scene context]\n{scene_context}"},
    ]
    for msg in practice_messages:
        role = "assistant" if msg.role == "coach" else "user"
        messages.append({"role": role, "content": msg.content})
    return messages


def coach_turn_node(state: dict) -> dict:
    """Coach generates a message (question / follow-up / wrap-up)."""
    scene = state["scene"]
    practice_messages: list[PracticeMessage] = state.get("practice_messages", [])

    messages = _build_coach_messages(scene, practice_messages)
    reply: CoachReply = call_chat_structured(messages, CoachReply)

    coach_msg = PracticeMessage(role="coach", content=reply.message)
    return {
        "practice_messages": [coach_msg],
        "coach_ready": reply.ready_for_evaluation,
    }


def human_turn_node(state: dict) -> dict:
    """Interrupt to collect user reply, append to practice_messages."""
    practice_messages: list[PracticeMessage] = state.get("practice_messages", [])

    # Find the latest coach message to show the user
    coach_msgs = [m for m in practice_messages if m.role == "coach"]
    latest_coach = coach_msgs[-1].content if coach_msgs else ""

    scene = state["scene"]
    practice_round = state.get("practice_round", 0)

    payload = {
        "scene_id": scene.scene_id,
        "round": practice_round + 1,
        "coach_message": latest_coach,
    }
    user_reply = interrupt(payload)

    user_msg = PracticeMessage(role="user", content=user_reply)
    return {
        "practice_messages": [user_msg],
        "practice_round": practice_round + 1,
    }


def _format_conversation(practice_messages: list[PracticeMessage]) -> str:
    """Format multi-turn practice_messages into a readable transcript."""
    lines = []
    for msg in practice_messages:
        label = "Coach" if msg.role == "coach" else "User"
        lines.append(f"[{label}]: {msg.content}")
    return "\n\n".join(lines)


def practice_evaluator_node(state: dict) -> dict:
    """Score user answer based on full conversation transcript."""
    scene = state["scene"]
    raw_text = state.get("raw_text", "")
    practice_messages: list[PracticeMessage] = state.get("practice_messages", [])

    # Format full conversation for evaluator
    if practice_messages:
        conversation = _format_conversation(practice_messages)
    else:
        # Fallback for legacy single-turn user_answer
        conversation = state.get("user_answer", "")

    user_content = (
        f"Scene task: {scene.task}\nConstraints: {scene.constraints}\n"
        f"Rubric: {scene.rubric}\n\n"
        f"Practice conversation:\n{conversation}\n\n"
        f"Raw learning content (reference):\n{raw_text}"
    )
    performance: PracticePerformance = call_structured(
        get_practice_evaluator_system_prompt(),
        user_content,
        PracticePerformance,
    )
    return {
        "performance": performance,
        "user_answer": conversation,
    }

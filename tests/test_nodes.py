"""Node function isolation tests (mock call_structured)."""

import pytest

from openpraxis.nodes.tagger import tagger_node
from openpraxis.nodes.practice import (
    coach_turn_node,
    practice_evaluator_node,
    practice_generator_node,
    _format_conversation,
)
from openpraxis.nodes.insight import insight_generator_node
from openpraxis.models import PracticeMessage


@pytest.mark.usefixtures("mock_llm")
def test_tagger_node() -> None:
    state = {
        "raw_text": "This is a report about RAG.",
        "type_hint": None,
    }
    out = tagger_node(state)
    assert "tagger_output" in out
    assert "should_practice" in out
    assert out["tagger_output"].summary == "A technical report on RAG pipeline architecture."
    assert out["should_practice"] is True


@pytest.mark.usefixtures("mock_llm")
def test_practice_generator_node(mock_tagger_output) -> None:
    state = {
        "tagger_output": mock_tagger_output,
        "raw_text": "Raw content",
    }
    out = practice_generator_node(state)
    assert "scene" in out
    assert out["scene"].role == "Tech Lead"


@pytest.mark.usefixtures("mock_llm")
def test_coach_turn_node_first_turn(mock_scene) -> None:
    """First coach turn: no prior messages."""
    state = {
        "scene": mock_scene,
        "practice_messages": [],
    }
    out = coach_turn_node(state)
    assert "practice_messages" in out
    assert len(out["practice_messages"]) == 1
    assert out["practice_messages"][0].role == "coach"
    assert out["coach_ready"] is False


@pytest.mark.usefixtures("mock_llm")
def test_coach_turn_node_with_history(mock_scene) -> None:
    """Coach turn after user reply: should get follow-up question."""
    state = {
        "scene": mock_scene,
        "practice_messages": [
            PracticeMessage(role="coach", content="Walk me through failure modes?"),
            PracticeMessage(role="user", content="Retrieval miss and context overflow."),
        ],
    }
    out = coach_turn_node(state)
    assert len(out["practice_messages"]) == 1
    assert out["practice_messages"][0].role == "coach"
    # Second call → still not ready
    assert out["coach_ready"] is False


@pytest.mark.usefixtures("mock_llm")
def test_practice_evaluator_node_with_messages() -> None:
    from openpraxis.models import PracticeScene, SceneType

    state = {
        "scene": PracticeScene(
            scene_id="s1",
            scene_type=SceneType.EXPLAIN,
            role="R",
            task="T",
            constraints=[],
            rubric=[],
            expected_structure_hint=[],
        ),
        "practice_messages": [
            PracticeMessage(role="coach", content="Explain failure modes."),
            PracticeMessage(role="user", content="Retrieval miss is the main one."),
        ],
        "raw_text": "Raw",
    }
    out = practice_evaluator_node(state)
    assert "performance" in out
    assert out["performance"].performance_signal.clarity == 7
    # user_answer should be the formatted conversation
    assert "user_answer" in out
    assert "[Coach]:" in out["user_answer"]
    assert "[User]:" in out["user_answer"]


def test_format_conversation() -> None:
    msgs = [
        PracticeMessage(role="coach", content="Question?"),
        PracticeMessage(role="user", content="Answer."),
        PracticeMessage(role="coach", content="Follow-up?"),
        PracticeMessage(role="user", content="More detail."),
    ]
    result = _format_conversation(msgs)
    assert "[Coach]: Question?" in result
    assert "[User]: Answer." in result
    assert "[Coach]: Follow-up?" in result
    assert "[User]: More detail." in result


@pytest.mark.usefixtures("mock_llm")
def test_insight_generator_node() -> None:
    from openpraxis.models import (
        InputType,
        PracticePerformance,
        PracticeScene,
        PerformanceSignal,
        SceneType,
        TaggerOutput,
        Tags,
        CapabilityMap,
        PracticeSeed,
        RoutingPolicy,
        Sensitivity,
    )

    state = {
        "tagger_output": TaggerOutput(
            input_type=InputType.REPORT,
            summary="Summary",
            tags=Tags(topics=[], domains=[], difficulty=1, sensitivity=Sensitivity.NORMAL),
            capability_map=CapabilityMap(
                concept_understanding=5,
                structuring=5,
                tradeoff_thinking=5,
                system_thinking=5,
                communication=5,
            ),
            routing_policy=RoutingPolicy.NONE,
            practice_seed=PracticeSeed(
                preferred_scene=SceneType.EXPLAIN,
                skills=[],
                concepts=[],
                constraints=[],
            ),
        ),
        "scene": PracticeScene(
            scene_id="s2",
            scene_type=SceneType.EXPLAIN,
            role="R",
            task="T",
            constraints=[],
            rubric=[],
            expected_structure_hint=[],
        ),
        "user_answer": "[Coach]: Q?\n\n[User]: A.",
        "performance": PracticePerformance(
            performance_signal=PerformanceSignal(
                clarity=6,
                reasoning_depth=6,
                decision_quality=6,
                communication=6,
            ),
            improvement_vectors=[],
        ),
    }
    out = insight_generator_node(state)
    assert "insights" in out
    assert len(out["insights"]) >= 1
    assert out["insights"][0].insight_title == "Structured expression gap"

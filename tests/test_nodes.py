"""Node function isolation tests (mock call_structured)."""

import pytest

from openpraxis.nodes.tagger import tagger_node
from openpraxis.nodes.practice import (
    practice_generator_node,
    practice_evaluator_node,
)
from openpraxis.nodes.insight import insight_generator_node


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
def test_practice_evaluator_node() -> None:
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
        "user_answer": "My answer content",
        "raw_text": "Raw",
    }
    out = practice_evaluator_node(state)
    assert "performance" in out
    assert out["performance"].performance_signal.clarity == 7


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
        "user_answer": "Answer",
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

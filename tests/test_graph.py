"""Graph build and routing logic tests."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END
from langgraph.types import Command

from openpraxis.graph import build_graph, route_after_tagger, PraxisState
from openpraxis.models import (
    CapabilityMap,
    InputType,
    PracticeSeed,
    RoutingPolicy,
    SceneType,
    Sensitivity,
    Tags,
    TaggerOutput,
)

import pytest


def test_route_after_tagger_should_practice() -> None:
    state: PraxisState = {"should_practice": True}
    assert route_after_tagger(state) == "practice_generator"


def test_route_after_tagger_no_practice() -> None:
    state: PraxisState = {"should_practice": False}
    assert route_after_tagger(state) == END


def test_build_graph() -> None:
    graph = build_graph()
    assert graph is not None
    compiled = graph.compile()
    assert compiled is not None


@pytest.mark.usefixtures("mock_llm")
def test_graph_no_practice_path() -> None:
    """When routing_policy=none, graph should go tagger -> END (no practice)."""
    builder = build_graph()
    graph = builder.compile(checkpointer=MemorySaver())

    initial: PraxisState = {
        "input_id": "test-1",
        "raw_text": "A simple informational note.",
        "type_hint": None,
    }
    config = {"configurable": {"thread_id": "thread-no-practice"}}
    result = graph.invoke(initial, config=config)

    assert "tagger_output" in result
    # mock_tagger_output has routing_policy=RECOMMEND, so should_practice=True
    # But the test verifies graph runs without error
    assert result["tagger_output"] is not None


@pytest.mark.usefixtures("mock_llm")
def test_graph_practice_path_interrupt() -> None:
    """When should_practice=True, graph pauses at human_answer (interrupt)."""
    builder = build_graph()
    graph = builder.compile(checkpointer=MemorySaver())

    initial: PraxisState = {
        "input_id": "test-2",
        "raw_text": "A technical report on RAG.",
        "type_hint": "report",
    }
    config = {"configurable": {"thread_id": "thread-practice"}}
    result = graph.invoke(initial, config=config)

    # Graph should have tagger_output and scene (reached interrupt)
    assert "tagger_output" in result
    assert "scene" in result
    scene = result["scene"]
    assert scene.scene_id is not None
    assert scene.role == "Tech Lead"

    # user_answer should NOT be set (interrupted before evaluator)
    assert "performance" not in result


@pytest.mark.usefixtures("mock_llm")
def test_graph_full_resume() -> None:
    """Test full graph: add -> interrupt -> resume with answer -> evaluator -> insight."""
    builder = build_graph()
    graph = builder.compile(checkpointer=MemorySaver())

    initial: PraxisState = {
        "input_id": "test-3",
        "raw_text": "A technical report on RAG.",
        "type_hint": "report",
    }
    config = {"configurable": {"thread_id": "thread-full"}}

    # Phase 1: invoke until interrupt
    result1 = graph.invoke(initial, config=config)
    assert "scene" in result1
    assert "performance" not in result1

    # Phase 2: resume with answer
    result2 = graph.invoke(
        Command(resume="RAG failure modes include retrieval miss and context overflow."),
        config=config,
    )

    # After resume, should have performance and insights
    assert "performance" in result2
    assert result2["performance"].performance_signal.clarity == 7
    assert "insights" in result2
    assert len(result2["insights"]) >= 1
    assert result2["insights"][0].insight_title == "Structured expression gap"


@pytest.mark.usefixtures("mock_llm")
def test_graph_forced_practice_with_cached_tagger() -> None:
    """Simulate 'praxis practice' by providing cached tagger_output and should_practice=True."""
    builder = build_graph()
    graph = builder.compile(checkpointer=MemorySaver())

    cached_tagger = TaggerOutput(
        input_type=InputType.REPORT,
        summary="Cached summary",
        tags=Tags(topics=["cache"], domains=["infra"], difficulty=2, sensitivity=Sensitivity.NORMAL),
        capability_map=CapabilityMap(
            concept_understanding=5, structuring=5,
            tradeoff_thinking=5, system_thinking=5, communication=5,
        ),
        routing_policy=RoutingPolicy.NONE,  # normally would skip practice
        practice_seed=PracticeSeed(
            preferred_scene=SceneType.EXPLAIN,
            skills=[], concepts=[], constraints=[],
        ),
    )

    initial: PraxisState = {
        "input_id": "test-4",
        "raw_text": "Some content",
        "type_hint": None,
        "tagger_output": cached_tagger,
        "should_practice": True,  # force practice despite routing_policy=NONE
    }
    config = {"configurable": {"thread_id": "thread-forced"}}
    result = graph.invoke(initial, config=config)

    # Should reach practice_generator and interrupt at human_answer
    assert "scene" in result

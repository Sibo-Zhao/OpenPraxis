"""Graph build and routing logic tests."""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END
from langgraph.types import Command

from openpraxis.graph import build_graph, route_after_tagger, route_after_coach, PraxisState
from openpraxis.models import (
    CapabilityMap,
    InputType,
    PracticeMessage,
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


def test_route_after_coach_ready() -> None:
    state: PraxisState = {"coach_ready": True, "practice_round": 1}
    assert route_after_coach(state) == "practice_evaluator"


def test_route_after_coach_max_rounds() -> None:
    from openpraxis.nodes.practice import MAX_PRACTICE_ROUNDS
    state: PraxisState = {"coach_ready": False, "practice_round": MAX_PRACTICE_ROUNDS}
    assert route_after_coach(state) == "practice_evaluator"


def test_route_after_coach_continue() -> None:
    state: PraxisState = {"coach_ready": False, "practice_round": 1}
    assert route_after_coach(state) == "human_turn"


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
    assert result["tagger_output"] is not None


@pytest.mark.usefixtures("mock_llm")
def test_graph_practice_path_first_interrupt() -> None:
    """When should_practice=True, graph pauses at human_turn (first interrupt)."""
    builder = build_graph()
    graph = builder.compile(checkpointer=MemorySaver())

    initial: PraxisState = {
        "input_id": "test-2",
        "raw_text": "A technical report on RAG.",
        "type_hint": "report",
    }
    config = {"configurable": {"thread_id": "thread-practice"}}
    result = graph.invoke(initial, config=config)

    # Graph should have tagger_output, scene, and first coach message
    assert "tagger_output" in result
    assert "scene" in result
    scene = result["scene"]
    assert scene.scene_id is not None
    assert scene.role == "Tech Lead"

    # Should have one coach message (first turn)
    assert "practice_messages" in result
    assert len(result["practice_messages"]) == 1
    assert result["practice_messages"][0].role == "coach"

    # Should NOT have performance yet (interrupted before evaluator)
    assert "performance" not in result


@pytest.mark.usefixtures("mock_llm")
def test_graph_multi_turn_full_resume() -> None:
    """Test full multi-turn flow: coach asks -> user replies -> coach follows up -> ... -> evaluator -> insight."""
    builder = build_graph()
    graph = builder.compile(checkpointer=MemorySaver())

    initial: PraxisState = {
        "input_id": "test-3",
        "raw_text": "A technical report on RAG.",
        "type_hint": "report",
    }
    config = {"configurable": {"thread_id": "thread-multi-turn"}}

    # Phase 1: invoke until first interrupt (coach asks first question)
    result1 = graph.invoke(initial, config=config)
    assert "scene" in result1
    assert len(result1["practice_messages"]) == 1
    assert result1["practice_messages"][0].role == "coach"
    assert "performance" not in result1

    # Phase 2: user replies -> coach follows up -> second interrupt
    result2 = graph.invoke(
        Command(resume="RAG failure modes include retrieval miss and context overflow."),
        config=config,
    )
    # Should now have: coach1, user1, coach2 messages and be at second interrupt
    assert len(result2["practice_messages"]) == 3
    assert result2["practice_messages"][0].role == "coach"
    assert result2["practice_messages"][1].role == "user"
    assert result2["practice_messages"][2].role == "coach"
    assert "performance" not in result2

    # Phase 3: user replies again -> coach says ready -> evaluator -> insight
    result3 = graph.invoke(
        Command(resume="For retrieval miss, I would add monitoring on recall metrics and set alerts."),
        config=config,
    )
    # Should have full conversation: coach1, user1, coach2, user2, coach3 (wrap-up)
    assert len(result3["practice_messages"]) >= 4
    # Should have performance and insights now
    assert "performance" in result3
    assert result3["performance"].performance_signal.clarity == 7
    assert "insights" in result3
    assert len(result3["insights"]) >= 1
    assert result3["insights"][0].insight_title == "Structured expression gap"
    # user_answer should be the formatted conversation
    assert "user_answer" in result3
    assert "[Coach]:" in result3["user_answer"]
    assert "[User]:" in result3["user_answer"]


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

    # Should reach practice_generator, coach_turn, and interrupt at human_turn
    assert "scene" in result
    assert "practice_messages" in result
    assert len(result["practice_messages"]) == 1
    assert result["practice_messages"][0].role == "coach"

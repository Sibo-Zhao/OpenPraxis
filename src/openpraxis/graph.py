"""LangGraph StateGraph definition."""

import sqlite3
from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from openpraxis.models import (
    InsightCard,
    PracticePerformance,
    PracticeScene,
    TaggerOutput,
)


class PraxisState(TypedDict, total=False):
    input_id: str
    raw_text: str
    type_hint: str | None
    tagger_output: TaggerOutput
    scene: PracticeScene
    user_answer: str
    performance: PracticePerformance
    insights: list[InsightCard]
    should_practice: bool


def route_after_tagger(state: PraxisState) -> str:
    """Conditional edge: enter Practice based on should_practice."""
    if state.get("should_practice"):
        return "practice_generator"
    return END


def build_graph():
    """Build StateGraph (no checkpointer)."""
    from openpraxis.nodes.practice import (
        human_answer_node,
        practice_evaluator_node,
        practice_generator_node,
    )
    from openpraxis.nodes.insight import insight_generator_node
    from openpraxis.nodes.tagger import tagger_node

    builder = StateGraph(PraxisState)
    builder.add_node("tagger", tagger_node)
    builder.add_node("practice_generator", practice_generator_node)
    builder.add_node("human_answer", human_answer_node)
    builder.add_node("practice_evaluator", practice_evaluator_node)
    builder.add_node("insight_generator", insight_generator_node)

    builder.add_edge(START, "tagger")
    builder.add_conditional_edges(
        "tagger",
        route_after_tagger,
        {"practice_generator": "practice_generator", END: END},
    )
    builder.add_edge("practice_generator", "human_answer")
    builder.add_edge("human_answer", "practice_evaluator")
    builder.add_edge("practice_evaluator", "insight_generator")
    builder.add_edge("insight_generator", END)

    return builder


def get_compiled_graph(db_path: str):
    """Compiled graph with SqliteSaver. thread_id = input_id."""
    conn = sqlite3.connect(
        str(db_path) + ".checkpoints",
        check_same_thread=False,
    )
    checkpointer = SqliteSaver(conn)
    return build_graph().compile(checkpointer=checkpointer)

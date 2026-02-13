"""LangGraph 节点：Tagger / Practice / Insight。"""

from openpraxis.nodes.tagger import tagger_node
from openpraxis.nodes.practice import (
    human_answer_node,
    practice_evaluator_node,
    practice_generator_node,
)
from openpraxis.nodes.insight import insight_generator_node

__all__ = [
    "tagger_node",
    "practice_generator_node",
    "human_answer_node",
    "practice_evaluator_node",
    "insight_generator_node",
]

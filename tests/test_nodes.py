"""节点函数隔离测试（Mock call_structured）。"""

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
        "raw_text": "这是一篇关于 RAG 的报告。",
        "type_hint": None,
    }
    out = tagger_node(state)
    assert "tagger_output" in out
    assert "should_practice" in out
    assert out["tagger_output"].summary == "一篇关于 RAG 流水线架构的技术报告。"
    assert out["should_practice"] is True


@pytest.mark.usefixtures("mock_llm")
def test_practice_generator_node(mock_tagger_output) -> None:
    state = {
        "tagger_output": mock_tagger_output,
        "raw_text": "原始内容",
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
        "user_answer": "我的回答内容",
        "raw_text": "原始",
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
            summary="摘要",
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
        "user_answer": "回答",
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
    assert out["insights"][0].insight_title == "结构化表达缺口"

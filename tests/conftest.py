"""共享 fixtures 与 mock。"""

import pytest
from unittest.mock import patch

from openpraxis.models import (
    CapabilityMap,
    InsightCard,
    InsightList,
    InsightType,
    InputType,
    PracticePerformance,
    PracticeScene,
    PracticeSceneLLM,
    PerformanceSignal,
    PracticeSeed,
    RoutingPolicy,
    SceneType,
    Sensitivity,
    Tags,
    TaggerOutput,
)


@pytest.fixture
def mock_tagger_output() -> TaggerOutput:
    return TaggerOutput(
        input_type=InputType.REPORT,
        summary="一篇关于 RAG 流水线架构的技术报告。",
        tags=Tags(
            topics=["RAG"],
            domains=["ML System"],
            difficulty=3,
            sensitivity=Sensitivity.NORMAL,
        ),
        capability_map=CapabilityMap(
            concept_understanding=7,
            structuring=5,
            tradeoff_thinking=4,
            system_thinking=6,
            communication=5,
        ),
        routing_policy=RoutingPolicy.RECOMMEND,
        practice_seed=PracticeSeed(
            preferred_scene=SceneType.EXPLAIN,
            skills=["failure-mode framing"],
            concepts=["retrieval"],
            constraints=["3 minutes"],
        ),
    )


@pytest.fixture
def mock_scene() -> PracticeScene:
    return PracticeScene(
        scene_id="test-scene-id",
        scene_type=SceneType.EXPLAIN,
        role="Tech Lead",
        task="在 3 分钟内解释 RAG 的失败模式。",
        constraints=["3 minutes", "包含 1 个 failure mode"],
        rubric=["clarity", "reasoning_depth", "decision_quality", "communication"],
        expected_structure_hint=["定义", "例子", "缓解"],
    )


@pytest.fixture
def mock_performance() -> PracticePerformance:
    return PracticePerformance(
        performance_signal=PerformanceSignal(
            clarity=7,
            reasoning_depth=6,
            decision_quality=6,
            communication=7,
        ),
        improvement_vectors=["可补充具体案例", "时间分配可更明确"],
    )


@pytest.fixture
def mock_insight_list() -> InsightList:
    return InsightList(
        cards=[
            InsightCard(
                insight_title="结构化表达缺口",
                insight_type=InsightType.STRUCTURING_GAP,
                what_happened="回答未按定义→例子→缓解展开",
                why_it_matters="面试中结构不清会降低可信度",
                upgrade_pattern="Always do 定义 → 例子 → 缓解",
                micro_practice="30 秒内说出一个概念的三个要点",
                concepts=["RAG"],
                skills=["structuring"],
                scenes=["test-scene-id"],
                intensity=2,
            ),
        ]
    )


@pytest.fixture
def mock_llm(
    mock_tagger_output: TaggerOutput,
    mock_scene: PracticeScene,
    mock_performance: PracticePerformance,
    mock_insight_list: InsightList,
):
    """Patch call_structured，按 response_model 返回对应 fixture。"""
    from openpraxis.models import PracticeSceneLLM

    def fake_call(system_prompt, user_content, response_model, **kwargs):
        if response_model == TaggerOutput:
            return mock_tagger_output
        if response_model == PracticeSceneLLM:
            llm_scene = PracticeSceneLLM(
                scene_type=mock_scene.scene_type,
                role=mock_scene.role,
                task=mock_scene.task,
                constraints=mock_scene.constraints,
                rubric=mock_scene.rubric,
                expected_structure_hint=mock_scene.expected_structure_hint,
            )
            return llm_scene
        if response_model == PracticePerformance:
            return mock_performance
        if response_model == InsightList:
            return mock_insight_list
        raise ValueError(f"Unknown response_model: {response_model}")

    # Patch 在节点模块中的引用，否则节点已绑定到真实 call_structured
    with patch("openpraxis.nodes.tagger.call_structured", side_effect=fake_call), \
         patch("openpraxis.nodes.practice.call_structured", side_effect=fake_call), \
         patch("openpraxis.nodes.insight.call_structured", side_effect=fake_call):
        yield

"""Shared fixtures and mocks."""

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
        summary="A technical report on RAG pipeline architecture.",
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
        task="Explain RAG failure modes in 3 minutes.",
        constraints=["3 minutes", "Include 1 failure mode"],
        rubric=["clarity", "reasoning_depth", "decision_quality", "communication"],
        expected_structure_hint=["Definition", "Example", "Mitigation"],
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
        improvement_vectors=["Add concrete examples", "Time allocation could be clearer"],
    )


@pytest.fixture
def mock_insight_list() -> InsightList:
    return InsightList(
        cards=[
            InsightCard(
                insight_title="Structured expression gap",
                insight_type=InsightType.STRUCTURING_GAP,
                what_happened="Answer did not follow definition → example → mitigation",
                why_it_matters="Unclear structure in interviews reduces credibility",
                upgrade_pattern="Always do definition → example → mitigation",
                micro_practice="State three points of a concept in 30 seconds",
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
    """Patch call_structured to return the corresponding fixture by response_model."""
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

    # Patch references in node modules; otherwise nodes are bound to real call_structured
    with patch("openpraxis.nodes.tagger.call_structured", side_effect=fake_call), \
         patch("openpraxis.nodes.practice.call_structured", side_effect=fake_call), \
         patch("openpraxis.nodes.insight.call_structured", side_effect=fake_call):
        yield

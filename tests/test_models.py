"""Pydantic model and enum tests."""

import pytest
from pydantic import ValidationError

from openpraxis.models import (
    CapabilityMap,
    InputType,
    PracticeScene,
    Tags,
    TaggerOutput,
    Sensitivity,
    RoutingPolicy,
    SceneType,
    InsightType,
    InsightCard,
    PerformanceSignal,
    PracticePerformance,
)


def test_input_type_enum() -> None:
    assert InputType.REPORT.value == "report"
    assert InputType.INTERVIEW.value == "interview"


def test_tags_valid() -> None:
    t = Tags(
        topics=["RAG"],
        domains=["ML"],
        difficulty=3,
        sensitivity=Sensitivity.NORMAL,
    )
    assert t.difficulty == 3
    assert t.sensitivity == Sensitivity.NORMAL


def test_tags_difficulty_bounds() -> None:
    with pytest.raises(ValidationError):
        Tags(topics=[], domains=[], difficulty=0)
    with pytest.raises(ValidationError):
        Tags(topics=[], domains=[], difficulty=6)


def test_capability_map_bounds() -> None:
    CapabilityMap(
        concept_understanding=5,
        structuring=5,
        tradeoff_thinking=5,
        system_thinking=5,
        communication=5,
    )
    with pytest.raises(ValidationError):
        CapabilityMap(
            concept_understanding=11,
            structuring=0,
            tradeoff_thinking=0,
            system_thinking=0,
            communication=0,
        )


def test_practice_scene_has_scene_id() -> None:
    scene = PracticeScene(
        scene_type=SceneType.EXPLAIN,
        role="Dev",
        task="Explain X",
        constraints=[],
        rubric=[],
        expected_structure_hint=[],
    )
    assert scene.scene_id is not None
    assert len(scene.scene_id) > 0


def test_insight_card_intensity_bounds() -> None:
    with pytest.raises(ValidationError):
        InsightCard(
            insight_title="x",
            insight_type=InsightType.STRUCTURING_GAP,
            what_happened="x",
            why_it_matters="x",
            upgrade_pattern="x",
            micro_practice="x",
            concepts=[],
            skills=[],
            scenes=[],
            intensity=0,
        )


def test_performance_signal_bounds() -> None:
    PerformanceSignal(clarity=5, reasoning_depth=5, decision_quality=5, communication=5)
    with pytest.raises(ValidationError):
        PerformanceSignal(
            clarity=11,
            reasoning_depth=0,
            decision_quality=0,
            communication=0,
        )

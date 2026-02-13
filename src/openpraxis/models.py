"""所有 Pydantic 模型与枚举。"""

from __future__ import annotations

from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

# ============================================================
# 枚举
# ============================================================


class InputType(str, Enum):
    REPORT = "report"
    INTERVIEW = "interview"
    REFLECTION = "reflection"
    IDEA = "idea"


class Sensitivity(str, Enum):
    NORMAL = "normal"
    PRIVATE = "private"


class RoutingPolicy(str, Enum):
    NONE = "none"
    RECOMMEND = "recommend"
    REQUIRED = "required"


class SceneType(str, Enum):
    EXPLAIN = "explain"
    CRITIQUE = "critique"
    DESIGN = "design"
    DECISION = "decision"
    INTERVIEW_FOLLOWUP = "interview_followup"
    POSTMORTEM = "postmortem"


class InsightType(str, Enum):
    STRUCTURING_GAP = "structuring_gap"
    FAILURE_MODE_GAP = "failure_mode_gap"
    TRADEOFF_GAP = "tradeoff_gap"
    METRIC_GAP = "metric_gap"
    EXAMPLE_GAP = "example_gap"
    ASSUMPTION_GAP = "assumption_gap"


# ============================================================
# Tagger 模型
# ============================================================


class Tags(BaseModel):
    topics: list[str]
    domains: list[str]
    difficulty: int = Field(ge=1, le=5)
    sensitivity: Sensitivity = Sensitivity.NORMAL


class CapabilityMap(BaseModel):
    concept_understanding: int = Field(ge=0, le=10)
    structuring: int = Field(ge=0, le=10)
    tradeoff_thinking: int = Field(ge=0, le=10)
    system_thinking: int = Field(ge=0, le=10)
    communication: int = Field(ge=0, le=10)


class PracticeSeed(BaseModel):
    preferred_scene: SceneType
    skills: list[str]
    concepts: list[str]
    constraints: list[str]


class TaggerOutput(BaseModel):
    input_type: InputType
    summary: str
    tags: Tags
    capability_map: CapabilityMap
    routing_policy: RoutingPolicy
    practice_seed: PracticeSeed


# ============================================================
# Practice 模型
# ============================================================


class PracticeSceneLLM(BaseModel):
    """发送给 LLM 的 schema（不含 scene_id，由应用生成）。"""

    scene_type: SceneType
    role: str
    task: str
    constraints: list[str]
    rubric: list[str]
    expected_structure_hint: list[str]


class PracticeScene(BaseModel):
    """完整场景模型（含 scene_id）。"""

    scene_id: str = Field(default_factory=lambda: str(uuid4()))
    scene_type: SceneType
    role: str
    task: str
    constraints: list[str]
    rubric: list[str]
    expected_structure_hint: list[str]


class PerformanceSignal(BaseModel):
    clarity: int = Field(ge=0, le=10)
    reasoning_depth: int = Field(ge=0, le=10)
    decision_quality: int = Field(ge=0, le=10)
    communication: int = Field(ge=0, le=10)


class PracticePerformance(BaseModel):
    performance_signal: PerformanceSignal
    improvement_vectors: list[str]


# ============================================================
# Insight 模型
# ============================================================


class InsightCard(BaseModel):
    insight_title: str
    insight_type: InsightType
    what_happened: str
    why_it_matters: str
    upgrade_pattern: str
    micro_practice: str
    concepts: list[str]
    skills: list[str]
    scenes: list[str]  # 关联的 scene_id
    intensity: int = Field(ge=1, le=5)


class InsightList(BaseModel):
    """LLM 返回的包装模型（OpenAI structured output 要求顶层为 object）。"""

    cards: list[InsightCard]

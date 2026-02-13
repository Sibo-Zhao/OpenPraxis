"""Insight 生成节点。"""

from openpraxis.llm import call_structured
from openpraxis.models import InsightCard, InsightList
from openpraxis.prompts import get_insight_generator_system_prompt


def insight_generator_node(state: dict) -> dict:
    """从 Tagger + 场景 + 回答 + 评估 生成洞察卡。"""
    tagger_output = state["tagger_output"]
    scene = state["scene"]
    user_answer = state["user_answer"]
    performance = state["performance"]
    user_content = (
        f"输入摘要: {tagger_output.summary}\n"
        f"能力映射: {tagger_output.capability_map.model_dump()}\n\n"
        f"场景: {scene.role} — {scene.task}\n"
        f"用户回答: {user_answer}\n\n"
        f"评估: {performance.performance_signal.model_dump()}\n"
        f"改进向量: {performance.improvement_vectors}\n\n"
        f"scene_id: {scene.scene_id}"
    )
    result: InsightList = call_structured(
        get_insight_generator_system_prompt(),
        user_content,
        InsightList,
    )
    return {"insights": result.cards}

"""图构建与路由逻辑测试。"""

from langgraph.graph import END

from openpraxis.graph import build_graph, route_after_tagger, PraxisState


def test_route_after_tagger_should_practice() -> None:
    state: PraxisState = {"should_practice": True}
    assert route_after_tagger(state) == "practice_generator"


def test_route_after_tagger_no_practice() -> None:
    state: PraxisState = {"should_practice": False}
    assert route_after_tagger(state) == END


def test_build_graph() -> None:
    graph = build_graph()
    assert graph is not None
    # 编译后应可调用
    compiled = graph.compile()
    assert compiled is not None
